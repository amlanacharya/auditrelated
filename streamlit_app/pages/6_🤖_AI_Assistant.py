"""
Page 6: AI Assistant

Intelligent suggestions for workflow improvements and violation detection
"""

import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import plotly.express as px

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from audit_agent.ai_assistant import DataAnalyzer, SuggestionEngine, TemplateLibrary

st.set_page_config(page_title="AI Assistant", page_icon="🤖", layout="wide")

st.title("🤖 AI Audit Assistant")
st.markdown("Intelligent suggestions to enhance your audit workflow and catch blind spots.")

# Initialize components
if 'ai_analyzer' not in st.session_state:
    st.session_state.ai_analyzer = DataAnalyzer()
    st.session_state.suggestion_engine = SuggestionEngine()
    st.session_state.template_library = TemplateLibrary()
    st.session_state.ai_suggestions = []
    st.session_state.ai_analysis_done = False

# Main tabs
tab1, tab2, tab3 = st.tabs(["📊 Data Analysis", "🏗️ Workflow Suggestions", "📚 Templates"])

# ========================================
# TAB 1: DATA ANALYSIS
# ========================================
with tab1:
    st.markdown("## 📊 AI-Powered Data Analysis")
    st.markdown("Let AI analyze your data to find patterns, anomalies, and potential violations.")

    # Check if data is uploaded
    if not st.session_state.get('data_uploaded', False):
        st.warning("⚠️ Please upload data first to enable AI analysis!")
        if st.button("← Go to Upload Data"):
            st.switch_page("pages/1_📤_Upload_Data.py")
        st.stop()

    col1, col2 = st.columns([2, 1])

    with col1:
        if not st.session_state.ai_analysis_done:
            st.info("👉 Click 'Run AI Analysis' to scan your data for anomalies and patterns.")

            if st.button("🚀 Run AI Analysis", use_container_width=True, type="primary"):
                with st.spinner("🔍 Analyzing your data..."):
                    # Analyze each uploaded table
                    all_anomalies = []

                    # Get data from parquet
                    try:
                        # Analyze expenses if available
                        expenses_path = Path("data/parquet/expenses")
                        if expenses_path.exists():
                            expenses_df = pd.read_parquet(str(expenses_path))
                            anomalies = st.session_state.ai_analyzer.analyze(expenses_df, 'expenses')
                            all_anomalies.extend(anomalies)

                        # Generate suggestions from anomalies
                        suggestions = st.session_state.suggestion_engine.generate_from_anomalies(all_anomalies)

                        st.session_state.ai_suggestions = suggestions
                        st.session_state.ai_analysis_done = True
                        st.session_state.suggestion_engine.suggestions = suggestions

                        st.success(f"✅ Analysis complete! Found {len(suggestions)} insights.")
                        st.balloons()
                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ Analysis failed: {str(e)}")
                        st.exception(e)

        else:
            # Show analysis results
            st.success(f"✅ AI analysis complete! Found **{len(st.session_state.ai_suggestions)}** insights.")

            if st.button("🔄 Re-run Analysis", use_container_width=True):
                st.session_state.ai_analysis_done = False
                st.rerun()

    with col2:
        if st.session_state.ai_analysis_done:
            # Quick stats
            suggestions = st.session_state.ai_suggestions

            by_priority = {}
            for s in suggestions:
                by_priority[s.priority] = by_priority.get(s.priority, 0) + 1

            st.metric("🔴 Critical", by_priority.get('critical', 0))
            st.metric("🟠 High", by_priority.get('high', 0))
            st.metric("🟡 Medium", by_priority.get('medium', 0))
            st.metric("🟢 Low", by_priority.get('low', 0))

    # Display findings
    if st.session_state.ai_analysis_done:
        st.markdown("---")
        st.markdown("### 🔍 Detailed Findings")

        # Filter controls
        col1, col2 = st.columns(2)

        with col1:
            priority_filter = st.multiselect(
                "Filter by Priority",
                ['critical', 'high', 'medium', 'low'],
                default=['critical', 'high']
            )

        with col2:
            category_filter = st.multiselect(
                "Filter by Category",
                list(set(s.category for s in st.session_state.ai_suggestions)),
                default=list(set(s.category for s in st.session_state.ai_suggestions))
            )

        # Filter suggestions
        filtered = [
            s for s in st.session_state.ai_suggestions
            if s.priority in priority_filter and s.category in category_filter
        ]

        st.markdown(f"**Showing {len(filtered)} of {len(st.session_state.ai_suggestions)} insights**")

        # Display each suggestion as a card
        for idx, suggestion in enumerate(filtered):
            priority_icon = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡',
                'low': '🟢'
            }

            with st.expander(
                f"{priority_icon.get(suggestion.priority, '⚪')} **{suggestion.title}**",
                expanded=(idx == 0 and suggestion.priority == 'critical')
            ):
                # Description
                st.markdown(f"**Description:**")
                st.markdown(suggestion.description)

                # Reasoning
                st.markdown(f"**Why This Matters:**")
                st.info(suggestion.reasoning)

                # Evidence
                st.markdown(f"**Evidence:**")
                evidence_df = pd.DataFrame([suggestion.evidence])
                st.dataframe(evidence_df.T, use_container_width=True)

                # Suggested action
                st.markdown(f"**Suggested Action:**")
                action = suggestion.suggested_action

                col1, col2, col3 = st.columns(3)

                with col1:
                    if action.get('type') == 'create_rule':
                        if st.button(f"✅ Create Rule", key=f"accept_{suggestion.id}"):
                            # Record feedback
                            st.session_state.suggestion_engine.record_feedback(
                                suggestion.id,
                                'accepted'
                            )

                            # Actually create the rule in KG
                            from audit_agent.knowledge_graph import KnowledgeGraphManager, ViolationGraph
                            from datetime import date

                            try:
                                kg_db_path = st.session_state.get('kg_db_path', 'data/kg.db')
                                with KnowledgeGraphManager(kg_db_path) as kg_manager:
                                    violation_graph = ViolationGraph(kg_manager)

                                    # Generate rule ID based on suggestion
                                    rule_id = f"AI_{suggestion.id[-6:]}"  # Use last 6 chars of suggestion ID

                                    # Create SQL template based on anomaly type
                                    sql_template = suggestion.suggested_action.get('sql_template',
                                        f"-- Auto-generated rule for {suggestion.title}\n-- TODO: Implement detection logic"
                                    )

                                    # Only create if not exists
                                    if not violation_graph.rule_exists(rule_id):
                                        violation_graph.create_rule(
                                            rule_id=rule_id,
                                            rule_name=suggestion.suggested_action.get('rule_name', suggestion.title),
                                            description=suggestion.description,
                                            severity=suggestion.priority,
                                            sql_template=sql_template,
                                            effective_from=date.today(),
                                            created_by="ai_assistant",
                                            change_reason=f"AI suggestion accepted: {suggestion.title}"
                                        )
                                        st.success(f"✓ Rule '{rule_id}' created successfully!")
                                        st.balloons()
                                    else:
                                        st.info(f"ℹ️ Rule '{rule_id}' already exists")
                            except Exception as e:
                                st.error(f"❌ Error creating rule: {str(e)}")
                                st.exception(e)

                with col2:
                    if st.button(f"🔍 Investigate", key=f"investigate_{suggestion.id}"):
                        # Set investigation mode in session state
                        st.session_state.investigating = suggestion.id
                        st.rerun()

                with col3:
                    if st.button(f"❌ Dismiss", key=f"dismiss_{suggestion.id}"):
                        st.session_state.suggestion_engine.record_feedback(
                            suggestion.id,
                            'dismissed'
                        )
                        st.warning("✓ Dismissed")

                # Confidence score
                st.markdown(f"*Confidence: {suggestion.confidence * 100:.0f}%*")

        # Investigation Mode
        if st.session_state.get('investigating'):
            st.markdown("---")
            st.markdown("### 🔍 Investigation Details")

            # Find the suggestion being investigated
            investigating_id = st.session_state.investigating
            investigating_suggestion = next(
                (s for s in st.session_state.ai_suggestions if s.id == investigating_id),
                None
            )

            if investigating_suggestion:
                st.markdown(f"**Investigating:** {investigating_suggestion.title}")

                # Show detailed evidence
                st.markdown("#### Evidence Details")
                evidence = investigating_suggestion.evidence

                # Parse JSON strings back to dicts for display
                import json
                display_evidence = {}
                for key, value in evidence.items():
                    if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                        try:
                            display_evidence[key] = json.loads(value)
                        except:
                            display_evidence[key] = value
                    else:
                        display_evidence[key] = value

                # Display as formatted JSON
                st.json(display_evidence)

                # Load and show affected records if available
                st.markdown("#### Affected Records")
                try:
                    table_name = investigating_suggestion.category.lower()
                    if table_name in ['statistical', 'temporal', 'behavioral']:
                        table_name = 'expenses'  # Default to expenses table

                    data_path = Path(f"data/parquet/{table_name}")
                    if data_path.exists():
                        df = pd.read_parquet(str(data_path))
                        st.dataframe(df.head(100), use_container_width=True)
                        st.caption(f"Showing first 100 records from {table_name} table")
                    else:
                        st.info(f"No data available for table: {table_name}")
                except Exception as e:
                    st.warning(f"Could not load affected records: {str(e)}")

                # Close investigation
                if st.button("← Close Investigation"):
                    st.session_state.investigating = None
                    st.rerun()

