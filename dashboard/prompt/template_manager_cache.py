"""
Template manager for the OntoMed dashboard with caching support.
"""

from typing import Dict, Any, List
import os
import yaml
import logging
import streamlit as st
from typing import Dict, List, Any, Optional
from llm.interface import LLMInterface
from prompt.llm_integration import LLMPromptManager

logger = logging.getLogger(__name__)

class TemplateManager:
    """Template manager for content generation with caching support."""
    
    def __init__(self, llm: LLMInterface):
        """Initializes the template manager.
        
        Args:
            llm: LLM interface for generation
        """
        self.llm = llm
        self.prompt_manager = LLMPromptManager(llm)
        
        # Initialize in session state if not exists
        if 'tm_templates' not in st.session_state:
            st.session_state.tm_templates = []
            
        if 'tm_templates_loaded' not in st.session_state:
            st.session_state.tm_templates_loaded = False
        
        self.templates_dir = self._get_templates_dir()
        
        # Load templates if not already loaded
        if not st.session_state.tm_templates_loaded:
            self._load_templates_from_disk()
            st.session_state.tm_templates_loaded = True
            logger.info(f"Templates loaded and cached in session state")
        else:
            logger.info(f"Using cached templates from session state")
    
    @property
    def templates(self):
        """Get templates from session state."""
        return st.session_state.tm_templates
    
    @templates.setter
    def templates(self, value):
        """Set templates in session state."""
        st.session_state.tm_templates = value
    
    def _get_templates_dir(self) -> str:
        """Gets the templates directory.
        
        Returns:
            Templates directory path
        """
        # Try to find the templates directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        templates_dir = os.path.join(current_dir, "templates")
        
        if not os.path.exists(templates_dir):
            # Try to find in the parent directory
            parent_dir = os.path.dirname(current_dir)
            templates_dir = os.path.join(parent_dir, "prompt", "templates")
            
        if not os.path.exists(templates_dir):
            # Try to find in the current working directory
            cwd = os.getcwd()
            logger.info(f"Current working directory: {cwd}")
            templates_dir = os.path.join(cwd, "prompt", "templates")
            
        return templates_dir
