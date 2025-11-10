"""
Violation Pattern Graph: Reusable rule library

Manages:
- Violation rule definitions with SQL templates
- Rule versioning and effective dates
- Rule dependencies
"""

from typing import Dict, List, Optional
from datetime import date, datetime
import structlog

logger = structlog.get_logger()


class ViolationGraph:
    """Manages violation detection rules"""

    def __init__(self, kg_manager):
        """
        Initialize ViolationGraph

        Args:
            kg_manager: KnowledgeGraphManager instance
        """
        self.kg = kg_manager
        self.conn = kg_manager.conn

    def create_rule(
        self,
        rule_id: str,
        rule_name: str,
        description: str,
        severity: str,
        sql_template: str,
        effective_from: date,
        created_by: str = "system",
        change_reason: Optional[str] = None
    ) -> int:
        """
        Create a new violation rule

        Args:
            rule_id: Unique rule identifier (stable across versions)
            rule_name: Human-readable rule name
            description: Detailed description
            severity: critical, high, medium, or low
            sql_template: SQL query template for detection
            effective_from: Date rule becomes active
            created_by: User/system creating the rule
            change_reason: Why this rule was created/changed

        Returns:
            Database ID of the rule
        """
        # Check if rule_id exists (versioning)
        cursor = self.conn.execute("""
            SELECT MAX(version) FROM violation_rules WHERE rule_id = ?
        """, (rule_id,))

        max_version = cursor.fetchone()[0]
        version = (max_version or 0) + 1

        # Deactivate previous version
        if max_version:
            self.conn.execute("""
                UPDATE violation_rules
                SET is_active = 0, effective_to = ?
                WHERE rule_id = ? AND version = ?
            """, (effective_from, rule_id, max_version))

        # Insert new version
        cursor = self.conn.execute("""
            INSERT INTO violation_rules
            (rule_id, rule_name, description, severity, sql_template,
             version, effective_from, created_by, change_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (rule_id, rule_name, description, severity, sql_template,
              version, effective_from, created_by, change_reason))

        self.conn.commit()

        db_id = cursor.lastrowid

        self.kg.log_action("create", "violation_rule", db_id, user_id=created_by, details={
            "rule_id": rule_id,
            "version": version,
            "severity": severity
        })

        logger.info("violation_rule_created",
                    rule_id=rule_id,
                    version=version,
                    severity=severity)

        return db_id

    def get_active_rules(self, as_of_date: Optional[date] = None) -> List[Dict]:
        """
        Get all active rules for a specific date

        Args:
            as_of_date: Date to check (default: today)

        Returns:
            List of active rules
        """
        if as_of_date is None:
            as_of_date = date.today()

        cursor = self.conn.execute("""
            SELECT rule_id, rule_name, description, severity, sql_template, version
            FROM violation_rules
            WHERE effective_from <= ?
              AND (effective_to IS NULL OR effective_to >= ?)
              AND is_active = 1
            ORDER BY severity DESC, rule_name
        """, (as_of_date, as_of_date))

        return [dict(row) for row in cursor.fetchall()]

    def get_rule_by_id(self, rule_id: str, version: Optional[int] = None) -> Optional[Dict]:
        """
        Get a specific rule version

        Args:
            rule_id: Rule identifier
            version: Optional version number (default: latest active)

        Returns:
            Rule dict or None
        """
        if version:
            cursor = self.conn.execute("""
                SELECT rule_id, rule_name, description, severity, sql_template,
                       version, effective_from, effective_to
                FROM violation_rules
                WHERE rule_id = ? AND version = ?
            """, (rule_id, version))
        else:
            cursor = self.conn.execute("""
                SELECT rule_id, rule_name, description, severity, sql_template,
                       version, effective_from, effective_to
                FROM violation_rules
                WHERE rule_id = ? AND is_active = 1
                ORDER BY version DESC
                LIMIT 1
            """, (rule_id,))

        row = cursor.fetchone()

        if row:
            return dict(row)

        return None

    def add_rule_dependency(self, rule_id: str, depends_on_rule_id: str):
        """
        Define that one rule depends on another (execution order)

        Args:
            rule_id: Rule that has dependency
            depends_on_rule_id: Rule that must execute first
        """
        self.conn.execute("""
            INSERT INTO rule_dependencies (rule_id, depends_on_rule_id)
            VALUES (?, ?)
        """, (rule_id, depends_on_rule_id))

        self.conn.commit()

        logger.info("rule_dependency_added", rule=rule_id, depends_on=depends_on_rule_id)

    def get_execution_order(self) -> List[str]:
        """
        Get rule execution order respecting dependencies

        Returns:
            Ordered list of rule IDs
        """
        # Get all active rules
        active_rules = self.get_active_rules()
        rule_ids = [r['rule_id'] for r in active_rules]

        # Get dependencies
        cursor = self.conn.execute("""
            SELECT rule_id, depends_on_rule_id
            FROM rule_dependencies
            WHERE rule_id IN ({})
        """.format(','.join('?' * len(rule_ids))), rule_ids)

        dependencies = {}
        for row in cursor.fetchall():
            rule_id = row[0]
            depends_on = row[1]
            if rule_id not in dependencies:
                dependencies[rule_id] = []
            dependencies[rule_id].append(depends_on)

        # Topological sort
        ordered = []
        visited = set()

        def visit(rule_id):
            if rule_id in visited:
                return
            visited.add(rule_id)

            # Visit dependencies first
            if rule_id in dependencies:
                for dep in dependencies[rule_id]:
                    visit(dep)

            ordered.append(rule_id)

        for rule_id in rule_ids:
            visit(rule_id)

        return ordered

    def initialize_core_rules(self):
        """Initialize the 5 core violation rules for POC"""

        today = date.today()

        # Rule 1: Self-Approval
        self.create_rule(
            rule_id="R001",
            rule_name="Self-Approval Detection",
            description="Detects when an employee approves their own expense",
            severity="critical",
            sql_template="""
                SELECT
                    e.expense_id,
                    e.employee_id as requester_id,
                    e.approver_id,
                    e.amount,
                    e.transaction_date,
                    'Self-approval violation' as violation_reason
                FROM expenses e
                WHERE e.employee_id = e.approver_id
                  AND e.amount > 0
            """,
            effective_from=today,
            change_reason="Initial core rule"
        )

        # Rule 2: Duplicate Expenses
        self.create_rule(
            rule_id="R002",
            rule_name="Duplicate Expense Detection",
            description="Detects duplicate expenses (same amount, vendor, within 48 hours)",
            severity="high",
            sql_template="""
                SELECT
                    e1.expense_id,
                    e1.employee_id,
                    e1.amount,
                    e1.vendor_id,
                    e1.transaction_date,
                    e2.expense_id as duplicate_expense_id,
                    'Potential duplicate expense' as violation_reason
                FROM expenses e1
                JOIN expenses e2
                  ON e1.employee_id = e2.employee_id
                  AND e1.amount = e2.amount
                  AND e1.vendor_id = e2.vendor_id
                  AND e1.expense_id < e2.expense_id
                  AND ABS(JULIANDAY(e1.transaction_date) - JULIANDAY(e2.transaction_date)) <= 2
            """,
            effective_from=today,
            change_reason="Initial core rule"
        )

        # Rule 3: Missing Approval
        self.create_rule(
            rule_id="R003",
            rule_name="Missing Approval Detection",
            description="Detects expenses that were paid without approval record",
            severity="critical",
            sql_template="""
                SELECT
                    e.expense_id,
                    e.employee_id,
                    e.amount,
                    e.transaction_date,
                    'No approval record found' as violation_reason
                FROM expenses e
                LEFT JOIN approvals a ON e.expense_id = a.expense_id
                WHERE a.approval_id IS NULL
                  AND e.status = 'paid'
            """,
            effective_from=today,
            change_reason="Initial core rule"
        )

        # Rule 4: Timeline Violation
        self.create_rule(
            rule_id="R004",
            rule_name="Approval After Payment Detection",
            description="Detects approvals that occurred after payment was made",
            severity="high",
            sql_template="""
                SELECT
                    e.expense_id,
                    e.employee_id,
                    a.approval_date,
                    p.payment_date,
                    'Approval after payment' as violation_reason
                FROM expenses e
                JOIN approvals a ON e.expense_id = a.expense_id
                JOIN payments p ON e.expense_id = p.expense_id
                WHERE a.approval_date > p.payment_date
            """,
            effective_from=today,
            change_reason="Initial core rule"
        )

        # Rule 5: Split Transaction (Just Below Threshold)
        self.create_rule(
            rule_id="R005",
            rule_name="Split Transaction Detection",
            description="Detects potential split transactions just below approval threshold",
            severity="medium",
            sql_template="""
                SELECT
                    e.expense_id,
                    e.employee_id,
                    e.amount,
                    e.transaction_date,
                    COUNT(*) OVER (
                        PARTITION BY e.employee_id, e.vendor_id, DATE(e.transaction_date)
                    ) as same_day_count,
                    'Multiple transactions just below threshold' as violation_reason
                FROM expenses e
                WHERE e.amount BETWEEN 950 AND 999
                  AND (SELECT COUNT(*)
                       FROM expenses e2
                       WHERE e2.employee_id = e.employee_id
                         AND e2.vendor_id = e.vendor_id
                         AND DATE(e2.transaction_date) = DATE(e.transaction_date)
                         AND e2.amount BETWEEN 950 AND 999) > 1
            """,
            effective_from=today,
            change_reason="Initial core rule"
        )

        logger.info("core_rules_initialized", count=5)
