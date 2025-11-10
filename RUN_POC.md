# 🚀 Run the POC - Quick Start Guide

## Option 1: Interactive Web Interface (Recommended) 🌐

### Launch Streamlit App

```bash
# From the project root
streamlit run streamlit_app/app.py
```

**The app will open automatically in your browser at:** `http://localhost:8501`

### Complete Workflow (2 Minutes)

1. **Upload Data** (30 seconds)
   - Click "Generate Sample Dataset" button
   - Wait for 10,000 expenses + 500 employees to be created
   - Click "Extract Schemas and Build Knowledge Graph"

2. **Define Process** (15 seconds)
   - Select "Use Pre-built Process (Expense Reimbursement)"
   - Click "Use This Process"

3. **Build Rules** (15 seconds)
   - Select "Use Core Rules (Recommended)"
   - Click "Initialize Core Rules"

4. **Run Audit** (30 seconds)
   - Keep parallel execution enabled
   - Click "Run Violation Detection"
   - Watch progress bar

5. **View Results** (Browse as long as you want)
   - Navigate to "Results Dashboard"
   - Explore interactive charts
   - Filter by severity, rule, amount
   - Export violations to CSV/JSON

**Expected Output**: ~400 violations detected across 5 rules

---

## Option 2: Command Line (For Developers) 💻

### Run Python Script

```bash
# From the project root
python examples/quick_start.py
```

**This will**:
- Generate synthetic data
- Ingest to Parquet
- Build Knowledge Graph
- Initialize rules
- Execute violation detection
- Generate reports

**Output Files**:
- `data/violations_report.csv` - All violations
- `data/kg_export.json` - Knowledge Graph
- `data/metrics_report.json` - Performance metrics

**Runtime**: ~30 seconds

---

## Option 3: Interactive Python (Jupyter/IPython) 📓

### Step-by-Step Execution

```python
import sys
sys.path.insert(0, '/path/to/auditrelated')

# 1. Generate data
from audit_agent.synthetic_data import DatasetGenerator

generator = DatasetGenerator(num_employees=500, num_expenses=10000)
stats = generator.generate_dataset("data/raw")
print(f"Generated {stats['expenses']} expenses")

# 2. Ingest to Parquet
from audit_agent.data_layer import DataIngestion

ingestion = DataIngestion()
tables = ["employees", "vendors", "expenses", "approvals", "payments"]

for table in tables:
    metadata = ingestion.load_csv_to_parquet(
        csv_path=f"data/raw/{table}.csv",
        table_name=table
    )
    print(f"✓ {table}: {metadata['row_count']} rows")

# 3. Initialize Knowledge Graph
from audit_agent.knowledge_graph import KnowledgeGraphManager, ViolationGraph

kg = KnowledgeGraphManager("data/kg.db")
vg = ViolationGraph(kg)
vg.initialize_core_rules()
print("✓ Rules initialized")

# 4. Run audit
from audit_agent.violation_engine import RuleExecutor

executor = RuleExecutor()
violations = executor.run_all_rules(parallel=True)
print(f"✓ Detected {len(violations)} violations")

# 5. Analyze results
summary = executor.get_violation_summary(violations)
print(f"\nSummary:")
print(f"  Total violations: {summary['total_violations']}")
print(f"  By severity: {summary['by_severity']}")
print(f"  Financial impact: ${summary.get('total_financial_impact', 0):,.2f}")

# Export
executor.export_violations(violations, "violations.csv", format="csv")
print("\n✓ Results exported to violations.csv")

executor.close()
kg.close()
```

---

## Verification Steps ✅

### 1. Check Data Was Generated

```bash
ls -lh data/raw/
# Should show: employees.csv, vendors.csv, expenses.csv, approvals.csv, payments.csv
```

### 2. Check Parquet Files

```bash
ls -lh data/parquet/*/
# Should show partitioned Parquet files for expenses
```

### 3. Check Knowledge Graph

```bash
sqlite3 data/kg.db "SELECT COUNT(*) FROM violation_rules;"
# Should return: 5 (core rules)
```

### 4. Check Violations

```bash
wc -l data/violations_report.csv
# Should show: ~400 violations (varies with random seed)
```

---

