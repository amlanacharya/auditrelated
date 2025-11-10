"""
Intelligent Audit Agent

90% SQL-based violation detection + 10% AI assistance for compliance-grade auditing.
"""

__version__ = "0.1.0"
__author__ = "Audit Agent Team"

from audit_agent.data_layer import DataIngestion, QueryEngine, SchemaExtractor
from audit_agent.knowledge_graph import KnowledgeGraphManager

__all__ = [
    "DataIngestion",
    "QueryEngine",
    "SchemaExtractor",
    "KnowledgeGraphManager",
]
