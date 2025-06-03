#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Validator for prompt templates in MedKnowBridge.
Ensures that templates follow the expected schema and contain all required fields.
"""

import logging
import os
import yaml
import json
import jsonschema
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)

class PromptValidator:
    """
    Validator for prompt templates.
    Ensures that templates follow the expected schema and contain all required fields.
    """
    
    def __init__(self):
        """
        Initializes the prompt validator with the base schema.
        """
        # Define the base schema for prompt templates
        self.base_schema = {
            "type": "object",
            "required": ["template_id", "description", "template", "parameters"],
            "properties": {
                "template_id": {"type": "string"},
                "description": {"type": "string"},
                "template": {"type": "string"},
                "parameters": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "object",
                        "required": ["type", "description"],
                        "properties": {
                            "type": {"type": "string", "enum": ["string", "number", "boolean", "array", "object"]},
                            "description": {"type": "string"},
                            "required": {"type": "boolean"},
                            "default": {}
                        }
                    }
                },
                "examples": {
                    "type": "array",
                    "items": {"type": "object"}
                }
            }
        }
        
    def validate_template_file(self, template_path: str) -> Dict[str, Any]:
        """
        Validates a template file against the schema.
        
        Args:
            template_path: Path to the template file (YAML or JSON)
            
        Returns:
            Dictionary containing the validated template
            
        Raises:
            FileNotFoundError: If template file doesn't exist
            yaml.YAMLError: If template file is not valid YAML
            jsonschema.exceptions.ValidationError: If template doesn't match schema
        """
        if not os.path.exists(template_path):
            error_msg = f"Template file not found: {template_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
            
        # Determine file type from extension
        _, ext = os.path.splitext(template_path)
        
        try:
            # Load template from file
            with open(template_path, 'r') as f:
                if ext.lower() in ['.yaml', '.yml']:
                    template = yaml.safe_load(f)
                elif ext.lower() == '.json':
                    template = json.load(f)
                else:
                    error_msg = f"Unsupported template file format: {ext}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                    
            # Validate template against schema
            self.validate_template(template)
            
            logger.info(f"Template validated successfully: {template_path}")
            return template
        except yaml.YAMLError as e:
            error_msg = f"Invalid YAML in template file: {e}"
            logger.error(error_msg)
            raise
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in template file: {e}"
            logger.error(error_msg)
            raise
        except Exception as e:
            error_msg = f"Error validating template file: {e}"
            logger.error(error_msg)
            raise
            
    def validate_template(self, template: Dict[str, Any]) -> None:
        """
        Validates a template against the schema.
        
        Args:
            template: Template to validate
            
        Raises:
            jsonschema.exceptions.ValidationError: If template doesn't match schema
        """
        try:
            jsonschema.validate(instance=template, schema=self.base_schema)
            
            # Additional validation for parameter references in template
            self._validate_parameter_references(template)
            
        except jsonschema.exceptions.ValidationError as e:
            error_msg = f"Template validation failed: {e.message}"
            logger.error(error_msg)
            raise
            
    def _validate_parameter_references(self, template: Dict[str, Any]) -> None:
        """
        Validates that all parameter references in the template string exist in the parameters object.
        
        Args:
            template: Template to validate
            
        Raises:
            ValueError: If template contains references to undefined parameters
        """
        template_str = template.get("template", "")
        parameters = template.get("parameters", {})
        
        # Find all parameter references in the template string
        import re
        param_refs = set(re.findall(r'\{([^{}]+)\}', template_str))
        
        # Check that all referenced parameters are defined
        undefined_params = param_refs - set(parameters.keys())
        if undefined_params:
            error_msg = f"Template contains references to undefined parameters: {', '.join(undefined_params)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # Check that all required parameters are referenced
        required_params = {name for name, param in parameters.items() 
                          if param.get("required", False)}
        unreferenced_required = required_params - param_refs
        if unreferenced_required:
            logger.warning(f"Required parameters not referenced in template: {', '.join(unreferenced_required)}")
            
    def validate_parameters(self, template: Dict[str, Any], parameters: Dict[str, Any]) -> None:
        """
        Validates that the provided parameters match the expected schema.
        
        Args:
            template: Template to validate against
            parameters: Parameters to validate
            
        Raises:
            ValueError: If parameters are invalid
        """
        template_params = template.get("parameters", {})
        
        # Check for missing required parameters
        missing_params = []
        for name, param_schema in template_params.items():
            if param_schema.get("required", False) and name not in parameters:
                missing_params.append(name)
                
        if missing_params:
            error_msg = f"Missing required parameters: {', '.join(missing_params)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # Check for unexpected parameters
        unexpected_params = set(parameters.keys()) - set(template_params.keys())
        if unexpected_params:
            logger.warning(f"Unexpected parameters provided: {', '.join(unexpected_params)}")
            
        # Validate parameter types
        type_errors = []
        for name, value in parameters.items():
            if name in template_params:
                param_type = template_params[name].get("type")
                if param_type == "string" and not isinstance(value, str):
                    type_errors.append(f"{name} should be a string")
                elif param_type == "number" and not isinstance(value, (int, float)):
                    type_errors.append(f"{name} should be a number")
                elif param_type == "boolean" and not isinstance(value, bool):
                    type_errors.append(f"{name} should be a boolean")
                elif param_type == "array" and not isinstance(value, list):
                    type_errors.append(f"{name} should be an array")
                elif param_type == "object" and not isinstance(value, dict):
                    type_errors.append(f"{name} should be an object")
                    
        if type_errors:
            error_msg = f"Parameter type errors: {'; '.join(type_errors)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
