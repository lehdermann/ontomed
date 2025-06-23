import logging
import os
import sys
from datetime import datetime

import requests
import streamlit as st
from dotenv import load_dotenv

# Page configuration (must be the first Streamlit call)
st.set_page_config(
    page_title="OntoMed Dashboard",
    page_icon="🏥",
    layout="wide"
)
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add components to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from components.shared_layout_new import setup_shared_layout_content, render_chat_ui, create_three_column_layout, check_rerun
from components.chat.chat_ui_new import ChatUI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize templates only once
if 'templates_initialized' not in st.session_state:
    try:
        import sys
        # Add the root directory to the path to import the prompt module
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from prompt.initialize import initialize
        initialize()
        logger.info("Templates initialized successfully")
        st.session_state.templates_initialized = True
    except Exception as e:
        logger.error(f"Error initializing templates: {e}")
        st.sidebar.error(f"Error initializing templates: {e}")
else:
    logger.debug("Templates already initialized")

# We'll handle page navigation in the main() function
# No need to call setup_shared_layout_content() here

# Import the API client
from utils.api_client import APIClient

# Function to get graph statistics
@st.cache_data(ttl=60)  # Cache por 60 segundos para permitir atualizações frequentes
def get_graph_statistics():
    try:
        # Use the API client to get statistics
        api_client = APIClient()
        logger.info("Call API to get statistics...")
        stats = api_client.get_graph_statistics()
        
        # Log detalhado do retorno da API
        logger.info(f"Return API statistics: {stats}")
        
        return stats
    except Exception as e:
        st.error(f"Error getting statistics: {str(e)}")
        logger.error(f"Error getting statistics: {str(e)}")
        return None

def handle_user_message(message: str) -> None:
    """Handle user message from the chat UI.
    
    Args:
        message: The user message
    """
    try:
        # Initialize the API client if it doesn't exist
        if 'api_client' not in st.session_state:
            st.session_state.api_client = APIClient()
        
        # Process the message using the APIClient process_chat_message method
        logging.info(f"Processing user message: {message}")
        chat_response = st.session_state.api_client.process_chat_message(message)
        
        # Extract the response and identified intent
        response_text = chat_response.get('response', "Desculpe, não consegui processar sua mensagem.")
        intent = chat_response.get('intent', "outro")
        
        # Register the identified intent for debugging purposes
        logging.info(f"Identified intent: {intent}")
        
        # Add the bot's response to the chat history
        if 'chat_messages' in st.session_state:
            st.session_state.chat_messages.append({"is_user": False, "content": response_text})
        
    except Exception as e:
        error_msg = f"Desculpe, ocorreu um erro ao processar sua mensagem: {str(e)}"
        if 'chat_messages' in st.session_state:
            st.session_state.chat_messages.append({"is_user": False, "content": error_msg})
        logging.error(f"Error processing chat message: {e}", exc_info=True)

# Only styles necessary for the chat
st.markdown("""
    <style>
        /* Chat container */
        #chat-container {
            z-index: 1000 !important;
        }
    </style>
""", unsafe_allow_html=True)

# Main page
def main():
    """Main function for the home page."""
    # Setup shared layout content (page config already set at the top of the file)
    page = setup_shared_layout_content()
    
    # Handle page navigation
    #if page == "Templates":
    #    # Redirect to templates page
    #    st.switch_page("pages/3_Templates.py")
    #    st.stop()  # Stop execution of the rest of the Home code
    
    # Use st directly for the main content, without additional columns
    # This allows CSS to better control the positioning
    st.title("OntoMed Dashboard")
    
    # Statistics
    st.header("Ontology Statistics")
    
    # Get statistics
    stats = get_graph_statistics()
    
    # Basic statistics
    st.subheader("Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Concepts",
            f"{stats['total_concepts'] if stats else '0'}"
        )
    with col2:
        st.metric(
            "Relationships",
            f"{stats['total_relationships'] if stats else '0'}"
        )
    with col3:
        # Placeholder for additional statistics that will be implemented in the API
        st.metric(
            "Classes",
            f"{stats.get('class_count', '?')}"
        )
    with col4:
        st.metric(
            "Subclasses",
            f"{stats.get('subclass_count', '?')}"
        )
    
    # Second row of statistics
    st.subheader("Structure Details")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Axioms",
            f"{stats.get('axiom_count', '?')}"
        )
    with col2:
        st.metric(
            "Annotations",
            f"{stats.get('annotation_count', '?')}"
        )
    with col3:
        st.metric(
            "Properties",
            f"{stats.get('property_count', '?')}"
        )
    with col4:
        st.metric(
            "Last Update",
            datetime.now().strftime("%d/%m/%Y %H:%M")
        )
        
    # Graphical visualization of statistics
    st.subheader("Distribution of Ontology Elements")
    
    if stats:
        # Prepare data for the chart
        chart_data = {
            'Concepts': stats['total_concepts'],
            'Relationships': stats['total_relationships'],
            'Classes': stats.get('class_count', 0),
            'Subclasses': stats.get('subclass_count', 0),
            'Annotations': stats.get('annotation_count', 0),
            'Axioms': stats.get('axiom_count', 0),
            'Properties': stats.get('property_count', 0)
        }
        
        # Create bar chart
        st.bar_chart(chart_data)
        
        # Add an explanation about the statistics
        with st.expander("About these statistics"):
            st.write("""
            **Concepts**: Total concepts in the ontology.  
            **Relationships**: Total relations between concepts.  
            **Classes**: Number of classes defined in the ontology.  
            **Subclasses**: Number of hierarchical subclass relationships.  
            **Annotations**: Number of annotations associated with ontology elements.  
            **Axioms**: Number of logical axioms (equivalentClass, disjointWith, etc.).  
            **Properties**: Total number of properties (ObjectProperty, DatatypeProperty, AnnotationProperty).  
            """)
    else:
        st.error("Unable to load data for graphical visualization.")
            
    # Render chat UI (must be after all other Streamlit elements)
    render_chat_ui()
    
    # Check if we need to rerun the app
    check_rerun()

if __name__ == "__main__":
    main()
