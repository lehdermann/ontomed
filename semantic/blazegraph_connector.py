"""
Blazegraph graph database connector implementation for MedKnowBridge.
Provides a persistent storage solution using Blazegraph.
"""

import os
import logging
import requests
import re
from typing import Dict, Any, Optional, Tuple, List
import rdflib
from rdflib import Graph, URIRef, Literal, Namespace, BNode, RDF, RDFS, OWL
from pymantic import sparql

from .interface import GraphDatabaseInterface

logger = logging.getLogger(__name__)

class BlazegraphConnectionError(Exception):
    """Exception raised for connection errors."""
    pass

class BlazegraphNamespaceManager:
    """Manager for Blazegraph namespace administration via REST API."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self._session = requests.Session()
        
    def create_namespace(self, name: str) -> bool:
        """
        Creates a namespace in Blazegraph using REST API.
        
        Args:
            name: Namespace name
            
        Returns:
            bool: True if namespace was created successfully, False otherwise
        
        Raises:
            requests.RequestException: If the request fails
            ValueError: If the namespace name is invalid
        """
        if not name or not isinstance(name, str):
            raise ValueError("Namespace name must be a non-empty string")
            
        url = f"{self.base_url}/namespace"
        headers = {'Content-Type': 'text/plain'}
        data = f"""com.bigdata.namespace.{name}.spo.com.bigdata.btree.BTreeBranchingFactor=1024
