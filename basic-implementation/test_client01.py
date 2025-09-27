import streamlit as st
import requests
import json
from functools import partial

# --- 1. CONFIGURATION ---

# IMPORTANT: This must match the address where you run your FastAPI server.
FASTAPI_BASE_URL = "http://127.0.0.1:8000"
CHAT_ENDPOINT = f"{FASTAPI_BASE_URL}/chat"
TRANSLATE_ENDPOINT = f"{FASTAPI_BASE_URL}/translate"

# Define supported languages (must match the backend's LANGUAGES_MAP)
LANGUAGES = {
    "English": "en-IN",
    "Hindi": "hi-IN",
    "Gujarati": "gu-IN",
    "Bengali": "bn-IN",
    "Kannada": "kn-IN",
    "Punjabi": "pa-IN"
}

# Define the system prompt (will be the first message in the API history)
SYSTEM_PROMPT = "You are a helpful and polite multilingual agricultural assistant. Your responses must be brief, clear, and relevant to farming, crops, weather, and soil health."

# --- 2. SESSION STATE MANAGEMENT ---

st.set_page_config(page_title="Agnostic Chatbot", layout="centered")

# Initialize states
if "active_mode" not in st.session_state:
    st.session_state.active_mode = "Chat"
if "active_lang" not in st.session_state:
    st.session_state.active_lang = "English"
if "chat_histories" not in st.session_state:
    st.session_state.chat_histories = {}
    for lang in LANGUAGES:
        # Initial history: ONLY the system message, ready for the user's first input.
        st.session_state.chat_histories[lang] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
if "master_api_key" not in st.session_state:
    st.session_state.master_api_key = ""
if "translation_output" not in st.session_state:
    st.session_state.translation_output = ""

# --- 3. HELPER FUNCTIONS ---

def get_api_headers():
    """Returns headers including Content-Type and the Master API Key."""
    return {
        "Content-Type": "application/json",
        "X-API-Key": st.session_state.master_api_key 
    }

def call_api(url, payload):
    """Generic function to handle the API call and error checking."""
    if not st.session_state.master_api_key:
        st.error("Please enter your Master API Key in the sidebar.")
        return None

    try:
        response = requests.post(url, json=payload, headers=get_api_headers())
        response.raise_for_status() # Raise exception for 4xx or 5xx errors
        return response.json()
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        error_detail = e.response.json().get("detail", "No detail available.")
        
        if status_code == 401:
            st.error(f"API Error ({status_code} Unauthorized): Invalid API Key. Please check the key in the sidebar.")
        else:
            st.error(f"API Error ({status_code}): {error_detail}")
        st.caption("Please check your FastAPI console for detailed server logs.")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Connection Error: Could not connect to the backend server. Is FastAPI running? ({e})")
        return None

# --- 4. UI SECTIONS (FUNCTIONS) ---

def render_sidebar():
    """Renders the sidebar for mode and language selection, and API key input."""
    with st.sidebar:
        st.markdown("## 🔐 Security & Mode")
        
        # Master API Key Input
        st.text_input(
            "Master API Key", 
            type="password", 
            key="master_api_key",
            placeholder="Enter your MASTER_API_KEY ",
            help="This key secures your FastAPI backend."
        )

        # Mode Selection
        st.markdown("---")
        st.markdown("## ⚙️ Application Mode")
        if st.button("💬 Chat Mode", use_container_width=True, type="primary" if st.session_state.active_mode == "Chat" else "secondary"):
            st.session_state.active_mode = "Chat"
            st.rerun()
        
        if st.button("🌍 Translation Mode", use_container_width=True, type="primary" if st.session_state.active_mode == "Translation" else "secondary"):
            st.session_state.active_mode = "Translation"
            st.rerun()

        # Language Selection (only visible in Chat Mode)
        if st.session_state.active_mode == "Chat":
            st.markdown("---")
            st.markdown("## 🗣️ Chat Language")
            
            # Use a selectbox for languages (cleaner than many buttons)
            selected_lang = st.selectbox(
                "Select Target Language for Chat Replies:", 
                options=list(LANGUAGES.keys()),
                index=list(LANGUAGES.keys()).index(st.session_state.active_lang),
                key="language_selector"
            )
            if selected_lang != st.session_state.active_lang:
                st.session_state.active_lang = selected_lang
                # Rerun is not needed here as selectbox handles state update gracefully

