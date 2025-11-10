"""
Page 3: Violation Rule Builder

Create custom violation detection rules
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from audit_agent.knowledge_graph import KnowledgeGraphManager, ViolationGraph

st.set_page_config(page_title="Build Rules", page_icon="⚙️", layout="wide")

st.title("⚙️ Violation Rule Builder")
st.markdown("Create SQL-based rules to detect process violations.")

# Check prerequisites
if not st.session_state.get('process_defined', False):
    st.warning("⚠️ Please define a process first!")
    if st.button("← Go to Define Process"):
        st.switch_page("pages/2_📋_Define_Process.py")
    st.stop()

# Initialize KG
if 'kg_manager' not in st.session_state:
    st.session_state.kg_manager = KnowledgeGraphManager("data/kg.db")

kg_manager = st.session_state.kg_manager
violation_graph = ViolationGraph(kg_manager)

# Rule management
st.markdown("## Step 1: Select Rules")

option = st.radio(
    "Choose an option:",
    ["Use Core Rules (Recommended)", "Create Custom Rule"],
    horizontal=True
)

if option == "Use Core Rules (Recommended)":
    st.markdown("### 📋 Pre-built Core Rules")

    st.markdown("""
    Initialize the 5 core violation detection rules:

    1. **Self-Approval Detection** (Critical) - Employee approves their own expense
    2. **Duplicate Expense Detection** (High) - Same amount, vendor, within 48 hours
    3. **Missing Approval Detection** (Critical) - Payment without approval record
    4. **Timeline Violation Detection** (High) - Approval after payment
    5. **Split Transaction Detection** (Medium) - Multiple expenses just below threshold
    """)

    if st.button("✅ Initialize Core Rules", use_container_width=True):
        with st.spinner("Initializing rules..."):
            violation_graph.initialize_core_rules()

            st.session_state.rules_initialized = True

            st.success("✅ 5 core rules initialized successfully!")
            st.balloons()

else:
    # Custom rule builder
    st.markdown("### 🎨 Custom Rule Builder")

    with st.form("custom_rule"):
        col1, col2 = st.columns(2)

        with col1:
            rule_id = st.text_input(
                "Rule ID",
                placeholder="e.g., CUSTOM_001",
                help="Unique identifier for this rule"
            )

            rule_name = st.text_input(
                "Rule Name",
                placeholder="e.g., Weekend Approval Detection"
            )

        with col2:
            severity = st.selectbox(
                "Severity",
                ["critical", "high", "medium", "low"]
            )

            effective_from = st.date_input(
                "Effective From",
                value=date.today()
            )

        description = st.text_area(
            "Description",
            placeholder="Describe what this rule detects..."
        )

        st.markdown("#### SQL Query Template")

        # SQL editor with syntax highlighting
        sql_template = st.text_area(
            "SQL Query",
            height=200,
            placeholder="""SELECT
    e.expense_id,
    e.employee_id,
    e.amount,
    e.transaction_date,
    'Violation description' as violation_reason
FROM expenses e
WHERE <your_condition_here>""",
            help="Write a SQL query that returns violations. Include expense_id, employee_id, and violation_reason columns."
        )

        # SQL helper
        with st.expander("📚 SQL Query Examples"):
            st.markdown("""
            **Example 1: High-Value Expenses**
            ```sql
            SELECT expense_id, employee_id, amount,
                   'High-value expense without dual approval' as violation_reason
            FROM expenses e
            LEFT JOIN (SELECT expense_id, COUNT(*) as approver_count
                       FROM approvals GROUP BY expense_id) a
              ON e.expense_id = a.expense_id
            WHERE e.amount > 10000 AND (a.approver_count IS NULL OR a.approver_count < 2)
            ```

            **Example 2: Weekend Transactions**
            ```sql
            SELECT expense_id, employee_id, transaction_date,
                   'Transaction on weekend' as violation_reason
            FROM expenses
            WHERE CAST(strftime('%w', transaction_date) AS INTEGER) IN (0, 6)
            ```

            **Example 3: Rapid Transactions**
            ```sql
            SELECT e1.expense_id, e1.employee_id, e1.amount,
                   'Multiple transactions within 1 hour' as violation_reason
            FROM expenses e1
            JOIN expenses e2 ON e1.employee_id = e2.employee_id AND e1.expense_id < e2.expense_id
            WHERE (JULIANDAY(e2.transaction_date) - JULIANDAY(e1.transaction_date)) * 24 < 1
            ```
            """)

        change_reason = st.text_input(
            "Change Reason",
            placeholder="Why was this rule created?"
        )

        submitted = st.form_submit_button("💾 Save Custom Rule", use_container_width=True)

        if submitted:
            if not rule_id or not rule_name or not sql_template:
                st.error("❌ Rule ID, Name, and SQL query are required!")
            else:
                try:
                    with st.spinner("Creating custom rule..."):
                        violation_graph.create_rule(
                            rule_id=rule_id,
                            rule_name=rule_name,
                            description=description,
                            severity=severity,
                            sql_template=sql_template,
                            effective_from=effective_from,
                            created_by="web_user",
                            change_reason=change_reason
                        )

                        st.session_state.rules_initialized = True

                        st.success(f"✅ Custom rule '{rule_name}' created successfully!")
                        st.balloons()

                except Exception as e:
                    st.error(f"❌ Error creating rule: {str(e)}")

# Show active rules
st.markdown("---")
st.markdown("## Step 2: Review Active Rules")

active_rules = violation_graph.get_active_rules(as_of_date=date.today())

if active_rules:
    st.success(f"**{len(active_rules)} active rules found**")

    # Display rules in cards
    for rule in active_rules:
        with st.expander(f"**{rule['rule_name']}** [{rule['severity'].upper()}]"):
            st.markdown(f"**Description:** {rule.get('description', 'N/A')}")
            st.markdown(f"**Version:** {rule['version']}")

            st.markdown("**SQL Query:**")
            st.code(rule['sql_template'], language='sql')

    # Set rules initialized
    st.session_state.rules_initialized = True

else:
    st.info("No active rules found. Initialize core rules or create custom ones above.")

# Navigation
if st.session_state.get('rules_initialized', False):
    st.markdown("---")
    st.success("✅ Rules configured! Proceed to **4️⃣ Run Audit** to execute violation detection.")

    if st.button("➡️ Go to Run Audit", use_container_width=True):
        st.switch_page("pages/4_🚀_Run_Audit.py")
