"""
Main NLP Processor principal de linguagem natural para o OntoMed.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
import spacy
from spacy.tokens import Doc

from .models import Entity, Intent
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class ProcessedMessage:
    """Class to represent processed messages, compatible with the legacy interface."""
    text: str
    intent: str = ""
    entities: List[Entity] = None
    confidence: float = 0.0
    context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.entities is None:
            self.entities = []
        if self.context is None:
            self.context = {}

from .entity_manager import EntityManager
from .dependency_matcher import DependencyMatcherManager
from .scoring_system import IntentScoringSystem
from .ontology_concept_manager import OntologyConceptManager

logger = logging.getLogger(__name__)


class NLPProcessor:
    """
    Main NLP Processor for the OntoMed.
    Orchestrates different components for text processing,
    entity recognition and intent detection.
    """
    
    def __init__(self, model_name: str = "pt_core_news_lg", api_client=None, scoring_system: IntentScoringSystem = None):
        """
        Initializes the NLP Processor.
        
        Args:
            model_name: Name of the spaCy model to be loaded
            api_client: API client to access the ontology
            scoring_system: Shared scoring system instance (optional)
        """
        self.model_name = model_name
        self.nlp = None
        self.entity_manager = None
        self.dependency_matcher = None
        self.scoring_system = scoring_system or IntentScoringSystem()
        self.ontology_concept_manager = None
        self.api_client = api_client
        self.conversation_context = {}
        
    def initialize(self) -> bool:
        """
        Initializes the NLP Processor and its components.
        
        Returns:
            bool: True if initialized successfully, False otherwise
        """
        # Load spaCy model
        if not self._load_spacy_model():
            return False
        
        # Initialize scoring_system if not provided
        if self.scoring_system is None:
            from .scoring_system import IntentScoringSystem
            self.scoring_system = IntentScoringSystem(self.nlp)
            logger.warning("No scoring_system provided, created a new instance with spaCy model")
        elif hasattr(self.scoring_system, 'nlp') and self.scoring_system.nlp is None:
            # If the scoring_system already exists but doesn't have the spaCy model, update it
            self.scoring_system.nlp = self.nlp
            logger.info("Updated existing scoring_system with spaCy model")
            
            # Call _preprocess_static_keywords to process static keywords with the spaCy model
            if hasattr(self.scoring_system, '_preprocess_static_keywords'):
                logger.info("Calling _preprocess_static_keywords to enrich static keywords")
                self.scoring_system._preprocess_static_keywords()
            
        # Save existing entity-intent mapping (if any)
        existing_entity_intent_map = {}
        existing_intent_keywords = {}
        
        # Preserve entity-intent mapping
        if hasattr(self.scoring_system, 'entity_intent_map'):
            existing_entity_intent_map = self.scoring_system.entity_intent_map.copy()
            logger.info(f"Preserving existing entity-intent mapping: {existing_entity_intent_map}")
        
        # Preserve intent keywords
        if hasattr(self.scoring_system, 'intent_keywords'):
            existing_intent_keywords = self.scoring_system.intent_keywords.copy()
            logger.info(f"Preserving existing intent keywords: {existing_intent_keywords}")
        
        # Initialize EntityManager
        self.entity_manager = EntityManager(self.nlp)
        
        # Get the custom entity_ruler that we added in _load_spacy_model
        entity_ruler = None
        if "medical_terms_ruler" in self.nlp.pipe_names:
            entity_ruler = self.nlp.get_pipe("medical_terms_ruler")
            logger.info("Using custom entity_ruler for ontology concepts")
        
        # Initialize the ontology concept manager if api_client is available
        if self.api_client:
            # Initialize OntologyConceptManager with the custom entity_ruler
            self.ontology_concept_manager = OntologyConceptManager(
                self.nlp, 
                self.api_client,
                entity_ruler=entity_ruler
            )
            
            # Initialize EntityManager with the same entity_ruler for consistency
            if entity_ruler:
                self.entity_manager.entity_ruler = entity_ruler
                self.entity_manager.entity_ruler_initialized = True
            
            if not self.ontology_concept_manager.initialize():
                logger.warning("Failed to initialize ontology concept manager")
            else:
                logger.info("Ontology concept manager initialized successfully")
        
        # Initialize Dependency Matcher
        self.dependency_matcher = DependencyMatcherManager(self.nlp)
        
        # Restore entity-intent mapping
        if existing_entity_intent_map:
            # Update the mapping with existing values
            self.scoring_system.entity_intent_map.update(existing_entity_intent_map)
            logger.info(f"Entity-intent mapping restored after initialization: {self.scoring_system.entity_intent_map}")
        
        # Restore intent keywords
        if existing_intent_keywords:
            # Update the keywords with existing values
            self.scoring_system.intent_keywords.update(existing_intent_keywords)
            logger.info(f"Intent keywords restored after initialization: {self.scoring_system.intent_keywords}")
            
        # Log intent keywords for all intents
        logger.info(f"Intent keywords for all intents: {self.scoring_system.intent_keywords}")
        logger.info(f"Entity-intent mapping after initialization: {self.scoring_system.entity_intent_map}")
        
        # Initialize Dependency Matcher
        if not self.dependency_matcher.initialize():
            logger.warning("Failed to initialize Dependency Matcher")
            
        logger.info("NLPProcessor initialized successfully")
        return True
    
    def _load_spacy_model(self) -> bool:
        """
        Load the spaCy model.
        
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        # Check if the model is already loaded
        if hasattr(self, 'nlp') and self.nlp is not None:
            logger.debug(f"spaCy model '{self.model_name}' is already loaded")
            return True
            
        try:
            # Load spaCy model
            logger.info(f"Loading spaCy model '{self.model_name}'...")
            
            # Load the model without the NER component
            self.nlp = spacy.load(self.model_name, disable=["ner"])
            
            # Add an EntityRuler with basic patterns at the beginning of the pipeline
            if "entity_ruler" not in self.nlp.pipe_names:
                # Configure to overwrite existing entities and use LOWER for matching
                ruler = self.nlp.add_pipe(
                    "entity_ruler",
                    name="medical_terms_ruler",
                    first=True,  # Add at the beginning of the pipeline
                    config={"overwrite_ents": True, "phrase_matcher_attr": "LOWER"}
                )
                
                # Add some basic patterns to avoid the warning
                basic_patterns = [
                    {"label": "MEDICAL_TERM", "pattern": "doença"},
                    {"label": "MEDICAL_TERM", "pattern": "sintoma"},
                    {"label": "MEDICAL_TERM", "pattern": "diagnóstico"},
                    {"label": "MEDICAL_TERM", "pattern": "tratamento"}
                ]
                ruler.add_patterns(basic_patterns)
                logger.info("EntityRuler added with basic patterns at the beginning of the pipeline")
            
            logger.info(f"spaCy model '{self.model_name}' loaded successfully")
            
            # Register custom extensions for entities
            if not Doc.has_extension("concept_id"):
                Doc.set_extension("concept_id", default=None)
                
            return True
        except ImportError:
            logger.warning("spaCy is not installed. Using only rules for natural language processing.")
            return False
        except Exception as e:
            logger.error(f"Error loading spaCy model '{self.model_name}': {str(e)}")
            return False
    
    def process_text(self, text: str, context: Dict[str, Any] = None) -> Tuple[Intent, List[Entity]]:
        """
        Process the text to identify intents and entities.
        
        Args:
            text: Text to be processed
            context: Conversation context (optional)
            
        Returns:
            Tuple[Intent, List[Entity]]: Tuple with intent and entities
        """
        try:
            logger.info(f"Processing text: '{text}'")
            logger.info(f"Context: {context}")
            
            if not self.initialize():
                logger.error("Failed to initialize NLP processor")
                return Intent(name="outro", confidence=0.3, entities=[]), []
            
            # Check if the text contains keywords related to literature summaries
            literature_keywords = ["literature", "summary", "resumo", "literatura", "artigos", "papers"]
            found_keywords = [kw for kw in literature_keywords if kw.lower() in text.lower()]
            if found_keywords:
                logger.info(f"Literature keywords found: {found_keywords}")
            
            # Process the text with spaCy
            doc = self.nlp(text)
            
            # Extract entities identified by the Entity Ruler
            entity_matches = [(ent.text, ent.label_) for ent in doc.ents]
            logger.info(f"Entities identified by the Entity Ruler: {entity_matches}")
            
            # Check if there are intent entities (INTENT_*)
            intent_entities = [(ent.text, ent.label_) for ent in doc.ents if ent.label_.startswith("INTENT_")]
            logger.info(f"Intent entities (INTENT_*): {intent_entities}")
            
            # Check if there are entities related to scientific literature summaries
            literature_entities = [(ent.text, ent.label_) for ent in doc.ents 
                                  if ent.label_ == "INTENT_SCIENTIFIC_LITERATURE_SUMMARY" or 
                                     "literature" in ent.text.lower() or 
                                     "summary" in ent.text.lower()]
            logger.info(f"Entities related to scientific literature summaries: {literature_entities}")
            
            # Extract dependency patterns
            dependency_matches = self.dependency_matcher.match(doc)
            logger.info(f"Dependency patterns found: {dependency_matches}")
            
            # Check entity-intent mapping
            if hasattr(self.scoring_system, 'entity_intent_map'):
                logger.info(f"Entity-intent mapping: {self.scoring_system.entity_intent_map}")
                
                # Check dynamic intent mappings
                # Search for entity name patterns that may have variations
                intent_prefixes = ["CREATE_", "GENERATE_", "ANALYZE_", "EXPLAIN_"]
                
                # Identify pairs of entities that may be variations of each other
                entity_variations = {}
                for entity in self.scoring_system.entity_intent_map.keys():
                    if entity.startswith("INTENT_"):
                        base_name = entity[7:]  # Remove "INTENT_"
                        
                        # Check if the name contains any of the known prefixes
                        for prefix in intent_prefixes:
                            if prefix in base_name:
                                # Create a variation without the prefix
                                simplified_name = base_name.replace(prefix, "")
                                simplified_entity = f"INTENT_{simplified_name}"
                                
                                # Register the variation
                                if entity not in entity_variations:
                                    entity_variations[entity] = []
                                entity_variations[entity].append(simplified_entity)
                                
                                # Register the inverse relationship as well
                                if simplified_entity not in entity_variations:
                                    entity_variations[simplified_entity] = []
                                entity_variations[simplified_entity].append(entity)
                
                # Ensure that all variations map to the same intent
                for entity, variations in entity_variations.items():
                    if entity in self.scoring_system.entity_intent_map:
                        mapped_intent = self.scoring_system.entity_intent_map[entity]
                        logger.info(f"Entity {entity} is mapped to: {mapped_intent}")
                        
                        # Map all variations to the same intent
                        for var_entity in variations:
                            if var_entity not in self.scoring_system.entity_intent_map:
                                self.scoring_system.entity_intent_map[var_entity] = mapped_intent
                                logger.info(f"Adding alternative mapping: {var_entity} -> {mapped_intent}")
            
            # Calculate scores for different intents
            intent_scores = self.scoring_system.score_intents(
                text, doc, entity_matches, dependency_matches, self.conversation_context
            )
            logger.info(f"Intent scores calculated: {intent_scores}")
            
            # Extract relevant entities before identifying the intent
            entities = self.entity_manager.extract_entities(doc, text)
            
            # Identify the intent with the highest score
            if intent_scores:
                intent = self.scoring_system.get_best_intent(intent_scores, entities)
                logger.info(f"Intent with highest score: {intent.name} (confidence: {intent.confidence:.2f})")
            else:
                intent = Intent(name="outro", confidence=0.3, entities=[])
                logger.info(f"No scores calculated, using default intent: {intent.name}")
            
            # Extract additional specific entities
            # (general entities were already extracted before intent identification)
            
            # Extract entities specific to the intent
            intent_specific_entities = self.entity_manager.extract_entities_for_intent(
                text, doc, intent.name
            )
            
            # Combine and remove duplicates
            all_entities = entities + intent_specific_entities
            unique_entities = self.entity_manager.remove_duplicate_entities(all_entities)
            
            # Apply special cases
            final_intent = self.scoring_system.apply_special_cases(text, intent)
            final_intent.entities = unique_entities
            
            # Update conversation context
            self.conversation_context["previous_intent"] = final_intent.name
            self.conversation_context["previous_entities"] = [e.value for e in unique_entities]
            
            logger.info(f"Intent identified: {final_intent.name} (confidence: {final_intent.confidence:.2f})")
            logger.info(f"Extracted entities: {[str(e) for e in unique_entities]}")
            
            return final_intent, unique_entities
            
        except Exception as e:
            logger.error(f"Error processing text: {str(e)}")
            return Intent(name="outro", confidence=0.3, entities=[]), []
    
    def update_entity_intent_mapping(self, entity_type: str, intent_name: str) -> bool:
        """
        Updates the entity-intent mapping in the NLP system.
        
        Args:
            entity_type: Entity type (e.g., INTENT_LISTAR_TERMOS)
            intent_name: Intent name (e.g., listar_termos)
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        try:
            # Check if the processor was initialized
            if self.scoring_system is None:
                if not self.initialize():
                    logger.warning("Processor not initialized to update entity-intent mapping")
                    return False
            
            # Normalize the entity name to ensure consistency
            # Remove prefixes like 'create_', 'generate_', etc. for normalization
            normalized_intent = intent_name
            
            # Generate variations of the entity name to ensure compatibility
            entity_variations = [entity_type]
            
            # Extract the main part of the entity name (after INTENT_)
            if entity_type.startswith("INTENT_"):
                base_name = entity_type[7:]  # Remove "INTENT_"
                
                # Check if the name contains words like CREATE, GENERATE, etc.
                prefixes = ["CREATE_", "GENERATE_", "ANALYZE_", "EXPLAIN_"]
                for prefix in prefixes:
                    if prefix in base_name:
                        # Create a variation without the prefix
                        simplified_name = base_name.replace(prefix, "")
                        entity_variations.append(f"INTENT_{simplified_name}")
                        logger.info(f"Created entity variation: INTENT_{simplified_name}")
            
            # Update the mapping in IntentScoringSystem for all variations
            if hasattr(self.scoring_system, 'entity_intent_map'):
                for entity_var in entity_variations:
                    self.scoring_system.entity_intent_map[entity_var] = normalized_intent
                    logger.info(f"Updated entity-intent mapping: {entity_var} -> {normalized_intent}")
                return True
            else:
                logger.warning(f"Scoring system does not have entity-intent mapping")
                return False
                
        except Exception as e:
            logger.error(f"Error updating entity-intent mapping: {str(e)}")
            return False
    
    def refresh_nlp_components(self) -> bool:
        """
        Updates the NLP components.
        
        Returns:
            bool: True if updated successfully, False otherwise
        """
        try:
            # Reinitialize the Entity Ruler
            if self.entity_manager:
                self.entity_manager.initialize_entity_ruler()
                
            # Reinitialize the Dependency Matcher
            if self.dependency_matcher:
                self.dependency_matcher.initialize_matchers()
                
            # Update the ontology concept manager
            if self.ontology_concept_manager:
                self.ontology_concept_manager.refresh()
                
            logger.info("NLP components updated successfully")
            return True
        except Exception as e:
            logger.error(f"Error updating NLP components: {str(e)}")
            return False
    
    def normalize_medical_term(self, text: str) -> str:
        """
        Normalizes medical terms to improve recognition.
        
        Args:
            text: Text to be normalized
            
        Returns:
            str: Normalized text
        """
        # Convert to lowercase
        normalized = text.lower()
        
        # Remove accents (optional, depending on the spaCy model)
        # normalized = unidecode(normalized)
        
        # Remove special characters
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        
        # Replace multiple spaces with a single space
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized.strip()
    
    def get_conversation_context(self) -> Dict[str, Any]:
        """
        Returns the current conversation context.
        
        Returns:
            Dict[str, Any]: Conversation context
        """
        return self.conversation_context
    
    def reset_conversation_context(self):
        """
        Resets the conversation context.
        """
        self.conversation_context = {}
