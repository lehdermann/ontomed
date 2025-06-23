"""
Classes of models for natural language processing.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class Entity:
    """Represents an entity extracted from text."""
    value: str
    entity_type: str
    start: int = 0
    end: int = 0
    
    def __str__(self) -> str:
        return f"{self.entity_type}={self.value}"


@dataclass
class Intent:
    """Represents an intent identified in text."""
    name: str
    confidence: float
    entities: List['Entity'] = None
    
    def __post_init__(self):
        if self.entities is None:
            self.entities = []
    
    def __str__(self) -> str:
        return f"{self.name} (confidence: {self.confidence:.2f})"


@dataclass
class EntityPattern:
    """Represents a pattern for the Entity Ruler with priority."""
    label: str
    pattern: str
    priority: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Converts the pattern to the format expected by the Entity Ruler."""
        return {
            "label": self.label,
            "pattern": self.pattern,
            "id": f"{self.label}_{hash(self.pattern)}",
            "attrs": {"priority": self.priority}
        }
