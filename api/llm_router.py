from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from llm.chatgpt import ChatGPTConnector
from llm.factory import LLMFactory

router = APIRouter()

# Modelo para requisição de geração de texto
class TextGenerationRequest(BaseModel):
    prompt: str
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 500
    template_id: Optional[str] = None

# Modelo para requisição de embedding
class EmbeddingRequest(BaseModel):
    text: str

@router.post(
    "/generate",
    summary="Generate content using LLM",
    description="""
    Generate content using the LLM based on a prompt. Optionally, a template can be used to guide the generation.
    
    Parameters:
    - prompt: The text prompt to generate content from
    - temperature: Controls randomness in generation (0.0 to 1.0)
    - max_tokens: Maximum number of tokens in the generated content
    - template_id: Optional ID of a template to use for generation
    """,
    response_description="Generated content"
)
async def generate_content(request: TextGenerationRequest):
    """Gera conteúdo usando o LLM.
    
    Args:
        request: Dados da requisição
        
    Returns:
        Conteúdo gerado
    """
    try:
        # Criar instância do LLM
        llm = LLMFactory.create('chatgpt')
        
        # Se houver template_id, obter o template
        if request.template_id:
            # Aqui seria implementada a lógica para buscar o template
            pass
        
        # Gerar o conteúdo
        generated_content = llm.generate_text(request.prompt)
        
        return {
            "success": True,
            "content": generated_content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/embedding",
    summary="Generate text embedding",
    description="""
    Generate a vector embedding for the given text using the LLM's embedding model.
    
    Parameters:
    - text: The text to generate embedding for
    """,
    response_description="Text embedding"
)
async def get_embedding(request: EmbeddingRequest):
    """Gera embedding para um texto.
    
    Args:
        request: Dados da requisição
        
    Returns:
        Embedding do texto
    """
    try:
        # Criar instância do LLM
        llm = LLMFactory.create('chatgpt')
        
        # Gerar o embedding
        embedding = llm.get_embedding(request.text)
        
        return {
            "success": True,
            "embedding": embedding
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/structured",
    summary="Generate structured response",
    description="""
    Generate a structured JSON response using the LLM.
    
    Parameters:
    - prompt: The text prompt to generate response from
    - temperature: Controls randomness in generation (0.0 to 1.0)
    - max_tokens: Maximum number of tokens in the generated content
    """,
    response_description="Structured response"
)
async def generate_structured(request: TextGenerationRequest):
    """Gera resposta estruturada usando o LLM.
    
    Args:
        request: Dados da requisição
        
    Returns:
        Resposta estruturada
    """
    try:
        # Criar instância do LLM
        llm = LLMFactory.create('chatgpt')
        
        # Gerar a resposta estruturada
        response = llm.generate_structured(request.prompt)
        
        return {
            "success": True,
            "response": response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
