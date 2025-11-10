# Intelligent Audit Agent

**90% Deterministic SQL + 10% AI** for compliance-grade business process violation detection.

## Architecture Overview

```
Raw Data → Parquet Storage → DuckDB Queries → Violation Detection
                          ↓
                   Knowledge Graphs (SQLite)
                          ↓
                   LLM Context (RAG)
```

## Core Components

### 1. Data Layer
- **Parquet Storage**: Columnar format for fast analytical queries
- **DuckDB Engine**: SQL queries directly on Parquet files
- **Schema Extraction**: Automatic metadata extraction and validation

### 2. Knowledge Graphs (SQLite)
- **Process Graph**: Business workflow definitions (A→B→C→D)
- **Entity Relationship Graph**: Employee hierarchies, approval limits
- **Table Relationship Graph**: Schema mappings, join keys
- **Violation Pattern Graph**: Reusable rule library

### 3. Violation Engine
- **SQL-Based Rules**: Deterministic, auditable detection
- **Parallel Execution**: Multi-threaded rule processing
- **Severity Scoring**: Critical → High → Medium → Low

### 4. Observability
- **Structured Logging**: Full audit trail
- **Performance Metrics**: Query times, detection rates
- **Data Quality Monitoring**: Completeness, consistency checks

## Quick Start

```python
from audit_agent.synthetic_data import DatasetGenerator
from audit_agent.data_layer import DataIngestion
from audit_agent.violation_engine import RuleExecutor

# Generate POC dataset
generator = DatasetGenerator(num_employees=500, num_expenses=10000)
generator.generate_dataset("data/raw/")

# Ingest to Parquet
ingestion = DataIngestion()
ingestion.load_to_parquet("data/raw/", "data/parquet/")

# Run violation detection
executor = RuleExecutor()
violations = executor.run_all_rules("data/parquet/")
print(f"Detected {len(violations)} violations")
```

## Phase 0 Goals (Foundation)

- [x] Project structure
- [ ] Parquet + DuckDB pipeline
- [ ] SQLite Knowledge Graph storage
- [ ] Synthetic dataset generator (10K expenses, 500 employees)
- [ ] Observability framework

## Next Phases

- **Phase 1**: Core detection (5 violation rules)
- **Phase 2**: AI integration (column mapping, NL explanations)
- **Phase 3**: Production features (multi-tenant, rule versioning)

## Design Principles

1. **Auditable**: Every detection has full SQL + data lineage
2. **Deterministic**: No AI hallucinations on violations
3. **Scalable**: 100M+ rows without Spark
4. **Minimal KG**: Just enough context for LLM, not full graph DB

## License

MIT
