"""
Template manager for the OntoMed dashboard.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional, List
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Singleton(type):
    """
    Metaclass to implement the Singleton pattern.
    """
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class PromptManager(metaclass=Singleton):
    """
    Template manager for the OntoMed dashboard.
    """
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize the template manager.
        
        Args:
            templates_dir: Directory where templates are stored
        """
        self.templates = {}
        
        if templates_dir is None:
            # Use the default directory
            self.templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
        else:
            self.templates_dir = templates_dir
            
        # Load templates
        self._load_templates()
    
    def _load_templates(self) -> None:
        """
        Load all templates from the templates directory.
        """
        if not os.path.exists(self.templates_dir):
            logger.warning(f"Templates directory not found: {self.templates_dir}")
            return
            
        for filename in os.listdir(self.templates_dir):
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                filepath = os.path.join(self.templates_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        template_data = yaml.safe_load(f)
                        
                    # Check if the template has an ID
                    template_id = template_data.get('template_id')
                    if template_id:
                        self.templates[template_id] = template_data
                        logger.info(f"Template loaded: {template_id}")
                    else:
                        logger.warning(f"Template without ID: {filepath}")
                except Exception as e:
                    logger.error(f"Error loading template {filepath}: {e}")
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a template by ID.
        
        Args:
            template_id: Template ID
            
        Returns:
            Template or None if not found
        """
        template = self.templates.get(template_id)
        if template is None:
            logger.warning(f"Template not found: {template_id}")
        return template
    
    def fill_template(self, template_id: str, parameters: Dict[str, Any]) -> Optional[str]:
        """
        Fill a template with the provided parameters.
        
        Args:
            template_id: Template ID
            parameters: Parameters to fill the template
            
        Returns:
            Filled template or None if the template is not found
        """
        template = self.get_template(template_id)
        if template is None:
            return None
            
        template_content = template.get('template', '')
        
        # Fill the template
        for param_name, param_value in parameters.items():
            placeholder = f"{{{{{param_name}}}}}"
            template_content = template_content.replace(placeholder, str(param_value))
            
        return template_content
    
    def get_embedding(self, template_name: str, parameters: Dict[str, Any]) -> List[float]:
        """
        Generate embeddings for a concept using the specified template.
        
        Args:
            template_name: Template name
            parameters: Template parameters
            
        Returns:
            List of embeddings (empty if template is not found)
        """
        # Return an empty list as fallback
        return []
