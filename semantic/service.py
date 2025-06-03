#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Service layer for interacting with graph databases in MedKnowBridge.
Implements the Service pattern to provide a high-level API for semantic operations.
"""

import logging
import datetime
from typing import Dict, List, Set, Tuple, Any, Optional, Union
from rdflib import Graph, URIRef, Literal, Namespace, BNode

from .interface import GraphDatabaseInterface
from .factory import GraphDatabaseFactory

logger = logging.getLogger(__name__)

class GraphDatabaseService:
    """
    Service for interacting with graph databases.
    Provides high-level operations for managing medical knowledge.
    """
    
    def __init__(self, connector_type: str = "memory", **connector_args):
        """
        Initializes the graph database service.
        
        Args:
            connector_type: Type of connector to use (default: "memory")
            **connector_args: Arguments to pass to the connector constructor
        """
        self.factory = GraphDatabaseFactory()
        self.connector_type = connector_type
        self.connector_args = connector_args
        self.connector = None
        self.connected = False
        
    def connect(self) -> bool:
        """
        Connects to the graph database.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.connector = self.factory.create_connector(
                self.connector_type, **self.connector_args
            )
            
            self.connected = self.connector.connect()
            
            if self.connected:
                logger.info(f"Connected to graph database using {self.connector_type} connector")
                self._setup_namespaces()
            else:
                logger.error(f"Failed to connect to graph database")
                
            return self.connected
        except Exception as e:
            logger.error(f"Error connecting to graph database: {e}")
            self.connector = None
            self.connected = False
            return False
            
    def _setup_namespaces(self) -> None:
        """
        Sets up namespaces in the graph database.
        """
        if not self.connected or not self.connector:
            logger.error("Cannot set up namespaces: not connected to the graph database")
            return
            
        # Configure essential namespaces for the medical ontology
        # Divide into essential and optional namespaces
        essential_namespaces = {
            "med": "http://example.org/medical-ontology#",
            "agent": "http://example.org/agent-ontology#"
        }
        
        optional_namespaces = {
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "owl": "http://www.w3.org/2002/07/owl#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "skos": "http://www.w3.org/2004/02/skos/core#",
            "time": "http://www.w3.org/2006/time#"
        }
        
        # Create essential namespaces - failure here is critical
        for prefix, uri in essential_namespaces.items():
            try:
                logger.info(f"Creating essential namespace: {prefix}")
                success = self.connector.create_namespace(prefix, uri)
                if not success:
                    logger.warning(f"Could not create essential namespace {prefix}. "
                                  f"The system may not function correctly.")
            except Exception as e:
                logger.warning(f"Error creating essential namespace {prefix}: {e}. "
                              f"The system may not function correctly.")
        
        # Create optional namespaces - failure here is just logged
        for prefix, uri in optional_namespaces.items():
            try:
                logger.info(f"Creating optional namespace: {prefix}")
                success = self.connector.create_namespace(prefix, uri)
                if not success:
                    logger.info(f"Optional namespace {prefix} was not created. "
                               f"Some advanced features may be limited.")
            except Exception as e:
                logger.info(f"Optional namespace {prefix} was not created: {e}. "
                           f"Some advanced features may be limited.")
            
    def disconnect(self) -> bool:
        """
        Disconnects from the graph database.
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        if self.connected and self.connector:
            try:
                success = self.connector.disconnect()
                if success:
                    logger.info("Disconnected from graph database")
                else:
                    logger.warning("Failed to disconnect from graph database")
                    
                self.connected = not success
                return success
            except Exception as e:
                logger.error(f"Error disconnecting from graph database: {e}")
                return False
        
        self.connected = False
        return True
        
    def import_rdflib_graph(self, graph: Graph, context: Optional[str] = None) -> bool:
        """
        Imports an RDFLib graph into the graph database.
        
        Args:
            graph: RDFLib graph to import
            context: Optional context name for the graph
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.connected or not self.connector:
                logger.error("Cannot import graph: not connected to the graph database")
                return False
                
            # Delegate to connector
            return self.connector.import_rdflib_graph(graph, context)
            
        except Exception as e:
            logger.error(f"Error importing RDFLib graph: {str(e)}")
            return False
            
    def is_connected(self) -> bool:
        """
        Checks if connected to the graph database.
        
        Returns:
            bool: True if connected, False otherwise
        """
        if not self.connector:
            return False
            
        try:
            self.connected = self.connector.is_connected()
            return self.connected
        except Exception as e:
            logger.error(f"Error checking connection status: {e}")
            self.connected = False
            return False
            
    def get_concepts(self) -> List[Dict[str, Any]]:
        """
        Retrieves all concepts from the graph database.
        
        Returns:
            List[Dict[str, Any]]: List of concepts with their properties
        """
        if not self.connected or not self.connector:
            logger.error("Cannot get concepts: not connected to the graph database")
            return []
            
        try:
            # Build SPARQL query with proper namespace
            query = """
            SELECT DISTINCT ?concept ?label ?type ?description
            WHERE {
                ?concept a ?type .
                ?concept rdfs:label ?label .
                OPTIONAL { ?concept rdfs:comment ?description }
            }
            """
            
            # Execute query
            results = self.connector.execute_query(query)
            
            # Convert results to list of dictionaries
            concepts = []
            for binding in results:
                concept = {
                    'id': binding.get('concept', {}).get('value'),
                    'name': binding.get('label', {}).get('value'),  
                    'type': binding.get('type', {}).get('value'),
                    'description': binding.get('description', {}).get('value')
                }
                concepts.append(concept)
            
            return concepts
            
        except Exception as e:
            logger.error(f"Error getting concepts: {str(e)}")
            return []

    def get_graph_statistics(self) -> Dict[str, int]:
        """
        Retrieves statistics about the graph database.
        
        Returns:
            Dict[str, int]: Dictionary with graph statistics
        """
        if not self.connected or not self.connector:
            logger.error("Cannot get graph statistics: not connected to the graph database")
            return {
                'total_concepts': 0,
                'total_relationships': 0,
                'class_count': 0,
                'subclass_count': 0,
                'annotation_count': 0,
                'axiom_count': 0,
                'property_count': 0
            }
            
        try:
            return self.connector.get_statistics()
        except Exception as e:
            logger.error(f"Error getting graph statistics: {str(e)}")
            return {
                'total_concepts': 0,
                'total_relationships': 0,
                'class_count': 0,
                'subclass_count': 0,
                'annotation_count': 0,
                'axiom_count': 0,
                'property_count': 0
            }

    def query_concept(self, concept_id: str, relationship_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Queries information about a medical concept.
        
        Args:
            concept_id: ID of the concept
            relationship_type: Optional type of relationships to query
            
        Returns:
            Dictionary containing concept information
        """
        if not self.connected or not self.connector:
            logger.error("Cannot query concept: not connected to the graph database")
            return {}
            
        try:
            # Build SPARQL query
            query = self._build_query("concept", {
                "concept_id": concept_id,
                "relationship_type": relationship_type
            })
            
            # Execute query
            results = self.connector.execute_query(query)
            
            # Process results
            concept_data = {
                "id": concept_id,
                "relationships": []
            }
            
            for result in results:
                if "relationship" in result:
                    # Extrair o tipo de relacionamento da URI
                    relationship_value = result.get("relationship", {})
                    relationship_str = relationship_value.get("value", "") if isinstance(relationship_value, dict) else str(relationship_value)
                    
                    # Extrair o alvo da URI
                    target_value = result.get("target", {})
                    target_str = target_value.get("value", "") if isinstance(target_value, dict) else str(target_value)
                    
                    # Extrair o nome legível do alvo
                    target_label = result.get("targetLabel", {})
                    label_str = target_label.get("value", "") if isinstance(target_label, dict) else str(target_label)
                    
                    # Extrair a parte após o último # ou / para obter um nome mais legível
                    relationship_name = relationship_str.split("#")[-1] if "#" in relationship_str else relationship_str.split("/")[-1]
                    target_name = target_str.split("#")[-1] if "#" in target_str else target_str.split("/")[-1]
                    
                    relationship = {
                        "type": relationship_name,
                        "target": target_name,
                        "label": label_str
                    }
                    concept_data["relationships"].append(relationship)
                    
                elif "targetLabel" in result:
                    target_label = result.get("targetLabel", {})
                    concept_data["label"] = target_label.get("value", "") if isinstance(target_label, dict) else str(target_label)
                    
            return concept_data
        except Exception as e:
            logger.error(f"Error querying concept {concept_id}: {e}")
            return {}
            
    def store_concept(self, concept_id: str, concept_data: Dict[str, Any]) -> bool:
        """
        Stores a medical concept in the graph database.
        
        Args:
            concept_id: ID of the concept
            concept_data: Concept data to store
            
        Returns:
            bool: True if storage was successful, False otherwise
        """
        if not self.connected or not self.connector:
            logger.error("Cannot store concept: not connected to the graph database")
            return False
            
        try:
            # Create a temporary graph
            g = Graph()
            
            # Add namespace bindings
            g.bind("med", "http://example.org/medical-ontology#")
            g.bind("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#")
            g.bind("rdfs", "http://www.w3.org/2000/01/rdf-schema#")
            
            # Create concept URI
            concept_uri = URIRef(f"http://example.org/medical-ontology#{concept_id}")
            
            # Add concept type
            g.add((concept_uri, URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), 
                   URIRef("http://example.org/medical-ontology#Concept")))
            
            # Add label if provided
            if "label" in concept_data:
                g.add((concept_uri, URIRef("http://www.w3.org/2000/01/rdf-schema#label"), 
                       Literal(concept_data["label"])))
            
            # Add relationships
            for relationship in concept_data.get("relationships", []):
                rel_type = relationship.get("type")
                target_id = relationship.get("target")
                
                if rel_type and target_id:
                    target_uri = URIRef(f"http://example.org/medical-ontology#{target_id}")
                    g.add((concept_uri, URIRef(f"http://example.org/medical-ontology#{rel_type}"), 
                           target_uri))
            
            # Import the graph
            result = self.connector.import_rdflib_graph(g, context=f"concept_{concept_id}")
            
            if result:
                logger.info(f"Stored concept {concept_id}")
            else:
                logger.error(f"Failed to store concept {concept_id}")
                
            return result
        except Exception as e:
            logger.error(f"Error storing concept {concept_id}: {e}")
            return False
            
    def list_concepts(self) -> List[Dict[str, str]]:
        """
        Lists all concepts in the graph.
        
        Returns:
            List[Dict[str, str]]: List of concepts with their IDs and labels
        """
        try:
            if not self.connected:
                logger.warning("Attempting to list concepts while not connected")
                if not self.connect():
                    logger.error("Failed to connect before listing concepts")
                    return []
            
            logger.info("Starting concept listing")
            concepts = self.connector.get_concepts()
            logger.info(f"Retrieved {len(concepts)} concepts")
            return concepts
            
        except Exception as e:
            logger.error(f"Error listing concepts: {e}", exc_info=True)
            return []


    def _build_query(self, query_type: str, query_params: Dict[str, Any]) -> str:
        """
        Builds a SPARQL query based on type and parameters.
        
        Args:
            query_type: Type of query to build
            query_params: Parameters for the query
            
        Returns:
            SPARQL query string
        """
        if query_type == "concept":
            concept_id = query_params.get("concept_id")
            relationship_type = query_params.get("relationship_type")
            
            if not concept_id:
                return ""
            
            # Usar URI completa entre <> em vez de prefixo para evitar problemas com caracteres especiais
            concept_uri = f"<{concept_id}>" if not concept_id.startswith("<") else concept_id
            
            if relationship_type:
                relationship_uri = f"<{relationship_type}>" if not relationship_type.startswith("<") else relationship_type
                return f"""
                    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                    
                    SELECT ?target ?targetLabel
                    WHERE {{
                        {concept_uri} {relationship_uri} ?target .
                        OPTIONAL {{ ?target rdfs:label ?targetLabel }}
                    }}
                """
            else:
                return f"""
                    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                    
                    SELECT ?relationship ?target ?targetLabel
                    WHERE {{
                        {concept_uri} ?relationship ?target .
                        OPTIONAL {{ ?target rdfs:label ?targetLabel }}
                    }}
                """
        else:
            logger.warning(f"Unknown query type: {query_type}")
            return ""
