import streamlit as st
from datetime import datetime
import requests
from dotenv import load_dotenv
import os
import json
import logging

# Page configuration (must be the first Streamlit call)
st.set_page_config(
    page_title="OntoMed Dashboard",
    page_icon="🏥",
    layout="wide"
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize templates
try:
    import sys
    # Add the root directory to the path to import the prompt module
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from prompt.initialize import initialize
    initialize()
    logger.info("Templates initialized successfully")
    st.sidebar.success("Templates initialized successfully")
except Exception as e:
    logger.error(f"Error initializing templates: {e}")
    st.sidebar.error(f"Error initializing templates: {e}")

# Sidebar
st.sidebar.title("OntoMed Dashboard")

# Navigation
page = st.sidebar.radio(
    "Navigation",
    ["Home", "Templates"],
    index=0
)

if page == "Templates":
    # Redirect to templates page
    import streamlit as st
    st.switch_page("pages/3_Templates.py")
    st.stop()  # Stop execution of the rest of the Home code

# Import the API client
from utils.api_client import APIClient

# Function to get graph statistics
@st.cache_data
def get_graph_statistics():
    try:
        # Use the API client to get statistics
        api_client = APIClient()
        stats = api_client.get_graph_statistics()
        return stats
    except Exception as e:
        st.error(f"Error getting statistics: {str(e)}")
        logger.error(f"Error getting statistics: {str(e)}")
        return None

# Main page
def main():
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

if __name__ == "__main__":
    main()
