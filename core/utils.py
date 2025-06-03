#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utility functions and classes for MedKnowBridge.
"""

import logging
import os
import json
from typing import Dict, Any, Optional, List, Union

# Configure logging
logger = logging.getLogger("ontomed")

def setup_logging(level: int = logging.INFO, log_file: Optional[str] = None) -> None:
    """
    Sets up logging for MedKnowBridge.
    
    Args:
        level: Logging level (default: INFO)
        log_file: Path to log file (optional)
    """
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    logger.info(f"Logging initialized at level {logging.getLevelName(level)}")

def load_config(config_path: str) -> Dict[str, Any]:
    """
    Loads configuration from a JSON file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Dict containing configuration
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is not valid JSON
    """
    try:
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        logger.info(f"Configuration loaded from {config_path}")
        return config
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        raise

class Singleton:
    """
    Singleton metaclass for ensuring only one instance of a class exists.
    """
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
