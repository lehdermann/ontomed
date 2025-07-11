import streamlit as st
import pandas as pd
import sys
import os
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import shared layout components
from components.shared_layout_new import setup_shared_layout_content, render_chat_ui, create_three_column_layout, check_rerun
from components.chat.chat_ui_new import ChatUI

from utils.api_client import APIClient

# Initialize API client
api_client = APIClient()

# Page configuration
    
# Button to clear database
if st.sidebar.button("Clear Database", help="Removes all data from the database"):
    with st.spinner("Clearing database..."):
        try:
            response = api_client.clear_database()
            if response.get("success"):
                st.success("Database cleared successfully!")
            else:
                st.error("Error clearing database")
        except Exception as e:
            st.error(f"Erro: {str(e)}")

# Function to handle chat messages
def handle_user_message(message: str) -> None:
    """Handle user message in the chat.
    
    Args:
        message: The message from the user
    """
    logger.info(f"handle_user_message chamado com mensagem: '{message}'")
    
    # Verificar se já processamos esta mensagem antes
    if hasattr(st.session_state, 'last_handled_message') and st.session_state.last_handled_message == message:
        logger.info(f"Message already processed, ignoring: '{message}'")
        return
    
    try:
        # Mark this message as processed
        st.session_state.last_handled_message = message
        logger.info(f"Marking message as processed: '{message}'")
        
        # Use the global API client
        global api_client
        
        # Process the user message using the APIClient's process_chat_message method
        logger.info(f"Processing user message: {message}")
        chat_response = api_client.process_chat_message(message)
        
        # Extract the response and identified intent
        response_text = chat_response.get('response', "Desculpe, não consegui processar sua mensagem.")
        intent = chat_response.get('intent', "outro")
        
        # Log the identified intent for debugging purposes
        logger.info(f"Intent identified: {intent}")
        logger.info(f"Generating response: '{response_text[:50]}...'")
        
        # Add bot response to chat history
        if 'chat_messages' in st.session_state:
            st.session_state.chat_messages.append({"is_user": False, "content": response_text})
            logger.info("Bot response added to chat history")
        
    except Exception as e:
        error_msg = f"Sorry, an error occurred while processing your message: {str(e)}"
        if 'chat_messages' in st.session_state:
            st.session_state.chat_messages.append({"is_user": False, "content": error_msg})
        logger.error(f"Error handling user message: {e}", exc_info=True)
        logger.error(f"Error processing message: {e}")
    
    # No need to hide typing indicator with new implementation

