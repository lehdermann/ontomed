"""
Chatbot integration module with NLP processor and API client.
"""
import logging
from typing import Dict, Any, List

from .nlp_processor import NLPProcessor
from .api_client import APIClient

# Configure logging
logger = logging.getLogger(__name__)

class ChatbotIntegration:
    """
    Chatbot integration class with NLP processor and API client.
    
    This class coordinates the message processing flow:
    1. Processes the user message using NLPProcessor to identify intent and entities
    2. Executes actions based on the identified intent using APIClient
    3. Generates and returns appropriate responses
    """
    
    def __init__(self, api_client: APIClient):
        """
        Initializes the chatbot integration.
        
        Args:
            api_client: API client for communication with the backend
        """
        self.api_client = api_client
        self.nlp_processor = NLPProcessor()
        logger.info("ChatbotIntegration initialized successfully")
    
    def process_message(self, message: str) -> Dict[str, Any]:
        """
        Process a user message and return the response.
        
        Args:
            message: User message
            
        Returns:
            Dictionary containing the response, intent, and entities
        """
        try:
            logger.info(f"Processing message: '{message}'")
            
            # Process the user message using NLPProcessor to identify intent and entities
            processed_message = self.nlp_processor.process_message(message)
            
            # Extract intent and entities
            intent = processed_message.intent
            entities = processed_message.entities
            
            logger.info(f"Intent identified: {intent}")
            
            # Generate response based on intent
            if intent == "buscar_conceito":
                return self._handle_buscar_conceito(entities)
                
            elif intent == "explicar_termo":
                return self._handle_explicar_termo(entities)
                
            elif intent == "relacionamentos":
                return self._handle_relacionamentos(entities)
                
            elif intent == "ajuda":
                return self._handle_ajuda()
                
            else:
                # Generic fallback response
                return self._handle_outro(message)
                
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return {
                "intent": "erro",
                "response": "Desculpe, encontrei um problema ao processar sua mensagem. Por favor, tente novamente ou reformule sua pergunta."
            }
    
    def _handle_buscar_conceito(self, entities: List) -> Dict[str, Any]:
        """Process the intent to search for concepts."""
        if not entities:
            return {
                "intent": "buscar_conceito",
                "response": "Não consegui identificar sobre qual termo você gostaria de buscar conceitos. Poderia especificar?"
            }
        
        # Extract the search term
        term = entities[0].value
        
        try:
            # Try to search concepts in the API
            concepts = self.api_client.get_concepts({"search": term})
            
            if concepts and len(concepts) > 0:
                # Format the found concepts
                concepts_text = "\n\n".join([
                    f"**{c.get('label', c.get('id', 'Conceito'))}**: {c.get('description', 'Sem descrição disponível')}" 
                    for c in concepts[:5]
                ])
                response_text = f"Found the following concepts related to '{term}':\n\n{concepts_text}"
            else:
                # If not found in the API, generate response via LLM
                response_text = self.api_client.generate_content(
                    f"Liste e explique brevemente conceitos médicos relacionados a '{term}'",
                    temperature=0.7,
                    max_tokens=500
                )
        except Exception as e:
            logger.error(f"Error searching concepts: {str(e)}", exc_info=True)
            # Fallback to LLM generation
            response_text = self.api_client.generate_content(
                f"Liste e explique brevemente conceitos médicos relacionados a '{term}'",
                temperature=0.7,
                max_tokens=500
            )
        
        return {
            "intent": "buscar_conceito",
            "response": response_text,
            "entities": [e.to_dict() for e in entities]
        }
    
    def _handle_explicar_termo(self, entities: List) -> Dict[str, Any]:
        """Process the intent to explain a term."""
        if not entities:
            return {
                "intent": "explicar_termo",
                "response": "Não consegui identificar qual termo você gostaria que eu explicasse. Poderia especificar?"
            }
        
        # Extract the term
        term = entities[0].value
        
        # Generate explanation via LLM
        response_text = self.api_client.generate_content(
            f"Explique em detalhes o que é '{term}' em termos médicos",
            temperature=0.7,
            max_tokens=500
        )
        
        return {
            "intent": "explicar_termo",
            "response": response_text,
            "entities": [e.to_dict() for e in entities]
        }
    
    def _handle_relacionamentos(self, entities: List) -> Dict[str, Any]:
        """Process the intent to show relationships."""
        if len(entities) < 2:
            return {
                "intent": "relacionamentos",
                "response": "Não consegui identificar quais termos você gostaria de ver relacionamentos. Poderia especificar?"
            }
        
        # Extract the terms
        term1 = entities[0].value
        term2 = entities[1].value
        
        try:
            # Simplified implementation - in practice, we would need to first search for the IDs of the concepts
            response_text = self.api_client.generate_content(
                f"Explique como os conceitos '{term1}' e '{term2}' se relacionam na medicina",
                temperature=0.7,
                max_tokens=500
            )
        except Exception as e:
            logger.error(f"Error searching relationships: {str(e)}", exc_info=True)
            response_text = f"Desculpe, não consegui encontrar informações sobre a relação entre {term1} e {term2}."
        
        return {
            "intent": "relacionamentos",
            "response": response_text,
            "entities": [e.to_dict() for e in entities]
        }
    
    def _handle_ajuda(self) -> Dict[str, Any]:
        """Process a intent to help."""
        response_text = """Posso ajudá-lo com as seguintes ações:
        
1. **Search concepts** - Ex: "Show concepts about diabetes"
2. **Explain terms** - Ex: "What is hypertension?"
3. **Show relationships** - Ex: "How diabetes relates to obesity?"
4. **Ajuda** - Ex: "Quais comandos posso usar?"

Como posso ajudá-lo hoje?"""
        
        return {
            "intent": "ajuda",
            "response": response_text
        }
    
    def _handle_outro(self, message: str) -> Dict[str, Any]:
        """Process unknown intents."""
        # Try to get medical terms from the ontology to provide context
        try:
            # Get a sample of medical terms from the ontology
            concepts = self.api_client.get_concepts()
            
            # Extract terms from concepts (limit to avoid token limits)
            medical_terms = []
            if concepts and len(concepts) > 0:
                # Extract the most relevant terms (max 30)
                for concept in concepts[:30]:
                    if isinstance(concept, dict):
                        term = concept.get('label') or concept.get('display_name') or concept.get('name')
                        if term and isinstance(term, str):
                            medical_terms.append(term)
            
            # Create context with available terms if we have any
            if medical_terms:
                logger.info(f"Providing {len(medical_terms)} medical terms as context for LLM")
                context = "Contexto da ontologia médica - termos disponíveis incluem: " + ", ".join(medical_terms)
                
                # Fallback to generic response via LLM with context
                response_text = self.api_client.generate_content(
                    f"{context}\n\nConsiderando o contexto acima, responda à seguinte pergunta sobre medicina: '{message}'",
                    temperature=0.7,
                    max_tokens=500
                )
            else:
                # If no terms available, use the original approach
                logger.warning("No medical terms available for context, using standard prompt")
                response_text = self.api_client.generate_content(
                    f"Responda à seguinte pergunta sobre medicina: '{message}'",
                    temperature=0.7,
                    max_tokens=500
                )
        except Exception as e:
            logger.error(f"Error getting medical terms for context: {str(e)}", exc_info=True)
            # Fallback without context if there's an error
            response_text = self.api_client.generate_content(
                f"Responda à seguinte pergunta sobre medicina: '{message}'",
                temperature=0.7,
                max_tokens=500
            )
        
        return {
            "intent": "outro",
            "response": response_text
        }
