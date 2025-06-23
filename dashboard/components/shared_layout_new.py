"""Shared layout components for all pages with three-panel design (navigation, content, chat)."""
import streamlit as st
import uuid
import inspect
from typing import Callable, Optional, Dict, Any, Tuple
from .chat.chat_ui_new import ChatUI

def setup_shared_layout_content() -> str:
    """Set up shared layout components including the chat UI.
    This should be called after st.set_page_config() has been called in the main script.
    
    Returns:
        str: The selected page name.
    """
    # Add chat autoscroll script
    add_chat_autoscroll_script()
    
    # Initialize chat state
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    
    if 'chat_initialized' not in st.session_state:
        st.session_state.chat_initialized = False
        
    # Initialize rerun flag to prevent infinite loops
    if 'need_rerun' not in st.session_state:
        st.session_state.need_rerun = False
    
    # Add custom CSS for the three-panel layout (navigation, content, chat)
    st.markdown("""
        <style>
            /* Main container adjustments */
            .main .block-container {
                max-width: 100% !important;
                width: 100% !important;
                padding: 0 !important;
                margin: 0 !important;
            }
            
            /* Center content adjustment */
            .row-widget.stButton,
            .row-widget.stDownloadButton,
            .element-container,
            .stMarkdown,
            .stHeader,
            .stText,
            .stDataFrame,
            .stTable,
            .stImage,
            .stMetric {
                padding-left: 0 !important;
                margin-left: 0 !important;
            }
            
            /* Sidebar (left panel) adjustments */
            .css-1d391kg, .css-1wrcr25 {
                width: 14rem !important;
            }
            
            /* Sidebar chat styling */
            .sidebar .stMarkdown h3 {
                margin-top: 0;
                color: #333;
            }
            
            /* Chat message styling */
            .sidebar .stMarkdown p {
                margin-bottom: 8px;
                padding: 8px;
                border-radius: 4px;
                background-color: #f9f9f9;
            }
            
            /* User message styling */
            .sidebar .user-message {
                background-color: #e6f3ff;
                border-left: 3px solid #4a86e8;
            }
            
            /* Assistant message styling */
            .sidebar .assistant-message {
                background-color: #f0f0f0;
                border-left: 3px solid #4CAF50;
            }
            
            /* Divider styling */
            .sidebar hr {
                margin: 8px 0;
                border-color: #e0e0e0;
            }
            
            /* Main content area */
            .main-content {
                width: 100%;
                padding-right: 1rem;
                margin-left: 0 !important;
            }
            
            /* Adjust column positioning and width */
            div[data-testid="column"] {
                padding-left: 0 !important;
                margin-left: 0 !important;
                width: 100% !important;
            }
            
            /* Make center column content expand to fill available space */
            div[data-testid="column"]:nth-child(2) {
                min-width: calc(100% - 320px - 14rem) !important;
                flex-grow: 1 !important;
            }
            
            /* Adjust content width to occupy all available space */
            .stApp > header + div[data-testid="stAppViewContainer"] > div[data-testid="stVerticalBlock"] {
                max-width: calc(100% - 320px) !important;
                width: calc(100% - 320px) !important;
                padding-left: 0 !important;
                padding-right: 20px !important;
                margin-left: 0 !important;
            }
        </style>
        
        <!-- No custom chat panel needed as we're using Streamlit's sidebar -->
    """, unsafe_allow_html=True)
    
    # Add navigation sidebar
    st.sidebar.title("OntoMed Dashboard")
    
    # Navigation
    page = st.sidebar.radio(
        "Navigation",
        ["Home", "Visualizer", "Concepts", "Templates", "Generator"],
        index=0,
        key="main_navigation"
    )
    
    # Initialize chat UI as a singleton
    if not hasattr(st.session_state, 'chat_ui'):
        # Create a single instance of ChatUI
        try:
            chat_ui = ChatUI()
            
            # Initialize chat state
            if hasattr(chat_ui, '_init_session_state'):
                chat_ui._init_session_state()
            
            # Store the instance in session state
            st.session_state.chat_ui = chat_ui
            
            # Explicitly mark as initialized
            st.session_state.chat_initialized = True
        except Exception as e:
            st.error(f"Error creating ChatUI instance: {e}")
            raise
    
    return page

