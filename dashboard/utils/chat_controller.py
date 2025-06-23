"""
Chat Controller for the OntoMed.
Integrates NLP processor, API client and context management.
"""

import logging
from typing import Dict, Any, List, Optional
import streamlit as st
import re
import json
from datetime import datetime

from .nlp.processor import NLPProcessor
from .nlp.models import Entity, Intent
from .nlp.scoring_system import IntentScoringSystem
from .nlp.static_intent_manager import StaticIntentManager
from .api_client import APIClient
from prompt.manager import PromptManager as TemplateManager
from llm.factory import LLMFactory

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler with a more detailed format
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create formatter and add to handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Add the handler to the logger
if not logger.handlers:
    logger.addHandler(console_handler)

logger.info("Module chat_controller loaded")

class ChatController:
    """
    Chat Controller for the OntoMed.
    
    Responsibilities:
    1. Process user messages using NLP
    2. Identify intents and entities
    3. Execute commands based on intent
    4. Manage conversation context
    5. Generate responses using templates and LLM
    """
    
    def __init__(self, nlp_processor=None):
        """Initialize the chat controller.
        
        Args:
            nlp_processor: Optional shared NLPProcessor instance. If not provided, a new one will be created.
        """
        # Configure logger for this instance
        self.logger = logging.getLogger(f"{__name__}.ChatController")
        
        # If no handlers, add console handler
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
            
        self.logger.info("ChatController inicializado")
        
        # Initialize components
        self.api_client = APIClient()
        
        # Use provided NLP processor or get the shared one
        if nlp_processor is not None:
            self.nlp_processor = nlp_processor
            self.scoring_system = getattr(nlp_processor, 'scoring_system', None)
            self.logger.info(f"Using provided NLPProcessor instance. scoring_system: {self.scoring_system is not None}")
        else:
            # Get the shared NLP processor with its scoring system
            from utils.session_manager import get_nlp_processor
            self.nlp_processor = get_nlp_processor()
            self.scoring_system = getattr(self.nlp_processor, 'scoring_system', None)
            self.logger.info(f"Using shared NLPProcessor instance. scoring_system: {self.scoring_system is not None}")
            
        # Check if the scoring_system has the update_intent_keywords method
        if hasattr(self.nlp_processor, 'scoring_system') and self.nlp_processor.scoring_system is not None:
            has_update_method = hasattr(self.nlp_processor.scoring_system, 'update_intent_keywords')
            self.logger.info(f"scoring_system has update_intent_keywords method: {has_update_method}")
            
            # Check if the spaCy model is available in the scoring_system
            has_nlp = hasattr(self.nlp_processor.scoring_system, 'nlp') and self.nlp_processor.scoring_system.nlp is not None
            self.logger.info(f"scoring_system has spaCy model available: {has_nlp}")
        else:
            self.logger.error("NLPProcessor does not have a valid scoring_system")
            raise RuntimeError("NLPProcessor is not properly initialized with a scoring system")
            
        # Initialize Static Intent Manager
        self.static_intent_manager = StaticIntentManager(self.nlp_processor.nlp)
        self.logger.info("StaticIntentManager initialized")
        
        # Get shared template manager from session
        from utils.session_manager import get_template_manager
        self.template_manager = get_template_manager()
        self.logger.debug("Using shared TemplateManager instance")
        
        # Configuration
        self.debug_mode = False  # Default to debug mode disabled
        
        # Initialize cache
        self._concept_cache = {}
        self._relationship_cache = {}
        
        # Initialize LLM for fallback responses e análise de templates
        try:
            self.llm = LLMFactory.create_llm()
            self.logger.info("LLM initialized successfully")
        except Exception as e:
            self.logger.warning(f"Failed to initialize LLM: {str(e)}")
            self.llm = None
        
        # Get available templates and dynamically build intent-template mapping
        self._intent_template_mapping = self._build_intent_template_mapping()
        
        # Initialize conversation context
        if 'chat_context' not in st.session_state:
            st.session_state.chat_context = {
                'last_intent': None,
                'last_entities': [],
                'mentioned_concepts': [],
                'current_flow': None,
                'flow_state': {}
            }
            
        self.logger.info("ChatController initialized successfully")
        
    def _build_intent_template_mapping(self) -> Dict[str, str]:
        """
        Dynamically builds the intent-template mapping based on available templates.
        Uses LLM-extracted intent information when available.
        
        Returns:
            Dictionary mapping intents to template IDs
        """
        # We no longer use static default mapping
        # We only rely on the dynamic mapping generated by LLM analysis
        self.logger.info("Building dynamic intent-template mapping")
        
        # Get all available templates
        try:
            templates = self.template_manager.get_templates()
            # templates is a list of dictionaries, not a dictionary
            template_ids = [template.get('id', '') for template in templates]
            self.logger.info(f"Found {len(templates)} templates available: {template_ids}")
            
            # Check if the templates have been analyzed by LLM
            templates_need_analysis = False
            for template in templates:
                if "intent_info" not in template or template.get("intent_info", {}).get("intent") == "unknown":
                    templates_need_analysis = True
                    self.logger.info(f"Template {template.get('id')} does not have intent analysis")
                    break
            
            # If the templates have not been analyzed, call the analysis method
            if templates_need_analysis and self.llm is not None:
                self.logger.info("Some templates do not have intent analysis. Performing analysis...")
                # Call the template analysis method
                self.template_manager._analyze_templates(templates)
                # Get the updated templates
                templates = self.template_manager.get_templates()
                self.logger.info("Analysis of templates completed")
            
            # Build dynamic mapping from LLM-extracted intent information
            dynamic_mapping = {}
            
            # DBG: Check specifically if we have the template literature_summary
            scientific_template = next((t for t in templates if t.get('id') == "literature_summary"), None)
            if scientific_template:
                self.logger.info(f"Template 'literature_summary' found")
                self.logger.info(f"Metadata of template: {scientific_template.get('intent_info', {})}")
            else:
                self.logger.info(f"Template 'literature_summary' NOT found")
            
            for template in templates:
                # Get template ID and intent information from template metadata
                template_id = template.get("id", "")
                intent_info = template.get("intent_info", {})
                self.logger.info(f"Template '{template_id}' has intent_info: {intent_info}")
                
                if intent_info and "intent" in intent_info:
                    intent_name = intent_info["intent"]
                    dynamic_mapping[intent_name] = template_id
                    self.logger.info(f"Added dynamic mapping: intent '{intent_name}' -> template '{template_id}'")
                    
                    # Update the NLP system with intent information
                    self._update_nlp_system_with_intent_info(intent_name, intent_info)
                    
                else:
                    self.logger.info(f"Template '{template_id}' does not have intent defined")
            
            if not dynamic_mapping:
                self.logger.warning("No dynamic mapping of intent to template was created. Verify LLM analysis.")
            
            
            # Log of all dynamic mappings for debugging
            self.logger.info(f"Complete dynamic mapping of intents to templates: {dynamic_mapping}")
            
            # We only use the dynamic mapping
            result = dynamic_mapping
            self.logger.info(f"Final dynamic mapping of intents to templates: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error building intent-template mapping: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {}  # Return empty dictionary in case of error
    
    def _update_nlp_system_with_intent_info(self, intent_name: str, intent_info: Dict[str, Any]) -> None:
        """
        Updates the NLP system with intent information extracted by the LLM.
        
        Args:
            intent_name: Intent name
            intent_info: Information extracted by the LLM (keywords, patterns, entities)
        """
        try:
            self.logger.info(f"Starting update of NLP system for dynamic intent '{intent_name}'")
            
            # Check if we have an NLP processor available
            if not hasattr(self, 'nlp_processor') or not self.nlp_processor:
                self.logger.warning(f"No NLP processor available for updating dynamic intent '{intent_name}'")
                return
                
            # Extract relevant information
            keywords = intent_info.get('keywords', [])
            patterns = intent_info.get('patterns', [])
            entities = intent_info.get('entities', [])
            
            self.logger.info(f"Updating NLP system for dynamic intent '{intent_name}' with: {len(keywords)} keywords, {len(patterns)} patterns, {len(entities)} entities")
            self.logger.info(f"Keywords for dynamic intent '{intent_name}': {keywords}")
            self.logger.info(f"Entities for dynamic intent '{intent_name}': {entities}")
            
            
            # Update keywords in the intent scoring system
            if keywords:
                self.logger.info(f"Updating keywords for intent '{intent_name}': {keywords}")
                
                # Get the scoring_system from nlp_processor
                scoring_system = None
                
                # Check if the scoring_system is directly in nlp_processor
                if hasattr(self.nlp_processor, 'scoring_system') and self.nlp_processor.scoring_system is not None:
                    scoring_system = self.nlp_processor.scoring_system
                    self.logger.info(f"Accessing scoring_system directly from nlp_processor for dynamic intent '{intent_name}'")
                    
                    # Check if the scoring_system has the update_intent_keywords method
                    has_update_method = hasattr(scoring_system, 'update_intent_keywords')
                    self.logger.info(f"scoring_system has update_intent_keywords method: {has_update_method}")
                    
                    # Check if the scoring_system has the nlp model available
                    has_nlp = hasattr(scoring_system, 'nlp') and scoring_system.nlp is not None
                    self.logger.info(f"scoring_system has nlp model available: {has_nlp}")
                    
                # Check if there is a nested processor
                elif hasattr(self.nlp_processor, 'processor') and hasattr(self.nlp_processor.processor, 'scoring_system') and self.nlp_processor.processor.scoring_system is not None:
                    scoring_system = self.nlp_processor.processor.scoring_system
                    self.logger.info(f"Accessing scoring_system from nlp_processor.processor for dynamic intent '{intent_name}'")
                    
                    # Check if the scoring_system has the update_intent_keywords method
                    has_update_method = hasattr(scoring_system, 'update_intent_keywords')
                    self.logger.info(f"scoring_system has update_intent_keywords method: {has_update_method}")
                    
                    # Check if the scoring_system has the nlp model available
                    has_nlp = hasattr(scoring_system, 'nlp') and scoring_system.nlp is not None
                    self.logger.info(f"scoring_system has nlp model available: {has_nlp}")
                else:
                    self.logger.error(f"Unable to find scoring_system for dynamic intent '{intent_name}'")
                    self.logger.error(f"nlp_processor has scoring_system: {hasattr(self.nlp_processor, 'scoring_system')}")
                    if hasattr(self.nlp_processor, 'processor'):
                        self.logger.error(f"nlp_processor.processor has scoring_system: {hasattr(self.nlp_processor.processor, 'scoring_system')}")
                    else:
                        self.logger.error(f"nlp_processor does not have processor attribute")
                        
                
                if scoring_system is not None:
                    # Check if the scoring_system has the update_intent_keywords method
                    if hasattr(scoring_system, 'update_intent_keywords') and callable(getattr(scoring_system, 'update_intent_keywords')):
                        try:
                            self.logger.info(f"Calling update_intent_keywords for dynamic intent '{intent_name}'")
                            success = scoring_system.update_intent_keywords(intent_name, keywords)
                            if success:
                                self.logger.info(f"Keywords updated successfully for dynamic intent '{intent_name}'")
                            else:
                                self.logger.warning(f"Failed to update keywords for dynamic intent '{intent_name}'")
                                self.logger.warning(f"Verify the logs of IntentScoringSystem for more details")
                        except Exception as e:
                            self.logger.error(f"Error updating keywords for intent '{intent_name}': {str(e)}")
                            # Fallback for direct method
                            self._update_intent_keywords_direct(scoring_system, intent_name, keywords)
                    # Fallback for direct update of intent_keywords dictionary
                    elif hasattr(scoring_system, 'intent_keywords'):
                        self._update_intent_keywords_direct(scoring_system, intent_name, keywords)
                    else:
                        self.logger.warning(f"No method available to update keywords for intent '{intent_name}'")
                else:
                    self.logger.error("Unable to access the scoring_system of NLPProcessor to update keywords")
            
            # Update patterns in EntityManager
            if patterns:
                self._update_patterns_in_entity_manager(intent_name, patterns)
            
            # Update expected entities in NLP system
            if entities:
                self.logger.info(f"Registering expected entities for intent '{intent_name}': {entities}")
                
                # Get the scoring_system from nlp_processor
                scoring_system = None
                
                # Check if the scoring_system is directly in nlp_processor
                if hasattr(self.nlp_processor, 'scoring_system') and self.nlp_processor.scoring_system is not None:
                    scoring_system = self.nlp_processor.scoring_system
                    self.logger.info("Accessing scoring_system directly from nlp_processor")
                # Check if there is a nested processor
                elif hasattr(self.nlp_processor, 'processor') and hasattr(self.nlp_processor.processor, 'scoring_system') and self.nlp_processor.processor.scoring_system is not None:
                    scoring_system = self.nlp_processor.processor.scoring_system
                    self.logger.info("Accessing scoring_system from nlp_processor.processor")
                
                if scoring_system is not None:
                    # Use the update_entity_intent_mapping method to update entities
                    for entity in entities:
                        if not self.nlp_processor.update_entity_intent_mapping(entity, intent_name):
                            self.logger.warning(f"Failed to map entity: {entity} -> {intent_name}")
                    
                    # Log of the complete mapping for diagnosis (if available)
                    if hasattr(scoring_system, 'entity_intent_map'):
                        self.logger.debug(f"Complete mapping: {scoring_system.entity_intent_map}")
                else:
                    self.logger.error("Unable to access the scoring_system of NLPProcessor")
        
        except Exception as e:
            self.logger.error(f"Error updating NLP system with intent info: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())  # Return default mapping in case of error
    
    def _update_intent_keywords_direct(self, scoring_system, intent_name: str, keywords: List[str]) -> None:
        """Helper method to update the intent_keywords dictionary directly.
        
        Args:
            scoring_system: Intent scoring system
            intent_name: Intent name
            keywords: List of keywords
        """
        try:
            self.logger.info(f"Updating directly keywords for dynamic intent '{intent_name}' (direct method)")
            self.logger.info(f"Keywords to be added: {keywords}")
            
            if intent_name not in scoring_system.intent_keywords:
                scoring_system.intent_keywords[intent_name] = keywords
                self.logger.info(f"Added {len(keywords)} keywords for dynamic intent '{intent_name}' (direct method)")
                
                # Try to call the enrichment method manually
                if hasattr(scoring_system, '_enrich_keywords') and callable(getattr(scoring_system, '_enrich_keywords')):
                    self.logger.info(f"Trying to enrich keywords for dynamic intent '{intent_name}' (direct method)")
                    try:
                        # Call the enrichment method directly
                        enriched = scoring_system._enrich_keywords(keywords)
                        scoring_system.intent_keywords[intent_name] = list(enriched)
                        self.logger.info(f"Keywords enriched successfully for dynamic intent '{intent_name}': {len(enriched)} keywords")
                    except Exception as e:
                        self.logger.error(f"Erro ao enriquecer palavras-chave para intenção DINÂMICA '{intent_name}': {str(e)}")
            else:
                # Add only keywords that do not exist yet
                existing_keywords = set(scoring_system.intent_keywords[intent_name])
                self.logger.info(f"Keywords for dynamic intent '{intent_name}': {existing_keywords}")
                
                new_keywords = [kw for kw in keywords if kw not in existing_keywords]
                scoring_system.intent_keywords[intent_name].extend(new_keywords)
                self.logger.info(f"Added {len(new_keywords)} new keywords for dynamic intent '{intent_name}' (direct method)")
                
                # Try to call the enrichment method manually
                if hasattr(scoring_system, '_enrich_keywords') and callable(getattr(scoring_system, '_enrich_keywords')):
                    self.logger.info(f"Trying to enrich keywords for dynamic intent '{intent_name}' (direct method)")
                    try:
                        # Call the enrichment method directly
                        enriched = scoring_system._enrich_keywords(scoring_system.intent_keywords[intent_name])
                        scoring_system.intent_keywords[intent_name] = list(enriched)
                        self.logger.info(f"Keywords enriched successfully for dynamic intent '{intent_name}': {len(enriched)} keywords")
                    except Exception as e:
                        self.logger.error(f"Error enriching keywords for dynamic intent '{intent_name}': {str(e)}")
                        
                # Try to lemmatize the keywords manually
                if hasattr(scoring_system, 'nlp') and scoring_system.nlp is not None:
                    self.logger.info(f"Trying to lemmatize keywords for dynamic intent '{intent_name}' (direct method)")
                    try:
                        for keyword in scoring_system.intent_keywords[intent_name]:
                            if keyword not in scoring_system.keyword_lemmas_cache:
                                doc = scoring_system.nlp(keyword)
                                scoring_system.keyword_lemmas_cache[keyword] = [token.lemma_ for token in doc]
                                self.logger.info(f"Keyword '{keyword}' lemmatized: {scoring_system.keyword_lemmas_cache[keyword]}")
                    except Exception as e:
                        self.logger.error(f"Error lemmatizing keywords for dynamic intent '{intent_name}': {str(e)}")
                        
        except Exception as e:
            self.logger.error(f"Failed to update keywords directly for intent '{intent_name}': {str(e)}")
            
    def _update_patterns_in_entity_manager(self, intent_name: str, patterns: List[str]) -> None:
        """Helper method to update patterns in EntityManager.
        
        Args:
            intent_name: Intent name
            patterns: List of patterns
        """
        try:
            # Get the entity_manager from nlp_processor
            entity_manager = None
                
            # Check if the entity_manager is directly in nlp_processor
            if hasattr(self.nlp_processor, 'entity_manager') and self.nlp_processor.entity_manager is not None:
                entity_manager = self.nlp_processor.entity_manager
                self.logger.info("Accessing entity_manager directly from nlp_processor")
            # Check if there is an nested processor
            elif hasattr(self.nlp_processor, 'processor') and hasattr(self.nlp_processor.processor, 'entity_manager') and self.nlp_processor.processor.entity_manager is not None:
                entity_manager = self.nlp_processor.processor.entity_manager
                self.logger.info("Accessing entity_manager from nlp_processor.processor")
            else:
                self.logger.error("Unable to access the entity_manager of NLPProcessor")
                return
                    
            # Create an entity name based on the intent name
            intent_entity = f"INTENT_{intent_name.upper()}"
            self.logger.info(f"Creating entity '{intent_entity}' for intent '{intent_name}'")
            
            # Create patterns as simple dictionaries
            entity_patterns = []
            for pattern in patterns:
                entity_patterns.append({
                    'label': intent_entity,
                    'pattern': pattern,
                    'id': f"{intent_entity}_{len(entity_patterns)}"
                })
            
            self.logger.info(f"Adding {len(entity_patterns)} patterns for entity '{intent_entity}': {patterns}")
            
            # Add patterns to EntityRuler
            if entity_patterns:
                success = entity_manager.add_patterns_to_ruler(entity_patterns)
                if success:
                    self.logger.info(f"Added {len(entity_patterns)} patterns for entity '{intent_entity}' to EntityRuler")
                else:
                    self.logger.warning(f"Failed to add patterns for entity '{intent_entity}' to EntityRuler")
            
            # Update the entity to intent mapping in scoring_system
            scoring_system = None
            
            # Check if the scoring_system is directly in nlp_processor
            if hasattr(self.nlp_processor, 'scoring_system') and self.nlp_processor.scoring_system is not None:
                scoring_system = self.nlp_processor.scoring_system
                self.logger.info("Accessing scoring_system directly from nlp_processor to update mapping")
            # Check if there is an nested processor
            elif hasattr(self.nlp_processor, 'processor') and hasattr(self.nlp_processor.processor, 'scoring_system') and self.nlp_processor.processor.scoring_system is not None:
                scoring_system = self.nlp_processor.processor.scoring_system
                self.logger.info("Accessing scoring_system from nlp_processor.processor to update mapping")
            
            if scoring_system is not None:
                # Use the update_entity_intent_mapping method to update the entity
                if not self.nlp_processor.update_entity_intent_mapping(intent_entity, intent_name):
                    self.logger.warning(f"Failed to map entity: {intent_entity} -> {intent_name}")
                
                # Log the complete mapping for diagnosis (if available)
                if hasattr(scoring_system, 'entity_intent_map'):
                    self.logger.debug(f"Complete mapping: {scoring_system.entity_intent_map}")
            else:
                self.logger.error("Unable to access the scoring_system of NLPProcessor to update entity mapping")
                    
        except Exception as e:
            self.logger.error(f"Erro em _update_patterns_in_entity_manager: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def process_message(self, message: str) -> Dict[str, Any]:
        """
        Process a user message and return a response.
        
        Args:
            message: User message
            
        Returns:
            Dictionary containing the response and metadata
        """
        try:
            self.logger.info(f"Processing message: '{message}'")
            
            # 1. First check for static intents
            static_intent = self.static_intent_manager.detect_intent(message)
            if static_intent and static_intent['confidence'] >= 0.7:
                self.logger.info(f"Static intent detected: {static_intent['intent']} (confidence: {static_intent['confidence']:.2f})")
                return self._handle_static_intent(static_intent, message)
            
            # 2. If no static intent was detected, process normally
            self.logger.info("No static intent detected, processing with NLP")
            
            # Process the message with NLP
            self.logger.info("Sending message for NLP processing")
            intent, entities = self.nlp_processor.process_text(message)
            self.logger.info(f"Intent identified: {intent.name} (confidence: {intent.confidence:.2f})")
            self.logger.info(f"Entities extracted: {[str(e) for e in entities]}")
            
            # Update conversation context
            self._update_context(intent)
            
            # Execute action based on intent
            self.logger.info(f"Executing action for intent: {intent.name}")
            response = self._execute_intent(intent, message)
            
            # Log the generated response
            self.logger.info(f"Generated response: {response.get('response', '')[:50]}...")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return {
                'response': f"Desculpe, ocorreu um erro ao processar sua mensagem: {str(e)}",
                'intent': 'error',
                'confidence': 0.0,
                'source': 'error_handler'
            }
    
    def _handle_static_intent(self, static_intent: Dict, message: str) -> Dict[str, Any]:
        """
        Handle a detected static intent.
        
        Args:
            static_intent: Dictionary containing static intent information
            message: Original user message
            
        Returns:
            Dictionary containing the response
        """
        intent_type = static_intent['intent']
        confidence = static_intent.get('confidence', 1.0)
        self.logger.info(f"Processing static intent: {intent_type} (confidence: {confidence:.2f})")
        
        try:
            # Map to the appropriate handler method
            handlers = {
                'INTENT_RELATIONSHIPS': self._handle_show_relationships,
                'INTENT_LIST_TERMS': self._handle_list_terms,
                'INTENT_CAPABILITIES': self._handle_capabilities,
                'INTENT_HELP': self._handle_help_with_intent,
                'INTENT_ABOUT_ONTOMED': self._handle_about_ontomed
            }
            
            handler = handlers.get(intent_type)
            if not handler:
                self.logger.warning(f"No handler found for static intent: {intent_type}")
                return {
                    'response': "Desculpe, não consegui processar sua solicitação.",
                    'intent': intent_type,
                    'confidence': confidence,
                    'source': 'static_intent',
                    'error': 'handler_not_found'
                }
            
            # Call the appropriate handler
            self.logger.info(f"Calling handler for static intent: {intent_type}")
            # Create an Intent object to pass to the handler
            intent_obj = Intent(name=intent_type, confidence=confidence)
            # Call the handler with the necessary parameters
            response = handler(intent_obj, message)
            
            # Ensure the response has the required fields
            if not isinstance(response, dict):
                response = {'response': str(response) if response else 'Empty response'}
                
            # Add metadata to the response
            response.update({
                'intent': intent_type,
                'confidence': confidence,
                'source': 'static_intent'
            })
            
            # Create and update the context with the processed intent
            intent_obj = Intent(name=intent_type, confidence=confidence)
            self._update_context(intent_obj)
            
            self.logger.info(f"Generated response for static intent {intent_type}")
            return response
            
        except Exception as e:
            error_msg = f"Erro ao processar intenção estática {intent_type}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return {
                'response': f"Desculpe, ocorreu um erro ao processar sua solicitação: {str(e)}",
                'intent': intent_type,
                'confidence': confidence,
                'source': 'error_handler',
                'error': str(e)
            }
        
    def _update_context(self, intent: Intent) -> None:
        """
        Updates the conversation context based on the processed message.
        
        Args:
            intent: Processed message
        """
        context = st.session_state.chat_context
        
        # Update last intent
        context['last_intent'] = intent.name
        
        # Update entities
        context['last_entities'] = [{'value': e.value, 'entity_type': e.entity_type, 'start': e.start, 'end': e.end} for e in intent.entities]
        
        # Add mentioned concepts
        for entity in intent.entities:
            if entity.entity_type == 'termo_medico' and entity.value not in context['mentioned_concepts']:
                context['mentioned_concepts'].append(entity.value)
        
        # Update context in session_state
        st.session_state.chat_context = context
    
    def _execute_intent(self, intent_obj: Intent, text: str) -> Dict[str, Any]:
        """
        Execute the command corresponding to the identified intent.
        
        Args:
            intent_obj: Processed message
            
        Returns:
            Dictionary with response and metadata
        """
        intent_name = intent_obj.name
        entities = intent_obj.entities
        
        self.logger.info(f"Executing intent: '{intent_name}' for text: '{text}'")
        self.logger.info(f"Entities available: {[str(e) for e in entities]}")
        
        # Check for keywords related to scientific literature summaries
        literature_keywords = ["literature", "summary", "resumo", "literatura", "artigos", "papers"]
        found_keywords = [kw for kw in literature_keywords if kw.lower() in text.lower()]
        if found_keywords:
            self.logger.info(f"Keywords of scientific literature found in text: {found_keywords}")
            self.logger.info(f"Intent identified: '{intent_name}', expected: 'scientific_literature_summary'")
            
            # Check if scientific_literature_summary is in the mapping
            if 'scientific_literature_summary' in self._intent_template_mapping:
                self.logger.info(f"'scientific_literature_summary' is in the template mapping")
            else:
                self.logger.info(f"'scientific_literature_summary' is NOT in the template mapping")
                self.logger.info(f"Templates available: {list(self._intent_template_mapping.keys())}")
        
        # Check if we have a valid intent
        if not intent_name:
            self.logger.info(f"Intent is empty, using fallback")
            return self._generate_fallback_response(intent_obj, text)
        
        # Execute command based on intent
        if intent_name == "buscar_conceito":
            self.logger.info(f"Executing handler for buscar_conceito")
            return self._handle_explain_term(intent_obj, text)  # Using _handle_explain_term to explain term
        elif intent_name == "listar_termos":
            self.logger.info(f"Executing handler for listar_termos")
            return self._handle_list_terms(intent_obj, text)
        elif intent_name == "relacionamentos":
            self.logger.info(f"Executing handler for relacionamentos")
            return self._handle_show_relationships(intent_obj, text)
        elif intent_name == "capacidades":
            self.logger.info(f"Executing handler for capacidades")
            return self._handle_capabilities(intent_obj, text)
        elif intent_name == "ajuda":
            self.logger.info(f"Executing handler for ajuda")
            return self._handle_help_with_intent(intent_obj, text)
        # Check if the intent has a template associated
        elif intent_name in self._intent_template_mapping:
            self.logger.info(f"Intent '{intent_name}' has template associated: {self._intent_template_mapping[intent_name]}")
            return self._handle_template_based_intent(intent_obj, text, intent_name)
        else:
            self.logger.info(f"Intent '{intent_name}' does not have a template associated, using fallback")
            self.logger.info(f"Templates available: {list(self._intent_template_mapping.keys())}")
            return self._generate_fallback_response(intent_obj, text)
    
    def _handle_capabilities(self, intent_obj: Intent, text: str) -> Dict[str, Any]:
        """
        Handles the intent to list the chatbot's capabilities.
        Dynamically extracts capabilities based on templates and static capabilities.
        
        Args:
            intent_obj: Processed message
            
        Returns:
            Dictionary with response and metadata
        """
        try:
            self.logger.info("Executing intent: capabilities - Listing chatbot capabilities")
            
            # 1. Static capabilities (basic system functions)
            static_capabilities = [
                {
                    "name": "Listar conceitos médicos",
                    "description": "Mostrar todos os conceitos médicos disponíveis na base de conhecimento",
                    "examples": ["Quais conceitos médicos estão disponíveis?", "Liste os termos médicos", "Mostre todos os conceitos"]
                },
                {
                    "name": "Buscar conceito",
                    "description": "Buscar um conceito médico específico na base de conhecimento",
                    "examples": ["Busque informações sobre diabetes", "Procure por hipertensão", "Encontre o termo asma"]
                },
                {
                    "name": "Relacionamentos entre conceitos",
                    "description": "Mostrar os relacionamentos entre dois conceitos médicos diferentes",
                    "examples": ["Qual a relação entre diabetes e obesidade?", "Como hipertensão e doença cardíaca estão relacionadas?", "Mostre a conexão entre asma e alergia"]
                },
                {
                    "name": "Mostrar relacionamentos",
                    "description": "Exibir os relacionamentos semânticos de um conceito médico",
                    "examples": ["Quais são os relacionamentos de diabetes?", "Mostre as relações de hipertensão", "Como asma se relaciona com outros conceitos?"]                                }
            ]
            
            # 2. Dynamic capabilities based on available templates
            dynamic_capabilities = []
            
            # Get all available templates
            templates = self.template_manager.get_templates()
            
            # Extract capabilities dynamically from templates using LLM information
            for template in templates:
                template_id = template.get("id", "")
                intent_info = template.get("intent_info", {})
                
                if not template_id or not intent_info:
                    continue
                
                # Extrair informações relevantes do intent_info
                intent_name = intent_info.get("intent", "")
                keywords = intent_info.get("keywords", [])
                keywords_pt = intent_info.get("keywords_pt", [])
                keywords_en = intent_info.get("keywords_en", [])
                patterns = intent_info.get("patterns", [])
                patterns_pt = intent_info.get("patterns_pt", [])
                patterns_en = intent_info.get("patterns_en", [])
                
                # Combine keywords and patterns for examples
                all_keywords = list(set(keywords + keywords_pt + keywords_en))
                all_patterns = list(set(patterns + patterns_pt + patterns_en))
                
                # Create examples from patterns and keywords
                examples = []
                
                # Use up to 3 patterns as examples
                for pattern in all_patterns[:3]:
                    if pattern and len(pattern) < 50:  # Avoid patterns that are too long
                        examples.append(pattern)
                
                # If we don't have 3 examples, add some keywords
                if len(examples) < 3:
                    for keyword in all_keywords[:3 - len(examples)]:
                        if keyword and keyword not in examples:
                            examples.append(f"{keyword}?")
                
                # If we don't have enough examples, use the intent name
                if not examples and intent_name:
                    examples.append(f"Informações sobre {intent_name.replace('_', ' ')}")                
                
                # Create a dynamic capability for this template
                if intent_name:
                    # Format the capability name
                    capability_name = intent_name.replace('_', ' ').title()
                    
                    # Create description based on the intent name
                    description = f"Fornecer informações sobre {intent_name.replace('_', ' ')}"
                    
                    # Create the capability
                    capability = {
                        "name": capability_name,
                        "description": description,
                        "examples": examples
                    }
                    
                    # Avoid duplicates
                    if not any(cap["name"] == capability["name"] for cap in dynamic_capabilities):
                        dynamic_capabilities.append(capability)
                        self.logger.info(f"Dynamic capability created for template '{template_id}': {capability['name']}")
            
            # If no dynamic capabilities, log a warning
            if not dynamic_capabilities:
                self.logger.warning("Nenhuma capacidade dinâmica foi criada a partir dos templates. Verifique a análise do LLM.")
            
            # Combine static and dynamic capabilities
            all_capabilities = static_capabilities + dynamic_capabilities
            
            # Build the response
            response = "Aqui estão as minhas capacidades como assistente médico virtual:\n\n"
            
            for i, capability in enumerate(all_capabilities, 1):
                response += f"**{i}. {capability['name']}**\n"
                response += f"{capability['description']}\n"
                response += "Exemplos de perguntas:\n"
                for example in capability['examples']:
                    response += f"- {example}\n"
                response += "\n"
            
            response += "\nVocê pode me fazer perguntas usando linguagem natural sobre qualquer um desses tópicos!"
            
            return {
                'response': response,
                'intent': 'capacidades',
                'confidence': 1.0,
                'source': 'dynamic',
                'capabilities': all_capabilities  # Include capabilities in the response for reference
            }
            
        except Exception as e:
            self.logger.error(f"Error listing capabilities: {str(e)}", exc_info=True)
            return {
                'response': "Desculpe, ocorreu um erro ao tentar listar minhas capacidades.",
                'intent': 'capacidades',
                'confidence': 1.0,
                'source': 'error'
            }
            
    def _handle_list_terms_by_concept(self, intent_obj: Intent, text: str) -> Dict[str, Any]:
        """
        Handle the intent to list terms.
        
        Args:
            intent_obj: Processed intent
            
        Returns:
            Dictionary with response and metadata
        """
        # Extract relevant entities
        concept_terms = [e.value for e in intent_obj.entities if e.entity_type == 'termo_medico']
        
        if not concept_terms:
            return {
                'response': "Please specify which medical concept you would like to list.",
                'intent': 'listar_termos',
                'confidence': intent_obj.confidence,
                'source': 'list_terms'
            }
        
        # Search concepts in API
        try:
            # Use the first term as search term
            search_term = concept_terms[0]
            
            # Check cache first
            if search_term in self._concept_cache:
                concepts = self._concept_cache[search_term]
            else:
                # Search in API
                concepts = self.api_client.search_concepts(search_term)
                # Store in cache
                self._concept_cache[search_term] = concepts
            
            # Format response
            if concepts:
                response_text = f"I found the following concepts related to '{search_term}':\n\n"
                for i, concept in enumerate(concepts[:5], 1):
                    name = concept.get('label', concept.get('display_name', concept.get('id', 'Sem nome')))
                    description = concept.get('description', 'Sem descrição disponível')
                    response_text += f"**{i}. {name}**\n{description}\n\n"
                
                if len(concepts) > 5:
                    response_text += f"*...and more {len(concepts) - 5} concepts found.*"
            else:
                response_text = f"I could not find any concepts related to '{search_term}'. Try another term."
            
            return {
                'response': response_text,
                'intent': 'buscar_conceito',
                'confidence': intent_obj.confidence,
                'source': 'search_concept',
                'concepts': concepts
            }
        except Exception as e:
            self.logger.error(f"Error searching concepts: {str(e)}", exc_info=True)
            return {
                'response': f"Sorry, an error occurred while searching concepts: {str(e)}",
                'intent': 'buscar_conceito',
                'confidence': intent_obj.confidence,
                'source': 'error_handler'
            }
    
    def _handle_explain_term(self, intent_obj: Intent, text: str) -> Dict[str, Any]:
        """
        Handle the intent to explain a medical term.
        
        Args:
            intent_obj: Processed intent
            
        Returns:
            Dictionary with response and metadata
        """
        # Extract the term to be explained
        term = None
        for entity in intent_obj.entities:
            if entity.entity_type == 'termo_medico':
                term = entity.value
                break
                
        if not term:
            return {
                'response': "Sorry, but I couldn't identify which medical term you would like me to explain. Could you please specify the term?",
                'intent': 'explicar_termo',
                'confidence': intent_obj.confidence,
                'source': 'rule'
            }
            
        # Log the term being explained
        self.logger.info(f"Explaining medical term: '{term}'")
        
        # Check if the term contains underscore for special treatment
        has_underscore = '_' in term
        if has_underscore:
            self.logger.info(f"Term with underscore detected: '{term}'. Applying special treatment.")

        try:
            # Search concept in API
            concept = self.api_client.get_concept_by_term(term)
            
            if concept:
                # Prepare data for the template
                concept_data = {
                    # Fields for template compatibility
                    'display_name': concept.get('label', concept.get('display_name', term)),
                    'id': concept.get('id', f'unknown_{term}'),
                    'type': concept.get('type', 'Medical Concept'),
                    'description': concept.get('description', ''),
                    
                    # Additional fields for processing
                    'concept_name': concept.get('label', concept.get('display_name', term)),
                    'concept_description': concept.get('description', ''),
                    'concept_type': concept.get('type', 'Conceito'),
                    'relationships': concept.get('relationships', [])
                }
                
                # Log the concept data for debugging
                self.logger.info(f"Concept data for explanation: {concept_data}")
                
                # If no description, try to create one based on the name
                if not concept_data['description'] and '_' in term:
                    parts = term.split('_')
                    if len(parts) >= 2:
                        category = parts[0]
                        condition = '_'.join(parts[1:]).replace('_', ' ')
                        
                        # Mapping common categories to more precise descriptions
                        category_descriptions = {
                            'temperature': 'temperatura corporal',
                            'respiratoryrate': 'frequência respiratória',
                            'bloodpressure': 'pressão arterial',
                            'heartrate': 'frequência cardíaca',
                            'glucose': 'nível de glicose',
                            'oxygen': 'saturação de oxigênio',
                            'pain': 'sensação de dor'
                        }
                        
                        category_desc = category_descriptions.get(category.lower(), category)
                        
                        # Generate automatic description based on the category
                        concept_data['description'] = f"Medical condition related to {category_desc} characterized by {condition}"
                        
                        # For specific cases like Temperature_High_fever
                        if category.lower() == 'temperature' and 'fever' in condition.lower():
                            concept_data['description'] = f"Medical condition characterized by elevated body temperature (fever), typically above 38.5°C. Can be a symptom of infection, inflammation, or other pathological conditions."
                        
                        # Update both description fields
                        concept_data['concept_description'] = concept_data['description']
                        
                        self.logger.info(f"Automatically generated description: {concept_data['description']}")


                
                # Use template to generate explanation
                template = self.template_manager.get_template('concept_explanation')
                
                if template:
                    # Generate explanation using the template and LLM
                    explanation = self.template_manager.generate_content(
                        template,
                        concept_data,
                        temperature=0.7,
                        max_tokens=500
                    )
                    
                    return {
                        'response': explanation,
                        'intent': 'explicar_termo',
                        'confidence': intent_obj.confidence,
                        'source': 'template_llm',
                        'concept': concept
                    }
                else:
                    # Fallback: use direct concept description
                    description = concept.get('description', '')
                    if description:
                        response_text = f"**{concept_data['concept_name']}** é {description}"
                    else:
                        response_text = f"I found the concept **{concept_data['concept_name']}**, but I don't have a detailed description available."
                    
                    return {
                        'response': response_text,
                        'intent': 'explicar_termo',
                        'confidence': intent_obj.confidence,
                        'source': 'direct_concept',
                        'concept': concept
                    }
            else:
                # Term not found, but we can create a synthetic concept for terms with underscore
                if '_' in term:
                    self.logger.info(f"Creating synthetic concept for term with underscore: {term}")
                    
                    # Create a synthetic concept based on the parts of the term
                    parts = term.split('_')
                    category = parts[0]
                    condition = '_'.join(parts[1:]).replace('_', ' ')
                    
                    # Map common categories
                    category_descriptions = {
                        'temperature': 'temperatura corporal',
                        'respiratoryrate': 'frequência respiratória',
                        'bloodpressure': 'pressão arterial',
                        'heartrate': 'frequência cardíaca',
                        'glucose': 'nível de glicose',
                        'oxygen': 'saturação de oxigênio',
                        'pain': 'sensação de dor'
                    }
                    
                    category_desc = category_descriptions.get(category.lower(), category)
                    
                    # Create description based on the term structure
                    description = f"Condição médica relacionada a {category_desc} caracterizada por {condition}"
                    
                    # For specific cases
                    if category.lower() == 'temperature' and 'fever' in condition.lower():
                        description = f"Condição médica caracterizada por temperatura corporal elevada (febre), tipicamente acima de 38.5°C. Pode ser sintoma de infecção, inflamação ou outras condições patológicas."
                    
                    # Create synthetic concept
                    synthetic_concept = {
                        'id': f"synthetic_{term.lower().replace(' ', '_')}",
                        'label': term.replace('_', ' '),
                        'display_name': term.replace('_', ' '),
                        'description': description,
                        'type': 'Conceito Médico Sintético',
                        'relationships': []
                    }
                    
                    # Prepare data for the template
                    concept_data = {
                        'display_name': synthetic_concept['display_name'],
                        'id': synthetic_concept['id'],
                        'type': synthetic_concept['type'],
                        'description': synthetic_concept['description'],
                        'concept_name': synthetic_concept['display_name'],
                        'concept_description': synthetic_concept['description'],
                        'concept_type': synthetic_concept['type'],
                        'relationships': []
                    }
                    
                    self.logger.info(f"Synthetic concept created: {concept_data}")
                    
                    # Use template to generate explanation
                    template = self.template_manager.get_template('concept_explanation')
                    
                    if template:
                        # Generate explanation using the template and LLM
                        explanation = self.template_manager.generate_content(
                            template,
                            concept_data,
                            temperature=0.7,
                            max_tokens=500
                        )
                        
                        return {
                            'response': explanation,
                            'intent': 'explicar_termo',
                            'confidence': intent_obj.confidence,
                            'source': 'template_llm_synthetic',
                            'concept': synthetic_concept
                        }
                
                # Final fallback: use LLM to generate explanation
                prompt = f"""Explique o termo médico '{term}' de forma clara e educativa. 
                Inclua definição, contexto médico, relações com outros conceitos e importância clínica."""
                
                explanation = self.llm.generate_text(prompt)
                
                return {
                    'response': explanation,
                    'intent': 'explicar_termo',
                    'confidence': intent_obj.confidence,
                    'source': 'llm_fallback',
                    'concept': None,
                    'term': term
                }
        except Exception as e:
            self.logger.error(f"Error explaining term: {str(e)}", exc_info=True)
            return {
                'response': f"Desculpe, ocorreu um erro ao explicar o termo '{term}': {str(e)}",
                'intent': 'explicar_termo',
                'confidence': intent_obj.confidence,
                'source': 'error_handler'
            }
    
    def _handle_show_relationships(self, intent_obj: Intent, text: str) -> Dict[str, Any]:
        """
        Handle the intent to show relationships between concepts.
        
        Args:
            intent_obj: Intent object containing entities
            text: Original user message
            
        Returns:
            Dictionary with response and metadata
        """
        # Extract relevant entities and filter out the word 'relacionamentos' which is not a medical term
        term_entities = [e.value for e in intent_obj.entities if e.entity_type == 'termo_medico' and e.value.lower() != 'relacionamentos']
        
        # Special case: only one medical term
        if len(term_entities) == 1:
            term = term_entities[0]
            try:
                # Search for the concept for the term
                self.logger.info(f"Searching for concept for term: '{term}'")
                concept = self.api_client.get_concept_by_term(term)
                
                if not concept:
                    self.logger.warning(f"Concept not found for term: '{term}'")
                    return {
                        'response': f"Não encontrei o conceito médico '{term}'. Por favor, verifique o termo ou especifique dois conceitos médicos para que eu possa mostrar os relacionamentos entre eles.",
                        'intent': 'relacionamentos',
                        'confidence': intent_obj.confidence,
                        'source': 'show_relationships'
                    }
                
                # Search for relationships for the concept
                concept_id = concept.get('id')
                concept_label = concept.get('label', term)
                
                self.logger.info(f"Concept found: ID={concept_id}, Label={concept_label}")
                
                if not concept_id:
                    self.logger.warning(f"Concept found for '{term}', but with invalid ID")
                    return {
                        'response': f"Encontrei o conceito '{term}', mas ele não possui um identificador válido. Por favor, tente com outro conceito ou especifique dois conceitos para relacionar.",
                        'intent': 'relacionamentos',
                        'confidence': intent_obj.confidence,
                        'source': 'show_relationships'
                    }
                
                # Check if the concept already has relationships included
                existing_relationships = concept.get('relationships', [])
                
                if existing_relationships and len(existing_relationships) > 0:
                    self.logger.info(f"Using {len(existing_relationships)} relationships already included in the concept")
                    relationships = existing_relationships
                else:
                    # Get relationships for the concept via a separate API call
                    self.logger.info(f"Searching for relationships for concept ID: {concept_id}")
                    relationships = self.api_client.get_relationships(concept_id)
                
                if not relationships:
                    return {
                        'response': f"Não encontrei relacionamentos para o conceito '{term}'. Por favor, tente com outro conceito ou especifique dois conceitos para relacionar.",
                        'intent': 'relacionamentos',
                        'confidence': intent_obj.confidence,
                        'source': 'show_relationships'
                    }
                
                # Format response
                response_text = f"Relationships for concept **{term}**:\n\n"
                
                # Group relationships by type for better organization
                relationship_types = {}
                
                for rel in relationships:
                    # Check if rel is a dictionary
                    if isinstance(rel, dict):
                        rel_type = rel.get('type', rel.get('predicate', 'relacionado a'))
                        target = rel.get('target', '')
                        
                        # Extract the target name from the URI if necessary
                        target_name = target
                        if '#' in target:
                            target_name = target.split('#')[-1]
                        elif '/' in target:
                            target_name = target.split('/')[-1]
                        
                        # Replace underscores with spaces for better readability
                        target_name = target_name.replace('_', ' ')
                        
                        # Add to the grouped dictionary
                        if rel_type not in relationship_types:
                            relationship_types[rel_type] = []
                        
                        relationship_info = {
                            'target_name': target_name,
                            'details': rel.get('details', '')
                        }
                        relationship_types[rel_type].append(relationship_info)
                    elif isinstance(rel, str):
                        # If it's a string, use it as a generic relationship type
                        if 'Outros' not in relationship_types:
                            relationship_types['Outros'] = []
                        relationship_types['Outros'].append({'target_name': rel, 'details': ''})
                
                # Generate formatted response by relationship type
                for rel_type, rel_items in relationship_types.items():
                    response_text += f"**{rel_type}**:\n"
                    
                    for i, item in enumerate(rel_items, 1):
                        response_text += f"{i}. **{item['target_name']}**"
                        
                        if item['details']:
                            response_text += f" - {item['details']}"
                            
                        response_text += "\n"
                    
                    response_text += "\n"
                
                return {
                    'response': response_text,
                    'intent': 'relacionamentos',
                    'confidence': intent_obj.confidence,
                    'source': 'show_relationships_single_term',
                    'term': term
                }
                
            except Exception as e:
                self.logger.error(f"Erro ao buscar relacionamentos para um termo: {str(e)}", exc_info=True)
                return {
                    'response': f"Desculpe, ocorreu um erro ao buscar relacionamentos para '{term}': {str(e)}",
                    'intent': 'relacionamentos',
                    'confidence': intent_obj.confidence,
                    'source': 'error_handler'
                }
        
        # Normal case: two or more medical terms
        elif len(term_entities) == 0:
            return {
                'response': "Por favor, especifique dois conceitos médicos para que eu possa mostrar os relacionamentos entre eles.",
                'intent': 'relacionamentos',
                'confidence': intent_obj.confidence,
                'source': 'show_relationships'
            }
        
        # Use the first two terms
        term1 = term_entities[0]
        term2 = term_entities[1]
        
        try:
            # Search for relationships in the API
            relationships = self.api_client.get_relationships_between(term1, term2)
            
            if relationships:
                # Format response
                response_text = f"Relacionamentos entre **{term1}** e **{term2}**:\n\n"
                
                for i, rel in enumerate(relationships, 1):
                    # Check if rel is a dictionary
                    if isinstance(rel, dict):
                        # Get the relationship type
                        rel_type = rel.get('type', rel.get('predicate', 'relacionado a'))
                        
                        # Check if it's a synthetic relationship
                        is_synthetic = rel.get('synthetic', False)
                        
                        # Add relationship information
                        response_text += f"{i}. **{term1}** *{rel_type}* **{term2}**"
                        
                        # Add synthetic indication if applicable
                        if is_synthetic:
                            response_text += " *(relacionamento inferido)*"
                        
                        response_text += "\n"
                        
                        # Add description if available
                        if 'description' in rel:
                            response_text += f"   Descrição: {rel['description']}\n"
                            
                        # Add details if available
                        if 'details' in rel:
                            response_text += f"   Detalhes: {rel['details']}\n"
                            
                        # Add debug information if available and in debug mode
                        if 'debug_info' in rel and self.debug_mode:
                            debug_info = rel['debug_info']
                            response_text += f"   Debug: {debug_info}\n"
                    elif isinstance(rel, str):
                        # If it's a string, use it as a relationship type
                        response_text += f"{i}. **{term1}** *{rel}* **{term2}**\n"
                    else:
                        # If it's neither a dictionary nor a string
                        response_text += f"{i}. **{term1}** está relacionado a **{term2}**\n"
            else:
                # Didn't find direct relationships, try inferring with LLM
                prompt = f"Explique a relação entre os conceitos médicos '{term1}' e '{term2}'. Seja conciso e preciso."
                explanation = self.llm.generate_text(prompt)
                
                response_text = f"Não encontrei relacionamentos diretos entre **{term1}** e **{term2}** na ontologia, mas posso inferir:\n\n{explanation}"
            
            return {
                'response': response_text,
                'intent': 'relacionamentos',
                'confidence': intent_obj.confidence,
                'source': 'show_relationships',
                'terms': [term1, term2]
            }
        except Exception as e:
            self.logger.error(f"Error searching for relationships: {str(e)}", exc_info=True)
            return {
                'response': f"Desculpe, ocorreu um erro ao buscar relacionamentos: {str(e)}",
                'intent': 'relacionamentos',
                'confidence': intent_obj.confidence,
                'source': 'error_handler'
            }
    def _handle_list_terms(self, intent_obj: Intent, text: str) -> Dict[str, Any]:
        """
        List available medical terms/concepts.
        
        Args:
            intent_obj: Processed intent object
            text: Original user message
            
        Returns:
            Dictionary with the list of terms
        """
        try:
            # Register the intent clearly in the logs
            self.logger.info("Executing intent: listar_termos - Listing all available medical concepts")
            
            # Search for all available concepts
            self.logger.info("Searching for available medical concepts from the API")
            concepts = self.api_client.get_concepts()
            
            # Verify if we have concepts
            if not concepts:
                self.logger.warning("No concepts returned by the API")
                return {
                    'response': "Desculpe, não encontrei nenhum termo médico disponível no momento.",
                    'intent': 'listar_termos',
                    'confidence': 1.0,
                    'source': 'api'
                }
                
            # Filter valid concepts (that have at least id, label or display_name)
            valid_concepts = [c for c in concepts if isinstance(c, dict) and (c.get('id') or c.get('label') or c.get('display_name'))]
            
            self.logger.info(f"Total of concepts found: {len(valid_concepts)}")
            
            # Limit the number of terms to avoid overloading the response
            max_terms = 20
            total_terms = len(valid_concepts)
            
            # Extract names of concepts
            term_names = []
            for concept in valid_concepts[:max_terms]:
                # Use label, display_name or extract from ID
                name = concept.get('label') or concept.get('display_name')
                if not name and 'id' in concept:
                    concept_id = concept['id']
                    if concept_id:
                        if '#' in concept_id:
                            name = concept_id.split('#')[-1]
                        elif '/' in concept_id:
                            name = concept_id.split('/')[-1]
                        else:
                            name = concept_id
                
                if name and name not in term_names:
                    # Remove underscores and format for better readability
                    formatted_name = name.replace('_', ' ')
                    term_names.append(formatted_name)
            
            # Sort terms alphabetically for better presentation
            term_names.sort()
            
            # Build the response
            if term_names:
                # Format as numbered list for better readability
                terms_text = "\n".join([f"{i+1}. {name}" for i, name in enumerate(term_names)])
                
                if total_terms > max_terms:
                    response = f"Aqui estão alguns dos conceitos médicos disponíveis (mostrando {len(term_names)} de {total_terms}):\n\n{terms_text}\n\nVocê pode perguntar sobre qualquer um desses conceitos usando 'O que é [conceito]?', 'Explique [conceito]' ou 'Mostre relacionamentos de [conceito]'."
                else:
                    response = f"Aqui estão os conceitos médicos disponíveis:\n\n{terms_text}\n\nVocê pode perguntar sobre qualquer um desses conceitos usando 'O que é [conceito]?', 'Explique [conceito]' ou 'Mostre relacionamentos de [conceito]'."
            else:
                response = "Desculpe, não consegui extrair os nomes dos conceitos médicos disponíveis. Tente perguntar sobre um conceito específico como 'O que é febre?' ou 'Explique hipertensão'."
            
            return {
                'response': response,
                'intent': 'listar_termos',
                'confidence': 1.0,
                'source': 'api',
                'concepts': valid_concepts[:max_terms]  # Include concepts in the response for reference
            }
        except Exception as e:
            self.logger.error(f"Error listing medical terms: {str(e)}", exc_info=True)
            return {
                'response': "Desculpe, ocorreu um erro ao tentar listar os termos médicos disponíveis.",
                'intent': 'error',
                'confidence': 0.0,
                'source': 'error_handler'
            }

    def _handle_show_relationships(self, intent_obj: Intent, text: str) -> Dict[str, Any]:
        """
        Handle the intent to show relationships between concepts.
        
        Args:
            intent_obj: Intent object containing entities
            text: Original user message
            
        Returns:
            Dictionary with the response and metadata
        """
        # Extract relevant entities and filter out the word 'relacionamentos' which is not a medical term
        term_entities = [e.value for e in intent_obj.entities if e.entity_type == 'termo_medico' and e.value.lower() != 'relacionamentos']
        
        # Verify if we have enough entities
        if not term_entities:
            return {
                'response': "Por favor, especifique pelo menos um termo médico para que eu possa mostrar os relacionamentos.",
                'intent': 'relacionamentos',
                'confidence': intent_obj.confidence,
                'source': 'show_relationships'
            }
        
        # Special case: only one medical term
        if len(term_entities) == 1:
            term = term_entities[0]
            try:
                # Search for the concept for the term
                self.logger.info(f"Searching for concept for term: '{term}'")
                concept = self.api_client.get_concept_by_term(term)
                
                if not concept:
                    self.logger.warning(f"Concept not found for term: '{term}'")
                    return {
                        'response': f"Não encontrei o conceito médico '{term}'. Por favor, verifique o termo ou especifique dois conceitos médicos para que eu possa mostrar os relacionamentos entre eles.",
                        'intent': 'relacionamentos',
                        'confidence': intent_obj.confidence,
                        'source': 'show_relationships',
                        'term': term
                    }
                
                # Search for relationships for the concept
                concept_id = concept.get('id')
                concept_label = concept.get('label', term)
                
                self.logger.info(f"Concept found: ID={concept_id}, Label={concept_label}")
                
                if not concept_id:
                    self.logger.warning(f"Concept found for '{term}', but without a valid ID")
                    return {
                        'response': f"Encontrei o conceito '{term}', mas ele não possui um identificador válido. Por favor, tente com outro conceito ou especifique dois conceitos para relacionar.",
                        'intent': 'relacionamentos',
                        'confidence': intent_obj.confidence,
                        'source': 'show_relationships',
                        'term': term
                    }
            
                # Search for relationships for the concept
                relationships = self.api_client.get_relationships(concept_id)
                
                if not relationships:
                    return {
                        'response': f"Não encontrei relacionamentos para o conceito '{concept_label}'. Tente com outro termo ou especifique dois conceitos para relacionar.",
                        'intent': 'relacionamentos',
                        'confidence': intent_obj.confidence,
                        'source': 'show_relationships',
                        'term': term
                    }
                
                # Format response
                response_text = f"## Relacionamentos para **{concept_label}**:\n\n"
                
                # Group relationships by type
                rel_by_type = {}
                for rel in relationships:
                    if isinstance(rel, dict):
                        rel_type = rel.get('type', rel.get('predicate', 'relacionado a'))
                        target = rel.get('target', '')
                        
                        # Extract the target name from the URI if necessary
                        if '#' in target:
                            target = target.split('#')[-1]
                        elif '/' in target:
                            target = target.split('/')[-1]
                        
                        # Format for better readability
                        target = target.replace('_', ' ')
                        
                        if rel_type not in rel_by_type:
                            rel_by_type[rel_type] = []
                        rel_by_type[rel_type].append(target)
                
                # Build the grouped response
                for rel_type, targets in rel_by_type.items():
                    response_text += f"**{rel_type}**:\n"
                    for i, target in enumerate(targets, 1):
                        response_text += f"{i}. {target}\n"
                    response_text += "\n"
                
                return {
                    'response': response_text,
                    'intent': 'relacionamentos',
                    'confidence': intent_obj.confidence,
                    'source': 'show_relationships',
                    'term': term
                }
                
            except Exception as e:
                self.logger.error(f"Error find relationships for the term '{term}': {str(e)}", exc_info=True)
                return {
                    'response': f"Ocorreu um erro ao buscar relacionamentos para o termo '{term}': {str(e)}",
                    'intent': 'relacionamentos',
                    'confidence': intent_obj.confidence,
                    'source': 'error_handler',
                    'term': term
                }
    
        # Case normal: two or more medical terms
        elif len(term_entities) > 1:
            # Use the first two terms
            term1 = term_entities[0]
            term2 = term_entities[1]
            
            try:
                # Search for relationships in the API
                relationships = self.api_client.get_relationships_between(term1, term2)
                
                if relationships:
                    # Format response
                    response_text = f"Relacionamentos entre **{term1}** e **{term2}**:\n\n"
                    
                    for i, rel in enumerate(relationships, 1):
                        if isinstance(rel, dict):
                            # Get the type of relationship
                            rel_type = rel.get('type', rel.get('predicate', 'relacionado a'))
                            
                            # Check if it is a synthetic relationship
                            is_synthetic = rel.get('synthetic', False)
                            
                            # Add relationship information
                            response_text += f"{i}. **{term1}** *{rel_type}* **{term2}**"
                            
                            # Add indication that it is synthetic if applicable
                            if is_synthetic:
                                response_text += " *(relacionamento inferido)*"
                            
                            response_text += "\n"
                            
                            # Add description if available
                            if 'description' in rel:
                                response_text += f"   Description: {rel['description']}\n"
                                
                            # Add details if available
                            if 'details' in rel:
                                response_text += f"   Detalhes: {rel['details']}\n"
                                
                            # Add debug information if available and we are in debug mode
                            if 'debug_info' in rel and self.debug_mode:
                                debug_info = rel['debug_info']
                                response_text += f"   Debug: {debug_info}\n"
                        elif isinstance(rel, str):
                            # If it is a string, use it as the relationship type
                            response_text += f"{i}. **{term1}** *{rel}* **{term2}**\n"
                        else:
                            # If it is neither a dictionary nor a string
                            response_text += f"{i}. **{term1}** está relacionado a **{term2}**\n"
                else:
                    # If no direct relationships were found, try to infer with LLM
                    prompt = f"Explique a relação entre os conceitos médicos '{term1}' e '{term2}'. Seja conciso e preciso."
                    explanation = self.llm.generate_text(prompt)
                    
                    response_text = f"Nenhum relacionamento direto encontrado entre **{term1}** e **{term2}** na ontologia, mas posso inferir:\n\n{explanation}"
                
                return {
                    'response': response_text,
                    'intent': 'relacionamentos',
                    'confidence': intent_obj.confidence,
                    'source': 'show_relationships',
                    'terms': [term1, term2]
                }
                
            except Exception as e:
                self.logger.error(f"Error find relationships between '{term1}' and '{term2}': {str(e)}", exc_info=True)
                return {
                    'response': f"Ocorreu um erro ao buscar relacionamentos entre '{term1}' e '{term2}': {str(e)}",
                    'intent': 'relacionamentos',
                    'confidence': intent_obj.confidence,
                    'source': 'error_handler',
                    'terms': [term1, term2]
                }

    def _handle_help(self, text: str) -> Dict[str, Any]:
        """
        Generate a help response with the system capabilities.
        Includes static and dynamic commands based on templates.
        
        Args:
            text: Original user message
            
        Returns:
            Dictionary with the help response
        """
        # Static commands
        static_commands = [
            ("Listar termos/conceitos", [
                "Liste os conceitos médicos",
                "Quais termos você conhece?"
            ]),
            ("Mostrar relacionamentos", [
                "Mostre os relacionamentos de diabetes",
                "Quais as relações entre hipertensão e diabetes?"
            ]),
            ("Explicar termos médicos", [
                "O que é diabetes?",
                "Defina hipertensão"
            ]),
            ("Capacidades do sistema", [
                "O que você pode fazer?",
                "Quais são suas capacidades?"
            ])
        ]

        # Dynamic commands based on templates
        dynamic_commands = []
        try:
            templates = self.template_manager.get_templates()
            for template in templates:
                intent_info = template.get('intent_info', {})
                if intent_info and 'intent' in intent_info and 'description' in intent_info:
                    intent_name = intent_info['intent']
                    description = intent_info['description']
                    examples = intent_info.get('examples', [])
                    
                    # Add examples only if they exist
                    if examples:
                        dynamic_commands.append((description, examples))
                    else:
                        dynamic_commands.append((description, [f"{description}"]))
        except Exception as e:
            self.logger.error(f"Error loading dynamic commands: {str(e)}")

        # Build the help text
        help_text = "## Ajuda do OntoMed\n\n"
        help_text += "Aqui estão alguns exemplos do que posso fazer:\n\n"
        
        # Add static commands
        help_text += "### Comandos Básicos\n"
        for category, examples in static_commands:
            help_text += f"- **{category}**:\n"
            for example in examples:
                help_text += f"  - \"{example}\"\n"
            help_text += "\n"
        
        # Add dynamic commands if they exist
        if dynamic_commands:
            help_text += "### Comandos Avançados\n"
            for description, examples in dynamic_commands:
                help_text += f"- **{description}**:\n"
                for example in examples:
                    help_text += f"  - \"{example}\"\n"
                help_text += "\n"
        
        help_text += "\nPosso ajudar com explicações sobre termos médicos, listar conceitos e mostrar relacionamentos entre eles."
        
        return {
            'response': help_text,
            'intent': 'INTENT_HELP',
            'confidence': 1.0,
            'source': 'static_intent',
            'has_dynamic_commands': len(dynamic_commands) > 0
        }
    
    def _handle_list_terms(self, intent_obj: Intent, text: str) -> Dict[str, Any]:
        """
        List available medical terms/concepts.
        
        Args:
            intent_obj: Processed intent object
            text: Original user message
            
        Returns:
            Dictionary with the list of terms
        """
        try:
            # Search for all concepts in the API
            concepts = self.api_client.get_concepts()
            
            if not concepts:
                return {
                    'response': "Não consegui encontrar nenhum conceito médico no momento. Por favor, tente novamente mais tarde.",
                    'intent': 'INTENT_LIST_TERMS',
                    'confidence': 1.0,
                    'source': 'static_intent'
                }
            
            # Filter valid concepts and extract labels, handling null values
            valid_concepts = []
            for concept in concepts:
                if not concept or not isinstance(concept, dict):
                    continue
                    
                # Try to get the label or display_name
                label = concept.get('label') or concept.get('display_name')
                
                # If no label, try to extract from ID/URI
                if not label or not isinstance(label, str):
                    uri = concept.get('id', '')
                    if '#' in uri:
                        # Extract the part after the # (fragment)
                        label = uri.split('#')[-1]
                    elif '/' in uri:
                        # Extract the part after the last /
                        label = uri.split('/')[-1]
                    else:
                        label = uri
                
                # Remove the namespace prefix if it exists
                label = label.replace('https://w3id.org/hmarl-genai/ontology#', '')
                
                # Format the label to be more readable
                label = label.replace('_', ' ').title()
                
                # Remove common terms that may be at the end
                label = label.replace(' Condition', '').replace(' Disease', '')
                
                # Add spaces before uppercase letters in the middle of words

                label = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', label)
                
                # Remove múltiplos espaços
                label = ' '.join(label.split())
                
                if not label:
                    continue
                    
                valid_concepts.append({
                    'label': label.strip(),
                    'uri': concept.get('id', ''),
                    'concept': concept
                })
            
            if not valid_concepts:
                return {
                    'response': "Não encontrei conceitos médicos disponíveis para exibição.",
                    'intent': 'INTENT_LIST_TERMS',
                    'confidence': 1.0,
                    'source': 'api'
                }
            
            # Sort concepts by label (case-insensitive)
            sorted_concepts = sorted(valid_concepts, key=lambda x: x['label'].lower())
            
            # Format response
            response_text = "## Termos Médicos Disponíveis\n\n"
            
            # Group by initial letter to facilitate navigation
            terms_by_letter = {}
            for item in sorted_concepts:
                label = item['label']
                first_letter = label[0].upper() if label else '#'
                
                if first_letter not in terms_by_letter:
                    terms_by_letter[first_letter] = []
                terms_by_letter[first_letter].append(label)
            
            # Add grouped terms by letter
            for letter in sorted(terms_by_letter.keys()):
                response_text += f"### {letter}\n"
                for term in sorted(terms_by_letter[letter]):
                    response_text += f"- {term}\n"
                response_text += "\n"
            
            response_text += ("\n**Dica**: Digite o nome de um termo para obter mais informações sobre ele!")
            
            return {
                'response': response_text,
                'intent': 'INTENT_LIST_TERMS',
                'confidence': 1.0,
                'source': 'static_intent',
                'total_terms': len(sorted_concepts)
            }
            
        except Exception as e:
            self.logger.error(f"Error listing terms: {str(e)}", exc_info=True)
            return {
                'response': "Desculpe, ocorreu um erro ao listar os termos médicos. Por favor, tente novamente mais tarde.",
                'intent': 'INTENT_LIST_TERMS',
                'confidence': 1.0,
                'source': 'error_handler'
            }
    
    def _handle_show_relationships(self, intent_obj: Intent, text: str) -> Dict[str, Any]:
        """
        Handle the intent to show relationships between medical terms.
        
        Args:
            intent_obj: Processed intent object
            text: Original user message
            
        Returns:
            Dictionary with the response containing the relationships
        """
        # If no entities in the intent, try to extract from the text
        if not hasattr(intent_obj, 'entities') or not intent_obj.entities:
            try:
                # Use the NLP processor to extract entities
                _, extracted_entities = self.nlp_processor.process_text(text)
                intent_obj.entities = [e for e in extracted_entities 
                                    if e.entity_type == 'termo_medico']
            except Exception as e:
                self.logger.error(f"Error extracting entities: {str(e)}", exc_info=True)
                intent_obj.entities = []
        
        # If no entities, ask for more information
        if not intent_obj.entities:
            return {
                'response': "Por favor, especifique os termos médicos sobre os quais deseja ver os relacionamentos.\n\nExemplo: 'Mostre os relacionamentos entre hipertensão e diabetes'",
                'intent': 'relacionamentos',
                'confidence': 1.0,
                'source': 'static_intent'
            }
        
        # If only one term, show its relationships
        if len(intent_obj.entities) == 1:
            term = intent_obj.entities[0].value
            return self._show_relationships_for_term(term)
        
        # If more than one term, show relationships between them
        return self._show_relationships_between_terms([e.value for e in intent_obj.entities])
    
    def _show_relationships_for_term(self, term: str) -> Dict[str, Any]:
        """Show relationships for a single term."""
        try:
            # First, try to get the concept directly by term
            concept = self.api_client.get_concept_by_term(term)
            
            # If not found, try to search all concepts and do a case-sensitive search
            if not concept or 'id' not in concept:
                # Try to search all concepts and do a case-sensitive search
                all_concepts = self.api_client.get_concepts()
                matching_concepts = [
                    c for c in all_concepts 
                    if c.get('label') == term or c.get('display_name') == term
                ]
                
                if matching_concepts:
                    concept = matching_concepts[0]
                else:
                    return {
                        'response': f"Não encontrei informações para o termo '{term}'. Por favor, verifique se o termo está correto.",
                        'intent': 'INTENT_RELATIONSHIPS',
                        'confidence': 1.0,
                        'source': 'relationship_lookup'
                    }
            
            # Extract concept information
            concept_id = concept.get('id', '')
            concept_label = concept.get('label', term).strip()
            concept_type = concept.get('type', 'Desconhecido')
            
            # If the label is empty, use the ID as fallback
            if not concept_label and concept_id:
                # Extract the concept name from the ID (last part after # or /)
                concept_label = concept_id.split('#')[-1].split('/')[-1]
                # Remove special characters and capitalize
                concept_label = ' '.join(word.capitalize() for word in concept_label.replace('_', ' ').split())
            
            self.logger.info(f"Find relationships for the concept ID: {concept_id}, Label: '{concept_label}', Type: {concept_type}")
            
            # Get relationships of the concept
            relationships = self.api_client.get_relationships(concept_id)
            
            # If no relationships found, try to search additional information about the concept
            if not relationships:
                try:
                    self.logger.info(f"No relationships found. Searching for complete concept details...")
                    full_concept = self.api_client.get_concept(concept_id)
                    
                    if full_concept:
                        self.logger.info(f"Concept details found. Keys: {full_concept.keys()}")
                        
                        # Update label if empty
                        if not concept_label and 'label' in full_concept and full_concept['label']:
                            concept_label = full_concept['label']
                        
                        # Try to get relationships from different possible keys
                        for rel_key in ['relationships', 'relations', 'related', 'properties']:
                            if rel_key in full_concept and isinstance(full_concept[rel_key], list) and full_concept[rel_key]:
                                relationships = full_concept[rel_key]
                                self.logger.info(f"Found {len(relationships)} relationships in key '{rel_key}'")
                                break
                except Exception as e:
                    self.logger.warning(f"Erro ao buscar conceito completo: {str(e)}")
            
            # If no relationships found, check if it's a generic concept
            if not relationships and ('generic_' in concept_id.lower() or concept.get('type') == 'GenericConcept'):
                return {
                    'response': (
                        f"## Termo não encontrado na ontologia\n\n"
                        f"O termo '{concept_label}' não foi encontrado na ontologia.\n\n"
                        "**Sugestões:**\n"
                        "- Verifique se o termo está escrito corretamente\n"
                        "- Tente usar um termo mais específico\n"
                        "- Use termos em português ou inglês"
                    ),
                    'intent': 'relacionamentos',
                    'confidence': 1.0,
                    'source': 'api'
                }
            
            # If no relationships found, inform that none were found
            if not relationships:
                return {
                    'response': (
                        f"## Sem relacionamentos encontrados\n\n"
                        f"Não foram encontrados relacionamentos para o termo '{concept_label}'.\n\n"
                        "**Possíveis motivos:**\n"
                        "- Este pode ser um conceito terminal na ontologia\n"
                        "- O conceito pode não ter relacionamentos definidos\n"
                        "- Pode ser necessário expandir a ontologia com mais relacionamentos"
                    ),
                    'intent': 'relacionamentos',
                    'confidence': 1.0,
                    'source': 'api',
                    'metadata': {
                        'concept_id': concept_id,
                        'concept_label': concept_label,
                        'concept_type': concept_type,
                        'relationship_count': 0
                    }
                }
            
            # Format response
            response = f"## Relacionamentos para '{concept_label}':\n\n"
            
            # Group relationships by type
            rel_by_type = {}
            for rel in relationships:
                rel_type = rel.get('type', 'Relacionamento')
                target = rel.get('target', 'N/A')
                target_label = rel.get('target_label', target)
                
                if rel_type not in rel_by_type:
                    rel_by_type[rel_type] = []
                rel_by_type[rel_type].append(target_label)
            
            # Add each type of relationship to the response
            for rel_type, targets in rel_by_type.items():
                response += f"**{rel_type}:**\n"
                for target in targets:
                    response += f"- {target}\n"
                response += "\n"
            
            return {
                'response': response,
                'intent': 'relacionamentos',
                'confidence': 1.0,
                'source': 'api',
                'metadata': {
                    'concept_id': concept_id,
                    'concept_label': concept_label,
                    'relationship_count': len(relationships)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error find relationships for {term}: {str(e)}", exc_info=True)
            return {
                'response': f"Ocorreu um erro ao buscar os relacionamentos para '{term}'. Por favor, tente novamente.",
                'intent': 'relacionamentos',
                'confidence': 1.0,
                'source': 'error_handler'
            }
    
    def _show_relationships_between_terms(self, terms: List[str]) -> Dict[str, Any]:
        """Show relationships between multiple terms."""
        if len(terms) < 2:
            return {
                'response': "Por favor, especifique pelo menos dois termos para verificar relacionamentos entre eles.",
                'intent': 'relacionamentos',
                'confidence': 1.0,
                'source': 'static_intent'
            }
            
        try:
            # Find relationships between the terms
            relationships = []
            for i in range(len(terms)):
                for j in range(i + 1, len(terms)):
                    rels = self.api_client.get_relationships_between(terms[i], terms[j])
                    if rels:
                        relationships.extend(rels)
            
            if not relationships:
                return {
                    'response': f"Não encontrei relacionamentos entre os termos: {', '.join(terms)}",
                    'intent': 'relacionamentos',
                    'confidence': 1.0,
                    'source': 'api'
                }
            
            # Format response
            response = f"## Relacionamentos entre os termos:\n\n"
            for rel in relationships:
                response += f"- {rel.get('source')} → {rel.get('type', 'relaciona-se com')} → {rel.get('target')}\n"
            
            return {
                'response': response,
                'intent': 'relacionamentos',
                'confidence': 1.0,
                'source': 'api'
            }
            
        except Exception as e:
            self.logger.error(f"Error find relationships between terms: {str(e)}", exc_info=True)
            return {
                'response': "Ocorreu um erro ao buscar os relacionamentos entre os termos. Por favor, tente novamente.",
                'intent': 'relacionamentos',
                'confidence': 1.0,
                'source': 'error_handler'
            }
        
    def _handle_help_with_intent(self, intent_obj: Intent, text: str):
        """
        Compatibility method for the help handler that receives an Intent object.
        Redirects to the _handle_help method that does not require the intent_obj parameter.
        """
        return self._handle_help(text)

    def _handle_about_ontomed(self, intent_obj: Intent, text: str) -> Dict[str, Any]:
        """
        Responds to questions about what OntoMed is.
        
        Args:
            intent_obj: Intent object containing information about the detected intent.
            text: User message text.
            
        Returns:
            Dictionary with the formatted response.
        """
        self.logger.info("Answering the question about what OntoMed is")
        
        response = {
            'response': "O OntoMed é um assistente virtual especializado em saúde que utiliza "
                      "processamento de linguagem natural (NLP) e uma ontologia médica para fornecer "
                      "informações precisas sobre termos médicos, doenças, tratamentos e conceitos relacionados "
                      "à saúde. Ele foi desenvolvido para ajudar profissionais de saúde, estudantes e "
                      "pacientes a compreenderem melhor a terminologia médica e as relações entre "
                      "diferentes conceitos médicos. O sistema combina técnicas avançadas de NLP com "
                      "uma base de conhecimento médico estruturada para oferecer respostas contextualizadas "
                      "e baseadas em evidências.",
            'confidence': 1.0,
            'metadata': {
                'source': 'static_definition',
                'about': 'ontomed_description'
            }
        }
        
        return response

    def _handle_template_based_intent(self, intent_obj: Intent, text: str, intent_name: str) -> Dict[str, Any]:
        """Process dynamic intents based on templates using LLM for content generation.
        Leverages ontology concepts to enrich the context and improve accuracy.
        
        Args:
            intent_obj: Detected intent object
            text: Original message text
            intent_name: Name of the intent to be processed
            
        Returns:
            Formatted response based on the intent, dynamically generated by the LLM
        """
        self.logger.info(f"Processing dynamic intent: {intent_name}")
        
        # Process the text with NLP to leverage ontology concepts
        doc = self.nlp_processor.nlp(text)
        
        # Extract relevant entities from the text
        entities = intent_obj.entities if hasattr(intent_obj, 'entities') else []
        self.logger.info(f"Extracted entities: {entities}")
        
        # Extract medical terms or other relevant terms
        medical_terms = []
        concept_info = []
        
        # First, extract medical terms from the entities already identified
        for entity in entities:
            if entity.entity_type == "termo_medico":
                medical_terms.append(entity.value)
        
        # Then, extract medical terms identified by EntityRuler with ontology concepts
        for ent in doc.ents:
            if ent.label_ == "termo_medico":
                term = ent.text
                if term not in medical_terms:  # Avoid duplicates
                    medical_terms.append(term)
                
                # Try to get the concept ID from the ontology
                concept_id = None
                if hasattr(self.nlp_processor, 'ontology_concept_manager') and self.nlp_processor.ontology_concept_manager:
                    concept_id = self.nlp_processor.ontology_concept_manager.get_concept_id(term)
                
                # If we have a concept ID, fetch detailed information
                if concept_id:
                    try:
                        concept_data = self.api_client.get_concept(concept_id)
                        if concept_data:
                            # Add to cache for future use
                            self._concept_cache[term.lower()] = concept_data
                            
                            # Extract relevant concept information
                            concept_info.append({
                                'term': term,
                                'id': concept_id,
                                'label': concept_data.get('label', term),
                                'description': concept_data.get('description', ''),
                                'synonyms': concept_data.get('synonyms', []),
                                'relationships': concept_data.get('relationships', [])
                            })
                    except Exception as e:
                        self.logger.warning(f"Error getting concept information {concept_id}: {str(e)}")
        
        self.logger.info(f"Medical terms identified: {medical_terms}")
        self.logger.info(f"Concept information obtained: {len(concept_info)}")
        
        # Extract the primary term for use in generation
        primary_term = medical_terms[0] if medical_terms else text
        self.logger.info(f"Primary term for intent {intent_name}: {primary_term}")
        
        # Build ontology context information to enrich the prompt
        ontology_context = ""
        if concept_info:
            ontology_context = "\nInformações da ontologia médica sobre os termos identificados:\n"
            for info in concept_info:
                ontology_context += f"\nTermo: {info['label']}\n"
                if info.get('description'):
                    ontology_context += f"Descrição: {info['description']}\n"
                if info.get('synonyms'):
                    ontology_context += f"Sinônimos: {', '.join(info['synonyms'][:5])}\n"
                if info.get('relationships'):
                    rel_examples = [f"{r.get('type', '')}: {r.get('target_label', '')}" 
                                   for r in info['relationships'][:3] if r.get('type') and r.get('target_label')]
                    if rel_examples:
                        ontology_context += f"Relacionamentos principais: {', '.join(rel_examples)}\n"
        
        # Build generic prompt to the LLM generate a response based on the intent and terms
        prompt = f"""
        Você é um assistente médico especializado em fornecer informações precisas e úteis.
        
        O usuário está solicitando informações relacionadas à intenção: {intent_name}
        
        Consulta original do usuário: "{text}"
        
        Termo principal identificado: "{primary_term}"
        
        Outros termos médicos identificados: {', '.join([t for t in medical_terms if t != primary_term]) if len(medical_terms) > 1 else 'nenhum adicional'}
        {ontology_context}
        
        Por favor, gere uma resposta completa e informativa que atenda à intenção do usuário.
        Analise o nome da intenção e os termos identificados para determinar o tipo de resposta mais adequado.
        Utilize as informações da ontologia médica fornecidas para enriquecer sua resposta com conhecimento específico.
        
        Sua resposta deve ser:
        1. Relevante para a intenção identificada ({intent_name})
        2. Focada nos termos médicos identificados
        3. Estruturada de forma clara e informativa
        4. Baseada em conhecimento médico atual e nas informações da ontologia
        5. Precisa e cientificamente correta
        """
        
        try:
            # Generate response using the LLM
            self.logger.info(f"Generating response with LLM for intent: {intent_name}")
            response_content = self.llm.generate_text(prompt)
            
            # Format and return the response
            response = {
                'response': response_content,
                'intent': intent_name,
                'confidence': intent_obj.confidence,
                'source': 'llm_dynamic',
                'concepts': [info['id'] for info in concept_info] if concept_info else []
            }
            return response
            
        except Exception as e:
            self.logger.error(f"Error generating response for {intent_name} with LLM: {str(e)}")
            return self._generate_fallback_response(intent_obj, text)
    
    def _generate_fallback_response(self, intent_obj: Intent, text: str) -> Dict[str, Any]:
        """
        Generate a fallback response when unable to identify the intent.
        
        Args:
            intent_obj: Detected intent object
            text: Original message text
            
        Returns:
            Dictionary with the response and metadata
        """
        # If the LLM is available, try using it
        if hasattr(self, 'llm') and self.llm is not None:
            try:
                # Add context to the prompt to improve the response
                context = st.session_state.chat_context
                mentioned_concepts = ", ".join(context['mentioned_concepts'][-3:]) if context['mentioned_concepts'] else "nenhum"
                
                prompt = f"""
                Você é um assistente médico especializado em ontologias médicas.
                O usuário está interagindo com um sistema que permite buscar conceitos médicos, explicar termos e mostrar relacionamentos.
                
                Conceitos mencionados recentemente: {mentioned_concepts}
                
                Mensagem do usuário: "{text}"
                
                Responda de forma útil, concisa e educada. Se não souber a resposta, sugira usar um dos comandos disponíveis.
                """
                
                response = self.llm.generate_text(prompt)
                
                return {
                    'response': response,
                    'intent': 'outro',
                    'confidence': 0.5,
                    'source': 'llm_fallback'
                }
            except Exception as e:
                self.logger.warning(f"Error using LLM for fallback response: {str(e)}")
                # Continue to static fallback in case of error
        
        # If the LLM is not available or an error occurs, use static response
        suggestions = [
            "Você pode tentar: 'O que é doença?', 'Liste os sintomas de gripe' ou 'Mostre os relacionamentos de hipertensão'.",
            "Tente reformular sua pergunta ou digite 'ajuda' para ver os comandos disponíveis.",
            "Se estiver procurando informações sobre um termo médico, tente 'O que é [termo]?'"
        ]
        import random
        suggestion = random.choice(suggestions)
        
        return {
            'response': f"Desculpe, não consegui entender sua solicitação. {suggestion}",
            'intent': 'outro',
            'confidence': 0.0,
            'source': 'static_fallback'
        }
