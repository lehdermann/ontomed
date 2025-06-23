import os
import sys
import traceback
import logging

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("visualizer")

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import streamlit as st
import networkx as nx
from pyvis.network import Network
import sys
import os

# Import shared layout components
from components.shared_layout_new import setup_shared_layout_content, render_chat_ui, create_three_column_layout, check_rerun
from components.chat.chat_ui_new import ChatUI

# Add the dashboard directory to the path to allow imports
dashboard_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if dashboard_dir not in sys.path:
    sys.path.append(dashboard_dir)

from utils.api_client import APIClient
from utils.embedding_manager import SimpleEmbeddingManager

# Initialize API client
api_client = APIClient()

# Initialize simplified embedding manager
embedding_manager = SimpleEmbeddingManager()

# Function to handle chat messages
def handle_user_message(message: str) -> None:
    """Handle user message in the chat.
    
    Args:
        message: The message from the user
    """
    try:
        # Usar o cliente API global
        global api_client
        
        # Processar a mensagem usando o método process_chat_message do APIClient
        logger.info(f"Processando mensagem do usuário: {message}")
        chat_response = api_client.process_chat_message(message)
        
        # Extrair a resposta e a intenção identificada
        response_text = chat_response.get('response', "Desculpe, não consegui processar sua mensagem.")
        intent = chat_response.get('intent', "outro")
        
        # Registrar a intenção identificada para fins de depuração
        logger.info(f"Intenção identificada: {intent}")
        
        # Adicionar a resposta do bot ao histórico de chat
        if 'chat_messages' in st.session_state:
            st.session_state.chat_messages.append({"is_user": False, "content": response_text})
        
    except Exception as e:
        error_msg = f"Desculpe, ocorreu um erro ao processar sua mensagem: {str(e)}"
        if 'chat_messages' in st.session_state:
            st.session_state.chat_messages.append({"is_user": False, "content": error_msg})
        logger.error(f"Error handling user message: {e}", exc_info=True)

