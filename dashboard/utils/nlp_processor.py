"""
Module for NLP processing in the OntoMed chatbot.
Este módulo foi refatorado para seguir o princípio de responsabilidade única.
A implementação principal foi movida para o pacote nlp/.
"""
import logging
import re
import unicodedata
from typing import Dict, List, Any, Optional, Tuple

from .nlp.models import Entity as NewEntity, Intent
from .nlp.processor import NLPProcessor as RefactoredNLPProcessor

# Configure logging
logger = logging.getLogger(__name__)

class Entity:
    """Class to represent extracted entities from text."""
    def __init__(self, value: str, entity_type: str, start: int = 0, end: int = 0):
        self.value = value
        self.entity_type = entity_type
        self.start = start
        self.end = end
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the entity to a dictionary."""
        return {
            "value": self.value,
            "entity_type": self.entity_type,
            "start": self.start,
            "end": self.end
        }
    
    @classmethod
    def from_new_entity(cls, entity):
        """Converte uma entidade do novo modelo para o modelo antigo."""
        return cls(
            value=entity.value,
            entity_type=entity.entity_type,
            start=entity.start,
            end=entity.end
        )

class Message:
    """Class to represent processed messages."""
    def __init__(self, text: str, intent: str = "", entities: List[Entity] = None, 
                 confidence: float = 0.0, context: Dict[str, Any] = None):
        self.text = text
        self.intent = intent
        self.entities = entities or []
        self.confidence = confidence
        self.context = context or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the message to a dictionary."""
        return {
            "text": self.text,
            "intent": self.intent,
            "entities": [e.to_dict() for e in self.entities],
            "confidence": self.confidence,
            "context": self.context
        }

