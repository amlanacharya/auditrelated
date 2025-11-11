"""
Page 7: Relation Visualization

Interactive network visualization of all relation types in the knowledge graph
"""

import streamlit as st
import sys
from pathlib import Path
import networkx as nx
from pyvis.network import Network
import tempfile
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from audit_agent.knowledge_graph import (
    KnowledgeGraphManager,
    ProcessGraph,
    EntityGraph,
    TableGraph,
    ViolationGraph
)

st.set_page_config(page_title="Relation Visualization", page_icon="🔗", layout="wide")

st.title("🔗 Relation Visualization")
st.markdown("Interactive network visualization of knowledge graph relations")

# Check if KG is initialized
if not st.session_state.get('kg_initialized', False):
    st.warning("⚠️ Knowledge Graph not initialized. Please upload data first!")
    if st.button("← Go to Upload Data"):
        st.switch_page("pages/1_📤_Upload_Data.py")
    st.stop()

# Initialize KG
kg_path = Path("data/kg.db")
kg = KnowledgeGraphManager(str(kg_path))

# Graph type selector
st.sidebar.markdown("## Select Graph Type")
graph_type = st.sidebar.radio(
    "Choose a relation type to visualize:",
    ["Process Flow", "Entity Hierarchy", "Table Dependencies", "Rule Dependencies"]
)

# Layout options
st.sidebar.markdown("## Layout Settings")
layout = st.sidebar.selectbox(
    "Layout Algorithm",
    ["hierarchical", "force_atlas_2based", "barnes_hut", "circular", "spiral"]
)

physics = st.sidebar.checkbox("Enable Physics", value=True)
show_edge_labels = st.sidebar.checkbox("Show Edge Labels", value=True)


def create_process_flow_graph():
    """Create network graph for process flows"""
    st.markdown("### 📊 Process Flow Graph")
    st.markdown("Visualizes business process workflows with steps and transitions")

    # Get process types
    conn = kg.storage.get_connection()
    cursor = conn.execute("SELECT id, name, description FROM process_types")
    process_types = cursor.fetchall()

    if not process_types:
        st.info("No process flows defined yet. Define a process in the 'Define Process' page.")
        return

    # Let user select a process
    process_options = {p['name']: p['id'] for p in process_types}
    selected_process = st.selectbox("Select Process", list(process_options.keys()))

    if selected_process:
        process_id = process_options[selected_process]

        # Get process details
        cursor = conn.execute(
            "SELECT * FROM process_types WHERE id = ?", (process_id,)
        )
        process = cursor.fetchone()

        # Get steps
        cursor = conn.execute(
            "SELECT id, step_number, name, description FROM process_steps WHERE process_type_id = ? ORDER BY step_number",
            (process_id,)
        )
        steps = cursor.fetchall()

        # Get transitions
        cursor = conn.execute(
            """
            SELECT pt.*,
                   from_step.name as from_step_name,
                   to_step.name as to_step_name
            FROM process_transitions pt
            LEFT JOIN process_steps from_step ON pt.from_step_id = from_step.id
            LEFT JOIN process_steps to_step ON pt.to_step_id = to_step.id
            WHERE pt.process_type_id = ?
            """,
            (process_id,)
        )
        transitions = cursor.fetchall()

        # Create NetworkX graph
        G = nx.DiGraph()

        # Add nodes (steps)
        for step in steps:
            G.add_node(
                step['id'],
                label=f"Step {step['step_number']}\n{step['name']}",
                title=step['description'] or step['name'],
                color='#97C2FC',
                shape='box',
                size=25
            )

        # Add edges (transitions)
        for trans in transitions:
            if trans['from_step_id'] and trans['to_step_id']:
                edge_label = ""
                if trans['condition']:
                    edge_label = f"Condition: {trans['condition']}"

                G.add_edge(
                    trans['from_step_id'],
                    trans['to_step_id'],
                    label=edge_label if show_edge_labels else "",
                    title=edge_label,
                    arrows='to'
                )

        # Create PyVis network
        net = Network(height="600px", width="100%", directed=True, notebook=False)
        net.from_nx(G)

        # Configure layout
        if layout == "hierarchical":
            net.set_options("""
            {
              "layout": {
                "hierarchical": {
                  "enabled": true,
                  "direction": "LR",
                  "sortMethod": "directed"
                }
              },
              "physics": {
                "enabled": """ + str(physics).lower() + """
              },
              "edges": {
                "arrows": "to",
                "smooth": {"type": "cubicBezier"}
              }
            }
            """)
        else:
            net.set_options(f"""
            {{
              "physics": {{
                "enabled": {str(physics).lower()}
              }},
              "edges": {{
                "arrows": "to"
              }}
            }}
            """)

        # Save and display
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w') as f:
            net.save_graph(f.name)
            with open(f.name, 'r') as f:
                html_content = f.read()

        components.html(html_content, height=650)

        # Show statistics
        st.markdown("#### Graph Statistics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Steps", len(steps))
        with col2:
            st.metric("Total Transitions", len(transitions))
        with col3:
            st.metric("Complexity", f"{len(transitions)/max(len(steps), 1):.2f}")


