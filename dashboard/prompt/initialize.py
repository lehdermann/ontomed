"""
Script to initialize system templates.
This script loads templates from the templates/ directory and registers them in PromptManager.
"""

import os
import yaml
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_template_file(filepath: str) -> Dict[str, Any]:
    """
    Load a template file.
    
    Args:
        filepath: Path to the template file
        
    Returns:
        Dictionary with the template content
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            if filepath.endswith('.yaml') or filepath.endswith('.yml'):
                return yaml.safe_load(f)
            else:
                logger.warning(f"Unsupported file format: {filepath}")
                return {}
    except Exception as e:
        logger.error(f"Error loading template {filepath}: {e}")
        return {}

def register_concept_embedding_template() -> None:
    """
    Registers the concept_embedding template in PromptManager.
    """
    # Import here to avoid circular import issues
    from prompt.manager import PromptManager
    
    # Get the PromptManager instance (singleton)
    manager = PromptManager()
    
    # Path to the templates directory
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    
    # Path to the template file
    template_path = os.path.join(templates_dir, 'concept_embedding.yaml')
    
    # Check if the file exists
    if not os.path.exists(template_path):
        logger.error(f"Template not found: {template_path}")
        
        # Create the template if it doesn't exist
        os.makedirs(os.path.dirname(template_path), exist_ok=True)
        
        template_data = {
            'template_id': 'concept_embedding',
            'name': 'Concept Embedding Template',
            'description': 'Template for generating embeddings for medical concepts',
            'version': '1.0',
            'type': 'embedding',
            'template': 'Concept: {{concept_name}}\nDescription: {{concept_description}}\nType: {{concept_type}}\nProperties: {{concept_properties}}',
            'parameters': [
                {'name': 'concept_name', 'description': 'Name of the medical concept', 'required': True},
                {'name': 'concept_description', 'description': 'Description of the concept', 'required': False},
                {'name': 'concept_type', 'description': 'Type or category of the concept', 'required': False},
                {'name': 'concept_properties', 'description': 'Additional properties of the concept', 'required': False}
            ],
            'metadata': {
                'domain': 'medical',
                'usage': 'embedding',
                'author': 'OntoMed'
            }
        }
        
        # Save the template
        try:
            with open(template_path, 'w', encoding='utf-8') as f:
                yaml.dump(template_data, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"Template created: {template_path}")
        except Exception as e:
            logger.error(f"Error creating template: {e}")
            return
    
    # Load the template
    template_data = load_template_file(template_path)
    if not template_data:
        logger.error(f"Failed to load template: {template_path}")
        return
    
    # Register the template
    try:
        # Add directly to the templates dictionary
        template_id = template_data.get('template_id')
        if template_id:
            manager.templates[template_id] = template_data
            logger.info(f"Template registered: {template_id}")
        else:
            logger.error(f"Template without ID: {template_path}")
    except Exception as e:
        logger.error(f"Error registering template: {e}")

def initialize():
    """
    Initializes the system templates.
    """
    # Register the concept_embedding template
    register_concept_embedding_template()
    
    logger.info("Templates initialized successfully")

# Run initialization if the script is executed directly
if __name__ == "__main__":
    initialize()
