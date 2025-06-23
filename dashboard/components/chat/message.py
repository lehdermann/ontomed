"""Chat message model for the OntoMed chatbot."""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class ChatMessage(BaseModel):
    """Model representing a chat message.
    
    Attributes:
        message_id: Unique message identifier
        session_id: Session identifier
        user_id: Optional user identifier
        content: Message text content
        timestamp: When the message was created
        message_type: Type of message ('user', 'bot', 'system')
        intent: Detected intent, if any
        confidence: Confidence score for the detected intent (0-1)
        entities: List of extracted entities
        metadata: Additional metadata
    """
    message_id: str
    session_id: str
    user_id: Optional[str] = None
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    message_type: str = 'user'  # 'user', 'bot', 'system'
    
    # Processing metadata
    intent: Optional[str] = None
    confidence: Optional[float] = None
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return self.dict()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        """Create message from dictionary."""
        return cls(**data)
