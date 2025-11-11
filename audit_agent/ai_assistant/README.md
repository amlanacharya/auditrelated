# AI Assistant Module

Intelligent audit workflow suggestions powered by statistical analysis and machine learning.

## Overview

The AI Assistant helps auditors overcome blind spots and biases by:
- **Analyzing data** for statistical anomalies (Benford's Law, outliers, clustering)
- **Detecting patterns** that humans might miss (weekend activity, threshold gaming)
- **Suggesting workflows** based on industry best practices
- **Recommending rules** tailored to your specific data
- **Matching templates** from a library of proven audit workflows

## Components

### 1. Data Analyzer (`analyzer.py`)

Statistical analysis engine that detects:

**Statistical Anomalies:**
- Benford's Law violations (fabricated numbers)
- Excessive round numbers
- Threshold gaming (transactions just below limits)
- Outlier detection

**Temporal Patterns:**
- Weekend activity spikes
- End-of-period manipulation
- Unusual timing patterns

**Behavioral Patterns:**
- Employee outliers (unusual spending)
- Self-approval violations
- Behavioral clustering

**Schema Issues:**
- Missing critical columns
- Data quality problems

### 2. Suggestion Engine (`suggestions.py`)

Converts findings into actionable recommendations:

**Suggestion Types:**
- `data_issue`: Schema or compliance problems
- `pattern`: Detected anomalies requiring rules
- `missing_step`: Workflow gaps
- `new_rule`: Recommended detection rules
- `template`: Pre-built workflow matches

**Priority Levels:**
- `critical`: Immediate action required (e.g., self-approvals)
- `high`: Significant risk (e.g., threshold gaming)
- `medium`: Best practice improvements
- `low`: Optional enhancements

### 3. Template Library (`templates.py`)

Pre-built industry-standard workflows:

**Available Templates:**
1. **Corporate Expense Reimbursement (SOX Compliant)** - Full 6-step workflow with 7 rules
2. **Small Business Expense Review** - Simplified 3-step workflow
3. **Travel & Entertainment Audit** - T&E-specific with per diem checks

**Template Matching:**
- Analyzes uploaded data characteristics
- Calculates match confidence score
- Recommends best-fit template

## Usage

### Basic Data Analysis

```python
from audit_agent.ai_assistant import DataAnalyzer
import pandas as pd

# Initialize analyzer
analyzer = DataAnalyzer()

# Analyze expenses
expenses_df = pd.read_parquet('data/parquet/expenses')
anomalies = analyzer.analyze(expenses_df, 'expenses')

# Review findings
for anomaly in anomalies:
    print(f"{anomaly.severity}: {anomaly.title}")
    print(f"Evidence: {anomaly.evidence}")
    print(f"Suggested action: {anomaly.suggested_action}")
```

### Generate Suggestions

```python
from audit_agent.ai_assistant import SuggestionEngine

# Initialize engine
engine = SuggestionEngine()

# Convert anomalies to suggestions
suggestions = engine.generate_from_anomalies(anomalies)

# Group by priority
grouped = engine.get_suggestions_by_priority()
print(f"Critical: {len(grouped['critical'])}")
print(f"High: {len(grouped['high'])}")
```

### Match Templates

```python
from audit_agent.ai_assistant import TemplateLibrary

# Initialize library
templates = TemplateLibrary()

# Find best match
data_context = {
    'tables': ['expenses', 'employees', 'approvals'],
    'columns': ['expense_id', 'amount', 'transaction_date'],
    'row_count': 10000
}

best_match = templates.match_template(data_context)
print(f"Best match: {best_match.name} ({best_match.match_confidence * 100:.0f}%)")
```

## Detection Algorithms

### Benford's Law

Natural datasets follow Benford's distribution where ~30% of numbers start with 1, ~17.6% start with 2, etc.

```python
# Expected distribution
benford = {1: 0.301, 2: 0.176, 3: 0.125, ...}

# Chi-square test
chi2, p_value = stats.chisquare(observed, expected)

# If p_value < 0.05, distribution is anomalous
```

### Threshold Gaming Detection

Detects transactions clustered just below approval thresholds:

```python
# For each threshold (e.g., $1000)
just_below = df[(df['amount'] >= threshold - 50) & (df['amount'] < threshold)]

# If >60% of transactions in ±$50 window are below threshold
# → Flag as potential splitting/structuring
```

### Behavioral Clustering

Uses DBSCAN to find employee outliers:

```python
from sklearn.cluster import DBSCAN

# Aggregate employee spending patterns
features = df.groupby('employee_id').agg({
    'amount': ['mean', 'std', 'count'],
    'vendor_id': 'nunique'
})

# Cluster
clusters = DBSCAN(eps=0.5).fit(features)

# Small/isolated clusters = unusual behavior
```

## Streamlit Integration

The AI Assistant is integrated into the POC via `streamlit_app/pages/6_🤖_AI_Assistant.py`:

**Tab 1: Data Analysis**
- Run comprehensive analysis
- View findings by priority
- Accept/dismiss suggestions
- Create rules automatically

**Tab 2: Workflow Suggestions**
- Detect missing workflow steps
- Recommend conditional logic
- Compare to best practices

**Tab 3: Templates**
- Browse template library
- Auto-match to your data
- One-click apply

## Extending the System

### Add New Detection Algorithm

```python
# In analyzer.py

def analyze_custom_pattern(self, df: pd.DataFrame):
    """Your custom detection logic"""
    if some_condition:
        self.anomalies.append(Anomaly(
            type='custom',
            severity='high',
            title='Custom Pattern Detected',
            description='...',
            evidence={...},
            suggested_action={...},
            confidence=0.85
        ))
```

### Add New Template

```python
# In templates.py

templates.append(WorkflowTemplate(
    id='TPL_CUSTOM',
    name='My Custom Template',
    description='...',
    industry='custom',
    steps=[...],
    rules=[...],
    compliance_standards=[...],
    use_count=0
))
```

## Configuration

### Adjust Detection Sensitivity

```python
# In analyzer.py

# Benford's Law threshold
if p_value < 0.01:  # More strict (was 0.05)
    self.anomalies.append(...)

# Round number threshold
if round_pct > 60:  # More strict (was 50)
    self.anomalies.append(...)
```

### Customize Suggestions

```python
# In suggestions.py

def _generate_reasoning(self, anomaly: Anomaly) -> str:
    # Add custom reasoning for your domain
    if 'your_pattern' in anomaly.title:
        return "Your custom explanation..."
```

## Dependencies

```
scikit-learn>=1.3.0  # DBSCAN clustering, outlier detection
scipy>=1.11.0         # Statistical tests (chi-square)
pandas>=2.0.0         # Data manipulation
numpy>=1.24.0         # Numerical operations
```

## Performance

**Typical Analysis Times:**
- 1K records: <1 second
- 10K records: 2-3 seconds
- 100K records: 10-15 seconds
- 1M records: 60-90 seconds

**Memory Usage:**
- ~2MB per 1K records
- ~20MB per 10K records
- ~200MB per 100K records

## Future Enhancements

Potential additions:
- LLM integration for natural language explanations (OpenAI/Anthropic)
- Network analysis for vendor-employee collusion detection
- Time-series forecasting for anomaly prediction
- Active learning from user feedback
- Multi-variate anomaly detection (Isolation Forest)

## Testing

```bash
# Run analyzer tests
pytest tests/test_ai_assistant.py -v

# Test on sample data
python -m audit_agent.ai_assistant.analyzer
```

## References

- **Benford's Law**: [Nigrini, Mark (2012). Benford's Law: Applications for Forensic Accounting, Auditing, and Fraud Detection](https://www.wiley.com/en-us/Benford%27s+Law%3A+Applications+for+Forensic+Accounting%2C+Auditing%2C+and+Fraud+Detection-p-9781118152850)
- **DBSCAN Clustering**: [Ester et al. (1996). A density-based algorithm for discovering clusters](https://www.aaai.org/Papers/KDD/1996/KDD96-037.pdf)
- **SOX Compliance**: [Sarbanes-Oxley Act Section 404](https://www.sec.gov/rules/final/33-8238.htm)

## License

MIT License - See parent directory LICENSE file
