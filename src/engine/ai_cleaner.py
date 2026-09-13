"""
AI Text Cleaner using any OpenAI-compatible API (Groq, OpenAI, OpenRouter, DeepSeek, Ollama).
Cleans up punctuation, grammar, capitalization, and filler words from voice dictation.
Never drops text on network or API failures (returns raw local transcript fallback).
"""

import httpx
from typing import Optional, Tuple

DEFAULT_SYSTEM_PROMPT = (
    "You are an expert transcription editor for voice dictation. "
    "Your job is to fix punctuation, capitalization, formatting, numbers, and obvious phonetic speech recognition errors "
    "while strictly preserving the user's exact wording, meaning, language, and tone. "
    "Do NOT add conversational commentary, do NOT add introductory text, and do NOT wrap output in quotation marks. "
    "Output ONLY the cleaned, finalized transcript."
)

class AICleaner:
    def __init__(self, base_url: str = "https://api.groq.com/openai/v1",
                 model: str = "openai/gpt-oss-20b",
                 api_key: str = "",
                 timeout: float = 4.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def test_connection(self) -> Tuple[bool, str]:
        """Verify API key and model availability."""
        if not self.api_key:
            return False, "API key is empty"

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": "ping"}
            ],
            "max_tokens": 5
        }

        try:
            with httpx.Client(timeout=8.0) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    return True, "OK"
                else:
                    return False, f"HTTP {res.status_code}: {res.text[:120]}"
        except Exception as e:
            return False, str(e)

    def clean_text(self, text: str) -> str:
        """
        Cleans up raw transcribed text.
        Returns cleaned text, or original text if API fails.
        """
        if not text or not self.api_key:
            return text

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            "temperature": 0.1,
            "max_tokens": max(150, len(text.split()) * 3)
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    cleaned = data["choices"][0]["message"]["content"].strip()
                    # Strip wrapping quotes if LLM added them
                    if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith('«') and cleaned.endswith('»')):
                        cleaned = cleaned[1:-1].strip()
                    return cleaned if cleaned else text
                else:
                    print(f"[AICleaner] API returned status {res.status_code}. Using raw text.")
                    return text
        except Exception as e:
            print(f"[AICleaner] Request error: {e}. Using raw text.")
            return text
