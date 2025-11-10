"""
Page 1: Data Upload and Ingestion

Upload CSV files and convert to Parquet format
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from audit_agent.data_layer import DataIngestion, SchemaExtractor
from audit_agent.knowledge_graph import KnowledgeGraphManager, TableGraph

st.set_page_config(page_title="Upload Data", page_icon="📤", layout="wide")

st.title("📤 Data Upload & Ingestion")
st.markdown("Upload your CSV files to begin the audit process.")

# Initialize components
if 'ingestion' not in st.session_state:
    st.session_state.ingestion = DataIngestion(output_base_path="data/parquet")
    st.session_state.uploaded_files = {}

# File upload section
st.markdown("## Step 1: Upload CSV Files")
st.markdown("Upload your expense data files. Required tables: **expenses**, **employees**, **approvals**")

col1, col2 = st.columns([2, 1])

with col1:
    # Option 1: Use sample data
    st.markdown("### Option A: Use Sample Data")
    if st.button("🎲 Generate Sample Dataset", use_container_width=True):
        with st.spinner("Generating sample data..."):
            from audit_agent.synthetic_data import DatasetGenerator

            generator = DatasetGenerator(
                num_employees=500,
                num_expenses=10000,
                start_date="2024-01-01",
                end_date="2024-03-31"
            )

            stats = generator.generate_dataset("data/raw")

            st.session_state.data_uploaded = True
            st.session_state.sample_data_stats = stats

            st.success("✅ Sample dataset generated successfully!")
            st.json(stats)
            st.rerun()

    st.markdown("---")

    # Option 2: Upload custom files
    st.markdown("### Option B: Upload Your Own Files")

    uploaded_files = st.file_uploader(
        "Choose CSV files",
        type=['csv'],
        accept_multiple_files=True,
        help="Upload expenses.csv, employees.csv, vendors.csv, approvals.csv, payments.csv"
    )

    if uploaded_files:
        st.markdown(f"**{len(uploaded_files)} files uploaded:**")
        for file in uploaded_files:
            st.markdown(f"- {file.name} ({file.size / 1024:.1f} KB)")

        if st.button("🚀 Process Uploaded Files", use_container_width=True):
            with st.spinner("Processing files..."):
                # Save uploaded files temporarily
                temp_dir = tempfile.mkdtemp()

                try:
                    ingestion_results = []

                    for uploaded_file in uploaded_files:
                        # Save to temp directory
                        temp_path = Path(temp_dir) / uploaded_file.name
                        with open(temp_path, 'wb') as f:
                            f.write(uploaded_file.getbuffer())

                        # Extract table name from filename
                        table_name = uploaded_file.name.replace('.csv', '')

                        # Ingest to Parquet
                        metadata = st.session_state.ingestion.load_csv_to_parquet(
                            csv_path=str(temp_path),
                            table_name=table_name,
                            date_column="transaction_date" if table_name == "expenses" else None,
                            partition_cols=["year", "month"] if table_name == "expenses" else None
                        )

                        ingestion_results.append(metadata)
                        st.session_state.uploaded_files[table_name] = metadata

                    st.session_state.data_uploaded = True

                    # Display results
                    st.success(f"✅ Successfully processed {len(uploaded_files)} files!")

                    results_df = pd.DataFrame(ingestion_results)
                    st.dataframe(results_df[['table_name', 'row_count', 'column_count', 'duration_seconds']])

                finally:
                    # Cleanup temp directory
                    shutil.rmtree(temp_dir, ignore_errors=True)

with col2:
    st.markdown("### 📋 Required Files")
    st.markdown("""
    **Core Tables:**
    - `expenses.csv` ⭐
    - `employees.csv` ⭐
    - `approvals.csv` ⭐

    **Optional Tables:**
    - `vendors.csv`
    - `payments.csv`
    - `departments.csv`

    **Sample Format:**

    `expenses.csv`:
    ```
    expense_id,employee_id,amount,transaction_date
    1,101,250.00,2024-01-15
    2,102,1500.50,2024-01-16
    ```
    """)

# Show uploaded data
if st.session_state.data_uploaded:
    st.markdown("---")
    st.markdown("## Step 2: Review Ingested Data")

    # Get ingestion summary
    if hasattr(st.session_state, 'sample_data_stats'):
        stats = st.session_state.sample_data_stats

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Employees", stats['employees'])
        col2.metric("Vendors", stats['vendors'])
        col3.metric("Expenses", stats['expenses'])
        col4.metric("Approvals", stats['approvals'])
        col5.metric("Payments", stats['payments'])

        st.info("💡 **Note**: Sample data includes intentional violations for demonstration purposes.")

    elif st.session_state.uploaded_files:
        summary_data = []
        for table_name, metadata in st.session_state.uploaded_files.items():
            summary_data.append({
                'Table': table_name,
                'Rows': metadata['row_count'],
                'Columns': metadata['column_count'],
                'Duration (s)': metadata['duration_seconds']
            })

        st.dataframe(pd.DataFrame(summary_data), use_container_width=True)

    # Schema extraction
    st.markdown("## Step 3: Extract Schemas")

    if st.button("🔍 Extract Schemas and Build Knowledge Graph", use_container_width=True):
        with st.spinner("Extracting schemas..."):
            schema_extractor = SchemaExtractor("data/parquet")
            kg_manager = KnowledgeGraphManager("data/kg.db")
            table_graph = TableGraph(kg_manager)

            # Determine which tables to process
            if hasattr(st.session_state, 'sample_data_stats'):
                tables = ["employees", "vendors", "expenses", "approvals", "payments"]
            else:
                tables = list(st.session_state.uploaded_files.keys())

            schema_results = []

            for table in tables:
                try:
                    schema = schema_extractor.extract_schema(table)
                    table_graph.register_table_schema(table, schema)

                    schema_results.append({
                        'Table': table,
                        'Columns': schema['column_count'],
                        'Files': schema['parquet_files']
                    })
                except Exception as e:
                    st.warning(f"⚠️ Could not extract schema for {table}: {str(e)}")

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

            st.session_state.kg_initialized = True
            st.session_state.kg_manager = kg_manager
            st.session_state.relationships = relationships

            st.success(f"✅ Extracted schemas for {len(schema_results)} tables!")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Schema Summary:**")
                st.dataframe(pd.DataFrame(schema_results), use_container_width=True)

            with col2:
                st.markdown(f"**Relationships Detected: {len(relationships)}**")
                for rel in relationships[:5]:  # Show first 5
                    st.markdown(f"- `{rel['from_table']}.{rel['from_column']}` → `{rel['to_table']}.{rel['to_column']}` ({rel['confidence']})")

                if len(relationships) > 5:
                    st.markdown(f"*...and {len(relationships) - 5} more*")

            kg_manager.close()

# Navigation hint
if st.session_state.data_uploaded and st.session_state.kg_initialized:
    st.markdown("---")
    st.success("✅ Data ingestion complete! Proceed to **2️⃣ Define Process** to set up your audit workflow.")

    if st.button("➡️ Go to Process Definition", use_container_width=True):
        st.switch_page("pages/2_📋_Define_Process.py")
