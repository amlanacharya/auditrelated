"""
Knowledge Graph Storage: SQLite-based graph database

Manages all four KG components with ACID transactions and versioning.
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
import json
from datetime import datetime
import structlog

logger = structlog.get_logger()


class KnowledgeGraphManager:
    """Manages the Knowledge Graph SQLite database"""

    def __init__(self, db_path: str = "data/kg.db"):
        """
        Initialize Knowledge Graph database

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Thread-safe connection for Streamlit
        # check_same_thread=False is safe because Python GIL ensures sequential execution
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Return rows as dicts

        self._initialize_schema()

        logger.info("knowledge_graph_initialized", db_path=str(self.db_path))

    def _initialize_schema(self):
        """Create all KG tables if they don't exist"""

        # Process Graph Tables
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS process_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                process_name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS process_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                process_type_id INTEGER NOT NULL,
                step_name TEXT NOT NULL,
                sequence_order INTEGER NOT NULL,
                required_table TEXT,
                expected_duration_minutes INTEGER,
                FOREIGN KEY (process_type_id) REFERENCES process_types(id),
                UNIQUE(process_type_id, sequence_order)
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS process_transitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_step_id INTEGER NOT NULL,
                to_step_id INTEGER NOT NULL,
                condition_json TEXT,  -- JSON: optional conditions for transition
                FOREIGN KEY (from_step_id) REFERENCES process_steps(id),
                FOREIGN KEY (to_step_id) REFERENCES process_steps(id)
            )
        """)

        # Entity Relationship Graph Tables
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS entity_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_name TEXT UNIQUE NOT NULL,
                description TEXT
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS entity_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_entity_type TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                to_entity_type TEXT NOT NULL,
                properties_json TEXT,  -- JSON: additional properties
                UNIQUE(from_entity_type, relationship_type, to_entity_type)
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS approval_authorities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                role TEXT NOT NULL,
                max_amount DECIMAL(12, 2),
                effective_from DATE NOT NULL,
                effective_to DATE,
                delegation_from_employee_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Table Relationship Graph Tables
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS table_schemas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT UNIQUE NOT NULL,
                column_count INTEGER,
                schema_json TEXT,  -- JSON: full schema metadata
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS column_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                column_name TEXT NOT NULL,
                mapped_entity TEXT,  -- e.g., "employee_id", "amount"
                data_type TEXT,
                is_nullable BOOLEAN,
                mapping_version INTEGER DEFAULT 1,
                confidence_score DECIMAL(3, 2),
                user_confirmed BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(table_name, column_name, mapping_version)
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS table_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_table TEXT NOT NULL,
                from_column TEXT NOT NULL,
                to_table TEXT NOT NULL,
                to_column TEXT NOT NULL,
                relationship_type TEXT DEFAULT 'foreign_key',
                confidence TEXT DEFAULT 'high',
                UNIQUE(from_table, from_column, to_table, to_column)
            )
        """)

        # Violation Pattern Graph Tables
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS violation_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id TEXT UNIQUE NOT NULL,
                rule_name TEXT NOT NULL,
                description TEXT,
                severity TEXT NOT NULL CHECK(severity IN ('critical', 'high', 'medium', 'low')),
                sql_template TEXT NOT NULL,
                version INTEGER DEFAULT 1,
                effective_from DATE NOT NULL,
                effective_to DATE,
                created_by TEXT,
                change_reason TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS rule_dependencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id TEXT NOT NULL,
                depends_on_rule_id TEXT NOT NULL,
                FOREIGN KEY (rule_id) REFERENCES violation_rules(rule_id),
                FOREIGN KEY (depends_on_rule_id) REFERENCES violation_rules(rule_id)
            )
        """)

        # Audit Log (for compliance)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                action TEXT NOT NULL,
                entity_type TEXT,
                entity_id INTEGER,
                user_id TEXT,
                details_json TEXT
            )
        """)

        self.conn.commit()

        logger.info("kg_schema_initialized")

    def log_action(self, action: str, entity_type: str, entity_id: Optional[int] = None,
                   user_id: Optional[str] = None, details: Optional[Dict] = None):
        """
        Log an action to the audit trail

        Args:
            action: Action type (e.g., 'create', 'update', 'delete')
            entity_type: Type of entity (e.g., 'violation_rule', 'process_step')
            entity_id: ID of affected entity
            user_id: User performing action
            details: Additional details as dict
        """
        self.conn.execute("""
            INSERT INTO audit_log (action, entity_type, entity_id, user_id, details_json)
            VALUES (?, ?, ?, ?, ?)
        """, (action, entity_type, entity_id, user_id, json.dumps(details) if details else None))

        self.conn.commit()

    def export_to_json(self, output_path: str):
        """
        Export entire KG to JSON (for LLM context or backup)

        Args:
            output_path: Path to save JSON file
        """
        export_data = {
            "process_types": self._table_to_dict("process_types"),
            "process_steps": self._table_to_dict("process_steps"),
            "entity_types": self._table_to_dict("entity_types"),
            "entity_relationships": self._table_to_dict("entity_relationships"),
            "table_schemas": self._table_to_dict("table_schemas"),
            "column_mappings": self._table_to_dict("column_mappings"),
            "table_relationships": self._table_to_dict("table_relationships"),
            "violation_rules": self._table_to_dict("violation_rules"),
            "exported_at": datetime.now().isoformat(),
        }

        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        logger.info("kg_exported", path=output_path)

    def _table_to_dict(self, table_name: str) -> List[Dict]:
        """Convert SQLite table to list of dicts"""
        cursor = self.conn.execute(f"SELECT * FROM {table_name}")
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        return [dict(zip(columns, row)) for row in rows]

    def get_statistics(self) -> Dict:
        """Get statistics about the Knowledge Graph"""
        stats = {}

        tables = [
            "process_types", "process_steps", "entity_types",
            "entity_relationships", "table_schemas", "violation_rules"
        ]

        for table in tables:
            cursor = self.conn.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            stats[table] = count

        return stats

    def close(self):
        """Close database connection"""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
            logger.info("knowledge_graph_closed")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures connection is closed"""
        self.close()
        return False  # Don't suppress exceptions
