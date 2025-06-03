#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Data models for the OntoMed API.
Defines Pydantic models for request and response objects.
"""

from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field

class ConceptRelationship(BaseModel):
    """Model for a relationship between concepts."""
    type: str = Field(..., description="Type of relationship")
    target: str = Field(..., description="Target concept ID")
    label: Optional[str] = Field(None, description="Human-readable label for the target concept")

class Concept(BaseModel):
    """Model for a medical concept."""
    id: str = Field(..., description="Unique identifier for the concept")
    label: Optional[str] = Field(None, description="Human-readable label for the concept")
    relationships: List[ConceptRelationship] = Field(default_factory=list, 
                                                    description="Relationships to other concepts")

class ConceptCreate(BaseModel):
    """Model for creating a new concept."""
    id: str = Field(..., description="Unique identifier for the concept")
    label: Optional[str] = Field(None, description="Human-readable label for the concept")
    relationships: List[ConceptRelationship] = Field(default_factory=list, 
                                                    description="Relationships to other concepts")

class ConceptQuery(BaseModel):
    """Model for querying concepts."""
    concept_id: str = Field(..., description="ID of the concept to query")
    relationship_type: Optional[str] = Field(None, 
                                           description="Optional type of relationships to filter by")

class TemplateParameter(BaseModel):
    """Model for a template parameter."""
    type: str = Field(..., description="Parameter type (string, number, boolean, array, object)")
    description: str = Field(..., description="Description of the parameter")
    required: bool = Field(default=False, description="Whether the parameter is required")
    default: Optional[Any] = Field(None, description="Default value for the parameter")

class Template(BaseModel):
    """Model for a prompt template."""
    template_id: str = Field(..., description="Unique identifier for the template")
    description: str = Field(..., description="Description of the template")
    template: str = Field(..., description="Template string with parameter placeholders")
    parameters: Dict[str, TemplateParameter] = Field(..., 
                                                   description="Parameters for the template")
    examples: Optional[List[Dict[str, Any]]] = Field(None, 
                                                   description="Example parameter values")

class TemplateFill(BaseModel):
    """Model for filling a template with parameters."""
    template_id: str = Field(..., description="ID of the template to fill")
    parameters: Dict[str, Any] = Field(..., description="Parameter values to fill the template with")

class ErrorResponse(BaseModel):
    """Model for error responses."""
    detail: str = Field(..., description="Error message")

class SuccessResponse(BaseModel):
    """Model for success responses."""
    message: str = Field(..., description="Success message")
    data: Optional[Any] = Field(None, description="Response data")
