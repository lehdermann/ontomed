from typing import Dict, Any, List
import os
import yaml
import json
import logging
import streamlit as st
from typing import Dict, List, Any, Optional
from llm.interface import LLMInterface
from prompt.llm_integration import LLMPromptManager

logger = logging.getLogger(__name__)

class TemplateManager:
    """Template manager for content generation."""
    
    def __init__(self, llm: LLMInterface, skip_intent_analysis: bool = False):
        """Initializes the template manager.
        
        Args:
            llm: LLM interface for generation
            skip_intent_analysis: Se True, pula a análise de intenção dos templates
                                  Útil quando os templates já foram inicializados anteriormente
        """
        self.llm = llm
        self.prompt_manager = LLMPromptManager(llm)
        self.skip_intent_analysis = skip_intent_analysis
        
        # Verify if templates were initialized in Home.py
        templates_initialized = 'templates_initialized' in st.session_state and st.session_state.templates_initialized
        
        # Initialize in session state if not exists
        if 'tm_templates' not in st.session_state:
            st.session_state.tm_templates = []
            
        if 'tm_templates_loaded' not in st.session_state:
            st.session_state.tm_templates_loaded = False
        
        # Ensure consistency between flags
        if templates_initialized and not st.session_state.tm_templates_loaded:
            st.session_state.tm_templates_loaded = True
            logger.info("Marking tm_templates_loaded as True since templates_initialized is True")
        
        self.templates_dir = self._get_templates_dir()
        
        # Verify if we need to load the templates
        templates_need_loading = not st.session_state.tm_templates_loaded or len(st.session_state.tm_templates) == 0
        
        # If we already have templates in the session_state, use the cached templates
        if 'tm_templates' in st.session_state and len(st.session_state.tm_templates) > 0:
            logger.info(f"Templates already exist in session_state ({len(st.session_state.tm_templates)} templates). Using cache.")
            self._templates = st.session_state.tm_templates
            
            # Ensure that the flag is set correctly
            if not st.session_state.tm_templates_loaded:
                st.session_state.tm_templates_loaded = True
                logger.info("Updating tm_templates_loaded flag to True")
            return
        
        if templates_need_loading:
            logger.info(f"Loading templates from disk. skip_intent_analysis={self.skip_intent_analysis}")
            # First, load templates from disk (without analysis)
            raw_templates = self._load_templates_from_disk()
            
            # Then, analyze templates if necessary
            if not self.skip_intent_analysis:
                logger.info("Analyzing templates with LLM for intent extraction")
                self._analyze_templates(raw_templates)
            else:
                logger.info("Skipping template intent analysis (skip_intent_analysis=True)")
                # Only add templates without analysis
                self.templates = raw_templates
                # Store in session_state
                st.session_state.tm_templates = raw_templates
                
            st.session_state.tm_templates_loaded = True
            # Also mark templates_initialized as True to maintain consistency
            st.session_state.templates_initialized = True
            logger.info(f"Templates loaded and cached in session state")
        else:
            logger.info(f"Using cached templates from session state. skip_intent_analysis={self.skip_intent_analysis}")
            # Use templates from session_state
            self._templates = st.session_state.tm_templates
    
    @property
    def templates(self):
        """Gets the templates."""
        if hasattr(self, '_templates'):
            return self._templates
        return []
    
    @templates.setter
    def templates(self, value):
        """Sets the templates."""
        self._templates = value
        # Update templates in session_state
        st.session_state.tm_templates = value
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Gets a template by ID.
        
        Args:
            template_id: ID of the template to get
            
        Returns:
            Template or None if not found
        """
        for template in self.templates:
            if template["id"] == template_id:
                return template
        return None
    
    def get_templates(self) -> List[Dict[str, Any]]:
        """Gets all templates.
        
        Returns:
            List of templates
        """
        return self.templates
    
    def get_template_ids(self) -> List[str]:
        """Gets all template IDs.
        
        Returns:
            List of template IDs
        """
        return [template["id"] for template in self.templates]
    
    def get_template_names(self) -> List[str]:
        """Gets all template names.
        
        Returns:
            List of template names
        """
        return [template["name"] for template in self.templates]
    
    def get_template_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Gets a template by name.
        
        Args:
            name: Name of the template to get
            
        Returns:
            Template or None if not found
        """
        for template in self.templates:
            if template["name"] == name:
                return template
        return None
    
    def get_template_by_intent(self, intent: str) -> Optional[Dict[str, Any]]:
        """Gets a template by intent.
        
        Args:
            intent: Intent of the template to get
            
        Returns:
            Template or None if not found
        """
        for template in self.templates:
            if template.get("intent_info", {}).get("intent") == intent:
                return template
        return None
    
    def fill_template(self, template_id: str, variables: Dict[str, Any]) -> str:
        """Fills a template with variables.
        
        Args:
            template_id: ID of the template to fill
            variables: Variables to fill the template with
            
        Returns:
            Filled template
        """
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
            
        # Fill template with variables
        return self.prompt_manager.fill_template(template["content"], variables)
    
    def fill_structured_template(self, template_id: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Fills a structured template with variables.
        
        Args:
            template_id: ID of the template to fill
            variables: Variables to fill the template with
            
        Returns:
            Filled template
        """
        try:
            template = self.get_template(template_id)
            if not template:
                raise ValueError(f"Template not found: {template_id}")
                
            # Fill template with variables
            filled_template = self.prompt_manager.fill_template(template["content"], variables)
            
            # Parse filled template as JSON
            result = json.loads(filled_template)
            
            return result
        except Exception as e:
            logger.error(f"Error filling structured template: {str(e)}")
            raise ValueError(f"Error filling structured template: {str(e)}")
    
    def _get_templates_dir(self) -> str:
        """Gets the templates directory.
        
        Returns:
            Path to the templates directory
        """
        # Project base directory
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Templates directory
        templates_dir = os.path.join(base_dir, "prompt", "templates")
        
        # Check if the directory exists
        if not os.path.exists(templates_dir):
            logger.warning(f"Templates directory not found: {templates_dir}")
            os.makedirs(templates_dir, exist_ok=True)
        
        return templates_dir
    
    def _load_templates_from_disk(self) -> List[Dict[str, Any]]:
        """Loads templates from disk without performing intent analysis.
        
        Returns:
            List of templates loaded from disk
        """
        # If templates already exist in session_state and have content, we can use them
        if 'tm_templates' in st.session_state and len(st.session_state.tm_templates) > 0 and self.skip_intent_analysis:
            logger.info(f"Using existing templates from session_state (total: {len(st.session_state.tm_templates)})")
            return st.session_state.tm_templates
            
        logger.info(f"Attempting to load templates from: {self.templates_dir}")
        logger.info(f"Current working directory: {os.getcwd()}")
        
        # Check if directory exists and list its contents
        if not os.path.exists(self.templates_dir):
            logger.error(f"Templates directory not found: {self.templates_dir}")
            logger.error(f"Directory contents: {os.listdir(os.path.dirname(self.templates_dir)) if os.path.exists(os.path.dirname(self.templates_dir)) else 'Parent directory does not exist'}")
            return []
        
        # Log directory contents
        try:
            dir_contents = os.listdir(self.templates_dir)
            logger.info(f"Found {len(dir_contents)} items in templates directory: {dir_contents}")
        except Exception as e:
            logger.error(f"Error listing directory contents: {str(e)}")
            return []
        
        # List to store loaded templates
        loaded_templates = []
        
        # Process each YAML file in the templates directory
        for filename in dir_contents:
            if not filename.endswith(".yaml") and not filename.endswith(".yml"):
                continue
                
            file_path = os.path.join(self.templates_dir, filename)
            logger.info(f"Processing template file: {file_path}")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    template_data = yaml.safe_load(file)
                
                template_id = template_data.get("id", os.path.splitext(filename)[0])
                template_name = template_data.get("name", template_id)
                template_type = template_data.get("type", "unknown")
                
                template = {
                    "id": template_id,
                    "name": template_name,
                    "type": template_type,
                    "content": template_data.get("content", ""),
                    "variables": [param.get("name") for param in template_data.get("parameters", [])],
                    "description": template_data.get("description", ""),
                    "status": "Active",
                    "category": template_data.get("metadata", {}).get("domain", "general")
                }
                
                # Check if intent_info already exists in the YAML file
                if "intent_info" in template_data:
                    template["intent_info"] = template_data["intent_info"]
                    logger.info(f"Using predefined intent info for template {template_id}: {template['intent_info']}")
                else:
                    # Initialize with empty intent_info to be filled later
                    template["intent_info"] = {
                        "intent": "unknown",
                        "keywords": [],
                        "description": "Intent analysis pending"
                    }
                
                loaded_templates.append(template)
                logger.info(f"Successfully loaded template from disk: {template_name} (ID: {template_id}, Type: {template['type']})")
                
            except yaml.YAMLError as e:
                logger.error(f"YAML parsing error in {filename}: {str(e)}")
            except Exception as e:
                logger.error(f"Error loading template {filename}: {str(e)}", exc_info=True)
        
        logger.info(f"Total templates loaded from disk: {len(loaded_templates)}")
        return loaded_templates
        

    
    def _analyze_templates(self, templates: List[Dict[str, Any]]) -> None:
        """Analyze templates using LLM to extract intent information.
        
        Args:
            templates: List of templates to analyze
        """
        if not templates:
            logger.warning("No templates to analyze")
            self.templates = []
            return
            
        analyzed_templates = []
        
        for template in templates:
            template_id = template.get("id", "unknown")
            
            # If already has complete intent_info, no need to analyze
            if "intent_info" in template and template.get("intent_info", {}).get("intent") != "unknown":
                logger.info(f"Template {template_id} already has intent info: {template['intent_info']}")
                analyzed_templates.append(template)
                continue
                
            # Analyze template with LLM to extract intent information
            logger.info(f"Analyzing template {template_id} with LLM to extract intent information")
            intent_info = self.analyze_template_with_llm(template)
            template["intent_info"] = intent_info
            
            analyzed_templates.append(template)
            logger.info(f"Successfully analyzed template: {template['name']} (ID: {template_id}, Intent: {template['intent_info'].get('intent', 'unknown')})")
        
        # Update analyzed templates
        self.templates = analyzed_templates
        logger.info(f"Total templates analyzed: {len(analyzed_templates)}")
        logger.info(f"Template IDs: {[t['id'] for t in analyzed_templates]}")
    
    def analyze_template_with_llm(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a template using LLM to extract intent information.
        
        Args:
            template: Template to analyze
            
        Returns:
            Dict with extracted intent information
        """
        prompt = f"""
        Analise o seguinte template de resposta e extraia:
        1. A intenção principal que este template atende (use snake_case em inglês, ex: explain_term, list_terms, create_literature_summary)
        2. Palavras-chave relevantes para identificar esta intenção em PORTUGUÊS (5-10 palavras)
        3. Palavras-chave relevantes para identificar esta intenção em INGLÊS (5-10 palavras)
        4. Padrões de frases em PORTUGUÊS que um usuário poderia usar para ativar esta intenção (3-5 padrões)
        5. Padrões de frases em INGLÊS que um usuário poderia usar para ativar esta intenção (3-5 padrões)
        6. Tipos de entidades que são esperadas para este template (ex: termo_medico, medicamento)

        Template ID: {template.get('id', 'unknown')}
        Template Name: {template.get('name', 'unknown')}
        Template Content:
        {template.get('content', '')}

        Responda em formato JSON com os seguintes campos:
        {{
            "intent": "intenção_principal",
            "keywords_language": ["pt", "en"],
            "keywords_pt": ["palavra1", "palavra2", "..."],
            "keywords_en": ["word1", "word2", "..."],
            "patterns_pt": ["padrão 1", "padrão 2", "..."],
            "patterns_en": ["pattern 1", "pattern 2", "..."],
            "entities": ["entidade1", "entidade2", "..."]
        }}
        """
        
        try:
            # Generate structured content using the LLM
            result = self.llm.generate_structured(prompt)
            
            # Process the result
            if isinstance(result, dict):
                # Add all keywords to a single list for easier search
                result["keywords"] = result.get("keywords_pt", []) + result.get("keywords_en", [])
                result["patterns"] = result.get("patterns_pt", []) + result.get("patterns_en", [])
                
                logger.info(f"LLM analysis for template {template.get('id', 'unknown')}: {result}")
                return result
            else:
                logger.error(f"Invalid LLM response format: {result}")
                return {
                    "intent": "unknown",
                    "keywords": [],
                    "description": "Failed to analyze intent"
                }
        except Exception as e:
            logger.error(f"Error analyzing template with LLM: {str(e)}")
            return {
                "intent": "unknown",
                "keywords": [],
                "description": f"Error: {str(e)}"
            }
            
    def generate_content(self, template: Dict[str, Any], concept: Dict[str, Any], temperature: float = 0.7, max_tokens: int = 500) -> str:
        """Generates content using a specific template.
        
        Args:
            template: Template to be used
            concept: Dictionary with concept information
            temperature: Randomness control (0.0 to 1.0)
            max_tokens: Maximum number of tokens
            
        Returns:
            Generated content
        """
        # Preparar parâmetros baseados no conceito
        parameters = {
            "concept_name": concept.get("name", ""),
            "concept_description": concept.get("description", ""),
            "concept_type": concept.get("type", ""),
            "concept_properties": concept.get("properties", {})
        }
        
        # Generate content using the template
        # Note: LLMPromptManager.fill_and_generate doesn't accept temperature and max_tokens
        # Let's fill the template manually and use the LLM directly
        
        # Preencher o template usando string.format()
        template_content = template.get("content", "")
        try:
            # Substituir variáveis no formato {{var}} por seus valores
            for key, value in parameters.items():
                placeholder = "{{" + key + "}}"
                template_content = template_content.replace(placeholder, str(value))
                
            # Adicionar instruções de temperatura no prompt, já que não podemos passar como parâmetro
            if temperature > 0.7:
                template_content = f"Instrução: Seja criativo e variável em suas respostas.\n\n{template_content}"
            elif temperature < 0.3:
                template_content = f"Instrução: Seja conciso e direto em suas respostas.\n\n{template_content}"
                
            # Generate text using the LLM (without extra parameters that are not supported)
            return self.llm.generate_text(template_content)
        except Exception as e:
            logger.error(f"Error filling template: {str(e)}")
            raise ValueError(f"Error filling template: {str(e)}")
            
    def generate_structured(self, template: Dict[str, Any], concept: Dict[str, Any], temperature: float = 0.7, max_tokens: int = 500) -> Dict[str, Any]:
        """Generates structured content using a template.
        
        Args:
            template: Template to be used
            concept: Dictionary with concept information
            temperature: Randomness control (0.0 to 1.0)
            max_tokens: Maximum number of tokens
            
        Returns:
            Generated structured content
        """
        # Implementação similar ao generate_content, mas para conteúdo estruturado
        # Esta é uma implementação básica que pode ser expandida conforme necessário
        
        try:
            # Preencher o template e gerar conteúdo estruturado
            template_id = template.get("id") or template.get("template_id")
            filled_template = self.fill_structured_template(template_id, concept)
            return filled_template
        except Exception as e:
            logger.error(f"Error generating structured content: {str(e)}")
            return {"error": str(e)}
