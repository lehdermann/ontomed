"""
Ontology Concept Manager for integration with spaCy.
"""

import logging
import time
import traceback
from typing import List, Dict, Any, Optional
import spacy
from spacy.pipeline import EntityRuler
from spacy.tokens import Doc
from spacy.language import Language

logger = logging.getLogger(__name__)

class OntologyConceptManager:
    """
    Manages the integration of ontology concepts with spaCy.
    Adds ontology concepts as patterns for the EntityRuler.
    """
    
    def __init__(self, nlp, api_client, entity_ruler=None):
        """
        Initializes the ontology concept manager.
        
        Args:
            nlp: Loaded spaCy model
            api_client: API client to access the ontology
            entity_ruler: Existing EntityRuler to add patterns (optional)
        """
        self.nlp = nlp
        self.api_client = api_client
        self.entity_ruler = entity_ruler
        self.concept_ruler = None
        self.concept_ruler_initialized = False
        self.concept_patterns = []
        self.concept_id_map = {}  # Maps pattern text to concept ID
        
    def initialize(self) -> bool:
        """
        Initializes the ontology concept manager.
        
        Returns:
            bool: True if initialized successfully, False otherwise
        """
        try:
            # Get all concepts from the ontology
            concepts = self._get_all_ontology_concepts()
            
            if not concepts:
                logger.warning("No concepts obtained from the ontology")
                return False
                
            # Create patterns for the EntityRuler
            self._create_concept_patterns(concepts)
            
            # Use the provided entity_ruler or create a new one if not provided
            if self.entity_ruler is not None:
                self.concept_ruler = self.entity_ruler
                logger.info("Using provided EntityRuler")
            else:
                # Add the EntityRuler component to the pipeline
                if "concept_ruler" in self.nlp.pipe_names:
                    self.nlp.remove_pipe("concept_ruler")
                    logger.info("Removed existing concept_ruler component for re-creation")
                    
                # Create a new EntityRuler with optimized configuration
                # Set overwrite_ents=True to ensure that the concept_ruler patterns have priority
                config = {
                    "overwrite_ents": True,
                    "phrase_matcher_attr": "LOWER"
                }
                
                # Add after the ner component to process after default entity recognition
                if "ner" in self.nlp.pipe_names:
                    self.concept_ruler = self.nlp.add_pipe("entity_ruler", after="ner", config=config, name="concept_ruler")
                    logger.info("Added concept_ruler after the ner component")
                else:
                    self.concept_ruler = self.nlp.add_pipe("entity_ruler", name="concept_ruler", config=config)
                    logger.info("Added concept_ruler to the pipeline (ner not found)")
            
            # Add patterns to the EntityRuler
            self.concept_ruler.add_patterns(self.concept_patterns)
            
            # Mark as initialized
            self.concept_ruler_initialized = True
            
            logger.info(f"Ontology Concept Manager initialized with {len(self.concept_patterns)} patterns")
            return True
        except Exception as e:
            logger.error(f"Error initializing ontology concept manager: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    # Cache in memory for concepts
    _concepts_cache = None
    _last_fetch_time = 0
    CACHE_TTL = 3600  # 1 hour in seconds

    def _get_all_ontology_concepts(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Gets all concepts from the ontology with caching.
        
        Args:
            force_refresh: If True, ignores the cache and fetches from the API
            
        Returns:
            List[Dict[str, Any]]: List of concepts from the ontology
        """
        current_time = time.time()
        
        # Returns from cache if not forced refresh and cache is recent
        if not force_refresh and self._concepts_cache is not None:
            time_since_last_fetch = current_time - self._last_fetch_time
            if time_since_last_fetch < self.CACHE_TTL:
                logger.debug(f"Returning concepts from cache (last update {time_since_last_fetch:.1f}s ago)")
                return self._concepts_cache
            else:
                logger.debug(f"Cache expired (last update {time_since_last_fetch:.1f}s ago, TTL: {self.CACHE_TTL}s)")
            
        try:
            logger.info("Fetching concepts from API...")
            concepts = self.api_client.get_concepts()
            
            if not concepts:
                logger.warning("API returned empty list of concepts")
                return self._concepts_cache or []  # Maintains previous cache if available
            
            # Updates the cache
            self._concepts_cache = concepts
            self._last_fetch_time = current_time
            
            logger.info(f"Cache of concepts updated with {len(concepts)} items (next update in {self.CACHE_TTL}s)")
            logger.debug(f"Timestamp of last update: {current_time}")
            
            # Verifies the format of the concepts
            if concepts and isinstance(concepts, list):
                logger.info(f"Type of first item: {type(concepts[0])}")
                if isinstance(concepts[0], dict):
                    logger.debug(f"Keys available in the first concept: {concepts[0].keys()}")
                    logger.debug(f"Example of the first concept: {concepts[0]}")
                else:
                    logger.warning(f"The concepts are not dictionaries! Type: {type(concepts[0])}")
            
            return concepts
            
        except Exception as e:
            logger.error(f"Error getting concepts from the ontology: {str(e)}")
            if self._concepts_cache is not None:
                logger.warning("Using cache due to API error")
                return self._concepts_cache
            return []
    
    def _create_concept_patterns(self, concepts: List[Dict[str, Any]]) -> None:
        """
        Creates patterns for the EntityRuler from the concepts of the ontology.
        
        Args:
            concepts: List of concepts from the ontology
        """
        self.concept_patterns = []
        self.concept_id_map = {}
        
        # Statistics counter
        total_terms = 0
        total_variations = 0
        total_synonyms = 0
        
        for i, concept in enumerate(concepts):
            # Extract ID and label from the concept
            concept_id = concept.get('id')
            label = concept.get('label') or concept.get('display_name') or concept.get('name')
            
            # If no label, try to extract from ID
            original_label = label
            if not label and concept_id:
                if "#" in concept_id:
                    label = concept_id.split("#")[-1]
                elif "/" in concept_id:
                    label = concept_id.split("/")[-1]
                else:
                    label = concept_id
                logger.debug(f"Concept {i}: Extracting label '{label}' from ID '{concept_id}'")
            
            if not concept_id or not label:
                continue
                
            # Count original terms
            total_terms += 1
            
            # Create pattern for the original term
            pattern = {"label": "termo_medico", "pattern": label, "id": concept_id}
            self.concept_patterns.append(pattern)
            self.concept_id_map[label.lower()] = concept_id
            logger.debug(f"Added original term pattern: {label} -> {concept_id}")
            
            # Create term variations (replace _ with space and vice versa)
            if '_' in label:
                variant = label.replace('_', ' ')
                if variant.lower() not in self.concept_id_map:  # Avoid duplicates
                    pattern = {"label": "termo_medico", "pattern": variant, "id": concept_id}
                    self.concept_patterns.append(pattern)
                    self.concept_id_map[variant.lower()] = concept_id
                    total_variations += 1
                    logger.debug(f"Added space variation: {variant} -> {concept_id}")
                    
            if ' ' in label:
                variant = label.replace(' ', '_')
                if variant.lower() not in self.concept_id_map:  # Avoid duplicates
                    pattern = {"label": "termo_medico", "pattern": variant, "id": concept_id}
                    self.concept_patterns.append(pattern)
                    self.concept_id_map[variant.lower()] = concept_id
                    total_variations += 1
                    logger.debug(f"Added underscore variation: {variant} -> {concept_id}")
            
            # Add synonyms if available
            synonyms = concept.get('synonyms', [])
            if isinstance(synonyms, list):
                for synonym in synonyms:
                    if not synonym:
                        continue
                        
                    # Normalize the synonym
                    synonym = synonym.strip()
                    if not synonym or synonym.lower() in self.concept_id_map:
                        continue
                        
                    # Add the original synonym
                    pattern = {"label": "termo_medico", "pattern": synonym, "id": concept_id}
                    self.concept_patterns.append(pattern)
                    self.concept_id_map[synonym.lower()] = concept_id
                    total_synonyms += 1
                    logger.debug(f"Added synonym: {synonym} -> {concept_id}")
                    
                    # Create variations for the synonyms
                    if '_' in synonym or ' ' in synonym:
                        # Space variation
                        variant = synonym.replace('_', ' ').replace('  ', ' ').strip()
                        if variant.lower() not in self.concept_id_map:
                            pattern = {"label": "termo_medico", "pattern": variant, "id": concept_id}
                            self.concept_patterns.append(pattern)
                            self.concept_id_map[variant.lower()] = concept_id
                            total_variations += 1
                            logger.debug(f"Added space variation of synonym: {variant} -> {concept_id}")
                        
                        # Underscore variation
                        variant = synonym.replace(' ', '_').replace('__', '_').strip('_')
                        if variant.lower() not in self.concept_id_map:
                            pattern = {"label": "termo_medico", "pattern": variant, "id": concept_id}
                            self.concept_patterns.append(pattern)
                            self.concept_id_map[variant.lower()] = concept_id
                            total_variations += 1
                            logger.debug(f"Added underscore variation of synonym: {variant} -> {concept_id}")
        
        logger.info(f"Created {len(self.concept_patterns)} patterns from {total_terms} original terms "
                   f"({total_variations} variations, {total_synonyms} synonyms)")
        logger.debug(f"Example of loaded terms: {list(self.concept_id_map.keys())[:10]}...")
        
        if not self.concept_patterns and concepts:
            logger.error("ERROR: No patterns were created from the ontology concepts!")
            logger.error(f"Example of concept: {concepts[0]}")
            logger.error(f"Available keys: {concepts[0].keys() if isinstance(concepts[0], dict) else 'Not a dictionary'}")
        elif self.concept_patterns:
            logger.debug(f"Examples of created patterns: {self.concept_patterns[:3]}")
    
    def refresh(self) -> bool:
        """
        Updates the ontology concepts in the EntityRuler.
        
        Returns:
            bool: True if updated successfully, False otherwise
        """
        try:
            logger.info("Starting update of ontology concepts...")
            
            # If using a shared EntityRuler, we only update the patterns
            if self.entity_ruler is not None and self.concept_ruler is not None:
                logger.info("Updating patterns in shared EntityRuler...")
                # Clear existing patterns
                self.concept_ruler.patterns = []
                
                # Get updated concepts
                concepts = self._get_all_ontology_concepts(force_refresh=True)
                if not concepts:
                    logger.error("Failed to retrieve updated concepts from the ontology")
                    return False
                
                # Recreate patterns
                self._create_concept_patterns(concepts)
                
                # Add new patterns
                if self.concept_patterns:
                    self.concept_ruler.add_patterns(self.concept_patterns)
                    logger.info(f"Updated {len(self.concept_patterns)} patterns in shared EntityRuler")
                    return True
                else:
                    logger.error("No patterns were created from the ontology concepts")
                    return False
            else:
                # If not using a shared EntityRuler, recreate the component
                logger.info("Recreating the concept_ruler component...")
                if "concept_ruler" in self.nlp.pipe_names:
                    self.nlp.remove_pipe("concept_ruler")
                
                # Reinitialize
                return self.initialize()
        except Exception as e:
            logger.error(f"Error updating ontology concepts: {str(e)}", exc_info=True)
            return False
    
    def get_concept_id(self, term: str) -> Optional[str]:
        """
        Gets the ID of the concept for a term.
        
        Args:
            term: Term to be searched
            
        Returns:
            Optional[str]: ID of the concept or None if not found
        """
        return self.concept_id_map.get(term.lower())