# Main page
def main():
    # Setup shared layout
    page = setup_shared_layout_content()
    
    # Importar módulo time para usar em todo o escopo da função
    import time
    
    st.title("Concept Management")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["View", "Create", "Edit"])
    
    with tab1:
        # View concepts
        st.header("Concept List")
        
        # Initialize cache structures in session_state
        if 'concepts_cache' not in st.session_state:
            st.session_state.concepts_cache = None
        if 'concepts_cache_timestamp' not in st.session_state:
            st.session_state.concepts_cache_timestamp = None
        if 'concepts_cache_filter' not in st.session_state:
            st.session_state.concepts_cache_filter = None
        if 'concept_details_cache' not in st.session_state:
            st.session_state.concept_details_cache = {}
        if 'concept_details_timestamp' not in st.session_state:
            st.session_state.concept_details_timestamp = {}
        if 'relationships_cache' not in st.session_state:
            st.session_state.relationships_cache = {}
        if 'relationships_cache_timestamp' not in st.session_state:
            st.session_state.relationships_cache_timestamp = {}
            
        # Define cache expiration time (in seconds)
        cache_expiration = 300  # 5 minutes
        
        # Verify if we have a valid cache for the concept list
        concepts_cache_valid = False
        if st.session_state.concepts_cache is not None and st.session_state.concepts_cache_timestamp is not None:
            current_time = time.time()
            # Verify if the cache is still valid (has not expired)
            if current_time - st.session_state.concepts_cache_timestamp < cache_expiration:
                concepts_cache_valid = True
                
        # Button to force update of all caches
        if st.button("Update all data", key="refresh_all"):
            # Clear all caches
            st.session_state.concepts_cache = None
            st.session_state.concept_details_cache = {}
            st.session_state.relationships_cache = {}
            concepts_cache_valid = False
            st.info("Updating all data...")
        
        # Load concepts from API or cache
        if concepts_cache_valid:
            concepts = st.session_state.concepts_cache
            st.success("Concept list loaded from cache")
        else:
            with st.spinner("Loading concept list from API..."):
                concepts = api_client.get_concepts()
                # Update cache
                st.session_state.concepts_cache = concepts
                st.session_state.concepts_cache_timestamp = time.time()
                st.session_state.concepts_cache_filter = None  # No filter in this case
        
        if not concepts:
            st.warning("No concepts found.")
        else:
            # Process concepts to display more useful information
            processed_concepts = []
            for concept in concepts:
                # Extract ID and label
                concept_id = concept.get("id", "")
                
                # Extrair a parte final do URI como label se não houver label
                label = concept.get("label", "")
                if not label:
                    if "#" in concept_id:
                        label = concept_id.split("#")[-1]
                    elif "/" in concept_id:
                        label = concept_id.split("/")[-1]
                    else:
                        label = concept_id
                
                # Extract type from ID
                concept_type = ""
                if "#" in concept_id:
                    # Analyze URI structure to infer type
                    parts = concept_id.split("#")[-1].split("_")
                    if len(parts) > 1:
                        # If it has underscore, the first element may be the type
                        concept_type = parts[0]
                    else:
                        # Check if the name has uppercase letter in the middle (CamelCase)
                        if any(c.isupper() for c in parts[0][1:]):
                            concept_type = "Class"
                        else:
                            concept_type = "Property"
                
                # Generate a description based on the name
                description = ""
                if "_" in label:
                    # Replace underscores with spaces for a more readable description
                    description = label.replace("_", " ")
                else:
                    # Add spaces before uppercase letters to separate words in CamelCase
                    import re
                    description = re.sub(r'(?<!^)(?=[A-Z])', ' ', label)
                
                # Get relationships count from the concept data
                relationships = concept.get('relationships', [])
                num_relationships = len(relationships) if isinstance(relationships, list) else 0
                
                # Create dictionary with processed information
                processed_concept = {
                    "ID": concept_id,
                    "Name": label,
                    "Type": concept.get("type", concept_type),
                    "Description": concept.get("description", description),
                    "Number of Relationships": num_relationships
                }
                processed_concepts.append(processed_concept)
            
            # Convert to DataFrame
            df = pd.DataFrame(processed_concepts)
            
            # Display DataFrame with most useful columns first
            columns_order = ["Name", "Type", "Description", "Number of Relationships", "ID"]
            # Ensure we only use columns that exist
            available_columns = [col for col in columns_order if col in df.columns]
            # Add any remaining columns
            for col in df.columns:
                if col not in available_columns:
                    available_columns.append(col)
            
            st.dataframe(df[available_columns], use_container_width=True)
            
            # Display details of a selected concept
            st.subheader("Concept Details")
            
            # Create a mapping from ID to Name for faster lookup
            id_to_name = dict(zip(df["ID"], df["Name"]))
            
            # Get the list of concept IDs for the selectbox
            concept_ids = df["ID"].tolist()
            
            # Create the selectbox with the optimized format function
            selected_concept_id = st.selectbox(
                "Select a concept to view details",
                options=concept_ids,
                format_func=lambda x: id_to_name.get(x, x)  # Direct dictionary lookup
            )
            
            if selected_concept_id:
                # Check if we have the concept in cache
                concept_cache_valid = False
                if (selected_concept_id in st.session_state.concept_details_cache and 
                    selected_concept_id in st.session_state.concept_details_timestamp):
                    current_time = time.time()
                    # Verify if the cache is still valid (has not expired)
                    if current_time - st.session_state.concept_details_timestamp[selected_concept_id] < cache_expiration:
                        concept_cache_valid = True
                
                # Button to force update of the cache of concept details
                if st.button("Update concept details", key="refresh_concept_details"):
                    concept_cache_valid = False
                    st.info("Updating concept details...")
                
                # Get concept details from cache or API
                if concept_cache_valid:
                    selected_concept = st.session_state.concept_details_cache[selected_concept_id]
                    st.success("Concept details loaded from cache")
                else:
                    # Always get concept details from the API to ensure we have all information
                    with st.spinner("Loading concept details from API..."):
                        try:
                            # Retrieve complete details of the concept from the API
                            selected_concept = api_client.get_concept(selected_concept_id)
                            if not selected_concept:
                                st.error("Unable to load concept details")
                                return
                                
                            # Update cache
                            st.session_state.concept_details_cache[selected_concept_id] = selected_concept
                            st.session_state.concept_details_timestamp[selected_concept_id] = time.time()
                            
                        except Exception as e:
                            st.error(f"Erro ao carregar detalhes do conceito: {str(e)}")
                            return
                
                if selected_concept:
                    # Extract concept information with fallbacks
                    concept_id = selected_concept.get('id', '')
                    
                    # Extract label - use the part after the last # or / if label is empty
                    label = selected_concept.get('label', '')
                    if not label and '#' in concept_id:
                        label = concept_id.split('#')[-1]
                    elif not label and '/' in concept_id:
                        label = concept_id.split('/')[-1]
                    elif not label:
                        label = concept_id
                    
                    # Format the concept type to be more readable
                    concept_type = selected_concept.get('type', '')
                    if not concept_type and '#' in concept_id:
                        # Try to infer type from the ID
                        if 'ontology#' in concept_id:
                            concept_type = concept_id.split('ontology#')[1].split('_')[0]
                    
                    # Display detailed information in two columns
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**ID:** {concept_id}")
                        st.write(f"**Name:** {label}")
                        st.write(f"**Type:** {concept_type or 'Not specified'}")
                    
                    with col2:
                        # Empty column for alignment
                        pass
                    
                    # Description in full width below the columns
                    description = selected_concept.get('description', '')
                    st.write(f"**Description:** {description if description else 'No description available.'}")
                    
                    # Add spacing
                    st.write("")
                    
                    # Check if we have a valid cache for the relationships of this concept
                    rel_cache_valid = False
                    if (selected_concept_id in st.session_state.relationships_cache and 
                        selected_concept_id in st.session_state.relationships_cache_timestamp):
                        current_time = time.time()
                        # Check if the cache is still valid (has not expired)
                        if current_time - st.session_state.relationships_cache_timestamp[selected_concept_id] < cache_expiration:
                            rel_cache_valid = True
                    
                    # Button to force update of the relationships cache
                    if st.button("Update relationships", key="refresh_relationships"):
                        rel_cache_valid = False
                        st.info("Updating relationships...")
                    
                    # Load relationships from cache or API
                    if rel_cache_valid:
                        relationships = st.session_state.relationships_cache[selected_concept_id]
                        st.success("Relationships loaded from cache")
                    else:
                        # Get relationships from API
                        with st.spinner("Loading relationships from API..."):
                            try:
                                # Get the concept data which already includes relationships
                                concept_data = api_client.get_concept(selected_concept_id)
                                
                                # Extract relationships from the concept data
                                if concept_data and 'relationships' in concept_data:
                                    relationships = concept_data['relationships']
                                else:
                                    relationships = []
                                    st.warning("Nenhum relacionamento encontrado para o conceito")
                                
                                # Update cache
                                st.session_state.relationships_cache[selected_concept_id] = relationships
                                st.session_state.relationships_cache_timestamp[selected_concept_id] = time.time()
                            except Exception as e:
                                st.error(f"Error loading relationships: {str(e)}")
                                relationships = []
                    
                    # Display relationships section
                    st.subheader("Relationships")
                    st.write(f"**Total of relationships:** {len(relationships)}")
                    
                    if relationships:
                        # Process relationships for display
                        rel_data = []
                        for rel in relationships:
                            # Process relationship
                            
                            # Check if relationship is a dictionary
                            if isinstance(rel, dict):
                                # Check different possible dictionary formats
                                if "type" in rel and "target" in rel:
                                    rel_type = rel.get("type", "")
                                    target = rel.get("target", "")
                                    label = rel.get("label", "") or rel.get("target_label", "")
                                elif "predicate" in rel and "object" in rel:
                                    rel_type = rel.get("predicate", "")
                                    target = rel.get("object", "")
                                    label = rel.get("object_label", "")
                                else:
                                    # Unknown format, try using the first two keys
                                    keys = list(rel.keys())
                                    if len(keys) >= 2:
                                        rel_type = str(keys[0])
                                        target = str(rel.get(keys[0], ""))
                                        label = str(rel.get(keys[1], ""))
                                    else:
                                        # Could not extract sufficient information
                                        rel_type = "Desconhecido"
                                        target = str(rel)
                                        label = ""
                            elif isinstance(rel, str):
                                # If it's a string, assume it's the target URI
                                rel_type = "Relacionamento"
                                target = rel
                                label = ""
                            elif isinstance(rel, list) and len(rel) >= 2:
                                # If it's a list, try using the first two elements
                                rel_type = str(rel[0])
                                target = str(rel[1])
                                label = str(rel[1]) if len(rel) == 2 else str(rel[2])
                            else:
                                # Unknown type, skip
                                continue
                            
                            # Extract the final part of the URI as label if there is no label
                            if not label:
                                if "#" in target:
                                    label = target.split("#")[-1]
                                elif "/" in target:
                                    label = target.split("/")[-1]
                                else:
                                    label = target
                            
                            rel_data.append({
                                "Type": rel_type,
                                "Target": label,
                                "Target URI": target
                            })
                        
                        # Display relationships as table
                        if rel_data:
                            st.dataframe(pd.DataFrame(rel_data), use_container_width=True)
                        else:
                            st.info("No relationships found.")
                    else:
                        st.info("No relationships found for this concept.")
        
        # Filters
        st.sidebar.header("Filters")
        concept_type = st.sidebar.selectbox(
            "Concept Type",
            ["All", "Diagnosis", "Treatment", "Symptom"]
        )
        
    with tab2:
        # Criar novo conceito
        st.header("Create New Concept")
        
        with st.form("new_concept"):
            concept_name = st.text_input("Concept Name")
            concept_type = st.selectbox(
                "Concept Type",
                ["Diagnosis", "Treatment", "Symptom"]
            )
            description = st.text_area("Description")
            
            if st.form_submit_button("Criar"):
                # Aqui seria feita a chamada à API para criar o conceito
                st.success("Concept created successfully!")
    
    with tab3:
        # Editar conceito
        st.header("Edit Concept")
        
        # Seleção do conceito para editar
        selected_concept = st.selectbox(
            "Select the concept to edit",
            ["Concept 1", "Concept 2"]
        )
        
        if selected_concept:
            # Formulário de edição
            with st.form("edit_concept"):
                concept_name = st.text_input("Concept Name", value=selected_concept)
                description = st.text_area("Description")
                
                if st.form_submit_button("Save"):
                    st.success("Concept updated successfully!")
    
    # Render chat UI
    render_chat_ui()
    
    # Check if we need to rerun the app
    check_rerun()

if __name__ == "__main__":
    main()
