"""
Session management for the OntoMed application.
Handles shared state across pages and components.
"""
import streamlit as st
from typing import Any, Optional, Tuple
from utils.chat_controller import ChatController
from utils.nlp.processor import NLPProcessor
from utils.api_client import APIClient
from utils.nlp.scoring_system import IntentScoringSystem
from prompt.manager import PromptManager
from llm.factory import LLMFactory
from prompt.template_manager import TemplateManager
import logging
import os
import sys

logger = logging.getLogger(__name__)

def get_scoring_system() -> 'IntentScoringSystem':
    """Get or create the shared IntentScoringSystem instance.
    
    Returns:
        IntentScoringSystem: The shared scoring system instance
    """
    if 'scoring_system' not in st.session_state:
        logger.info("Initializing new IntentScoringSystem instance")
        st.session_state.scoring_system = IntentScoringSystem()
    else:
        logger.debug("Using existing IntentScoringSystem instance")
    
    return st.session_state.scoring_system

def get_nlp_processor() -> NLPProcessor:
    """Get or create the shared NLPProcessor instance.
    
    Returns:
        NLPProcessor: The shared NLP processor instance
    """
    if 'nlp_processor' not in st.session_state:
        logger.info("Initializing new NLPProcessor instance")
        api_client = APIClient()
        # Get shared scoring system
        scoring_system = get_scoring_system()
        st.session_state.nlp_processor = NLPProcessor(api_client=api_client, scoring_system=scoring_system)
        
        # Initialize the processor
        if not st.session_state.nlp_processor.initialize():
            logger.error("Failed to initialize NLPProcessor")
            raise RuntimeError("Failed to initialize NLPProcessor")
    else:
        logger.debug("Using existing NLPProcessor instance")
    
    return st.session_state.nlp_processor

def get_chat_controller() -> ChatController:
    """Get or create the shared ChatController instance.
    
    Returns:
        ChatController: The shared controller instance
    """
    if 'chat_controller' not in st.session_state:
        logger.info("Initializing new ChatController instance")
        
        # Get the shared NLP processor
        nlp_processor = get_nlp_processor()
        
        # Create the controller with the shared processor
        st.session_state.chat_controller = ChatController()
        
        # Inject the shared NLP processor
        st.session_state.chat_controller.nlp_processor = nlp_processor
        
        logger.info("ChatController initialized with shared NLPProcessor")
    else:
        logger.debug("Using existing ChatController instance")
        
    return st.session_state.chat_controller

def get_template_manager() -> 'TemplateManager':
    """Get or create the shared TemplateManager instance.
    Verifica se os templates já foram inicializados em Home.py ou se já foram carregados
    no session_state para evitar reinicialização desnecessária.
    
    Returns:
        TemplateManager: The shared template manager instance
    """
    # Check if the templates were initialized in Home.py or if they were already loaded in the session_state
    templates_already_initialized = 'templates_initialized' in st.session_state and st.session_state.templates_initialized
    templates_already_loaded = 'tm_templates_loaded' in st.session_state and st.session_state.tm_templates_loaded
    templates_exist = 'tm_templates' in st.session_state and len(st.session_state.tm_templates) > 0
    
    # Set flag to skip analysis if any of the conditions are true
    skip_analysis = templates_already_initialized or templates_already_loaded or templates_exist
    
    # Ensure session state flags are consistent
    if templates_exist and not templates_already_loaded:
        st.session_state.tm_templates_loaded = True
        logger.info("Marking tm_templates_loaded as True since templates exist in session_state")
        
    if templates_already_loaded and not templates_already_initialized:
        st.session_state.templates_initialized = True
        logger.info("Marking templates_initialized as True since tm_templates_loaded is True")
    
    if 'template_manager' not in st.session_state:
        # Add root path to sys.path to ensure correct import
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        if root_path not in sys.path:
            sys.path.insert(0, root_path)
        
        llm = LLMFactory.create_llm()
        
        if skip_analysis:
            logger.info(f"Templates already initialized or loaded, creating TemplateManager without reprocessing")
            logger.info(f"templates_initialized={templates_already_initialized}, tm_templates_loaded={templates_already_loaded}, templates_exist={templates_exist}")
            # Create TemplateManager with flag to avoid reprocessing
            st.session_state.template_manager = TemplateManager(llm, skip_intent_analysis=True)
            logger.info("TemplateManager initialized with skip_intent_analysis=True")
        else:
            logger.info("Initializing new TemplateManager (templates were not initialized previously)")
            st.session_state.template_manager = TemplateManager(llm, skip_intent_analysis=False)
            logger.info("TemplateManager initialized with complete processing")
    else:
        logger.debug("Using existing TemplateManager instance")
    
    return st.session_state.template_manager

def clear_chat_controller() -> None:
    """Clear the ChatController, NLPProcessor, TemplateManager and ScoringSystem instances from the session state."""
    if 'chat_controller' in st.session_state:
        logger.info("Clearing ChatController from session state")
        del st.session_state.chat_controller
    
    if 'nlp_processor' in st.session_state:
        logger.info("Clearing NLPProcessor from session state")
        del st.session_state.nlp_processor
        
    if 'template_manager' in st.session_state:
        logger.info("Clearing TemplateManager from session state")
        del st.session_state.template_manager
        
    if 'scoring_system' in st.session_state:
        logger.info("Clearing ScoringSystem from session state")
        del st.session_state.scoring_system