def create_three_column_layout() -> Tuple[object, object]:
    """Create a two-column layout with navigation and content.
    O chat foi movido para a sidebar, então não precisamos mais da coluna direita.
    
    Returns:
        Tuple containing the two columns (left_col, center_col)
    """
    # Add custom CSS to make the layout more responsive
    st.markdown("""
    <style>
        /* Main container adjustments */
        .main .block-container {
            max-width: 100% !important;
            width: 100% !important;
            padding: 1rem !important;
        }
        
        /* Center content adjustment */
        .row-widget.stButton,
        .row-widget.stDownloadButton {
            text-align: center;
        }
        
        /* Make center column content expand to fill available space */
        div[data-testid="column"]:nth-child(2) {
            width: 100% !important;
            flex-grow: 1 !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Create columns with appropriate widths
    # Using a ratio that faz o conteúdo principal ocupar todo o espaço
    left_col, center_col = st.columns([0.01, 0.99])
    
    return left_col, center_col


def check_rerun() -> None:
    """Check if we need to rerun the app and do so if needed.
    This should be called at the end of each page's main function.
    """
    print(f"DEBUG: check_rerun chamado, need_rerun = {st.session_state.get('need_rerun', False)}")
    if st.session_state.get('need_rerun', False):
        # Reset the flag
        st.session_state.need_rerun = False
        print("DEBUG: Executando st.rerun()")
        # Rerun the app
        st.rerun()

def add_chat_autoscroll_script() -> None:
    """Add JavaScript script to auto-scroll chat to the last message."""
    st.markdown("""
    <script>
        // Function to scroll to the last message
        function scrollToBottom() {
            const chatMessages = document.querySelector('.chat-messages');
            if (chatMessages) {
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        }
        
        // Function to configure the mutation observer
        function setupObserver() {
            const chatMessages = document.querySelector('.chat-messages');
            if (chatMessages) {
                // Execute initial scroll
                scrollToBottom();
                
                // Configure observer for future changes
                const observer = new MutationObserver(scrollToBottom);
                observer.observe(chatMessages, { childList: true, subtree: true });
                
                console.log('Chat auto-scroll configured successfully');
            } else {
                // If the element doesn't exist yet, try again after a delay
                setTimeout(setupObserver, 300);
            }
        }
        
        // Start configuration when the DOM is fully loaded
        if (document.readyState === 'complete') {
            setupObserver();
        } else {
            document.addEventListener('DOMContentLoaded', setupObserver);
            // Fallback to ensure the script runs even if the DOMContentLoaded event has already occurred
            setTimeout(setupObserver, 500);
        }
    </script>
    """, unsafe_allow_html=True)

def handle_message(message: str):
    """Handle a message from the chat UI.
    
    Args:
        message: Message from the chat UI
    """
    # Add the message to the chat history
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    
    # Add user message
    st.session_state.chat_messages.append({"is_user": True, "content": message})
    
    # Obter o controlador de chat usando o gerenciador de sessão
    from utils.session_manager import get_chat_controller
    controller = get_chat_controller()
    controller.logger.debug("ChatController obtido para processamento de mensagem")
    
    # Show typing indicator
    st.session_state.thinking = True
    
    try:
        # Process the message
        response_data = controller.process_message(message)
        
        # Extract the response
        response_text = response_data.get('response', "Desculpe, não consegui processar sua mensagem.")
        intent = response_data.get('intent', "outro")
        confidence = response_data.get('confidence', 0.0)
        source = response_data.get('source', "unknown")
        
        # Add response to history
        st.session_state.chat_messages.append({
            "is_user": False, 
            "content": response_text,
            "metadata": {
                "intent": intent,
                "confidence": confidence,
                "source": source
            }
        })
        
        # Register for debugging
        print(f"Message processed: intent={intent}, confidence={confidence:.2f}, source={source}")
    except Exception as e:
        # Handle error
        error_message = f"Desculpe, ocorreu um erro ao processar sua mensagem: {str(e)}"
        st.session_state.chat_messages.append({"is_user": False, "content": error_message})
        print(f"Erro ao processar mensagem: {str(e)}")
    finally:
        # Stop typing indicator
        st.session_state.thinking = False


def render_chat_ui():
    """Render the chat UI below the sidebar.
    """
    # Import uuid here to avoid UnboundLocalError
    import uuid
    
    # Initialize chat messages if not already done
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    
    # Add Font Awesome for icons
    st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        /* Style for the chat panel below the sidebar */
        .chat-panel {
            display: flex;
            flex-direction: column;
            background-color: #f8f9fa;
            border-radius: 10px;
            margin-top: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            height: auto;
            max-height: 600px;
            overflow: hidden;
        }
        
        .chat-header {
            padding: 10px;
            background: linear-gradient(135deg, #2c7be5 0%, #1a68d1 100%);
            color: white;
            border-radius: 10px 10px 0 0;
            font-weight: bold;
            margin-bottom: 0;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            letter-spacing: 0.5px;
        }
        
        .chat-messages-container {
            flex-grow: 1;
            overflow-y: auto;
            padding: 0;
            background-color: transparent;
            max-height: 400px;
            min-height: 60px;
            scrollbar-width: thin;
            scrollbar-color: rgba(155, 155, 155, 0.5) transparent;
        }
        
        /* Scrollbar styling for WebKit browsers (Chrome, Safari) */
        .chat-messages-container::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        
        .chat-messages-container::-webkit-scrollbar-track {
            background: #f8f9fa;
            border-radius: 4px;
        }
        
        .chat-messages-container::-webkit-scrollbar-thumb {
            background-color: rgba(108, 117, 125, 0.4);
            border-radius: 4px;
            border: 2px solid transparent;
        }
        
        .chat-messages::-webkit-scrollbar-thumb:hover {
            background-color: rgba(108, 117, 125, 0.6);
        }
        
        .chat-message {
            padding: 10px 14px;
            border-radius: 12px;
            margin-bottom: 10px;
            max-width: 85%;
            word-wrap: break-word;
            display: flex;
            align-items: flex-start;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            line-height: 1.4;
            color: #333;
        }
        
        .welcome-message {
            margin-top: 0;
            margin-bottom: 0; /* Remove bottom margin */
            border-radius: 0 0 12px 12px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        }
        
        /* Adjust padding of the messages container when only the welcome message is present */
        .chat-messages-container {
            padding-top: 0;
        }
        
        .chat-message.user {
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            margin-left: auto;
            border-radius: 12px 12px 0 12px;
            flex-direction: row-reverse;
            border-left: 1px solid #bbdefb;
            border-top: 1px solid #bbdefb;
        }
        
        .chat-message.bot {
            background: linear-gradient(135deg, #f5f5f5 0%, #eeeeee 100%);
            margin-right: auto;
            border-radius: 12px 12px 12px 0;
            border-right: 1px solid #e0e0e0;
            border-top: 1px solid #e0e0e0;
        }
        
        .chat-avatar {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 8px;
            font-weight: bold;
            color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .chat-avatar.user {
            background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);
        }
        
        .chat-avatar.bot {
            background: linear-gradient(135deg, #4CAF50 0%, #388E3C 100%);
        }
        
        .chat-content {
            padding: 0 8px;
            font-size: 0.95rem;
            color: #333 !important;
        }
        
        .chat-input {
            padding: 12px;
            background-color: white;
            border-radius: 0 0 10px 10px;
            border-top: 1px solid #f0f0f0;
            box-shadow: 0 -2px 5px rgba(0,0,0,0.02);
        }
        
        /* Ajustes para o input e botão */
        .chat-input .stTextInput > div > div > input {
            border-radius: 20px;
            border: 1px solid #dee2e6;
            padding: 10px 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            transition: all 0.2s ease;
        }
        
        .chat-input .stTextInput > div > div > input:focus {
            border-color: #2c7be5;
            box-shadow: 0 0 0 3px rgba(44, 123, 229, 0.15);
        }
        
        .chat-input .stButton > button {
            background: linear-gradient(135deg, #2c7be5 0%, #1a68d1 100%);
            color: white;
            border-radius: 20px;
            border: none;
            width: 100%;
            font-weight: 500;
            padding: 4px 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: all 0.2s ease;
        }
        
        .chat-input .stButton > button:hover {
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            transform: translateY(-1px);
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Render the chat in the sidebar
    with st.sidebar:
        # Add space between navigation and chat
        st.markdown("<hr/>", unsafe_allow_html=True)
        
        # Create the chat container
        chat_container = st.container()
        
        with chat_container:
            # Chat header
            st.markdown("""<div class="chat-panel"><div class="chat-header">💬 OntoMed Assistant</div>""", unsafe_allow_html=True)
            
            # Messages area
            st.markdown("""<div class="chat-messages-container">""", unsafe_allow_html=True)
        
        with chat_container:
            # Display messages
            if not st.session_state.chat_messages:
                st.markdown("""
                <div class='chat-message bot welcome-message'>
                    <div class='chat-avatar bot'><i class="fas fa-robot"></i></div>
                    <div class='chat-content'>
                        <strong>Bem-vindo ao OntoMed Assistant!</strong><br>
                        Estou aqui para ajudar com suas dúvidas sobre a ontologia médica. 
                        Você pode me perguntar sobre conceitos, relacionamentos ou como navegar pelo dashboard.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                for msg in st.session_state.chat_messages:
                    if msg['is_user']:
                        st.markdown(f"""
                        <div class='chat-message user'>
                            <div class='chat-avatar user'><i class="fas fa-user"></i></div>
                            <div class='chat-content'>{msg['content']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class='chat-message bot'>
                            <div class='chat-avatar bot'><i class="fas fa-robot"></i></div>
                            <div class='chat-content'>{msg['content']}</div>
                        </div>
                        """, unsafe_allow_html=True)
        
        with chat_container:
            # Close the messages container
            st.markdown("</div><!-- End chat-messages-container -->", unsafe_allow_html=True)
            
            # Text input area
            st.markdown("<div class='chat-input'>", unsafe_allow_html=True)
            
            # Generate a unique key for the input if it doesn't exist
            if 'chat_input_key' not in st.session_state:
                st.session_state.chat_input_key = str(uuid.uuid4())
            
            # Use the unique key for the input
            prompt = st.text_input(
                "Mensagem", 
                key=st.session_state.chat_input_key,
                label_visibility="collapsed",
                placeholder="Digite sua pergunta aqui..."
            )
            
            send_pressed = st.button("Enviar", key="send_button")
            
            # Check if we have a new message to process
            if prompt and send_pressed:
                handle_message(prompt)
                
                # Clear the input after sending
                st.session_state.chat_input_key = str(uuid.uuid4())
                
                # Reload page to show a new message
                st.rerun()
            
            # Close the input area and panel
            st.markdown("</div><!-- Fim chat-input --></div><!-- Fim chat-panel -->", unsafe_allow_html=True)
