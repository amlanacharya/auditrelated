"""
Page 2: Process Definition

Define custom business processes and workflows
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from audit_agent.knowledge_graph import KnowledgeGraphManager, ProcessGraph, EntityGraph

st.set_page_config(page_title="Define Process", page_icon="📋", layout="wide")

st.title("📋 Define Business Process")
st.markdown("Create or select a business workflow to audit.")

# Check prerequisites
if not st.session_state.get('data_uploaded', False):
    st.warning("⚠️ Please upload data first!")
    if st.button("← Go to Upload Data"):
        st.switch_page("pages/1_📤_Upload_Data.py")
    st.stop()

# Initialize KG - create fresh connection each time (thread-safe)
kg_db_path = st.session_state.get('kg_db_path', 'data/kg.db')
kg_manager = KnowledgeGraphManager(kg_db_path)
process_graph = ProcessGraph(kg_manager)
entity_graph = EntityGraph(kg_manager)

# Process selection
st.markdown("## Step 1: Select or Create Process")

option = st.radio(
    "Choose an option:",
    ["Use Pre-built Process (Expense Reimbursement)", "Create Custom Process"],
    horizontal=True
)

if option == "Use Pre-built Process (Expense Reimbursement)":
    st.markdown("### 📝 Expense Reimbursement Process")

    st.markdown("""
    This pre-built process includes:

    **Workflow Steps:**
    1. **Initiation** - Employee submits expense
    2. **Approval** - Manager reviews and approves
    3. **Payment** - Finance processes payment

    **Expected Timeline:**
    - Initiation → Approval: 2-3 days
    - Approval → Payment: 7-10 days
    """)

    if st.button("✅ Use This Process", use_container_width=True):
        with st.spinner("Setting up process..."):
            # Check if process already exists
            existing_process_id = process_graph.get_process_by_name("expense_reimbursement")

            if existing_process_id:
                # Process already exists, just mark it as active
                st.session_state.process_defined = True
                st.session_state.process_name = "expense_reimbursement"
                st.success("✅ Expense reimbursement process is already configured!")
            else:
                # Create new process
                process_id = process_graph.create_process_type(
                    process_name="expense_reimbursement",
                    description="Employee expense reimbursement workflow"
                )

                # Add steps
                step1_id = process_graph.add_process_step(
                    process_type_id=process_id,
                    step_name="initiation",
                    sequence_order=1,
                    required_table="expenses",
                    expected_duration_minutes=0
                )

                step2_id = process_graph.add_process_step(
                    process_type_id=process_id,
                    step_name="approval",
                    sequence_order=2,
                    required_table="approvals",
                    expected_duration_minutes=2880  # 2 days
                )

                step3_id = process_graph.add_process_step(
                    process_type_id=process_id,
                    step_name="payment",
                    sequence_order=3,
                    required_table="payments",
                    expected_duration_minutes=10080  # 7 days
                )

                # Add transitions
                process_graph.add_transition(step1_id, step2_id)
                process_graph.add_transition(step2_id, step3_id)

                # Setup entities (these use INSERT OR IGNORE/REPLACE so safe to call)
                entity_graph.create_entity_type("employee", "Employee entity")
                entity_graph.create_entity_type("manager", "Manager entity")
                entity_graph.create_entity_type("vendor", "Vendor entity")

                entity_graph.add_relationship("employee", "reports_to", "manager")

                st.session_state.process_defined = True
                st.session_state.process_name = "expense_reimbursement"

                st.success("✅ Expense reimbursement process configured!")
                st.balloons()

else:
    # Custom process builder
    st.markdown("### 🎨 Custom Process Builder")

    with st.form("custom_process"):
        process_name = st.text_input(
            "Process Name",
            placeholder="e.g., purchase_order, payroll_processing",
            help="Use lowercase with underscores"
        )

        process_description = st.text_area(
            "Description",
            placeholder="Describe the business process..."
        )

        st.markdown("#### Define Workflow Steps")

        num_steps = st.number_input("Number of Steps", min_value=2, max_value=10, value=3)

        steps = []
        for i in range(num_steps):
            st.markdown(f"**Step {i+1}:**")
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                step_name = st.text_input(
                    f"Step Name",
                    key=f"step_name_{i}",
                    placeholder=f"e.g., initiation, approval"
                )

            with col2:
                required_table = st.text_input(
                    f"Data Table",
                    key=f"table_{i}",
                    placeholder=f"e.g., expenses, approvals"
                )

            with col3:
                duration_days = st.number_input(
                    f"Duration (days)",
                    key=f"duration_{i}",
                    min_value=0,
                    value=0
                )

            if step_name and required_table:
                steps.append({
                    'name': step_name,
                    'table': required_table,
                    'duration_minutes': duration_days * 24 * 60
                })

        submitted = st.form_submit_button("💾 Save Custom Process", use_container_width=True)

        if submitted:
            if not process_name:
                st.error("❌ Process name is required!")
            elif len(steps) < 2:
                st.error("❌ At least 2 steps are required!")
            else:
                with st.spinner("Creating custom process..."):
                    # Check if process already exists
                    existing_process_id = process_graph.get_process_by_name(process_name)

                    if existing_process_id:
                        # Process already exists
                        st.session_state.process_defined = True
                        st.session_state.process_name = process_name
                        st.warning(f"⚠️ Process '{process_name}' already exists! Using existing process.")
                    else:
                        # Create new process
                        process_id = process_graph.create_process_type(
                            process_name=process_name,
                            description=process_description
                        )

                        # Add steps
                        step_ids = []
                        for idx, step in enumerate(steps):
                            step_id = process_graph.add_process_step(
                                process_type_id=process_id,
                                step_name=step['name'],
                                sequence_order=idx + 1,
                                required_table=step['table'],
                                expected_duration_minutes=step['duration_minutes']
                            )
                            step_ids.append(step_id)

                        # Add transitions (sequential)
                        for i in range(len(step_ids) - 1):
                            process_graph.add_transition(step_ids[i], step_ids[i + 1])

                        st.session_state.process_defined = True
                        st.session_state.process_name = process_name

                        st.success(f"✅ Custom process '{process_name}' created successfully!")
                        st.balloons()

# Show current process if defined
if st.session_state.get('process_defined', False):
    st.markdown("---")
    st.markdown("## Step 2: Review Process Flow")

    process_name = st.session_state.process_name
    flow = process_graph.get_process_flow(process_name)

    if flow:
        st.success(f"**Active Process:** {flow['process_name']}")
        st.markdown(f"*{flow['description']}*")

        # Display flow diagram
        st.markdown("### Workflow Visualization")

        for idx, step in enumerate(flow['steps']):
            col1, col2, col3 = st.columns([1, 3, 2])

            with col1:
                st.markdown(f"**Step {step['sequence_order']}**")

            with col2:
                st.markdown(f"**{step['step_name'].title()}**")
                st.caption(f"Table: `{step['required_table']}`")

            with col3:
                if step['expected_duration_minutes']:
                    days = step['expected_duration_minutes'] / (24 * 60)
                    st.metric("Expected Duration", f"{days:.1f} days")

            if idx < len(flow['steps']) - 1:
                st.markdown("&nbsp;&nbsp;&nbsp;&nbsp;⬇️")

        # Entity relationships
        st.markdown("### Entity Relationships")

        relationships = entity_graph.get_entity_relationships()
        if relationships:
            for rel in relationships:
                st.markdown(f"- `{rel['from_entity_type']}` **{rel['relationship_type']}** `{rel['to_entity_type']}`")
        else:
            st.info("No entity relationships defined yet.")

    # Navigation
    st.markdown("---")
    st.success("✅ Process definition complete! Proceed to **3️⃣ Build Rules** to create violation detection rules.")

    if st.button("➡️ Go to Rule Builder", use_container_width=True):
        st.switch_page("pages/3_⚙️_Build_Rules.py")
