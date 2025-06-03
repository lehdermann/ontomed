"""
Interface para LLMs (Large Language Models).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List

class LLMInterface(ABC):
    """Interface base para LLMs."""
    
    @abstractmethod
    def generate_text(self, prompt: str) -> str:
        """Gera texto baseado em um prompt.
        
        Args:
            prompt: Prompt para o LLM
            
        Returns:
            Texto gerado
        """
        pass
    
    @abstractmethod
    def generate_structured(self, prompt: str) -> Dict[str, Any]:
        """Gera conteúdo estruturado baseado em um prompt.
        
        Args:
            prompt: Prompt para o LLM
            
        Returns:
            Dicionário com o conteúdo estruturado
        """
        pass
    
    @abstractmethod
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Analisa um texto e retorna informações relevantes.
        
        Args:
            text: Texto a ser analisado
            
        Returns:
            Análise do texto
        """
        pass
    
    @abstractmethod
    def generate_embeddings(self, text: str) -> List[float]:
        """Gera embeddings para um texto.
        
        Args:
            text: Texto para gerar embeddings
            
        Returns:
            Lista de embeddings
        """
        pass
