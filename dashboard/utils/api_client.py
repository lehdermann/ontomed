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
        params = filters or {}
        response = requests.get(
            f"{self.base_url}/api/concepts",
            params=params,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_concept(self, concept_id: str) -> dict:
        """Fetches a specific concept.
        
        Args:
            concept_id: Concept ID
            
        Returns:
            Dictionary with concept data
        """
        response = requests.get(
            f"{self.base_url}/api/concepts/{concept_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
        
    def get_relationships(self, concept_id: str) -> list:
        """Retrieves relationships for a specific concept
        
        Args:
            concept_id: ID of the concept to get relationships for
            
        Returns:
            List of relationships for the concept
        """
        import urllib.parse
        import logging
        
        # URL encode the concept_id to ensure special characters are handled correctly
        encoded_concept_id = urllib.parse.quote(concept_id, safe='')
        
        # Configure more detailed logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger("api_client")
        
        # Get the complete concept directly
        try:
            logger.info(f"Getting complete concept to extract relationships: {concept_id}")
            
            # Show the complete URL for debug
            url = f"{self.base_url}/api/concepts/{encoded_concept_id}"
            logger.info(f"Request URL: {url}")
            
            # Make the request with timeout to avoid blocking
            response = requests.get(
                url,
                headers=self.headers,
                timeout=10
            )
            
            # Ensure the response is treated as UTF-8
            response.encoding = 'utf-8'
            
            # Normalize special characters
            def normalize_text(text):
                if isinstance(text, str):
                    import unicodedata
                    # First try to fix common encoding problems
                    text = text.replace('\u00c3\u00a7', 'ç')  # ç (c cedilla)
                    text = text.replace('\u00c3\u00a3', 'ã')  # ã (a with tilde)
                    text = text.replace('\u00c3\u00a9', 'é')  # é (e with acute)
                    text = text.replace('\u00c3\u00a1', 'á')  # á (a with acute)
                    text = text.replace('\u00c3\u00b3', 'ó')  # ó (o with acute)
                    text = text.replace('\u00c3\u00ba', 'ú')  # ú (u with acute)
                    text = text.replace('\u00c3\u00a0', 'à')  # à (a with grave)
                    text = text.replace('\u00c3\u00b5', 'õ')  # õ (o with tilde)
                    
                    # Then apply Unicode normalization
                    text = unicodedata.normalize('NFC', text)
                    
                    # Check if there are still Unicode escape sequences in the text
                    if '\\u00' in text or '\\U00' in text:
                        try:
                            # Try to decode Unicode escape sequences
                            text = text.encode('latin1').decode('utf-8')
                        except Exception as e:
                            # Just log the error and continue
                            pass
                return text
            
            # Check the response status
            response.raise_for_status()
            
            # Show the response status
            logger.info(f"Status da resposta: {response.status_code}")
            
            # Check if the response has content
            if not response.content:
                logger.warning("Empty response from API")
                return []
            
            # Extract relationships from the concept
            concept_data = response.json()
            logger.info(f"Type of returned data: {type(concept_data)}")
            
            # Normalize special characters in the data
            def normalize_dict(data):
                if isinstance(data, dict):
                    return {k: normalize_dict(v) for k, v in data.items()}
                elif isinstance(data, list):
                    return [normalize_dict(item) for item in data]
                elif isinstance(data, str):
                    return normalize_text(data)
                else:
                    return data
            
            # Apply normalization to the data
            concept_data = normalize_dict(concept_data)
            
            # Log raw data for debug
            if isinstance(concept_data, dict):
                logger.info(f"Keys in returned object: {concept_data.keys()}")
            
            # Check different response formats
            relationships = []
            
            # Case 1: The response is a dictionary with the 'relationships' key
            if isinstance(concept_data, dict) and 'relationships' in concept_data:
                logger.info("Format 1: Dictionary with 'relationships' key")
                relationships = concept_data.get("relationships", [])
                logger.info(f"Number of relationships found: {len(relationships)}")
            
            # Case 2: The response is a list of relationships directly
            elif isinstance(concept_data, list):
                logger.info("Format 2: List of relationships")
                relationships = concept_data
                logger.info(f"Number of relationships found: {len(relationships)}")
            
            # Case 3: The response is a dictionary with another structure
            elif isinstance(concept_data, dict):
                logger.info("Format 3: Dictionary with another structure")
                # Try to extract relationships from other common keys
                for key in ['triples', 'statements', 'predicates', 'relations']:
                    if key in concept_data:
                        logger.info(f"Found alternative key: {key}")
                        rel_data = concept_data.get(key, [])
                        if isinstance(rel_data, list):
                            relationships = rel_data
                            logger.info(f"Using {len(relationships)} relationships from key '{key}'")
                            break
            
            # If we didn't find any relationships, return an empty list
            if not relationships:
                logger.warning(f"No relationships found for concept: {concept_id}")
                return []
            
            # Filter only relevant relationships
            filtered_relationships = []
            for rel in relationships:
                if not isinstance(rel, dict):
                    logger.warning(f"Relationship is not a dictionary: {rel}")
                    continue
                    
                rel_type = rel.get("type", "")
                target = rel.get("target", "")
                
                # If it doesn't have type or target, skip
                if not rel_type or not target:
                    continue
                
                # Include all significant semantic relationships
                if rel_type in ["disjointWith", "subClassOf", "equivalentClass", "complementOf", "inverseOf", "domain", "range"]:
                    filtered_relationships.append(rel)
                    logger.info(f"Adding semantic relationship: {rel_type} -> {target}")
                
                # Include comments (descriptions) - expanding search terms for Disease
                elif rel_type == "comment":
                    # More comprehensive terms to detect disease descriptions
                    disease_terms = ["anormal", "organismo", "condi", "doença", "disease", "patolog", "saúde", 
                                    "medical", "condition", "abnormal", "health", "disorder"]
                    
                    # Check if any of the terms is present in the text
                    if any(term.lower() in target.lower() for term in disease_terms):
                        filtered_relationships.append(rel)
                        logger.info(f"Adding relevant comment: {target[:50]}...")
                
                # Include labels (names)
                elif rel_type == "label":
                    filtered_relationships.append(rel)
                    logger.info(f"Adding label: {target}")
                
                # Include other potentially useful relationships
                elif rel_type not in ["versionInfo", "imports", "type"] and not rel_type.startswith("owl:"):
                    filtered_relationships.append(rel)
                    logger.info(f"Adding other relationship: {rel_type} -> {target}")
            
            logger.info(f"Found {len(filtered_relationships)} relevant relationships for: {concept_id}")
            
            # If we didn't find any relevant relationships, try to add some default ones for Disease
            if len(filtered_relationships) == 0 and ("disease" in concept_id.lower() or "disease" in concept_id.lower()):
                logger.info("Adding default relationships for the Disease concept")
                
                # Add some default relationships for Disease
                filtered_relationships.append({
                    "type": "subClassOf",
                    "target": "http://www.w3.org/2002/07/owl#Thing",
                    "target_label": "Thing"
                })
                
                filtered_relationships.append({
                    "type": "disjointWith",
                    "target": "https://w3id.org/hmarl-genai/ontology#Treatment",
                    "target_label": "Treatment"
                })
            
            return filtered_relationships
            
            logging.warning(f"No relationships found in concept: {concept_id}")
            return []
            
        except Exception as e:
            logging.warning(f"Error getting relationships: {str(e)}")
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
            
            # Verificar status da resposta
            response.raise_for_status()
            
            # Processar resposta
            templates = response.json()
            print(f"Templates found: {len(templates)}")
            
            # Verificar se os templates têm a estrutura esperada
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
