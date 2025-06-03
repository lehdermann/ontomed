#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Abstract interface for graph database connectors in MedKnowBridge.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Set, Tuple, Any, Optional, Union
import rdflib
from rdflib import Graph

logger = logging.getLogger(__name__)

class GraphDatabaseInterface(ABC):
    """
    Abstract interface for graph database connectors.
    Defines the contract that all concrete implementations must follow.
    """
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Establishes a connection to the graph database.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def clear_database(self) -> bool:
        """
        Clears all data from the graph database.
        
        Returns:
            bool: True if clearing was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        Terminates the connection to the graph database.
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Checks if the connection to the graph database is active.
        
        Returns:
            bool: True if connected, False otherwise
        """
        pass
    
    @abstractmethod
    def create_namespace(self, prefix: str, uri: str) -> bool:
        """
        Creates a namespace in the graph database.
        
        Args:
            prefix: Namespace prefix
            uri: Namespace URI
            
        Returns:
            bool: True if namespace was created successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Executes a SPARQL query against the graph database.
        
        Args:
            query: SPARQL query string
            params: Optional parameters for the query
            
        Returns:
            List of dictionaries containing query results
            
        Raises:
            Exception: If query execution fails
        """
        pass
    
    @abstractmethod
    def import_rdflib_graph(self, graph: Graph, context: Optional[str] = None) -> bool:
        """
        Imports an RDFLib graph into the graph database.
        
        Args:
            graph: RDFLib graph to import
            context: Optional named graph/context
            
        Returns:
            bool: True if import was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def export_to_rdflib_graph(self, context: Optional[str] = None) -> Graph:
        """
        Exports data from the graph database to an RDFLib graph.
        
        Args:
            context: Optional named graph/context to export
            
        Returns:
            RDFLib Graph containing the exported data
        """
        pass