def create_entity_hierarchy_graph():
    """Create network graph for entity hierarchies"""
    st.markdown("### 👥 Entity Hierarchy Graph")
    st.markdown("Visualizes entity relationships including reporting structures and approval authorities")

    conn = kg.storage.get_connection()

    # Get entity types
    cursor = conn.execute("SELECT DISTINCT entity_type FROM entity_types")
    entity_types = [row['entity_type'] for row in cursor.fetchall()]

    if not entity_types:
        st.info("No entities defined yet. Upload data to populate the entity graph.")
        return

    # Get relationships
    cursor = conn.execute(
        """
        SELECT er.*,
               parent.entity_name as parent_name,
               child.entity_name as child_name,
               parent.entity_type as parent_type,
               child.entity_type as child_type
        FROM entity_relationships er
        JOIN entity_types parent ON er.parent_entity_id = parent.id
        JOIN entity_types child ON er.child_entity_id = child.id
        """
    )
    relationships = cursor.fetchall()

    # Get approval authorities
    cursor = conn.execute(
        """
        SELECT aa.*,
               et.entity_name,
               et.entity_type
        FROM approval_authorities aa
        JOIN entity_types et ON aa.entity_id = et.id
        WHERE aa.effective_to IS NULL OR aa.effective_to >= date('now')
        """
    )
    authorities = cursor.fetchall()

    # Create NetworkX graph
    G = nx.DiGraph()

    # Track entities
    entities = {}

    # Add nodes from relationships
    for rel in relationships:
        if rel['parent_entity_id'] not in entities:
            entities[rel['parent_entity_id']] = {
                'name': rel['parent_name'],
                'type': rel['parent_type']
            }
        if rel['child_entity_id'] not in entities:
            entities[rel['child_entity_id']] = {
                'name': rel['child_name'],
                'type': rel['child_type']
            }

    # Add nodes
    color_map = {
        'employee': '#97C2FC',
        'manager': '#FFA807',
        'vendor': '#FB7E81',
        'department': '#7BE141'
    }

    for entity_id, entity_info in entities.items():
        color = color_map.get(entity_info['type'].lower(), '#CCCCCC')
        G.add_node(
            entity_id,
            label=entity_info['name'],
            title=f"{entity_info['type']}: {entity_info['name']}",
            color=color,
            shape='dot',
            size=20
        )

    # Add edges from relationships
    for rel in relationships:
        label = rel['relationship_type']
        if show_edge_labels:
            G.add_edge(
                rel['parent_entity_id'],
                rel['child_entity_id'],
                label=label,
                title=label,
                arrows='to'
            )
        else:
            G.add_edge(
                rel['parent_entity_id'],
                rel['child_entity_id'],
                title=label,
                arrows='to'
            )

    if len(G.nodes()) == 0:
        st.info("No entity relationships found.")
        return

    # Create PyVis network
    net = Network(height="600px", width="100%", directed=True, notebook=False)
    net.from_nx(G)

    # Configure layout
    if layout == "hierarchical":
        net.set_options("""
        {
          "layout": {
            "hierarchical": {
              "enabled": true,
              "direction": "UD",
              "sortMethod": "directed"
            }
          },
          "physics": {
            "enabled": """ + str(physics).lower() + """
          },
          "edges": {
            "arrows": "to"
          }
        }
        """)
    else:
        net.set_options(f"""
        {{
          "physics": {{
            "enabled": {str(physics).lower()}
          }},
          "edges": {{
            "arrows": "to"
          }}
        }}
        """)

    # Save and display
    with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w') as f:
        net.save_graph(f.name)
        with open(f.name, 'r') as f:
            html_content = f.read()

    components.html(html_content, height=650)

    # Show statistics
    st.markdown("#### Graph Statistics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Entities", len(G.nodes()))
    with col2:
        st.metric("Total Relationships", len(G.edges()))
    with col3:
        st.metric("Entity Types", len(entity_types))

    # Show approval authorities
    if authorities:
        st.markdown("#### Approval Authorities")
        auth_data = []
        for auth in authorities:
            auth_data.append({
                "Entity": auth['entity_name'],
                "Type": auth['entity_type'],
                "Max Amount": f"${auth['max_amount']:,.2f}" if auth['max_amount'] else "N/A",
                "Effective From": auth['effective_from']
            })
        st.dataframe(auth_data, use_container_width=True)


