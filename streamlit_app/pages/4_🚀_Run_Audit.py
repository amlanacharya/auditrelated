"""
Page 4: Run Audit

Execute violation detection and view results
"""

import streamlit as st
import sys
from pathlib import Path
import time
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from audit_agent.violation_engine import RuleExecutor

st.set_page_config(page_title="Run Audit", page_icon="🚀", layout="wide")

st.title("🚀 Execute Audit")
st.markdown("Run violation detection across your data.")

# Check prerequisites
if not st.session_state.get('rules_initialized', False):
    st.warning("⚠️ Please initialize rules first!")
    if st.button("← Go to Build Rules"):
        st.switch_page("pages/3_⚙️_Build_Rules.py")
    st.stop()

# Audit configuration
st.markdown("## Step 1: Configure Audit")

col1, col2 = st.columns(2)

with col1:
    parallel_execution = st.checkbox(
        "Parallel Execution",
        value=True,
        help="Run rules in parallel for faster execution"
    )

    num_threads = st.slider(
        "Number of Threads",
        min_value=1,
        max_value=8,
        value=4,
        help="More threads = faster execution"
    ) if parallel_execution else 1

with col2:
    st.metric("Parallel Mode", "Enabled" if parallel_execution else "Disabled")
    st.metric("Threads", num_threads if parallel_execution else "N/A")

# Execute audit
st.markdown("## Step 2: Execute Audit")

if st.button("🚀 Run Violation Detection", use_container_width=True, type="primary"):
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        # Initialize executor
        status_text.text("Initializing audit engine...")
        progress_bar.progress(10)

        executor = RuleExecutor(
            parquet_path="data/parquet",
            kg_db_path="data/kg.db",
            num_threads=num_threads
        )

        # Execute rules
        status_text.text("Executing violation rules...")
        progress_bar.progress(30)

        start_time = time.time()
        violations = executor.run_all_rules(parallel=parallel_execution)
        execution_time = time.time() - start_time

        progress_bar.progress(70)

        # Get summary
        status_text.text("Analyzing results...")
        summary = executor.get_violation_summary(violations)

        progress_bar.progress(90)

        # Get metrics
        metrics = executor.metrics
        perf_summary = metrics.get_performance_summary()

        progress_bar.progress(100)
        status_text.text("✅ Audit complete!")

        # Store results
        st.session_state.violations = violations
        st.session_state.audit_executed = True
        st.session_state.audit_summary = summary
        st.session_state.execution_time = execution_time
        st.session_state.performance_metrics = perf_summary

        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()

        # Show success message
        st.success(f"✅ Audit completed in {execution_time:.2f} seconds!")
        st.balloons()

        executor.close()

    except Exception as e:
        st.error(f"❌ Audit failed: {str(e)}")
        st.exception(e)

# Show results if available
if st.session_state.get('audit_executed', False):
    st.markdown("---")
    st.markdown("## Step 3: Audit Results")

    violations = st.session_state.violations
    summary = st.session_state.audit_summary

    # High-level metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Violations",
            summary['total_violations'],
            delta=f"{summary['total_violations']} issues"
        )

    with col2:
        st.metric(
            "Unique Expenses",
            summary.get('unique_expenses', 'N/A')
        )

    with col3:
        if 'total_financial_impact' in summary:
            st.metric(
                "Financial Impact",
                f"${summary['total_financial_impact']:,.2f}",
                delta="Total exposure"
            )
        else:
            st.metric("Financial Impact", "N/A")

    with col4:
        execution_time = st.session_state.execution_time
        st.metric(
            "Execution Time",
            f"{execution_time:.2f}s",
            delta=f"{summary['total_violations']/execution_time:.0f} checks/sec" if execution_time > 0 else "N/A"
        )

    # Severity breakdown
    st.markdown("### 📊 Violations by Severity")

    col1, col2, col3, col4 = st.columns(4)

    severity_colors = {
        'critical': '🔴',
        'high': '🟠',
        'medium': '🟡',
        'low': '🟢'
    }

    for idx, (severity, count) in enumerate(summary['by_severity'].items()):
        col = [col1, col2, col3, col4][idx % 4]
        with col:
            st.metric(
                f"{severity_colors.get(severity, '⚪')} {severity.title()}",
                count,
                delta=f"{count/summary['total_violations']*100:.1f}%"
            )

    # Rule breakdown
    st.markdown("### 📋 Violations by Rule")

    rule_data = pd.DataFrame([
        {'Rule': rule, 'Count': count}
        for rule, count in summary['by_rule'].items()
    ]).sort_values('Count', ascending=False)

    st.dataframe(rule_data, use_container_width=True, hide_index=True)

    # Sample violations
    st.markdown("### 🔍 Sample Violations (Top 10)")

    if not violations.empty:
        # Prepare display columns
        display_cols = ['expense_id', 'rule_name', 'severity']

        if 'employee_id' in violations.columns:
            display_cols.append('employee_id')
        if 'amount' in violations.columns:
            display_cols.append('amount')
        if 'violation_reason' in violations.columns:
            display_cols.append('violation_reason')

        sample_df = violations[display_cols].head(10)

        # Color code by severity
        def highlight_severity(row):
            colors = {
                'critical': 'background-color: #ffcccc',
                'high': 'background-color: #ffe6cc',
                'medium': 'background-color: #ffffcc',
                'low': 'background-color: #ccffcc'
            }
            return [colors.get(row['severity'], '')] * len(row)

        styled_df = sample_df.style.apply(highlight_severity, axis=1)
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

        # Export options
        st.markdown("### 💾 Export Results")

        col1, col2, col3 = st.columns(3)

        with col1:
            csv_data = violations.to_csv(index=False)
            st.download_button(
                label="📄 Download CSV",
                data=csv_data,
                file_name="violations_report.csv",
                mime="text/csv",
                use_container_width=True
            )

        with col2:
            json_data = violations.to_json(orient='records', indent=2)
            st.download_button(
                label="📋 Download JSON",
                data=json_data,
                file_name="violations_report.json",
                mime="application/json",
                use_container_width=True
            )

        with col3:
            # Excel export would require openpyxl
            st.info("Excel export available with openpyxl package")

    else:
        st.success("🎉 No violations detected! Your data is clean.")

    # Performance metrics
    if 'performance_metrics' in st.session_state:
        perf = st.session_state.performance_metrics

        st.markdown("---")
        st.markdown("### ⚡ Performance Metrics")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Queries", perf.get('total_queries', 'N/A'))

        with col2:
            avg_duration = perf.get('avg_duration', 0)
            st.metric("Avg Query Time", f"{avg_duration:.3f}s")

        with col3:
            max_duration = perf.get('max_duration', 0)
            st.metric("Max Query Time", f"{max_duration:.3f}s")

        with col4:
            total_rows = perf.get('total_rows_processed', 0)
            st.metric("Rows Processed", f"{total_rows:,}")

    # Navigation to detailed dashboard
    st.markdown("---")
    st.success("✅ Audit execution complete! View detailed analysis in **5️⃣ Results Dashboard**.")

    if st.button("➡️ Go to Results Dashboard", use_container_width=True):
        st.switch_page("pages/5_📊_Results_Dashboard.py")
