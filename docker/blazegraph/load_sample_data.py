#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to load sample medical knowledge into BlazegraphDB for MedKnowBridge demonstration.
This provides a basic set of medical concepts and relationships to showcase the system.
"""

import os
import sys
import logging
import requests
import time
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("sample_data_loader")

# API endpoint
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
CONCEPTS_ENDPOINT = f"{API_BASE_URL}/semantic/concepts/"

# Sample medical concepts
SAMPLE_CONCEPTS = [
    {
        "id": "Hypertension",
        "label": "Hypertension (High Blood Pressure)",
        "relationships": [
            {
                "type": "hasCause",
                "target": "GeneticFactors",
                "label": "Genetic Factors"
            },
            {
                "type": "hasCause",
                "target": "Lifestyle",
                "label": "Lifestyle Factors"
            },
            {
                "type": "hasSymptom",
                "target": "Headache",
                "label": "Headache"
            },
            {
                "type": "hasSymptom",
                "target": "Dizziness",
                "label": "Dizziness"
            },
            {
                "type": "hasComplication",
                "target": "HeartDisease",
                "label": "Heart Disease"
            },
            {
                "type": "hasComplication",
                "target": "Stroke",
                "label": "Stroke"
            },
            {
                "type": "hasTreatment",
                "target": "ACEInhibitors",
                "label": "ACE Inhibitors"
            },
            {
                "type": "hasTreatment",
                "target": "LifestyleModification",
                "label": "Lifestyle Modification"
            }
        ]
    },
    {
        "id": "DiabetesMellitus",
        "label": "Diabetes Mellitus (Type 2)",
        "relationships": [
            {
                "type": "hasCause",
                "target": "GeneticFactors",
                "label": "Genetic Factors"
            },
            {
                "type": "hasCause",
                "target": "Obesity",
                "label": "Obesity"
            },
            {
                "type": "hasSymptom",
                "target": "Polyuria",
                "label": "Excessive Urination"
            },
            {
                "type": "hasSymptom",
                "target": "Polydipsia",
                "label": "Excessive Thirst"
            },
            {
                "type": "hasComplication",
                "target": "Neuropathy",
                "label": "Neuropathy"
            },
            {
                "type": "hasComplication",
                "target": "Retinopathy",
                "label": "Retinopathy"
            },
            {
                "type": "hasTreatment",
                "target": "Metformin",
                "label": "Metformin"
            },
            {
                "type": "hasTreatment",
                "target": "LifestyleModification",
                "label": "Lifestyle Modification"
            }
        ]
    },
    {
        "id": "Asthma",
        "label": "Asthma",
        "relationships": [
            {
                "type": "hasCause",
                "target": "GeneticFactors",
                "label": "Genetic Factors"
            },
            {
                "type": "hasCause",
                "target": "EnvironmentalTriggers",
                "label": "Environmental Triggers"
            },
            {
                "type": "hasSymptom",
                "target": "Wheezing",
                "label": "Wheezing"
            },
            {
                "type": "hasSymptom",
                "target": "ChestTightness",
                "label": "Chest Tightness"
            },
            {
                "type": "hasComplication",
                "target": "StatusAsthmaticus",
                "label": "Status Asthmaticus"
            },
            {
                "type": "hasTreatment",
                "target": "Bronchodilators",
                "label": "Bronchodilators"
            },
            {
                "type": "hasTreatment",
                "target": "InhaledCorticosteroids",
                "label": "Inhaled Corticosteroids"
            }
        ]
    }
]

def wait_for_api(max_retries=30, retry_interval=5):
    """
    Wait until the API is available.
    
    Args:
        max_retries: Maximum number of retries
        retry_interval: Interval between retries in seconds
        
    Returns:
        bool: True if API is available, False otherwise
    """
    logger.info(f"Waiting for API at {API_BASE_URL}...")
    
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{API_BASE_URL}/health")
            if response.status_code == 200:
                logger.info("API is available!")
                return True
        except requests.exceptions.RequestException:
            pass
            
        logger.info(f"API not available yet. Retrying in {retry_interval} seconds... ({attempt+1}/{max_retries})")
        time.sleep(retry_interval)
    
    logger.error(f"API not available after {max_retries} attempts")
    return False

def load_concept(concept):
    """
    Load a concept into the database via the API.
    
    Args:
        concept: Concept data
        
    Returns:
        bool: True if concept was loaded successfully, False otherwise
    """
    try:
        # First check if concept already exists
        response = requests.get(f"{CONCEPTS_ENDPOINT}{concept['id']}")
        if response.status_code == 200:
            logger.info(f"Concept '{concept['id']}' already exists")
            return True
        
        # Create the concept
        response = requests.post(
            CONCEPTS_ENDPOINT,
            json=concept
        )
        
        if response.status_code in [200, 201]:
            logger.info(f"Concept '{concept['id']}' loaded successfully")
            return True
        else:
            logger.error(f"Failed to load concept '{concept['id']}': {response.status_code} - {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Error loading concept '{concept['id']}': {e}")
        return False

def main():
    """
    Main function to load sample data.
    """
    logger.info("Starting sample data loading")
    
    # Wait for API to be available
    if not wait_for_api():
        logger.error("API not available. Exiting.")
        sys.exit(1)
    
    # Load concepts
    success_count = 0
    for concept in SAMPLE_CONCEPTS:
        if load_concept(concept):
            success_count += 1
    
    logger.info(f"Loaded {success_count}/{len(SAMPLE_CONCEPTS)} sample concepts")
    
    if success_count == len(SAMPLE_CONCEPTS):
        logger.info("All sample data loaded successfully")
    else:
        logger.warning("Some sample data could not be loaded")
        
    logger.info("Sample data loading completed")

if __name__ == "__main__":
    main()