# ========================================
# TAB 2: WORKFLOW SUGGESTIONS
# ========================================
with tab2:
    st.markdown("## 🏗️ Workflow Enhancement Suggestions")
    st.markdown("AI-recommended improvements to your audit workflow.")

    # Check prerequisites
    if not st.session_state.get('process_defined', False):
        st.warning("⚠️ Please define a process first to get workflow suggestions!")
        if st.button("← Go to Define Process"):
            st.switch_page("pages/2_📋_Define_Process.py")
        st.stop()

    if st.button("🔍 Analyze My Workflow", use_container_width=True, type="primary"):
        with st.spinner("Analyzing workflow..."):
            # Get current workflow
            from audit_agent.knowledge_graph import KnowledgeGraphManager, ProcessGraph

            kg_db_path = st.session_state.get('kg_db_path', 'data/kg.db')
            with KnowledgeGraphManager(kg_db_path) as kg_manager:
                process_graph = ProcessGraph(kg_manager)

                process_name = st.session_state.process_name
                flow = process_graph.get_process_flow(process_name)

                # Generate suggestions
                data_context = {
                    'has_amount_column': True,  # TODO: Get from actual data
                    'tables': ['expenses', 'approvals', 'payments']
                }

                workflow_suggestions = st.session_state.suggestion_engine.suggest_missing_steps(
                    flow['steps'],
                    data_context
                )

                st.session_state.workflow_suggestions = workflow_suggestions

            st.success(f"✅ Found {len(workflow_suggestions)} workflow improvements!")
            st.rerun()

    # Display workflow suggestions
    if 'workflow_suggestions' in st.session_state:
        suggestions = st.session_state.workflow_suggestions

        if not suggestions:
            st.success("🎉 Your workflow follows best practices! No improvements needed.")
        else:
            for suggestion in suggestions:
                priority_icon = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}

                with st.expander(
                    f"{priority_icon.get(suggestion.priority)} **{suggestion.title}**",
                    expanded=True
                ):
                    st.markdown(suggestion.description)

                    st.markdown("**Why This Helps:**")
                    st.info(suggestion.reasoning)

                    st.markdown("**Proposed Change:**")
                    action = suggestion.suggested_action

                    if action['type'] == 'add_workflow_step':
                        st.code(f"""
New Step: {action['step_name']}
Position: After '{action.get('insert_after', 'start')}'
Rules: {', '.join(action.get('rules_to_apply', []))}
                        """)

                    elif action['type'] == 'add_conditional_branch':
                        st.code(f"""
Condition: IF {action['condition']}
Then: {action['branch_name']}
Additional Approvers: {action.get('additional_approvers', 1)}
                        """)

                    col1, col2 = st.columns(2)

                    with col1:
                        if st.button("✅ Add to Workflow", key=f"add_{suggestion.id}"):
                            # Record feedback
                            st.session_state.suggestion_engine.record_feedback(
                                suggestion.id,
                                'accepted'
                            )

                            # Actually add the workflow step
                            from audit_agent.knowledge_graph import KnowledgeGraphManager, ProcessGraph

                            try:
                                kg_db_path = st.session_state.get('kg_db_path', 'data/kg.db')
                                with KnowledgeGraphManager(kg_db_path) as kg_manager:
                                    process_graph = ProcessGraph(kg_manager)

                                    process_name = st.session_state.process_name
                                    process_id = process_graph.get_process_by_name(process_name)

                                    if action['type'] == 'add_workflow_step':
                                        # Get current max sequence order
                                        flow = process_graph.get_process_flow(process_name)
                                        max_order = max(s['sequence_order'] for s in flow['steps']) if flow['steps'] else 0

                                        # Add new step
                                        process_graph.add_process_step(
                                            process_type_id=process_id,
                                            step_name=action['step_name'],
                                            sequence_order=max_order + 1,
                                            required_table=action.get('table', None),
                                            expected_duration_minutes=action.get('duration_minutes', 0)
                                        )

                                        st.success(f"✓ Step '{action['step_name']}' added to workflow!")
                                        st.balloons()
                                    else:
                                        st.info("✓ Workflow enhancement recorded! (Advanced features coming soon)")
                            except Exception as e:
                                st.error(f"❌ Error adding step: {str(e)}")
                                st.exception(e)

                    with col2:
                        if st.button("❌ Not Needed", key=f"skip_{suggestion.id}"):
                            st.warning("✓ Skipped")

                    st.markdown(f"*Confidence: {suggestion.confidence * 100:.0f}%*")

