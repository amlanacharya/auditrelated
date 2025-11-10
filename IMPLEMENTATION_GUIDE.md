# Implementation Guide - Intelligent Audit Agent

## Phase 0: Foundation ✅ COMPLETE

This guide walks through the complete implementation and usage of the Intelligent Audit Agent.

---

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Or install in development mode:

```bash
pip install -e .
```

### 2. Verify Installation

```bash
python -c "import audit_agent; print('✓ Installation successful')"
```

---

## Quick Start (5 Minutes)

Run the complete demo:

```bash
python examples/quick_start.py
```

This will:
1. Generate 10,000 synthetic expense transactions with violations
2. Ingest data to Parquet format
3. Build Knowledge Graph with process flows and entity relationships
4. Initialize 5 core violation detection rules
5. Execute violation detection in parallel
6. Generate comprehensive reports

**Expected Output:**
- `data/raw/` - CSV files with synthetic data
- `data/parquet/` - Parquet files (partitioned by year/month for expenses)
- `data/kg.db` - SQLite Knowledge Graph database
- `data/violations_report.csv` - Detected violations
- `data/kg_export.json` - Knowledge Graph export
- `data/metrics_report.json` - Performance metrics

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     RAW DATA SOURCES                         │
│           (PostgreSQL, CSV, Excel, APIs)                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │   DATA INGESTION      │
         │   (audit_agent/       │
         │    data_layer/        │
         │    ingest.py)         │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  PARQUET STORAGE      │
         │  - Columnar format    │
         │  - Partitioned        │
         │  - Compressed         │
         └───────────┬───────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌────────────────┐      ┌────────────────────┐
│  DUCKDB ENGINE │      │ KNOWLEDGE GRAPH    │
│  (query_engine)│◄────►│  (SQLite)          │
│                │      │                    │
│  - SQL queries │      │  - Process Graph   │
│  - Parallel    │      │  - Entity Graph    │
│  - Cached      │      │  - Table Graph     │
└────────┬───────┘      │  - Violation Graph │
         │              └────────────────────┘
         │
         ▼
┌────────────────────────┐
│  VIOLATION ENGINE      │
│  (rule_executor)       │
│                        │
│  - Parallel execution  │
│  - Result aggregation  │
│  - Audit trails        │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│  VIOLATIONS REPORT     │
│  - CSV/JSON/Excel      │
│  - Severity ranked     │
│  - Full context        │
└────────────────────────┘
```

---

## Core Components

### 1. Data Layer (`audit_agent/data_layer/`)

**Purpose**: Load data from various sources into Parquet format

#### DataIngestion
```python
from audit_agent.data_layer import DataIngestion

ingestion = DataIngestion(output_base_path="data/parquet")

# Load CSV to Parquet
metadata = ingestion.load_csv_to_parquet(
    csv_path="expenses.csv",
    table_name="expenses",
    date_column="transaction_date",
    partition_cols=["year", "month"]  # Partition for performance
)

# Load from PostgreSQL
metadata = ingestion.load_postgres_to_parquet(
    connection_string="postgresql://user:pass@host/db",
    table_name="expenses",
    date_range=("2024-01-01", "2024-03-31")
)
```

#### QueryEngine
```python
from audit_agent.data_layer import QueryEngine

engine = QueryEngine(parquet_base_path="data/parquet", num_threads=4)

# Register tables
engine.register_parquet_table("expenses")
engine.register_parquet_table("approvals")

# Execute SQL
violations = engine.execute_query("""
    SELECT e.expense_id, e.employee_id, e.amount
    FROM expenses e
    LEFT JOIN approvals a ON e.expense_id = a.expense_id
    WHERE a.approval_id IS NULL
""")
```

#### SchemaExtractor
```python
from audit_agent.data_layer import SchemaExtractor

extractor = SchemaExtractor("data/parquet")

