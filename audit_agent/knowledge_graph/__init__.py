"""
Knowledge Graph: SQLite-based storage for business process context

Four graph components:
1. Process Graph: Business workflow definitions (A→B→C→D)
2. Entity Relationship Graph: Employee hierarchies, approval limits
3. Table Relationship Graph: Schema mappings, join keys
4. Violation Pattern Graph: Reusable rule library
"""

from audit_agent.knowledge_graph.kg_storage import KnowledgeGraphManager
from audit_agent.knowledge_graph.process_graph import ProcessGraph
from audit_agent.knowledge_graph.entity_graph import EntityGraph
from audit_agent.knowledge_graph.table_graph import TableGraph
from audit_agent.knowledge_graph.violation_graph import ViolationGraph

__all__ = [
    "KnowledgeGraphManager",
    "ProcessGraph",
    "EntityGraph",
    "TableGraph",
    "ViolationGraph",
]
