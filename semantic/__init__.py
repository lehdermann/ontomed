"""
Semantic module for OntoMed.
Provides graph database connectors and services for managing medical knowledge.
"""

from .interface import GraphDatabaseInterface
from .service import GraphDatabaseService
from .factory import GraphDatabaseFactory

__all__ = ['GraphDatabaseInterface', 'GraphDatabaseService', 'GraphDatabaseFactory']
