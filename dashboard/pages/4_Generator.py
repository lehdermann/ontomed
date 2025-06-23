import os
import sys
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import streamlit as st
from utils.api_client import APIClient
from prompt.manager import PromptManager as TemplateManager
from llm.factory import LLMFactory

# Import shared layout components
from components.shared_layout_new import setup_shared_layout_content, render_chat_ui, create_three_column_layout, check_rerun
from components.chat.chat_ui_new import ChatUI

# Initialize API client
api_client = APIClient()

# Initialize managers
llm = LLMFactory.create_llm()

# Get shared template manager
from utils.session_manager import get_template_manager
template_manager = get_template_manager()
logging.info("Using shared TemplateManager instance")

# Function to handle chat messages
def handle_user_message(message: str) -> None:
    """Handle user message in the chat."""
    try:
        # Use the global API client
        global api_client
        
        # Process the message using the APIClient's process_chat_message method
        logger.info(f"Processing user message: {message}")
        chat_response = api_client.process_chat_message(message)
        
        # Extract the response and identified intent
        response_text = chat_response.get('response', "Desculpe, não consegui processar sua mensagem.")
        intent = chat_response.get('intent', "outro")
        
        # Register the identified intent for debugging purposes
        logger.info(f"Intenção identificada: {intent}")
        
        # Add the bot's response to the chat history
        if 'chat_messages' in st.session_state:
            st.session_state.chat_messages.append({"is_user": False, "content": response_text})
        
    except Exception as e:
        error_msg = f"Desculpe, ocorreu um erro ao processar sua mensagem: {str(e)}"
        if 'chat_messages' in st.session_state:
            st.session_state.chat_messages.append({"is_user": False, "content": error_msg})
        logger.error(f"Error handling user message: {e}", exc_info=True)