com.bigdata.rdf.store.AbstractTripleStore.textIndex=false
com.bigdata.rdf.store.AbstractTripleStore.axiomsClass=com.bigdata.rdf.axioms.NoAxioms
com.bigdata.rdf.sail.namespace={name}
com.bigdata.rdf.store.AbstractTripleStore.quads=false
com.bigdata.namespace.{name}.lex.com.bigdata.btree.BTreeBranchingFactor=400
com.bigdata.rdf.store.AbstractTripleStore.statementIdentifiers=false
"""
        
        try:
            response = self._session.post(url, headers=headers, data=data)
            
            # If namespace already exists (409), consider it a success
            if response.status_code == 409:
                logger.info(f"Namespace '{name}' already exists.")
                return True
            
            # Raise for other status codes
            response.raise_for_status()
            
            if response.status_code == 201:
                logger.info(f"Namespace '{name}' created.")
                return True
            else:
                raise RuntimeError(f"Failed to create namespace: {response.status_code}, {response.text}")
                
        except requests.RequestException as e:
            logger.error(f"Namespace creation error: {e}")
            raise

class BlazegraphConnector(GraphDatabaseInterface):
    """
    Implementation of GraphDatabaseInterface that uses Blazegraph as the backend.
    Provides persistent storage for the graph database.
    """
    
    def __init__(self, base_url: str, namespace: str):
        """
        Initializes the Blazegraph connector.
        
        Args:
            base_url: Base URL of the Blazegraph server
            namespace: Namespace name for this connector
        """
        self.base_url = base_url
        self.namespace = namespace
        self.connected = False
        # Initialize namespace manager with proper arguments
        self._namespace_manager = BlazegraphNamespaceManager(
            base_url=base_url
        )
        
        # Initialize the SPARQL server with proper namespace bindings
        self.sparql_server = sparql.SPARQLServer(f"{base_url}/namespace/{namespace}/sparql")
        
        # Initialize graph with essential namespaces
        self.graph = Graph()
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("owl", OWL)
        self.graph.bind("onto", "https://w3id.org/hmarl-genai/ontology#")
        logger.info(f"[{namespace}] Connector initialized successfully")
        
        # Ensure namespace exists with proper binding
        if not self.create_namespace_if_not_exists(
            name=namespace,
            uri="https://w3id.org/hmarl-genai/ontology#",
            prefix="onto"
        ):
            raise ValueError(f"Failed to create namespace: {namespace}")
            
        self.graph.bind("onto", rdflib.URIRef("https://w3id.org/hmarl-genai/ontology#"))

    def connect(self) -> bool:
        """
        Establishes a connection to the Blazegraph database.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Test connection by checking namespace
            url = f"{self.base_url}/namespace/{self.namespace}/sparql"
            response = requests.get(url)
            if response.status_code == 200:
                self.connected = True
                logger.info(f"[{self.namespace}] Connected to Blazegraph")
                return True
            else:
                logger.error(f"[{self.namespace}] Failed to connect to Blazegraph: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"[{self.namespace}] Connection error: {str(e)}")
            return False

    def clear_database(self) -> bool:
        """
        Clears all data from the database.
        
        Returns:
            bool: True if clearing was successful, False otherwise
        """
        try:
            if not self.is_connected():
                raise BlazegraphConnectionError("Not connected to Blazegraph")
            
            # Clear the namespace
            url = f"{self.base_url}/namespace/{self.namespace}/sparql"
            headers = {'Content-Type': 'application/sparql-update'}
            
            # Clear all data
            update_query = """
            DELETE WHERE { ?s ?p ?o }
            """
            
            response = requests.post(url, headers=headers, data=update_query)
            response.raise_for_status()
            
            logger.info(f"[{self.namespace}] Cleared database namespace")
            return True
            
        except requests.RequestException as e:
            logger.error(f"[{self.namespace}] Error clearing database: {e}")
            return False

    def is_connected(self) -> bool:
        """
        Checks if the connection to Blazegraph is active.
        
        Returns:
            bool: True if connection is active, False otherwise
        """
        try:
            # Test connection by checking namespace
            url = f"{self.base_url}/namespace/{self.namespace}/sparql"
            response = requests.get(url)
            if response.status_code == 200:
                self.connected = True
                return True
            else:
                self.connected = False
                return False
        except Exception as e:
            logger.error(f"[{self.namespace}] Connection test error: {str(e)}")
            self.connected = False
            return False

    def disconnect(self) -> bool:
        """
        Terminates the connection to the Blazegraph database.
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        try:
            # Clear any session state
            self.connected = False
            logger.info(f"[{self.namespace}] Disconnected from Blazegraph")
            return True
        except Exception as e:
            logger.error(f"[{self.namespace}] Disconnection error: {str(e)}")
            return False
        
    def _format_sparql_value(self, value: Any) -> str:
        """
        Formats a Python value into a safe SPARQL string representation.
        
        Args:
            value: Value to format
            
        Returns:
            str: Safe SPARQL string representation
            
        Raises:
            ValueError: If value type is not supported
        """
        if isinstance(value, str):
            return rdflib.Literal(value).n3()
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, URIRef):
            return f"<{value}>"
        elif isinstance(value, BNode):
            return f"_:b{value}"
        elif isinstance(value, Literal):
            return value.n3()
        else:
            raise ValueError(f"Unsupported value type: {type(value)}")
    
    def _validate_uri(self, uri: str) -> str:
        """
        Validates and normalizes a URI string using rdflib.URIRef.
        
        Args:
            uri: URI string to validate
            
        Returns:
            str: Normalized URI string
            
        Raises:
            ValueError: If the URI is invalid
        """
        if not uri or not isinstance(uri, str):
            raise ValueError("URI must be a non-empty string")
            
        try:
            # Use rdflib.URIRef to validate and normalize the URI
            uri_ref = URIRef(uri)
            return str(uri_ref)
            
        except Exception as e:
            raise ValueError(f"Invalid URI format: {str(e)}")

    def create_namespace(self, name: str, uri: Optional[str] = None, prefix: Optional[str] = None) -> bool:
        """
        Creates a namespace in Blazegraph and binds it to the RDFLib graph if URI and prefix are given.
        
        Args:
            name: Name of the namespace (used in REST API and endpoint path).
            uri: Base URI for RDFLib binding (optional).
            prefix: Prefix for RDFLib binding (optional).
            
        Returns:
            bool: True if namespace was created or already exists.
            
        Raises:
            ValueError: If namespace name is invalid.
            BlazegraphConnectionError: If connection fails.
            Exception: For other unexpected errors.
        """
        try:
            if not name or not isinstance(name, str):
                raise ValueError("Namespace name must be a non-empty string")
            
            if not self.is_connected():
                raise BlazegraphConnectionError("Not connected to Blazegraph")
            
            # Create namespace using REST API
            namespace_created = self._namespace_manager.create_namespace(name)
            if namespace_created:
                logger.info(f"[{self.namespace}] Namespace '{name}' created.")
                
            # If URI and prefix are provided, bind them
            if uri and prefix:
                validated_uri = self._validate_uri(uri)
                self.graph.bind(prefix, URIRef(validated_uri))
                logger.info(f"[{self.namespace}] Bound prefix '{prefix}' to URI '{validated_uri}'")
            
            return True
            
        except ValueError as e:
            logger.error(f"[{self.namespace}] Value error creating namespace '{name}': {e}")
            raise
        except BlazegraphConnectionError as e:
            logger.error(f"[{self.namespace}] Connection error creating namespace '{name}': {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.namespace}] Unexpected error creating namespace '{name}': {e}")
            raise Exception(f"Failed to create namespace: {e}")

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Executes a SPARQL query against Blazegraph.
        
        Args:
            query: SPARQL query string
            
        Returns:
            List of dictionaries containing query results
            
        Raises:
            BlazegraphConnectionError: If connection fails
            Exception: For other unexpected errors
        """
        try:
            if not self.is_connected():
                raise BlazegraphConnectionError("Not connected to Blazegraph")
            
            logger.debug(f"[{self.namespace}] Executing query: {query}")
            # Execute query with UTF-8 encoding
            headers = {'Accept': 'application/sparql-results+json; charset=utf-8'}
            result = self.sparql_server.query(query, headers=headers)
            
            if not result or not result['results'] or not result['results']['bindings']:
                logger.info(f"[{self.namespace}] Query returned no results")
                return []
            
            logger.info(f"[{self.namespace}] Query returned {len(result['results']['bindings'])} results")
            
            # Convert all string values to ensure UTF-8 encoding
            results = []
            for binding in result['results']['bindings']:
                converted = {}
                for key, value in binding.items():
                    if isinstance(value, dict) and 'value' in value:
                        # Convert string values to ensure UTF-8 encoding
                        converted_value = str(value['value'])
                        converted[key] = {
                            'type': value['type'],
                            'value': converted_value
                        }
                    else:
                        converted[key] = value
                results.append(converted)
            return results
            
        except BlazegraphConnectionError as e:
            logger.error(f"[{self.namespace}] Connection error executing query: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.namespace}] Error executing query: {e}", exc_info=True)
            logger.debug(f"[{self.namespace}] Query that failed: {query}")
            raise Exception(f"Query execution failed: {e}")

    def connect(self) -> bool:
        """
        Establishes a connection to Blazegraph.
        
        Returns:
            bool: True if connection successful, False otherwise
            
        Raises:
            BlazegraphConnectionError: If connection fails
        """
        try:
            # Verify if already connected
            if self.connected:
                return True
            
            # Try to execute a simple query to test connection
            query = """
            SELECT (COUNT(?s) as ?count)
            WHERE { ?s ?p ?o }
            LIMIT 1
            """
            
            result = self.sparql_server.query(query)
            if result and result['results']['bindings']:
                logger.info(f"[{self.namespace}] Successfully connected to Blazegraph")
                self.connected = True
                return True
            
            logger.error(f"[{self.namespace}] Failed to connect to Blazegraph: empty response")
            raise BlazegraphConnectionError("Empty response from Blazegraph")
            
        except Exception as e:
            logger.error(f"[{self.namespace}] Connection error: {e}")
            raise BlazegraphConnectionError(f"Failed to connect: {e}")

    def is_connected(self) -> bool:
        """
        Checks if connected to the graph database.
        
        Returns:
            bool: True if connected, False otherwise
        """
        try:
            # First check if we have a valid sparql server
            if not self.sparql_server:
                logger.error(f"[{self.namespace}] No SPARQL server initialized")
                return False
            
            # Test connection by checking namespace
            url = f"{self.base_url}/namespace/{self.namespace}/sparql"
            response = requests.get(url)
            if response.status_code == 200:
                logger.info(f"[{self.namespace}] Successfully verified namespace connection")
                self.connected = True
                return True
            else:
                logger.error(f"[{self.namespace}] Namespace not found or empty")
                self.connected = False
                return False
        except Exception as e:
            logger.error(f"[{self.namespace}] Error checking connection status: {e}")
            self.connected = False
            return False

    def create_namespace_if_not_exists(self, name: Optional[str] = None, uri: Optional[str] = None, prefix: Optional[str] = None) -> bool:
        """
        Ensures a namespace is created and usable.
        
        Args:
            name: Name of the namespace (optional, uses current namespace if not provided)
            uri: Base URI for RDFLib binding (optional)
            prefix: Prefix for RDFLib binding (optional)
            
        Returns:
            bool: True if namespace exists or was created.
            
        Raises:
            ValueError: If name is invalid
        """
        try:
            # Use current namespace if not provided
            name = name or self.namespace
            if not name:
                raise ValueError("Namespace name cannot be empty")
            
            # Create namespace using NamespaceManager
            if not self._namespace_manager.create_namespace(name):
                raise Exception(f"Failed to create namespace: {name}")
            
            # If URI and prefix are provided, bind them
            if uri and prefix:
                validated_uri = self._validate_uri(uri)
                self.graph.bind(prefix, URIRef(validated_uri))
                logger.info(f"[{self.namespace}] Bound prefix '{prefix}' to URI '{validated_uri}'")
            
            return True
            
        except Exception as e:
            logger.error(f"[{self.namespace}] Error creating namespace '{name}': {e}")
            raise

    def disconnect(self) -> bool:
        """
        Terminates the connection to the Blazegraph database.
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        try:
            # Clear any session state
            self.connected = False
            self.sparql_server = None
            logger.info(f"[{self.namespace}] Disconnected from Blazegraph")
            return True
        except Exception as e:
            logger.error(f"[{self.namespace}] Error disconnecting: {e}")
            raise Exception(f"Failed to disconnect: {e}")

    def upload_ontology(self, ontology_file: str) -> bool:
        """
        Uploads an ontology file to Blazegraph.
        
        Args:
            ontology_file: Path to the ontology file
            
        Returns:
            bool: True if upload was successful, False otherwise
        
        Raises:
            FileNotFoundError: If ontology file is not found
            ValueError: If file format is not supported
            Exception: For other unexpected errors
        """
        try:
            if not self.is_connected():
                raise BlazegraphConnectionError("Not connected to Blazegraph")
        
            # Check if file exists
            if not os.path.exists(ontology_file):
                raise FileNotFoundError(f"Ontology file not found: {ontology_file}")
        
            raise requests.RequestException(f"Network error during upload: {e}")
        except BlazegraphConnectionError as e:
            logger.error(f"[{self.namespace}] Connection error uploading ontology: {e}")
            raise BlazegraphConnectionError(f"Failed to connect to Blazegraph: {e}")
        except Exception as e:
            logger.error(f"[{self.namespace}] Unexpected error uploading ontology: {e}")
            raise Exception(f"Failed to upload ontology: {e}")
    
            # Add namespace declarations to query
            namespace_declarations = []
            for prefix, uri in self.graph.namespaces():
                namespace_declarations.append(f"PREFIX {prefix}: <{uri}>")
            processed_query = "\n".join(namespace_declarations) + "\n" + processed_query
            
            # Execute the query
            result = self.sparql_server.query(processed_query)
            
            # Process results
            bindings = result.get('results', {}).get('bindings', [])
            processed_results = []
            
            for binding in bindings:
                processed_binding = {}
                for var, value in binding.items():
                    if value['type'] == 'uri':
                        processed_binding[var] = URIRef(value['value'])
                    elif value['type'] == 'literal':
                        if 'datatype' in value:
                            processed_binding[var] = Literal(value['value'], datatype=value['datatype'])
                        elif 'xml:lang' in value:
                            processed_binding[var] = Literal(value['value'], lang=value['xml:lang'])
                        else:
                            processed_binding[var] = Literal(value['value'])
                    elif value['type'] == 'bnode':
                        processed_binding[var] = BNode(value['value'])
                    else:
                        processed_binding[var] = value['value']
                
                processed_results.append(processed_binding)
            
            return processed_results
            
        except ValueError as e:
            logger.error(f"Value error executing query: {e}")
            raise
        except BlazegraphConnectionError as e:
            logger.error(f"Connection error executing query: {e}")
            raise
        except requests.RequestException as e:
            logger.error(f"Network error executing query: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error executing query: {e}")
            raise Exception(f"Query execution failed: {e}")

    def get_concepts(self) -> List[Dict[str, Any]]:
        """
        Retrieves all concepts from the graph with enhanced information.
        
        Returns:
            List[Dict[str, Any]]: List of concepts with their IDs, labels, types, descriptions and relationships
        """
        try:
            if not self.is_connected():
                logger.warning("Attempting to get concepts while not connected")
                if not self.connect():
                    return []
                    
            # Query for concepts with enhanced information
            query = """
            SELECT DISTINCT ?concept ?label ?type ?description
            WHERE {
                ?concept a ?type .
                OPTIONAL { ?concept rdfs:label ?label . }
                OPTIONAL { ?concept rdfs:comment ?description . }
            }
            """
            
            results = self.execute_query(query)
            
            if not results or not results['results'] or not results['results']['bindings']:
                logger.info(f"[{self.namespace}] Query returned no results")
                return []
            
            # Processar resultados para extrair informações completas
            concepts = []
            for res in results['results']['bindings']:
                # Extrair valores dos resultados
                concept_id = self._extract_value(res, "concept")
                label = self._extract_value(res, "label")
                concept_type = self._extract_value(res, "type")
                description = self._extract_value(res, "description")
                
                # Extrair nome legível do tipo
                type_name = ""
                if concept_type:
                    if "#" in concept_type:
                        type_name = concept_type.split("#")[-1]
                    elif "/" in concept_type:
                        type_name = concept_type.split("/")[-1]
                
                # Criar objeto do conceito com informações completas
                concept = {
                    "id": concept_id,
                    "label": label,
                    "type": type_name,
                    "description": description,
                    "relationships": []
                }
                
                concepts.append(concept)
            
            # Buscar relacionamentos para cada conceito
            self._load_relationships_for_concepts(concepts)
            
            logger.info(f"[{self.namespace}] Retrieved {len(concepts)} concepts with enhanced information")
            return concepts
        except Exception as e:
            logger.error(f"[{self.namespace}] Error executing concept query: {e}", exc_info=True)
            logger.debug(f"[{self.namespace}] Query that failed: {query}")
            return []
            
    def _extract_value(self, result_binding, key):
        """
        Extrai um valor do binding de resultado SPARQL de forma segura.
        
        Args:
            result_binding: O binding de resultado SPARQL
            key: A chave do valor a ser extraído
            
        Returns:
            str: O valor extraído ou string vazia se não encontrado
        """
        if key not in result_binding:
            return ""
            
        value_obj = result_binding[key]
        if "value" not in value_obj:
            return ""
            
        return value_obj["value"]
        
    def _load_relationships_for_concepts(self, concepts):
        """
        Carrega os relacionamentos para uma lista de conceitos.
        
        Args:
            concepts: Lista de conceitos para carregar relacionamentos
        """
        # Se não houver conceitos, não há nada a fazer
        if not concepts:
            return
            
        try:
            # Construir uma lista de IDs de conceitos para a consulta
            concept_ids = [f"<{concept['id']}>" for concept in concepts]
            concept_ids_str = " ".join(concept_ids)
            
            # Consulta para buscar relacionamentos
            query = f"""
            SELECT ?subject ?predicate ?object
            WHERE {{
                VALUES ?subject {{ {concept_ids_str} }}
                ?subject ?predicate ?object .
                FILTER(?predicate != rdf:type)
            }}
            """
            
            results = self.execute_query(query)
            
            if not results or not results['results'] or not results['results']['bindings']:
                logger.info(f"[{self.namespace}] No relationships found for concepts")
                return
                
            # Mapear conceitos por ID para facilitar a atualização
            concept_map = {concept["id"]: concept for concept in concepts}
            
            # Processar relacionamentos
            for res in results['results']['bindings']:
                subject_id = self._extract_value(res, "subject")
                predicate = self._extract_value(res, "predicate")
                object_id = self._extract_value(res, "object")
                
                # Extrair nomes legíveis
                predicate_name = predicate
                if "#" in predicate:
                    predicate_name = predicate.split("#")[-1]
                elif "/" in predicate:
                    predicate_name = predicate.split("/")[-1]
                    
                # Adicionar relacionamento ao conceito
                if subject_id in concept_map:
                    relationship = {
                        "predicate": predicate,
                        "predicate_name": predicate_name,
                        "object": object_id
                    }
                    concept_map[subject_id]["relationships"].append(relationship)
                    
        except Exception as e:
            logger.error(f"[{self.namespace}] Error loading relationships: {e}", exc_info=True)
            
        except Exception as e:
            logger.error(f"[{self.namespace}] Error executing concept query: {e}", exc_info=True)
            logger.debug(f"[{self.namespace}] Query that failed: {query}")
            logger.error(f"Error retrieving concepts: {e}")
            return []

    def get_statistics(self) -> Dict[str, int]:
        """
{{ ... }}
        Retrieves statistics about the graph.
        
        Returns:
            Dict[str, int]: Dictionary with graph statistics
        """
        try:
            if not self.is_connected():
                logger.warning("Attempting to get statistics while not connected")
                if not self.connect():
                    return {}

            # Query for total triples
            query_total = """
            SELECT (COUNT(*) as ?totalTriples)
            WHERE {
                ?s ?p ?o .
            }
            """

            # Query for number of concepts
            query_concepts = """
            SELECT (COUNT(DISTINCT ?concept) as ?numConcepts)
            WHERE {
                ?concept a owl:Class .
            }
            """

            # Query for number of relationships
            query_relationships = """
            SELECT (COUNT(DISTINCT ?relationship) as ?numRelationships)
            WHERE {
                ?relationship a owl:ObjectProperty .
            }
            """
            
            # Query for number of classes
            query_classes = """
            SELECT (COUNT(DISTINCT ?class) as ?numClasses)
            WHERE {
                ?class a owl:Class .
                FILTER(!isBlank(?class))
            }
            """
            
            # Query for number of subclasses
            query_subclasses = """
            SELECT (COUNT(?subclass) as ?numSubclasses)
            WHERE {
                ?subclass rdfs:subClassOf ?superclass .
                ?subclass a owl:Class .
                ?superclass a owl:Class .
                FILTER(?subclass != ?superclass)
                FILTER(!isBlank(?subclass))
                FILTER(!isBlank(?superclass))
            }
            """
            
            # Query for number of annotations
            query_annotations = """
            SELECT (COUNT(?s) as ?numAnnotations)
            WHERE {
                ?s ?p ?o .
                ?p a owl:AnnotationProperty .
            }
            """
            
            # Query for number of axioms
            query_axioms = """
            SELECT (COUNT(?s) as ?numAxioms)
            WHERE {
                { ?s owl:equivalentClass ?o } UNION
                { ?s owl:disjointWith ?o } UNION
                { ?s owl:complementOf ?o } UNION
                { ?s owl:intersectionOf ?o } UNION
                { ?s owl:unionOf ?o }
            }
            """
            
            # Query for number of properties
            query_properties = """
            SELECT (COUNT(DISTINCT ?property) as ?numProperties)
            WHERE {
                { ?property a owl:ObjectProperty } UNION
                { ?property a owl:DatatypeProperty } UNION
                { ?property a owl:AnnotationProperty }
            }
            """

            # Execute queries
            results = {}
            for query, key in [
                (query_total, 'totalTriples'),
                (query_concepts, 'numConcepts'),
                (query_relationships, 'numRelationships'),
                (query_classes, 'numClasses'),
                (query_subclasses, 'numSubclasses'),
                (query_annotations, 'numAnnotations'),
                (query_axioms, 'numAxioms'),
                (query_properties, 'numProperties')
            ]:
                try:
                    result = self.sparql_server.query(query)
                    if result and result['results'] and result['results']['bindings']:
                        results[key] = int(result['results']['bindings'][0][key]['value'])
                except Exception as e:
                    logger.warning(f"[{self.namespace}] Error executing query for {key}: {e}")
                    results[key] = 0

            # Calculate relationships count
            relationships_count = results.get('numRelationships', 0)
            
            logger.info(f"[{self.namespace}] Retrieved statistics: {results}")
            return {
                'total_concepts': results.get('numConcepts', 0),
                'total_relationships': relationships_count,
                'class_count': results.get('numClasses', 0),
                'subclass_count': results.get('numSubclasses', 0),
                'annotation_count': results.get('numAnnotations', 0),
                'axiom_count': results.get('numAxioms', 0),
                'property_count': results.get('numProperties', 0)
            }
            
        except Exception as e:
            logger.error(f"[{self.namespace}] Error getting statistics: {e}", exc_info=True)
            return {
                'total_concepts': 0,
                'total_relationships': 0,
                'class_count': 0,
                'subclass_count': 0,
                'annotation_count': 0,
                'axiom_count': 0,
                'property_count': 0
            }

    def export_graph(self) -> Graph:
        """
        Exports the entire graph from Blazegraph.
        
        Returns:
            Graph: RDFLib graph containing the exported data
        """
        try:
            if not self.is_connected():
                logger.warning("Attempting to export graph while not connected")
                if not self.connect():
                    return Graph()
                    
            # Query for all triples
            query = """
            CONSTRUCT {
                ?s ?p ?o
            }
            WHERE {
                ?s ?p ?o
            }
            """
            
            # Execute query
            result = self.sparql_server.query(query)
            
            # Create export graph
            export_graph = Graph()
            
            # Add default namespaces
            export_graph.bind("rdf", rdflib.RDF)
            export_graph.bind("rdfs", rdflib.RDFS)
            export_graph.bind("owl", rdflib.OWL)
            
            # Process results and add to graph
            for row in result:
                subject = row.get('s')
                predicate = row.get('p')
                obj = row.get('o')
                
                export_graph.add((subject, predicate, obj))
            
            logger.info(f"[{self.namespace}] Graph exported successfully")
            return export_graph
        except Exception as e:
            logger.error(f"[{self.namespace}] Error exporting graph: {e}")
            raise Exception(f"Graph export failed: {e}")

    def export_to_rdflib_graph(self, context: Optional[str] = None) -> Graph:
        """
        Exports data from Blazegraph to an RDFLib graph.
        
        Args:
            context: Optional named graph/context to export from
            
        Returns:
            Graph: RDFLib graph containing the exported data
            
        Raises:
            BlazegraphConnectionError: If connection fails
            Exception: For other unexpected errors
        """
        try:
            if not self.is_connected():
                raise BlazegraphConnectionError("Not connected to Blazegraph")
            
            # Build the query with optional context
            query = """
            CONSTRUCT { ?s ?p ?o }
            WHERE { GRAPH ?g { ?s ?p ?o } }
            """
            
            if context:
                # In triples mode, we can't use GRAPH clauses, so we'll have to filter by context in application code
                # This is a simplified query that gets all triples
                query = """
                CONSTRUCT { ?s ?p ?o }
                WHERE { ?s ?p ?o }
                """
            
            # Execute query
            result = self.sparql_server.query(query)
            
            # Create new RDFLib graph
            export_graph = rdflib.Graph()
            
            # Process results
            for binding in result['results']['bindings']:
                subject = URIRef(binding['s']['value'])
                predicate = URIRef(binding['p']['value'])
                
                if binding['o']['type'] == 'uri':
                    object = URIRef(binding['o']['value'])
                elif binding['o']['type'] == 'literal':
                    if 'datatype' in binding['o']:
                        object = Literal(binding['o']['value'], datatype=URIRef(binding['o']['datatype']))
                    elif 'xml:lang' in binding['o']:
                        object = Literal(binding['o']['value'], lang=binding['o']['xml:lang'])
                    else:
                        object = Literal(binding['o']['value'])
                else:
                    object = BNode(binding['o']['value'])
                
                export_graph.add((subject, predicate, object))
            
            return export_graph
            
        except BlazegraphConnectionError as e:
            logger.error(f"Connection error exporting graph: {e}")
            raise
        except Exception as e:
            logger.error(f"Error exporting graph: {e}")
            raise Exception(f"Graph export failed: {e}")

    def import_rdflib_graph(self, graph: Graph, context: Optional[str] = None) -> bool:
        """
        Imports an RDFLib graph into the Blazegraph database.
        
        Args:
            graph: RDFLib graph to import
            context: Optional context name for the graph
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.is_connected():
                raise Exception("Not connected to Blazegraph")
                
            # Convert the graph to N-Triples format
            ntriples = graph.serialize(format='nt')
            
            # Prepare the SPARQL endpoint URL
            url = f"{self.base_url}/namespace/{self.namespace}/sparql"
            
            # Prepare the headers
            headers = {
                'Content-Type': 'application/sparql-update',
                'Accept': 'application/json'
            }
            
            # Create a simple SPARQL update query
            query = f"""
            INSERT DATA {{
                {ntriples}
            }}
            """
            
            # Send the data
            response = requests.post(url, headers=headers, data=query)
            
            if response.status_code == 200:
                logger.info(f"[{self.namespace}] Successfully imported {len(graph)} triples")
                return True
            else:
                logger.error(f"[{self.namespace}] Failed to import graph: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"[{self.namespace}] Error importing graph: {str(e)}")
            return False
    
    def get_concepts(self) -> List[Dict[str, str]]:
        """
        Retrieves all concepts from the graph.
        
        Returns:
            List[Dict[str, str]]: List of concepts with their IDs and labels
        """
        try:
            if not self.is_connected():
                logger.warning("Attempting to get concepts while not connected")
                if not self.connect():
                    return []
                    
            # Query for concepts
            query = f"""
            SELECT DISTINCT ?concept ?label
            WHERE {{
                ?concept a <{self.base_url}/namespace/{self.namespace}/Concept> .
                OPTIONAL {{ ?concept rdfs:label ?label }}
            }}
            """
            
            results = self.execute_query(query)
            return [{
                "id": res.get("concept", ""), 
                "label": res.get("label", ""),
                "name": res.get("label", "")  # Add 'name' key for compatibility with Visualizer
            } for res in results]
        except Exception as e:
            logger.error(f"Error retrieving concepts: {e}")
            return []