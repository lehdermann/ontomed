from typing import Dict, Any, List
import os
import yaml
import logging
from typing import Dict, List, Any, Optional
from llm.interface import LLMInterface
from prompt.llm_integration import LLMPromptManager

logger = logging.getLogger(__name__)

class TemplateManager:
    """Template manager for content generation."""
    
    def __init__(self, llm: LLMInterface):
        """Initializes the template manager.
        
        Args:
            llm: LLM interface for generation
        """
        self.llm = llm
        self.prompt_manager = LLMPromptManager(llm)
        self.templates = []
        self.templates_dir = self._get_templates_dir()
        self._load_templates_from_disk()
    
    def create_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a new template.
        
        Args:
            template_data: Template data
            
        Returns:
            Created template
        """
        # Validate template data
        required_fields = ["name", "type", "content", "variables"]
        for field in required_fields:
            if field not in template_data:
                raise ValueError(f"Required field '{field}' not found")
        
        # Criar ID único
        template_id = f"temp_{len(self.templates) + 1}"
        
        # Adicionar template
        template = {
            "id": template_id,
            **template_data
        }
        self.templates.append(template)
        
        return template
    
    def get_template(self, template_id: str) -> Dict[str, Any]:
        """Gets a template by ID.
        
        Args:
            template_id: Template ID
            
        Returns:
            Found template
        """
        template = next((t for t in self.templates if t["id"] == template_id), None)
        if not template:
            raise ValueError(f"Template with ID {template_id} not found")
        return template
    
    def update_template(self, template_id: str, updated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Updates an existing template.
        
        Args:
            template_id: Template ID
            updated_data: Updated data
            
        Returns:
            Updated template
        """
        # Find template
        template = self.get_template(template_id)
        
        # Update data
        for key, value in updated_data.items():
            if key != "id":
                template[key] = value
        
        return template
    
    def delete_template(self, template_id: str) -> None:
        """Deletes a template.
        
        Args:
            template_id: Template ID
        """
        # Find and remove template
        self.templates = [t for t in self.templates if t["id"] != template_id]
    
    def get_templates(self) -> List[Dict[str, Any]]:
        """Gets all templates.
        
        Returns:
            List of templates
        """
        return self.templates
    
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
        template_content = template["content"]
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
            Structured content
        """
        # Preparar parâmetros baseados no conceito
        parameters = {
            "concept_name": concept.get("name", ""),
            "concept_description": concept.get("description", ""),
            "concept_type": concept.get("type", ""),
            "concept_properties": concept.get("properties", {})
        }
        
        # Generate structured content using the template
        # Note: LLMPromptManager.fill_and_generate_structured doesn't accept temperature and max_tokens
        # Let's fill the template manually and use the LLM directly
        
        # Preencher o template usando string.format()
        template_content = template["content"]
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
                
            # Generate structured content using the LLM (without extra parameters that are not supported)
            return self.llm.generate_structured(template_content)
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
    
    def _load_templates_from_disk(self) -> None:
        """Loads templates from the file system."""
        if not os.path.exists(self.templates_dir):
            logger.warning(f"Templates directory not found: {self.templates_dir}")
            return
        
        # Clear existing templates
        self.templates = []
        
        # List YAML files in the templates directory
        for filename in os.listdir(self.templates_dir):
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                try:
                    # Full path to the file
                    file_path = os.path.join(self.templates_dir, filename)
                    
                    # Load template from file
                    with open(file_path, "r", encoding="utf-8") as f:
                        template_data = yaml.safe_load(f)
                    
                    # Validate template data
                    if not template_data or not isinstance(template_data, dict):
                        logger.warning(f"Invalid template: {filename}")
                        continue
                    
                    # Extract template name from file
                    template_name = template_data.get("name", os.path.splitext(filename)[0])
                    
                    # Create unique ID based on filename
                    template_id = os.path.splitext(filename)[0]
                    
                    # Add template to the list
                    # Check if the template has 'content' or 'template' field
                    template_content = template_data.get("content", "")
                    if not template_content:
                        template_content = template_data.get("template", "")
                        if template_content:
                            logger.info(f"Template {template_id} uses the 'template' field instead of 'content'")
                    
                    template = {
                        "id": template_id,
                        "name": template_name,
                        "type": template_data.get("type", "text"),
                        "content": template_content,
                        "variables": [param.get("name") for param in template_data.get("parameters", [])],
                        "description": template_data.get("description", ""),
                        "status": "Active",
                        "category": template_data.get("metadata", {}).get("domain", "general")
                    }
                    
                    self.templates.append(template)
                    logger.info(f"Template loaded: {template_name} ({template_id})")
                    
                except Exception as e:
                    logger.error(f"Error loading template {filename}: {str(e)}")
        
        logger.info(f"Total templates loaded: {len(self.templates)}")
    
    def get_embedding(self, template_id: str, concept: Dict[str, Any]) -> List[float]:
        """Generates embedding for a concept using a specific template.
        
        Args:
            template_id: Template ID
            concept: Dictionary with concept information
            
        Returns:
            List of floats representing the embedding
        """
        try:
            # Get template
            template = self.get_template(template_id)
            if not template:
                logger.error(f"Template not found: {template_id}")
                return []
                
            # Extract template content
            template_content = template.get("content", "")
            
            if not template_content:
                # Reload templates from disk to ensure we have the most recent data
                logger.warning(f"Template {template_id} has no content. Reloading templates...")
                self._load_templates_from_disk()
                
                # Try to get the template again
                template = self.get_template(template_id)
                if not template:
                    logger.error(f"Template {template_id} not found after reload")
                    return []
                    
                template_content = template.get("content", "")
                if not template_content:
                    logger.error(f"Template {template_id} has no content after reload")
                    # Display debug information about the template
                    logger.debug(f"Template content: {template}")
                    return []
                
            # Prepare parameters based on the concept
            parameters = {
                "concept_name": concept.get("concept_name", concept.get("name", concept.get("label", ""))),
                "concept_description": concept.get("concept_description", concept.get("description", "")),
                "concept_type": concept.get("concept_type", concept.get("type", "")),
                "concept_properties": concept.get("concept_properties", concept.get("properties", {}))
            }
            
            # Check if we have enough information
            if not parameters["concept_name"] and not parameters["concept_description"]:
                logger.warning(f"Concept without name or description: {concept}")
                
            # Generate embedding using template content
            logger.info(f"Generating embedding for concept: {parameters['concept_name']}")
            logger.info(f"Template content: {template_content[:100]}...")
            return self.prompt_manager.get_embedding(template_content, parameters)
        except Exception as e:
            logger.error(f"Error generating embedding with template {template_id}: {str(e)}")
            # Return an empty embedding as fallback
            return []