class NLPProcessor:
    """
    NLP processor for the OntoMed chatbot.
    Esta classe agora é um wrapper para a implementação refatorada em nlp/processor.py.
    """
    
    def __init__(self, api_client=None, model_name="pt_core_news_lg"):
        """
        Initialize the NLP processor.
        
        Args:
            api_client: API client for OntoMed (optional)
            model_name: Name of the spaCy model to load
        """
        # Initialize the refactored processor
        self.processor = RefactoredNLPProcessor(model_name=model_name)
        self.api_client = api_client
        
        # For compatibility with existing code
        self.nlp = None
        self.entity_ruler = None
        self.entity_ruler_initialized = False
        self.intent_keywords = {
            "buscar_conceito": ["buscar", "busca", "encontrar", "encontre", "procurar", "procure", "pesquisar", "pesquise", "conceito", "termo"],
            #"explicar_termo": ["explicar", "explique", "definir", "defina", "o que é", "o que significa", "significado", "definição"],
            "relacionamentos": ["relacionamento", "relacionamentos", "relação", "relações", "conectado", "conectados", "ligado", "ligados"],
            "listar_termos": ["listar termos", "liste termos", "mostrar termos", "mostre termos", "exibir termos", "exiba termos", "todos os termos", "todas as termos", "termos disponíveis", "termos existentes", "conceitos disponíveis", "conceitos existentes", "listar conceitos", "liste conceitos", "mostrar conceitos", "mostre conceitos", "exibir conceitos", "exiba conceitos", "listar conceitos médicos", "liste conceitos médicos", "mostrar conceitos médicos", "mostre conceitos médicos", "exibir conceitos médicos", "exiba conceitos médicos", "quais são os conceitos", "quais são os termos"],
            #"tratamento": ["tratamento", "tratamentos", "tratar", "terapia", "terapias", "medicamento", "medicamentos", "remédio", "remédios"],
            "capacidades": ["capacidades", "capacidades do chatbot", "funcionalidades", "funcionalidades do chatbot", "o que você pode fazer", "o que você sabe fazer", "o que você faz", "o que você pode", "quais são suas capacidades", "quais são suas funcionalidades", "quais são as ações", "o que sabe fazer", "pode fazer", "consegue fazer", "capaz de fazer", "funções", "recursos", "ações", "habilidades", "listar capacidades", "liste capacidades", "mostrar capacidades", "mostre capacidades", "exibir capacidades", "exiba capacidades"],
            "ajuda": ["ajuda", "ajudar", "ajude", "socorro", "help", "auxílio"]
        }
        
        # Initialize the spaCy model lazily (only when needed)
        self.nlp = None
        
        # Entity ruler for medical concepts
        self.entity_ruler = None
        
        # Cache of medical concepts for the entity ruler
        self.medical_concepts_cache = []
        
        # Flag to indicate if the entity ruler was initialized
        self.entity_ruler_initialized = False
        
        logger.info("NLPProcessor initialized successfully")
        
    def normalize_medical_term(self, term: str) -> str:
        """Normalize medical terms for more effective search.
        
        Args:
            term: Medical term to be normalized
            
        Returns:
            Normalized term for search
        """
        # Delegate to the refactored processor
        return self.processor.normalize_medical_term(term)

        
    def expand_query_with_ontology(self, term: str, max_related: int = 3) -> List[str]:
        """Expand a query term using the ontology.
        
        Args:
            term: Term to expand
            max_related: Maximum number of related terms to include
            
        Returns:
            List of expanded terms
        """
        # Check if the processor was initialized
        if not hasattr(self, 'processor') or self.processor is None:
            if not self.initialize():
                logger.warning("Processor not initialized for query expansion")
                return [term]
        
        # Configure the API client in the processor if necessary
        if self.api_client and not self.processor.api_client:
            self.processor.set_api_client(self.api_client)
            
        # Delegate to the refactored processor
        return self.processor.expand_query_with_ontology(term, max_related)
    
    def initialize(self) -> bool:
        """Initialize the spaCy model and entity ruler.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        # Delegate to the refactored processor
        success = self.processor.initialize()
        
        if success:
            # For compatibility with existing code
            self.nlp = self.processor.nlp
            if hasattr(self.processor, 'entity_manager') and hasattr(self.processor.entity_manager, 'entity_ruler'):
                self.entity_ruler = self.processor.entity_manager.entity_ruler
                self.entity_ruler_initialized = True
            
            logger.info("NLPProcessor initialized successfully via refactored implementation")
        else:
            logger.error("Failed to initialize NLPProcessor refactored")
            
        return success
    
    def update_medical_concepts_ruler(self, concepts=None):
        """Update the Entity Ruler with medical concepts.
        
        Args:
            concepts: Optional list of medical concepts to add to the ruler
            
        Returns:
            bool: True if the update was successful, False otherwise
        """
        # Check if the processor was initialized
        if not hasattr(self, 'processor') or self.processor is None:
            if not self.initialize():
                logger.warning("Processor not initialized for updating medical concepts")
                return False
        
        # Configure the API client in the processor if necessary
        if self.api_client and not self.processor.api_client:
            self.processor.set_api_client(self.api_client)
            
        # Delegate to the refactored processor
        success = self.processor.update_medical_concepts_ruler(concepts)
        
        # Update references for compatibility
        if success and hasattr(self.processor, 'entity_manager') and hasattr(self.processor.entity_manager, 'entity_ruler'):
            self.entity_ruler = self.processor.entity_manager.entity_ruler
            self.entity_ruler_initialized = True
            
        return success
                
        return self.nlp is not None
        
    def update_medical_concepts_ruler(self, force_update=False):
        """Update the Entity Ruler with medical concepts from the ontology.
        
        Args:
            force_update: Force update even if already initialized
            
        Returns:
            True if the update was successful, False otherwise
        """
        # Check if spaCy is initialized
        if not self._initialize_spacy():
            logger.warning("spaCy could not be initialized for updating medical concepts")
            return False
            
        # Check if already initialized and not forcing update
        if self.entity_ruler_initialized and not force_update:
            logger.info("Entity Ruler already initialized with medical concepts")
            return True
            
        try:
            # Search for medical concepts from the API
            if self.api_client:
                logger.info("Searching for medical concepts from the API for the Entity Ruler")
                concepts = self.api_client.get_concepts()
                
                if not concepts:
                    logger.warning("No medical concepts found in the API")
                    return False
                    
                # Create patterns for the entity ruler
                patterns = []
                
                for concept in concepts:
                    # Get the concept name
                    concept_name = concept.get("label", "")
                    if not concept_name:
                        continue
                        
                    # Add the concept name as a pattern
                    patterns.append({"label": "MEDICAL_TERM", "pattern": concept_name})
                    
                    # Add version with underscore replacing spaces
                    if " " in concept_name:
                        underscore_name = concept_name.replace(" ", "_")
                        patterns.append({"label": "MEDICAL_TERM", "pattern": underscore_name})
                    
                    # Add version without underscore
                    if "_" in concept_name:
                        space_name = concept_name.replace("_", " ")
                        patterns.append({"label": "MEDICAL_TERM", "pattern": space_name})
                
                # Add patterns to the entity ruler
                if patterns:
                    # Check if the entity ruler is available
                    if self.entity_ruler:
                        self.entity_ruler.add_patterns(patterns)
                        logger.info(f"Added {len(patterns)} medical concept patterns to the Entity Ruler")
                        
                        # Update the concepts cache
                        self.medical_concepts_cache = concepts
                        
                        # Mark as initialized
                        self.entity_ruler_initialized = True
                        return True
                    else:
                        logger.error("Entity Ruler is not available to add medical concept patterns")
                
        except Exception as e:
            logger.error(f"Error updating Entity Ruler with medical concepts: {str(e)}")
            
        return False
        
    def register_chatbot_actions(self, static_actions=None, template_actions=None):
        """Register chatbot actions (static and template-based) in the Entity Ruler.
        
        Args:
            static_actions: List of static chatbot actions
            template_actions: List of template-based actions
            
        Returns:
            True if the registration was successful, False otherwise
        """
        # Check if the processor was initialized
        if not hasattr(self, 'processor') or self.processor is None:
            if not self.initialize():
                logger.warning("Processor not initialized for registering chatbot actions")
                return False
                
        # Delegate to the refactored processor
        return self.processor.register_chatbot_actions(static_actions, template_actions)
    
    def update_entity_intent_mapping(self, entity_type: str, intent_name: str) -> bool:
        """
        Update the mapping of entities to intents in the NLP system.
        Delegates the operation to the scoring_system.
        
        Args:
            entity_type: Type of entity (ex: INTENT_LISTAR_TERMOS)
            intent_name: Intent name (ex: listar_termos)
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        try:
            # Check if the processor was initialized
            if not hasattr(self, 'processor') or self.processor is None:
                if not self.initialize():
                    logger.warning("Processor not initialized for updating entity intent mapping")
                    return False
            
            # Delegate to the scoring_system if available
            if hasattr(self.processor, 'scoring_system'):
                return self.processor.scoring_system.update_entity_intent_mapping(entity_type, intent_name)
            
            logger.warning("Scoring system not found in processor")
            return False
                
        except Exception as e:
            logger.error(f"Error updating entity-intent mapping: {str(e)}")
            return False
    
    def process_message(self, text: str, context: Dict[str, Any] = None) -> Message:
        """
        Process a text message and returns the intent and entities identified.
        
        Args:
            text: Text of the message
            context: Optional context information for the conversation
            
        Returns:
            Message object with intent and entities identified
        """
        text = text.strip()
        
        # Check if the text is empty
        if not text:
            return Message(text="", intent="", entities=[], confidence=0.0)
            
        # Initialize the processor if necessary
        if not self.initialize():
            logger.error("Failed to initialize NLP processor")
            return Message(text=text, intent="outro", entities=[], confidence=0.3)
            
        # Process the text using the refactored processor
        intent = self.processor.process_text(text, context)
        
        # Convert entities from the new format to the old format
        legacy_entities = self._convert_entities(intent.entities)
        
        # Create and return the processed message
        return Message(
            text=text,
            intent=intent.intent,
            entities=legacy_entities,
            confidence=intent.confidence,
            context=self.processor.get_conversation_context()
        )
