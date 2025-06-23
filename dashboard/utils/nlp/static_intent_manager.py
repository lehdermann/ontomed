"""
Module for managing static intents of OntoMed.
"""
import logging
from typing import Dict, List, Optional, Any
import spacy
from spacy.tokens import Span, Doc

logger = logging.getLogger(__name__)

class StaticIntentManager:
    """Manages the detection of static intents based on patterns."""

    def __init__(self, nlp):
        """
        Initializes the static intent manager.
        
        Args:
            nlp: Loaded spaCy model instance.
        """
        self.nlp = nlp
        self.matcher = spacy.matcher.Matcher(nlp.vocab)
        self._initialize_patterns()
        
    def _initialize_patterns(self):
        """Initializes the patterns for each type of static intent."""
        self.patterns = {
            'INTENT_RELATIONSHIPS': self._get_relationship_patterns(),
            'INTENT_LIST_TERMS': self._get_list_terms_patterns(),
            'INTENT_CAPABILITIES': self._get_capabilities_patterns(),
            'INTENT_HELP': self._get_help_patterns(),
            'INTENT_ABOUT_ONTOMED': self._get_about_ontomed_patterns()
        }
        
        # Registers the patterns in the Matcher
        for intent_name, patterns in self.patterns.items():
            for i, pattern in enumerate(patterns):
                self.matcher.add(f"{intent_name}_{i}", [pattern])
        logger.info(f"Static intent patterns initialized: {list(self.patterns.keys())}")

    def _get_relationship_patterns(self):
        """Returns patterns for the relationships intent."""
        action_verbs = ["mostrar", "listar", "ver", "exibir", "quais"]
        relationship_nouns = ["relacionamentos", "relações", "relacionamento", "relação"]
        return [
            # "show relationships of [term]"
            [{"LEMMA": {"IN": action_verbs}},
             {"LEMMA": {"IN": relationship_nouns}, "OP": "?"},
             {"LEMMA": "de", "OP": "?"}],
            
            # "what are the relationships of [term]"
            [{"LOWER": {"IN": ["quais", "quais são"]}},
             {"LOWER": {"IN": ["as", "os"]}, "OP": "?"},
             {"LEMMA": {"IN": relationship_nouns}},
             {"LOWER": {"IN": ["do", "da", "de"]}, "OP": "?"}],
            
            # "relationships of [term]" (without action verb)
            [{"LOWER": {"IN": relationship_nouns}},
             {"LEMMA": "de", "OP": "?"}],
             
            # "[term] relationships"
            [{"LOWER": {"IN": relationship_nouns}}]
        ]

    def _get_list_terms_patterns(self):
        """Returns patterns for listing terms/concepts."""
        action_verbs = ["listar", "mostrar", "exibir", "ver"]
        concept_terms = ["termo", "conceito", "termos", "conceitos"]
        return [
            # "list terms/concepts" - Focus on action verbs and significant nouns
            [{"LEMMA": {"IN": action_verbs}},
             # Removed dependency on stopwords like "os", "todos"
             {"LEMMA": {"IN": concept_terms}}],
            
            # "terms/concepts" with medical qualifier
            [{"LEMMA": {"IN": concept_terms}},
             {"LOWER": "médico"}],
            
            # Specific pattern for "listar conceitos" without stopwords
            [{"LEMMA": {"IN": action_verbs}},
             {"LEMMA": {"IN": concept_terms}}]
        ]

    def _get_capabilities_patterns(self):
        """Returns patterns for querying system capabilities."""
        capability_terms = ["capacidade", "função", "recurso", "funcionalidade", "habilidade", "comandos"]
        action_verbs = ["listar", "mostrar", "exibir", "ver"]
        
        return [
            # Focus on action verbs and significant nouns
            [{"LEMMA": {"IN": action_verbs}}],
            
            # Focus on nouns related to capabilities
            [{"LEMMA": {"IN": capability_terms}}],
            
            # Specific terms for capabilities
            [{"LOWER": "capacidades"}],
            
            # Verb + noun combination without depending on stopwords
            [{"LEMMA": {"IN": action_verbs}},
             {"LEMMA": {"IN": capability_terms}}]
        ]

    def _get_help_patterns(self):
        """Returns patterns for help requests."""
        help_terms = ["ajuda", "help", "socorro", "assistência", "suporte"]
        action_verbs = ["usar", "utilizar", "operar"]
        
        return [
            # Direct help terms
            [{"LEMMA": {"IN": help_terms}}],
            
            # Verbs related to usage
            [{"LEMMA": {"IN": action_verbs}}],
            
            # Specific commands
            [{"LOWER": "comandos"}],
            
            # Significant combinations without depending on stopwords
            [{"LEMMA": "precisar"}, 
             {"LEMMA": {"IN": help_terms}}]
        ]
        
    def _get_about_ontomed_patterns(self):
        """Returns patterns for questions about what OntoMed is."""
        ontomed_terms = ["ontomed", "onto med", "onto-med", "sistema", "aplicação", "ferramenta"]
        action_verbs = ["falar", "contar", "explicar", "dizer", "descrever", "informar", "apresentar"]
        question_terms = ["sobre", "acerca", "respeito"]
        
        return [
            # Direct terms related to OntoMed
            [{"LOWER": {"IN": ontomed_terms}}],
            
            # Action verbs + OntoMed (without depending on stopwords)
            [{"LEMMA": {"IN": action_verbs}},
             {"LOWER": {"IN": ontomed_terms}}],
             
            # Significant combinations without depending on stopwords
            [{"LEMMA": {"IN": question_terms}},
             {"LOWER": {"IN": ontomed_terms}}],
             
            # Pattern for "what is" without depending on the exact structure
            [{"LEMMA": "ser"},
             {"LOWER": {"IN": ontomed_terms}}],
            
            # Verbs + prepositions + OntoMed
            [{"LEMMA": {"IN": action_verbs}},
             {"LOWER": {"IN": ["sobre", "do", "da"]}},
             {"LOWER": {"IN": ontomed_terms}}],
            
            # "OntoMed what is" - reformulated to be more robust
            [{"LOWER": {"IN": ontomed_terms}},
             {"LEMMA": "ser"}]
        ]

    def detect_intent(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Detects the most likely static intent in the text.
        
        Args:
            text: User input text.
            
        Returns:
            Dictionary with intent information or None if no intent is detected.
        """
        if not text or not text.strip():
            return None
            
        doc = self.nlp(text.lower())
        matches = self.matcher(doc)
        
        if not matches:
            return None
            
        # Group matches by intent type
        intent_scores = {}
        for match_id, start, end in matches:
            # Get the full pattern name and extract the base intent name (before the first underscore)
            pattern_name = self.nlp.vocab.strings[match_id]
            intent_name = '_'.join(pattern_name.split('_')[:-1])  # Join all parts except the last one (index)
            score = self._calculate_match_score(doc[start:end])
            
            if intent_name not in intent_scores or score > intent_scores[intent_name]['score']:
                intent_scores[intent_name] = {
                    'score': score,
                    'span': (start, end)
                }
        
        if not intent_scores:
            return None
            
        # Get the intent with the highest score
        best_intent, best_match = max(intent_scores.items(), key=lambda x: x[1]['score'])
        start, end = best_match['span']
        
        return {
            'intent': best_intent,
            'confidence': best_match['score'],
            'text': doc[start:end].text,
            'start': start,
            'end': end
        }

    def _calculate_match_score(self, span) -> float:
        """
        Calculates the score of a match.
        
        Args:
            span: Span of the document that matches the pattern.
            
        Returns:
            Confidence score between 0 and 1.
        """
        # Base score based on match length
        base_score = min(0.5 + (len(span) * 0.1), 0.9)
        
        # Bonus if covers more than 50% of the words in the sentence
        doc = span.doc
        coverage = len(span) / len(doc)
        if coverage > 0.5:
            base_score = min(base_score + 0.2, 1.0)
            
        return round(base_score, 2)
