"""
Table Relationship Graph: Schema mappings and table joins

Manages:
- Table schemas with versioned column mappings
- Foreign key relationships
- Join paths between tables
"""

from typing import Dict, List, Optional
import json
import structlog

logger = structlog.get_logger()


class TableGraph:
    """Manages table schemas and relationships"""

    def __init__(self, kg_manager):
        """
        Initialize TableGraph

        Args:
            kg_manager: KnowledgeGraphManager instance
        """
        self.kg = kg_manager
        self.conn = kg_manager.conn

    def register_table_schema(self, table_name: str, schema: Dict):
        """
        Register a table schema in the KG

        Args:
            table_name: Name of the table
            schema: Schema dict from SchemaExtractor
        """
        column_count = len(schema.get('columns', []))

        self.conn.execute("""
            INSERT OR REPLACE INTO table_schemas (table_name, column_count, schema_json)
            VALUES (?, ?, ?)
        """, (table_name, column_count, json.dumps(schema)))

        self.conn.commit()

        logger.info("table_schema_registered", table=table_name, columns=column_count)

    def add_column_mapping(
        self,
        table_name: str,
        column_name: str,
        mapped_entity: str,
        data_type: str,
        is_nullable: bool,
        confidence_score: float = 1.0,
        user_confirmed: bool = False
    ):
        """
        Map a column to a business entity

        Args:
            table_name: Table name
            column_name: Column name
            mapped_entity: Entity this column represents (e.g., 'employee_id', 'amount')
            data_type: Data type
            is_nullable: Whether column is nullable
            confidence_score: Confidence of mapping (0-1)
            user_confirmed: Whether user validated this mapping
        """
        self.conn.execute("""
            INSERT INTO column_mappings
            (table_name, column_name, mapped_entity, data_type, is_nullable,
             confidence_score, user_confirmed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (table_name, column_name, mapped_entity, data_type, is_nullable,
              confidence_score, user_confirmed))

        self.conn.commit()

        logger.info("column_mapped",
                    table=table_name,
                    column=column_name,
                    entity=mapped_entity,
                    confidence=confidence_score)

    def add_table_relationship(
        self,
        from_table: str,
        from_column: str,
        to_table: str,
        to_column: str,
        confidence: str = "high"
    ):
        """
        Define a foreign key relationship between tables

        Args:
            from_table: Source table
            from_column: Source column (foreign key)
            to_table: Target table
            to_column: Target column (primary key)
            confidence: Confidence level (high, medium, low)
        """
        self.conn.execute("""
            INSERT OR REPLACE INTO table_relationships
            (from_table, from_column, to_table, to_column, confidence)
            VALUES (?, ?, ?, ?, ?)
        """, (from_table, from_column, to_table, to_column, confidence))

        self.conn.commit()

        logger.info("table_relationship_added",
                    from_table=from_table,
                    to_table=to_table,
                    confidence=confidence)

    def get_table_schema(self, table_name: str) -> Optional[Dict]:
        """
        Get schema for a table

        Args:
            table_name: Name of the table

        Returns:
            Schema dict or None
        """
        cursor = self.conn.execute("""
            SELECT schema_json FROM table_schemas WHERE table_name = ?
        """, (table_name,))

        row = cursor.fetchone()

        if row:
            return json.loads(row[0])

        return None

    def get_column_mappings(self, table_name: str) -> List[Dict]:
        """
        Get all column mappings for a table

        Args:
            table_name: Name of the table

        Returns:
            List of column mappings
        """
        cursor = self.conn.execute("""
            SELECT column_name, mapped_entity, data_type, is_nullable,
                   confidence_score, user_confirmed
            FROM column_mappings
            WHERE table_name = ?
            ORDER BY column_name
        """, (table_name,))

        return [dict(row) for row in cursor.fetchall()]

    def get_join_path(self, from_table: str, to_table: str) -> List[Dict]:
        """
        Find join path between two tables

        Args:
            from_table: Source table
            to_table: Target table

        Returns:
            List of join relationships
        """
        # Simple direct join lookup
        cursor = self.conn.execute("""
            SELECT from_table, from_column, to_table, to_column
            FROM table_relationships
            WHERE from_table = ? AND to_table = ?
        """, (from_table, to_table))

        direct_joins = [dict(row) for row in cursor.fetchall()]

        if direct_joins:
            return direct_joins

        # TODO: Implement multi-hop join path discovery
        # For now, just return empty if no direct join

        return []

    def generate_join_sql(self, tables: List[str]) -> str:
        """
        Generate SQL JOIN clause for a list of tables

        Args:
            tables: List of table names to join

        Returns:
            SQL JOIN clause
        """
        if len(tables) < 2:
            return tables[0] if tables else ""

        # Start with first table
        sql = tables[0]

        # Add joins for remaining tables
        for i in range(1, len(tables)):
            from_table = tables[i - 1]
            to_table = tables[i]

            # Find join relationship
            cursor = self.conn.execute("""
                SELECT from_column, to_column
                FROM table_relationships
                WHERE from_table = ? AND to_table = ?
                LIMIT 1
            """, (from_table, to_table))

            join = cursor.fetchone()

            if join:
                sql += f"\nJOIN {to_table} ON {from_table}.{join[0]} = {to_table}.{join[1]}"
            else:
                logger.warning("no_join_path", from_table=from_table, to_table=to_table)
                # Fallback: try to infer join
                sql += f"\n-- Manual join needed between {from_table} and {to_table}"

        return sql
