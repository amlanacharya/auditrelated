"""
Page 5: Results Dashboard

Interactive dashboard for violation analysis
"""

import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

st.set_page_config(page_title="Results Dashboard", page_icon="📊", layout="wide")

st.title("📊 Audit Results Dashboard")
st.markdown("Comprehensive analysis of detected violations.")

# Check if audit was executed
if not st.session_state.get('audit_executed', False):
    st.warning("⚠️ No audit results available. Please run an audit first!")
    if st.button("← Go to Run Audit"):
        st.switch_page("pages/4_🚀_Run_Audit.py")
    st.stop()

violations = st.session_state.violations
summary = st.session_state.audit_summary

if violations.empty:
    st.success("🎉 No violations detected! Your data is clean.")
    st.stop()

# Filters
st.markdown("## 🔍 Filters")

col1, col2, col3 = st.columns(3)

with col1:
    severity_filter = st.multiselect(
        "Severity",
        options=['critical', 'high', 'medium', 'low'],
        default=['critical', 'high', 'medium', 'low']
    )

with col2:
    rule_filter = st.multiselect(
        "Rule",
        options=violations['rule_name'].unique().tolist(),
        default=violations['rule_name'].unique().tolist()
    )

with col3:
    if 'amount' in violations.columns:
        min_amount = float(violations['amount'].min())
        max_amount = float(violations['amount'].max())

        amount_range = st.slider(
            "Amount Range",
            min_value=min_amount,
            max_value=max_amount,
            value=(min_amount, max_amount)
        )
    else:
        amount_range = None

# Apply filters
filtered_violations = violations[
    (violations['severity'].isin(severity_filter)) &
    (violations['rule_name'].isin(rule_filter))
]

if amount_range and 'amount' in violations.columns:
    filtered_violations = filtered_violations[
        (filtered_violations['amount'] >= amount_range[0]) &
        (filtered_violations['amount'] <= amount_range[1])
    ]

st.markdown(f"**Showing {len(filtered_violations)} of {len(violations)} violations**")

# Summary metrics
st.markdown("---")
st.markdown("## 📈 Key Metrics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Violations", len(filtered_violations))

with col2:
    if 'employee_id' in filtered_violations.columns:
        unique_employees = filtered_violations['employee_id'].nunique()
        st.metric("Affected Employees", unique_employees)

with col3:
    if 'amount' in filtered_violations.columns:
        total_amount = filtered_violations['amount'].sum()
        st.metric("Total Amount", f"${total_amount:,.2f}")

with col4:
    critical_count = len(filtered_violations[filtered_violations['severity'] == 'critical'])
    st.metric("Critical Issues", critical_count, delta="High priority")

# Visualizations
st.markdown("---")
st.markdown("## 📊 Visualizations")

# Severity distribution
col1, col2 = st.columns(2)

