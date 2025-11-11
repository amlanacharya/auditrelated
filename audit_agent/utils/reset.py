"""
Reset Utility: Drop all tables and clear data for fresh start

Provides functionality to:
- Drop all SQLite knowledge graph tables
- Delete all parquet data files
- Clean up temporary files
"""

import sqlite3
import shutil
from pathlib import Path
from typing import Optional
import structlog

logger = structlog.get_logger()


class ResetManager:
    """Manage system reset operations"""

    def __init__(self, kg_db_path: str = "data/kg.db", parquet_path: str = "data/parquet"):
        """
        Initialize ResetManager

        Args:
            kg_db_path: Path to knowledge graph SQLite database
            parquet_path: Path to parquet data directory
        """
        self.kg_db_path = Path(kg_db_path)
        self.parquet_path = Path(parquet_path)

    def drop_all_tables(self) -> bool:
        """
        Drop all tables from the knowledge graph database

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.kg_db_path.exists():
                logger.info("kg_database_not_found", path=str(self.kg_db_path))
                return True

            conn = sqlite3.connect(str(self.kg_db_path))
            cursor = conn.cursor()

            # Get all table names
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            tables = cursor.fetchall()

            # Drop each table
            for (table_name,) in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                logger.info("table_dropped", table=table_name)

            conn.commit()
            conn.close()

            logger.info("all_tables_dropped", count=len(tables))
            return True

        except Exception as e:
            logger.error("error_dropping_tables", error=str(e))
            return False

    def delete_parquet_data(self) -> bool:
        """
        Delete all parquet data files

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.parquet_path.exists():
                logger.info("parquet_directory_not_found", path=str(self.parquet_path))
                return True

            # Remove entire parquet directory
            shutil.rmtree(str(self.parquet_path))
            logger.info("parquet_data_deleted", path=str(self.parquet_path))

            # Recreate empty directory
            self.parquet_path.mkdir(parents=True, exist_ok=True)

            return True

        except Exception as e:
            logger.error("error_deleting_parquet", error=str(e))
            return False

    def delete_database_file(self) -> bool:
        """
        Delete the entire database file

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.kg_db_path.exists():
                self.kg_db_path.unlink()
                logger.info("database_file_deleted", path=str(self.kg_db_path))
            return True

        except Exception as e:
            logger.error("error_deleting_database", error=str(e))
            return False

    def reset_all(self, delete_db_file: bool = False) -> dict:
        """
        Perform complete system reset

        Args:
            delete_db_file: If True, delete entire DB file; if False, just drop tables

        Returns:
            Dict with reset status for each component
        """
        results = {}

        # Drop tables or delete DB file
        if delete_db_file:
            results['database'] = self.delete_database_file()
        else:
            results['database'] = self.drop_all_tables()

        # Delete parquet data
        results['parquet_data'] = self.delete_parquet_data()

        # Overall success
        results['success'] = all(results.values())

        if results['success']:
            logger.info("system_reset_complete", results=results)
        else:
            logger.error("system_reset_incomplete", results=results)

        return results

    def get_system_status(self) -> dict:
        """
        Get current system status (what exists)

        Returns:
            Dict with status of each component
        """
        status = {
            'kg_database_exists': self.kg_db_path.exists(),
            'kg_database_size_mb': 0,
            'parquet_directory_exists': self.parquet_path.exists(),
            'parquet_files_count': 0,
            'parquet_total_size_mb': 0,
        }

        # Get DB size
        if status['kg_database_exists']:
            status['kg_database_size_mb'] = self.kg_db_path.stat().st_size / (1024 * 1024)

        # Get parquet stats
        if status['parquet_directory_exists']:
            parquet_files = list(self.parquet_path.rglob("*.parquet"))
            status['parquet_files_count'] = len(parquet_files)
            status['parquet_total_size_mb'] = sum(
                f.stat().st_size for f in parquet_files
            ) / (1024 * 1024)

        return status


def reset_system(
    kg_db_path: str = "data/kg.db",
    parquet_path: str = "data/parquet",
    delete_db_file: bool = False
) -> dict:
    """
    Convenience function to reset the entire system

    Args:
        kg_db_path: Path to knowledge graph database
        parquet_path: Path to parquet directory
        delete_db_file: If True, delete DB file completely

    Returns:
        Dict with reset results
    """
    manager = ResetManager(kg_db_path, parquet_path)
    return manager.reset_all(delete_db_file=delete_db_file)
