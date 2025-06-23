import os
import sys
import logging

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import streamlit as st
import pandas as pd
import json
import requests
from utils.api_client import APIClient
from prompt.manager import PromptManager as TemplateManager
from prompt.category_manager import CategoryManager
from prompt.suggestion_manager import SuggestionManager
from prompt.editor_manager import EditorManager
from prompt.dependency_manager import DependencyManager
from prompt.export_manager import ExportManager
from llm.factory import LLMFactory
from components.shared_layout_new import setup_shared_layout_content, render_chat_ui, check_rerun, create_three_column_layout
from components.chat.chat_ui_new import ChatUI

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup shared layout
page = setup_shared_layout_content()

# Handle chat messages
def handle_user_message(message: str) -> None:
    """Handle user message in the chat."""
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

# Inicialização controlada dos componentes NLP
# Seguindo o mesmo padrão usado em Home.py para inicialização dos templates
if 'nlp_initialized' not in st.session_state:
    try:
        # Importar APIClient diretamente
        api_client = APIClient()
        logger.info("APIClient inicializado diretamente")
        
        # Armazenar no estado da sessão para uso futuro
        st.session_state.api_client = api_client
        
        # Marcar como inicializado
        st.session_state.nlp_initialized = True
    except Exception as e:
        logger.error(f"Erro ao inicializar APIClient: {e}")
        st.sidebar.error(f"Erro ao inicializar APIClient: {e}")
else:
    # Usar a instância existente
    logger.debug("Usando APIClient já inicializado")
    api_client = st.session_state.api_client

# Initialize chat UI (must be after all other Streamlit elements)
# Moved to main() function

# Initialize LLM (moved to main)
llm = None

# Managers (initialized in main)
template_manager = None
category_manager = None
suggestion_manager = None
editor_manager = None
dependency_manager = None
export_manager = None

# Page configuration

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


# Custom CSS for templates page
st.markdown("""
    <style>
        /* Main container */
        .main .block-container {
            max-width: 95% !important;
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
        }
        
        /* Template cards */
        .stContainer {
            border-radius: 10px !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
            padding: 1.5rem !important;
            margin-bottom: 1.5rem !important;
            background: white !important;
            border: 1px solid #e0e0e0 !important;
            transition: transform 0.2s, box-shadow 0.2s !important;
        }
        
        .stContainer:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
        }
        
        /* Buttons */
        .stButton > button {
            width: 100% !important;
            margin: 0.25rem 0 !important;
            transition: all 0.2s !important;
        }
        
        .stButton > button:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            flex: 1 !important;
            text-align: center !important;
            padding: 0.5rem 1rem !important;
            border-radius: 8px !important;
            background: #f0f2f6 !important;
            border: 1px solid #e0e0e0 !important;
            margin: 0 !important;
        }
        
        .stTabs [aria-selected="true"] {
            background: #4a86e8 !important;
            color: white !important;
            border-color: #4a86e8 !important;
        }
        
        /* Forms */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stSelectbox > div > div > div {
            border-radius: 8px !important;
            border: 1px solid #e0e0e0 !important;
            padding: 0.5rem 1rem !important;
        }
        
        /* Expandable sections */
        .stExpander > div > div {
            border-radius: 8px !important;
            border: 1px solid #e0e0e0 !important;
            margin-bottom: 1rem !important;
        }
    </style>
""", unsafe_allow_html=True)

