import streamlit as st
st.set_page_config(page_title="Multilingual Chat", layout="centered")  # must be first

from sarvamai import SarvamAI
from dotenv import load_dotenv
import os
import requests

# Load environment variables
load_dotenv()
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

# Initialize SarvamAI client
client = SarvamAI(api_subscription_key=SARVAM_API_KEY)

# Define supported languages
LANGUAGES = {
    "English": "en-IN",
    "Hindi": "hi-IN",
    "Gujarati": "gu-IN",
    "Bengali": "bn-IN",
    "Kannada": "kn-IN",
    "Punjabi": "pa-IN"
}

# Session state: active language
if "active_lang" not in st.session_state:
    st.session_state.active_lang = "English"

# Session state: initialize chat & display history per language
for lang in LANGUAGES:
    if f"chat_history_{lang}" not in st.session_state:
        st.session_state[f"chat_history_{lang}"] = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]
    if f"display_history_{lang}" not in st.session_state:
        st.session_state[f"display_history_{lang}"] = []

# Sidebar: language buttons
st.sidebar.markdown("## Select Language")
for lang in LANGUAGES:
    if st.sidebar.button(lang):
        st.session_state.active_lang = lang

# Get current language details
current_lang = st.session_state.active_lang
target_lang_code = LANGUAGES[current_lang]
chat_history_key = f"chat_history_{current_lang}"
display_history_key = f"display_history_{current_lang}"

# App Title
st.markdown(f"<h2 style='text-align: center;'>{current_lang} </h2>", unsafe_allow_html=True)
st.divider()

# Display chat messages
for chat in st.session_state[display_history_key]:
    st.markdown(chat, unsafe_allow_html=True)

# Chat input like GPT
with st.form("chat_form", clear_on_submit=True):
    user_input = st.text_input("You", placeholder="Type your message here...", label_visibility="collapsed")
    submitted = st.form_submit_button("Send")

if submitted and user_input.strip():
    # Store user message
    st.session_state[chat_history_key].append({"role": "user", "content": user_input})
    st.session_state[display_history_key].append(
        f"<div style='text-align: right; color: #1e90ff;'><strong>You:</strong> {user_input}</div>"
    )

    # Call Sarvam LLM
    headers = {
        "Authorization": f"Bearer {SARVAM_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "sarvam-m",
        "messages": st.session_state[chat_history_key]
    }

    response = requests.post("https://api.sarvam.ai/v1/chat/completions", headers=headers, json=payload)

    if response.status_code == 200:
        assistant_reply = response.json()["choices"][0]["message"]["content"]

        # Translate only if not already in target language
        if target_lang_code != "en-IN":
            translation = client.text.translate(
                input=assistant_reply,
                source_language_code="en-IN",
                target_language_code=target_lang_code,
                speaker_gender="Male"
            )
            final_reply = translation.translated_text
        else:
            final_reply = assistant_reply

        # Store assistant response
        st.session_state[chat_history_key].append({"role": "assistant", "content": final_reply})
        st.session_state[display_history_key].append(
            f"<div style='text-align: left; color: #10b981;'><strong>Assistant:</strong> {final_reply}</div>"
        )
    else:
        st.error(f"API Error: {response.status_code} - {response.text}")