# Extract schema metadata
schema = extractor.extract_schema("expenses")
# Returns: column names, types, nullable, foreign key candidates

# Infer relationships
relationships = extractor.infer_relationships()
# Detects: employee_id → employees, vendor_id → vendors
```

---

### 2. Knowledge Graph (`audit_agent/knowledge_graph/`)

**Purpose**: Store business context for LLM and rule generation

#### Four Graph Components

**Process Graph**: Business workflow definitions
```python
from audit_agent.knowledge_graph import ProcessGraph, KnowledgeGraphManager

kg = KnowledgeGraphManager("data/kg.db")
process_graph = ProcessGraph(kg)

# Define expense reimbursement process
process_id = process_graph.create_process_type(
    process_name="expense_reimbursement",
    description="Employee expense workflow"
)

# Add steps
step1 = process_graph.add_process_step(
    process_type_id=process_id,
    step_name="initiation",
    sequence_order=1,
    required_table="expenses",
    expected_duration_minutes=0
)

step2 = process_graph.add_process_step(
    process_type_id=process_id,
    step_name="approval",
    sequence_order=2,
    required_table="approvals",
    expected_duration_minutes=2880  # 2 days
)

# Define transition
process_graph.add_transition(step1, step2)
```

**Entity Graph**: Hierarchies and approval authorities
```python
from audit_agent.knowledge_graph import EntityGraph
from datetime import date

entity_graph = EntityGraph(kg)

# Add approval authority
entity_graph.add_approval_authority(
    employee_id=123,
    role="Manager",
    max_amount=5000.00,
    effective_from=date(2024, 1, 1),
    effective_to=None  # Current authority
)

# Validate authority
can_approve = entity_graph.validate_approval_authority(
    employee_id=123,
    amount=4500.00,
    transaction_date=date(2024, 3, 15)
)
```

**Table Graph**: Schema mappings and join paths
```python
from audit_agent.knowledge_graph import TableGraph

table_graph = TableGraph(kg)

# Register schema
table_graph.register_table_schema("expenses", schema_metadata)

# Add column mapping
table_graph.add_column_mapping(
    table_name="expenses",
    column_name="emp_id",
    mapped_entity="employee_id",
    data_type="INTEGER",
    is_nullable=False,
    confidence_score=0.95,
    user_confirmed=True
)

# Define relationship
table_graph.add_table_relationship(
    from_table="expenses",
    from_column="employee_id",
    to_table="employees",
    to_column="id",
    confidence="high"
)
```

**Violation Graph**: Rule library with versioning
```python
from audit_agent.knowledge_graph import ViolationGraph

violation_graph = ViolationGraph(kg)

# Create rule
violation_graph.create_rule(
    rule_id="CUSTOM_001",
    rule_name="High-Value Expense Rule",
    description="Expenses over $10K require dual approval",
    severity="high",
    sql_template="""
        SELECT e.expense_id, e.amount, COUNT(a.approver_id) as approver_count
        FROM expenses e
        LEFT JOIN approvals a ON e.expense_id = a.expense_id
        WHERE e.amount > 10000
        GROUP BY e.expense_id, e.amount
        HAVING COUNT(a.approver_id) < 2
    """,
    effective_from=date(2024, 1, 1),
    created_by="compliance_team",
    change_reason="New policy for high-value expenses"
)

# Get active rules
active_rules = violation_graph.get_active_rules(as_of_date=date(2024, 3, 15))
```

---

### 3. Violation Engine (`audit_agent/violation_engine/`)

**Purpose**: Execute violation detection rules

```python
from audit_agent.violation_engine import RuleExecutor

executor = RuleExecutor(
    parquet_path="data/parquet",
    kg_db_path="data/kg.db",
    num_threads=4
)

# Run all active rules in parallel
violations = executor.run_all_rules(parallel=True)

# Get summary
summary = executor.get_violation_summary(violations)
print(f"Total violations: {summary['total_violations']}")
print(f"Financial impact: ${summary['total_financial_impact']:,.2f}")

