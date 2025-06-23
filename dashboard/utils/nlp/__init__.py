"""
Pacote de processamento de linguagem natural para o OntoMed.
Este pacote contém componentes para processamento de texto, reconhecimento de entidades,
detecção de intenções e análise de dependência sintática.
"""

from .processor import NLPProcessor
from .models import Entity, Intent

__all__ = ['NLPProcessor', 'Entity', 'Intent']
