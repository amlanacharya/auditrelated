"""
Data Layer: Parquet storage + DuckDB query engine

Components:
- DataIngestion: Load data from CSV/Postgres → Parquet
- QueryEngine: Execute SQL queries on Parquet files via DuckDB
- SchemaExtractor: Extract metadata for Knowledge Graph
"""

from audit_agent.data_layer.ingest import DataIngestion
from audit_agent.data_layer.query_engine import QueryEngine
from audit_agent.data_layer.schema_extractor import SchemaExtractor

__all__ = ["DataIngestion", "QueryEngine", "SchemaExtractor"]
