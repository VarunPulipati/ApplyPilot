# app/services/ai.py
from __future__ import annotations
import os, json
from typing import Any, Dict
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

_client: genai.Client | None = None

def get_client() -> genai.Client:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is required (set env or .env)")
    global _client
    if _client is None:
        _client = genai.Client(api_key=key)
    return _client

def chat_text(system: str, user: str, temperature: float = 0.2) -> str:
    """
    Send a single-turn prompt with a system instruction.
    """
    resp = get_client().models.generate_content(
        model="gemini-2.5-flash",
        # Message must be a list of Content; each Part needs "text"
        contents=[{"role": "user", "parts": [{"text": user}]}],
        # System prompt goes here (not as a 'system' message)
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
        ),
    )
    return (getattr(resp, "text", "") or "").strip()

def chat_json(system: str, user: str, temperature: float = 0.2) -> Dict[str, Any]:
    """
    Ask for strict JSON. If parsing fails, return {}.
    """
    resp = get_client().models.generate_content(
        model="gemini-2.5-flash",
        contents=[{"role": "user", "parts": [{"text": user}]}],
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            temperature=temperature,
        ),
    )
    try:
        return json.loads(resp.text or "{}")
    except Exception:
        return {}