## Performance Expectations 📊

### Dataset Sizes
- **Small POC**: 500 employees, 10K expenses → ~30 seconds
- **Medium**: 1K employees, 50K expenses → ~2 minutes
- **Large**: 5K employees, 250K expenses → ~10 minutes

### System Requirements
- **RAM**: 2GB minimum, 4GB recommended
- **CPU**: 4 cores recommended for parallel execution
- **Disk**: 500MB for POC dataset

---

## Troubleshooting 🔧

### Issue: "Port 8501 already in use"

```bash
# Find and kill existing Streamlit
pkill -f streamlit

# Or use different port
streamlit run streamlit_app/app.py --server.port 8502
```

### Issue: "Module 'audit_agent' not found"

```bash
# Install in development mode
pip install -e .

# Or add to Python path
export PYTHONPATH="${PYTHONPATH}:/path/to/auditrelated"
```

### Issue: "DuckDB query timeout"

```python
# Reduce parallelism
executor = RuleExecutor(num_threads=2)  # Instead of 4
```

### Issue: "Streamlit shows blank page"

```bash
# Clear Streamlit cache
rm -rf ~/.streamlit/

# Restart with cache clearing
streamlit run streamlit_app/app.py --server.runOnSave false
```

---

## Next Steps 🎯

### After Running POC:

1. **Upload Your Own Data**
   - Replace sample data with real expense files
   - Format: CSV with columns matching schema

2. **Create Custom Rules**
   - Navigate to "Build Rules" → "Create Custom Rule"
   - Write SQL queries for your specific violations

3. **Define Custom Process**
   - Navigate to "Define Process" → "Create Custom Process"
   - Model your actual business workflow

4. **Integrate with Production**
   - See `IMPLEMENTATION_GUIDE.md` for PostgreSQL integration
   - Set up scheduled audits (cron jobs)
   - Configure Slack alerts

---

## Demo Video (Simulated Transcript) 🎬

```
[00:00] Opening Streamlit app...
[00:05] Click "Generate Sample Dataset"
[00:15] 10,000 expenses generated with violations
[00:20] Click "Extract Schemas"
[00:25] Knowledge Graph built with 5 tables
[00:30] Navigate to "Define Process"
[00:35] Select "Use Pre-built Process"
[00:40] Expense reimbursement workflow configured
[00:45] Navigate to "Build Rules"
[00:50] Click "Initialize Core Rules"
[00:55] 5 rules activated (self-approval, duplicates, etc.)
[01:00] Navigate to "Run Audit"
[01:05] Click "Run Violation Detection"
[01:10] Progress bar: Initializing... 30%
[01:20] Progress bar: Executing rules... 70%
[01:30] Audit complete! 387 violations detected
[01:35] Navigate to "Results Dashboard"
[01:40] Interactive charts showing:
        - 50 critical violations (self-approvals)
        - 30 high (duplicates)
        - Total exposure: $1.2M
[01:50] Filter by severity: "critical" only
[01:55] Export filtered results to CSV
[02:00] Done! Complete audit workflow in 2 minutes.
```

---

## Share Your Results 📤

### Export for Review

```bash
# All files in data/ directory
zip -r audit_results.zip \
  data/violations_report.csv \
  data/kg_export.json \
  data/metrics_report.json

# Share the ZIP file
```

### Generate Summary Report

```bash
python -c "
import pandas as pd

violations = pd.read_csv('data/violations_report.csv')

print('AUDIT SUMMARY')
print('=' * 50)
print(f'Total Violations: {len(violations)}')
print(f'Critical: {len(violations[violations[\"severity\"] == \"critical\"])}')
print(f'High: {len(violations[violations[\"severity\"] == \"high\"])}')
print(f'Total Amount: ${violations[\"amount\"].sum():,.2f}')
print('\\nTop 5 Rules:')
print(violations['rule_name'].value_counts().head(5))
" > audit_summary.txt

cat audit_summary.txt
```

---

## Questions? 🤔

- **Documentation**: `IMPLEMENTATION_GUIDE.md`
- **Examples**: `examples/` directory
- **Tests**: `pytest tests/`
- **Issues**: Report on GitHub

Happy auditing! 🔍
