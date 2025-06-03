import streamlit as st
import pandas as pd
from utils.api_client import APIClient

# Initialize API client
api_client = APIClient()

# Page configuration
st.set_page_config(
    page_title="Manage Concepts",
    page_icon="📚",
    layout="wide"
)

# Sidebar
st.sidebar.title("Actions")
    
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

# Main page
def main():
    st.title("Concept Management")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["View", "Create", "Edit"])
    
    with tab1:
        # View concepts
        st.header("Concept List")
        
        # Load concepts from API
        with st.spinner("Loading concepts..."):
            concepts = api_client.get_concepts()
        
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
                
                # Get relationships for the concept
                try:
                    relationships = api_client.get_relationships(concept_id)
                    if not isinstance(relationships, list):
                        if isinstance(relationships, dict) and 'relationships' in relationships:
                            relationships = relationships.get('relationships', [])
                        else:
                            relationships = []
                except Exception:
                    relationships = []
                
                num_relationships = len(relationships)
                
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
            selected_concept_id = st.selectbox("Select a concept to view details", 
                                           options=df["ID"].tolist(),
                                           format_func=lambda x: df[df["ID"] == x]["Name"].iloc[0] if not df[df["ID"] == x].empty else x)
            
            if selected_concept_id:
                # Find the selected concept
                selected_concept = next((c for c in concepts if c.get("id") == selected_concept_id), None)
                
                if selected_concept:
                    # Display detailed information
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**ID:** {selected_concept.get('id', '')}")
                        st.write(f"**Nome:** {selected_concept.get('label', '')}")
                        st.write(f"**Tipo:** {selected_concept.get('type', '')}")
                        st.write(f"**Descrição:** {selected_concept.get('description', '')}")
                    
                    with col2:
                        # Get relationships
                        with st.spinner("Loading relationships..."):
                            relationships = api_client.get_relationships(selected_concept_id)
                        
                        # Exibir relacionamentos
                        st.write(f"**Relationships ({len(relationships)}):**")
                        
                        if relationships:
                            # Process relationships for display
                            rel_data = []
                            for rel in relationships:
                                # Check if relationship is a dictionary
                                if isinstance(rel, dict):
                                    rel_type = rel.get("type", "")
                                    target = rel.get("target", "")
                                    label = rel.get("label", "")
                                elif isinstance(rel, str):
                                    # If it's a string, assume it's the target URI
                                    rel_type = "Relationship"
                                    target = rel
                                    label = ""
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
                            st.info("Nenhum relacionamento encontrado.")
        
        # Filters
        st.sidebar.header("Filters")
        concept_type = st.sidebar.selectbox(
            "Tipo de Conceito",
            ["All", "Diagnosis", "Treatment", "Symptom"]
        )
        
    with tab2:
        # Criar novo conceito
        st.header("Criar Novo Conceito")
        
        with st.form("new_concept"):
            concept_name = st.text_input("Nome do Conceito")
            concept_type = st.selectbox(
                "Tipo de Conceito",
                ["Diagnóstico", "Tratamento", "Sintoma"]
            )
            description = st.text_area("Descrição")
            
            if st.form_submit_button("Criar"):
                # Aqui seria feita a chamada à API para criar o conceito
                st.success("Conceito criado com sucesso!")
    
    with tab3:
        # Editar conceito
        st.header("Editar Conceito")
        
        # Seleção do conceito para editar
        selected_concept = st.selectbox(
            "Selecione o conceito para editar",
            ["Conceito 1", "Conceito 2"]
        )
        
        if selected_concept:
            # Formulário de edição
            with st.form("edit_concept"):
                concept_name = st.text_input("Nome do Conceito", value=selected_concept)
                description = st.text_area("Descrição")
                
                if st.form_submit_button("Salvar"):
                    # Aqui seria feita a chamada à API para atualizar o conceito
                    st.success("Conceito atualizado com sucesso!")

if __name__ == "__main__":
    main()
