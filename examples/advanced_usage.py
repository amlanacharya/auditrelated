"""
Advanced Usage Examples

Demonstrates:
- Custom violation rules
- Time-based queries
- Manual process validation
- Approval authority checking
"""

import sys
from pathlib import Path
from datetime import date, datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from audit_agent.knowledge_graph import KnowledgeGraphManager, ViolationGraph, EntityGraph
from audit_agent.violation_engine import RuleExecutor


def example_1_custom_rule():
    """Create and execute a custom violation rule"""

    print("\n" + "=" * 80)
    print("Example 1: Custom Violation Rule")
    print("=" * 80)

    kg_manager = KnowledgeGraphManager("data/kg.db")
    violation_graph = ViolationGraph(kg_manager)

    # Create a custom rule: Expenses over $500 without itemized receipt
    violation_graph.create_rule(
        rule_id="R999",
        rule_name="Missing Itemized Receipt",
        description="Expenses over $500 should have itemized receipts",
        severity="medium",
        sql_template="""
            SELECT
                e.expense_id,
                e.employee_id,
                e.amount,
                e.transaction_date,
                'High-value expense without itemized receipt' as violation_reason
            FROM expenses e
            WHERE e.amount > 500
              AND (e.description NOT LIKE '%itemized%' OR e.description IS NULL)
        """,
        effective_from=date.today(),
        created_by="admin",
        change_reason="New policy for high-value expenses"
    )

    print("✓ Custom rule created: Missing Itemized Receipt")

    # Execute the rule
    executor = RuleExecutor(kg_db_path="data/kg.db")
    violations = executor.run_single_rule("R999")

    print(f"✓ Detected {len(violations)} violations")

    executor.close()
    kg_manager.close()


def example_2_approval_authority_check():
    """Check approval authorities for specific scenarios"""

    print("\n" + "=" * 80)
    print("Example 2: Approval Authority Validation")
    print("=" * 80)

    kg_manager = KnowledgeGraphManager("data/kg.db")
    entity_graph = EntityGraph(kg_manager)

    # Add approval authority for employee
    authority_id = entity_graph.add_approval_authority(
        employee_id=100,
        role="Manager",
        max_amount=5000.00,
        effective_from=date(2024, 1, 1),
        effective_to=None  # No end date
    )

    print(f"✓ Added approval authority: ID {authority_id}")

    # Check if employee 100 can approve $4500 on 2024-03-15
    can_approve = entity_graph.validate_approval_authority(
        employee_id=100,
        amount=4500.00,
        transaction_date=date(2024, 3, 15)
    )

    print(f"✓ Employee 100 can approve $4,500: {can_approve}")

    # Check if employee 100 can approve $6000 (should fail)
    can_approve_high = entity_graph.validate_approval_authority(
        employee_id=100,
        amount=6000.00,
        transaction_date=date(2024, 3, 15)
    )

    print(f"✓ Employee 100 can approve $6,000: {can_approve_high}")

    kg_manager.close()


def example_3_query_performance_analysis():
    """Analyze query performance"""

    print("\n" + "=" * 80)
    print("Example 3: Query Performance Analysis")
    print("=" * 80)

    executor = RuleExecutor()

    # Get performance summary
    perf_summary = executor.query_engine.get_query_performance_summary()

    if not perf_summary.empty:
        print("\nQuery Performance by Rule:")
        print(perf_summary)
    else:
        print("No query performance data available")

    executor.close()


def example_4_historical_rule_execution():
    """Execute rules as they existed on a historical date"""

    print("\n" + "=" * 80)
    print("Example 4: Historical Rule Execution")
    print("=" * 80)

    # Execute rules as they were on January 1, 2024
    executor = RuleExecutor()

    historical_date = date(2024, 1, 15)
    violations = executor.run_all_rules(as_of_date=historical_date)

    print(f"✓ Executed rules effective on {historical_date}")
    print(f"✓ Detected {len(violations)} violations")

    executor.close()


if __name__ == "__main__":
    # First, ensure data exists by running quick_start.py
    if not Path("data/kg.db").exists():
        print("Error: Please run examples/quick_start.py first to generate data")
        sys.exit(1)

    example_1_custom_rule()
    example_2_approval_authority_check()
    example_3_query_performance_analysis()
    example_4_historical_rule_execution()

    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80 + "\n")