# --- 5. CHAT MODE IMPLEMENTATION ---

def render_chat_mode():
    """Renders the interactive multilingual chat interface."""
    current_lang = st.session_state.active_lang
    current_history = st.session_state.chat_histories[current_lang]

    st.title("💬 Agnostic Lingual Chat Interface")
    st.markdown(f"Target Language: <span style='color:#10b981; font-weight:bold;'>{current_lang}</span>", unsafe_allow_html=True)
    st.caption(f"Using secured endpoint: {CHAT_ENDPOINT}")
    st.divider()

    # Display initial welcome message (not stored in API history)
    if len(current_history) == 1 and current_history[0]["role"] == "system":
        welcome_message = f"Hello! Welcome to the Multilingual Chatbot. Current language is {current_lang}. Ask me anything!"
        with st.chat_message("assistant"):
            st.write(welcome_message)

    # Display subsequent messages (skipping the initial system message)
    for message in current_history:
        if message["role"] != "system":
            with st.chat_message(message["role"]):
                st.write(message["content"])

    # Chat Input
    if user_input := st.chat_input("Type your message here..."):
        # 1. Store user message locally
        user_message_object = {"role": "user", "content": user_input}
        current_history.append(user_message_object)

        # 2. Display the new user message immediately
        with st.chat_message("user"):
            st.write(user_input)

        # 3. Prepare and call API
        payload = {
            "messages": current_history, 
            "target_language": current_lang
        }

        with st.chat_message("assistant"):
            with st.spinner(f"Translating and generating response in {current_lang}..."):
                api_response_data = call_api(CHAT_ENDPOINT, payload)
                
                if api_response_data:
                    assistant_reply = api_response_data.get("reply", "Error: No 'reply' field in API response.")

                    # 4. Store and display assistant response
                    assistant_message_object = {"role": "assistant", "content": assistant_reply}
                    current_history.append(assistant_message_object)
                    st.write(assistant_reply)
        
        st.rerun()


# --- 6. TRANSLATION MODE IMPLEMENTATION ---

def handle_translation(input_text, source_lang, target_lang):
    """Handles the translation API call and updates state."""
    if not input_text:
        st.session_state.translation_output = "Please enter text to translate."
        return

    payload = {
        "text": input_text,
        "source_language": source_lang,
        "target_language": target_lang
    }

    with st.spinner(f"Translating from {source_lang} to {target_lang}..."):
        api_response_data = call_api(TRANSLATE_ENDPOINT, payload)

        if api_response_data:
            st.session_state.translation_output = api_response_data.get("translated_text", "Error: Translation failed.")
        else:
            # Error already displayed by call_api
            st.session_state.translation_output = "Translation request failed."

def render_translation_mode():
    """Renders the dedicated translation interface."""
    st.title("🌍 Direct Translation Tool")
    st.caption(f"Using secured endpoint: {TRANSLATE_ENDPOINT}")
    st.divider()

    col1, col2 = st.columns(2)
    
    with col1:
        source_lang = st.selectbox("Source Language", options=list(LANGUAGES.keys()), index=list(LANGUAGES.keys()).index("English"))
    with col2:
        target_lang = st.selectbox("Target Language", options=list(LANGUAGES.keys()), index=list(LANGUAGES.keys()).index("Hindi"))

    input_text = st.text_area("Input Text", height=150, placeholder="Enter the text you want to translate here.")
    
    # Using partial to pass arguments to the handler function when the button is clicked
    translate_handler = partial(handle_translation, input_text, source_lang, target_lang)

    st.button("Translate", on_click=translate_handler, use_container_width=True, type="primary", disabled=not st.session_state.master_api_key)

    st.markdown("---")
    st.subheader("Translated Output")
    st.code(st.session_state.translation_output, language=LANGUAGES.get(target_lang, "text").split('-')[0].lower())


# --- 7. MAIN APP LOGIC ---

# 1. Render Sidebar first
render_sidebar()

# 2. Render main content based on selected mode
if st.session_state.active_mode == "Chat":
    render_chat_mode()
elif st.session_state.active_mode == "Translation":
    render_translation_mode()
