"""
Module for defining entity patterns used in the NLP pipeline.
"""
from typing import List, Dict, Any, Optional, Union

class EntityPattern:
    """
    Represents a pattern for matching entities in text.
    
    This class is used to define patterns that can be used by spaCy's EntityRuler
    to identify entities in text based on linguistic patterns.
    
    Attributes:
        label (str): The label/type of the entity (e.g., 'PERSON', 'ORG').
        pattern (Union[str, List[Dict[str, Any]]]): The pattern to match.
            Can be a string (exact match) or a list of token patterns.
        id (Optional[str]): Optional ID for the pattern.
        priority (int): Priority of the pattern (higher = tried first).
    """
    
    def __init__(
        self, 
        label: str, 
        pattern: Union[str, List[Dict[str, Any]]], 
        id: Optional[str] = None,
        priority: int = 5
    ) -> None:
        """
        Initialize an EntityPattern.
        
        Args:
            label: The entity type/label.
            pattern: The pattern to match. Can be a string or a list of token patterns.
            id: Optional identifier for the pattern.
            priority: Priority of the pattern (higher = tried first).
        """
        self.label = label
        self.pattern = pattern
        self.id = id
        self.priority = priority
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the pattern to a dictionary format suitable for spaCy's EntityRuler.
        
        Returns:
            Dictionary containing the pattern data.
        """
        pattern_dict = {
            'label': self.label,
            'pattern': self.pattern
        }
        
        if self.id is not None:
            pattern_dict['id'] = self.id
            
        return pattern_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EntityPattern':
        """
        Create an EntityPattern from a dictionary.
        
        Args:
            data: Dictionary containing pattern data.
            
        Returns:
            A new EntityPattern instance.
        """
        return cls(
            label=data.get('label', ''),
            pattern=data.get('pattern', []),
            id=data.get('id'),
            priority=data.get('priority', 5)
        )
    
    def __repr__(self) -> str:
        """Return a string representation of the pattern."""
        return f"EntityPattern(label='{self.label}', pattern={self.pattern}, id={self.id}, priority={self.priority})"

# Alias for backward compatibility
Pattern = EntityPattern