def main():
    """Main function of the graph visualization page."""
    # Setup shared layout
    page = setup_shared_layout_content()
    
    # Page title
    st.title("Graph Visualizer")
    
    # Debug mode
    debug_mode = st.sidebar.checkbox("Debug Mode", value=True)
    
    # Sidebar - Filters
    st.sidebar.header("Filters")
    concept_type = st.sidebar.selectbox("Concept Type", ["All", "Diagnosis", "Treatment", "Prevention"])
    similarity_threshold = st.sidebar.slider(
        "Similarity Threshold",
        min_value=0.0,
        max_value=1.0,
        value=0.5,  # Default value reduced to 0.5 to capture more relationships
        step=0.1
    )
    
    # Initialize session variables if they don't exist
    if 'selected_concept_option' not in st.session_state:
        st.session_state.selected_concept_option = "Select a Base Concept"
    
    # Initialization log
    logger.debug("Starting Graph Visualizer page")
    if debug_mode:
        st.sidebar.write("**Session state:**")
        st.sidebar.write(st.session_state)
    
    # Main content
    st.header("Graph Visualization")
    
    # Load all concepts
    with st.spinner("Loading concepts..."):
        try:
            all_concepts_data = api_client.get_concepts()
            
            # Check if we have concepts
            if not all_concepts_data:
                st.error("Unable to load concepts. Check the connection with the API.")
                return
            
            # Extract list of concepts
            all_concepts = all_concepts_data
            
            # Filter concepts by type if necessary
            if concept_type != "All":
                # Implement type filter
                pass
                
            # Create list of options for the selectbox
            concept_options = []
            for c in all_concepts:
                # Get the concept label, or extract from ID if the label is None
                label = c.get('label')
                if label is None or label == "":
                    # Extract a readable name from the ID
                    if "#" in c['id']:
                        label = c['id'].split("#")[-1]
                    elif "/" in c['id']:
                        label = c['id'].split("/")[-1]
                    else:
                        label = c['id']
                
                concept_options.append(f"{label} ({c['id']})")
            
            # Add empty option at the beginning
            concept_options.insert(0, "Select a Base Concept")
            
            # Dropdown to select the base concept (using session_state to persist the selection)
            selected_concept_option = st.selectbox(
                "Select a Base Concept", 
                concept_options,
                key="selected_concept_option"
            )
            
            # Log of the concept selection
            logger.debug(f"Selected concept: {selected_concept_option}")
            
            # Display debug information if the mode is activated
            if debug_mode:
                st.write("**Debug information:**")
                st.write(f"Selected concept: {selected_concept_option}")
                st.write(f"Number of loaded concepts: {len(all_concepts)}")
                if selected_concept_option != "Select a Base Concept":
                    selected_concept_id = selected_concept_option.split("(")[-1].split(")")[0]
                    st.write(f"Selected concept ID: {selected_concept_id}")
                    # Check if the concept exists in the list
                    concept_exists = any(c["id"] == selected_concept_id for c in all_concepts)
                    st.write(f"Concept exists in the list: {concept_exists}")
                    if concept_exists:
                        # Show the first fields of the concept
                        concept = next((c for c in all_concepts if c["id"] == selected_concept_id), None)
                        st.write("First fields of the concept:")
                        st.json({k: v for i, (k, v) in enumerate(concept.items()) if i < 5})
            
        except Exception as e:
            st.error(f"Error loading concepts: {str(e)}")
            return
    
    # Process the concept selection
    selected_concept = None
    if selected_concept_option != "Select a Base Concept":
        try:
            # Extract the concept ID from the selected option
            selected_concept_id = selected_concept_option.split("(")[-1].split(")")[0]
            
            # Find the corresponding concept
            selected_concept = next((c for c in all_concepts if c["id"] == selected_concept_id), None)
            
            if not selected_concept:
                st.error(f"Could not find concept with ID: {selected_concept_id}")
                st.info("Try selecting another concept or reload the page.")
        except Exception as e:
            st.error(f"Error processing concept selection: {str(e)}")
            st.info("Try selecting another concept or reload the page.")
            import traceback
            st.expander("Error details").code(traceback.format_exc())
    
    if selected_concept:
        logger.debug(f"Starting graph generation for concept: {selected_concept.get('label', 'No label')} ({selected_concept.get('id', 'No ID')})")
        
        if debug_mode:
            st.write("**Starting graph generation**")
            st.write(f"Concept: {selected_concept.get('label', 'No label')} ({selected_concept.get('id', 'No ID')})")
        
        # Create empty graph
        G = nx.Graph()
        logger.debug("Empty graph created")
        
        # Add node for the selected concept with metadata
        # Get the concept label, or extract from ID if the label is None/NULL
        concept_label = selected_concept.get('label')
        if concept_label is None or concept_label == "NULL" or concept_label == "":
            # Extract a readable name from the ID
            concept_id = selected_concept['id']
            if "#" in concept_id:
                concept_label = concept_id.split("#")[-1]
            elif "/" in concept_id:
                concept_label = concept_id.split("/")[-1]
            else:
                concept_label = concept_id
            
            logger.debug(f"Null or empty label, using label extracted from ID: {concept_label}")
            if debug_mode:
                st.write(f"**Warning:** Null or empty label, using label extracted from ID: {concept_label}")
        
        # Prepare metadata for the tooltip
        node_title = f"<div class='tooltip-content'>"
        node_title += f"<div class='tooltip-title'>{concept_label}</div>"
        node_title += f"<div class='tooltip-line'>ID: {selected_concept['id']}</div>"
        
        # Add description if available
        if "description" in selected_concept and selected_concept['description']:
            node_title += f"<div class='tooltip-line'>Description: {selected_concept['description']}</div>"
        
        # Add other metadata if available
        for key, value in selected_concept.items():
            # Handle simple metadata
            if key not in ["id", "label", "description", "annotations"] and not isinstance(value, (list, dict)) and value:
                node_title += f"<div class='tooltip-line'>{key}: {value}</div>"
        
        # Add annotations if available
        if "annotations" in selected_concept and selected_concept["annotations"]:
            node_title += f"<div class='tooltip-section'>Annotations:</div>"
            annotations = selected_concept["annotations"]
            
            # Check if annotations is a dictionary or list
            if isinstance(annotations, dict):
                for anno_key, anno_value in annotations.items():
                    if anno_value:  # Check if the value is not empty
                        # Format annotation value (can be string, list or dictionary)
                        if isinstance(anno_value, list):
                            # If it's a list, show each item
                            for item in anno_value[:3]:  # Limit to 3 items to not overload the tooltip
                                node_title += f"<div class='tooltip-line'>{anno_key}: {item}</div>"
                            if len(anno_value) > 3:
                                node_title += f"<div class='tooltip-line'>... and {len(anno_value) - 3} more values</div>"
                        else:
                            # If it's a simple value
                            node_title += f"<div class='tooltip-line'>{anno_key}: {anno_value}</div>"
            elif isinstance(annotations, list):
                # If annotations is a list of dictionaries
                for i, anno in enumerate(annotations[:3]):  # Limit to 3 annotations
                    if isinstance(anno, dict):
                        for anno_key, anno_value in anno.items():
                            if anno_value:
                                node_title += f"<div class='tooltip-line'>{anno_key}: {anno_value}</div>"
                    else:
                        node_title += f"<div class='tooltip-line'>Annotation {i+1}: {anno}</div>"
                if len(annotations) > 3:
                    node_title += f"<div class='tooltip-line'>... and {len(annotations) - 3} more annotations</div>"
        
        node_title += "</div>"
        
        G.add_node(selected_concept["id"], 
                  label=concept_label,
                  title=node_title,  # Tooltip with HTML formatted metadata
                  color="#00ff00",
                  size=20)
        
        # Get relationships
        all_relationships = []
        
        if debug_mode:
            st.write("**Getting relationships**")
        
        # Get relationships from the API
        try:
            logger.debug(f"Getting relationships from the API for concept: {selected_concept['id']}")
            
            # Get relationships for the selected concept
            relationships = api_client.get_relationships(selected_concept["id"])
            
            logger.debug(f"Relationships obtained from the API: {len(relationships) if isinstance(relationships, list) else 'Not a list'}")
            if debug_mode:
                st.write(f"Relationships obtained from the API: {len(relationships) if isinstance(relationships, list) else 'Not a list'}")
                if isinstance(relationships, list) and relationships:
                    st.write("Relationship example:")
                    st.json(relationships[0])
            
            # Check if relationships is a list
            if not isinstance(relationships, list):
                # Convert to list if it's a dictionary with 'relationships' key
                if isinstance(relationships, dict) and 'relationships' in relationships:
                    relationships = relationships.get('relationships', [])
                else:
                    # Otherwise, use an empty list
                    st.warning("Unexpected format of relationships. Using empty list.")
                    relationships = []
            
            # Process relationships from the API
            api_relationships = []
            for rel in relationships:
                # Check if the relationship is valid
                if not isinstance(rel, dict):
                    continue
                
                # Extract relationship information
                rel_type = rel.get("type", "")
                rel_target = rel.get("target", "")
                rel_label = rel.get("label", "")
                
                # Skip invalid relationships
                if not rel_type or not rel_target:
                    continue
                
                # Create relationship object
                api_rel = {
                    "source": selected_concept["id"],
                    "target": rel_target,
                    "type": rel_type,
                    "label": rel_label,
                    "title": rel_type,
                    "is_api": True
                }
                api_relationships.append(api_rel)
            
            # Get semantic relationships
            try:
                # Generate semantic relationships
                other_concepts = [c for c in all_concepts if c["id"] != selected_concept["id"]]
                semantic_relationships = embedding_manager.generate_semantic_relationships(
                    selected_concept,
                    other_concepts
                )
                
                # Filter semantic relationships by threshold
                semantic_relationships = [
                    r for r in semantic_relationships 
                    if r["similarity"] >= similarity_threshold
                ]
                
            except Exception as e:
                st.error(f"Error generating semantic relationships: {str(e)}")
                semantic_relationships = []
            
            # Combine relationships
            all_relationships = api_relationships + semantic_relationships
        
        except Exception as e:
            st.error(f"Error getting relationships: {str(e)}")
            all_relationships = []
        
        # Check if we have relationships
        if not all_relationships:
            st.warning("No relationships found for this concept. Displaying only the selected concept node.")
            
            # Add at least one additional node to ensure the graph is displayed
            dummy_node_id = f"{selected_concept['id']}_info"
            G.add_node(dummy_node_id, 
                      label="Info",
                      title="Additional information about the concept",
                      color="#cccccc",
                      size=10)
            
            # Add an edge to the dummy node
            G.add_edge(selected_concept["id"], dummy_node_id,
                      title="Additional information",
                      color="#cccccc")
        
        # Add relationships to the graph
        for rel in all_relationships:
            source = rel.get("source", "")
            target = rel.get("target", "")
            
            # Skip invalid relationships
            if not source or not target:
                continue
            
            # Add target node (if it's not the selected concept)
            if target != selected_concept["id"]:
                # Check if the target is a URI or simple string
                if "#" in target:
                    node_label = target.split("#")[-1]
                elif "/" in target:
                    node_label = target.split("/")[-1]
                else:
                    node_label = target
                
                # Find the complete concept to get metadata
                target_concept = next((c for c in all_concepts if c["id"] == target), None)
                
                # Prepare metadata for the tooltip using CSS classes
                node_title = f"<div class='tooltip-content'>"
                node_title += f"<div class='tooltip-title'>{node_label}</div>"
                node_title += f"<div class='tooltip-line'>ID: {target}</div>"
                
                # Add more metadata if the concept was found
                if target_concept:
                    if "description" in target_concept and target_concept['description']:
                        node_title += f"<div class='tooltip-line'>Description: {target_concept['description']}</div>"
                    
                    # Add other available metadata
                    for key, value in target_concept.items():
                        if key not in ["id", "label", "description", "annotations"] and not isinstance(value, (list, dict)) and value:
                            node_title += f"<div class='tooltip-line'>{key}: {value}</div>"
                    
                    # Add annotations if available
                    if "annotations" in target_concept and target_concept["annotations"]:
                        node_title += f"<div class='tooltip-section'>Annotations:</div>"
                        annotations = target_concept["annotations"]
                        
                        # Check if annotations is a dictionary or list
                        if isinstance(annotations, dict):
                            for anno_key, anno_value in annotations.items():
                                if anno_value:  # Check if the value is not empty
                                    # Format annotation value (can be string, list or dictionary)
                                    if isinstance(anno_value, list):
                                        # If it's a list, show each item
                                        for item in anno_value[:3]:  # Limit to 3 items to not overload the tooltip
                                            node_title += f"<div class='tooltip-line'>{anno_key}: {item}</div>"
                                        if len(anno_value) > 3:
                                            node_title += f"<div class='tooltip-line'>... and {len(anno_value) - 3} more values</div>"
                                    else:
                                        # If it's a simple value
                                        node_title += f"<div class='tooltip-line'>{anno_key}: {anno_value}</div>"
                        elif isinstance(annotations, list):
                            # If annotations is a list of dictionaries
                            for i, anno in enumerate(annotations[:3]):  # Limitar a 3 anotações
                                if isinstance(anno, dict):
                                    for anno_key, anno_value in anno.items():
                                        if anno_value:
                                            node_title += f"<div class='tooltip-line'>{anno_key}: {anno_value}</div>"
                                else:
                                    node_title += f"<div class='tooltip-line'>Annotation {i+1}: {anno}</div>"
                            if len(annotations) > 3:
                                node_title += f"<div class='tooltip-line'>... and {len(annotations) - 3} more annotations</div>"
                
                node_title += "</div>"
                
                G.add_node(target, 
                          label=node_label,
                          title=node_title,  # Tooltip with metadata
                          color="#0000ff",
                          size=15)
            
            # Add edge with predicate information
            edge_color = "#0000ff"
            
            # Prepare edge title with predicate name
            rel_type = rel.get("type", "")
            rel_label = rel.get("label", "")
            
            # Build edge title using formatted HTML
            edge_title = f"<div class='tooltip-content'>"
            
            if rel_label:
                edge_title += f"<div class='tooltip-title'>Predicate: {rel_label}</div>"
                edge_title += f"<div class='tooltip-line'>Type: {rel_type}</div>"
            else:
                edge_title += f"<div class='tooltip-title'>Type: {rel_type}</div>"
            
            # Add description if available
            if "description" in rel and rel["description"]:
                edge_title += f"<div class='tooltip-line'>Description: {rel['description']}</div>"
            
            # Configure semantic edges with different color
            if rel.get("type") == "SEMANTIC":
                edge_color = "#ff9900"  # Orange for semantic relationships
                
                # Use similarity as edge label for semantic relationships
                edge_label = f"Similarity: {rel.get('similarity', 0):.2f}"
                
                # Título para tooltip (será usado como fallback)
                edge_title = f"Semantic Relationship\nSimilarity: {rel.get('similarity', 0):.2f}"
                if "description" in rel and rel["description"]:
                    edge_title += f"\nDescription: {rel['description']}"
            else:
                # Use predicate name as edge label
                edge_label = rel_label if rel_label else rel_type
                
                # Título para tooltip (será usado como fallback)
                edge_title = f"Type: {rel_type}"
                if rel_label:
                    edge_title += f"\nPredicate: {rel_label}"
                if "description" in rel and rel["description"]:
                    edge_title += f"\nDescription: {rel['description']}"
            
            G.add_edge(source, target,
                      title=edge_title,
                      label=edge_label,
                      font={'size': 10, 'color': '#333333', 'align': 'middle'},
                      color=edge_color)
        
        # Check if the graph has nodes and edges
        if debug_mode:
            st.write(f"Number of nodes in the graph: {len(G.nodes())}")
            st.write(f"Number of edges in the graph: {len(G.edges())}")
            st.write("Nodes in the graph:")
            st.write([node for node in G.nodes()][:5])
        
        # Check if the graph is empty
        if len(G.nodes()) == 0:
            st.error("The graph is empty. There are no nodes to visualize.")
            st.info("Try selecting another concept or check if there are available relationships.")
            return
        
        # Create visualization
        logger.debug("Creating Network object for visualization")
        net = Network(notebook=True, height="750px", width="100%", directed=True, bgcolor="#ffffff", font_color="#000000")
        
        # Configure advanced options to improve graph visualization
        logger.debug("Configuring graph options")
        net.set_options("""
        var options = {
            "nodes": {
                "font": {"size": 16, "face": "Arial"},
                "shape": "dot",
                "size": 25,
                "color": {
                    "border": "#2B7CE9",
                    "background": "#D2E5FF",
                    "highlight": {
                        "border": "#2B7CE9",
                        "background": "#5A9AEF"
                    }
                }
            },
            "edges": {
                "color": {"inherit": false, "color": "#848484"},
                "smooth": {
                    "enabled": true,
                    "type": "dynamic",
                    "roundness": 0.5
                },
                "width": 2,
                "arrows": {
                    "to": {"enabled": true, "scaleFactor": 0.5}
                },
                "font": {
                    "size": 12,
                    "face": "Arial",
                    "color": "#000000",
                    "strokeWidth": 3,
                    "strokeColor": "#ffffff",
                    "align": "middle"
                }
            },
            "interaction": {
                "hover": true,
                "hideEdgesOnDrag": false,
                "multiselect": true,
                "navigationButtons": true,
                "keyboard": true
            },
            "physics": {
                "enabled": true,
                "solver": "forceAtlas2Based",
                "forceAtlas2Based": {
                    "gravitationalConstant": -50,
                    "centralGravity": 0.01,
                    "springLength": 150,
                    "springConstant": 0.05,
                    "damping": 0.4
                },
                "stabilization": {
                    "enabled": true,
                    "iterations": 1000,
                    "updateInterval": 100
                }
            },
            "layout": {
                "improvedLayout": true,
                "hierarchical": {
                    "enabled": false
                }
            },
            "manipulation": {"enabled": false}
        }
        """)
        
        # Custom CSS for tooltips
        tooltip_css = """
        <style>
        .tooltip-content {
            font-family: Arial, sans-serif;
            font-size: 14px;
            padding: 8px;
            background-color: #f8f9fa;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            max-width: 300px;
            color: #333;
        }
        .tooltip-title {
            color: #007bff;
            font-weight: bold;
            font-size: 16px;
            margin-bottom: 8px;
            border-bottom: 1px solid #eee;
            padding-bottom: 4px;
        }
        .tooltip-section {
            color: #28a745;
            font-weight: bold;
            font-size: 14px;
            margin-top: 8px;
            margin-bottom: 4px;
            border-top: 1px dotted #ccc;
            padding-top: 4px;
        }
        .tooltip-line {
            margin-bottom: 4px;
            line-height: 1.4;
        }
        .vis-tooltip {
            position: absolute;
            visibility: hidden;
            padding: 5px;
            white-space: normal !important;
            word-wrap: break-word;
            font-family: Arial, sans-serif;
            font-size: 14px;
            color: #000000;
            background-color: #f5f5f5;
            border: 1px solid #808080;
            border-radius: 3px;
            box-shadow: 3px 3px 10px rgba(0, 0, 0, 0.2);
            pointer-events: none;
            z-index: 9999;
            max-width: 350px;
            overflow: auto;
            max-height: 300px;
        }
        </style>
        """
        
        # Improved JavaScript script to ensure HTML tooltips work correctly
        html_script = """
        <script type="text/javascript">
        // Function to create a custom tooltip that renders HTML
        function createCustomTooltip() {
            // Remove existing tooltip if any
            const existingTooltip = document.getElementById('custom-tooltip');
            if (existingTooltip) {
                existingTooltip.remove();
            }
            
            // Create custom tooltip element
            const tooltipDiv = document.createElement('div');
            tooltipDiv.id = 'custom-tooltip';
            tooltipDiv.className = 'vis-tooltip';
            tooltipDiv.style.display = 'none';
            tooltipDiv.style.position = 'absolute';
            tooltipDiv.style.zIndex = '10000';
            tooltipDiv.style.pointerEvents = 'none';
            document.body.appendChild(tooltipDiv);
            
            return tooltipDiv;
        }
        
        // Function to set up custom HTML tooltips
        function setupCustomTooltips() {
            try {
                console.log("Starting custom HTML tooltips configuration");
                
                // Check if vis.js network is available
                const networkContainer = document.querySelector('.vis-network');
                if (!networkContainer) {
                    console.log("Network container not found. Trying again in 500ms...");
                    setTimeout(setupCustomTooltips, 500);
                    return;
                }
                
                // Check if network instance is available
                if (typeof visNetworks === 'undefined' || !visNetworks[0]) {
                    console.log("Network instance not found. Trying again in 500ms...");
                    setTimeout(setupCustomTooltips, 500);
                    return;
                }
                
                // Get network instance
                const network = visNetworks[0];
                window.pyvisNetwork = network; // Expose for debugging
                
                console.log("vis.js network found, configuring HTML tooltips");
                
                // Create custom tooltip
                const tooltipDiv = createCustomTooltip();
                
                // Disable native tooltips
                network.setOptions({
                    interaction: {
                        tooltipDelay: 99999999 // High value to effectively disable
                    }
                });
                
                // Add event handlers for nodes
                network.on("hoverNode", function (params) {
                    const nodeId = params.node;
                    const node = network.body.nodes[nodeId];
                    if (node && node.options && node.options.title) {
                        tooltipDiv.innerHTML = node.options.title;
                        tooltipDiv.style.display = 'block';
                        tooltipDiv.style.left = (params.event.pageX + 10) + 'px';
                        tooltipDiv.style.top = (params.event.pageY + 10) + 'px';
                    }
                });
                
                network.on("blurNode", function () {
                    tooltipDiv.style.display = 'none';
                });
                
                // Add event handlers for edges
                network.on("hoverEdge", function (params) {
                    const edgeId = params.edge;
                    const edge = network.body.edges[edgeId];
                    if (edge && edge.options && edge.options.title) {
                        tooltipDiv.innerHTML = edge.options.title;
                        tooltipDiv.style.display = 'block';
                        tooltipDiv.style.left = (params.event.pageX + 10) + 'px';
                        tooltipDiv.style.top = (params.event.pageY + 10) + 'px';
                    }
                });
                
                network.on("blurEdge", function () {
                    tooltipDiv.style.display = 'none';
                });
                
                // Update tooltip position when moving the mouse
                networkContainer.addEventListener('mousemove', function(event) {
                    if (tooltipDiv.style.display === 'block') {
                        tooltipDiv.style.left = (event.pageX + 10) + 'px';
                        tooltipDiv.style.top = (event.pageY + 10) + 'px';
                    }
                });
                
                console.log("Custom HTML tooltips successfully configured!");
            } catch (error) {
                console.error("Error configuring HTML tooltips:", error);
            }
        }
        
        // Execute when document is loaded
        document.addEventListener('DOMContentLoaded', function() {
            console.log("Document loaded, configuring HTML tooltips...");
            setTimeout(setupCustomTooltips, 1000);
        });
        
        // Check if document is already loaded
        if (document.readyState === 'complete' || document.readyState === 'interactive') {
            console.log("Document already loaded, configuring tooltips immediately...");
            setTimeout(setupCustomTooltips, 500);
        }
        </script>
        """
        
        # We no longer need the network exposure script, as this is already being done in the main script
        
        # Add NetworkX graph to Network object
        logger.debug("Adding NetworkX graph to Network object")
        try:
            # Use from_nx to convert NetworkX graph to pyvis format
            net.from_nx(G)
            logger.debug("NetworkX graph successfully converted to pyvis")
            
            if debug_mode:
                st.write("NetworkX graph successfully converted to pyvis")
        except Exception as e:
            logger.error(f"Error converting NetworkX graph to pyvis: {str(e)}")
            st.error(f"Error converting graph: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            if debug_mode:
                st.expander("Conversion error details").code(traceback.format_exc())
            return
        
        with st.spinner("Generating graph visualization..."):
            # Save the graph to a temporary HTML file with UTF-8 encoding
            html_file = os.path.join(os.path.dirname(__file__), "graph.html")
            logger.debug(f"Saving graph to: {html_file}")
            
            try:
                net.save_graph(html_file)
                logger.debug(f"Graph saved to HTML file: {os.path.exists(html_file)}")
                
                if debug_mode:
                    st.write(f"HTML file generated: {os.path.exists(html_file)}")
                    if os.path.exists(html_file):
                        st.write(f"File size: {os.path.getsize(html_file)} bytes")
            except Exception as e:
                logger.error(f"Error saving graph to HTML: {str(e)}")
                st.error(f"Error saving graph: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                if debug_mode:
                    st.expander("Save error details").code(traceback.format_exc())
                return
        try:
            logger.debug("Starting processing of graph HTML file")
            
            # Check if the file was created correctly
            if not os.path.exists(html_file) or os.path.getsize(html_file) == 0:
                st.error("Error generating graph visualization file.")
                st.info("Try selecting another concept or reload the page.")
                return
                
            # Read HTML file content
            logger.debug("Reading HTML file content")
            with open(html_file, "r", encoding="utf-8") as f:
                html_content = f.read()
            
            # Check if HTML content is valid
            if len(html_content) < 100 or "<html" not in html_content:
                logger.error(f"Invalid HTML content: {html_content[:100]}...")
                st.error("The generated HTML file does not contain a valid HTML document.")
                return
            
            # Ensure HTML has meta charset UTF-8
            logger.debug("Adding meta charset UTF-8")
            if "<meta charset=\"utf-8\"" not in html_content:
                html_content = html_content.replace("<head>", "<head>\n<meta charset=\"utf-8\">")
            
            # Add custom CSS for tooltips
            logger.debug("Adding custom CSS")
            if "</head>" in html_content:
                html_content = html_content.replace("</head>", f"{tooltip_css}\n</head>")
            else:
                html_content = f"{tooltip_css}\n{html_content}"
            
            # Inject JavaScript script for HTML tooltips
            logger.debug("Injecting JavaScript script for HTML tooltips")
            if "</body>" in html_content:
                html_content = html_content.replace("</body>", f"{html_script}\n</body>")
            else:
                html_content = f"{html_content}\n{html_script}"
            
            # Display HTML directly
            logger.debug("Displaying HTML with st.components.v1.html")
            st.components.v1.html(html_content, height=750)
            
            # Success confirmation
            concept_label = selected_concept.get('label')
            if concept_label is None or concept_label == '':
                # Extract a readable name from the ID
                concept_id = selected_concept.get('id', '')
                if '#' in concept_id:
                    concept_label = concept_id.split('#')[-1]
                elif '/' in concept_id:
                    concept_label = concept_id.split('/')[-1]
                else:
                    concept_label = concept_id
            
            st.success(f"Graph successfully generated for concept '{concept_label}'")
            
            if debug_mode:
                st.write("**Selected concept data:**")
                st.json(selected_concept)
        except Exception as e:
            st.error(f"Error generating the graph: {str(e)}")
            st.info("Tente selecionar outro conceito ou recarregar a página.")
            import traceback
            st.expander("Error details").code(traceback.format_exc())    
        
        # Show semantic relationships
        st.header("Semantic Relationships")
        semantic_relationships_filtered = [r for r in all_relationships if r.get("type") == "SEMANTIC"]
        if semantic_relationships_filtered:
            for rel in semantic_relationships_filtered:
                source_concept = next((c for c in all_concepts if c["id"] == rel["source"]), None)
                target_concept = next((c for c in all_concepts if c["id"] == rel["target"]), None)
                
                if source_concept and target_concept:
                    # Get concept labels, extracting from ID if null
                    source_label = source_concept.get('label')
                    if source_label is None or source_label == '':
                        source_id = source_concept.get('id', '')
                        if '#' in source_id:
                            source_label = source_id.split('#')[-1]
                        elif '/' in source_id:
                            source_label = source_id.split('/')[-1]
                        else:
                            source_label = source_id
                    
                    target_label = target_concept.get('label')
                    if target_label is None or target_label == '':
                        target_id = target_concept.get('id', '')
                        if '#' in target_id:
                            target_label = target_id.split('#')[-1]
                        elif '/' in target_id:
                            target_label = target_id.split('/')[-1]
                        else:
                            target_label = target_id
                    
                    with st.expander(f"{source_label} → {target_label}"):
                        st.write(f"**Similarity:** {rel['similarity']:.2f}")
                        st.write(f"**Description:** {rel['description']}")
                        
                        # Add IDs for debugging
                        if debug_mode:
                            st.write("**Details:**")
                            st.write(f"Source ID: {source_concept['id']}")
                            st.write(f"Target ID: {target_concept['id']}")
        else:
            st.write("No semantic relationships found.")
            
    # Render chat UI in the right panel
    render_chat_ui()
    
    # Check if we need to rerun the app
    check_rerun()

if __name__ == "__main__":
    main()
