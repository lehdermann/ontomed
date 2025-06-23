"""
Implementation of the Dependency Matcher for the OntoMed.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import spacy
from spacy.matcher import DependencyMatcher

from .models import Entity

logger = logging.getLogger(__name__)


class DependencyMatcherManager:
    """
    Manages the Dependency Matcher of spaCy to identify syntactic patterns.
    """
    
    def __init__(self, nlp):
        """
        Initializes the Dependency Matcher Manager.
        
        Args:
            nlp: Loaded spaCy model
        """
        self.nlp = nlp
        self.matcher = DependencyMatcher(self.nlp.vocab)
        self.initialized = False
        self.intent_patterns = {}
        
    def initialize(self) -> bool:
        """
        Initializes the Dependency Matcher with patterns for different intents.
        
        Returns:
            bool: True if initialized successfully, False otherwise
        """
        if self.initialized:
            return True
            
        try:
            # Define patterns for different intents
            self._define_patterns()
            
            # Add patterns to matcher
            for intent, patterns in self.intent_patterns.items():
                for i, pattern in enumerate(patterns):
                    self.matcher.add(f"{intent}_{i}", [pattern])
            
            self.initialized = True
            logger.info(f"Dependency Matcher initialized with patterns for {len(self.intent_patterns)} intents")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Dependency Matcher: {str(e)}")
            return False
    
    def _define_patterns(self):
        """
        Define syntactic patterns for different intents.
        """
        # Lista de termos específicos do OntoMed
        ontomed_terms = ["ontomed", "onto med", "onto-med", "sistema", "aplicação", "ferramenta"]
        
        # Patterns for explaining OntoMed (sobre_ontomed)
        self.intent_patterns["sobre_ontomed"] = [
            # What is OntoMed?
            [
                {"RIGHT_ID": "root", "RIGHT_ATTRS": {"LEMMA": "ser"}},
                {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "subject", "RIGHT_ATTRS": {"DEP": "nsubj"}},
                {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "attr", "RIGHT_ATTRS": {"DEP": "attr", "LOWER": {"IN": ontomed_terms}}}
            ],
            # Explain OntoMed
            [
                {"RIGHT_ID": "root", "RIGHT_ATTRS": {"LEMMA": {"IN": ["explicar", "descrever", "falar", "contar", "apresentar", "definir"]}}},
                {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "object", "RIGHT_ATTRS": {"DEP": "dobj", "LOWER": {"IN": ontomed_terms}}}
            ],
            # About OntoMed
            [
                {"RIGHT_ID": "root", "RIGHT_ATTRS": {"LEMMA": {"IN": ["sobre", "acerca", "respeito"]}}},
                {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "pobj", "RIGHT_ATTRS": {"LOWER": {"IN": ontomed_terms}}}
            ],
        ]
        
        # We do not define specific patterns for concept_explanation since it is a dynamic intent
        # Instead, we use the generic explicar_termo pattern and contextual analysis in scoring_system.py
        
        # Patterns for general term explanation (fallback)
        self.intent_patterns["explicar_termo"] = [
            # What is X?
            [
                {"RIGHT_ID": "root", "RIGHT_ATTRS": {"LEMMA": "ser"}},
                {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "subject", "RIGHT_ATTRS": {"DEP": "nsubj"}},
                {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "attr", "RIGHT_ATTRS": {"DEP": "attr", "POS": "NOUN"}}
            ],
            # Explain X
            [
                {"RIGHT_ID": "root", "RIGHT_ATTRS": {"LEMMA": "explicar"}},
                {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "object", "RIGHT_ATTRS": {"DEP": "dobj", "POS": "NOUN"}}
            ],
            # Explanations about X
            [
                {"RIGHT_ID": "root", "RIGHT_ATTRS": {"LEMMA": "explicação"}},
                {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "prep", "RIGHT_ATTRS": {"DEP": "prep", "LEMMA": "sobre"}},
                {"LEFT_ID": "prep", "REL_OP": ">", "RIGHT_ID": "pobj", "RIGHT_ATTRS": {"DEP": "pobj", "POS": "NOUN"}}
            ],
            # Definition of X
            [
                {"RIGHT_ID": "root", "RIGHT_ATTRS": {"LEMMA": "definição"}},
                {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "prep", "RIGHT_ATTRS": {"DEP": "prep", "LEMMA": "de"}},
                {"LEFT_ID": "prep", "REL_OP": ">", "RIGHT_ID": "pobj", "RIGHT_ATTRS": {"DEP": "pobj", "POS": "NOUN"}}
            ],
            # Signification of X
            [
                {"RIGHT_ID": "root", "RIGHT_ATTRS": {"LEMMA": "significado"}},
                {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "prep", "RIGHT_ATTRS": {"DEP": "prep", "LEMMA": "de"}},
                {"LEFT_ID": "prep", "REL_OP": ">", "RIGHT_ID": "pobj", "RIGHT_ATTRS": {"DEP": "pobj", "POS": "NOUN"}}
            ]
        ]
        
        # Patterns for concept search
        self.intent_patterns["buscar_conceito"] = [
            # Search concept X
            [
                {"RIGHT_ID": "root", "RIGHT_ATTRS": {"LEMMA": "buscar"}},
                {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "dobj", "RIGHT_ATTRS": {"DEP": "dobj", "LEMMA": "conceito"}},
                {"LEFT_ID": "dobj", "REL_OP": ">", "RIGHT_ID": "prep", "RIGHT_ATTRS": {"DEP": "prep", "LEMMA": "de"}},
                {"LEFT_ID": "prep", "REL_OP": ">", "RIGHT_ID": "pobj", "RIGHT_ATTRS": {"DEP": "pobj", "POS": "NOUN"}}
            ],
            # Search information about X
            [
                {"RIGHT_ID": "root", "RIGHT_ATTRS": {"LEMMA": "buscar"}},
                {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "dobj", "RIGHT_ATTRS": {"DEP": "dobj", "LEMMA": "informação"}},
                {"LEFT_ID": "dobj", "REL_OP": ">", "RIGHT_ID": "prep", "RIGHT_ATTRS": {"DEP": "prep", "LEMMA": "sobre"}},
                {"LEFT_ID": "prep", "REL_OP": ">", "RIGHT_ID": "pobj", "RIGHT_ATTRS": {"DEP": "pobj", "POS": "NOUN"}}
            ]
        ]
        
        # Patterns for treatments
        self.intent_patterns["tratamento"] = [
            # How to treat X?
            [
                {"RIGHT_ID": "root", "RIGHT_ATTRS": {"LEMMA": "tratar"}},
                {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "dobj", "RIGHT_ATTRS": {"DEP": "dobj", "POS": "NOUN"}}
            ],
            # Treatment for X
            [
                {"RIGHT_ID": "root", "RIGHT_ATTRS": {"LEMMA": "tratamento"}},
                {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "prep", "RIGHT_ATTRS": {"DEP": "prep", "LEMMA": "para"}},
                {"LEFT_ID": "prep", "REL_OP": ">", "RIGHT_ID": "pobj", "RIGHT_ATTRS": {"DEP": "pobj", "POS": "NOUN"}}
            ],
            # Treatment of X
            [
                {"RIGHT_ID": "root", "RIGHT_ATTRS": {"LEMMA": "tratamento"}},
                {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "prep", "RIGHT_ATTRS": {"DEP": "prep", "LEMMA": "de"}},
                {"LEFT_ID": "prep", "REL_OP": ">", "RIGHT_ID": "pobj", "RIGHT_ATTRS": {"DEP": "pobj", "POS": "NOUN"}}
            ]
        ]
        
        # Patterns for care plans
        self.intent_patterns["plano_cuidado"] = [
            # Care plan for X
            [
                {"RIGHT_ID": "root", "RIGHT_ATTRS": {"LEMMA": "plano"}},
                {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "prep_de", "RIGHT_ATTRS": {"DEP": "prep", "LEMMA": "de"}},
                {"LEFT_ID": "prep_de", "REL_OP": ">", "RIGHT_ID": "pobj_cuidado", "RIGHT_ATTRS": {"DEP": "pobj", "LEMMA": "cuidado"}},
                {"LEFT_ID": "pobj_cuidado", "REL_OP": ">", "RIGHT_ID": "prep_para", "RIGHT_ATTRS": {"DEP": "prep", "LEMMA": "para"}},
                {"LEFT_ID": "prep_para", "REL_OP": ">", "RIGHT_ID": "pobj", "RIGHT_ATTRS": {"DEP": "pobj", "POS": "NOUN"}}
            ],
            # Care for X
            [
                {"RIGHT_ID": "root", "RIGHT_ATTRS": {"LEMMA": "cuidado"}},
                {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "prep", "RIGHT_ATTRS": {"DEP": "prep", "LEMMA": "para"}},
                {"LEFT_ID": "prep", "REL_OP": ">", "RIGHT_ID": "pobj", "RIGHT_ATTRS": {"DEP": "pobj", "POS": "NOUN"}}
            ],
            # How to take care of X
            [
                {"RIGHT_ID": "root", "RIGHT_ATTRS": {"LEMMA": "cuidar"}},
                {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "prep", "RIGHT_ATTRS": {"DEP": "prep", "LEMMA": "de"}},
                {"LEFT_ID": "prep", "REL_OP": ">", "RIGHT_ID": "pobj", "RIGHT_ATTRS": {"DEP": "pobj", "POS": "NOUN"}}
            ]
        ]
        
        # Patterns for diagnoses
        self.intent_patterns["diagnostico"] = [
            # Diagnosis of X
            [
                {"RIGHT_ID": "root", "RIGHT_ATTRS": {"LEMMA": "diagnóstico"}},
                {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "prep", "RIGHT_ATTRS": {"DEP": "prep", "LEMMA": "de"}},
                {"LEFT_ID": "prep", "REL_OP": ">", "RIGHT_ID": "pobj", "RIGHT_ATTRS": {"DEP": "pobj", "POS": "NOUN"}}
            ],
            # Diagnoses for X
            [
                {"RIGHT_ID": "root", "RIGHT_ATTRS": {"LEMMA": "diagnóstico"}},
                {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "prep", "RIGHT_ATTRS": {"DEP": "prep", "LEMMA": "para"}},
                {"LEFT_ID": "prep", "REL_OP": ">", "RIGHT_ID": "pobj", "RIGHT_ATTRS": {"DEP": "pobj", "POS": "NOUN"}}
            ],
            # How to diagnose X
            [
                {"RIGHT_ID": "root", "RIGHT_ATTRS": {"LEMMA": "diagnosticar"}},
                {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "dobj", "RIGHT_ATTRS": {"DEP": "dobj", "POS": "NOUN"}}
            ]
        ]
        
        # Patterns for relationships
        self.intent_patterns["relacionamentos"] = [
            # Relationships of X
            [
                {"RIGHT_ID": "root", "RIGHT_ATTRS": {"LEMMA": "relação"}},
                {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "prep", "RIGHT_ATTRS": {"DEP": "prep", "LEMMA": "de"}},
                {"LEFT_ID": "prep", "REL_OP": ">", "RIGHT_ID": "pobj", "RIGHT_ATTRS": {"DEP": "pobj", "POS": "NOUN"}}
            ],
            # What is related to X?
            [
                {"RIGHT_ID": "root", "RIGHT_ATTRS": {"LEMMA": "relacionar"}},
                {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "prep", "RIGHT_ATTRS": {"DEP": "prep", "LEMMA": "com"}},
                {"LEFT_ID": "prep", "REL_OP": ">", "RIGHT_ID": "pobj", "RIGHT_ATTRS": {"DEP": "pobj", "POS": "NOUN"}}
            ],
            # Relationships between X and Y
            [
                {"RIGHT_ID": "root", "RIGHT_ATTRS": {"LEMMA": "relacionamento"}},
                {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "prep", "RIGHT_ATTRS": {"DEP": "prep", "LEMMA": "entre"}},
                {"LEFT_ID": "prep", "REL_OP": ">", "RIGHT_ID": "pobj", "RIGHT_ATTRS": {"DEP": "pobj", "POS": "NOUN"}}
            ]
        ]
    
    def match(self, doc) -> Dict[str, int]:
        """
        Find matches for dependency patterns in the document.
        
        Args:
            doc: spaCy processed document
            
        Returns:
            Dict[str, int]: Dictionary with intents and number of matches
        """
        if not self.initialized:
            self.initialize()
            
        matches = self.matcher(doc)
        
        # Count matches per intent
        intent_matches = {}
        
        for match_id, token_ids in matches:
            # Get intent name from pattern ID
            intent_name = self.nlp.vocab.strings[match_id].split('_')[0]
            
            # Increment count for this intent
            if intent_name in intent_matches:
                intent_matches[intent_name] += 1
            else:
                intent_matches[intent_name] = 1
                
            logger.debug(f"Dependency match found: {intent_name}")
            
        return intent_matches
    
    def extract_entities_from_matches(self, doc, matches) -> List[Entity]:
        """
        Extract entities from dependency matches.
        
        Args:
            doc: spaCy processed document
            matches: Dependency Matcher matches
            
        Returns:
            List[Entity]: List of extracted entities
        """
        entities = []
        
        for match_id, token_ids in matches:
            pattern_name = self.nlp.vocab.strings[match_id]
            
            # Extract entities based on pattern type
            if "explicar_termo" in pattern_name:
                # Extract the term to be explained
                for token_id in token_ids:
                    token = doc[token_id]
                    if token.pos_ == "NOUN" and token.dep_ in ["attr", "dobj", "pobj"]:
                        entities.append(Entity(
                            value=token.text,
                            entity_type="termo_medico",
                            start=token.idx,
                            end=token.idx + len(token.text)
                        ))
            
            elif "tratamento" in pattern_name or "plano_cuidado" in pattern_name or "diagnostico" in pattern_name:
                # Extract the medical term target
                for token_id in token_ids:
                    token = doc[token_id]
                    if token.pos_ == "NOUN" and token.dep_ == "pobj":
                        entities.append(Entity(
                            value=token.text,
                            entity_type="termo_medico",
                            start=token.idx,
                            end=token.idx + len(token.text)
                        ))
        
        return entities
