"""Gemini agent - uses Google AI Studio free API key.

Google's internal Gemini web API changes frequently and is not stable.
Instead, this uses the official Generative Language API with a FREE API key
from https://aistudio.google.com/apikey

The free tier gives you:
- Gemini 2.5 Flash: 500 req/day (free)
- Gemini 2.5 Pro: 25 req/day (free)
- Same models as Gemini Advanced subscription

No credit card needed. Just sign in with Google and create a key.
"""

import json
import requests
from .base import BaseAgent, AgentResult
from .session_store import get_session


class GeminiWebAgent(BaseAgent):
    def __init__(self):
        super().__init__("Gemini", "reviewer")
        session = get_session("gemini")
        self.api_key = session.get("api_key", "")
        self.model = session.get("model", "gemini-2.5-flash")

    def is_ready(self) -> bool:
        return bool(self.api_key)

    def execute(self, prompt: str, context: str = "") -> AgentResult:
        if not self.is_ready():
            return AgentResult(self.name, self.role, "", False,
                             "Gemini not set up. Run: python3 aiteam.py login gemini\n"
                             "Get free API key at: https://aistudio.google.com/apikey")

        full_prompt = self.build_prompt(
            prompt, context,
            "Review code thoroughly. Find bugs, security issues, performance problems. Be specific with line references."
        )

        models_to_try = [self.model, "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-pro"]
        seen = set()
        models_to_try = [m for m in models_to_try if not (m in seen or seen.add(m))]

        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "maxOutputTokens": 8192,
                "temperature": 0.7,
            },
        }

        last_error = ""
        for model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"

            try:
                response = requests.post(url, json=payload, timeout=120)

                if response.status_code == 404:
                    last_error = f"Model {model} not found"
                    continue

                if response.status_code in (401, 403):
                    return AgentResult(self.name, self.role, "", False,
                                      "Invalid API key. Get a new one at: https://aistudio.google.com/apikey")

                if response.status_code == 429:
                    return AgentResult(self.name, self.role, "", False,
                                      "Gemini rate limit hit. Free tier: 500 req/day for Flash, 25/day for Pro.")

                response.raise_for_status()
                data = response.json()

                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return AgentResult(self.name, self.role, text.strip(), True)

            except requests.exceptions.Timeout:
                return AgentResult(self.name, self.role, "", False, "Gemini request timed out")
            except (KeyError, IndexError) as e:
                return AgentResult(self.name, self.role, "", False, f"Unexpected response format: {e}")
            except Exception as e:
                last_error = str(e)
                continue

        return AgentResult(self.name, self.role, "", False, f"All Gemini models failed. Last error: {last_error}")
