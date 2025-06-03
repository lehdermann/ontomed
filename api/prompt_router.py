#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Prompt endpoints for the OntoMed API.
Provides REST endpoints for interacting with the prompt module.
"""

import os
import sys
import yaml
import tempfile
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List, Dict, Any

# Add the current directory to the path so we can import the modules
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from prompt.manager import PromptManager
from prompt.validator import PromptValidator

from models import Template, TemplateFill, SuccessResponse, ErrorResponse

# Create router
router = APIRouter(
    prefix="/api",
    tags=["prompt"],
    responses={404: {"model": ErrorResponse}}
)

# Dependency to get prompt manager
def get_prompt_manager():
    """
    Dependency to get a prompt manager instance.
    
    Returns:
        PromptManager: Prompt manager instance
    """
    # Obter o diretório de templates
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    templates_dir = os.path.join(base_dir, "prompt", "templates")
    
    # Verificar se o diretório existe
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir, exist_ok=True)
        print(f"Criado diretório de templates: {templates_dir}")
    
    # Criar o gerenciador com o diretório de templates
    manager = PromptManager(templates_dir=templates_dir)
    
    # Verificar se há templates carregados
    templates = manager.list_templates()
    print(f"Templates carregados: {len(templates)}")
    
    try:
        yield manager
    finally:
        pass

@router.get("/templates/", response_model=List[Dict[str, str]])
async def list_templates(manager: PromptManager = Depends(get_prompt_manager)):
    """
    List all available templates.
    
    Args:
        manager: Prompt manager instance
        
    Returns:
        List[Dict[str, str]]: List of templates with ID and description
    """
    try:
        templates = manager.list_templates()
        return templates
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing templates: {str(e)}")

@router.get("/templates/{template_id}", response_model=Template)
async def get_template(template_id: str, manager: PromptManager = Depends(get_prompt_manager)):
    """
    Get a template by ID.
    
    Args:
        template_id: ID of the template to get
        manager: Prompt manager instance
        
    Returns:
        Template: The requested template
    """
    try:
        template = manager.get_template(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        
        # Convert to API model
        return Template(
            template_id=template.get("template_id", ""),
            description=template.get("description", ""),
            template=template.get("template", ""),
            parameters=template.get("parameters", {}),
            examples=template.get("examples", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving template: {str(e)}")

@router.post("/generate/text/{template_id}")
async def generate_text(template_id: str, params: Dict[str, Any], manager: PromptManager = Depends(get_prompt_manager)):
    """
    Generate text content using a template.
    
    Args:
        template_id: ID of the template to use
        params: Parameters for generation (concept, temperature, etc.)
        manager: Prompt manager instance
        
    Returns:
        str: Generated text content
    """
    try:
        # Extrair parâmetros
        concept = params.get("concept", {})
        temperature = params.get("temperature", 0.7)
        max_tokens = params.get("max_tokens", 500)
        
        # Gerar conteúdo
        content = manager.generate_content(
            template_id=template_id,
            data=concept,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating text: {str(e)}")

@router.post("/generate/structured/{template_id}")
async def generate_structured(template_id: str, params: Dict[str, Any], manager: PromptManager = Depends(get_prompt_manager)):
    """
    Generate structured content using a template.
    
    Args:
        template_id: ID of the template to use
        params: Parameters for generation (concept, temperature, etc.)
        manager: Prompt manager instance
        
    Returns:
        Dict: Generated structured content
    """
    try:
        # Extrair parâmetros
        concept = params.get("concept", {})
        temperature = params.get("temperature", 0.7)
        max_tokens = params.get("max_tokens", 500)
        
        # Gerar conteúdo estruturado
        content = manager.generate_structured(
            template_id=template_id,
            data=concept,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating structured content: {str(e)}")

@router.post("/generate/embedding/{template_id}")
async def generate_embedding(template_id: str, params: Dict[str, Any], manager: PromptManager = Depends(get_prompt_manager)):
    """
    Generate embedding for a concept using a template.
    
    Args:
        template_id: ID of the template to use
        params: Parameters for generation (concept)
        manager: Prompt manager instance
        
    Returns:
        List[float]: Generated embedding
    """
    try:
        # Extrair parâmetros
        concept = params.get("concept", {})
        
        # Gerar embedding
        embedding = manager.get_embedding(
            template_id=template_id,
            data=concept
        )
        
        return embedding
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating embedding: {str(e)}")

@router.post("/templates/", response_model=SuccessResponse, status_code=201)
async def create_template(template: Template, manager: PromptManager = Depends(get_prompt_manager)):
    """
    Create a new template.
    
    Args:
        template: Template to create
        manager: Prompt manager instance
        
    Returns:
        SuccessResponse: Success message
    """
    try:
        # Convert to internal format
        template_data = {
            "template_id": template.template_id,
            "description": template.description,
            "template": template.template,
            "parameters": template.parameters,
        }
        
        if template.examples:
            template_data["examples"] = template.examples
        
        # Add the template
        success = manager.add_template(template_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create template")
        
        return SuccessResponse(
            message=f"Template {template.template_id} created successfully",
            data={"template_id": template.template_id}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating template: {str(e)}")

@router.post("/templates/upload/", response_model=SuccessResponse, status_code=201)
async def upload_template(
    file: UploadFile = File(...),
    manager: PromptManager = Depends(get_prompt_manager),
    validator: PromptValidator = Depends(lambda: PromptValidator())
):
    """
    Upload a template file (YAML or JSON).
    
    Args:
        file: Template file to upload
        manager: Prompt manager instance
        validator: Prompt validator instance
        
    Returns:
        SuccessResponse: Success message
    """
    try:
        # Check file extension
        _, ext = os.path.splitext(file.filename)
        if ext.lower() not in ['.yaml', '.yml', '.json']:
            raise HTTPException(
                status_code=400, 
                detail="Unsupported file format. Must be YAML or JSON."
            )
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as temp_file:
            # Write the uploaded file content to the temporary file
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Validate and load the template
            template = validator.validate_template_file(temp_file_path)
            
            # Add the template
            success = manager.add_template(template)
            
            if not success:
                raise HTTPException(status_code=500, detail="Failed to add template")
            
            return SuccessResponse(
                message=f"Template {template.get('template_id')} uploaded successfully",
                data={"template_id": template.get('template_id')}
            )
        finally:
            # Clean up the temporary file
            os.unlink(temp_file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading template: {str(e)}")

@router.post("/fill/", response_model=Dict[str, Any])
async def fill_template(fill_request: TemplateFill, manager: PromptManager = Depends(get_prompt_manager)):
    """
    Fill a template with parameters.
    
    Args:
        fill_request: Template fill request
        manager: Prompt manager instance
        
    Returns:
        Dict[str, Any]: Response with filled template
    """
    try:
        # Fill the template
        filled_template = manager.fill_template(
            fill_request.template_id,
            fill_request.parameters
        )
        
        return {
            "template_id": fill_request.template_id,
            "filled_template": filled_template
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error filling template: {str(e)}")
