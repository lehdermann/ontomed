"""
Scoring system for intent scoring in OntoMed.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Set
import re
import math

from .models import Entity, Intent
from spacy.lang.pt.stop_words import STOP_WORDS as pt_stop_words

logger = logging.getLogger(__name__)


class IntentScoringSystem:
    """
    Scoring system for intent scoring in OntoMed.
    """
    
    def __init__(self, nlp=None):
        """
        Initializes the scoring system.
        
        Args:
            nlp: spaCy model for natural language processing
        """
        self.nlp = nlp
        
        # Cache for lemmas of keywords
        self.keyword_lemmas_cache = {}
        
        # Confidence thresholds
        self.confidence_thresholds = {
            "high": 0.95,
            "medium": 0.75,
            "low": 0.5,
            "minimum": 0.3
        }
        
        # Weights for different types of evidence
        self.weights = {
            "entity_ruler": 4.0,   # Reduced weight for Entity Ruler entities
            "dependency": 5.0,     # Medium weight for dependency patterns
            "keyword": 3.0,        # Increased weight for keywords
            "entity_count": 1.0,   # Weight for number of entities
            "context": 3.0         # Weight for conversation context
        }
        
        # Mapping of entities to intents
        self.entity_intent_map = {
            # Static intents (not based on templates)
            "INTENT_LIST_TERMS": "listar_termos",
            "INTENT_RELATIONSHIPS": "relacionamentos",
            "INTENT_CAPABILITIES": "capacidades",
            "INTENT_HELP": "ajuda",
            "INTENT_ABOUT_ONTOMED": "sobre_ontomed",
            
            # Dynamic intents (based on templates) will be added
            # automatically by ChatController._update_nlp_system_with_intent_info
        }
        
        # Keywords for static intents - using more specific combinations to avoid ambiguity
        self.intent_keywords = {
            "listar_termos": ["listar conceitos", "liste conceitos", "mostrar conceitos", "mostre conceitos", "exibir conceitos", "exiba conceitos", "listar termos", "liste termos", "mostrar termos", "mostre termos", "exibir termos", "exiba termos", "conceitos médicos", "termos médicos"],
            "relacionamentos": ["relacionamento", "relação", "conexão", "ligação", "associação", "como se relaciona", "relacionado com"],
            "capacidades": ["capacidades", "funcionalidades", "ações", "recursos", "habilidades", "listar capacidades", "liste capacidades", "mostrar capacidades", "mostre capacidades", "exibir capacidades", "exiba capacidades", "listar funcionalidades", "listar recursos", "listar comandos"],
            "ajuda": ["ajuda", "help", "socorro", "comandos", "suporte", "assistência", "usar", "utilizar", "operar"],
            "sobre_ontomed": ["o que é ontomed", "ontomed é", "sobre ontomed", "explique ontomed", "descreva ontomed", "fale sobre ontomed", "conte sobre ontomed", "apresente ontomed", "defina ontomed", "ontomed significa", "significado de ontomed"],
            
            # Dynamic intents (based on templates) will be added via update_intent_keywords
        }
        
        # Pre-process static keywords if spaCy model is available
        if self.nlp:
            self._preprocess_static_keywords()
    
    def _process_keyword(self, keyword: str, lemmatize: bool = True) -> List[str]:
        """
        Process a keyword, splitting by underscores, removing stopwords and punctuation,
        and applying lemmatization and stemming.
        
        Args:
            keyword: Keyword to be processed
            lemmatize: If True, apply lemmatization
            
        Returns:
            List[str]: List of processed terms (lemmas and radicals)
        """
        if not keyword or not isinstance(keyword, str):
            return []
            
        # Splits by underscore and space
        words = keyword.replace('_', ' ').split()
        
        if not self.nlp:
            # Fallback without spaCy
            stopwords = pt_stop_words
            return [word.lower() for word in words 
                   if len(word) > 2 and word.lower() not in stopwords]
        
        # Process with spaCy
        terms = []
        seen_terms = set()
        
        for word in words:
            if not word.strip():
                continue
                
            doc = self.nlp(word.lower())
            
            for token in doc:
                # Filters stopwords, punctuation and very short words
                if (token.is_stop or token.is_punct or 
                    len(token.text.strip()) <= 2):
                    continue
                    
                # Applies lemmatization if requested
                term = token.lemma_ if lemmatize else token.text
                terms.append(term)
        
        # Remove duplicates while maintaining order
        seen = set()
        return [term for term in terms if not (term in seen or seen.add(term))]
    
    def update_intent_keywords(self, intent: str, keywords: List[str]) -> bool:
        """
        Updates the keywords for an intent and preprocesses their lemmas.
        Also extracts individual words, decomposes sentences, and enriches with N-grams.
        
        Args:
            intent: Intent name
            keywords: List of keywords
            
        Returns:
            bool: True if the update was successful, False otherwise
        """
        try:
            logger.info(f"Dynamic Intent '{intent}': Original keywords: {keywords}")
            
            # 1. Process initial keywords
            processed_keywords = set()
            for keyword in keywords:
                # Add original word
                processed_keywords.add(keyword)
                # Add processed terms
                processed_keywords.update(self._process_keyword(keyword, lemmatize=False))
            
            # 2. Extract keywords from related entities
            entity_keywords = self._extract_keywords_from_entities(intent)
            if entity_keywords:
                logger.info(f"Intent DYNAMIC '{intent}': Extracted keywords from entities: {entity_keywords}")
                processed_keywords.update(entity_keywords)
            
            # 3. Generate n-grams
            ngrams = self._generate_ngrams(processed_keywords)
            if ngrams:
                logger.info(f"[DIAGNÓSTICO] Intent DYNAMIC '{intent}': Generated n-grams: {ngrams}")
                processed_keywords.update(ngrams)
            
            logger.info(f"[DIAGNÓSTICO] Intent DYNAMIC '{intent}': Original keywords: {len(keywords)}, Enriched: {len(processed_keywords)}")
            
            # Update intent keywords
            self.intent_keywords[intent] = list(processed_keywords)
            
            # Process lemmas if spaCy model is available
            if self.nlp:
                logger.info(f"Dynamic Intent '{intent}': Starting lemmatization of {len(processed_keywords)} keywords")
                lemmatized_count = 0
                
                for keyword in processed_keywords:
                    if keyword not in self.keyword_lemmas_cache:
                        try:
                            self.keyword_lemmas_cache[keyword] = self._process_keyword(keyword, lemmatize=True)
                            logger.debug(f"Dynamic Intent '{intent}': Keyword '{keyword}' lemmatized: {self.keyword_lemmas_cache[keyword]}")
                            lemmatized_count += 1
                        except Exception as e:
                            logger.error(f"Dynamic Intent '{intent}': Error lematizing keyword '{keyword}': {str(e)}")
                            self.keyword_lemmas_cache[keyword] = keyword.lower().split()
                
                logger.info(f"Dynamic Intent '{intent}': Lematization completed - {lemmatized_count} new keywords lemmatized")
            else:
                logger.warning(f"Dynamic Intent '{intent}': spaCy model not available for lematization")

            return True
            
        except Exception as e:
            logger.error(f"Error updating keywords for intent '{intent}': {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def _preprocess_static_keywords(self) -> None:
        """
        Preprocess and cache lemmas for all static keywords.
        Also applies keyword enrichment for static intents.
        """
        logger.info(f"Preprocessing static keywords for lemmatization")
        
        # Process lemmas directly to avoid recursion during initialization
        for intent, keywords in self.intent_keywords.items():
            # 1. Extract keywords from entities related to this intent
            enriched_keywords = set(keywords)
            entity_keywords = self._extract_keywords_from_entities(intent)
            enriched_keywords.update(entity_keywords)
            
            # 2. Decompose sentences into individual words
            individual_words = self._decompose_to_individual_words(enriched_keywords)
            enriched_keywords.update(individual_words)
            
            # 3. Enrich with N-grams
            ngrams = self._generate_ngrams(enriched_keywords)
            enriched_keywords.update(ngrams)
            
            logger.info(f"Dynamic Intent '{intent}': Original keywords: {len(keywords)}, Enriched: {len(enriched_keywords)}")
            
            # Update the list of keywords with the enriched set
            self.intent_keywords[intent] = list(enriched_keywords)
            
            # Process lemmas
            for keyword in self.intent_keywords[intent]:
                if keyword not in self.keyword_lemmas_cache:
                    try:
                        keyword_doc = self.nlp(keyword)
                        self.keyword_lemmas_cache[keyword] = [token.lemma_ for token in keyword_doc]
                        logger.debug(f"Dynamic Intent '{intent}': Keyword '{keyword}' lemmatized: {self.keyword_lemmas_cache[keyword]}")
                    except Exception as e:
                        logger.error(f"Dynamic Intent '{intent}': Error lematizing keyword '{keyword}': {str(e)}")
                        # Fallback para texto bruto em caso de erro
                        self.keyword_lemmas_cache[keyword] = keyword.lower().split()

        logger.info(f"Static Intent '{intent}': Lematization completed - {len(self.keyword_lemmas_cache[keyword])} keywords lemmatized")
    
    def _extract_keywords_from_entities(self, intent: str) -> Set[str]:
        """
        Extract keywords from entities related to an intent.
        
        Args:
            intent: Intent name
            
        Returns:
            Set[str]: Set of keywords extracted from entities
        """
        logger.info(f"Dynamic Intent '{intent}': Verify entities for intent '{intent}'")
        logger.debug(f"Dynamic Intent '{intent}': Current mapping: {self.entity_intent_map}")
        
        keywords = set()
        
        # Find entities mapped to this intent
        related_entities = [entity_type for entity_type, mapped_intent in self.entity_intent_map.items() 
                           if mapped_intent == intent]
        
        logger.debug(f"Dynamic Intent '{intent}': Found entities for intent '{intent}': {related_entities}")
        
        # Extract keywords from entities
        for entity_type in related_entities:
            # Add the entity name itself as a keyword
            if isinstance(entity_type, str) and len(entity_type) > 3:  # Avoid adding short acronyms or abbreviations
                # Remove common prefixes like INTENT_ or TYPE_
                clean_entity = entity_type
                for prefix in ["INTENT_", "TYPE_", "ENTITY_"]:
                    if clean_entity.startswith(prefix):
                        clean_entity = clean_entity[len(prefix):]
                        logger.debug(f"Dynamic Intent '{intent}': Removed prefix from '{entity_type}' to '{clean_entity}'")
                
                # Convert from snake_case or SCREAMING_SNAKE_CASE to words
                words = clean_entity.lower().replace('_', ' ').split()
                keywords.update(words)
                logger.debug(f"Dynamic Intent '{intent}': Added individual words: {words}")
                
                # Add the complete entity also
                keywords.add(clean_entity.lower().replace('_', ' '))
                logger.debug(f"Dynamic Intent '{intent}': Added complete entity: {clean_entity.lower().replace('_', ' ')}")
        
        logger.debug(f"Dynamic Intent '{intent}': Extracted keywords from entities: {keywords}")
        return keywords
    
    def _decompose_to_individual_words(self, keywords: Set[str]) -> Set[str]:
        """
        Decompose sentences into individual words, filtering out very short words or stopwords.
        Utiliza o spaCy para identificar stopwords e fazer a decomposição de forma mais eficiente.
        
        Args:
            keywords: Set of keywords
            
        Returns:
            Set[str]: Set of individual words
        """
        logger.info(f"Starting decomposition of {len(keywords)} keywords")
        individual_words = set()
        
        for keyword in keywords:
            if not keyword or not isinstance(keyword, str):
                continue
                
            # Uses the _process_keyword function without lemmatization
            terms = self._process_keyword(keyword, lemmatize=False)
            
            if terms:
                logger.debug(f"_decompose_to_individual_words: keyword '{keyword}' decomposed into: {terms}")
                individual_words.update(terms)
        
        logger.info(f"Total of {len(individual_words)} individual words extracted")
        return individual_words
    
    def _generate_ngrams(self, keywords: Set[str], max_n: int = 3) -> Set[str]:
        """
        Generate N-grams from existing keywords.
        Utiliza o spaCy para gerar n-gramas linguísticamente relevantes quando disponível.
        
        Args:
            keywords: Set of keywords
            max_n: Maximum size of N-grams to be generated
            
        Returns:
            Set[str]: Set of generated N-grams
        """
        logger.info(f"Starting n-gram generation for {len(keywords)} keywords")
        ngrams = set()
        
        # Check if spaCy model is available
        if not self.nlp:
            logger.warning(f"spaCy model not available, using alternative method")
            
            # Convert to list to facilitate indexing
            keywords_list = list(keywords)
            
            # Generate N-grams only for phrases that already have at least 2 words
            multi_word_count = 0
            for keyword in keywords_list:
                words = keyword.split()
                
                # Only process phrases with at least 2 words
                if len(words) >= 2:
                    multi_word_count += 1
                    keyword_ngrams = []
                    # Generate all possible N-grams up to max_n
                    for n in range(2, min(len(words), max_n) + 1):
                        for i in range(len(words) - n + 1):
                            ngram = ' '.join(words[i:i+n])
                            ngrams.add(ngram)
                            keyword_ngrams.append(ngram)
                    
                    if keyword_ngrams:
                        logger.debug(f"Generated n-grams for '{keyword}': {keyword_ngrams}")
            
            logger.info(f"{multi_word_count} keywords with multiple words processed")
        else:
            # Use spaCy for generation of linguistically relevant n-grams
            
            processed_count = 0
            for keyword in keywords:
                # Process the keyword with spaCy
                doc = self.nlp(keyword)
                
                # 1. Add syntactic chunks (nominal phrases)
                chunks = list(doc.noun_chunks)
                chunk_texts = [chunk.text for chunk in chunks if len(chunk) > 1]
                
                # 2. Add combinations of adjacent tokens without stopwords
                tokens = [token for token in doc if not token.is_stop and not token.is_punct]
                
                # Generate n-grams based on relevant tokens
                token_ngrams = []
                if len(tokens) >= 2:
                    for n in range(2, min(len(tokens), max_n) + 1):
                        for i in range(len(tokens) - n + 1):
                            # Verify if tokens are adjacent in the original text
                            if tokens[i+n-1].i - tokens[i].i == n-1:
                                ngram = ' '.join([token.text for token in tokens[i:i+n]])
                                token_ngrams.append(ngram)
                
                # 3. Add combinations of entities and important terms
                entity_ngrams = [ent.text for ent in doc.ents if len(ent) > 1]
                
                # Combine all generated n-grams
                keyword_ngrams = chunk_texts + token_ngrams + entity_ngrams
                
                if keyword_ngrams:
                    processed_count += 1
                    ngrams.update(keyword_ngrams)
                    logger.debug(f"Generated n-grams with spaCy for '{keyword}': {keyword_ngrams}")
            
            logger.info(f"{processed_count} keywords processed with spaCy")
        
        logger.info(f"Total of {len(ngrams)} n-grams generated")
        return ngrams
    
    def score_intents(self, text: str, doc, entity_matches: List[Tuple[str, str]], 
                     dependency_matches: Dict[str, int], context: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """
        Calculate score for different intents based on multiple evidences.
        
        Args:
            text: Original text
            doc: spaCy processed document
            entity_matches: List of tuples (entity, type) found by Entity Ruler
            dependency_matches: Dictionary with intents and number of matches from Dependency Matcher
            context: Conversation context (optional)
            
        Returns:
            Dict[str, float]: Dictionary with intents and their scores
        """
        logger.info(f"Starting score calculation for text: '{text}'")
        logger.info(f"Entities found: {entity_matches}")
        if dependency_matches:
            logger.info(f"Dependency patterns: {dependency_matches}")
        if context:
            logger.info(f"Context: {context}")
            
        logger.info(f"Entity mapping to intents: {self.entity_intent_map}")
            
        logger.info(f"Keywords for all intents: {self.intent_keywords}")
            
        scores = {}
        
        # 1. Score based on entities from Entity Ruler
        logger.info(f"Calculando score baseado em entidades do Entity Ruler")
        for entity, entity_type in entity_matches:
            if entity_type in self.entity_intent_map:
                intent = self.entity_intent_map[entity_type]
                if intent in scores:
                    scores[intent] += self.weights["entity_ruler"]
                    logger.info(f"Entity '{entity}' of type '{entity_type}' incremented score for '{intent}': +{self.weights['entity_ruler']} (total: {scores[intent]})")
                else:
                    scores[intent] = self.weights["entity_ruler"]
                    logger.info(f"Entity '{entity}' of type '{entity_type}' started score for '{intent}': {scores[intent]}")
            # If no direct mapping, check if it's a medical entity type
            elif entity_type == "termo_medico":
                logger.info(f"Encontrada entidade '{entity}' do tipo '{entity_type}', buscando intenções relacionadas a termos médicos")
                
                # Identify intents related to medical terms in the mapping
                medical_entity_types = ["medical_concept", "term", "conceito_médico", "explanation"]
                medical_intents = set()
                
                # Search for all intents associated with medical entities
                for key, value in self.entity_intent_map.items():
                    if any(med_type in key.lower() for med_type in medical_entity_types):
                        medical_intents.add(value)
                        logger.info(f"Intent '{value}' identified as related to medical terms via '{key}'")
                
                # If no related intents found, use concept_explanation as fallback
                if not medical_intents:
                    medical_intents.add("concept_explanation")
                    logger.info(f"No related intents found for medical terms, using 'concept_explanation' as fallback")
                
                # Check if there is an explanation verb in the text
                has_explanation_verb = False
                explanation_verb_text = ""
                if self.nlp:
                    doc = self.nlp(text)
                    explanation_verbs = ["explicar", "definir", "descrever", "detalhar", "conceituar"]
                    
                    for token in doc:
                        if token.lemma_ in explanation_verbs:
                            has_explanation_verb = True
                            explanation_verb_text = token.text
                            logger.info(f"Encontrado verbo de explicação '{token.text}' com termo médico '{entity}'")
                            break
                
                # Process each related intent to medical terms
                for med_intent in medical_intents:
                    # Define base weight
                    weight = 1.5  # Base weight for medical terms
                    
                    # If explanation verb found, increase weight
                    if has_explanation_verb:
                        weight = 3.0  # Increase weight for combination of explanation verb + medical term
                        logger.info(f"Applying boost for intent '{med_intent}' due to combination of explanation verb '{explanation_verb_text}' + medical term '{entity}'")
                    
                    # Adjust score for this intent
                    if med_intent in scores:
                        old_score = scores[med_intent]
                        scores[med_intent] += self.weights["entity_ruler"] * weight
                        logger.info(f"Adjusting score for '{med_intent}' due to entity '{entity}' of type '{entity_type}': {old_score} -> {scores[med_intent]}")
                    else:
                        scores[med_intent] = self.weights["entity_ruler"] * weight
                        logger.info(f"Starting score for '{med_intent}' due to entity '{entity}' of type '{entity_type}': {scores[med_intent]}")
            else:
                logger.info(f"Entity '{entity}' of type '{entity_type}' not mapped to any intent")
                
        logger.info(f"Scores after entities: {scores}")

        
        # 2. Score based on dependency patterns
        logger.info(f"Calculating score based on dependency patterns")
        for intent, count in dependency_matches.items():
            if intent in scores:
                scores[intent] += self.weights["dependency"] * count
                logger.info(f"Patterns of dependency incremented score for '{intent}': +{self.weights['dependency'] * count} (total: {scores[intent]})")
            else:
                scores[intent] = self.weights["dependency"] * count
                logger.info(f"Patterns of dependency started score for '{intent}': {scores[intent]}")
                
        # Check if there are patterns of dependency related to literature summaries
        literature_related_patterns = [intent for intent in dependency_matches.keys() 
                                     if "literature" in intent.lower() or "summary" in intent.lower()]
        if literature_related_patterns:
            logger.info(f"Patterns of dependency related to literature summaries: {literature_related_patterns}")
        else:
            logger.info(f"No patterns of dependency related to literature summaries found")
                
        logger.info(f"Scores after dependency patterns: {scores}")
        
        # 3. Keyword-based scoring
        logger.info(f"Analyzing keywords for text: '{text}'")
        
        # The system now handles all intents dynamically, without specific checks for particular intents
        logger.info(f"Analyzing keywords for all intents")
        
        # 3. Keyword-based scoring
        logger.info(f"Calculating keyword-based scoring")
        self._score_keywords(text, doc, scores, logger)
        
        # Add generic "outro" intent with low score
        if "outro" not in scores:
            scores["outro"] = 0.1
            logger.info(f"Adding generic 'outro' intent with low score: 0.1")
        else:
            logger.info(f"Intent 'outro' already has score: {scores['outro']}")
        
        # Ensure that all possible intents have a score
        logger.info(f"Ensuring that all possible intents have a score")
        for intent in self.intent_keywords.keys():
            if intent not in scores:
                scores[intent] = 0.0
                logger.info(f"Starting score for intent '{intent}': 0.0")
            
        # Apply softmax normalization with temperature to smooth out the scores
        # and prevent a single evidence from dominating the system
        if scores:
            # Save original scores for logging
            original_scores = scores.copy()
            logger.info(f"Original scores before normalization: {original_scores}")
            
            # Temperature parameter: lower values increase confidence in the highest score,
            # higher values smooth out the differences
            temperature = 0.8
            
            # Apply softmax with temperature to smooth out the scores
            # and prevent a single evidence from dominating the system
            # 1. Get all scores
            score_values = list(scores.values())
            
            # 2. Avoid overflow with very high scores by subtracting the maximum
            max_score = max(score_values)
            
            # 3. Calculate the softmax denominator
            exp_sum = sum(math.exp((score - max_score) / temperature) for score in score_values)
            
            # 4. Apply softmax to each score
            for intent in scores:
                scores[intent] = math.exp((scores[intent] - max_score) / temperature) / exp_sum
            
            logger.info(f"Scores after softmax normalization (temp={temperature}): {scores}")
            
            # Check which intent has the highest score
            max_intent = max(scores.items(), key=lambda x: x[1])
            logger.info(f"Intent with highest score after normalization: '{max_intent[0]}' with {max_intent[1]}")
            
            # Check if normalization changed the winning intent
            original_max_intent = max(original_scores.items(), key=lambda x: x[1])
            if original_max_intent[0] != max_intent[0]:
                logger.info(f"Alert: Normalization changed the winning intent from '{original_max_intent[0]}' to '{max_intent[0]}'")
        
        logger.info(f"Final scores: {scores}")
        return scores
        
    def _score_keywords(self, text: str, doc, scores: Dict[str, float], logger) -> None:
        """
        Calculate scores based on keywords for all intents.
        
        Args:
            text: Original text
            doc: spaCy processed document
            scores: Dictionary of scores to be updated
            logger: Logger for diagnostics
        """
        
        # The system now handles all intents dynamically, without specific checks for particular intents
        logger.info(f"[DIAGNÓSTICO] Analisando palavras-chave para todas as intenções")
        
        # Extrair relações verbo-objeto do texto do usuário para análise contextual
        text_verb_objects = []
        if doc:
            for token in doc:
                if token.pos_ == "VERB":
                    # Encontrar objetos diretos deste verbo
                    for child in token.children:
                        if child.dep_ in ["dobj", "obj", "attr", "pobj"] and child.pos_ in ["NOUN", "PROPN"]:
                            text_verb_objects.append((token.lemma_, child.lemma_))
                            logger.info(f"Encontrada relação verbo-objeto: {token.lemma_} -> {child.lemma_}")
        
        # Log das relações verbo-objeto encontradas
        if text_verb_objects:
            logger.info(f"Verbo-objeto relations found in text: {text_verb_objects}")
        else:
            logger.info("No verbo-objeto relations found in text")
        
        # Analyze all intents and their keywords
        for intent, keywords in self.intent_keywords.items():
            # Counter to track the number of keywords found per intent
            keyword_matches = []
            
            # 1. Verify exact keyword matches
            for keyword in keywords:
                match_found = False
                
                # Check using lemmatization if available
                if self.nlp and doc and keyword in self.keyword_lemmas_cache:
                    keyword_lemmas = self.keyword_lemmas_cache[keyword]
                    
                    # Filter stopwords from text lemmas to give more weight to significant words
                    text_lemmas = [token.lemma_ for token in doc if not token.is_stop]
                    
                    # Filter stopwords from keyword lemmas
                    significant_keyword_lemmas = []
                    for kw_lemma in keyword_lemmas:
                        # Check if the lemma is a stopword using the spaCy vocabulary
                        token = self.nlp(kw_lemma)[0]  # Create a token to check if it's a stopword
                        if not token.is_stop:
                            significant_keyword_lemmas.append(kw_lemma)
                    
                    # If no significant lemmas after filtering stopwords, use the original ones
                    # This prevents keywords composed only of stopwords from being completely ignored
                    if not significant_keyword_lemmas:
                        significant_keyword_lemmas = keyword_lemmas
                    
                    # Check if all significant lemmas of the keyword are in the text
                    if all(kw_lemma in text_lemmas for kw_lemma in significant_keyword_lemmas):
                        match_found = True
                        logger.info(f"Keywords '{keyword}' found by lemmatization for intent '{intent}' (filtered stopwords)")
                        
                        # Apply reduced weight if the original keyword had many stopwords
                        if len(significant_keyword_lemmas) < len(keyword_lemmas):
                            logger.info(f"Keyword '{keyword}' contains stopwords, applying reduced weight")
                            # The weight will be proportional to the number of significant words
                            weight_factor = len(significant_keyword_lemmas) / len(keyword_lemmas)
                            self.weights["keyword"] *= max(0.5, weight_factor)  # Minimum 50% of the original weight
                else:
                    # Fallback for raw text comparison
                    if keyword.lower() in text.lower():
                        match_found = True
                        logger.info(f"Keywords '{keyword}' found by raw text comparison for intent '{intent}'")
                
                if match_found:
                    keyword_matches.append(keyword)
                    if intent in scores:
                        scores[intent] += self.weights["keyword"]
                        logger.info(f"Keywords '{keyword}' incremented score for '{intent}': +{self.weights['keyword']} (total: {scores[intent]})")
                    else:
                        scores[intent] = self.weights["keyword"]
                        logger.info(f"Keywords '{keyword}' started score for '{intent}': {scores[intent]}")
            
            # Apply bonus for multiple keywords of the same intent
            if len(keyword_matches) >= 2 and intent in scores:
                # Bonus increases with the number of keywords, but with decreasing returns
                bonus = self.weights["keyword"] * (1 + 0.3 * min(len(keyword_matches), 5))
                scores[intent] += bonus
                logger.info(f"Bonus applied for {len(keyword_matches)} keywords of intent '{intent}': +{bonus} (total: {scores[intent]})")
                logger.info(f"Keywords found: {keyword_matches}")

            
            # 2. Check partial matches for compound keywords
            for keyword in keywords:
                # Check only compound keywords with multiple words
                if ' ' in keyword:
                    # Use lemmatization if available
                    if self.nlp and doc and keyword in self.keyword_lemmas_cache:
                        keyword_lemmas = self.keyword_lemmas_cache[keyword]
                        
                        # Filter stopwords from text lemmas
                        text_lemmas = [token.lemma_ for token in doc if not token.is_stop]
                        
                        # Filter stopwords from keyword lemmas
                        significant_keyword_lemmas = []
                        for kw_lemma in keyword_lemmas:
                            token = self.nlp(kw_lemma)[0]  # Create a token to check if it's a stopword
                            if not token.is_stop:
                                significant_keyword_lemmas.append(kw_lemma)
                        
                        # If no significant lemmas, use the original ones
                        if not significant_keyword_lemmas:
                            significant_keyword_lemmas = keyword_lemmas
                        
                        # Check for matches only with significant lemmas
                        matching_significant_lemmas = [lemma for lemma in significant_keyword_lemmas if lemma in text_lemmas]
                        
                        # Analyze the verb-object structure of the keyword
                        keyword_doc = self.nlp(keyword)
                        keyword_verb_objects = []
                        
                        # Extract verb-object relations from the keyword
                        for token in keyword_doc:
                            if token.pos_ == "VERB":
                                for child in token.children:
                                    if child.dep_ in ["dobj", "obj", "attr", "pobj"] and child.pos_ in ["NOUN", "PROPN"]:
                                        keyword_verb_objects.append((token.lemma_, child.lemma_))
                        
                        # If the keyword has verb-object structure, check if it exists in the text
                        has_matching_verb_object = False
                        if keyword_verb_objects:
                            for kw_verb, kw_obj in keyword_verb_objects:
                                # Check if any verb-object relation in the text matches the keyword
                                for text_verb, text_obj in text_verb_objects:
                                    if kw_verb == text_verb:
                                        # Check if the object also matches or is semantically related
                                        # (more flexible verification to allow variations)
                                        if kw_obj == text_obj or text_obj.startswith(kw_obj) or kw_obj.startswith(text_obj):
                                            has_matching_verb_object = True
                                            logger.info(f"Found exact verb-object match: {kw_verb}->{kw_obj} with {text_verb}->{text_obj}")
                                            break
                                        else:
                                            # Partial verb match, but different objects
                                            logger.info(f"Verb match ({kw_verb}), but different objects: {kw_obj} vs {text_obj}")
                            
                            # If the keyword has verb-object structure but was not found in the text, skip
                            if keyword_verb_objects and not has_matching_verb_object:
                                logger.info(f"Keyword '{keyword}' has verb-object structure, but not found in the text - skipping partial match")
                                continue
                        
                        # Require at least one significant word in the matches
                        if matching_significant_lemmas and len(matching_significant_lemmas) / len(significant_keyword_lemmas) >= 0.4:
                            logger.info(f"Partial match with significant terms for keyword '{keyword}': {matching_significant_lemmas}")
                            
                            # Score proportional to the number of significant words matched
                            match_ratio = len(matching_significant_lemmas) / len(significant_keyword_lemmas)
                            
                            # Bonus for almost complete matches
                            if match_ratio >= 0.7:
                                bonus_factor = 1.5  # 50% bonus for strong matches
                            elif match_ratio >= 0.5:
                                bonus_factor = 1.2  # 20% bonus for moderate matches
                            else:
                                bonus_factor = 1.0
                            
                            # Check if the keyword has verb-object structure
                            keyword_doc = self.nlp(keyword)
                            
                            # Check if the keyword has verb and noun
                            has_verb = any(token.pos_ == "VERB" for token in keyword_doc)
                            has_noun = any(token.pos_ == "NOUN" or token.pos_ == "PROPN" for token in keyword_doc)
                            
                            # If the keyword has verb-object structure, check if it exists in the text
                            if has_verb and has_noun:
                                # Extract verbs and objects from the keyword
                                keyword_verbs = [token.lemma_ for token in keyword_doc if token.pos_ == "VERB"]
                                keyword_nouns = [token.lemma_ for token in keyword_doc if token.pos_ in ["NOUN", "PROPN"]]
                                
                                # Check if the verbs and objects of the keyword are present in the text verb-object relations
                                verb_object_match = False
                                perfect_match = False
                                matched_object = None
                                
                                for kw_verb in keyword_verbs:
                                    for kw_noun in keyword_nouns:
                                        for text_verb, text_obj in text_verb_objects:
                                            # Check for exact or partial match
                                            if kw_verb == text_verb and (kw_noun == text_obj or text_obj.startswith(kw_noun) or kw_noun.startswith(text_obj)):
                                                verb_object_match = True
                                                matched_object = text_obj
                                                logger.info(f"Verb-object match found: {kw_verb}->{kw_noun} with {text_verb}->{text_obj}")
                                                
                                                # Check if there is a perfect match (verb and object are exact)
                                                if kw_verb == text_verb and kw_noun == text_obj:
                                                    perfect_match = True
                                                    logger.info(f"Perfect verb-object match: {kw_verb}->{kw_noun}")
                                                break
                                
                                # Adjust the bonus_factor based on the quality of the verb-object match
                                if not verb_object_match:
                                    # If there is no verb-object match, drastically reduce the score
                                    logger.info(f"Keyword '{keyword}' has verb-object structure, but no match found in the text - drastically reducing score")
                                    bonus_factor = 0.05  # drastically reduce the score
                                elif perfect_match:
                                    # If there is a perfect match, significantly increase the score
                                    bonus_factor = 2.5  # significantly increase the score
                                    logger.info(f"Perfect verb-object match for '{intent}' - applying significant boost")
                                    
                                    # Generic approach: check if the object corresponds semantically to the intent
                                    # Extract key nouns from the intent (ignoring generic action verbs)
                                    intent_keywords = self.intent_keywords.get(intent, [])
                                    intent_nouns = []
                                    
                                    # Process each intent keyword to extract relevant nouns
                                    for kw in intent_keywords:
                                        if self.nlp:
                                            kw_doc = self.nlp(kw)
                                            # Extract nouns that are not generic action verbs
                                            for token in kw_doc:
                                                if token.pos_ in ["NOUN", "PROPN"] and token.lemma_ not in ["listar", "mostrar", "exibir", "ver"]:
                                                    intent_nouns.append(token.lemma_)
                                        else:
                                            # Fallback if spaCy is not available
                                            words = kw.lower().split()
                                            for word in words:
                                                if word not in ["listar", "liste", "mostrar", "mostre", "exibir", "exiba", "ver"]:
                                                    intent_nouns.append(word)
                                    
                                    # Remove duplicates and normalize
                                    intent_nouns = list(set(intent_nouns))
                                    
                                    # Check if the object corresponds to any characteristic noun of the intent
                                    semantic_match = False
                                    if matched_object:
                                        for noun in intent_nouns:
                                            if matched_object == noun or matched_object.startswith(noun) or noun.startswith(matched_object):
                                                semantic_match = True
                                                logger.info(f"Objeto '{matched_object}' corresponde semanticamente ao substantivo '{noun}' da intenção '{intent}'")
                                                break
                                    
                                    if semantic_match:
                                        bonus_factor = 3.0  # Boost extra for semantic matches
                                        logger.info(f"Objeto '{matched_object}' corresponde semanticamente à intenção '{intent}' - aplicando boost extra")
                            
                            match_score = self.weights["keyword"] * match_ratio * bonus_factor
                            
                            if intent in scores:
                                scores[intent] += match_score
                                logger.info(f"Partial match by lemmatization incremented score for '{intent}': +{match_score} (total: {scores[intent]})")
                            else:
                                scores[intent] = match_score
                                logger.info(f"Partial match by lemmatization started score for '{intent}': {scores[intent]}")
                    else:
                        # Fallback for raw text comparison
                        keyword_parts = keyword.lower().split()
                        text_lower = text.lower()
                        
                        # Check if at least 2 words of the keyword are present in the text
                        # Reduced threshold to 40% to capture more partial matches
                        matching_parts = [part for part in keyword_parts if part in text_lower]
                        if len(matching_parts) >= 2 and len(matching_parts) / len(keyword_parts) >= 0.4:
                            logger.info(f"Partial match for keyword '{keyword}': {matching_parts}")
                            
                            # Score proportional to the ratio of matching parts with a multiplication factor
                            match_ratio = len(matching_parts) / len(keyword_parts)
                            
                            # Bonus for almost complete matches
                            if match_ratio >= 0.7:
                                bonus_factor = 1.5  # 50% bonus for strong matches
                            elif match_ratio >= 0.5:
                                bonus_factor = 1.2  # 20% bonus for moderate matches
                            else:
                                bonus_factor = 1.0
                                
                            match_score = self.weights["keyword"] * match_ratio * bonus_factor
                            
                            if intent in scores:
                                scores[intent] += match_score
                                logger.info(f"Partial match by lemmatization incremented score for '{intent}': +{match_score} (total: {scores[intent]})")
                            else:
                                scores[intent] = match_score
                                logger.info(f"Partial match by lemmatization started score for '{intent}': {scores[intent]}")
            
            # 3. Check individual significant words for each intent
            # Extract significant words from intent keywords
            significant_words = set()
            
            # Use lemmatization if available
            if self.nlp and doc:
                for keyword in keywords:
                    if keyword in self.keyword_lemmas_cache:
                        # Add only significant lemmas (with more than 3 characters)
                        significant_words.update([lemma for lemma in self.keyword_lemmas_cache[keyword] if len(lemma) > 3])
            else:
                # Fallback for raw text
                for keyword in keywords:
                    # Split compound keywords
                    parts = keyword.lower().split()
                    # Add only significant words (with more than 3 characters)
                    significant_words.update([part for part in parts if len(part) > 3])
            
            # Check significant words in the text
            found_significant_words = []
            
            # Use lemmatization if available
            if self.nlp and doc:
                text_lemmas = [token.lemma_ for token in doc]
                for word in significant_words:
                    if word in text_lemmas:
                        found_significant_words.append(word)
                        logger.info(f"Significant word '{word}' found by lemmatization for intent '{intent}'")
            else:
                # Fallback for raw text
                text_lower = text.lower()
                found_significant_words = [word for word in significant_words if word in text_lower]
            
            # Use the list of found significant words
            matching_significant_words = found_significant_words
            
            # If we find at least one significant word, assign partial score
            if matching_significant_words:
                # Score proportional to the number of significant words found
                # with a maximum limit increased to value more significant words
                match_ratio = min(len(matching_significant_words) / len(significant_words), 0.9) if significant_words else 0
                
                # Increased to 120% of normal weight to give more relevance to significant words
                match_score = self.weights["keyword"] * match_ratio * 1.2
                
                # Additional bonus when multiple significant words are found
                if len(matching_significant_words) >= 2:
                    match_score *= (1 + 0.1 * min(len(matching_significant_words), 5))  # Up to 50% bonus for 5+ words
                
                if match_score > 0:
                    logger.info(f"Significant words found for '{intent}': {matching_significant_words}")
                    
                    if intent in scores:
                        scores[intent] += match_score
                        logger.info(f"Significant words incremented score for '{intent}': +{match_score} (total: {scores[intent]})")
                    else:
                        scores[intent] = match_score
                        logger.info(f"Significant words started score for '{intent}': {scores[intent]}")
        
        # Add generic "outro" intent with low score
        if "outro" not in scores:
            scores["outro"] = 0.1
            logger.info(f"Adding generic 'outro' intent with low score: 0.1")
        else:
            logger.info(f"Intent 'outro' already has score: {scores['outro']}")
        
        # Ensure all possible intents have a score
        logger.info(f"Ensuring all intents have a score")
        for intent in self.intent_keywords.keys():
            if intent not in scores:
                scores[intent] = 0.0
                logger.info(f"Starting score for intent '{intent}': 0.0")
            
        # Apply softmax normalization with temperature to smooth out the scores
        # and prevent a single evidence from dominating the system
        if scores:
            # Save original scores for logging
            original_scores = scores.copy()
            logger.info(f"Original scores before normalization: {original_scores}")
            
            # Temperature parameter: lower values increase confidence in the highest score,
            # higher values smooth out the differences
            temperature = 0.8
            
            # Apply softmax with temperature to smooth out the scores
            # and prevent a single evidence from dominating the system
            # 1. Get all scores
            score_values = list(scores.values())
            
            # 2. Avoid overflow with very high scores by subtracting the maximum
            max_score = max(score_values)
            
            # 3. Calculate the softmax denominator
            exp_sum = sum(math.exp((score - max_score) / temperature) for score in score_values)
            
            # 4. Apply softmax to each score
            for intent in scores:
                scores[intent] = math.exp((scores[intent] - max_score) / temperature) / exp_sum
            
            logger.info(f"Scores after softmax normalization (temp={temperature}): {scores}")
            
            # Check which intent has the highest score
            max_intent = max(scores.items(), key=lambda x: x[1])
            logger.info(f"Intent with highest score after normalization: '{max_intent[0]}' with {max_intent[1]}")
            
            # Check if normalization changed the winning intent
            original_max_intent = max(original_scores.items(), key=lambda x: x[1])
            if original_max_intent[0] != max_intent[0]:
                logger.info(f"Alert: Normalization changed the winning intent from '{original_max_intent[0]}' to '{max_intent[0]}'")
        
        logger.info(f"Final scores: {scores}")
        return scores
        
    def _adjust_scores_based_on_entities(self, scores: Dict[str, float], entity_matches: List[Tuple[str, str]], text: str) -> None:
        """
        Adjusts scores based on the presence of entities in the text.
        A generic approach without specific treatments for particular intents.
        
        Args:
            scores: Dictionary with intents and their scores
            entity_matches: List of tuples (entity, type) found by Entity Ruler
            text: Text message
        """
        logger.info("Adjusting scores based on entities")
        logger.info(f"Scores before adjustments: {scores}")
        logger.info(f"Entities detected: {entity_matches}")
        logger.info(f"Text message: '{text}'")
        logger.info(f"Mapeamento de entidades para intenções: {self.entity_intent_map}")
        
        # Check if the user is explicitly asking for relationships
        relationship_keywords = ["relacionamento", "relação", "relacionamentos", "relações", "conexão", "ligação"]
        has_relationship_keyword = any(keyword in text.lower() for keyword in relationship_keywords)
        
        if has_relationship_keyword and "relacionamentos" in scores:
            logger.info("User explicitly asking for relationships, prioritizing 'relacionamentos' intent")
            # Boost the relationship intent score
            scores["relacionamentos"] = max(scores.get("relacionamentos", 0), 15.0)  # Higher than the default entity_ruler weight (10.0)
            logger.info(f"Relationship intent score adjusted to: {scores['relacionamentos']}")
        
        # Group entities by type for generic analysis
        entity_types = {}
        for entity, entity_type in entity_matches:
            if entity_type not in entity_types:
                entity_types[entity_type] = []
            entity_types[entity_type].append(entity)
        
        # Log entity types found
        for entity_type, entities in entity_types.items():
            logger.info(f"Entity type '{entity_type}': {entities}")
        
        # Process intent entities (INTENT_*)
        intent_entities = [(entity, entity_type) for entity, entity_type in entity_matches 
                          if entity_type.startswith("INTENT_")]
        
        if intent_entities:
            logger.info(f"Intent entities found: {intent_entities}")
            
            for entity, entity_type in intent_entities:
                # Check if we have a mapping for this entity
                if entity_type in self.entity_intent_map:
                    intent_name = self.entity_intent_map[entity_type]
                    logger.info(f"Entity intent mapped: {entity_type} -> {intent_name}")
                    
                    # Increase score for this intent
                    if intent_name in scores:
                        old_score = scores[intent_name]
                        scores[intent_name] += self.weights["entity_ruler"] * 1.5
                        logger.info(f"Incrementing score for '{intent_name}': {old_score} -> {scores[intent_name]}")
                    else:
                        scores[intent_name] = self.weights["entity_ruler"] * 1.5
                        logger.info(f"Starting score for '{intent_name}': {scores[intent_name]}")
                    
                    # Reduce score for 'outro' if high
                    if "outro" in scores and scores["outro"] > 0.1:
                        old_score = scores["outro"]
                        scores["outro"] = 0.1
                        logger.info(f"Reducing score for 'outro': {old_score} -> {scores['outro']}")
                else:
                    # Try to find alternative mappings based on similarity
                    # Remove common prefixes like INTENT_ to search for matches
                    normalized_entity_type = entity_type
                    if normalized_entity_type.startswith("INTENT_"):
                        normalized_entity_type = normalized_entity_type[7:]
                    
                    # Check if any key in the mapping contains the normalized type
                    potential_matches = []
                    for key in self.entity_intent_map.keys():
                        normalized_key = key
                        if normalized_key.startswith("INTENT_"):
                            normalized_key = normalized_key[7:]
                        
                        # Check if there is significant overlap between the strings
                        if normalized_entity_type.lower() in normalized_key.lower() or \
                           normalized_key.lower() in normalized_entity_type.lower():
                            potential_matches.append((key, self.entity_intent_map[key]))
                    
                    if potential_matches:
                        logger.info(f"Found potential mappings for '{entity_type}': {potential_matches}")
                        
                        # Use the first potential mapping
                        intent_name = potential_matches[0][1]
                        if intent_name in scores:
                            old_score = scores[intent_name]
                            scores[intent_name] += self.weights["entity_ruler"]
                            logger.info(f"Incrementing score for '{intent_name}' (approximate mapping): {old_score} -> {scores[intent_name]}")
                        else:
                            scores[intent_name] = self.weights["entity_ruler"]
                            logger.info(f"Starting score for '{intent_name}' (approximate mapping): {scores[intent_name]}")
                    else:
                        logger.info(f"Entity intent '{entity_type}' not mapped to any intent")
        else:
            logger.info(f"No intent entities (INTENT_*) found in text")
        
        # Process generic entities that are not intents
        for entity_type, entities in entity_types.items():
            # Skip intent entities (already processed) and the 'outro' entity
            if entity_type.startswith("INTENT_") or entity_type == "outro":
                continue
                
            # If it's an entity type mapped to an intent, adjust the score
            intent_name = None
            
            # Verificar mapeamento direto
            if entity_type in self.entity_intent_map:
                intent_name = self.entity_intent_map[entity_type]
                logger.info(f"Entity intent mapped: {entity_type} -> {intent_name}")
                
                # Increase score for this intent
                if intent_name in scores:
                    old_score = scores[intent_name]
                    scores[intent_name] += self.weights["entity_ruler"] * 1.5
                    logger.info(f"Incrementing score for '{intent_name}': {old_score} -> {scores[intent_name]}")
                else:
                    scores[intent_name] = self.weights["entity_ruler"] * 1.5
                    logger.info(f"Starting score for '{intent_name}': {scores[intent_name]}")
            
            # Se não houver mapeamento direto, verificar se é um tipo de entidade médica
            elif entity_type == "termo_medico":
                logger.info(f"Encontrada entidade do tipo '{entity_type}', buscando intenções relacionadas a termos médicos")
                
                # Identificar intenções relacionadas a termos médicos no mapeamento
                medical_entity_types = ["medical_concept", "term", "conceito_médico"]
                medical_intents = set()
                
                # Buscar todas as intenções associadas a entidades médicas
                for key, value in self.entity_intent_map.items():
                    if any(med_type in key.lower() for med_type in medical_entity_types):
                        medical_intents.add(value)
                        logger.info(f"Intenção '{value}' identificada como relacionada a termos médicos via '{key}'")
                
                # Se não encontrou nenhuma intenção relacionada, usar concept_explanation como fallback
                if not medical_intents:
                    medical_intents.add("concept_explanation")
                    logger.info(f"Nenhuma intenção relacionada a termos médicos encontrada, usando 'concept_explanation' como fallback")
                
                # Verificar se há um verbo de explicação no texto
                has_explanation_verb = False
                explanation_verb_text = ""
                if self.nlp:
                    doc = self.nlp(text)
                    explanation_verbs = ["explicar", "definir", "descrever", "detalhar", "conceituar"]
                    
                    for token in doc:
                        if token.lemma_ in explanation_verbs:
                            has_explanation_verb = True
                            explanation_verb_text = token.text
                            logger.info(f"Encontrado verbo de explicação '{token.text}' com termo médico")
                            break
                
                # Processar cada intenção relacionada a termos médicos
                for med_intent in medical_intents:
                    # Definir peso base
                    weight = 1.5  # Peso base para termos médicos
                    
                    # Se encontrou um verbo de explicação, aumentar o peso
                    if has_explanation_verb:
                        weight = 3.0  # Peso maior para combinação de verbo de explicação + termo médico
                        logger.info(f"Aplicando boost para intenção '{med_intent}' devido à combinação de verbo de explicação '{explanation_verb_text}' + termo médico")
                    
                    # Ajustar a pontuação para esta intenção
                    if med_intent in scores:
                        old_score = scores[med_intent]
                        scores[med_intent] += self.weights["entity_ruler"] * weight
                        logger.info(f"Ajustando pontuação para '{med_intent}' devido a entidade do tipo '{entity_type}': {old_score} -> {scores[med_intent]}")
                    else:
                        scores[med_intent] = self.weights["entity_ruler"] * weight
                        logger.info(f"Iniciando pontuação para '{med_intent}' devido a entidade do tipo '{entity_type}': {scores[med_intent]}")
                
                # Definir intent_name como None para não entrar no bloco abaixo
                intent_name = None
                
                # Reduce score for 'outro' if it's the only entity
                if len(entity_types) == 1 and "outro" in scores and scores["outro"] > 0.1:
                    old_score = scores["outro"]
                    scores["outro"] = 0.1
                    logger.info(f"Reducing score for 'outro' due to exclusive presence of entities of type '{entity_type}': {old_score} -> {scores['outro']}")
            
                
        # Check final scores after all adjustments
        logger.info(f"Final scores after adjustments based on entities: {scores}")
        
        logger.info(f"Adjustment of scores based on entities completed")

    
    def normalize_scores(self, scores: Dict[str, float]) -> Dict[str, float]:
        """
        Normalizes the scores to values between 0 and 1 using Min-Max Scaling.
        
        Min-Max Scaling formula: (x - min) / (max - min)
        
        In this implementation, we assume min=0 for all scores, so the formula
        simplifies to: x / max
        
        Special cases:
        - If all scores are 0, max is set to 1.0 to avoid division by zero
        - If max is 0, all scores will be set to 0.0
        
        Args:
            scores: Dictionary with intents and their scores
            
        Returns:
            Dict[str, float]: Dictionary with intents and normalized scores between 0 and 1
        """
        logger.info(f"Starting score normalization: {scores}")
        
        # Check if 'outro' is in the scores
        if "outro" in scores:
            logger.info(f"Score for 'outro' before normalization: {scores['outro']}")
        
        # Find the maximum score
        max_score = max(scores.values()) if scores else 1.0
        logger.info(f"Maximum score found: {max_score}")
        
        # Identify which intent has the maximum score
        max_intent = max(scores.items(), key=lambda x: x[1])[0] if scores else "none"
        logger.info(f"Intent with maximum score: '{max_intent}' with {max_score}")
        
        # If the maximum score is zero, use 1.0 to avoid division by zero
        if max_score == 0:
            max_score = 1.0
            logger.info(f"Maximum score is zero, using 1.0 to avoid division by zero")
        
        # Normalize scores
        normalized = {}
        for intent, score in scores.items():
            normalized[intent] = score / max_score
            logger.info(f"Normalizing score for '{intent}': {score} / {max_score} = {normalized[intent]}")
        
        logger.info(f"Final normalized scores: {normalized}")
        return normalized
        
    def update_entity_intent_mapping(self, entity_type: str, intent_name: str) -> bool:
        """
        Updates the entity intent mapping.
        
        Args:
            entity_type: Entity type (e.g., INTENT_EXPLANATION or termo_medico)
            intent_name: Intent name (e.g., explicar_termo)
            
        Returns:
            bool: True if the update was successful, False otherwise
        """
        try:
            if not entity_type or not intent_name:
                logger.warning("Entity type or intent name not provided")
                return False
                
            logger.info(f"Updating entity intent mapping: {entity_type} -> {intent_name}")
            
            # Prevent direct mapping from 'termo_medico' to 'personalized_care_plan'
            if entity_type == 'termo_medico' and intent_name == 'personalized_care_plan':
                logger.info(f"Prevented direct mapping from 'termo_medico' to 'personalized_care_plan'")
                return False
            
            # Normalize the entity type to ensure consistency
            normalized_entity = entity_type.upper() if entity_type.startswith("INTENT_") else entity_type
            
            # Verify current mapping before update
            if normalized_entity in self.entity_intent_map:
                old_intent = self.entity_intent_map[normalized_entity]
                if old_intent != intent_name:
                    logger.info(f"Updating existing mapping: {normalized_entity} -> {old_intent} to {intent_name}")
            
            # Update the mapping
            self.entity_intent_map[normalized_entity] = intent_name
            logger.debug(f"Mapped: {normalized_entity} -> {intent_name}")
            
            # If it's an intent entity, ensure the uppercase version is also mapped
            if normalized_entity.startswith("INTENT_"):
                base_entity = normalized_entity[7:]  # Remove the INTENT_ prefix
                if base_entity not in self.entity_intent_map:
                    self.entity_intent_map[base_entity] = intent_name
                    logger.debug(f"Mapped (base entity): {base_entity} -> {intent_name}")
            
            logger.info(f"Entity intent mapping updated successfully")
            logger.debug(f"Current mappings: {self.entity_intent_map}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating entity intent mapping: {str(e)}")
            logger.error(traceback.format_exc())
            return False
            
    def update_intent_keywords_old(self, intent_name: str, keywords: List[str]) -> bool:
        """
        Updates the keywords for a specific intent.
        If the intent already exists, the keywords will be added to the existing ones.
        If the intent does not exist, a new entry will be created.
        
        Args:
            intent_name: Intent name (e.g., explicar_termo)
            keywords: List of keywords for the intent
            
        Returns:
            bool: True if the update was successful, False otherwise
        """
        try:
            logger.info(f"Updating keywords for intent '{intent_name}'")
            
            if not keywords:
                logger.warning(f"Update intent keywords failed: Intent '{intent_name}' has an empty list of keywords")
                return False
                
            logger.info(f"Updating keywords for intent '{intent_name}': {keywords}")
            
            # Check all intents and keywords currently in use
            logger.info(f"Current intents and keywords: {self.intent_keywords}")
            
            # If the intent already exists, add new keywords
            if intent_name in self.intent_keywords:
                logger.info(f"Intent '{intent_name}' already exists with keywords: {self.intent_keywords[intent_name]}")
                
                # Add only keywords that do not exist yet
                existing_keywords = set(self.intent_keywords[intent_name])
                new_keywords = [kw for kw in keywords if kw not in existing_keywords]
                
                if new_keywords:
                    logger.info(f"New keywords to be added: {new_keywords}")
                    self.intent_keywords[intent_name].extend(new_keywords)
                    logger.info(f"Added {len(new_keywords)} new keywords for intent '{intent_name}'")
                    logger.info(f"Updated keywords for '{intent_name}': {self.intent_keywords[intent_name]}")
                else:
                    logger.info(f"No new keywords to add to intent '{intent_name}'")
            else:
                # Create new entry for the intent
                logger.info(f"Creating new entry for intent '{intent_name}' with keywords: {keywords}")
                self.intent_keywords[intent_name] = keywords
                logger.info(f"Created new entry for intent '{intent_name}' with {len(keywords)} keywords")
            
            # Update completed successfully
            logger.info(f"Update of keywords for intent '{intent_name}' completed successfully")
                
            return True
        except Exception as e:
            logger.error(f"Error updating keywords for intent '{intent_name}': {str(e)}")
            return False
    
    def get_best_intent(self, scores: Dict[str, float], entities: List[Entity]) -> Intent:
        """
        Determines the best intent based on scores and entities.
        
        Args:
            scores: Dictionary with intents and their scores
            entities: List of entities extracted
            
        Returns:
            Intent: Intent object with the best intent, confidence, and entities
        """
        logger.info(f"Starting selection of best intent with scores: {scores}")
        logger.info(f"Entities available: {entities}")
        
        # The system now handles all intents dynamically, without specific checks for particular intents
        
        # Normalize scores
        normalized_scores = self.normalize_scores(scores)
        logger.info(f"Normalized scores: {normalized_scores}")
        
        # Encontrar a intenção com maior pontuação
        best_intent_name, best_score = max(normalized_scores.items(), key=lambda x: x[1])
        logger.info(f"Best intent selected: '{best_intent_name}' with score {best_score}")
        
        # Calculate final confidence
        base_confidence = best_score
        entity_boost = min(0.2, 0.05 * len(entities))  # Até +0.2 de boost por entidades
        logger.info(f"Confidence base: {base_confidence}, entity boost: {entity_boost}")
        
        # Adjust confidence for specific intents
        if best_intent_name in ["plano_cuidado", "tratamento", "diagnostico"] and best_score > 0.7:
            # Ensure high confidence for important medical intents
            final_confidence = min(0.95, base_confidence + entity_boost)
            logger.info(f"Applying confidence boost for important medical intent: {final_confidence}")
        else:
            final_confidence = min(0.9, base_confidence + entity_boost)
            logger.info(f"Applying default confidence boost: {final_confidence}")
        
        # If confidence is too low, use generic intent
        if final_confidence < self.confidence_thresholds["minimum"]:
            logger.info(f"Confidence too low ({final_confidence} < {self.confidence_thresholds['minimum']}), using generic intent 'outro'")
            best_intent_name = "outro"
            final_confidence = 0.3
        
        # Create Intent object
        intent = Intent(
            name=best_intent_name,
            confidence=final_confidence,
            entities=entities
        )
        
        logger.info(f"Final intent selected: '{intent.name}' with confidence {intent.confidence:.2f} and {len(intent.entities)} entities")
        return intent
    
    def apply_special_cases(self, text: str, intent: Intent) -> Intent:
        """
        Applies special cases to adjust the intent.
        
        Args:
            text: Original text
            intent: Current Intent object
            
        Returns:
            Intent: Intent object possibly modified
        """
        logger.info(f"Applying special cases for text: '{text}' and current intent: '{intent.name}' (confidence: {intent.confidence:.2f})")
        
        # Check for relationship queries
        relationship_keywords = ["relacionamento", "relação", "relacionamentos", "relações", "conexão", "ligação"]
        has_relationship_keyword = any(keyword in text.lower() for keyword in relationship_keywords)
        
        # If the user is explicitly asking for relationships, prioritize that intent
        if has_relationship_keyword and intent.name != "relacionamentos":
            logger.info(f"Special case: User is asking for relationships, but current intent is '{intent.name}'. Changing to 'relacionamentos'")
            # Keep the entities but change the intent to 'relacionamentos'
            return Intent(name="relacionamentos", confidence=0.95, entities=intent.entities)
        
        # Special case for the "ajuda" intent
        if re.search(r'\b(ajuda|help|comandos)\b', text.lower()):
            logger.info(f"Special case: Detected help pattern in text")
            return Intent(name="ajuda", confidence=0.9, entities=[])
        
        # Special case for treatment questions
        if (re.search(r'\b(tratamento|tratamentos|tratar)\b', text.lower()) and 
            "para" in text.lower() and intent.confidence < 0.9):
            
            logger.info(f"Special case: Detected treatment pattern in text")
            
            # Keep entities but remove "tratamento" as entity
            filtered_entities = [e for e in intent.entities 
                               if e.value.lower() not in ["tratamento", "tratamentos", "o tratamento"]]
            
            logger.info(f"Entities filtered for treatment intent: {[e.text for e in filtered_entities]}")
            return Intent(name="tratamento", confidence=0.95, entities=filtered_entities)
        
        logger.info(f"No special cases applied, maintaining original intent: '{intent.name}'")
        return intent
