# This file makes utils a Python package

# Export the session manager
from .session_manager import get_chat_controller, clear_chat_controller

__all__ = ['get_chat_controller', 'clear_chat_controller']
