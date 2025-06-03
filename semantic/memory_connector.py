#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
In-memory graph database connector implementation for MedKnowBridge.
Provides a simple implementation that stores all data in memory.
"""

import logging
from typing import Dict, List, Set, Tuple, Any, Optional, Union
import rdflib
from rdflib import Graph, URIRef, Literal, Namespace

from .interface import GraphDatabaseInterface

logger = logging.getLogger(__name__)

class MemoryConnector(GraphDatabaseInterface):
    """
    Implementation of GraphDatabaseInterface that stores all data in memory.
    Useful for testing, development, and small datasets.
    """
    
    def __init__(self):
        """
        Initializes the in-memory connector.
        """
        self.graph = None
        self.namespaces = {}
        self.connected = False
        
    def connect(self) -> bool:
        """
        Establishes a connection (creates a new in-memory graph).
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.graph = Graph()
            self.connected = True
            logger.info("Connected to in-memory graph database")
            return True
        except Exception as e:
            logger.error(f"Error connecting to in-memory graph database: {e}")
            self.graph = None
            self.connected = False
            return False
    
    def disconnect(self) -> bool:
        """
        Terminates the connection (clears the in-memory graph).
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        if self.graph:
            try:
                self.graph = None
                self.connected = False
                logger.info("Disconnected from in-memory graph database")
                return True
            except Exception as e:
                logger.error(f"Error disconnecting from in-memory graph database: {e}")
                return False
        return True
    
    def is_connected(self) -> bool:
        """
        Checks if the connection is active.
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self.connected and self.graph is not None
    
    def create_namespace(self, prefix: str, uri: str) -> bool:
        """
        Creates a namespace in the graph.
        
        Args:
            prefix: Namespace prefix
            uri: Namespace URI
            
        Returns:
            bool: True if namespace was created successfully, False otherwise
        """
        if not self.is_connected():
            logger.error("Cannot create namespace: not connected")
            return False
            
        try:
            self.graph.bind(prefix, uri)
            self.namespaces[prefix] = uri
            logger.info(f"Created namespace: {prefix} -> {uri}")
            return True
        except Exception as e:
            logger.error(f"Error creating namespace {prefix}: {e}")
            return False
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Executes a SPARQL query against the graph.
        
        Args:
            query: SPARQL query string
            params: Optional parameters for the query
            
        Returns:
            List of dictionaries containing query results
            
        Raises:
            Exception: If query execution fails
        """
        if not self.is_connected():
            logger.error("Cannot execute query: not connected")
            return []
            
        try:
            # Execute the query
            results = self.graph.query(query)
            
            # Convert results to list of dictionaries
            result_list = []
            for row in results:
                result_dict = {}
                for var_name in results.vars:
                    if var_name in row:
                        value = row[var_name]
                        # Convert URIRef to string
                        if isinstance(value, URIRef):
                            result_dict[var_name] = str(value)
                        # Convert Literal to Python primitive
                        elif isinstance(value, Literal):
                            result_dict[var_name] = value.value
                        else:
                            result_dict[var_name] = str(value)
                result_list.append(result_dict)
                
            logger.info(f"Query executed successfully, returned {len(result_list)} results")
            return result_list
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise
    
    def import_rdflib_graph(self, graph: Graph, context: Optional[str] = None) -> bool:
        """
        Imports an RDFLib graph into the in-memory graph.
        
        Args:
            graph: RDFLib graph to import
            context: Optional named graph/context (ignored in this implementation)
            
        Returns:
            bool: True if import was successful, False otherwise
        """
        if not self.is_connected():
            logger.error("Cannot import graph: not connected")
            return False
            
        try:
            # Import all triples
            for s, p, o in graph:
                self.graph.add((s, p, o))
                
            # Import namespace bindings
            for prefix, namespace in graph.namespaces():
                if prefix and namespace:  # Ignore empty bindings
                    self.graph.bind(prefix, namespace)
                    
            logger.info(f"Imported {len(graph)} triples into in-memory graph")
            return True
        except Exception as e:
            logger.error(f"Error importing graph: {e}")
            return False
    
    def list_triples(self, limit: int = 100) -> List[Dict[str, str]]:
        """
        Lista todas as triplas do grafo.

        Args:
            limit: Número máximo de triplas a retornar

        Returns:
            Lista de triplas no formato {"subject": str, "predicate": str, "object": str}
        """
        if not self.is_connected():
            logger.error("Cannot list triples: not connected")
            return []

        try:
            # Usa o método nativo do rdflib para listar triplas
            triples = []
            for s, p, o in self.graph:
                triples.append({
                    'subject': str(s),
                    'predicate': str(p),
                    'object': str(o)
                })
                if len(triples) >= limit:
                    break
            
            return triples
        except Exception as e:
            logger.error(f"Error listing triples: {e}")
            return []

    def get_all_concepts(self) -> List[dict]:
        """
        Retrieves all concepts stored in the in-memory graph.

        Returns:
            List[dict]: A list of dictionaries representing the concepts.
        """
        if not self.is_connected():
            logger.error("Cannot retrieve concepts: not connected")
            return []

        try:
            query = """
            PREFIX med: <http://example.org/medical-ontology#>
            SELECT ?concept ?label
            WHERE {
                ?concept a med:Concept .
                OPTIONAL { ?concept rdfs:label ?label }
            }
            """
            results = self.execute_query(query)
            return [{"id": res.get("concept", ""), "label": res.get("label", "")} for res in results]
        except Exception as e:
            logger.error(f"Error retrieving concepts: {e}")
            return []


    def import_graph(self, graph_data: Union[str, bytes], format: str = 'turtle') -> bool:
        """
        Imports RDF data into the graph.
        
        Args:
            graph_data: RDF data as string or bytes
            format: Format of the RDF data (default: 'turtle')
            
        Returns:
            bool: True if import successful, False otherwise
        """
        if not self.is_connected():
            logger.error("Cannot import graph: not connected")
            return False
            
        try:
            # Parse the RDF data into a temporary graph
            temp_graph = Graph()
            
            # Handle both string and bytes input
            if isinstance(graph_data, bytes):
                temp_graph.parse(data=graph_data.decode('utf-8'), format=format)
            else:
                temp_graph.parse(data=graph_data, format=format)
            
            # Add all triples to the main graph
            for triple in temp_graph:
                self.graph.add(triple)
                
            logger.info(f"Successfully imported {len(temp_graph)} triples into the graph")
            return True
            
        except Exception as e:
            logger.error(f"Error importing graph data: {e}")
            return False
            
    def export_to_rdflib_graph(self, context: Optional[str] = None) -> Graph:
        """
        Exports data from the in-memory graph to a new RDFLib graph.
        
        Args:
            context: Optional named graph/context (ignored in this implementation)
            
        Returns:
            RDFLib Graph containing the exported data
        """
        if not self.is_connected():
            logger.error("Cannot export graph: not connected")
            return Graph()
            
        try:
            # Create a new graph
            exported_graph = Graph()
            
            # Copy all triples
            for s, p, o in self.graph:
                exported_graph.add((s, p, o))
                
            # Copy namespace bindings
            for prefix, namespace in self.graph.namespaces():
                if prefix and namespace:  # Ignore empty bindings
                    exported_graph.bind(prefix, namespace)
                    
            logger.info(f"Exported {len(exported_graph)} triples from in-memory graph")
            return exported_graph
        except Exception as e:
            logger.error(f"Error exporting graph: {e}")
            return Graph()
