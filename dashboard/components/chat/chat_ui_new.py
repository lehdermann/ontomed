"""Streamlit chat UI component for OntoMed with fixed right panel design."""
from typing import Dict, Any, Callable, Type, TypeVar
from datetime import datetime
import streamlit as st
import uuid

T = TypeVar('T', bound='ChatUI')

class ChatUI:
    """A Streamlit-based chat interface for the OntoMed chatbot."""
    _instance = None
    
    def __new__(cls: Type[T], *args, **kwargs) -> T:
        if cls._instance is None:
            cls._instance = super(ChatUI, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, 
                 session_state_key: str = 'chat_ui',
                 title: str = 'OntoMed Assistant',
                 width: int = 320,
                 height: int = 600):
        """Initialize the chat UI as a singleton."""
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self._initialized = True
        self.session_state_key = session_state_key
        self.title = title
        self.width = width
        self.height = height
        
        # Initialize session state if needed
        if 'chat_initialized' not in st.session_state:
            self._init_session_state()
    
    def _init_session_state(self) -> None:
        """Initialize the chat session state."""
        # Use a different key for the chat state to avoid conflict with the ChatUI instance
        state_key = f"{self.session_state_key}_state"
        if not hasattr(st.session_state, state_key):
            setattr(st.session_state, state_key, {
                'is_open': True,  # Start with chat panel open
                'messages': [],
                'input_text': '',
                'is_typing': False,
                'typing_message_id': None
            })
        st.session_state.chat_initialized = True
        
    def _get_chat_state(self) -> dict:
        """Get the chat state from session state."""
        state_key = f"{self.session_state_key}_state"
        if not hasattr(st.session_state, state_key):
            self._init_session_state()
        return getattr(st.session_state, state_key, {})
        
    def _set_chat_state(self, state: dict) -> None:
        """Set the chat state in session state."""
        state_key = f"{self.session_state_key}_state"
        setattr(st.session_state, state_key, state)
    
    def add_user_message(self, content: str) -> None:
        """Add a user message to the chat."""
        chat_state = self._get_chat_state()
        
        if 'messages' not in chat_state:
            chat_state['messages'] = []
            
        chat_state['messages'].append({
            'id': str(uuid.uuid4()),
            'content': content,
            'sender': 'user',
            'timestamp': datetime.now().isoformat()
        })
        self._set_chat_state(chat_state)
    
    def add_bot_message(self, content: str, is_typing: bool = False) -> str:
        """Add a bot message to the chat.
        
        Args:
            content: The message content
            is_typing: Whether this is a typing indicator message
            
        Returns:
            str: The message ID
        """
        chat_state = self._get_chat_state()
        if 'messages' not in chat_state:
            chat_state['messages'] = []
            
        message_id = str(uuid.uuid4())
        
        # If this is a typing indicator, update the existing one if it exists
        if is_typing:
            if chat_state.get('typing_message_id'):
                # Update existing typing message
                for msg in chat_state['messages']:
                    if msg.get('id') == chat_state['typing_message_id']:
                        msg['content'] = content
                        break
            else:
                # Add new typing message
                chat_state['messages'].append({
                    'id': message_id,
                    'content': content,
                    'sender': 'bot',
                    'is_typing': True,
                    'timestamp': datetime.now().isoformat()
                })
                chat_state['typing_message_id'] = message_id
        else:
            # Remove typing indicator if it exists
            if chat_state.get('typing_message_id'):
                chat_state['messages'] = [
                    msg for msg in chat_state['messages'] 
                    if msg.get('id') != chat_state['typing_message_id']
                ]
                chat_state['typing_message_id'] = None
            
            # Add the actual message
            chat_state['messages'].append({
                'id': message_id,
                'content': content,
                'sender': 'bot',
                'timestamp': datetime.now().isoformat()
            })
        
        # Update session state
        self._set_chat_state(chat_state)
        return message_id
    
    def show_typing_indicator(self) -> str:
        """Show typing indicator in the chat.
        
        Returns:
            str: The typing message ID that can be used to remove it later
        """
        return self.add_bot_message("Typing...", is_typing=True)
    
    def render_message(self, message: Dict[str, Any]) -> None:
        """Render a chat message.
        
        Args:
            message: Message data with 'is_user' and 'content' keys
        """
        is_user = message.get("is_user", False)
        content = message.get("content", "")
        metadata = message.get("metadata", {})
        
        if is_user:
            avatar_img = "👤"
            name = "Você"
            message_class = "user"
        else:
            avatar_img = "🤖"
            name = "OntoMed"
            message_class = "bot"
            
            # Adicionar indicador de confiança e fonte para mensagens do bot
            confidence = metadata.get("confidence", None)
            intent = metadata.get("intent", "outro")
            source = metadata.get("source", "unknown")
            
            # Preparar o rodapé da mensagem
            footer_parts = []
            
            # Indicador de confiança
            if confidence is not None:
                if confidence > 0.8:
                    confidence_indicator = "✅ Alta confiança"
                elif confidence > 0.5:
                    confidence_indicator = "⚠️ Média confiança"
                else:
                    confidence_indicator = "❓ Baixa confiança"
                footer_parts.append(confidence_indicator)
            
            # Fonte da resposta
            if source != "unknown":
                source_text = f"Fonte: {source}"
                footer_parts.append(source_text)
            
            # Intenção identificada (apenas para debugging)
            if intent != "outro" and st.session_state.get("debug_mode", False):
                intent_text = f"Intent: {intent}"
                footer_parts.append(intent_text)
            
            # Adicionar rodapé à mensagem se houver informações
            if footer_parts:
                footer = " | ".join(footer_parts)
                content += f"\n\n<small><i>{footer}</i></small>"
        
        # Render the message with markdown support
        st.markdown(f"""
        <div class="chat-message {message_class}">
            <div class="avatar">
                <div style="font-size: 2.5rem; text-align: center;">{avatar_img}</div>
                <div style="text-align: center; font-weight: bold;">{name}</div>
            </div>
            <div class="message">{content}</div>
        </div>
        """, unsafe_allow_html=True)

    def render(self, on_send: Callable[[str], None]) -> None:
        """Render the chat UI.
        
        Args:
            on_send: Function to handle sending messages
        """
        # Initialize session state if not already done
        if not self._initialized:
            self._init_session_state()
        
        # Get chat state
        chat_state = st.session_state.get(self.session_state_key, {})
        
        # Definir estilos CSS para o chat
        chat_styles = """
            <style>
                .chat-container {
                    display: flex;
                    flex-direction: column;
                    height: 100%;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    overflow: hidden;
                    background-color: #f9f9f9;
                }
                
                .chat-header {
                    padding: 10px;
                    background-color: #4CAF50;
                    color: white;
                    font-weight: bold;
                    border-bottom: 1px solid #e0e0e0;
                }
                
                .chat-messages {
                    flex: 1;
                    overflow-y: auto;
                    padding: 10px;
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }
                
                .chat-input-container {
                    padding: 10px;
                    border-top: 1px solid #e0e0e0;
                    background-color: white;
                }
                
                .message-container {
                    display: flex;
                    margin-bottom: 10px;
                    max-width: 80%;
                }
                
                .message-container.user {
                    align-self: flex-end;
                }
                
                .message-container.bot {
                    align-self: flex-start;
                }
                
                .avatar {
                    width: 30px;
                    height: 30px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin-right: 8px;
                    font-size: 16px;
                }
                
                .message-content {
                    padding: 8px 12px;
                    border-radius: 18px;
                    background-color: #E8F5E9;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                }
                
                .message-container.user .message-content {
                    background-color: #E3F2FD;
                }
                
                .typing-indicator {
                    display: flex;
                    align-items: center;
                    padding: 8px 12px;
                    border-radius: 18px;
                    background-color: #f1f1f1;
                    width: fit-content;
                }
                
                .typing-dot {
                    width: 8px;
                    height: 8px;
                    background-color: #999;
                    border-radius: 50%;
                    margin: 0 2px;
                    animation: typing-dot 1.4s infinite ease-in-out both;
                }
                
                .typing-dot:nth-child(1) { animation-delay: 0s; }
                .typing-dot:nth-child(2) { animation-delay: 0.2s; }
                .typing-dot:nth-child(3) { animation-delay: 0.4s; }
                
                @keyframes typing-dot {
                    0%, 80%, 100% { transform: scale(0.7); }
                    40% { transform: scale(1); }
                }
            </style>
        """
        
        # Create a unique key for this chat UI instance
        if 'chat_ui_key' not in st.session_state:
            st.session_state.chat_ui_key = str(uuid.uuid4())
            messages = chat_state.get('messages', [])
            
            # Adicionar estilos CSS para o chat
            st.markdown(chat_styles, unsafe_allow_html=True)
            
            # Create a container for the chat header
            st.markdown(f"""
                <div class="chat-header">
                    <div>💬 {self.title}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # Create a container for the chat messages
            with st.container():
                # Use a container with fixed height and scrolling for messages
                st.markdown("""
                    <div class="chat-messages-container">
                        <div class="chat-messages">
                """, unsafe_allow_html=True)
                
                # Display messages
                for msg in messages:
                    self._render_message(msg)
                
                # Close message container
                st.markdown("</div></div>", unsafe_allow_html=True)
            
            # Create a container for the chat input
            st.markdown("""<div class="chat-input-container"></div>""", unsafe_allow_html=True)
            with st.container():
                # Use columns to create input field and send button
                col1, col2 = st.columns([5, 1])
                
                with col1:
                    # Input field
                    if 'chat_input_key' not in st.session_state:
                        st.session_state.chat_input_key = str(uuid.uuid4())
                        
                    chat_input = st.text_input(
                        "Message",
                        key=st.session_state.chat_input_key,
                        label_visibility="collapsed",
                        placeholder="Type a message..."
                    )
                
                with col2:
                    # Send button
                    send_pressed = st.button("Send", use_container_width=True)
                
                # Handle message sending
                if chat_input and send_pressed:
                    # Armazena a mensagem atual antes de processá-la
                    current_message = chat_input
                    # Limpa o campo de entrada gerando uma nova chave
                    st.session_state.chat_input_key = str(uuid.uuid4())
                    # Processa a mensagem
                    on_send(current_message)
                    # Use st.rerun() para atualizar a UI
                    st.rerun()
            
            # Add custom CSS for the chat UI
            st.markdown("""
                <style>
                    /* Chat messages container */
                    .chat-messages-container {
                        height: calc(100vh - 180px);
                        overflow-y: auto;
                        padding: 0;
                        background: #f9f9f9;
                    }
                    
                    /* Chat messages */
                    .chat-messages {
                        padding: 16px;
                        display: flex;
                        flex-direction: column;
                        min-height: 100%;
                    }
                    
                    /* Make the input field look nicer */
                    .stTextInput > div > div > input {
                        border-radius: 20px;
                        padding-left: 15px;
                    }
                    
                    /* Style the send button */
                    .stButton > button {
                        border-radius: 20px;
                        background-color: #4a86e8;
                        color: white;
                    }
                    
                    /* Hide default Streamlit elements */
                    .block-container {
                        padding-top: 0 !important;
                        padding-bottom: 0 !important;
                    }
                    
                    /* Remove padding from containers */
                    .stContainer {
                        padding: 0 !important;
                    }
                </style>
            """, unsafe_allow_html=True)
