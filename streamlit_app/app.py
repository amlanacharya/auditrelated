"""
Intelligent Audit Agent - Interactive POC

Streamlit frontend for:
- File upload and data ingestion
- Custom process definition
- Violation rule creation
- Audit execution
- Results visualization
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Page configuration
st.set_page_config(
    page_title="Intelligent Audit Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.25rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 0.25rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 0.25rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.data_uploaded = False
    st.session_state.kg_initialized = False
    st.session_state.audit_executed = False
    st.session_state.violations = None

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/200x80/1f77b4/ffffff?text=Audit+Agent", use_container_width=True)

    st.markdown("### 🔍 Navigation")
    st.markdown("---")

    # Status indicators
    st.markdown("#### System Status")

    status_data = "✅" if st.session_state.data_uploaded else "⏳"
    status_kg = "✅" if st.session_state.kg_initialized else "⏳"
    status_audit = "✅" if st.session_state.audit_executed else "⏳"

    st.markdown(f"""
    - {status_data} Data Uploaded
    - {status_kg} Knowledge Graph
    - {status_audit} Audit Executed
    """)

    st.markdown("---")
    st.markdown("#### Quick Actions")

    # Show system status with expander
    with st.expander("📊 System Status", expanded=False):
        from audit_agent.utils import ResetManager

        reset_mgr = ResetManager("data/kg.db", "data/parquet")
        status = reset_mgr.get_system_status()

        if status['kg_database_exists']:
            st.metric("Database", f"{status['kg_database_size_mb']:.2f} MB")
        else:
            st.metric("Database", "Not created")

        if status['parquet_directory_exists']:
            st.metric("Parquet Files", f"{status['parquet_files_count']} files")
            st.metric("Parquet Size", f"{status['parquet_total_size_mb']:.2f} MB")
        else:
            st.metric("Parquet Data", "Not created")

    # Initialize reset confirmation state
    if 'show_reset_confirm' not in st.session_state:
        st.session_state.show_reset_confirm = False

    if not st.session_state.show_reset_confirm:
        if st.button("🔄 Reset System", use_container_width=True, type="secondary"):
            st.session_state.show_reset_confirm = True
            st.rerun()
    else:
        st.warning("⚠️ **Warning**: This will delete ALL data and tables!")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Confirm", use_container_width=True, type="primary"):
                with st.spinner("Resetting system..."):
                    from audit_agent.utils import reset_system

                    # Perform reset
                    results = reset_system(
                        kg_db_path="data/kg.db",
                        parquet_path="data/parquet",
                        delete_db_file=True  # Delete entire DB file for clean slate
                    )

                    if results['success']:
                        # Clear session state
                        for key in list(st.session_state.keys()):
                            del st.session_state[key]

                        st.success("✅ System reset complete!")
                        st.rerun()
                    else:
                        st.error("❌ Reset failed. Check logs.")
                        st.session_state.show_reset_confirm = False

        with col2:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.show_reset_confirm = False
                st.rerun()

    st.markdown("---")
    st.markdown("""
    <small>
    **Intelligent Audit Agent**<br>
    90% SQL + 10% AI<br>
    Version 0.1.0
    </small>
    """, unsafe_allow_html=True)

# Main content
st.markdown('<p class="main-header">🔍 Intelligent Audit Agent</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">90% SQL + 10% AI for Compliance-Grade Violation Detection</p>', unsafe_allow_html=True)

# Welcome message
st.markdown("""
## Welcome to the Audit Agent POC! 👋

This interactive tool allows you to:

1. **📤 Upload Data** - Load your expense data from CSV files
2. **📋 Define Processes** - Create custom business workflows
3. **⚙️ Build Rules** - Design violation detection rules
4. **🚀 Run Audits** - Execute violation detection
5. **📊 View Results** - Analyze findings with visualizations

### 🎯 Workflow Overview

```
Upload CSV Files → Define Process → Create Rules → Run Audit → View Violations
```

### 🚀 Getting Started

1. Navigate to **"1️⃣ Upload Data"** in the sidebar
2. Upload your expense, employee, and vendor CSV files
3. Follow the guided workflow through each step

---
""")

# Feature highlights
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### 🎨 Key Features
    - **No-code interface** for audit setup
    - **Drag-and-drop** file upload
    - **Visual process builder**
    - **Custom rule creator**
    - **Real-time audit execution**
    """)

with col2:
    st.markdown("""
    ### 📊 Built-in Rules
    - Self-approval detection
    - Duplicate expenses
    - Missing approvals
    - Timeline violations
    - Split transactions
    """)

with col3:
    st.markdown("""
    ### 🔍 Analysis Tools
    - Interactive dashboards
    - Severity-based filtering
    - Financial impact analysis
    - Export to CSV/Excel
    - Full audit trail
    """)

st.markdown("---")

# Quick stats (if data available)
if st.session_state.data_uploaded:
    st.markdown("### 📈 Current Session Stats")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Data Status", "Loaded", delta="Ready")

    with col2:
        kg_status = "Initialized" if st.session_state.kg_initialized else "Pending"
        st.metric("Knowledge Graph", kg_status)

    with col3:
        audit_status = "Complete" if st.session_state.audit_executed else "Not Run"
        st.metric("Audit Status", audit_status)

    with col4:
        if st.session_state.violations is not None:
            violation_count = len(st.session_state.violations)
            st.metric("Violations Found", violation_count, delta=f"{violation_count} issues")
        else:
            st.metric("Violations Found", "N/A")

else:
    st.info("👆 Start by uploading your data files using the sidebar navigation!")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
<small>
Powered by DuckDB + Parquet + SQLite |
<a href='https://github.com/yourusername/audit-agent'>Documentation</a> |
<a href='https://github.com/yourusername/audit-agent/issues'>Report Issue</a>
</small>
</div>
""", unsafe_allow_html=True)
