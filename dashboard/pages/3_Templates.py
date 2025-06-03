import os
import sys

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import streamlit as st
import pandas as pd
import json
import requests
from utils.api_client import APIClient
from prompt.template_manager import TemplateManager
from prompt.category_manager import CategoryManager
from prompt.suggestion_manager import SuggestionManager
from prompt.editor_manager import EditorManager
from prompt.dependency_manager import DependencyManager
from prompt.export_manager import ExportManager
from llm.factory import LLMFactory

# Initialize API client
api_client = APIClient()

# Initialize managers
llm = LLMFactory.create_llm()
template_manager = TemplateManager(llm)
category_manager = CategoryManager(template_manager)
suggestion_manager = SuggestionManager(llm)
editor_manager = EditorManager(llm, template_manager)
dependency_manager = DependencyManager(llm)
export_manager = ExportManager(llm, template_manager)

# Page configuration
st.set_page_config(
    page_title="Manage Templates",
    page_icon="📋",
    layout="wide"
)

# Sidebar
st.sidebar.title("Actions")

# Debug log
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("3_Templates.py loaded")

# Ontology Section
st.sidebar.header("Ontology")

# Upload Section
ontology_file = st.sidebar.file_uploader("Upload Ontology", type=["rdf", "ttl", "xml", "jsonld", "owl"])
if ontology_file is not None:
    if st.sidebar.button("Upload Ontology"):
        with st.spinner("Uploading ontology..."):
            response = api_client.upload_ontology(ontology_file)
            if response.status_code == 200:
                st.sidebar.success("Ontology uploaded and loaded successfully.")
                st.rerun()  # Refresh the page to show data
            else:
                st.sidebar.error(f"Failed to upload ontology: {response.text}")

# View Data Section
if st.sidebar.button("View Ontology Data"):
    try:
        response = requests.get(f"{api_client.base_url}/api/ontology/triples")
        if response.status_code == 200:
            data = response.json()
            st.subheader(f"Ontology Data (Showing {len(data['triples'])} of {data['total_triples']} triples)")
            
            # Exibir as triplas em uma tabela
            df = pd.DataFrame(data['triples'])
            st.dataframe(df, use_container_width=True)
            
            # Opção para exportar os dados
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download as CSV",
                data=csv,
                file_name="ontology_triples.csv",
                mime="text/csv",
            )
        else:
            st.error(f"Failed to fetch ontology data: {response.text}")
    except Exception as e:
        st.error(f"Error: {str(e)}")


