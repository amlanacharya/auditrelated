# Intelligent Audit Agent - Streamlit POC

Interactive web interface for the Intelligent Audit Agent.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd /path/to/auditrelated
pip install -r requirements.txt
```

### 2. Launch the App

```bash
streamlit run streamlit_app/app.py
```

The app will open in your browser at `http://localhost:8501`

## 📱 User Interface

### Homepage
- System status overview
- Quick navigation
- Feature highlights

### 1️⃣ Upload Data
- **Option A**: Generate sample dataset (10K expenses, 500 employees)
- **Option B**: Upload your own CSV files
- Automatic Parquet conversion
- Schema extraction

### 2️⃣ Define Process
- **Pre-built**: Expense reimbursement workflow
- **Custom**: Build your own process flows
- Define steps, tables, and expected durations
- Visualize workflow

### 3️⃣ Build Rules
- **Core Rules**: Initialize 5 pre-built violation rules
- **Custom Rules**: Create SQL-based detection rules
- SQL query editor with examples
- Version management

### 4️⃣ Run Audit
- Configure parallel execution
- Real-time progress tracking
- Performance metrics
- Export results (CSV/JSON)

### 5️⃣ Results Dashboard
- Interactive visualizations
- Filter by severity, rule, amount
- Timeline analysis
- Top violators
- Detailed data table with pagination
- Export filtered results

## 🎨 Features

### No-Code Interface
- Drag-and-drop file upload
- Visual process builder
- Form-based rule creation
- Point-and-click audit execution

### Real-Time Analysis
- Instant violation detection
- Live performance metrics
- Interactive dashboards
- Severity-based filtering

### Export Capabilities
- CSV export
- JSON export
- Summary reports
- Filtered datasets

## 📊 Sample Workflow

1. **Start**: Navigate to "Upload Data"
2. **Generate**: Click "Generate Sample Dataset"
3. **Extract**: Click "Extract Schemas and Build Knowledge Graph"
4. **Process**: Go to "Define Process" → Use pre-built expense reimbursement
5. **Rules**: Go to "Build Rules" → Initialize core rules
6. **Audit**: Go to "Run Audit" → Execute with parallel mode
7. **Analyze**: Go to "Results Dashboard" → Explore violations

**Expected Time**: ~2 minutes for complete workflow

## 🔧 Configuration

### Session State Variables

The app uses Streamlit session state to track:
- `data_uploaded`: Whether data is loaded
- `kg_initialized`: Whether Knowledge Graph is built
- `audit_executed`: Whether audit has run
- `violations`: Detected violations DataFrame
- `process_defined`: Whether business process is configured
- `rules_initialized`: Whether rules are active

### File Locations

- **Parquet Data**: `data/parquet/`
- **Knowledge Graph**: `data/kg.db`
- **Raw CSV**: `data/raw/` (if using sample data)

## 📝 Custom Data Format

If uploading your own files, use this format:

### expenses.csv
```csv
expense_id,employee_id,vendor_id,amount,transaction_date,description,category,status,approver_id
1,101,201,250.00,2024-01-15,Office supplies,Supplies,paid,150
2,102,202,1500.50,2024-01-16,Client dinner,Meals,paid,151
```

### employees.csv
```csv
employee_id,first_name,last_name,email,department,title,manager_id,approval_limit,hire_date
101,John,Doe,john@company.com,Finance,Analyst,150,1000,2023-01-15
102,Jane,Smith,jane@company.com,Sales,Manager,151,5000,2022-06-01
```

### approvals.csv
```csv
approval_id,expense_id,approver_id,approval_date,status
1,1,150,2024-01-16,approved
2,2,151,2024-01-17,approved
```

## 🎯 Tips for Best Results

### Data Quality
- Ensure consistent date formats (YYYY-MM-DD)
- Include all required columns
- No missing IDs in relationships

### Performance
- Use parallel execution for large datasets
- Partition expenses by year/month
- 4 threads recommended for most systems

### Rule Creation
- Test SQL queries before saving
- Include descriptive violation reasons
- Set appropriate severity levels

## 🐛 Troubleshooting

### Issue: "Module not found"
**Solution**: Install dependencies
```bash
pip install -r requirements.txt
```

### Issue: "No data found"
**Solution**: Upload data first or generate sample dataset

### Issue: "SQL query error"
**Solution**: Validate SQL syntax, check table/column names

### Issue: "Slow performance"
**Solution**:
- Reduce number of threads
- Check available memory
- Partition large tables

## 🔗 Integration

### Use with Existing Data

```python
# Save your data as CSV
your_dataframe.to_csv('data/raw/expenses.csv', index=False)

# Upload via Streamlit UI
# Or use CLI:
from audit_agent.data_layer import DataIngestion

ingestion = DataIngestion()
ingestion.load_csv_to_parquet('data/raw/expenses.csv', 'expenses')
```

### Programmatic Access

```python
# Access violations from session state
import streamlit as st

if st.session_state.get('violations') is not None:
    violations = st.session_state.violations

    # Your custom analysis
    critical = violations[violations['severity'] == 'critical']

    # Send alerts, generate reports, etc.
```

## 📚 Additional Resources

- **Full Documentation**: `../IMPLEMENTATION_GUIDE.md`
- **Core Library**: `../audit_agent/`
- **Examples**: `../examples/`
- **Tests**: `../tests/`

## 🎨 Customization

### Add Custom Pages

Create a new file in `streamlit_app/pages/`:

```python
# streamlit_app/pages/6_Custom_Page.py

import streamlit as st

st.title("My Custom Page")
st.write("Custom analysis here...")
```

### Modify Styling

Edit CSS in `app.py`:

```python
st.markdown("""
    <style>
    .custom-class {
        /* Your styles */
    }
    </style>
""", unsafe_allow_html=True)
```

## 📧 Support

- Report issues on GitHub
- Check `IMPLEMENTATION_GUIDE.md` for detailed docs
- Review example scripts in `examples/`

## License

MIT License - See parent directory LICENSE file