# Main page
def main():
    """Main function of the template management page."""
    global llm, template_manager, category_manager, suggestion_manager, editor_manager, dependency_manager, export_manager
    
    # Initialize managers if not already initialized
    if template_manager is None:
        # Initialize LLM
        llm = LLMFactory.create_llm()
        
        # Verificar se os templates já foram inicializados em Home.py
        if 'templates_initialized' not in st.session_state:
            try:
                import sys
                # Add the root directory to the path to import the prompt module
                sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
                from prompt.initialize import initialize
                initialize()
                logging.info("Templates initialized successfully")
                st.session_state.templates_initialized = True
            except Exception as e:
                logging.error(f"Error initializing templates: {e}")
        else:
            logging.debug("Templates already initialized")
            
        # Criar instância do TemplateManager diretamente
        from prompt.template_manager import TemplateManager
        template_manager = TemplateManager(llm, skip_intent_analysis=True)
        logging.info("TemplateManager criado com skip_intent_analysis=True")
        
        # Initialize other managers with the shared template manager
        category_manager = CategoryManager(template_manager)
        suggestion_manager = SuggestionManager(llm)
        editor_manager = EditorManager(llm, template_manager)
        dependency_manager = DependencyManager(llm)
        export_manager = ExportManager(llm, template_manager)
    
    # Page title with icon
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1.5rem;">
            <h1 style="margin: 0;">📋 Template Management</h1>
        </div>
    """, unsafe_allow_html=True)
    
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
                
                # Mapping between internal types and display types
                type_mapping = {
                    "text": "Texto",
                    "structured": "Estruturado",
                    "embedding": "Embedding"
                }
                reverse_mapping = {v: k for k, v in type_mapping.items()}
                
                # Template type
                template_type = st.selectbox(
                    "Tipo de Template",
                    ["Texto", "Estruturado", "Embedding"]
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
                        # Converter o tipo de exibição para o tipo interno
                        internal_type = reverse_mapping.get(template_type, "text")  # Fallback para "text" se não encontrar
                        
                        new_template = {
                            "name": template_name,
                            "type": internal_type,
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
        logger.info("Loading templates...")
        templates = template_manager.get_templates()
        logger.info(f"Found {len(templates)} templates")
        
        # Log templates for debugging
        for i, t in enumerate(templates):
            logger.info(f"Template {i+1}: {t.get('name', 'Unnamed')} (ID: {t.get('id', 'No ID')})")
        
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
                    
                    # Template name
                    template_name = st.text_input("Nome do Template", value=template["name"])
                    
                    # Mapping between internal types and display types
                    type_mapping = {
                        "text": "Texto",
                        "structured": "Estruturado",
                        "embedding": "Embedding"
                    }
                    reverse_mapping = {v: k for k, v in type_mapping.items()}
                    
                    # Get display type from internal type
                    display_type = type_mapping.get(template["type"], "Texto")  # Fallback para "Texto" se não encontrar
                    
                    # Template type
                    template_type = st.selectbox(
                        "Tipo de Template",
                        ["Texto", "Estruturado", "Embedding"],
                        index=["Texto", "Estruturado", "Embedding"].index(display_type)
                    )
                    
                    # Category
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
                    
                    # Template content
                    template_content = st.text_area(
                        "Conteúdo do Template",
                        value=template["content"],
                        height=200,
                        help="Use variáveis no formato {{variavel}}"
                    )
                    
                    # Template variables
                    st.write("**Variáveis do Template**")
                    variables = []
                    existing_vars = template.get("variables", [])
                    
                    for i in range(5):  # Support for up to 5 variables
                        var_value = existing_vars[i] if i < len(existing_vars) else ""
                        var_name = st.text_input(
                            f"Variável {i+1}",
                            value=var_value,
                            key=f"edit_var_{i}"
                        )
                        if var_name:
                            variables.append(var_name)
                    
                    # Template description
                    template_description = st.text_area(
                        "Descrição",
                        value=template.get("description", ""),
                        height=100
                    )
                    
                    # Action buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        cancel = st.form_submit_button("Cancelar")
                    with col2:
                        submit = st.form_submit_button("Salvar")
                    
                    # Process actions
                    if cancel:
                        st.session_state.edit_template = None
                        st.rerun()
                    
                    if submit:
                        # Validate mandatory fields
                        if not template_name:
                            st.error("Nome do template é obrigatório")
                        elif not template_content:
                            st.error("Conteúdo do template é obrigatório")
                        else:
                            # Update template
                            # Convert display type back to internal type
                            internal_type = reverse_mapping.get(template_type, "text")  # Fallback para "text" se não encontrar
                            
                            updated_template = {
                                "id": template_id,
                                "name": template_name,
                                "type": internal_type,
                                "category": category["id"],
                                "content": template_content,
                                "variables": variables,
                                "description": template_description,
                                "status": template["status"]
                            }
                            
                            # Save template
                            try:
                                template_manager.update_template(updated_template)
                                st.success(f"Template '{template_name}' atualizado com sucesso!")
                                st.session_state.edit_template = None
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao atualizar template: {str(e)}")
        
        # Execution Modal
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
                            # Check dependencies
                            dependencies = dependency_manager.check_template_dependencies(template_id)
                            
                            if dependencies:
                                st.error("Este template não pode ser excluído pois possui dependências:")
                                for dep in dependencies:
                                    st.markdown(f"- {dep['type']}: {dep['name']}")
                            else:
                                # Delete template
                                template_manager.delete_template(template_id)
                                st.success(f"Template '{template['name']}' excluído com sucesso!")
                                st.session_state.delete_template = None
                                st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao excluir template: {str(e)}")
        
        # Export templates
        st.subheader("Exportar Templates")
        
        with st.expander("Opções de Exportação"):
            # Select template to export
            st.write("**Selecione os templates para exportação:**")
            
            selected_templates = []
            for template in templates:
                if st.checkbox(template["name"], key=f"export_{template['id']}"):
                    selected_templates.append(template["id"])
            
            # Export format
            export_format = st.selectbox(
                "Formato de Exportação",
                ["JSON", "YAML", "Python"]
            )
            
            # Export button
            if st.button("Exportar Templates"):
                if not selected_templates:
                    st.error("Selecione pelo menos um template para exportação")
                else:
                    try:
                        # Export templates
                        export_data = export_manager.export_templates(
                            selected_templates,
                            export_format.lower()
                        )
                        
                        # Determine file extension
                        file_ext = {
                            "json": "json",
                            "yaml": "yaml",
                            "python": "py"
                        }.get(export_format.lower(), "txt")
                        
                        # Offer download
                        st.download_button(
                            label=f"Download ({export_format})",
                            data=export_data,
                            file_name=f"templates_export.{file_ext}",
                            mime=f"text/{file_ext}"
                        )
                    except Exception as e:
                        st.error(f"Erro ao exportar templates: {str(e)}")

    # Render chat UI (must be after all other Streamlit elements)
    render_chat_ui()
    
    # Check if we need to rerun the app
    check_rerun()

if __name__ == "__main__":
    main()