# Main page
def main():
    """Main function of the template management page."""
    
    # Page title
    st.title("Template Management")
    
    # Sidebar - Filters
    st.sidebar.header("Filters")
    filter_type = st.sidebar.selectbox("Type", ["All", "Text", "Structured", "Embedding"])
    filter_status = st.sidebar.selectbox("Status", ["All", "Active", "Inactive"])
    filter_category = st.sidebar.selectbox(
        "Category",
        ["All"] + [c["name"] for c in category_manager.get_categories()]
    )
    
    # Main content
    with st.container():
        # Button to create new template
        if st.button("➡ New Template"):
            st.session_state.new_template = True

        # Form for new template
        if st.session_state.get("new_template"):
            with st.form("new_template_form"):
                st.subheader("Create New Template")
                
                # Concept selection for suggestion
                st.write("**Concept Selection**")
                with st.expander("Select Concept for Suggestion"):
                    # Load concepts
                    with st.spinner("Loading concepts..."):
                        concepts = api_client.get_concepts()
                    
                    # Concept selection
                    selected_concept = st.selectbox(
                        "Select a Concept",
                        concepts,
                        format_func=lambda x: x.get("name", "")
                    )
                    
                    if selected_concept:
                        # Button to suggest template
                        if st.button("Suggest Template"):
                            try:
                                # Suggest category
                                category_suggestion = suggestion_manager.suggest_category(selected_concept)
                                
                                # Suggest template
                                template_suggestion = suggestion_manager.suggest_template(
                                    selected_concept,
                                    category_suggestion["category"]
                                )
                                
                                # Fill form with suggestions
                                template_name = template_suggestion["name"]
                                template_type = template_suggestion["type"]
                                template_content = template_suggestion["content"]
                                variables = template_suggestion["variables"]
                                template_description = template_suggestion["description"]
                                
                                # Show suggestions
                                with st.expander("Suggestions"):
                                    st.write("**Suggested Category:**", category_suggestion["category"])
                                    st.write("**Reason:**", category_suggestion["reason"])
                                    st.write("**Suggested Template:**")
                                    st.code(template_content)
                                    st.write("**Suggested Variables:**")
                                    for var in variables:
                                        st.write(f"- {var}")
                                    st.write("**Suggested Description:**")
                                    st.write(template_description)
                            except Exception as e:
                                st.error(f"Error generating suggestions: {str(e)}")
                
                # Template name
                template_name = st.text_input("Template Name")
                
                # Template type
                template_type = st.selectbox(
                    "Template Type",
                    ["Text", "Structured", "Embedding"]
                )
                
                # Category
                categories = category_manager.get_categories()
                category = st.selectbox(
                    "Category",
                    categories,
                    format_func=lambda x: x["name"]
                )
                
                # Template content
                template_content = st.text_area(
                    "Template Content",
                    height=200,
                    help="Use variables in the format {{variable}}"
                )
                
                # Template variables
                st.write("**Template Variables**")
                variables = []
                for i in range(5):  # Support for up to 5 variables
                    var_name = st.text_input(
                        f"Variable {i+1}",
                        key=f"var_{i}"
                    )
                    if var_name:
                        variables.append(var_name)
                
                # Description
                template_description = st.text_area(
                    "Description",
                    height=100
                )
                
                # Action buttons
                col1, col2 = st.columns(2)
                with col1:
                    cancel = st.form_submit_button("Cancel")
                with col2:
                    submit = st.form_submit_button("Save")
                
                # Processar ações
                if cancel:
                    st.session_state.new_template = False
                    st.rerun()
                
                if submit:
                    # Validate required fields
                    if not template_name:
                        st.error("Template name is required")
                    elif not template_content:
                        st.error("Template content is required")
                    else:
                        # Criar template
                        new_template = {
                            "name": template_name,
                            "type": template_type,
                            "category": category["id"],
                            "content": template_content,
                            "variables": variables,
                            "description": template_description,
                            "status": "Active"
                        }
                        
                        # Salvar template
                        try:
                            template_manager.add_template(new_template)
                            st.success(f"Template '{template_name}' created successfully!")
                            st.session_state.new_template = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error creating template: {str(e)}")
        
        # List existing templates
        st.subheader("Existing Templates")
        
        # Obter templates
        templates = template_manager.get_templates()
        
        # Apply filters
        if filter_type != "All":
            templates = [t for t in templates if t["type"] == filter_type]
        
        if filter_status != "All":
            templates = [t for t in templates if t["status"] == filter_status]
        
        if filter_category != "All":
            templates = [t for t in templates if category_manager.get_category_name(t["category"]) == filter_category]
        
        # Exibir templates em cards
        if not templates:
            st.info("No templates found with the selected filters.")
        else:
            # Dividir em colunas
            cols = st.columns(3)
            
            for i, template in enumerate(templates):
                with cols[i % 3]:
                    with st.container(border=True):
                        # Cabeçalho do card
                        st.markdown(f"### {template['name']}")
                        st.markdown(f"**Type:** {template['type']}")
                        st.markdown(f"**Category:** {category_manager.get_category_name(template['category'])}")
                        st.markdown(f"**Status:** {template['status']}")
                        
                        # Template content
                        with st.expander("View content"):
                            st.code(template["content"])
                        
                        # Variables
                        if template.get("variables"):
                            with st.expander("Variables"):
                                for var in template["variables"]:
                                    st.markdown(f"- `{var}`")
                        
                        # Description
                        if template.get("description"):
                            with st.expander("Description"):
                                st.markdown(template["description"])
                        
                        # Ações
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if st.button("✏️ Edit", key=f"edit_{i}"):
                                st.session_state.edit_template = template["id"]
                                st.rerun()
                        
                        with col2:
                            status_toggle = "🔴 Deactivate" if template["status"] == "Active" else "🟢 Activate"
                            if st.button(status_toggle, key=f"toggle_{i}"):
                                new_status = "Inactive" if template["status"] == "Active" else "Active"
                                template_manager.update_template_status(template["id"], new_status)
                                st.success(f"Template status changed to {new_status}")
                                st.rerun()
                        
                        with col3:
                            if st.button("🗑️ Excluir", key=f"delete_{i}"):
                                st.session_state.delete_template = template["id"]
                                st.rerun()
        
        # Modal de edição
        if st.session_state.get("edit_template"):
            template_id = st.session_state.edit_template
            template = template_manager.get_template(template_id)
            
            if template:
                with st.form("edit_template_form"):
                    st.subheader(f"Editar Template: {template['name']}")
                    
                    # Nome do template
                    template_name = st.text_input("Nome do Template", value=template["name"])
                    
                    # Tipo de template
                    template_type = st.selectbox(
                        "Tipo de Template",
                        ["Texto", "Estruturado", "Embedding"],
                        index=["Texto", "Estruturado", "Embedding"].index(template["type"])
                    )
                    
                    # Categoria
                    categories = category_manager.get_categories()
                    category_index = 0
                    for i, cat in enumerate(categories):
                        if cat["id"] == template["category"]:
                            category_index = i
                            break
                    
                    category = st.selectbox(
                        "Categoria",
                        categories,
                        index=category_index,
                        format_func=lambda x: x["name"]
                    )
                    
                    # Conteúdo do template
                    template_content = st.text_area(
                        "Conteúdo do Template",
                        value=template["content"],
                        height=200,
                        help="Use variáveis no formato {{variavel}}"
                    )
                    
                    # Variáveis do template
                    st.write("**Variáveis do Template**")
                    variables = []
                    existing_vars = template.get("variables", [])
                    
                    for i in range(5):  # Suporte para até 5 variáveis
                        var_value = existing_vars[i] if i < len(existing_vars) else ""
                        var_name = st.text_input(
                            f"Variável {i+1}",
                            value=var_value,
                            key=f"edit_var_{i}"
                        )
                        if var_name:
                            variables.append(var_name)
                    
                    # Descrição
                    template_description = st.text_area(
                        "Descrição",
                        value=template.get("description", ""),
                        height=100
                    )
                    
                    # Botões de ação
                    col1, col2 = st.columns(2)
                    with col1:
                        cancel = st.form_submit_button("Cancelar")
                    with col2:
                        submit = st.form_submit_button("Salvar")
                    
                    # Processar ações
                    if cancel:
                        st.session_state.edit_template = None
                        st.rerun()
                    
                    if submit:
                        # Validar campos obrigatórios
                        if not template_name:
                            st.error("Nome do template é obrigatório")
                        elif not template_content:
                            st.error("Conteúdo do template é obrigatório")
                        else:
                            # Atualizar template
                            updated_template = {
                                "id": template_id,
                                "name": template_name,
                                "type": template_type,
                                "category": category["id"],
                                "content": template_content,
                                "variables": variables,
                                "description": template_description,
                                "status": template["status"]
                            }
                            
                            # Salvar template
                            try:
                                template_manager.update_template(updated_template)
                                st.success(f"Template '{template_name}' atualizado com sucesso!")
                                st.session_state.edit_template = None
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao atualizar template: {str(e)}")
        
        # Modal de exclusão
        if st.session_state.get("delete_template"):
            template_id = st.session_state.delete_template
            template = template_manager.get_template(template_id)
            
            if template:
                st.warning(f"Tem certeza que deseja excluir o template '{template['name']}'?")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Cancelar"):
                        st.session_state.delete_template = None
                        st.rerun()
                
                with col2:
                    if st.button("Confirmar Exclusão"):
                        try:
                            # Verificar dependências
                            dependencies = dependency_manager.check_template_dependencies(template_id)
                            
                            if dependencies:
                                st.error("Este template não pode ser excluído pois possui dependências:")
                                for dep in dependencies:
                                    st.markdown(f"- {dep['type']}: {dep['name']}")
                            else:
                                # Excluir template
                                template_manager.delete_template(template_id)
                                st.success(f"Template '{template['name']}' excluído com sucesso!")
                                st.session_state.delete_template = None
                                st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao excluir template: {str(e)}")
        
        # Exportar templates
        st.subheader("Exportar Templates")
        
        with st.expander("Opções de Exportação"):
            # Selecionar templates para exportação
            st.write("**Selecione os templates para exportação:**")
            
            selected_templates = []
            for template in templates:
                if st.checkbox(template["name"], key=f"export_{template['id']}"):
                    selected_templates.append(template["id"])
            
            # Formato de exportação
            export_format = st.selectbox(
                "Formato de Exportação",
                ["JSON", "YAML", "Python"]
            )
            
            # Botão de exportação
            if st.button("Exportar Templates"):
                if not selected_templates:
                    st.error("Selecione pelo menos um template para exportação")
                else:
                    try:
                        # Exportar templates
                        export_data = export_manager.export_templates(
                            selected_templates,
                            export_format.lower()
                        )
                        
                        # Determinar extensão do arquivo
                        file_ext = {
                            "json": "json",
                            "yaml": "yaml",
                            "python": "py"
                        }.get(export_format.lower(), "txt")
                        
                        # Oferecer download
                        st.download_button(
                            label=f"Download ({export_format})",
                            data=export_data,
                            file_name=f"templates_export.{file_ext}",
                            mime=f"text/{file_ext}"
                        )
                    except Exception as e:
                        st.error(f"Erro ao exportar templates: {str(e)}")


# Inicializar estado da sessão
if "new_template" not in st.session_state:
    st.session_state.new_template = False

if "edit_template" not in st.session_state:
    st.session_state.edit_template = None

if "delete_template" not in st.session_state:
    st.session_state.delete_template = None


if __name__ == "__main__":
    main()
