#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Server script for the OntoMed API.
Provides a command-line interface for starting the API server.
"""

import os
import sys
import logging
import argparse
import uvicorn

# Add the project root to the path so we can import the modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from core.utils import setup_logging

def main():
    """
    Main entry point for the server script.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Start the OntoMed API server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--log-level", default="info", 
                       choices=["debug", "info", "warning", "error", "critical"],
                       help="Logging level")
    args = parser.parse_args()
    
    # Set up logging
    log_level = getattr(logging, args.log_level.upper())
    setup_logging(level=log_level)
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting OntoMed API server on {args.host}:{args.port}")
    
    # Start the server
    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level.lower(),
    )

if __name__ == "__main__":
    main()
