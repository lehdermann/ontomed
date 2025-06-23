import requests
from dotenv import load_dotenv
import os
import logging

class APIClient:
    """Client for communication with the OntoMed API."""
    
    def __init__(self):
        """Initializes the client with the necessary settings."""
        load_dotenv()
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("api_client")
        
        # Try to determine if we're in Docker or local environment
        # Use the environment variable if set, otherwise try localhost first, then fallback to Docker service name
        api_url = os.getenv('ONTO_MED_API_URL')
        
        if not api_url:
            # Try localhost first (for local development)
            self.base_url = 'http://localhost:8000'
            self.logger.info(f"No ONTO_MED_API_URL set, trying {self.base_url} (local development)")
        else:
            self.base_url = api_url
            self.logger.info(f"Using API URL from environment: {self.base_url}")
            
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {os.getenv("API_KEY")}'
        }
    
    def generate_content(self, prompt: str, temperature: float = 0.7, max_tokens: int = 500, template_id: str = None) -> str:
        """Generates content using the LLM.
        
        Args:
            prompt: Prompt for generation
            temperature: Randomness control (0.0 to 1.0)
            max_tokens: Maximum number of tokens
            template_id: Template ID (optional)
            
        Returns:
            Generated content
        """
        data = {
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if template_id:
            data["template_id"] = template_id
            
        response = requests.post(
            f"{self.base_url}/llm/generate",
            json=data,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()["content"]
    
    def get_graph_statistics(self) -> dict:
        """Gets detailed statistics about the ontology.
        
        Returns:
            dict: Dictionary with ontology statistics, including:
                - total_concepts: Total number of concepts
                - total_relationships: Total number of relationships
                - class_count: Number of classes
                - subclass_count: Number of subclasses
                - annotation_count: Number of annotations
                - axiom_count: Number of axioms
                - property_count: Number of properties
        """
        try:
            # Log the request URL for debugging
            url = f"{self.base_url}/api/statistics"
            self.logger.info(f"Fetching statistics from: {url}")
            
            # Make the request with a timeout
            response = requests.get(url, headers=self.headers, timeout=10)
            
            # Log the response status
            self.logger.info(f"Statistics API response status: {response.status_code}")
            
            # Raise an exception for bad status codes
            response.raise_for_status()
            
            # Parse the response
            stats = response.json()
            self.logger.info(f"Statistics received: {stats}")
            return stats
            
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Connection error to API at {self.base_url}: {str(e)}")
            # Try alternative URL if we're using localhost
            if 'localhost' in self.base_url:
                try:
                    alt_url = self.base_url.replace('localhost', 'api')
                    self.logger.info(f"Trying alternative Docker URL: {alt_url}/api/statistics")
                    response = requests.get(f"{alt_url}/api/statistics", headers=self.headers, timeout=10)
                    response.raise_for_status()
                    return response.json()
                except requests.RequestException as alt_e:
                    self.logger.error(f"Alternative URL also failed: {str(alt_e)}")
            
            # Return default values
            return self._get_default_statistics()
            
        except requests.RequestException as e:
            self.logger.error(f"Error getting statistics: {str(e)}")
            return self._get_default_statistics()
    
    def _get_default_statistics(self) -> dict:
        """Returns default statistics values for when the API call fails."""
        self.logger.warning("Returning default statistics values due to API error")
        return {
            'total_concepts': 0,
            'total_relationships': 0,
            'class_count': 0,
            'subclass_count': 0,
            'annotation_count': 0,
            'axiom_count': 0,
            'property_count': 0
        }
    
    def clear_database(self) -> dict:
        """Clears all data from the database.
        
        Returns:
            dict: API response
        """
        response = requests.post(
            f"{self.base_url}/api/clear",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def get_embedding(self, text: str) -> list:
        """Generates embedding for a text.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            List of floats representing the embedding
        """
        response = requests.post(
            f"{self.base_url}/llm/embedding",
            json={"text": text},
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()["embedding"]
    
    def generate_structured(self, prompt: str, temperature: float = 0.7, max_tokens: int = 500) -> dict:
        """Generates structured response using the LLM.
        
        Args:
            prompt: Prompt for generation
            temperature: Randomness control (0.0 to 1.0)
            max_tokens: Maximum number of tokens
            
        Returns:
            Dictionary with the structured response
        """
        response = requests.post(
            f"{self.base_url}/llm/structured",
            json={
                "prompt": prompt,
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()["response"]
    
    def upload_ontology(self, file) -> requests.Response:
        """Uploads an ontology file to the API.
        
        Args:
            file: File-like object to upload
        
        Returns:
            Response from the API
        """
        files = {'file': (file.name, file, 'application/octet-stream')}
        response = requests.post(
            f"{self.base_url}/api/ontologies/upload",
            files=files,
            headers={key: value for key, value in self.headers.items() if key != 'Content-Type'}  # Remove Content-Type for multipart
        )
        response.raise_for_status()
        return response


    def get_concepts(self, filters: dict = None) -> list:
        """Fetches concepts from the API.
        
        Args:
            filters: Dictionary with search filters
            
        Returns:
            List of concepts
        """
        import logging
        logger = logging.getLogger(__name__)
        
        params = filters or {}
        logger.info(f"Buscando conceitos da API com filtros: {params}")
        
        response = requests.get(
            f"{self.base_url}/api/concepts",
            params=params,
            headers=self.headers
        )
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"API retornou {len(data) if isinstance(data, list) else 'objeto não-lista'} conceitos")
        
        # Check data structure
        if isinstance(data, list) and data:
            logger.info(f"Tipo do primeiro item: {type(data[0])}")
            if isinstance(data[0], dict):
                logger.info(f"Chaves disponíveis no primeiro conceito: {data[0].keys()}")
                # Check if the required fields are present
                has_id = 'id' in data[0]
                has_label = 'label' in data[0] or 'display_name' in data[0]
                logger.info(f"Campos necessários: id={has_id}, label/display_name={has_label}")
                
                if not has_id or not has_label:
                    logger.warning(f"ALERTA: Conceitos não possuem campos necessários! Exemplo: {data[0]}")
        
        return data
    
    def get_concept(self, concept_id: str) -> dict:
        """Fetches a specific concept.
        
        Args:
            concept_id: Concept ID
            
        Returns:
            Dictionary with concept data
        """
        try:
            if not concept_id:
                self.logger.error("Tentativa de obter conceito com ID vazio ou None")
                return {}
                
            self.logger.info(f"Buscando conceito com ID: {concept_id}")
            # Encode the concept ID correctly for the URL
            import urllib.parse
            encoded_concept_id = urllib.parse.quote(concept_id, safe='')
            self.logger.info(f"ID codificado para URL: {encoded_concept_id}")
            
            response = requests.get(
                f"{self.base_url}/api/concepts/{encoded_concept_id}",
                headers=self.headers,
                timeout=10  # Add timeout to avoid blocking
            )
            
            # Check response status
            response.raise_for_status()
            
            # Check if the response has content
            if not response.content:
                self.logger.warning(f"Resposta vazia para o conceito {concept_id}")
                return {}
                
            # Convert to JSON
            data = response.json()
            
            # Check if the result is valid
            if data is None:
                self.logger.warning(f"API retornou None para o conceito {concept_id}")
                return {}
                
            return data
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erro na requisição para obter conceito {concept_id}: {str(e)}")
            return {}
        except ValueError as e:
            self.logger.error(f"Erro ao converter resposta para JSON para conceito {concept_id}: {str(e)}")
            return {}
        except Exception as e:
            self.logger.error(f"Erro desconhecido ao obter conceito {concept_id}: {str(e)}")
            return {}
        
    def search_concepts(self, search_term: str) -> list:
        """Search concepts by term.
        
        Args:
            search_term: Term to search
            
        Returns:
            List of concepts found
        """
        try:
            # Check if the term is None or empty
            if search_term is None or search_term.strip() == '':
                self.logger.warning("Termo de busca é None ou vazio em search_concepts")
                return []
                
            original_term = search_term.strip().lower()
            normalized_term = original_term.replace('_', ' ')
            
            # Search for all concepts
            self.logger.info(f"Searching for concepts with term: '{search_term}' (normalized: '{normalized_term}')")
            
            # Search concepts from the API
            response = requests.get(
                f"{self.base_url}/api/concepts",
                headers=self.headers
            )
            response.raise_for_status()
            concepts = response.json()
            
            # Check if concepts is None or not a list
            if concepts is None:
                self.logger.warning("API returned None for the list of concepts")
                return []
                
            if not isinstance(concepts, list):
                self.logger.warning(f"API returned an unexpected type for concepts: {type(concepts)}")
                # Try to convert to list if it's a dictionary with a 'concepts' key
                if isinstance(concepts, dict) and 'concepts' in concepts:
                    concepts = concepts.get('concepts', [])
                else:
                    return []
            
            # Filter concepts that match the search term
            matching_concepts = []
            for concept in concepts:
                if not isinstance(concept, dict):
                    continue
                    
                # Check for ID, label or description - ensuring they are not None
                concept_id = (concept.get('id') or '').lower()
                label = (concept.get('label') or concept.get('display_name') or '').lower()
                description = (concept.get('description') or '').lower()
                
                # Check for exact match first (especially for terms with underscores)
                if original_term == concept_id or original_term == label:
                    self.logger.info(f"Exact match found for '{original_term}' in '{concept_id}'")
                    matching_concepts.append(concept)
                    continue
                
                # Check if the term is contained in the ID (especially useful for terms with underscores)
                if '_' in original_term and original_term in concept_id:
                    self.logger.info(f"Correspondência de termo com underscore encontrada: '{original_term}' em '{concept_id}'")
                    matching_concepts.append(concept)
                    continue
                
                # Normalize the ID and label to compare without underscores
                normalized_id = concept_id.replace('_', ' ')
                normalized_label = label.replace('_', ' ')
                
                # Check for partial match in the normalized fields
                if (normalized_term in normalized_id or 
                    normalized_term in normalized_label or 
                    normalized_term in description):
                    self.logger.info(f"Partial match found for '{normalized_term}' in '{normalized_id}'")
                    matching_concepts.append(concept)
            
            self.logger.info(f"Found {len(matching_concepts)} concepts for term '{search_term}'")
            return matching_concepts
        except Exception as e:
            self.logger.error(f"Error searching concepts: {str(e)}")
            return []
    
    def get_concept_by_term(self, term: str) -> dict:
        """Get a specific concept by term.
        
        Args:
            term: Term to search for the concept
            
        Returns:
            Concept found or None
        """
        try:
            # Check if the term is None or empty
            if term is None:
                self.logger.warning("Term is None in get_concept_by_term")
                return None
                
            # Ensure term is a string
            if not isinstance(term, str):
                self.logger.warning(f"Term is not a string: {term} (type: {type(term)})")
                term = str(term)
                
            # Remove whitespace
            term = term.strip()
            if not term:
                self.logger.warning("Term is empty in get_concept_by_term")
                return None
            
            # Remove common command prefixes to extract only the medical term
            prefixes = ["explique ", "o que é ", "defina ", "significado de ", "definição de "]
            clean_term = term
            for prefix in prefixes:
                if prefix and term.lower().startswith(prefix.lower()):
                    clean_term = term[len(prefix):].strip()
                    self.logger.info(f"Term cleaned after removing prefix '{prefix}': '{clean_term}'")
                    break
                    
            # Search concepts that match the cleaned term
            self.logger.info(f"Searching for concept for cleaned term: '{clean_term}'")
            concepts = self.search_concepts(clean_term)
            
            # Special search for terms with underscores
            if not clean_term:
                self.logger.warning("clean_term is None or empty in get_concept_by_term")
                return self._create_error_concept(term)
                
            # Check if the term contains spaces and convert them to underscores for search
            if ' ' in clean_term:
                self.logger.info(f"Term contains spaces: '{clean_term}'. Converting to underscore format.")
                clean_term_with_underscore = clean_term.replace(' ', '_')
                # Try to search for the term with underscore first
                concepts_with_underscore = self.search_concepts(clean_term_with_underscore)
                if concepts_with_underscore and len(concepts_with_underscore) > 0:
                    self.logger.info(f"Concept found using underscore format: '{clean_term_with_underscore}'")
                    # Use the first concept found
                    concept = concepts_with_underscore[0]
                    concept_id = concept.get('id')
                    if concept_id:
                        try:
                            self.logger.info(f"Retrieving details for concept ID: {concept_id}")
                            concept_details = self.get_concept(concept_id)
                            return concept_details
                        except Exception as e:
                            self.logger.warning(f"Error getting details for concept {concept_id}: {str(e)}")
                            return concept
                    else:
                        return concept
                
            term_lower = clean_term.lower() if clean_term else ''
            if "_" in clean_term:
                # Check if the exact term exists in the ontology
                self.logger.info(f"Detected term with underscore: '{clean_term}'. Performing special search.")
                
                # First, try direct search for the exact term
                
                # Get all concepts for local search
                all_concepts = self.get_concepts()
                self.logger.info(f"Total of concepts in ontology: {len(all_concepts)}")
                
                # Search for exact match in ID or label
                for concept in all_concepts:
                    if not isinstance(concept, dict):
                        continue
                        
                    concept_id = concept.get('id')
                    concept_label = concept.get('label')
                    concept_display = concept.get('display_name')
                    
                    # Ensure none of these are None before calling lower()
                    concept_id = concept_id.lower() if concept_id else ''
                    concept_label = concept_label.lower() if concept_label else ''
                    concept_display = concept_display.lower() if concept_display else ''
                    
                    # Check for exact match
                    if term_lower == concept_id or term_lower == concept_label or term_lower == concept_display:
                        self.logger.info(f"Found concept by exact match: {concept_id}")
                        concepts = [concept]
                        break
                
                # If no exact match was found, try partial match
                if not concepts:
                    for concept in all_concepts:
                        if not isinstance(concept, dict):
                            continue
                            
                        # Ensure none of these are None before calling lower()
                        concept_id = concept.get('id')
                        concept_label = concept.get('label')
                        concept_display = concept.get('display_name')
                        
                        concept_id = concept_id.lower() if concept_id else ''
                        concept_label = concept_label.lower() if concept_label else ''
                        concept_display = concept_display.lower() if concept_display else ''
                        
                        if term_lower in concept_id or term_lower in concept_label or term_lower in concept_display:
                            concepts = [concept]
                            break
                
                # If still not found, try splitting the term and checking if all parts are present
                if not concepts and "_" in term_lower:
                    parts = term_lower.split('_')
                    for concept in all_concepts:
                        concept_id = concept.get('id', '').lower()
                        concept_label = concept.get('label', '').lower()
                        concept_display = concept.get('display_name', '').lower()
                        concept_desc = concept.get('description', '').lower()
                        
                        all_parts_present = all(part in concept_id or part in concept_label or part in concept_display or part in concept_desc for part in parts)
                        if all_parts_present:
                            concepts = [concept]
                            break
            
            # Filter concepts to find the most specific
            if concepts and len(concepts) > 0:
                # If the exact term is in the list, prioritize it
                exact_match = None
                for concept in concepts:
                    concept_id = concept.get('id', '').lower()
                    concept_label = concept.get('label', '').lower()
                    concept_display = concept.get('display_name', '').lower()
                    
                    # Check if the term is exactly equal to the ID, label or display_name
                    if term_lower == concept_id.split('#')[-1] or term_lower == concept_label or term_lower == concept_display:
                        exact_match = concept
                        break
                
                # If an exact match was found, use it
                if exact_match:
                    self.logger.info(f"Found exact match for '{term_lower}'")
                    concept = exact_match
                else:
                    # Otherwise, use the first concept in the list
                    concept = concepts[0]
                
                concept_id = concept.get('id')
                
                if concept_id:
                    # Retrieve complete concept details
                    try:
                        self.logger.info(f"Retrieving details for concept ID: {concept_id}")
                        concept_details = self.get_concept(concept_id)
                        return concept_details
                    except Exception as e:
                        self.logger.warning(f"Error getting details for concept {concept_id}: {str(e)}")
                        return concept
                else:
                    return concept
            
            # If no concepts were found, try searching directly by term without prefix
            try:
                self.logger.warning(f"No concepts found for '{term}'. Trying to search directly by ID...")
                concept_details = self.get_concept(clean_term)
                if concept_details and 'error' not in concept_details:
                    self.logger.info(f"Concept found by directly searching ID: {clean_term}")
                    return concept_details
            except Exception as e:
                self.logger.warning(f"Error searching concept directly by ID {clean_term}: {str(e)}")
            
            # If still not found, create a generic concept
            generic_concept = {
                "id": clean_term.lower().replace(' ', '_') if clean_term else 'unknown',
                "label": clean_term,
                "display_name": clean_term,
                "description": f"Conceito genérico para o termo '{clean_term}'",
                "type": "GenericConcept",
                "relationships": []
            }
            
            self.logger.warning(f"Concept not found for '{term}'. Creating generic concept.")
            return generic_concept
            
        except Exception as e:
            self.logger.error(f"Error getting concept by term: {str(e)}")
            # Create a generic concept in case of error
            return self._create_error_concept(term)
            
    def _create_error_concept(self, term):
        """Create a generic error concept when a term cannot be found.
        
        Args:
            term: The term that was searched for
            
        Returns:
            A generic error concept dictionary
        """
        safe_term = term if term else 'unknown'
        # Make sure term is a string before calling replace
        if not isinstance(safe_term, str):
            safe_term = str(safe_term)
            
        # Use a valid ID format without error prefix
        normalized_term = safe_term.replace(' ', '_')
        
        # Try to get the concept directly first
        try:
            self.logger.warning(f"Tentando buscar conceito diretamente pelo ID: {normalized_term}")
            concept_details = self.get_concept(normalized_term)
            if concept_details and 'error' not in concept_details:
                self.logger.info(f"Encontrado conceito ao buscar diretamente pelo ID: {normalized_term}")
                return concept_details
        except Exception as e:
            self.logger.warning(f"Erro ao buscar conceito diretamente por ID {normalized_term}: {str(e)}")
        
        # If direct lookup fails, create a generic concept without the generic_ prefix
        return {
            'id': normalized_term,
            'label': safe_term,
            'description': "Conceito genérico criado para o termo solicitado.",
            'type': 'GenericConcept',
            'relationships': []
        }
        
    def get_concept_by_id(self, concept_id: str) -> dict:
        """Get a concept by its ID.
        
        Args:
            concept_id: The ID of the concept to fetch
            
        Returns:
            The concept data as a dictionary, or None if not found
        """
        try:
            if not concept_id:
                self.logger.warning("Empty concept_id provided to get_concept_by_id")
                return None
                
            # URL encode the concept_id
            import urllib.parse
            encoded_concept_id = urllib.parse.quote(concept_id, safe='')
            
            url = f"{self.base_url}/api/concepts/{encoded_concept_id}"
            self.logger.info(f"Fetching concept by ID: {url}")
            
            response = requests.get(
                url,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                self.logger.info(f"Concept not found: {concept_id}")
            else:
                self.logger.error(f"HTTP error fetching concept {concept_id}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error fetching concept {concept_id}: {str(e)}")
            
        return None
    
    def get_relationships(self, concept_id: str) -> list:
        """Retrieves relationships for a specific concept from the concept endpoint.
        
        Args:
            concept_id: ID of the concept to get relationships for (can be full IRI or just the local name)
            
        Returns:
            List of relationships for the concept, or empty list if none found
        """
        import urllib.parse
        
        if not concept_id:
            self.logger.warning("Attempted to get relationships with empty concept_id")
            return []
        
        # Try with the provided concept_id first
        concept_ids_to_try = [concept_id]
        
        # If the concept_id looks like a local name (no # or /), try with the full IRI
        if '#' not in concept_id and '/' not in concept_id:
            concept_ids_to_try.append(f"https://w3id.org/hmarl-genai/ontology#{concept_id}")
        
        for current_id in concept_ids_to_try:
            try:
                # URL encode the concept_id to handle special characters
                encoded_concept_id = urllib.parse.quote(current_id, safe='')
                url = f"{self.base_url}/api/concepts/{encoded_concept_id}"
                self.logger.info(f"Fetching concept to extract relationships: {url}")
                
                # Make the request
                response = requests.get(
                    url,
                    headers=self.headers,
                    timeout=10
                )
                response.raise_for_status()
                
                # Parse the response
                concept_data = response.json()
                
                # Extract relationships from the response
                relationships = []
                
                # Check if we have a valid concept with relationships
                if isinstance(concept_data, dict):
                    # Try to get relationships from the standard 'relationships' field
                    if 'relationships' in concept_data and isinstance(concept_data['relationships'], list):
                        relationships = concept_data['relationships']
                        self.logger.info(f"Found {len(relationships)} relationships in standard field for {current_id}")
                        if relationships:  # If we found relationships, no need to try other IDs
                            break
                    else:
                        # Try alternative field names if the standard one isn't found
                        for field in ['relations', 'related', 'properties', 'triples']:
                            if field in concept_data and isinstance(concept_data[field], list):
                                relationships = concept_data[field]
                                self.logger.info(f"Found {len(relationships)} relationships in alternative field '{field}' for {current_id}")
                                if relationships:  # If we found relationships, no need to try other fields
                                    break
                        if relationships:  # If we found relationships, no need to try other IDs
                            break
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Error fetching concept {current_id}: {str(e)}")
                continue
            
        # If we get here, we've either processed relationships or found none
        if not relationships:
            self.logger.warning(f"No relationships found for concept: {concept_id} (tried: {', '.join(concept_ids_to_try)})")
            return []
        
        # Process relationships to ensure consistent format
        processed_relationships = []
        
        for rel in relationships:
            # Skip None values
            if rel is None:
                continue
                
            # Convert string relationships to proper objects
            if isinstance(rel, str):
                processed_relationships.append({
                    'type': 'related',
                    'target': rel,
                    'target_label': rel.split('/')[-1].split('#')[-1],
                    'source': concept_id
                })
                continue
            
            # Process dictionary relationships
            if isinstance(rel, dict):
                # Ensure required fields exist
                if 'target' not in rel:
                    continue
                    
                # Create a new relationship object with consistent fields
                processed_rel = {
                    'type': rel.get('type', 'related'),
                    'target': rel['target'],
                    'target_label': rel.get('label') or rel.get('target_label'),
                    'source': concept_id
                }
                
                # If no label was provided, try to extract one from the target URI
                if not processed_rel['target_label'] and isinstance(rel['target'], str):
                    processed_rel['target_label'] = rel['target'].split('/')[-1].split('#')[-1]
                
                # Copy any additional fields
                for k, v in rel.items():
                    if k not in processed_rel:
                        processed_rel[k] = v
                
                processed_relationships.append(processed_rel)
        
        self.logger.info(f"Processed {len(processed_relationships)} relationships for concept: {concept_id}")
        return processed_relationships
            
    def get_relationships_between(self, term1: str, term2: str) -> list:
        """Find relationships between two medical concepts.
        
        Args:
            term1: First medical term
            term2: Second medical term
            
        Returns:
            List of relationships between the concepts
        """
        try:
            self.logger.info(f"Searching for relationships between '{term1}' and '{term2}'")
            
            # Normalize terms to lowercase for comparison
            term1_lower = term1.lower()
            term2_lower = term2.lower()
            
            # Get concepts for the terms
            concept1 = self.get_concept_by_term(term1)
            concept2 = self.get_concept_by_term(term2)
            
            # Log the concepts found
            self.logger.info(f"Concept 1 found: {concept1 is not None}")
            if concept1:
                self.logger.info(f"Concept 1 details: {concept1.get('label', 'Sem label')} | ID: {concept1.get('id', 'Sem ID')}")
                
            self.logger.info(f"Concept 2 found: {concept2 is not None}")
            if concept2:
                self.logger.info(f"Concept 2 details: {concept2.get('label', 'Sem label')} | ID: {concept2.get('id', 'Sem ID')}")
            
            if not concept1 or not concept2:
                self.logger.warning(f"Unable to find one or both concepts: '{term1}', '{term2}'")
                return []
            
            # Get IDs of the concepts
            concept1_id = concept1.get('id')
            concept2_id = concept2.get('id')
            
            if not concept1_id or not concept2_id:
                self.logger.warning(f"Unable to find ID for one or both concepts: '{term1}', '{term2}'")
                return []
                
            self.logger.info(f"Found concepts: '{concept1_id}' and '{concept2_id}'")
            
            # Get relationships of the first concept
            relationships1 = self.get_relationships(concept1_id)
            
            # Filter relationships that point to the second concept
            direct_relationships = []
            self.logger.info(f"Relationships of concept 1: {len(relationships1)}")
            
            for i, rel in enumerate(relationships1):
                self.logger.info(f"Analyzing relationship {i+1}/{len(relationships1)} of concept 1: {rel}")
                
                # Check if rel is a dictionary
                if isinstance(rel, dict):
                    # Check if the relationship target matches the second concept
                    target = rel.get('target', '').lower() if rel.get('target') else ''
                    self.logger.info(f"Target of relationship: {target}")
                    self.logger.info(f"Comparing with concept2_id: {concept2_id} and term2: {term2}")
                    
                    # Check if the target contains the second concept ID or term
                    if concept2_id and concept2_id.lower() in target:
                        self.logger.info(f"Match by second concept ID: {concept2_id}")
                        direct_relationships.append(rel)
                    elif term2_lower in target:
                        self.logger.info(f"Match by second concept term: {term2}")
                        direct_relationships.append(rel)
                    else:
                        self.logger.info(f"No match for this relationship")
                        
                elif isinstance(rel, str):
                    # If it's a string, check if it contains the second term
                    self.logger.info(f"Relationship is string: {rel}")
                    if term2_lower in rel.lower():
                        self.logger.info(f"Found direct relationship (string): {rel}")
                        direct_relationships.append({
                            'type': 'related to',
                            'target': term2,
                            'source': term1
                        })
                    else:
                        self.logger.info(f"String does not contain the second term: {term2}")
                else:
                    self.logger.info(f"Relationship type not recognized: {type(rel)}")
            
            self.logger.info(f"Total of direct relationships found: {len(direct_relationships)}")
            
            
            # If we found direct relationships, return them
            if direct_relationships:
                return direct_relationships
                
            # If we didn't find direct relationships, check relationships of the second concept
            relationships2 = self.get_relationships(concept2_id)
            self.logger.info(f"Relationships of concept 2: {len(relationships2)}")
            
            # Filter relationships that point to the first concept
            reverse_relationships = []
            
            for i, rel in enumerate(relationships2):
                self.logger.info(f"Analyzing relationship {i+1}/{len(relationships2)} of concept 2: {rel}")
                
                # Check if rel is a dictionary
                if isinstance(rel, dict):
                    # Check if the target of the relationship is the first concept
                    target = rel.get('target', '').lower() if rel.get('target') else ''
                    self.logger.info(f"Target of inverse relationship: {target}")
                    self.logger.info(f"Comparing with concept1_id: {concept1_id} and term1: {term1}")
                    
                    # Check if the target contains the ID of concept 1 or term 1
                    if concept1_id and concept1_id.lower() in target:
                        self.logger.info(f"Match inverse by concept 1 ID: {concept1_id}")
                        
                        # Invert the relationship
                        inverted_rel = rel.copy()
                        inverted_rel['source'] = concept2_id
                        inverted_rel['target'] = concept1_id
                        
                        # Adjust the type of the relationship for indicating it's inverted
                        rel_type = rel.get('type', '')
                        if rel_type:
                            inverted_rel['type'] = f"is {rel_type} by"
                        
                        self.logger.info(f"Criado relacionamento inverso: {inverted_rel}")
                        reverse_relationships.append(inverted_rel)
                    elif term1_lower in target:
                        self.logger.info(f"Match inverso por termo 1: {term1}")
                        
                        # Invert the relationship
                        inverted_rel = rel.copy()
                        inverted_rel['source'] = concept2_id
                        inverted_rel['target'] = concept1_id
                        
                        # Adjust the type of the relationship for indicating it's inverted
                        rel_type = rel.get('type', '')
                        if rel_type:
                            inverted_rel['type'] = f"is {rel_type} by"
                        
                        self.logger.info(f"Inverted relationship created: {inverted_rel}")
                        reverse_relationships.append(inverted_rel)
                    else:
                        self.logger.info(f"No inverse match for this relationship")
                        
                elif isinstance(rel, str):
                    # If it's a string, check if it contains term1
                    self.logger.info(f"Relationship inverse is string: {rel}")
                    if term1_lower in rel.lower():
                        self.logger.info(f"Found inverse relationship (string): {rel}")
                        reverse_relationships.append({
                            'type': 'is related to by',
                            'target': term1,
                            'source': term2
                        })
                    else:
                        self.logger.info(f"String does not contain term 1: {term1}")
                else:
                    self.logger.info(f"Type of inverse relationship not recognized: {type(rel)}")
            
            self.logger.info(f"Total of inverse relationships found: {len(reverse_relationships)}")
            
            
            # If we found inverse relationships, return them
            if reverse_relationships:
                return reverse_relationships
                
            # If no relationships were found, create a synthetic relationship
            self.logger.info(f"No relationships found between '{term1}' and '{term2}'. Creating synthetic relationship.")
            
            # Check if the concepts are of the same type
            concept1_type = concept1.get('type', '')
            concept2_type = concept2.get('type', '')
            
            self.logger.info(f"Type of concept 1 '{term1}': {concept1_type}")
            self.logger.info(f"Type of concept 2 '{term2}': {concept2_type}")
            
            # Check other attributes of the concepts to enrich the synthetic relationship
            concept1_label = concept1.get('label', term1)
            concept2_label = concept2.get('label', term2)
            
            self.logger.info(f"Label of concept 1 '{term1}': {concept1_label}")
            self.logger.info(f"Label of concept 2 '{term2}': {concept2_label}")
            
            # Create synthetic relationship with detailed information
            synthetic_rel = {
                'source': concept1_id,
                'target': concept2_id,
                'synthetic': True
            }
            
            if concept1_type == concept2_type:
                # If they are of the same type, create an association relationship
                synthetic_rel['type'] = 'associated with'
                synthetic_rel['description'] = f"Association between concepts of type {concept1_type}"
                self.logger.info(f"Synthetic association relationship created: {synthetic_rel}")
            else:
                # If they are of different types, create a relationship based on the types
                synthetic_rel['type'] = 'related to'
                synthetic_rel['description'] = f"Relação entre {concept1_type} e {concept2_type}"
                self.logger.info(f"Synthetic relationship created between different types: {synthetic_rel}")
            
            # Add extra information for debugging
            synthetic_rel['debug_info'] = {
                'term1': term1,
                'term2': term2,
                'concept1_id': concept1_id,
                'concept2_id': concept2_id,
                'concept1_label': concept1_label,
                'concept2_label': concept2_label
            }
            
            self.logger.info(f"Returning final synthetic relationship: {synthetic_rel}")
            return [synthetic_rel]
                
        except Exception as e:
            self.logger.error(f"Error fetching relationships between '{term1}' and '{term2}': {str(e)}", exc_info=True)
            return []
    
    def create_concept(self, concept_data: dict) -> dict:
        """Creates a new concept.
        
        Args:
            concept_data: Data of the concept to be created
            
        Returns:
            Dictionary with the created concept data
        """
        response = requests.post(
            f"{self.base_url}/api/concepts",
            json=concept_data,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def update_concept(self, concept_id: str, concept_data: dict) -> dict:
        """Updates an existing concept.
        
        Args:
            concept_id: Concept ID
            concept_data: Data of the concept to be updated
            
        Returns:
            Dictionary with the updated concept data
        """
        response = requests.put(
            f"{self.base_url}/api/concepts/{concept_id}",
            json=concept_data,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_templates(self, filters: dict = None) -> list:
        """
        Busca templates da API.
        
        Args:
            filters: Dicionário com filtros para a busca
            
        Returns:
            Lista de templates
        """
        try:
            # Preparar parâmetros
            params = filters or {}
            
            # Fazer a requisição
            print(f"Searching for templates at: {self.base_url}/api/templates")
            response = requests.get(
                f"{self.base_url}/api/templates",
                params=params,
                headers=self.headers,
                timeout=10  # Add timeout to prevent indefinite blocking
            )
            
            # Verify response status
            response.raise_for_status()
            
            # Process response
            templates = response.json()
            print(f"Templates found: {len(templates)}")
            
            # Verify if templates have the expected structure
            for template in templates:
                # Ensure all templates have the required keys
                if "id" not in template and "template_id" in template:
                    template["id"] = template["template_id"]
                    
                if "name" not in template:
                    template["name"] = template.get("id", "").replace('_', ' ').title()
                    
                if "type" not in template:
                    template["type"] = "text"
            
            return templates
            
        except requests.exceptions.RequestException as e:
            print(f"Error searching for templates: {str(e)}")
            # Return empty list in case of error
            return []
    
    def create_template(self, template_data: dict) -> dict:
        """Creates a new template.
        
        Args:
            template_data: Data of the template to be created
            
        Returns:
            Created template
        """
        response = requests.post(
            f"{self.base_url}/api/templates",
            json=template_data,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_template(self, template_id: str) -> dict:
        """Searches for a specific template.
        
        Args:
            template_id: Template ID
            
        Returns:
            Found template
        """
        response = requests.get(
            f"{self.base_url}/api/templates/{template_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def update_template(self, template_id: str, template_data: dict) -> dict:
        """Updates an existing template.
        
        Args:
            template_id: Template ID
            template_data: Updated template data
            
        Returns:
            Updated template
        """
        response = requests.put(
            f"{self.base_url}/api/templates/{template_id}",
            json=template_data,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def delete_template(self, template_id: str) -> None:
        """Deletes a template.
        
        Args:
            template_id: Template ID
        """
        response = requests.delete(
            f"{self.base_url}/api/templates/{template_id}",
            headers=self.headers
        )
        response.raise_for_status()
        
    def generate_content(self, template_id: str, params: dict) -> str:
        """Generates text content using a template.
        
        Args:
            template_id: ID of the template to be used
            params: Generation parameters (concept, temperature, etc.)
            
        Returns:
            Generated text content
        """
        try:
            print(f"Generating content with template {template_id}")
            response = requests.post(
                f"{self.base_url}/api/generate/text/{template_id}",
                json=params,
                headers=self.headers,
                timeout=30  # Longer timeout for content generation
            )
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error generating content: {str(e)}")
            raise ValueError(f"Error generating content: {str(e)}")
    
    def generate_structured_content(self, template_id: str, params: dict) -> dict:
        """Generates structured content using a template.
        
        Args:
            template_id: ID of the template to be used
            params: Generation parameters (concept, temperature, etc.)
            
        Returns:
            Generated structured content (dictionary)
        """
        try:
            print(f"Generating structured content with template {template_id}")
            response = requests.post(
                f"{self.base_url}/api/generate/structured/{template_id}",
                json=params,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error generating structured content: {str(e)}")
            raise ValueError(f"Error generating structured content: {str(e)}")
    
    def generate_embedding(self, template_id: str, params: dict) -> list:
        """Generates an embedding for a concept using a template.
        
        Args:
            template_id: ID of the template to be used
            params: Generation parameters (concept, etc.)
            
        Returns:
            Generated embedding (list of numbers)
        """
        try:
            print(f"Generating embedding with template {template_id}")
            response = requests.post(
                f"{self.base_url}/api/generate/embedding/{template_id}",
                json=params,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error generating embedding: {str(e)}")
            raise ValueError(f"Error generating embedding: {str(e)}")
    
    def get_template_content(self, template_id: str) -> str:
        """Gets the content of a template.
        
        Args:
            template_id: Template ID
            
        Returns:
            Template content
        """
        template = self.get_template(template_id)
        return template.get("content", "")
    
    def get_template_variables(self, template_id: str) -> list:
        """Gets the variables of a template.
        
        Args:
            template_id: Template ID
            
        Returns:
            List of template variables
        """
        template = self.get_template(template_id)
        return template.get("variables", [])
    
    def get_template(self, template_id: str) -> dict:
        """Searches for a specific template.
        
        Args:
            template_id: Template ID
            
        Returns:
            Dictionary with template data
        """
        response = requests.get(
            f"{self.base_url}/api/templates/{template_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def create_template(self, template_data: dict) -> dict:
        """Creates a new template.
        
        Args:
            template_data: Data of the template to be created
            
        Returns:
            Dictionary with the created template data
        """
        response = requests.post(
            f"{self.base_url}/api/templates",
            json=template_data,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def update_template(self, template_id: str, template_data: dict) -> dict:
        """Updates an existing template.
        
        Args:
            template_id: Template ID
            template_data: Template data to be updated
            
        Returns:
            Dictionary with the updated template data
        """
        response = requests.put(
            f"{self.base_url}/api/templates/{template_id}",
            json=template_data,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