def create_table_dependency_graph():
    """Create network graph for table dependencies"""
    st.markdown("### 🗄️ Table Dependency Graph")
    st.markdown("Visualizes database schema relationships and foreign key connections")

    conn = kg.storage.get_connection()

    # Get all tables
    cursor = conn.execute("SELECT DISTINCT table_name FROM table_schemas")
    tables = [row['table_name'] for row in cursor.fetchall()]

    if not tables:
        st.info("No table schemas defined yet. Upload data to populate the table graph.")
        return

    # Get table relationships
    cursor = conn.execute(
        """
        SELECT
            from_table,
            from_column,
            to_table,
            to_column,
            relationship_type,
            confidence_score
        FROM table_relationships
        """
    )
    relationships = cursor.fetchall()

    if not relationships:
        st.info("No table relationships detected yet.")
        return

    # Create NetworkX graph
    G = nx.Graph()  # Undirected for table relationships

    # Add nodes (tables)
    for table in tables:
        # Count columns
        cursor = conn.execute(
            "SELECT COUNT(*) as col_count FROM table_schemas WHERE table_name = ?",
            (table,)
        )
        col_count = cursor.fetchone()['col_count']

        G.add_node(
            table,
            label=table,
            title=f"{table}\n({col_count} columns)",
            color='#97C2FC',
            shape='box',
            size=20 + col_count * 2  # Size based on column count
        )

    # Add edges (relationships)
    for rel in relationships:
        edge_label = ""
        if show_edge_labels:
            edge_label = f"{rel['from_column']} → {rel['to_column']}"

        confidence = rel.get('confidence_score', 1.0)
        edge_color = '#2B7CE9' if confidence > 0.8 else '#FFA807' if confidence > 0.5 else '#FB7E81'

        G.add_edge(
            rel['from_table'],
            rel['to_table'],
            label=edge_label,
            title=f"{rel['relationship_type']}\nConfidence: {confidence:.2f}\n{rel['from_column']} → {rel['to_column']}",
            color=edge_color,
            width=1 + confidence * 3
        )

    # Create PyVis network
    net = Network(height="600px", width="100%", directed=False, notebook=False)
    net.from_nx(G)

    # Configure layout
    net.set_options(f"""
    {{
      "physics": {{
        "enabled": {str(physics).lower()},
        "solver": "forceAtlas2Based"
      }}
    }}
    """)

    # Save and display
    with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w') as f:
        net.save_graph(f.name)
        with open(f.name, 'r') as f:
            html_content = f.read()

    components.html(html_content, height=650)

    # Show statistics
    st.markdown("#### Graph Statistics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Tables", len(tables))
    with col2:
        st.metric("Total Relationships", len(relationships))
    with col3:
        avg_confidence = sum(r.get('confidence_score', 1.0) for r in relationships) / max(len(relationships), 1)
        st.metric("Avg Confidence", f"{avg_confidence:.2f}")
    with col4:
        high_conf = sum(1 for r in relationships if r.get('confidence_score', 1.0) > 0.8)
        st.metric("High Confidence", high_conf)


