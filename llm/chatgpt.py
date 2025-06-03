"""
Conector para o ChatGPT API.
"""

import json
from typing import Dict, Any, List
import os
from dotenv import load_dotenv
from .interface import LLMInterface
import openai

class ChatGPTConnector(LLMInterface):
    """Conector para o ChatGPT API."""
    
    def __init__(self):
        """Inicializa o conector."""
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY não configurada")
        
        openai.api_key = self.api_key
    
    def generate_text(self, prompt: str) -> str:
        """Gera texto baseado em um prompt.
        
        Args:
            prompt: Prompt para o LLM
            
        Returns:
            Texto gerado
        """
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Erro ao gerar texto: {str(e)}")
    
    def generate_structured(self, prompt: str) -> Dict[str, Any]:
        """Gera conteúdo estruturado baseado em um prompt.
        
        Args:
            prompt: Prompt para o LLM
            
        Returns:
            Dicionário com o conteúdo estruturado
        """
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": f"{prompt}\nResponda no formato JSON:"}
                ]
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            raise Exception(f"Erro ao gerar conteúdo estruturado: {str(e)}")
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Analisa um texto e retorna informações relevantes.
        
        Args:
            text: Texto a ser analisado
            
        Returns:
            Análise do texto
        """
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": f"Analise o seguinte texto:\n{text}\n\nForneça uma análise detalhada no formato JSON:"}
                ]
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            raise Exception(f"Erro ao analisar texto: {str(e)}")
    
    def generate_embeddings(self, text: str) -> List[float]:
        """Gera embeddings para um texto.
        
        Args:
            text: Texto para gerar embeddings
            
        Returns:
            Lista de embeddings
        """
        try:
            response = openai.embeddings.create(
                input=text,
                model="text-embedding-ada-002"
            )
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"Erro ao gerar embeddings: {str(e)}")