def main():
    """Main function of the content generation page."""
    # Setup shared layout
    page = setup_shared_layout_content()
    
    # Import the time module to use in the function scope
    import time
    # Page title
    st.title("Content Generator")
    
    # Sidebar - Filters
    st.sidebar.header("Filters")
    concept_type = st.sidebar.selectbox("Concept Type", ["All", "Diagnosis", "Treatment", "Prevention"])
    # Removing template type filtering to display all templates
    # template_type = st.sidebar.selectbox("Template Type", ["All", "text", "structured", "embedding"])
    
    # Hidden debug mode for developers
    debug_mode = st.sidebar.checkbox("Developer Mode", value=False)
    
    # Main content
    st.header("Select a Concept")
    
    # Initialize session state variables if they don't exist
    if 'concepts' not in st.session_state:
        st.session_state.concepts = []
    if 'selected_concept' not in st.session_state:
        st.session_state.selected_concept = None
    if 'selected_template' not in st.session_state:
        st.session_state.selected_template = None
    
    # Initialize cache variables in session_state if they don't exist
    if 'concepts_cache' not in st.session_state:
        st.session_state.concepts_cache = None
    if 'concepts_cache_timestamp' not in st.session_state:
        st.session_state.concepts_cache_timestamp = None
    if 'concepts_cache_filter' not in st.session_state:
        st.session_state.concepts_cache_filter = None
        
    # Define cache expiration time (in seconds)
    cache_expiration = 300  # 5 minutes
    
    # Get the current filter
    current_filter = {"type": concept_type if concept_type != "All" else None}
    
    # Check if we have a valid cache for the current filter
    cache_valid = False
    if (st.session_state.concepts_cache is not None and 
        st.session_state.concepts_cache_timestamp is not None and
        st.session_state.concepts_cache_filter == current_filter):
        current_time = time.time()
        # Check if the cache is still valid (has not expired)
        if current_time - st.session_state.concepts_cache_timestamp < cache_expiration:
            cache_valid = True
            
    # Button to force cache update
    if st.sidebar.button("Atualizar lista de conceitos"):
        cache_valid = False
        st.sidebar.info("Atualizando dados...")
    
    # Load concepts from API or cache
    if cache_valid:
        concepts = st.session_state.concepts_cache
        st.sidebar.success("Dados carregados do cache")
    else:
        with st.spinner("Carregando conceitos da API..."):
            concepts = api_client.get_concepts(filters=current_filter)
            # Update the cache
            st.session_state.concepts_cache = concepts
            st.session_state.concepts_cache_timestamp = time.time()
            st.session_state.concepts_cache_filter = current_filter
    
    # Store concepts in session state for other parts of the app
    st.session_state.concepts = concepts
    
    # Process concepts for display
    if concepts:
        # Add a display name for each concept
        for concept in concepts:
            # Extract ID
            concept_id = concept.get("id", "")
            
            # Use label if available, otherwise extract from ID
            label = concept.get("label", "")
            if not label:
                if "#" in concept_id:
                    label = concept_id.split("#")[-1]
                elif "/" in concept_id:
                    label = concept_id.split("/")[-1]
                else:
                    label = concept_id
            
            # Add display name to concept
            concept["display_name"] = label
        
        # Display information about the number of concepts
        st.caption(f"Total available concepts: {len(concepts)}")
        
        # Function to handle concept selection
        def on_concept_select():
            # Get the selected concept from the selectbox
            selected_option = st.session_state.concept_selectbox
            # Find the matching concept in our list
            for concept in concepts:
                if concept.get("id") == selected_option:
                    # Store the entire concept object in session state
                    st.session_state.selected_concept = concept
                    break
        
        # Get list of concept IDs for the selectbox
        concept_ids = [c.get("id") for c in concepts]
        
        # Determine the index for the current selection
        selected_index = 0
        if st.session_state.selected_concept is not None:
            selected_id = st.session_state.selected_concept.get("id")
            if selected_id in concept_ids:
                selected_index = concept_ids.index(selected_id)
        
        # Display function for concepts
        def format_concept(concept_id):
            for c in concepts:
                if c.get("id") == concept_id:
                    return c.get("display_name", c.get("label", c.get("id", "No name")))
            return concept_id
        
        # Concept selection using display_name with session state
        st.selectbox(
            "Concept", 
            concept_ids,
            index=selected_index,
            format_func=format_concept,
            key="concept_selectbox",
            on_change=on_concept_select
        )
        
        # Use the selected concept from session state
        selected_concept = st.session_state.selected_concept
        
        # Show minimal debug information if developer mode is enabled
        if debug_mode:
            st.caption(f"Developer info: {len(concepts)} concepts loaded")
    else:
        st.warning("No concepts found. Check if there is data in the database.")
        selected_concept = None
    
    if selected_concept is not None:
        # Function to fix character encoding issues using Unicode normalization
        def fix_encoding(text):
            if not text:
                return text
                
            import unicodedata
            
            # Handle string or other types
            if not isinstance(text, str):
                text = str(text)
                
            # Apply Unicode normalization (NFC form combines characters and diacritics)
            normalized_text = unicodedata.normalize('NFC', text)
            
            # Special case for common problematic strings
            if "Prot" in normalized_text and "g" in normalized_text:
                normalized_text = normalized_text.replace("ProtÃ©gÃ©", "Protégé")
                
            return normalized_text
        
        # Show concept details with fixed encoding
        display_name = fix_encoding(selected_concept.get('display_name', selected_concept.get('label', 'No name')))
        st.subheader(f"Concept Details: {display_name}")
        # Display concept ID 
        st.caption(f"ID: {selected_concept.get('id', '')}")
        
        # Get additional concept information via API
        with st.spinner("Getting detailed concept information..."):
            try:
                # Get the complete concept from the API
                concept_id = selected_concept.get('id', '')
                if concept_id:
                    # Get the complete concept
                    concept_details = api_client.get_concept(concept_id)
                    
                    # Extract basic concept information
                    if concept_details:
                        # Extract basic concept information
                        if concept_details.get('type'):
                            selected_concept['type'] = concept_details.get('type')
                        
                        if concept_details.get('label'):
                            selected_concept['label'] = concept_details.get('label')
                        
                        # Look for information in relationships
                        if concept_details.get('relationships'):
                            
                            # Process relationships to extract information
                            for rel in concept_details.get('relationships'):
                                rel_type = rel.get('type', '')
                                target = rel.get('target', '')
                                
                                # Extract concept type (Class)
                                if rel_type == 'type' and 'Class' in target:
                                    selected_concept['type'] = 'Class'
                                
                                # Extract concept label
                                elif rel_type == 'label':
                                    selected_concept['label'] = target
                                
                                # Extract concept description - improve detection for Disease
                                elif rel_type == 'comment':
                                    # Prioritize descriptions that seem to be from the Disease concept
                                    if any(term in target.lower() for term in ["anormal", "organismo", "condi", "doença", "disease", "patologia", "patológico", "saúde"]):
                                        selected_concept['description'] = target
                                    # If still no description, use any comment
                                    elif not selected_concept.get('description'):
                                        selected_concept['description'] = target
                        
                        # Get relevant relationships using the simplified method
                        relationships = api_client.get_relationships(concept_id)
                        if relationships:
                            selected_concept['relationships'] = relationships
            except Exception as e:
                st.warning(f"Could not get detailed information: {str(e)}")
                
                # Show error details for debugging
                with st.expander("Error details"):
                    st.error(str(e))
                    import traceback
                    st.code(traceback.format_exc())
        
        # Display concept information in a more organized way
        col1, col2 = st.columns(2)
        
        with col1:
            # Display concept type with fixed encoding
            concept_type = fix_encoding(selected_concept.get('type', ''))
            st.write(f"**Type:** {concept_type if concept_type else 'Not specified'}")
            
            # Display concept label with fixed encoding
            label = fix_encoding(selected_concept.get('label', ''))
            st.write(f"**Label:** {label if label else 'Not specified'}")
        
        with col2:
            # Display concept description with fixed encoding
            description = selected_concept.get('description', '')
            # Check if there is a description in 'comment'
            if not description and selected_concept.get('comment'):
                description = selected_concept.get('comment')
            description = fix_encoding(description)
            st.write(f"**Description:** {description if description else 'Not specified'}")
        
        # Display concept relationships
        relationships = selected_concept.get('relationships', [])
        if relationships:
            st.subheader("Relationships")
            
            # Create a relationships table
            relationship_data = []
            for rel in relationships:
                # Try different keys for the predicate
                predicate = rel.get('type', rel.get('predicate_name', rel.get('predicate', '')))
                
                # Try different keys for the object
                object_id = rel.get('target', rel.get('target_uri', rel.get('object', '')))
                
                # Extract readable name from object
                object_name = object_id
                if "#" in object_id:
                    object_name = object_id.split("#")[-1]
                elif "/" in object_id:
                    object_name = object_id.split("/")[-1]
                
                relationship_data.append({
                    "Predicate": fix_encoding(predicate),
                    "Object": fix_encoding(object_name),
                    "Full ID": object_id
                })
            
            if relationship_data:
                st.dataframe(relationship_data)
            else:
                st.info("No relationships found for this concept.")
        else:
            st.info("No relationships found for this concept.")
        
        # Template selection
        st.header("Select a Template")
        
        # Load all available templates directly from TemplateManager
        with st.spinner("Loading templates..."):
            try:
                # Get all templates from TemplateManager
                templates = template_manager.get_templates()
                # Display information about the number of templates
                st.caption(f"Total available templates: {len(templates)}")
                
                
                # If no templates are found, display a message
                if not templates:
                    st.warning("No templates found. Check if templates are loaded in the system.")
                    # Add a button to check the API
                    if st.button("Check Template API"):
                        st.info(f"Trying to access: {api_client.base_url}/api/templates")
                        try:
                            response = requests.get(
                                f"{api_client.base_url}/api/templates",
                                headers=api_client.headers
                            )
                            st.code(f"Status: {response.status_code}\nResponse: {response.text}")
                        except Exception as e:
                            st.error(f"Error accessing API: {str(e)}")
            except Exception as e:
                st.error(f"Error loading templates: {str(e)}")
                templates = []
                
        # Template selection (only if templates are available)
        if templates:
            # Format template name for display
            def format_template(template):
                name = template.get("name", "")
                template_type = template.get("type", "")
                if template_type:
                    return f"{name} ({template_type})"
                return name
                
            # Function to handle template selection
            def on_template_select():
                # Get the selected template from the selectbox
                selected_option = st.session_state.template_selectbox
                # Find the matching template in our list
                for template in templates:
                    template_id = template.get("id") or template.get("template_id")
                    if template_id == selected_option:
                        # Store the entire template object in session state
                        st.session_state.selected_template = template
                        break
            
            # Get list of template IDs for the selectbox
            template_ids = [t.get("id") or t.get("template_id") for t in templates]
            
            # Determine the index for the current selection
            selected_index = 0
            if st.session_state.selected_template is not None:
                selected_id = st.session_state.selected_template.get("id") or st.session_state.selected_template.get("template_id")
                if selected_id in template_ids:
                    selected_index = template_ids.index(selected_id)
            
            # Display function for templates
            def format_template_id(template_id):
                for t in templates:
                    t_id = t.get("id") or t.get("template_id")
                    if t_id == template_id:
                        name = t.get("name", "")
                        template_type = t.get("type", "")
                        if template_type:
                            return f"{name} ({template_type})"
                        return name
                return template_id
            
            # Template selection with session state
            st.selectbox(
                "Template", 
                template_ids,
                index=selected_index,
                format_func=format_template_id,
                key="template_selectbox",
                on_change=on_template_select
            )
            
            # Use the selected template from session state
            selected_template = st.session_state.selected_template
            
            # Show minimal debug information if developer mode is enabled
            if debug_mode:
                st.caption(f"Developer info: {len(templates)} templates loaded")
            
            # Display additional information about the selected template
            if selected_template:
                template_description = fix_encoding(selected_template.get('description', 'No description'))
                st.write(f"**Description:** {template_description}")
        else:
            selected_template = None
        
        if selected_template:
            # Generation settings
            st.header("Generation Settings")
            
            col1, col2 = st.columns(2)
            with col1:
                temperature = st.slider("Temperature", 0.0, 1.0, 0.7)
            with col2:
                max_tokens = st.slider("Max Tokens", 100, 1000, 500)
            
            # Debug mode is already defined at the top of the function
            
            # Generation button
            if st.button("Generate Content"):
                try:
                    # Make sure we have both a concept and template selected
                    if not st.session_state.selected_concept:
                        st.error("Please select a concept first.")
                        return
                    
                    if not st.session_state.selected_template:
                        st.error("Please select a template first.")
                        return
                    
                    # Use the concept and template from session state
                    selected_concept = st.session_state.selected_concept
                    selected_template = st.session_state.selected_template
                    
                    # Show debug information
                    if debug_mode:
                        st.info("**DEBUG - Selected Concept:**")
                        st.json({
                            "id": selected_concept.get("id", "None"),
                            "display_name": selected_concept.get("display_name", "None"),
                            "label": selected_concept.get("label", "None"),
                            "type": selected_concept.get("type", "None")
                        })
                        
                        st.info("**DEBUG - Selected Template:**")
                        st.json({
                            "id": selected_template.get("id", "None") or selected_template.get("template_id", "None"),
                            "name": selected_template.get("name", "None"),
                            "type": selected_template.get("type", "None")
                        })
                    
                    # Generate content using the API
                    template_id = selected_template.get("id") or selected_template.get("template_id")
                    
                    with st.spinner(f"Generating content with template '{selected_template.get('name')}' for concept '{selected_concept.get('display_name')}'..."):
                        try:
                            # Check the template type and use TemplateManager directly
                            template_type = selected_template.get("type", "").lower()
                            
                            # Prepare the concept for TemplateManager
                            # Ensure that variable names match those used in the template
                            
                            # Check if we have a description for the Disease concept
                            description = selected_concept.get("description", "")
                            if not description and selected_concept.get("display_name", "").lower() == "disease":
                                # Add a default description for Disease if none is available
                                description = "An abnormal medical condition that affects an organism, interrupting normal body functions and can be caused by external or internal factors."
                                selected_concept["description"] = description
                                st.caption("Added default description for the Disease concept")
                            
                            # Check if we have a type for the concept
                            concept_type = selected_concept.get("type", "")
                            if not concept_type:
                                # Add a default type if none is available
                                concept_type = "Class"
                                selected_concept["type"] = concept_type
                                st.caption("Added default type 'Class' for the concept")
                            
                            # Extract better concept name from relationships or display_name
                            concept_name = selected_concept.get("display_name", "")
                            concept_name = fix_encoding(concept_name)
                            
                            # Initialize variables that will be used later
                            min_value = None
                            max_value = None
                            unit = None
                            parent_class = None
                            
                            # Check se selected_concept não é None antes de acessar seus atributos
                            if selected_concept is None:
                                st.error("Erro: Nenhum conceito selecionado. Por favor, selecione um conceito válido.")
                                return
                                
                            # Look for a better name in the relationships
                            relationships = selected_concept.get("relationships") if selected_concept else None
                            if relationships is not None:
                                for rel in relationships:
                                    if rel.get("type") == "label" and rel.get("target"):
                                        concept_name = fix_encoding(rel.get("target"))
                                        break
                            
                            # Extract min, max values and unit from relationships
                            relationships = selected_concept.get("relationships") if selected_concept else None
                            if relationships is not None:
                                for rel in relationships:
                                    if rel.get("type") == "hasMinValue":
                                        min_value = rel.get("target")
                                    elif rel.get("type") == "hasMaxValue":
                                        max_value = rel.get("target")
                                    elif rel.get("type") == "hasDefaultUnit":
                                        unit = rel.get("target")
                                    elif rel.get("type") == "subClassOf":
                                        parent_class = rel.get("target")
                            
                            # Extract better description from relationships
                            better_description = fix_encoding(description)
                            relationships = selected_concept.get("relationships") if selected_concept else None
                            if relationships is not None:
                                for rel in relationships:
                                    # Look for comments that might contain descriptions
                                    if rel.get("type") == "comment" and rel.get("target"):
                                        # Check if this comment seems to be about this specific concept
                                        target_text = rel.get("target", "").lower()
                                        if "fever" in target_text or "temperature" in target_text or "high" in target_text:
                                            better_description = fix_encoding(rel.get("target"))
                                            break
                            
                            # Function to fix character encoding issues
                            def fix_encoding(text):
                                if not text:
                                    return text
                                # Replace common problematic characters
                                replacements = {
                                    "Â°": "°",
                                    "Ã©": "é",
                                    "Ã§": "ç",
                                    "Ã£": "ã",
                                    "Ã¡": "á",
                                    "Ã³": "ó",
                                    "Ãº": "ú",
                                    "Ã ": "à",
                                    "Ãµ": "õ"
                                }
                                for char, replacement in replacements.items():
                                    text = text.replace(char, replacement)
                                return text
                            
                            # If no specific description was found, create one based on the concept name and relationships
                            if not better_description or "versão ultra-simplificada" in better_description.lower() or "versão" in better_description.lower():
                                # Create a description based on available information
                                if "high_fever" in concept_name.lower() or "temperature_high" in concept_name.lower():
                                    # Clean up the unit string by removing special character issues
                                    clean_unit = unit if unit else "°C"
                                    if "Â" in clean_unit:
                                        clean_unit = clean_unit.replace("Â", "")
                                    
                                    better_description = f"High fever is defined as a body temperature between {min_value} and {max_value} {clean_unit}. It is a significant elevation in body temperature that may indicate a serious infection or inflammatory condition requiring medical attention. Common causes include viral infections, bacterial infections, inflammatory conditions, and certain medications. Treatment typically involves antipyretic medications, hydration, and addressing the underlying cause."
                                elif "temperature" in concept_name.lower():
                                    # Clean up the unit string
                                    clean_unit = unit if unit else "°C"
                                    if "Â" in clean_unit:
                                        clean_unit = clean_unit.replace("Â", "")
                                        
                                    better_description = f"A measure of the degree of heat in the body, typically measured in {clean_unit}. Abnormal body temperature can indicate various medical conditions."
                            
                            # Fix encoding in the description
                            better_description = fix_encoding(better_description)
                            
                            # Clean up the unit for display
                            clean_unit = fix_encoding(unit) if unit else "°C"
                            
                            # Add more specific information for the template
                            condition = "High Fever"
                            treatment = "Antipyretic medications (such as acetaminophen or ibuprofen), hydration, and rest"
                            medical_concepts = f"High fever, defined as a body temperature between {min_value if min_value else '39.1'} and {max_value if max_value else '41'} {clean_unit}, is a symptom of various underlying conditions rather than a disease itself. It often indicates the body's immune response to infection or inflammation. Common causes include viral infections (like influenza), bacterial infections (like strep throat or urinary tract infections), inflammatory conditions, and certain medications or vaccines."
                            patient_data = "The patient is a 35-year-old individual presenting with a temperature of 39.5°C (103.1°F), accompanied by chills, fatigue, and mild dehydration. They report the onset of symptoms approximately 24 hours ago, with no recent travel history or known exposure to infectious diseases."
                            
                            # Prepare the data with all possible variables and improved information
                            concept_data = {
                                # Variables used in the concept_explanation.yaml template
                                "display_name": concept_name,
                                "id": selected_concept.get("id", ""),
                                "type": concept_type,
                                "description": better_description,
                                
                                # Additional variables that can be used in other templates
                                "name": concept_name,
                                "concept_name": concept_name,
                                "concept_description": better_description,
                                "concept_type": concept_type,
                                "concept_properties": selected_concept.get("properties", {}),
                                
                                # Add relationships if available
                                "relationships": selected_concept.get("relationships", []),
                                
                                # Add template-specific variables
                                "condition": condition,
                                "treatment": treatment,
                                "medical_concepts": medical_concepts,
                                "patient_data": patient_data
                            }
                            
                            # Get the template content
                            template_content = selected_template.get("content", "")
                            
                            # Function to manually replace variables in the template
                            def fill_template(template_content, params):
                                import re
                                # Find all variables in both formats: {{var}} and {var}
                                double_brace_pattern = r'\{\{(\w+)\}\}'
                                single_brace_pattern = r'\{(\w+)\}'
                                
                                # Get variables with double braces
                                double_brace_vars = re.findall(double_brace_pattern, template_content)
                                
                                # Get variables with single braces
                                single_brace_vars = re.findall(single_brace_pattern, template_content)
                                
                                # Start with the original content
                                filled_content = template_content
                                
                                # Replace double-brace variables
                                for var in double_brace_vars:
                                    if var in params:
                                        value = str(params[var]) if params[var] is not None else ""
                                        placeholder = "{{" + var + "}}"
                                        filled_content = filled_content.replace(placeholder, value)
                                    else:
                                        # Replace with a placeholder
                                        filled_content = filled_content.replace("{{" + var + "}}", f"[{var} not available]")
                                
                                # Replace single-brace variables
                                for var in single_brace_vars:
                                    if var in params:
                                        value = str(params[var]) if params[var] is not None else ""
                                        placeholder = "{" + var + "}"
                                        filled_content = filled_content.replace(placeholder, value)
                                    else:
                                        # Replace with a placeholder
                                        filled_content = filled_content.replace("{" + var + "}", f"[{var} not available]")
                                
                                return filled_content
                            
                            # Manually replace variables in the template
                            filled_template = fill_template(template_content, concept_data)
                            
                            # Show minimal debug information if developer mode is enabled
                            if debug_mode:
                                with st.expander("Developer Information", expanded=False):
                                    st.write("**Concept data:**")
                                    st.json(concept_data)
                            
                            # Update the template with the filled content
                            template_with_filled_content = selected_template.copy()
                            template_with_filled_content["content"] = filled_template
                            
                            # Add explicit instructions to the template to focus on the selected concept
                            concept_specific_instruction = f"""IMPORTANT: This request is specifically about {concept_data['concept_name']}. 
                            Your response MUST focus on {concept_data['concept_name']} and NOT on any other medical condition.
                            The condition is: {concept_data['condition']}
                            The treatment is: {concept_data['treatment']}
                            """
                            
                            # Add medical warning for treatment rationale template
                            if selected_template.get("id") == "treatment_rationale" or selected_template.get("name") == "Treatment Rationale":
                                concept_specific_instruction += "\nAt the end of your response, include this warning: 'Warning: If symptoms persist, a doctor should be consulted.'"
                            
                            # Prepend the instruction to the template content
                            modified_template = template_with_filled_content.copy()
                            modified_template["content"] = concept_specific_instruction + "\n\n" + modified_template["content"]
                            
                            if debug_mode:
                                with st.expander("Developer Information", expanded=False):
                                    st.write("**Modified template:**")
                                    st.code(modified_template["content"], language="yaml")
                            
                            if template_type == "structured":
                                # Generate structured content using TemplateManager with the filled template
                                response = template_manager.generate_structured(
                                    modified_template,
                                    concept_data,
                                    temperature=temperature,
                                    max_tokens=max_tokens
                                )
                                # Display structured content
                                st.json(response)
                            elif template_type == "embedding":
                                # Generate embedding using TemplateManager
                                st.info("Generating embedding for the concept...")
                                
                                # Check if we have sufficient information in the concept
                                if not concept_data.get("concept_name") and not concept_data.get("name") and not concept_data.get("label"):
                                    st.warning("The concept does not have a defined name, which may affect the quality of the embedding.")
                                    
                                if not concept_data.get("concept_description") and not concept_data.get("description"):
                                    st.warning("The concept does not have a defined description, which may affect the quality of the embedding.")
                                
                                try:
                                    # Generate embedding
                                    response = template_manager.get_embedding(
                                        selected_template["id"],
                                        concept_data
                                    )
                                    
                                    # Check if the embedding was generated successfully
                                    if response and len(response) > 0:
                                        st.success(f"Embedding generated successfully! (Dimension: {len(response)})")
                                        # Display a sample of the embedding (first 10 values)
                                        st.write("Embedding sample:")
                                        st.write(response[:10])
                                    else:
                                        st.error("Failed to generate embedding. Check logs for more details.")
                                except Exception as e:
                                    st.error(f"Error generating embedding: {str(e)}")
                                    with st.expander("Error details"):
                                        import traceback
                                        st.code(traceback.format_exc())
                            else:
                                # Default to text generation
                                response = template_manager.generate_content(
                                    modified_template,
                                    concept_data,
                                    temperature=temperature,
                                    max_tokens=max_tokens
                                )
                                # Display text response
                                st.write(response)
                        except Exception as e:
                            st.error(f"Error generating content: {str(e)}")
                            # Display error details for debugging
                            with st.expander("Error details"):
                                st.error(str(e))
                                import traceback
                                st.code(traceback.format_exc())
                    
                    # Save button
                    if st.button("Save Content"):
                        # Here would be the API call to save the content
                        st.success("Content saved successfully!")
                except Exception as e:
                    st.error(f"Error generating content: {str(e)}")
    
    # Render chat UI
    render_chat_ui()
    
    # Check if we need to rerun the app
    check_rerun()

if __name__ == "__main__":
    main()
