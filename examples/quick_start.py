"""
Quick Start: Complete workflow demonstration

This script demonstrates:
1. Generate synthetic POC data
2. Ingest to Parquet
3. Extract schemas and build Knowledge Graph
4. Initialize core violation rules
5. Execute violation detection
6. Generate reports
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from audit_agent.synthetic_data import DatasetGenerator
from audit_agent.data_layer import DataIngestion, QueryEngine, SchemaExtractor
from audit_agent.knowledge_graph import (
    KnowledgeGraphManager,
    ProcessGraph,
    EntityGraph,
    TableGraph,
    ViolationGraph,
)
from audit_agent.violation_engine import RuleExecutor
from audit_agent.observability import configure_logging, MetricsCollector

import pandas as pd


def main():
    """Run complete audit workflow"""

    # Configure logging
    configure_logging(log_level="INFO")
    print("\n" + "=" * 80)
    print("INTELLIGENT AUDIT AGENT - Quick Start Demo")
    print("=" * 80 + "\n")

    # Step 1: Generate synthetic data
    print("Step 1: Generating synthetic dataset...")
    print("-" * 80)

    generator = DatasetGenerator(
        num_employees=500,
        num_expenses=10000,
        start_date="2024-01-01",
        end_date="2024-03-31"
    )

    stats = generator.generate_dataset("data/raw")

    print(f"✓ Generated {stats['employees']} employees")
    print(f"✓ Generated {stats['vendors']} vendors")
    print(f"✓ Generated {stats['expenses']} expenses")
    print(f"✓ Generated {stats['approvals']} approvals")
    print(f"✓ Generated {stats['payments']} payments")
    print(f"\nIntentional violations injected:")
    for violation_type, count in stats['violations_injected'].items():
        print(f"  - {violation_type}: {count}")

    # Step 2: Ingest to Parquet
    print("\n\nStep 2: Ingesting data to Parquet format...")
    print("-" * 80)

    ingestion = DataIngestion(output_base_path="data/parquet")

    tables = ["employees", "vendors", "expenses", "approvals", "payments"]
    for table in tables:
        metadata = ingestion.load_csv_to_parquet(
            csv_path=f"data/raw/{table}.csv",
            table_name=table,
            date_column="transaction_date" if table == "expenses" else None,
            partition_cols=["year", "month"] if table == "expenses" else None
        )
        print(f"✓ {table}: {metadata['row_count']} rows, {metadata['column_count']} columns")

    # Validation
    validation = ingestion.validate_ingestion()
    print(f"\n✓ Ingestion validation: {'PASSED' if validation['validation_passed'] else 'FAILED'}")
    print(f"  Total tables: {validation['total_tables']}")
    print(f"  Total rows: {validation['total_rows']}")

    # Step 3: Extract schemas and build Knowledge Graph
    print("\n\nStep 3: Building Knowledge Graph...")
    print("-" * 80)

    # Initialize KG
    kg_manager = KnowledgeGraphManager("data/kg.db")
    process_graph = ProcessGraph(kg_manager)
    entity_graph = EntityGraph(kg_manager)
    table_graph = TableGraph(kg_manager)
    violation_graph = ViolationGraph(kg_manager)

    # Extract schemas
    schema_extractor = SchemaExtractor("data/parquet")

    for table in tables:
        schema = schema_extractor.extract_schema(table)
        table_graph.register_table_schema(table, schema)
        print(f"✓ Schema extracted: {table} ({schema['column_count']} columns)")

    # Infer relationships
    relationships = schema_extractor.infer_relationships()
    for rel in relationships:
        table_graph.add_table_relationship(
            from_table=rel["from_table"],
            from_column=rel["from_column"],
            to_table=rel["to_table"],
            to_column=rel["to_column"],
            confidence=rel["confidence"]
        )
    print(f"\n✓ Inferred {len(relationships)} table relationships")

    # Define expense reimbursement process
    process_id = process_graph.create_process_type(
        process_name="expense_reimbursement",
        description="Employee expense reimbursement workflow"
    )

    steps = [
        ("initiation", 1, "expenses", 0),
        ("approval", 2, "approvals", 2880),  # 2 days
        ("payment", 3, "payments", 10080),  # 7 days
    ]

    step_ids = []
    for step_name, order, table, duration in steps:
        step_id = process_graph.add_process_step(
            process_type_id=process_id,
            step_name=step_name,
            sequence_order=order,
            required_table=table,
            expected_duration_minutes=duration
        )
        step_ids.append(step_id)

    # Add transitions
    for i in range(len(step_ids) - 1):
        process_graph.add_transition(step_ids[i], step_ids[i + 1])

    print(f"✓ Process flow defined: {len(steps)} steps")

    # Define entity types
    entities = ["employee", "manager", "vendor", "department"]
    for entity in entities:
        entity_graph.create_entity_type(entity, f"{entity.title()} entity")

    entity_graph.add_relationship("employee", "reports_to", "manager")
    entity_graph.add_relationship("employee", "belongs_to", "department")

    print(f"✓ Entity types defined: {len(entities)}")

    # Step 4: Initialize core violation rules
    print("\n\nStep 4: Initializing violation detection rules...")
    print("-" * 80)

    violation_graph.initialize_core_rules()

    active_rules = violation_graph.get_active_rules()
    print(f"✓ Initialized {len(active_rules)} violation rules:")
    for rule in active_rules:
        print(f"  - {rule['rule_name']} [{rule['severity']}]")

    # Export KG for inspection
    kg_manager.export_to_json("data/kg_export.json")
    print(f"\n✓ Knowledge Graph exported to data/kg_export.json")

    # Step 5: Execute violation detection
    print("\n\nStep 5: Running violation detection...")
    print("-" * 80)

    executor = RuleExecutor(
        parquet_path="data/parquet",
        kg_db_path="data/kg.db",
        num_threads=4
    )

    # Run all rules in parallel
    violations = executor.run_all_rules(parallel=True)

    if not violations.empty:
        print(f"\n✓ Detected {len(violations)} violations")

        # Get summary
        summary = executor.get_violation_summary(violations)
        print(f"\nViolation Summary:")
        print(f"  Total violations: {summary['total_violations']}")
        print(f"  Unique expenses affected: {summary['unique_expenses']}")
        if "total_financial_impact" in summary:
            print(f"  Total financial impact: ${summary['total_financial_impact']:,.2f}")

        print(f"\nBy Severity:")
        for severity, count in summary['by_severity'].items():
            print(f"  - {severity}: {count}")

        print(f"\nBy Rule:")
        for rule, count in summary['by_rule'].items():
            print(f"  - {rule}: {count}")

        # Export violations
        executor.export_violations(violations, "data/violations_report.csv", format="csv")
        print(f"\n✓ Violations exported to data/violations_report.csv")

        # Show sample violations
        print(f"\nSample Violations (Top 5 by amount):")
        print("-" * 80)
        sample = violations.head(5)[
            ["expense_id", "rule_name", "severity", "amount", "violation_reason"]
        ] if "amount" in violations.columns else violations.head(5)
        print(sample.to_string(index=False))

    else:
        print("✓ No violations detected")

    # Step 6: Generate metrics report
    print("\n\nStep 6: Generating metrics report...")
    print("-" * 80)

    metrics = executor.metrics

    # Performance summary
    perf_summary = metrics.get_performance_summary()
    if perf_summary:
        print(f"Performance Metrics:")
        print(f"  Total queries: {perf_summary['total_queries']}")
        print(f"  Average duration: {perf_summary['avg_duration']:.3f}s")
        print(f"  Max duration: {perf_summary['max_duration']:.3f}s")

    # Violation summary
    violation_summary = metrics.get_violation_summary()
    if not violation_summary.empty:
        print(f"\nViolation Detection Metrics:")
        print(violation_summary.to_string(index=False))

    # Health check
    health = metrics.check_health()
    print(f"\nSystem Health: {health['status'].upper()}")
    for check in health['checks']:
        print(f"  - {check['check']}: {check['message']}")

    # Export metrics
    metrics.export_metrics("data/metrics_report.json")
    print(f"\n✓ Metrics exported to data/metrics_report.json")

    # Cleanup
    executor.close()

    print("\n" + "=" * 80)
    print("Demo completed successfully!")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Review violations in: data/violations_report.csv")
    print("  2. Inspect Knowledge Graph: data/kg_export.json")
    print("  3. Analyze metrics: data/metrics_report.json")
    print("  4. Explore KG database: data/kg.db (use SQLite browser)")
    print("\n")


if __name__ == "__main__":
    main()
