"""
Entity Relationship Graph: Business entities and their relationships

Manages:
- Entity types (employee, manager, vendor, department)
- Hierarchies (employee → reports_to → manager)
- Approval authorities with temporal validity
"""

from typing import Dict, List, Optional
from datetime import date
import structlog

logger = structlog.get_logger()


class EntityGraph:
    """Manages entity relationships"""

    def __init__(self, kg_manager):
        """
        Initialize EntityGraph

        Args:
            kg_manager: KnowledgeGraphManager instance
        """
        self.kg = kg_manager
        self.conn = kg_manager.conn

    def create_entity_type(self, entity_name: str, description: str):
        """
        Register a new entity type

        Args:
            entity_name: Name of entity (e.g., 'employee', 'vendor')
            description: Description
        """
        self.conn.execute("""
            INSERT OR IGNORE INTO entity_types (entity_name, description)
            VALUES (?, ?)
        """, (entity_name, description))

        self.conn.commit()

        logger.info("entity_type_created", entity=entity_name)

    def add_relationship(
        self,
        from_entity: str,
        relationship_type: str,
        to_entity: str,
        properties: Optional[Dict] = None
    ):
        """
        Define a relationship between entity types

        Args:
            from_entity: Source entity type
            relationship_type: Type of relationship (e.g., 'reports_to', 'approves_for')
            to_entity: Target entity type
            properties: Optional additional properties
        """
        import json

        self.conn.execute("""
            INSERT OR REPLACE INTO entity_relationships
            (from_entity_type, relationship_type, to_entity_type, properties_json)
            VALUES (?, ?, ?, ?)
        """, (from_entity, relationship_type, to_entity, json.dumps(properties) if properties else None))

        self.conn.commit()

        logger.info("relationship_added",
                    from_entity=from_entity,
                    relationship=relationship_type,
                    to_entity=to_entity)

    def add_approval_authority(
        self,
        employee_id: int,
        role: str,
        max_amount: float,
        effective_from: date,
        effective_to: Optional[date] = None,
        delegation_from_employee_id: Optional[int] = None
    ) -> int:
        """
        Add approval authority for an employee

        Args:
            employee_id: Employee ID
            role: Role name (e.g., 'manager', 'director')
            max_amount: Maximum amount they can approve
            effective_from: Start date of authority
            effective_to: Optional end date
            delegation_from_employee_id: If delegated, original employee ID

        Returns:
            Authority record ID
        """
        cursor = self.conn.execute("""
            INSERT INTO approval_authorities
            (employee_id, role, max_amount, effective_from, effective_to, delegation_from_employee_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (employee_id, role, max_amount, effective_from, effective_to, delegation_from_employee_id))

        self.conn.commit()

        logger.info("approval_authority_added",
                    employee_id=employee_id,
                    role=role,
                    max_amount=max_amount)

        return cursor.lastrowid

    def get_approval_authority(
        self,
        employee_id: int,
        as_of_date: date
    ) -> Optional[Dict]:
        """
        Get approval authority for an employee on a specific date

        Args:
            employee_id: Employee ID
            as_of_date: Date to check authority

        Returns:
            Dict with authority info or None
        """
        cursor = self.conn.execute("""
            SELECT employee_id, role, max_amount, delegation_from_employee_id
            FROM approval_authorities
            WHERE employee_id = ?
              AND effective_from <= ?
              AND (effective_to IS NULL OR effective_to >= ?)
        """, (employee_id, as_of_date, as_of_date))

        row = cursor.fetchone()

        if row:
            return dict(row)

        return None

    def get_entity_relationships(self, entity_type: Optional[str] = None) -> List[Dict]:
        """
        Get all relationships for an entity type

        Args:
            entity_type: Optional filter by entity type

        Returns:
            List of relationships
        """
        if entity_type:
            cursor = self.conn.execute("""
                SELECT from_entity_type, relationship_type, to_entity_type, properties_json
                FROM entity_relationships
                WHERE from_entity_type = ? OR to_entity_type = ?
            """, (entity_type, entity_type))
        else:
            cursor = self.conn.execute("""
                SELECT from_entity_type, relationship_type, to_entity_type, properties_json
                FROM entity_relationships
            """)

        return [dict(row) for row in cursor.fetchall()]

    def validate_approval_authority(
        self,
        employee_id: int,
        amount: float,
        transaction_date: date
    ) -> bool:
        """
        Check if employee had authority to approve an amount on a date

        Args:
            employee_id: Employee ID
            amount: Amount to approve
            transaction_date: Date of transaction

        Returns:
            True if authorized, False otherwise
        """
        authority = self.get_approval_authority(employee_id, transaction_date)

        if not authority:
            logger.warning("no_approval_authority", employee_id=employee_id, date=transaction_date)
            return False

        if amount > authority['max_amount']:
            logger.warning("amount_exceeds_authority",
                          employee_id=employee_id,
                          amount=amount,
                          max_amount=authority['max_amount'])
            return False

        return True