# Export results
executor.export_violations(violations, "violations.csv", format="csv")
executor.export_violations(violations, "violations.xlsx", format="excel")
```

---

### 4. Observability (`audit_agent/observability/`)

**Purpose**: Structured logging and metrics

```python
from audit_agent.observability import configure_logging, MetricsCollector

# Configure logging
configure_logging(log_level="INFO", log_file="audit.log")

# Collect metrics
metrics = MetricsCollector()

# Record ingestion
metrics.record_table_ingestion(
    table_name="expenses",
    row_count=10000,
    column_count=8,
    duration_seconds=2.5
)

# Record violations
metrics.record_violation_detection(
    rule_name="Self-Approval Detection",
    severity="critical",
    violation_count=50,
    query_duration=0.3
)

# Get reports
data_quality = metrics.get_data_quality_report()
violation_summary = metrics.get_violation_summary()
health = metrics.check_health()
```

---

## The 5 Core Violation Rules

### 1. Self-Approval Detection (Critical)
**Detects**: Employee approves their own expense

```sql
SELECT e.expense_id, e.employee_id as requester_id, e.approver_id, e.amount
FROM expenses e
WHERE e.employee_id = e.approver_id AND e.amount > 0
```

### 2. Duplicate Expense Detection (High)
**Detects**: Same amount, vendor, within 48 hours

```sql
SELECT e1.expense_id, e1.employee_id, e1.amount, e2.expense_id as duplicate_id
FROM expenses e1
JOIN expenses e2
  ON e1.employee_id = e2.employee_id
  AND e1.amount = e2.amount
  AND e1.vendor_id = e2.vendor_id
  AND e1.expense_id < e2.expense_id
  AND ABS(JULIANDAY(e1.transaction_date) - JULIANDAY(e2.transaction_date)) <= 2
```

### 3. Missing Approval Detection (Critical)
**Detects**: Expense paid without approval record

```sql
SELECT e.expense_id, e.employee_id, e.amount
FROM expenses e
LEFT JOIN approvals a ON e.expense_id = a.expense_id
WHERE a.approval_id IS NULL AND e.status = 'paid'
```

### 4. Timeline Violation (High)
**Detects**: Approval after payment

```sql
SELECT e.expense_id, a.approval_date, p.payment_date
FROM expenses e
JOIN approvals a ON e.expense_id = a.expense_id
JOIN payments p ON e.expense_id = p.expense_id
WHERE a.approval_date > p.payment_date
```

### 5. Split Transaction Detection (Medium)
**Detects**: Multiple expenses just below approval threshold

```sql
SELECT e.expense_id, e.employee_id, e.amount, e.transaction_date
FROM expenses e
WHERE e.amount BETWEEN 950 AND 999
  AND (SELECT COUNT(*) FROM expenses e2
       WHERE e2.employee_id = e.employee_id
         AND e2.vendor_id = e.vendor_id
         AND DATE(e2.transaction_date) = DATE(e.transaction_date)
         AND e2.amount BETWEEN 950 AND 999) > 1
```

---

## Performance Optimization

### 1. Partitioning Strategy
```python
# Partition large tables by year/month
ingestion.load_csv_to_parquet(
    csv_path="expenses.csv",
    table_name="expenses",
    date_column="transaction_date",
    partition_cols=["year", "month"]
)
# Query only relevant partitions: WHERE year = 2024 AND month = 3
```

### 2. Parallel Execution
```python
# Run rules in parallel (4 threads)
executor = RuleExecutor(num_threads=4)
violations = executor.run_all_rules(parallel=True)
```

### 3. Query Optimization
```python
# Use EXPLAIN to check query plans
plan = engine.explain_query("SELECT ...")
# Look for: sequential scans, missing indexes
```

---

## Data Quality Monitoring

### Schema Drift Detection
```python
# Compare current schema to previous
current_schema = extractor.extract_schema("expenses")

