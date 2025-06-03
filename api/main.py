#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main entry point for the OntoMed API.
Provides a FastAPI application with endpoints for the OntoMed framework.
"""

import os
import sys
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.utils import setup_logging
from semantic_router import router as semantic_router
from prompt_router import router as prompt_router
from llm_router import router as llm_router
from models import ErrorResponse

# Set up logging
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar templates
try:
    from prompt.initialize import initialize
    initialize()
    logger.info("Templates inicializados com sucesso")
except Exception as e:
    logger.error(f"Erro ao inicializar templates: {e}")

# Create FastAPI application
app = FastAPI(
    title="OntoMed API",
    description="REST API for the OntoMed framework",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(semantic_router)
app.include_router(prompt_router)
app.include_router(llm_router, prefix="/api", tags=["llm"])

@app.get("/")
async def root():
    """
    Root endpoint for the API.
    """
    return {
        "message": "Welcome to the OntoMed API",
        "version": "0.1.0",
        "documentation": "/docs"
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify API readiness.
    
    Returns:
        dict: API status and version
    """
    return {
        "status": "healthy",
        "version": "0.1.0",
        "documentation": "/docs"
    }

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

# Optional: enable running via `python main.py`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=False)
