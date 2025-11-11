"""
Process Graph: Business workflow definitions

Manages process flows like:
Expense Reimbursement: Initiation → Approval → Execution → Reconciliation
"""

from typing import Dict, List, Optional
import structlog

logger = structlog.get_logger()


class ProcessGraph:
    """Manages process workflow definitions"""

    def __init__(self, kg_manager):
        """
        Initialize ProcessGraph

        Args:
            kg_manager: KnowledgeGraphManager instance
        """
        self.kg = kg_manager
        self.conn = kg_manager.conn

    def get_process_by_name(self, process_name: str) -> Optional[int]:
        """
        Get process ID by name if it exists

        Args:
            process_name: Name of the process

        Returns:
            Process ID if exists, None otherwise
        """
        cursor = self.conn.execute("""
            SELECT id FROM process_types WHERE process_name = ?
        """, (process_name,))

        result = cursor.fetchone()
        return result[0] if result else None

    def create_process_type(self, process_name: str, description: str) -> int:
        """
        Create a new process type

        Args:
            process_name: Name of the process (e.g., 'expense_reimbursement')
            description: Human-readable description

        Returns:
            Process type ID
        """
        cursor = self.conn.execute("""
            INSERT INTO process_types (process_name, description)
            VALUES (?, ?)
        """, (process_name, description))

        self.conn.commit()
        process_id = cursor.lastrowid

        self.kg.log_action("create", "process_type", process_id, details={
            "process_name": process_name
        })

        logger.info("process_type_created", name=process_name, id=process_id)

        return process_id

    def get_or_create_process_type(self, process_name: str, description: str) -> int:
        """
        Get existing process or create if it doesn't exist

        Args:
            process_name: Name of the process
            description: Description (used only if creating)

        Returns:
            Process type ID
        """
        existing_id = self.get_process_by_name(process_name)
        if existing_id:
            logger.info("process_type_exists", name=process_name, id=existing_id)
            return existing_id

        return self.create_process_type(process_name, description)

    def add_process_step(
        self,
        process_type_id: int,
        step_name: str,
        sequence_order: int,
        required_table: Optional[str] = None,
        expected_duration_minutes: Optional[int] = None
    ) -> int:
        """
        Add a step to a process

        Args:
            process_type_id: ID of the process type
            step_name: Name of the step (e.g., 'approval')
            sequence_order: Order in the workflow (1, 2, 3...)
            required_table: Table that tracks this step
            expected_duration_minutes: Expected time to complete step

        Returns:
            Step ID
        """
        cursor = self.conn.execute("""
            INSERT INTO process_steps
            (process_type_id, step_name, sequence_order, required_table, expected_duration_minutes)
            VALUES (?, ?, ?, ?, ?)
        """, (process_type_id, step_name, sequence_order, required_table, expected_duration_minutes))

        self.conn.commit()
        step_id = cursor.lastrowid

        logger.info("process_step_added", step_name=step_name, id=step_id)

        return step_id

    def add_transition(
        self,
        from_step_id: int,
        to_step_id: int,
        condition: Optional[Dict] = None
    ):
        """
        Define a transition between steps

        Args:
            from_step_id: Source step ID
            to_step_id: Target step ID
            condition: Optional conditions (e.g., {"amount_threshold": 1000})
        """
        import json

        self.conn.execute("""
            INSERT INTO process_transitions (from_step_id, to_step_id, condition_json)
            VALUES (?, ?, ?)
        """, (from_step_id, to_step_id, json.dumps(condition) if condition else None))

        self.conn.commit()

        logger.info("transition_added", from_step=from_step_id, to_step=to_step_id)

    def get_process_flow(self, process_name: str) -> Dict:
        """
        Get complete workflow for a process

        Args:
            process_name: Name of the process

        Returns:
            Dict with process steps and transitions
        """
        # Get process type
        cursor = self.conn.execute("""
            SELECT id, process_name, description
            FROM process_types
            WHERE process_name = ?
        """, (process_name,))

        process = cursor.fetchone()
        if not process:
            return {}

        process_id = process[0]

        # Get steps
        cursor = self.conn.execute("""
            SELECT id, step_name, sequence_order, required_table, expected_duration_minutes
            FROM process_steps
            WHERE process_type_id = ?
            ORDER BY sequence_order
        """, (process_id,))

        steps = [dict(row) for row in cursor.fetchall()]

        # Get transitions
        cursor = self.conn.execute("""
            SELECT from_step_id, to_step_id, condition_json
            FROM process_transitions
            WHERE from_step_id IN (SELECT id FROM process_steps WHERE process_type_id = ?)
        """, (process_id,))

        transitions = [dict(row) for row in cursor.fetchall()]

        return {
            "process_name": process[1],
            "description": process[2],
            "steps": steps,
            "transitions": transitions
        }

    def validate_process_execution(
        self,
        process_name: str,
        execution_data: Dict
    ) -> List[str]:
        """
        Validate that an execution followed the correct process flow

        Args:
            process_name: Name of the process
            execution_data: Dict with step completion timestamps/data

        Returns:
            List of violations (empty if valid)
        """
        flow = self.get_process_flow(process_name)
        violations = []

        # Check that all required steps exist
        required_steps = {step['step_name'] for step in flow['steps']}
        executed_steps = set(execution_data.keys())

        missing_steps = required_steps - executed_steps
        if missing_steps:
            violations.append(f"Missing steps: {missing_steps}")

        # Check sequence order (timestamps should be sequential)
        # TODO: Implement timestamp validation

        return violations
