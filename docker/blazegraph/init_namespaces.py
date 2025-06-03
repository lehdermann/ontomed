#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to initialize namespaces in Blazegraph for the HMARL+GenAI system.
This script creates the necessary namespaces to store the medical ontology,
agent knowledge, and temporal data.
"""

import requests
import time
import logging
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("blazegraph_init")

# Endpoint Blazegraph
BLAZEGRAPH_URL = "http://localhost:9999/bigdata"
SPARQL_ENDPOINT = f"{BLAZEGRAPH_URL}/sparql"

# Namespaces to be created
NAMESPACES = [
    {
        "name": "medical_ontology",
        "description": "Namespace for the HMARL+GenAI system's medical ontology",
        "properties": {
            "com.bigdata.rdf.store.AbstractTripleStore.textIndex": "true",
            "com.bigdata.rdf.store.AbstractTripleStore.axiomsClass": "com.bigdata.rdf.axioms.NoAxioms",
            "com.bigdata.namespace.medical_ontology.spo.com.bigdata.btree.BTree.branchingFactor": "400"
        }
    },
    {
        "name": "agent_knowledge",
        "description": "Namespace for the HMARL+GenAI system's agent knowledge",
        "properties": {
            "com.bigdata.rdf.store.AbstractTripleStore.textIndex": "true",
            "com.bigdata.rdf.store.AbstractTripleStore.axiomsClass": "com.bigdata.rdf.axioms.NoAxioms",
            "com.bigdata.namespace.agent_knowledge.spo.com.bigdata.btree.BTree.branchingFactor": "400"
        }
    },
    {
        "name": "temporal",
        "description": "Namespace for the HMARL+GenAI system's temporal data",
        "properties": {
            "com.bigdata.rdf.store.AbstractTripleStore.textIndex": "true",
            "com.bigdata.rdf.store.AbstractTripleStore.axiomsClass": "com.bigdata.rdf.axioms.NoAxioms",
            "com.bigdata.namespace.temporal.spo.com.bigdata.btree.BTree.branchingFactor": "400"
        }
    }
]

def wait_for_blazegraph(max_retries=10, retry_interval=5):
    """
    Wait until the Blazegraph server is available.
    
    Args:
        max_retries: Maximum number of retry attempts
        retry_interval: Interval between retries in seconds
        
    Returns:
        bool: True if the server is available, False otherwise
    """
    logger.info(f"Checking if Blazegraph server is available at {BLAZEGRAPH_URL}...")
    
    for i in range(max_retries):
        try:
            response = requests.get(BLAZEGRAPH_URL)
            if response.status_code == 200:
                logger.info("Blazegraph server is available!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        logger.info(f"Attempt {i+1}/{max_retries} failed. Retrying in {retry_interval} seconds...")
        time.sleep(retry_interval)
    
    logger.error(f"Blazegraph server is not available after {max_retries} attempts.")
    return False

def create_namespace(namespace):
    """
    Create a namespace in Blazegraph.
    
    Args:
        namespace: Dictionary with namespace information
        
    Returns:
        bool: True if the namespace was created successfully, False otherwise
    """
    logger.info(f"Creating namespace '{namespace['name']}'...")
    
    # Check if the namespace already exists
    try:
        response = requests.get(f"{BLAZEGRAPH_URL}/namespace/{namespace['name']}")
        if response.status_code == 200:
            logger.info(f"Namespace '{namespace['name']}' already exists.")
            return True
    except requests.exceptions.RequestException:
        pass
    
    # Create the namespace
    properties = {
        "com.bigdata.rdf.sail.namespace": namespace['name'],
        "com.bigdata.rdf.store.AbstractTripleStore.quads": "false",
        "com.bigdata.rdf.store.AbstractTripleStore.statementIdentifiers": "false",
        "com.bigdata.rdf.sail.truthMaintenance": "false"
    }
    
    # Add namespace-specific properties
    properties.update(namespace['properties'])
    
    # Convert properties to Java properties file format
    properties_text = "\n".join([f"{k}={v}" for k, v in properties.items()])
    
    try:
        response = requests.post(
            f"{BLAZEGRAPH_URL}/namespace",
            data=properties_text,
            headers={"Content-Type": "text/plain"}
        )
        
        if response.status_code == 201:
            logger.info(f"Namespace '{namespace['name']}' created successfully!")
            return True
        else:
            logger.error(f"Error creating namespace '{namespace['name']}': {response.status_code} - {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Error creating namespace '{namespace['name']}': {e}")
        return False

def main():
    """
    Main function to initialize namespaces in Blazegraph.
    """
    logger.info("Starting namespace initialization in Blazegraph for the HMARL+GenAI system...")
    
    # Wait for the Blazegraph server
    if not wait_for_blazegraph():
        logger.error("Could not connect to the Blazegraph server. Please check if the server is running.")
        sys.exit(1)
    
    # Create the namespaces
    success = True
    for namespace in NAMESPACES:
        if not create_namespace(namespace):
            success = False
    
    if success:
        logger.info("All namespaces have been created successfully!")
        logger.info(f"SPARQL endpoint available at: {SPARQL_ENDPOINT}")
        logger.info("The HMARL+GenAI system is ready to use the Blazegraph database.")
    else:
        logger.error("There were errors creating some namespaces. Check the logs for more details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