def create_rule_dependency_graph():
    """Create network graph for rule dependencies"""
    st.markdown("### ⚖️ Rule Dependency Graph")
    st.markdown("Visualizes violation detection rule dependencies and execution order")

    conn = kg.storage.get_connection()

    # Get active rules
    cursor = conn.execute(
        """
        SELECT
            id,
            rule_name,
            rule_type,
            severity,
            description,
            version
        FROM violation_rules
        WHERE effective_to IS NULL OR effective_to >= date('now')
        ORDER BY rule_name
        """
    )
    rules = cursor.fetchall()

    if not rules:
        st.info("No rules defined yet. Define rules in the 'Build Rules' page.")
        return

    # Get rule dependencies
    cursor = conn.execute(
        """
        SELECT
            rd.*,
            r1.rule_name as parent_rule,
            r2.rule_name as dependent_rule
        FROM rule_dependencies rd
        JOIN violation_rules r1 ON rd.parent_rule_id = r1.id
        JOIN violation_rules r2 ON rd.dependent_rule_id = r2.id
        """
    )
    dependencies = cursor.fetchall()

    # Create NetworkX graph
    G = nx.DiGraph()

    # Color map for severity
    severity_colors = {
        'critical': '#FB7E81',
        'high': '#FFA807',
        'medium': '#FFEB3B',
        'low': '#7BE141'
    }

    # Add nodes (rules)
    for rule in rules:
        color = severity_colors.get(rule['severity'].lower(), '#CCCCCC')
        G.add_node(
            rule['id'],
            label=rule['rule_name'],
            title=f"{rule['rule_name']}\nType: {rule['rule_type']}\nSeverity: {rule['severity']}\n{rule['description'][:100]}...",
            color=color,
            shape='box',
            size=25,
            borderWidth=2
        )

    # Add edges (dependencies)
    for dep in dependencies:
        label = ""
        if show_edge_labels and dep['execution_order']:
            label = f"Order: {dep['execution_order']}"

        G.add_edge(
            dep['parent_rule_id'],
            dep['dependent_rule_id'],
            label=label,
            title=f"Execution Order: {dep['execution_order']}",
            arrows='to'
        )

    # Create PyVis network
    net = Network(height="600px", width="100%", directed=True, notebook=False)
    net.from_nx(G)

    # Configure layout
    if layout == "hierarchical":
        net.set_options("""
        {
          "layout": {
            "hierarchical": {
              "enabled": true,
              "direction": "UD",
              "sortMethod": "directed"
            }
          },
          "physics": {
            "enabled": """ + str(physics).lower() + """
          },
          "edges": {
            "arrows": "to"
          }
        }
        """)
    else:
        net.set_options(f"""
        {{
          "physics": {{
            "enabled": {str(physics).lower()}
          }},
          "edges": {{
            "arrows": "to"
          }}
        }}
        """)

    # Save and display
    with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w') as f:
        net.save_graph(f.name)
        with open(f.name, 'r') as f:
            html_content = f.read()

    components.html(html_content, height=650)

    # Show statistics
    st.markdown("#### Graph Statistics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Rules", len(rules))
    with col2:
        st.metric("Dependencies", len(dependencies))
    with col3:
        isolated = sum(1 for node in G.nodes() if G.degree(node) == 0)
        st.metric("Isolated Rules", isolated)

    # Show rules table
    st.markdown("#### Rule Details")
    rule_data = []
    for rule in rules:
        rule_data.append({
            "Rule Name": rule['rule_name'],
            "Type": rule['rule_type'],
            "Severity": rule['severity'],
            "Version": rule['version']
        })
    st.dataframe(rule_data, use_container_width=True)


# Main content
st.markdown("---")

# Render selected graph
if graph_type == "Process Flow":
    create_process_flow_graph()
elif graph_type == "Entity Hierarchy":
    create_entity_hierarchy_graph()
elif graph_type == "Table Dependencies":
    create_table_dependency_graph()
elif graph_type == "Rule Dependencies":
    create_rule_dependency_graph()

# Help section
with st.expander("ℹ️ Help"):
    st.markdown("""
    ### Graph Types

    **Process Flow**: Shows the sequence of steps in business processes with transitions and conditions.

    **Entity Hierarchy**: Displays organizational structures, reporting relationships, and approval authorities.

    **Table Dependencies**: Visualizes database schema relationships through foreign keys and column mappings.

    **Rule Dependencies**: Shows how violation detection rules depend on each other for execution.

    ### Interaction

    - **Drag nodes** to rearrange the graph
    - **Scroll** to zoom in/out
    - **Hover** over nodes and edges for detailed information
    - **Click and drag** on empty space to pan
    - Use the **sidebar** to change layout and enable/disable physics

    ### Layout Algorithms

    - **Hierarchical**: Organizes nodes in a tree-like structure (best for processes and rules)
    - **Force Atlas 2**: Physics-based layout with attractive and repulsive forces
    - **Barnes Hut**: Optimized physics simulation for large graphs
    - **Circular**: Arranges nodes in a circle
    - **Spiral**: Creates a spiral arrangement
    """)