if current_schema != expected_schema:
    metrics.record_schema_drift("expenses", {
        "expected_columns": expected_schema["columns"],
        "actual_columns": current_schema["columns"]
    })
```

### Referential Integrity Checks
```python
# Detect orphaned records
orphaned_expenses = engine.execute_query("""
    SELECT e.expense_id
    FROM expenses e
    LEFT JOIN employees emp ON e.employee_id = emp.employee_id
    WHERE emp.employee_id IS NULL
""")
```

---

## Advanced Usage

### Custom Violation Rules

Create a rule that adapts to your business logic:

```python
violation_graph.create_rule(
    rule_id="WEEKEND_APPROVAL",
    rule_name="Weekend Approval Detection",
    description="Approvals on weekends should be flagged",
    severity="low",
    sql_template="""
        SELECT a.approval_id, a.expense_id, a.approval_date
        FROM approvals a
        WHERE CAST(strftime('%w', a.approval_date) AS INTEGER) IN (0, 6)
    """,
    effective_from=date.today()
)
```

### Historical Audit Replay

Re-run audits as they would have been on a past date:

```python
# Execute rules as they existed on 2024-01-15
violations = executor.run_all_rules(as_of_date=date(2024, 1, 15))
```

---

## Production Deployment

### 1. PostgreSQL Integration
```python
# Replace CSV with live PostgreSQL
ingestion.load_postgres_to_parquet(
    connection_string=os.getenv("DATABASE_URL"),
    table_name="expenses",
    date_range=(last_run_date, today)
)
```

### 2. Incremental Updates
```python
# Only process new data since last run
last_run = get_last_ingestion_timestamp()
ingestion.load_postgres_to_parquet(
    connection_string=db_url,
    table_name="expenses",
    query=f"SELECT * FROM expenses WHERE created_at > '{last_run}'"
)
```

### 3. Alerting
```python
# Slack webhook for critical violations
if summary["by_severity"].get("critical", 0) > 0:
    send_slack_alert(
        channel="#audit-alerts",
        message=f"🚨 {summary['by_severity']['critical']} critical violations detected"
    )
```

### 4. Scheduled Execution
```bash
# Cron job (daily at 2 AM)
0 2 * * * cd /opt/audit-agent && python examples/quick_start.py
```

---

## Testing

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test
```bash
pytest tests/test_data_layer.py::TestQueryEngine::test_register_and_query -v
```

### Coverage Report
```bash
pytest tests/ --cov=audit_agent --cov-report=html
```

---

## Troubleshooting

### Issue: "No Parquet files found"
**Solution**: Check that ingestion completed successfully
```bash
ls -la data/parquet/*/
```

### Issue: "DuckDB query timeout"
**Solution**: Increase threads or optimize query
```python
engine = QueryEngine(num_threads=8)  # More threads
```

### Issue: "Schema mismatch"
**Solution**: Re-extract schemas after data changes
```python
extractor = SchemaExtractor()
for table in tables:
    schema = extractor.extract_schema(table)
    table_graph.register_table_schema(table, schema)
```

---

## Next Steps

### Phase 1: Core Detection (Weeks 3-4)
- [ ] Add 10 more industry-specific rules
- [ ] Implement false positive feedback loop
- [ ] Build web dashboard for violations

### Phase 2: AI Integration (Weeks 5-6)
- [ ] LLM-based column mapping
- [ ] Natural language explanations for violations
- [ ] RAG system for audit questions

### Phase 3: Production Features (Weeks 7-8)
- [ ] Multi-tenant support
- [ ] Role-based access control
- [ ] Real-time streaming detection

---

## Support

- **Documentation**: See README.md
- **Examples**: Check `examples/` directory
- **Issues**: Report bugs via GitHub Issues
- **Slack**: #audit-agent (internal)

---

## License

MIT License - See LICENSE file
