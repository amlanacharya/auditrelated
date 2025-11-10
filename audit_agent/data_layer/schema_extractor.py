"""
Schema Extractor: Extract metadata from Parquet files for Knowledge Graph

Extracts:
- Column names and data types
- Nullable constraints
- Foreign key candidates (via naming patterns)
- Data statistics (min, max, distinct counts)
"""

from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import pyarrow.parquet as pq
import structlog

logger = structlog.get_logger()


class SchemaExtractor:
    """Extract schema metadata from Parquet files"""

    def __init__(self, parquet_base_path: str = "data/parquet"):
        """
        Initialize schema extractor

        Args:
            parquet_base_path: Base path where Parquet files are stored
        """
        self.parquet_base_path = Path(parquet_base_path)
        self.schemas = {}

    def extract_schema(self, table_name: str) -> Dict:
        """
        Extract schema metadata from a Parquet table

        Args:
            table_name: Name of the table

        Returns:
            Dict with schema information
        """
        table_path = self.parquet_base_path / table_name

        # Find parquet file(s)
        parquet_files = list(table_path.rglob("*.parquet"))

        if not parquet_files:
            raise ValueError(f"No Parquet files found for table: {table_name}")

        # Read schema from first file (all should be consistent)
        parquet_file = pq.ParquetFile(parquet_files[0])
        schema = parquet_file.schema_arrow

        # Extract column metadata
        columns = []
        for field in schema:
            column_info = {
                "name": field.name,
                "type": str(field.type),
                "nullable": field.nullable,
                "is_id_column": self._is_id_column(field.name),
                "is_foreign_key_candidate": self._is_foreign_key_candidate(field.name),
            }
            columns.append(column_info)

        metadata = {
            "table_name": table_name,
            "column_count": len(columns),
            "columns": columns,
            "parquet_files": len(parquet_files),
            "file_paths": [str(f) for f in parquet_files],
        }

        self.schemas[table_name] = metadata

        logger.info(
            "schema_extracted",
            table=table_name,
            columns=len(columns),
            files=len(parquet_files)
        )

        return metadata

    def extract_statistics(self, table_name: str) -> Dict:
        """
        Extract data statistics for a table

        Args:
            table_name: Name of the table

        Returns:
            Dict with statistics
        """
        table_path = self.parquet_base_path / table_name
        parquet_files = list(table_path.rglob("*.parquet"))

        # Read first file for statistics (sampling approach)
        df = pd.read_parquet(parquet_files[0])

        stats = {
            "table_name": table_name,
            "row_count": len(df),
            "column_stats": {}
        }

        for col in df.columns:
            col_stats = {
                "dtype": str(df[col].dtype),
                "null_count": int(df[col].isna().sum()),
                "null_percentage": round(df[col].isna().mean() * 100, 2),
                "distinct_count": int(df[col].nunique()),
            }

            # Numeric columns: add min/max/mean
            if pd.api.types.is_numeric_dtype(df[col]):
                col_stats.update({
                    "min": float(df[col].min()) if not df[col].isna().all() else None,
                    "max": float(df[col].max()) if not df[col].isna().all() else None,
                    "mean": round(float(df[col].mean()), 2) if not df[col].isna().all() else None,
                })

            stats["column_stats"][col] = col_stats

        return stats

    def infer_relationships(self, schemas: Optional[List[str]] = None) -> List[Dict]:
        """
        Infer foreign key relationships between tables

        Args:
            schemas: Optional list of table names to analyze (default: all)

        Returns:
            List of inferred relationships
        """
        if schemas is None:
            schemas = list(self.schemas.keys())

        relationships = []

        # Simple heuristic: match column names ending in _id
        for table_name, schema in self.schemas.items():
            if table_name not in schemas:
                continue

            for column in schema["columns"]:
                if column["is_foreign_key_candidate"]:
                    # Try to find matching table
                    # e.g., "employee_id" → "employees" table
                    potential_table = self._guess_referenced_table(column["name"])

                    if potential_table in self.schemas:
                        relationship = {
                            "from_table": table_name,
                            "from_column": column["name"],
                            "to_table": potential_table,
                            "to_column": "id",  # assumption
                            "confidence": "high" if column["name"].endswith("_id") else "medium",
                        }
                        relationships.append(relationship)

        logger.info("relationships_inferred", count=len(relationships))

        return relationships

    def _is_id_column(self, column_name: str) -> bool:
        """Check if column is likely an ID column"""
        name_lower = column_name.lower()
        return name_lower == "id" or name_lower.endswith("_id")

    def _is_foreign_key_candidate(self, column_name: str) -> bool:
        """Check if column is likely a foreign key"""
        name_lower = column_name.lower()
        # Foreign keys typically end with _id but not just "id"
        return name_lower.endswith("_id") and name_lower != "id"

    def _guess_referenced_table(self, column_name: str) -> str:
        """
        Guess the referenced table from a foreign key column name

        Examples:
            employee_id → employees
            manager_id → managers or employees
            vendor_id → vendors
        """
        # Remove _id suffix
        base_name = column_name.lower().replace("_id", "")

        # Pluralize (simple heuristic)
        if base_name.endswith("y"):
            return base_name[:-1] + "ies"  # category → categories
        elif base_name.endswith("s"):
            return base_name  # already plural
        else:
            return base_name + "s"  # employee → employees

    def export_schemas(self, output_path: str):
        """
        Export all schemas to JSON file

        Args:
            output_path: Path to save schemas JSON
        """
        import json

        with open(output_path, "w") as f:
            json.dump(self.schemas, f, indent=2)

        logger.info("schemas_exported", path=output_path, count=len(self.schemas))

    def get_schema_summary(self) -> pd.DataFrame:
        """Get summary of all extracted schemas"""
        if not self.schemas:
            return pd.DataFrame()

        summary = []
        for table_name, schema in self.schemas.items():
            summary.append({
                "table_name": table_name,
                "column_count": schema["column_count"],
                "parquet_files": schema["parquet_files"],
            })

        return pd.DataFrame(summary)
