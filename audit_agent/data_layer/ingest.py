"""
Data Ingestion: Load raw data into Parquet format

Supports:
- CSV files (for POC)
- PostgreSQL tables (for production)
- Automatic partitioning by year/month
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import structlog

logger = structlog.get_logger()


class DataIngestion:
    """Handles data ingestion from various sources to Parquet format"""

    def __init__(self, output_base_path: str = "data/parquet"):
        """
        Initialize data ingestion

        Args:
            output_base_path: Base directory for Parquet files
        """
        self.output_base_path = Path(output_base_path)
        self.output_base_path.mkdir(parents=True, exist_ok=True)
        self.ingestion_log = []

    def load_csv_to_parquet(
        self,
        csv_path: str,
        table_name: str,
        partition_cols: Optional[List[str]] = None,
        date_column: Optional[str] = None
    ) -> Dict:
        """
        Load CSV file to Parquet with optional partitioning

        Args:
            csv_path: Path to CSV file
            table_name: Name for the table (used in output path)
            partition_cols: Columns to partition by (e.g., ['year', 'month'])
            date_column: Column to extract year/month from

        Returns:
            Dict with ingestion metadata
        """
        start_time = datetime.now()
        logger.info("csv_ingestion_started", csv_path=csv_path, table=table_name)

        try:
            # Read CSV
            df = pd.read_csv(csv_path)
            row_count = len(df)

            # Extract year/month if date column provided
            if date_column and date_column in df.columns:
                df[date_column] = pd.to_datetime(df[date_column])
                df['year'] = df[date_column].dt.year
                df['month'] = df[date_column].dt.month

            # Convert to PyArrow table
            table = pa.Table.from_pandas(df)

            # Determine output path
            output_path = self.output_base_path / table_name

            # Write Parquet (partitioned or single file)
            if partition_cols:
                pq.write_to_dataset(
                    table,
                    root_path=str(output_path),
                    partition_cols=partition_cols
                )
            else:
                output_path.mkdir(parents=True, exist_ok=True)
                pq.write_table(table, output_path / "data.parquet")

            duration = (datetime.now() - start_time).total_seconds()

            metadata = {
                "table_name": table_name,
                "source": csv_path,
                "row_count": row_count,
                "column_count": len(df.columns),
                "columns": list(df.columns),
                "output_path": str(output_path),
                "partitioned": partition_cols is not None,
                "partition_cols": partition_cols,
                "duration_seconds": duration,
                "timestamp": datetime.now().isoformat(),
            }

            self.ingestion_log.append(metadata)

            logger.info(
                "csv_ingestion_completed",
                table=table_name,
                rows=row_count,
                duration=duration
            )

            return metadata

        except Exception as e:
            logger.error("csv_ingestion_failed", error=str(e), csv_path=csv_path)
            raise

    def load_postgres_to_parquet(
        self,
        connection_string: str,
        table_name: str,
        query: Optional[str] = None,
        date_range: Optional[tuple] = None
    ) -> Dict:
        """
        Load PostgreSQL table/query to Parquet

        Args:
            connection_string: PostgreSQL connection string
            table_name: Table name to load
            query: Optional custom SQL query (overrides table_name)
            date_range: Optional (start_date, end_date) for filtering

        Returns:
            Dict with ingestion metadata
        """
        start_time = datetime.now()
        logger.info("postgres_ingestion_started", table=table_name)

        try:
            import psycopg2
            from sqlalchemy import create_engine

            engine = create_engine(connection_string)

            # Build query
            if query:
                sql = query
            elif date_range:
                start_date, end_date = date_range
                sql = f"""
                    SELECT * FROM {table_name}
                    WHERE transaction_date BETWEEN '{start_date}' AND '{end_date}'
                """
            else:
                sql = f"SELECT * FROM {table_name}"

            # Read to DataFrame
            df = pd.read_sql(sql, engine)
            row_count = len(df)

            # Convert to PyArrow and write
            table = pa.Table.from_pandas(df)
            output_path = self.output_base_path / table_name
            output_path.mkdir(parents=True, exist_ok=True)

            pq.write_table(table, output_path / "data.parquet")

            duration = (datetime.now() - start_time).total_seconds()

            metadata = {
                "table_name": table_name,
                "source": "postgresql",
                "row_count": row_count,
                "column_count": len(df.columns),
                "columns": list(df.columns),
                "output_path": str(output_path),
                "duration_seconds": duration,
                "timestamp": datetime.now().isoformat(),
            }

            self.ingestion_log.append(metadata)

            logger.info(
                "postgres_ingestion_completed",
                table=table_name,
                rows=row_count,
                duration=duration
            )

            return metadata

        except Exception as e:
            logger.error("postgres_ingestion_failed", error=str(e), table=table_name)
            raise

    def validate_ingestion(self, expected_counts: Optional[Dict[str, int]] = None) -> Dict:
        """
        Validate ingestion results

        Args:
            expected_counts: Optional dict of {table_name: expected_row_count}

        Returns:
            Validation report
        """
        report = {
            "total_tables": len(self.ingestion_log),
            "total_rows": sum(log["row_count"] for log in self.ingestion_log),
            "tables": {},
            "issues": []
        }

        for log in self.ingestion_log:
            table_name = log["table_name"]
            actual_count = log["row_count"]

            report["tables"][table_name] = {
                "row_count": actual_count,
                "column_count": log["column_count"],
                "status": "ok"
            }

            # Check against expected counts
            if expected_counts and table_name in expected_counts:
                expected = expected_counts[table_name]
                if actual_count != expected:
                    issue = f"{table_name}: expected {expected} rows, got {actual_count}"
                    report["issues"].append(issue)
                    report["tables"][table_name]["status"] = "mismatch"
                    logger.warning("row_count_mismatch", table=table_name, expected=expected, actual=actual_count)

        report["validation_passed"] = len(report["issues"]) == 0

        return report

    def get_ingestion_summary(self) -> pd.DataFrame:
        """Get summary of all ingestions as DataFrame"""
        if not self.ingestion_log:
            return pd.DataFrame()

        return pd.DataFrame(self.ingestion_log)
