#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Manager for prompt templates in MedKnowBridge.
Provides methods for loading, validating, and filling prompt templates.
"""

import logging
import os
import sys
import json
import yaml
import datetime
from typing import Dict, List, Any, Optional, Union
from string import Formatter

# Importar o conector ChatGPT
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from llm.chatgpt import ChatGPTConnector

from .validator import PromptValidator

# Define Singleton metaclass locally to avoid import issues
class Singleton(type):
    """Singleton metaclass for ensuring only one instance of a class exists."""
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

logger = logging.getLogger(__name__)

class PromptManager(metaclass=Singleton):
    """
    Manager for prompt templates.
    Implements the Singleton pattern to ensure only one manager exists.
    """
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize the prompt manager.
        
        Args:
            templates_dir: Directory containing template files
        """
        # Initialize validator
        self.validator = PromptValidator()
        
        # Initialize template storage
        self.templates = {}
        self.templates_dir = templates_dir
        
        # Initialize the LLM connector
        try:
            self.llm = ChatGPTConnector()
            logger.info("ChatGPT connector initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize ChatGPT connector: {e}. Using fallback.")
            self.llm = None
            
        # Load templates if directory is provided
        if templates_dir:
            self.load_templates(templates_dir)
            
    def load_templates(self, templates_dir: str) -> None:
        """
        Loads all templates from a directory.
        
        Args:
            templates_dir: Directory containing template files
        """
        if not os.path.exists(templates_dir) or not os.path.isdir(templates_dir):
            error_msg = f"Templates directory not found: {templates_dir}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
            
        # Track loaded templates
        loaded_count = 0
        error_count = 0
        
        # Load all YAML and JSON files in the directory
        for filename in os.listdir(templates_dir):
            filepath = os.path.join(templates_dir, filename)
            
            # Skip directories and non-template files
            if os.path.isdir(filepath):
                continue
                
            _, ext = os.path.splitext(filename)
            if ext.lower() not in ['.yaml', '.yml', '.json']:
                continue
                
            try:
                # Load file content
                with open(filepath, 'r', encoding='utf-8') as f:
                    if ext.lower() in ['.yaml', '.yml']:
                        template_data = yaml.safe_load(f)
                    else:  # .json
                        template_data = json.load(f)
                
                # Check if template is valid
                if not template_data or not isinstance(template_data, dict):
                    logger.warning(f"Invalid template in {filepath}: not a dictionary")
                    error_count += 1
                    continue
                
                # Get or generate a template ID
                template_id = template_data.get("template_id", None)
                if not template_id:
                    # Use filename as ID
                    template_id = os.path.splitext(os.path.basename(filepath))[0]
                    logger.info(f"Using filename as template_id: {template_id}")
                
                # Ensure template has a name
                if "name" not in template_data:
                    template_data["name"] = template_id.replace('_', ' ').title()
                
                # Store the template
                self.templates[template_id] = template_data
                loaded_count += 1
                logger.info(f"Loaded template: {template_id} from {filepath}")
                
            except Exception as e:
                logger.error(f"Error loading template from {filepath}: {e}")
                error_count += 1
                
        logger.info(f"Loaded {loaded_count} templates from {templates_dir} ({error_count} errors)")
        
    def add_template(self, template: Dict[str, Any]) -> bool:
        """
        Adds a template to the manager.
        
        Args:
            template: Template to add
            
        Returns:
            bool: True if template was added successfully, False otherwise
        """
        try:
            # Validate the template
            self.validator.validate_template(template)
            
            template_id = template.get("template_id")
            if not template_id:
                logger.error("Template missing template_id")
                return False
                
            # Check for duplicate template_id
            if template_id in self.templates:
                logger.warning(f"Overwriting existing template: {template_id}")
                
            # Store the template
            self.templates[template_id] = template
            logger.info(f"Added template: {template_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding template: {e}")
            return False
            
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Gets a template by ID.
        
        Args:
            template_id: ID of the template to get
            
        Returns:
            Template dictionary, or None if not found
        """
        template = self.templates.get(template_id)
        if not template:
            logger.warning(f"Template not found: {template_id}")
            
        return template
        
    def fill_template(self, template_id: str, parameters: Dict[str, Any]) -> str:
        """
        Fills a template with parameters.
        
        Args:
            template_id: ID of the template to fill
            parameters: Parameters to fill the template with
            
        Returns:
            Filled template string
            
        Raises:
            ValueError: If template not found or parameters are invalid
        """
        # Get the template
        template = self.get_template(template_id)
        if not template:
            error_msg = f"Template not found: {template_id}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # Validate parameters
        self.validator.validate_parameters(template, parameters)
        
        # Fill the template
        template_str = template.get("template", "")
        
        try:
            # Apply default values for missing parameters
            template_params = template.get("parameters", {})
            for name, param_schema in template_params.items():
                if name not in parameters and "default" in param_schema:
                    parameters[name] = param_schema["default"]
            
            # Fill the template using string formatting
            filled_template = template_str.format(**parameters)
            logger.info(f"Filled template: {template_id}")
            return filled_template
            
        except KeyError as e:
            error_msg = f"Missing parameter in template: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Error filling template: {e}"
            logger.error(error_msg)
            raise
            
    def list_templates(self) -> List[Dict[str, Any]]:
        """
        Lists all available templates.
        
        Returns:
            List of dictionaries containing template information
        """
        # Check if there are any templates loaded
        if not self.templates:
            logger.warning("No templates loaded. Checking templates directory.")
            # If no templates, try loading again
            if self.templates_dir and os.path.exists(self.templates_dir):
                self.load_templates(self.templates_dir)
        
        # Return complete template information
        return [
            {
                "id": template_id,
                "name": template.get("name", template_id),
                "type": template.get("type", "text"),
                "description": template.get("description", ""),
                "category": template.get("metadata", {}).get("domain", "general")
            }
            for template_id, template in self.templates.items()
        ]
        
    def generate_content(self, template_id: str, data: Dict[str, Any], temperature: float = 0.7, max_tokens: int = 500) -> str:
        """
        Generates text content using a template.
        
        Args:
            template_id: ID of the template to use
            data: Data to fill the template with
            temperature: Temperature for generation (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            str: Generated text content
        """
        try:
            # Check if template exists
            if template_id not in self.templates:
                error_msg = f"Template not found: {template_id}"
                logger.error(error_msg)
                return f"Error: {error_msg}"
            
            # Get the template
            template = self.templates[template_id]
            
            # Check if template has 'template' field
            if "template" not in template:
                error_msg = f"Template {template_id} does not have a 'template' field"
                logger.error(error_msg)
                return f"Error: {error_msg}"
            
            # Fill the template with data
            prompt = self._fill_template(template["template"], data)
            
            # Generate content using LLM
            logger.info(f"Generating content with template {template_id}")
            
            # Check if LLM connector is available
            if self.llm:
                try:
                    # Use ChatGPT connector to generate content
                    content = self.llm.generate_text(prompt)
                    logger.info(f"Content generated successfully using ChatGPT")
                    return content
                except Exception as e:
                    logger.error(f"Error generating content with ChatGPT: {str(e)}. Using fallback.")
            
            # Fallback: return simulated content
            logger.warning("Using simulated content generator (fallback)")
            content = f"Generated content for concept {data.get('display_name', data.get('id', 'unknown'))}\n\n"
            content += f"This is an example of generated content using template '{template.get('name', template_id)}'.\n"
            content += f"In a real system, this text would be generated by an LLM based on the prompt:\n\n{prompt}"
            
            return content
            
        except Exception as e:
            error_msg = f"Error generating content: {str(e)}"
            logger.error(error_msg)
            return f"Erro: {error_msg}"
    
    def generate_structured(self, template_id: str, data: Dict[str, Any], temperature: float = 0.7, max_tokens: int = 500) -> Dict[str, Any]:
        """
        Generates structured content using a template.
        
        Args:
            template_id: ID of the template to use
            data: Data to fill the template with
            temperature: Temperature for generation (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            Dict[str, Any]: Generated structured content
        """
        try:
            # Check if template exists
            if template_id not in self.templates:
                error_msg = f"Template not found: {template_id}"
                logger.error(error_msg)
                return {"error": error_msg}
            
            # Get the template
            template = self.templates[template_id]
            
            # Check if template has 'template' field
            if "template" not in template:
                error_msg = f"Template {template_id} does not have a 'template' field"
                logger.error(error_msg)
                return {"error": error_msg}
            
            # Fill the template with data
            prompt = self._fill_template(template["template"], data)
            
            # Generate structured content using LLM
            logger.info(f"Generating structured content with template {template_id}")
            
            # Check if LLM connector is available
            if self.llm:
                try:
                    # Use ChatGPT connector to generate structured content
                    structured_content = self.llm.generate_structured(prompt)
                    logger.info(f"Structured content generated successfully using ChatGPT")
                    return structured_content
                except Exception as e:
                    logger.error(f"Error generating structured content with ChatGPT: {str(e)}. Using fallback.")
            
            # Fallback: return simulated structured content
            logger.warning("Using simulated structured content generator (fallback)")
            structured_content = {
                "concept": data.get("display_name", data.get("id", "unknown")),
                "template_used": template.get("name", template_id),
                "properties": {
                    "description": f"Generated description for {data.get('display_name', 'concept')}",
                    "examples": ["Example 1", "Example 2", "Example 3"],
                    "related_concepts": ["Related concept 1", "Related concept 2"]
                },
                "metadata": {
                    "generated_at": datetime.datetime.now().isoformat(),
                    "prompt_used": prompt
                }
            }
            
            return structured_content
            
        except Exception as e:
            error_msg = f"Error generating structured content: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    def get_embedding(self, template_id: str, data: Dict[str, Any]) -> List[float]:
        """
        Generates an embedding for the given data using a template.
        
        Args:
            template_id: ID of the template to use
            data: Data to fill the template with
            
        Returns:
            List[float]: Generated embedding
        """
        try:
            # Check if template exists
            if template_id not in self.templates:
                error_msg = f"Template not found: {template_id}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Get the template
            template = self.templates[template_id]
            
            # Check if template has 'template' field
            if "template" not in template:
                error_msg = f"Template {template_id} does not have a 'template' field"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Fill the template with data
            prompt = self._fill_template(template["template"], data)
            
            # Generate embedding using LLM
            logger.info(f"Generating embedding with template {template_id}")
            
            # Check if LLM connector is available
            if self.llm:
                try:
                    # Use ChatGPT connector to generate the embedding
                    embedding = self.llm.generate_embeddings(prompt)
                    logger.info(f"Embedding generated successfully using ChatGPT")
                    return embedding
                except Exception as e:
                    logger.error(f"Error generating embedding with ChatGPT: {str(e)}. Using fallback.")
            
            # Fallback: return simulated embedding
            logger.warning("Using simulated embedding generator (fallback)")
            import random
            embedding = [random.uniform(-1.0, 1.0) for _ in range(32)]
            
            return embedding
            
        except Exception as e:
            error_msg = f"Error generating embedding: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _fill_template(self, template_text: str, data: Dict[str, Any]) -> str:
        """
        Fills a template with data.
        
        Args:
            template_text: Template text with placeholders
            data: Data to fill the template with
            
        Returns:
            str: Filled template
        """
        try:
            # Create a copy of the data to avoid modifying the original
            context = data.copy() if data else {}
            
            # Process the template using Jinja2
            from jinja2 import Template
            jinja_template = Template(template_text)
            filled_template = jinja_template.render(**context)
            
            return filled_template
            
        except Exception as e:
            error_msg = f"Error filling template: {str(e)}"
            logger.error(error_msg)
            return f"Erro: {error_msg}"
