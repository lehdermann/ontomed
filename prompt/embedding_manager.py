from typing import Dict, List, Any
from llm.interface import LLMInterface
from prompt.template_manager import TemplateManager

class EmbeddingManager:
    """Graph embedding manager."""
    
    def __init__(self, llm: LLMInterface):
        """Initialize the embedding manager.
        
        Args:
            llm: LLM interface for embedding generation
        """
        self.llm = llm
        self.template_manager = TemplateManager(llm)
    
    def generate_concept_embedding(self, concept: Dict[str, Any]) -> List[float]:
        """Generates an embedding for a concept.
        
        Args:
            concept: Dictionary with concept information
            
        Returns:
            List of floats representing the embedding
        """
        # Use specific template for embedding generation
        return self.template_manager.get_embedding(
            "concept_embedding",
            concept
        )
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculates the similarity between two embeddings.
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            
        Returns:
            Similarity value (0.0 to 1.0)
        """
        # Cosine similarity implementation
        import numpy as np
        
        v1 = np.array(embedding1)
        v2 = np.array(embedding2)
        
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return dot_product / (norm1 * norm2)
    
    def find_related_concepts(self, concept: Dict[str, Any], concepts: List[Dict[str, Any]], threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Finds related concepts based on embeddings.
        
        Args:
            concept: Base concept to find related ones
            concepts: List of concepts to compare with
            threshold: Similarity threshold
            
        Returns:
            List of related concepts
        """
        # Generate embedding for the base concept
        base_embedding = self.generate_concept_embedding(concept)
        
        related_concepts = []
        
        for other_concept in concepts:
            if other_concept["id"] == concept["id"]:
                continue
                
            other_embedding = self.generate_concept_embedding(other_concept)
            similarity = self.calculate_similarity(base_embedding, other_embedding)
            
            if similarity >= threshold:
                related_concepts.append({
                    "concept": other_concept,
                    "similarity": similarity
                })
        
        # Sort by similarity
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
        # Find related concepts
        related_concepts = self.find_related_concepts(concept, concepts)
        
        relationships = []
        
        for related in related_concepts:
            # Generate relationship description using LLM
            relationship_description = self.template_manager.generate_content(
                "semantic_relationship",
                {
                    "concept1": concept,
                    "concept2": related["concept"],
                    "similarity": related["similarity"]
                }
            )
            
            relationships.append({
                "source": concept["id"],
                "target": related["concept"]["id"],
                "type": "SEMANTIC",
                "description": relationship_description,
                "similarity": related["similarity"]
            })
        
        return relationships
