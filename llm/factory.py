"""
Factory para criar instâncias de LLMs.
"""

from typing import Type
from .interface import LLMInterface
from .chatgpt import ChatGPTConnector

class LLMFactory:
    """Factory para criar instâncias de LLMs."""
    
    @staticmethod
    def create_llm() -> Type[LLMInterface]:
        """Cria uma instância de LLM.
        
        Returns:
            Instância de LLM
        """
        return ChatGPTConnector()