# ========================================
# TAB 3: TEMPLATES
# ========================================
with tab3:
    st.markdown("## 📚 Pre-Built Workflow Templates")
    st.markdown("Industry-standard templates you can adopt.")

    # Get all templates
    templates = st.session_state.template_library.get_all_templates()

    # Auto-match template
    if st.session_state.get('data_uploaded'):
        st.markdown("### 🎯 Best Match for Your Data")

        if st.button("🔍 Find Best Template", use_container_width=True):
            with st.spinner("Analyzing your data to find best template match..."):
                data_context = {
                    'tables': ['expenses', 'employees', 'approvals'],
                    'columns': ['expense_id', 'employee_id', 'amount', 'transaction_date'],
                    'row_count': 10000  # TODO: Get actual count
                }

                best_match = st.session_state.template_library.match_template(data_context)

                if best_match:
                    st.session_state.best_template_match = best_match
                    st.rerun()

        if 'best_template_match' in st.session_state:
            template = st.session_state.best_template_match

            st.success(f"✨ **Best Match:** {template.name} ({template.match_confidence * 100:.0f}% confidence)")

            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"**Description:** {template.description}")
                st.markdown(f"**Industry:** {template.industry.title()}")
                st.markdown(f"**Steps:** {len(template.steps)}")
                st.markdown(f"**Rules:** {len(template.rules)}")
                st.markdown(f"**Used by:** {template.use_count:,} organizations")

            with col2:
                st.markdown("**Compliance:**")
                for std in template.compliance_standards:
                    st.markdown(f"- ✓ {std}")

            if st.button("✅ Use This Template", use_container_width=True, type="primary"):
                st.success("✓ Template will be applied to your workflow!")
                # TODO: Actually apply template
                st.balloons()

            st.markdown("---")

    # Show all templates
    st.markdown("### 📋 All Available Templates")

    for template in templates:
        with st.expander(f"**{template.name}** ({template.use_count:,} users)"):
            st.markdown(template.description)

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Workflow Steps:**")
                for step in template.steps:
                    st.markdown(f"{step['sequence']}. {step['name']} - *{step['description']}*")

            with col2:
                st.markdown("**Included Rules:**")
                for rule in template.rules[:5]:
                    st.markdown(f"- {rule['name']} ({rule['severity']})")
                if len(template.rules) > 5:
                    st.markdown(f"*...and {len(template.rules) - 5} more*")

            if st.button("Use Template", key=f"use_{template.id}"):
                st.info("Template will be applied to your workflow")
                # TODO: Apply template

# Summary panel
if st.session_state.ai_analysis_done:
    st.markdown("---")
    st.markdown("## 📊 AI Assistant Summary")

    col1, col2, col3 = st.columns(3)

    with col1:
        total_suggestions = len(st.session_state.ai_suggestions)
        st.metric("Total Insights", total_suggestions)

    with col2:
        critical_count = sum(
            1 for s in st.session_state.ai_suggestions
            if s.priority == 'critical'
        )
        st.metric("Critical Issues", critical_count, delta="Immediate action needed" if critical_count > 0 else None)

    with col3:
        avg_confidence = sum(s.confidence for s in st.session_state.ai_suggestions) / len(st.session_state.ai_suggestions) if st.session_state.ai_suggestions else 0
        st.metric("Avg Confidence", f"{avg_confidence * 100:.0f}%")
