#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Factory for creating graph database connectors in MedKnowBridge.
Implements the Factory pattern for creating different types of database connectors.
"""

import logging
import os
from typing import Dict, Any, Optional, Type

from .interface import GraphDatabaseInterface
try:
    from .blazegraph_connector import BlazegraphConnector
except ImportError:
    logger.error("Failed to import BlazegraphConnector")
    raise

# Define Singleton metaclass locally to avoid import issues
class Singleton(type):
    """Singleton metaclass for ensuring only one instance of a class exists."""
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

logger = logging.getLogger(__name__)

class GraphDatabaseFactory(metaclass=Singleton):
    """
    Factory for creating graph database connectors.
    Implements the Singleton pattern to ensure only one factory exists.
    """
    
    def __init__(self):
        """
        Initializes the factory with registered connector types.
        """
        self._connector_types = {
            "blazegraph": BlazegraphConnector
        }
        
        # Initialize Blazegraph connector
        blazegraph_url = os.getenv('DATABASE_URL', 'http://blazegraph:8080/bigdata')
        namespace = os.getenv('BLAZEGRAPH_NAMESPACE', 'data')
        
        # Remove namespace from base URL if present
        if blazegraph_url.endswith(f'/namespace/{namespace}'):
            blazegraph_url = blazegraph_url.rsplit('/', 2)[0]
        
        # Create and connect the default Blazegraph instance
        self.default_connector = self._connector_types["blazegraph"](blazegraph_url, namespace)
        
        # Ensure the namespace exists
        if not self.default_connector.create_namespace_if_not_exists(name=namespace):
            logger.error(f"Failed to create namespace: {namespace}")
            raise Exception(f"Failed to create namespace: {namespace}")
        
        # Connect after ensuring namespace exists
        if not self.default_connector.connect():
            logger.error(f"Failed to connect to Blazegraph with namespace: {namespace}")
            raise Exception(f"Failed to connect to Blazegraph with namespace: {namespace}")
        
        logger.info(f"Registered and connected default connector: blazegraph with namespace: {namespace}")
        
    def register_connector(self, name: str, connector_class: Type[GraphDatabaseInterface]) -> None:
        """
        Registers a connector type with the factory.
        
        Args:
            name: Name of the connector type
            connector_class: Class implementing GraphDatabaseInterface
        """
        if not issubclass(connector_class, GraphDatabaseInterface):
            raise TypeError(f"Connector class must implement GraphDatabaseInterface")
        
        self._connector_types[name] = connector_class
        logger.info(f"Registered connector type: {name}")
        
    def create_connector(self, connector_type: str, **kwargs) -> GraphDatabaseInterface:
        """
        Creates a connector of the specified type.
        
        Args:
            connector_type: Type of connector to create
            **kwargs: Arguments to pass to the connector constructor
            
        Returns:
            Instance of GraphDatabaseInterface
            
        Raises:
            ValueError: If connector_type is not registered
        """
        if connector_type not in self._connector_types:
            raise ValueError(f"Unknown connector type: {connector_type}")
        
        connector_class = self._connector_types[connector_type]
        connector = connector_class(**kwargs)
        
        logger.info(f"Created connector of type: {connector_type}")
        return connector
        
    def get_available_connectors(self) -> Dict[str, Type[GraphDatabaseInterface]]:
        """
        Gets all registered connector types.
        
        Returns:
            Dictionary mapping connector names to connector classes
        """
        return self._connector_types.copy()
