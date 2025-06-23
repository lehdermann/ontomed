"""
Simplified embedding manager for the dashboard.
This version does not depend on the concept_embedding template.
"""

import numpy as np
from typing import Dict, List, Any

class SimpleEmbeddingManager:
    """Simplified version of the embedding manager for the dashboard."""
    
    def __init__(self):
        """Initializes the simplified embedding manager."""
        pass
    
    def _generate_simple_embedding(self, concept: Dict[str, Any]) -> List[float]:
        """Generates a simple embedding for a concept without using templates.
        
        Args:
            concept: Dictionary with concept information
            
        Returns:
            List of floats representing the embedding
        """
        # Extract concept information
        concept_id = concept.get("id", "")
        label = concept.get("label", "")
        description = concept.get("description", "")
        concept_type = concept.get("type", "")
        
        # Extract additional information that might be in relationships
        relationships = concept.get("relationships", [])
        related_terms = []
        
        # Extract related terms from relationships to enrich the embedding
        for rel in relationships:
            rel_type = rel.get("type", "")
            target = rel.get("target", "")
            
            # Extract the target name (part after # or /)
            if "#" in target:
                target_name = target.split("#")[-1]
            elif "/" in target:
                target_name = target.split("/")[-1]
            else:
                target_name = target
                
            related_terms.append(target_name)
            related_terms.append(rel_type)
        
        # Use hash of ID as seed to generate a pseudo-random but deterministic embedding
        import hashlib
        
        # Create a string with the concept information
        concept_text = f"{concept_id}|{label}|{description}|{concept_type}"
        
        # Generate hash
        hash_obj = hashlib.md5(concept_text.encode())
        hash_hex = hash_obj.hexdigest()
        
        # Use hash as seed to generate a 128-dimensional embedding
        np.random.seed(int(hash_hex, 16) % (2**32 - 1))
        embedding = np.random.normal(0, 1, 128)
        
        # Enrich the embedding with relationship information
        if related_terms:
            # Create a string with all related terms
            related_text = "|".join(related_terms)
            
            # Generate a hash for the related terms
            rel_hash_obj = hashlib.md5(related_text.encode())
            rel_hash_hex = rel_hash_obj.hexdigest()
            
            # Create an embedding for the related terms
            np.random.seed(int(rel_hash_hex, 16) % (2**32 - 1))
            rel_embedding = np.random.normal(0, 1, 128)
            
            # Combine embeddings (70% original concept, 30% relationships)
            embedding = embedding * 0.7 + rel_embedding * 0.3
        
        # Normalize the embedding
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding.tolist()
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculates the similarity between two embeddings.
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            
        Returns:
            Similarity value (0.0 to 1.0)
        """
        # Cosine similarity implementation
        v1 = np.array(embedding1)
        v2 = np.array(embedding2)
        
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return dot_product / (norm1 * norm2)
    
    def find_related_concepts(self, concept: Dict[str, Any], concepts: List[Dict[str, Any]], threshold: float = 0.5) -> List[Dict[str, Any]]:
        """Finds related concepts based on embeddings.
        
        Args:
            concept: Base concept to find related ones
            concepts: List of concepts to compare
            threshold: Similarity threshold
            
        Returns:
            List of related concepts
        """
        # Generate embedding for the base concept
        base_embedding = self._generate_simple_embedding(concept)
        
        related_concepts = []
        
        for other_concept in concepts:
            if other_concept["id"] == concept["id"]:
                continue
                
            other_embedding = self._generate_simple_embedding(other_concept)
            similarity = self.calculate_similarity(base_embedding, other_embedding)
            
            if similarity >= threshold:
                related_concepts.append({
                    "concept": other_concept,
                    "similarity": similarity
                })
        
        # Ordenar por similaridade
        related_concepts.sort(key=lambda x: x["similarity"], reverse=True)
        
        return related_concepts
    
    def generate_semantic_relationships(self, concept: Dict[str, Any], concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generates semantic relationships between concepts.
        
        Args:
            concept: Base concept
            concepts: List of concepts to analyze
            
        Returns:
            List of semantic relationships
        """
        import logging
        logger = logging.getLogger("embedding_manager")
        
        # Check if we have concepts to compare
        if not concepts:
            logger.warning("No concepts to compare. Returning empty list.")
            return []
            
        # Verificar se o conceito base tem ID
        if "id" not in concept:
            logger.warning("Base concept has no ID. Returning empty list.")
            return []
            
        logger.info(f"Generating semantic relationships for concept: {concept.get('id', '')}")
        logger.info(f"Number of concepts to compare: {len(concepts)}")
        
        # Encontrar conceitos relacionados
        try:
            related_concepts = self.find_related_concepts(concept, concepts, threshold=0.3)  # Use a lower threshold to generate more relationships
            logger.info(f"Found {len(related_concepts)} related concepts")
        except Exception as e:
            logger.error(f"Error finding related concepts: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            related_concepts = []
        
        relationships = []
        
        # If we didn't find related concepts, try to generate some for Disease
        concept_id = concept.get("id", "")
        concept_label = concept.get("label", "")
        
        # Verificar se id ou label são None e convertê-los para string vazia
        if concept_id is None:
            concept_id = ""
        if concept_label is None:
            concept_label = ""
            
        if not related_concepts and ("disease" in concept_id.lower() or "disease" in concept_label.lower()):
            logger.info("Generating default semantic relationships for Disease")
            
            # Find treatment and prevention concepts
            for other in concepts:
                other_id = other.get("id", "")
                other_label = other.get("label", "")
                
                # Verificar se id ou label são None e convertê-los para string vazia
                if other_id is None:
                    other_id = ""
                if other_label is None:
                    other_label = ""
                
                # Check if it's a treatment or prevention concept
                is_treatment = "treatment" in other_id.lower() or "treatment" in other_label.lower()
                is_prevention = "prevention" in other_id.lower() or "prevention" in other_label.lower()
                
                if is_treatment or is_prevention:
                    similarity = 0.6 if is_treatment else 0.5
                    related_concepts.append({"concept": other, "similarity": similarity})
                    # Use a default value for other_label if it's None
                    display_label = other_label if other_label else "Sem nome"
                    logger.info(f"Added default semantic relationship with {display_label} (sim: {similarity})")
        
        # Criar relacionamentos a partir dos conceitos relacionados
        for related in related_concepts:
            # Extrair informações do conceito relacionado
            related_concept = related["concept"]
            similarity = related["similarity"]
            related_label = related_concept.get("label", "Sem nome")
            
            # Ensure the base concept label is not None
            concept_label = concept.get('label')
            if concept_label is None:
                concept_label = ""
            
            # Generate more informative relationship description
            relationship_description = f"Relacionamento semântico entre {concept_label} e {related_label} (similaridade: {similarity:.2f})"
            
            # Criar o relacionamento
            relationships.append({
                "source": concept["id"],
                "target": related_concept["id"],
                "type": "SEMANTIC",
                "title": relationship_description,
                "description": relationship_description,
                "similarity": similarity,
                "is_semantic": True
            })
            
            logger.info(f"Added semantic relationship with {related_label} (sim: {similarity:.2f})")
        
        return relationships