with col1:
    st.markdown("### Violations by Severity")

    severity_counts = filtered_violations['severity'].value_counts()

    fig = px.pie(
        values=severity_counts.values,
        names=severity_counts.index,
        title="Severity Distribution",
        color=severity_counts.index,
        color_discrete_map={
            'critical': '#ff4444',
            'high': '#ff9944',
            'medium': '#ffdd44',
            'low': '#44ff44'
        }
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("### Violations by Rule")

    rule_counts = filtered_violations['rule_name'].value_counts().head(10)

    fig = px.bar(
        x=rule_counts.values,
        y=rule_counts.index,
        orientation='h',
        title="Top 10 Rules by Violation Count",
        labels={'x': 'Count', 'y': 'Rule'},
        color=rule_counts.values,
        color_continuous_scale='Reds'
    )
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# Amount analysis (if available)
if 'amount' in filtered_violations.columns:
    st.markdown("### Financial Impact Analysis")

    col1, col2 = st.columns(2)

    with col1:
        # Amount distribution
        fig = px.histogram(
            filtered_violations,
            x='amount',
            nbins=30,
            title="Amount Distribution",
            labels={'amount': 'Amount ($)', 'count': 'Frequency'},
            color_discrete_sequence=['#1f77b4']
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Amount by severity
        fig = px.box(
            filtered_violations,
            x='severity',
            y='amount',
            title="Amount by Severity",
            labels={'amount': 'Amount ($)', 'severity': 'Severity'},
            color='severity',
            color_discrete_map={
                'critical': '#ff4444',
                'high': '#ff9944',
                'medium': '#ffdd44',
                'low': '#44ff44'
            }
        )
        st.plotly_chart(fig, use_container_width=True)

# Timeline analysis (if date available)
if 'transaction_date' in filtered_violations.columns:
    st.markdown("### Timeline Analysis")

    # Convert to datetime
    filtered_violations['transaction_date'] = pd.to_datetime(filtered_violations['transaction_date'])

    # Group by date
    daily_violations = filtered_violations.groupby(
        filtered_violations['transaction_date'].dt.date
    ).size().reset_index(name='count')

    fig = px.line(
        daily_violations,
        x='transaction_date',
        y='count',
        title="Violations Over Time",
        labels={'transaction_date': 'Date', 'count': 'Violation Count'},
        markers=True
    )
    fig.update_traces(line_color='#1f77b4')
    st.plotly_chart(fig, use_container_width=True)

# Top violators (if employee_id available)
if 'employee_id' in filtered_violations.columns:
    st.markdown("---")
    st.markdown("### 👥 Top Violators")

    top_violators = filtered_violations['employee_id'].value_counts().head(10)

    col1, col2 = st.columns([1, 2])

    with col1:
        st.dataframe(
            pd.DataFrame({
                'Employee ID': top_violators.index,
                'Violation Count': top_violators.values
            }),
            use_container_width=True,
            hide_index=True
        )

    with col2:
        fig = px.bar(
            x=top_violators.values,
            y=top_violators.index.astype(str),
            orientation='h',
            title="Top 10 Employees by Violation Count",
            labels={'x': 'Violations', 'y': 'Employee ID'},
            color=top_violators.values,
            color_continuous_scale='Oranges'
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

# Detailed data table
st.markdown("---")
st.markdown("## 📋 Detailed Violations")

# Add search
search_term = st.text_input("🔍 Search violations", placeholder="Enter expense ID, employee ID, or keyword...")

if search_term:
    mask = filtered_violations.astype(str).apply(
        lambda row: row.str.contains(search_term, case=False).any(),
        axis=1
    )
    display_violations = filtered_violations[mask]
else:
    display_violations = filtered_violations

# Pagination
page_size = st.selectbox("Rows per page", [10, 25, 50, 100], index=1)
total_pages = (len(display_violations) - 1) // page_size + 1

if total_pages > 1:
    page = st.number_input(
        "Page",
        min_value=1,
        max_value=total_pages,
        value=1
    )
else:
    page = 1

start_idx = (page - 1) * page_size
end_idx = start_idx + page_size

# Display table
display_cols = ['expense_id', 'rule_name', 'severity']
if 'employee_id' in display_violations.columns:
    display_cols.append('employee_id')
if 'amount' in display_violations.columns:
    display_cols.append('amount')
if 'violation_reason' in display_violations.columns:
    display_cols.append('violation_reason')
if 'transaction_date' in display_violations.columns:
    display_cols.append('transaction_date')

paginated_df = display_violations[display_cols].iloc[start_idx:end_idx]

# Style by severity
def highlight_row(row):
    colors = {
        'critical': 'background-color: #ffcccc',
        'high': 'background-color: #ffe6cc',
        'medium': 'background-color: #ffffcc',
        'low': 'background-color: #e6ffe6'
    }
    return [colors.get(row['severity'], '')] * len(row)

styled_df = paginated_df.style.apply(highlight_row, axis=1)
st.dataframe(styled_df, use_container_width=True, hide_index=True)

st.markdown(f"*Showing rows {start_idx + 1} to {min(end_idx, len(display_violations))} of {len(display_violations)}*")

# Export filtered data
st.markdown("---")
st.markdown("## 💾 Export Filtered Results")

col1, col2, col3 = st.columns(3)

with col1:
    csv_data = display_violations.to_csv(index=False)
    st.download_button(
        label="📄 Download Filtered CSV",
        data=csv_data,
        file_name="filtered_violations.csv",
        mime="text/csv",
        use_container_width=True
    )

with col2:
    json_data = display_violations.to_json(orient='records', indent=2)
    st.download_button(
        label="📋 Download Filtered JSON",
        data=json_data,
        file_name="filtered_violations.json",
        mime="application/json",
        use_container_width=True
    )

with col3:
    # Summary report
    summary_text = f"""AUDIT SUMMARY REPORT
===================

Total Violations: {len(display_violations)}
Critical: {len(display_violations[display_violations['severity'] == 'critical'])}
High: {len(display_violations[display_violations['severity'] == 'high'])}
Medium: {len(display_violations[display_violations['severity'] == 'medium'])}
Low: {len(display_violations[display_violations['severity'] == 'low'])}

Top Rules:
{display_violations['rule_name'].value_counts().head(5).to_string()}
"""

    st.download_button(
        label="📝 Download Summary Report",
        data=summary_text,
        file_name="audit_summary.txt",
        mime="text/plain",
        use_container_width=True
    )
