"""Session management for the OntoMed chatbot."""
from datetime import datetime
from typing import Dict, List, Optional, Any
from .message import ChatMessage
from pydantic import BaseModel, Field

class ChatSession(BaseModel):
    """Represents a chat session with message history and context.
    
    Attributes:
        session_id: Unique session identifier
        user_id: Optional user identifier
        created_at: When the session was created
        last_activity: Timestamp of last activity
        context: Session context and state
        message_history: List of messages in the session
    """
    session_id: str
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = Field(default_factory=dict)
    message_history: List[ChatMessage] = Field(default_factory=list)
    
    def add_message(self, message: ChatMessage) -> None:
        """Add a message to the session history.
        
        Args:
            message: The message to add
        """
        self.message_history.append(message)
        self.last_activity = datetime.utcnow()
    
    def get_recent_messages(self, limit: int = 10) -> List[ChatMessage]:
        """Get the most recent messages from the session.
        
        Args:
            limit: Maximum number of messages to return
            
        Returns:
            List of recent messages, most recent last
        """
        return self.message_history[-limit:]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'context': self.context,
            'message_history': [msg.to_dict() for msg in self.message_history]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatSession':
        """Create session from dictionary."""
        from .message import ChatMessage
        
        # Convert string timestamps back to datetime objects
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['last_activity'] = datetime.fromisoformat(data['last_activity'])
        
        # Convert message dictionaries to ChatMessage objects
        messages = [ChatMessage.from_dict(msg) for msg in data.pop('message_history', [])]
        
        session = cls(**data)
        session.message_history = messages
        return session
