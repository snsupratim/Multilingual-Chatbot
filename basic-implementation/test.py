import os
import requests 
from fastapi import FastAPI, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, ValidationError
from dotenv import load_dotenv
from sarvamai import SarvamAI
from fastapi.middleware.cors import CORSMiddleware 

# --- 1. SETUP AND CONFIGURATION ---

load_dotenv()
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
# NEW: Key for securing your FastAPI server
MASTER_API_KEY = os.getenv("MASTER_API_KEY") 
SARVAM_CHAT_API_URL = "https://api.sarvam.ai/v1/chat/completions"

if not SARVAM_API_KEY:
    raise ValueError("SARVAM_API_KEY environment variable not found.")
if not MASTER_API_KEY:
    raise ValueError("MASTER_API_KEY environment variable not found. Please add it to your .env file.")

# Initialize SarvamAI client only for the text translation functionality
try:
    client = SarvamAI(api_subscription_key=SARVAM_API_KEY)
except Exception as e:
    print(f"Error initializing SarvamAI client for translation: {e}")
    client = None

LANGUAGES_MAP = {
    "English": "en-IN",
    "Hindi": "hi-IN",
    "Gujarati": "gu-IN",
    "Bengali": "bn-IN",
    "Kannada": "kn-IN",
    "Punjabi": "pa-IN"
}

# --- 2. SECURITY SETUP ---

# Define the expected header name
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=True)

# Dependency function to validate the API Key
async def get_api_key(api_key: str = Security(API_KEY_HEADER)):
    if api_key == MASTER_API_KEY:
        return api_key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API Key provided.",
    )

# --- 3. Pydantic Models for API Data Structure ---

class Message(BaseModel):
    role: str = Field(description="Role of the speaker: 'user', 'assistant', or 'system'")
    content: str = Field(description="The text content of the message")

class ChatRequest(BaseModel):
    messages: list[Message] = Field(description="The full conversation history to maintain context.")
    target_language: str = Field(description="The display name of the desired response language.")

class ChatResponse(BaseModel):
    reply: str = Field(description="The final, translated response from the assistant.")
    
class TranslateRequest(BaseModel):
    text: str = Field(description="The text to be translated.")
    source_language: str = Field(description="The display name of the source language.")
    target_language: str = Field(description="The display name of the desired target language.")

class TranslateResponse(BaseModel):
    translated_text: str = Field(description="The resulting translated text.")


# --- 4. FastAPI Application ---

app = FastAPI(
    title="Sarvam Multilingual Chat API",
    description="A language-agnostic chatbot API using Sarvam AI for chat and translation."
)

# CORS Fix: Allows the React client to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows all origins (safe for local development)
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (POST, OPTIONS, etc.)
    allow_headers=["*"],
)

@app.post("/chat", response_model=ChatResponse, status_code=200)
# NEW: Apply security dependency
async def handle_chat(request: ChatRequest, api_key: str = Security(get_api_key)): 
    """
    Processes a chat request: Sends history to Sarvam LLM and translates the English response.
    Requires a valid 'X-API-Key' header.
    """
    # ... (Rest of the handle_chat logic remains the same)
    
    # 1. Input Validation and Language Code Extraction
    target_lang_code = LANGUAGES_MAP.get(request.target_language)
    if not target_lang_code:
        available_langs = ", ".join(LANGUAGES_MAP.keys())
        raise HTTPException(status_code=400, detail=f"Unsupported target language: {request.target_language}. Available languages: {available_langs}")

    headers = {
        "Authorization": f"Bearer {SARVAM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # --- SAFER PAYLOAD CONSTRUCTION ---
    # Explicitly convert Pydantic Message models to clean Python dicts
    api_messages_dicts = [
        {"role": msg.role, "content": msg.content} 
        for msg in request.messages
    ]

    payload = {
        "model": "sarvam-m",
        "messages": api_messages_dicts
    }
    # -----------------------------------

    # 2. Call Sarvam LLM (sarvam-m) using direct requests.post
    assistant_reply = ""
    try:
        response = requests.post(SARVAM_CHAT_API_URL, headers=headers, json=payload)
        response.raise_for_status() # Raise exception for 4xx/5xx status codes
        
        response_json = response.json()
        
        # Safely extract the content
        assistant_reply = response_json["choices"][0]["message"]["content"]
        
    except requests.exceptions.RequestException as e:
        # Include the failing response text in the printout for better debugging
        print(f"Sarvam Chat API HTTP Error: {e}")
        try:
             print(f"Sarvam API Response Text: {response.text}")
        except:
             pass
        raise HTTPException(status_code=500, detail="Error communicating with Sarvam Chat Completion API. Check logs for details.")
    except (KeyError, IndexError):
        print(f"Sarvam API returned unexpected structure: {response_json}")
        raise HTTPException(status_code=500, detail="Sarvam API returned an invalid response format.")

    # 3. Translate if required (using the SarvamAI SDK)
    final_reply = assistant_reply
    if target_lang_code != "en-IN":
        if client is None:
             print("Translation client failed to initialize. Returning English response.")
             return ChatResponse(reply=final_reply)

        try:
            translation = client.text.translate(
                input=assistant_reply,
                source_language_code="en-IN",
                target_language_code=target_lang_code,
                speaker_gender="Male" 
            )
            final_reply = translation.translated_text
        except Exception as e:
            print(f"Sarvam Translation API Error: {e}")
            print("Translation failed, returning original English response.")
            pass 

    # 4. Return the final, translated response
    return ChatResponse(reply=final_reply)


@app.post("/translate", response_model=TranslateResponse, status_code=200)
# NEW: Apply security dependency
async def handle_translate(request: TranslateRequest, api_key: str = Security(get_api_key)): 
    """
    Translates text from source to target language using the SarvamAI SDK.
    Requires a valid 'X-API-Key' header.
    """
    if client is None:
        raise HTTPException(status_code=500, detail="Translation service is unavailable.")

    source_code = LANGUAGES_MAP.get(request.source_language)
    target_code = LANGUAGES_MAP.get(request.target_language)

    if not source_code or not target_code:
        raise HTTPException(status_code=400, detail="Invalid source or target language name.")

    try:
        translation = client.text.translate(
            input=request.text,
            source_language_code=source_code,
            target_language_code=target_code,
            speaker_gender="Male" 
        )
        return TranslateResponse(translated_text=translation.translated_text)
    except Exception as e:
        print(f"Sarvam Translation API Error: {e}")
        raise HTTPException(status_code=500, detail="Translation failed due to external API error.")