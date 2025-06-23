"""
Entity management and Entity Ruler for the OntoMed.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
import spacy
from spacy.pipeline import EntityRuler

from .models import Entity, EntityPattern

logger = logging.getLogger(__name__)


class EntityManager:
    """
    Entity management and Entity Ruler for the OntoMed.
    """
    
    def __init__(self, nlp):
        """
        Initialize the entity manager.
        
        Args:
            nlp: spaCy loaded model
        """
        self.nlp = nlp
        self.entity_ruler = None
        self.entity_ruler_initialized = False
        self.non_medical_terms = [
            "conceito", "termo", "definição", "significado", 
            "o que", "como", "quando", "onde", "por que", "qual", "quais",
            "relacionamento", "relacionamentos", "relação", "relações", "entre", "com",
            "buscar", "busca", "busque", "procurar", "procure", "encontrar", "encontre",
            "listar", "liste", "mostrar", "mostre", "exibir", "exiba",
            "explicar", "explique", "definir", "defina", "descrever", "descreva",
            "ajuda", "ajudar", "ajude", "socorro", "help", "auxílio",
            "capacidades", "funcionalidades", "ações", "recursos", "habilidades",
            "plano", "cuidados", "cuidado", "tratamento", "tratamentos"
        ]
    
    def initialize_entity_ruler(self) -> bool:
        """
        Initialize the Entity Ruler with patterns for entity recognition.
        
        Returns:
            bool: True if initialized successfully, False otherwise
        """
        if not self.nlp:
            logger.warning("spaCy model not initialized for Entity Ruler")
            return False
            
        try:
            # Create initial patterns
            patterns = self._create_initial_patterns()
            
            # Convert to the format expected by EntityRuler using the to_dict() method
            ruler_patterns = [pattern.to_dict() for pattern in patterns]
            
            # Add the EntityRuler component to the pipeline
            if "entity_ruler" in self.nlp.pipe_names:
                self.entity_ruler = self.nlp.get_pipe("entity_ruler")
            else:
                self.entity_ruler = self.nlp.add_pipe("entity_ruler", before="ner")
            
            # Add patterns to EntityRuler
            self.entity_ruler.add_patterns(ruler_patterns)
            # Mark as initialized
            self.entity_ruler_initialized = True
            
            logger.info(f"Entity Ruler initialized with {len(ruler_patterns)} patterns")
            return True
        except Exception as e:
            logger.error(f"Error initializing Entity Ruler: {str(e)}")
            return False
            
    def add_patterns_to_ruler(self, patterns: List[Any]) -> bool:
        """
        Add new patterns to the existing Entity Ruler.
        
        Args:
            patterns: List of patterns that can be dictionaries or EntityPattern objects
                      [{"label": "LABEL", "pattern": "pattern", "id": "id"}] or
                      [EntityPattern(label="LABEL", pattern="pattern")]
        
        Returns:
            bool: True if added successfully, False otherwise
        """
        if not self.nlp:
            logger.warning("spaCy model not initialized to add patterns")
            return False
            
        if not self.entity_ruler:
            logger.warning("Entity Ruler not initialized")
            if not self.initialize_entity_ruler():
                return False
                
        try:
            # Convert and validate patterns
            valid_patterns = []
            
            for pattern in patterns:
                # Check if it's an EntityPattern object
                if hasattr(pattern, 'to_dict'):
                    valid_patterns.append(pattern.to_dict())
                    continue
                    
                # If it's a dictionary, validate fields
                if isinstance(pattern, dict):
                    if "label" not in pattern or "pattern" not in pattern:
                        logger.warning(f"Invalid pattern ignored: {pattern}")
                        continue
                        
                    # Add ID if not exists
                    if "id" not in pattern:
                        pattern["id"] = f"{pattern['label']}_{len(valid_patterns)}"
                        
                    valid_patterns.append(pattern)
                else:
                    logger.warning(f"Unsupported pattern type: {type(pattern)}")
                
            if not valid_patterns:
                logger.warning("No valid patterns to add")
                return False
                
            # Add patterns to EntityRuler
            logger.info(f"Details of patterns being added:")
            for i, pattern in enumerate(valid_patterns):
                logger.info(f"Pattern {i+1}: Label={pattern.get('label', 'N/A')}, Pattern='{pattern.get('pattern', 'N/A')}', ID={pattern.get('id', 'N/A')}")
            
            self.entity_ruler.add_patterns(valid_patterns)
            logger.info(f"Added {len(valid_patterns)} new patterns to Entity Ruler")
            return True
        except Exception as e:
            logger.error(f"Error adding patterns to Entity Ruler: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _create_initial_patterns(self) -> List[EntityPattern]:
        """
        Creates initial patterns for the Entity Ruler.
        
        Returns:
            List[EntityPattern]: List of patterns for entity recognition
        """
        patterns = []
        
        # Add here patterns for medical entity recognition
        # Example:
        # patterns.append(EntityPattern(label="MEDICATION", pattern="aspirina"))
        
        return patterns
    
    def extract_entities(self, doc, text: str) -> List[Entity]:
        """
        Extract entities from the spaCy processed document.
        
        Args:
            doc: spaCy processed document
            text: Original text
            
        Returns:
            List[Entity]: List of extracted entities
        """
        entities = []
        
        # Log detailed information of all entities found by spaCy
        logger.info(f"All entities found by spaCy:")
        for i, ent in enumerate(doc.ents):
            logger.info(f"Entity {i+1}: Text='{ent.text}', Label='{ent.label_}', Start={ent.start_char}, End={ent.end_char}")
        
        # Log intent entities
        intent_entities = [ent for ent in doc.ents if ent.label_.startswith("INTENT_")]
        logger.info(f"Intent entities found: {[(ent.text, ent.label_) for ent in intent_entities]}")
        
        # Log medical terms
        medical_terms = [ent for ent in doc.ents if ent.label_ == "termo_medico"]
        logger.info(f"Medical terms found: {[(ent.text, ent.label_) for ent in medical_terms]}")
        
        # Extract entities recognized by spaCy
        for ent in doc.ents:
            # Check if it's an intent entity
            if ent.label_.startswith("INTENT_"):
                logger.info(f"Found intent entity: '{ent.text}' with label '{ent.label_}'")
                entities.append(Entity(
                    value=ent.text,
                    entity_type=ent.label_,
                    start=ent.start_char,
                    end=ent.end_char
                ))
            # Check if it's a medical term from the ontology
            elif ent.label_ == "termo_medico":
                logger.info(f"Found medical term from ontology: '{ent.text}'")
                entities.append(Entity(
                    value=ent.text,
                    entity_type="termo_medico",
                    start=ent.start_char,
                    end=ent.end_char
                ))
            # Filter other potentially relevant entities
            elif ent.label_ in ["DISEASE", "BODY_PART", "MEDICAL_PROCEDURE", "MEDICATION", "MEDICAL_TERM"] or \
               ent.label_ in ["MISC", "PER", "ORG"] and len(ent.text) > 3:  # Generic entities but potentially relevant
                entities.append(Entity(
                    value=ent.text,
                    entity_type="termo_medico",
                    start=ent.start_char,
                    end=ent.end_char
                ))
        
        return entities
    
    def extract_medical_terms(self, text: str, doc) -> List[Entity]:
        """
        Extract medical terms from the text using tokens and n-grams.
        
        Args:
            text: Original text
            doc: spaCy processed document
            
        Returns:
            List[Entity]: List of medical terms extracted
        """
        entities = []
        medical_tokens = []
        
        # Use tokens to identify compound and underscore medical terms
        for token in doc:
            # Skip stopwords, punctuation and common non-medical terms
            if (not token.is_stop and not token.is_punct and 
                token.text.lower() not in self.non_medical_terms and
                len(token.text) > 2):
                medical_tokens.append(token)
        
        # Create entities from medical tokens
        for token in medical_tokens:
            # Check if this token is part of a larger entity already identified
            is_part_of_entity = False
            for entity in entities:
                if (token.idx >= entity.start and 
                    token.idx + len(token.text) <= entity.end):
                    is_part_of_entity = True
                    break
            
            if not is_part_of_entity:
                entities.append(Entity(
                    value=token.text,
                    entity_type="termo_medico",
                    start=token.idx,
                    end=token.idx + len(token.text)
                ))
        
        return entities
    
    def extract_entities_for_intent(self, text: str, doc, intent: str) -> List[Entity]:
        """
        Extract specific entities for a given intent.
        
        Args:
            text: Original text
            doc: spaCy processed document
            intent: Intent name
            
        Returns:
            List[Entity]: List of extracted entities
        """
        entities = self.extract_entities(doc, text)
        
        if intent == "plano_cuidado":
            # Clean incorrect entities when the intent is plano_cuidado
            entities = [e for e in entities if e.value.lower() not in 
                       ["plano", "planos", "cuidado", "cuidados", "qual o plano", "cuidados para"]]
            
            # Extrair o termo médico principal da consulta
            care_plan_patterns = [
                r'(?:plano|planos)\s+de\s+(?:cuidados?)\s+(?:para|de)\s+([^\s.,;?!]+(?:\s+[^\s.,;?!]+)*)',
                r'(?:cuidados?)\s+(?:para|de)\s+([^\s.,;?!]+(?:\s+[^\s.,;?!]+)*)',
                r'(?:como)\s+(?:cuidar)\s+(?:de|do|da)\s+([^\s.,;?!]+(?:\s+[^\s.,;?!]+)*)',
            ]
            
            for pattern in care_plan_patterns:
                regex = re.compile(pattern, re.IGNORECASE)
                match = regex.search(text)
                if match and len(match.groups()) >= 1:
                    term = match.group(1).strip()
                    if term and term.lower() not in ["plano", "planos", "cuidado", "cuidados"]:
                        # Check if there is already an entity with this value
                        if not any(e.value.lower() == term.lower() for e in entities):
                            entities.append(Entity(
                                value=term,
                                entity_type="termo_medico",
                                start=match.start(1),
                                end=match.end(1)
                            ))
                        break
        
        elif intent == "tratamento":
            # Ensure we don't treat 'tratamento' as a medical entity
            entities = [e for e in entities if e.value.lower() not in 
                       ["tratamento", "tratamentos", "o tratamento", "tratar"]]
            
            # Extract the main medical term from the query
            treatment_patterns = [
                r'(?:tratamentos?)\s+(?:para|de)\s+([^\s.,;?!]+(?:\s+[^\s.,;?!]+)*)',
                r'(?:como)\s+(?:tratar)\s+([^\s.,;?!]+(?:\s+[^\s.,;?!]+)*)',
            ]
            
            for pattern in treatment_patterns:
                regex = re.compile(pattern, re.IGNORECASE)
                match = regex.search(text)
                if match and len(match.groups()) >= 1:
                    term = match.group(1).strip()
                    if term and term.lower() not in ["tratamento", "tratamentos"]:
                        # Check if there is already an entity with this value
                        if not any(e.value.lower() == term.lower() for e in entities):
                            entities.append(Entity(
                                value=term,
                                entity_type="termo_medico",
                                start=match.start(1),
                                end=match.end(1)
                            ))
                        break
        
        # Add other medical entities found in the text
        medical_entities = self.extract_medical_terms(text, doc)
        for entity in medical_entities:
            if not any(e.value.lower() == entity.value.lower() for e in entities):
                entities.append(entity)
        
        return entities
    
    def remove_duplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        """
        Remove duplicate entities from the list.
        
        Args:
            entities: List of entities
            
        Returns:
            List[Entity]: List of entities without duplicates
        """
        unique_entities = []
        seen_values = set()
        
        for entity in entities:
            normalized_value = entity.value.lower().strip()
            if normalized_value not in seen_values and len(normalized_value) > 2:
                seen_values.add(normalized_value)
                unique_entities.append(entity)
        
        return unique_entities
