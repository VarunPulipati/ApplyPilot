# app/services/ai.py
from __future__ import annotations
import os, json
from typing import Any, Dict
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load .env -> os.environ
load_dotenv()

# cache the client instance
_client_cache: genai.Client | None = None

def get_client() -> genai.Client:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is required (set in env or .env)")
    global _client_cache
    if _client_cache is None:
        _client_cache = genai.Client(api_key=key)
    return _client_cache

def chat_text(system: str, user: str, temperature: float = 0.2) -> str:
    resp = get_client().models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            {"role": "system", "parts": [system]},
            {"role": "user", "parts": [user]},
        ],
        config=types.GenerateContentConfig(temperature=temperature),
    )
    return (getattr(resp, "text", "") or "").strip()

def chat_json(system: str, user: str, temperature: float = 0.2) -> Dict[str, Any]:
    resp = get_client().models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            {"role": "system", "parts": [system]},
            {"role": "user", "parts": [user]},
        ],
        # Ask for JSON directly
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=temperature,
        ),
    )
    try:
        return json.loads(resp.text or "{}")
    except Exception:
        return {}
