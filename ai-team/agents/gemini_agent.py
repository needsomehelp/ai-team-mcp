"""Gemini agent - supports two authentication methods:

1. API Key (free from Google AI Studio) - uses official Generative Language API
2. Browser Cookies (uses your Gemini Advanced subscription) - uses Gemini's web API

API Key setup:
    Get free key at https://aistudio.google.com/apikey
    Free tier: 500 req/day (Flash), 25/day (Pro)

Browser Cookies setup (uses your Gemini Advanced subscription):
    1. Log into gemini.google.com in your browser
    2. Open DevTools (F12) -> Application -> Cookies -> gemini.google.com
    3. Copy all cookie name/value pairs as a JSON dict
    OR: DevTools -> Network -> click any request -> copy Cookie header value
    4. Use ai_team_login with service='gemini', token='<paste cookies>'
"""

import json
import requests
from .base import BaseAgent, AgentResult
from .session_store import get_session


def parse_cookie_string(cookie_str: str) -> dict:
    """Parse a raw Cookie header string into a dict."""
    cookies = {}
    for pair in cookie_str.split(";"):
        pair = pair.strip()
        if "=" in pair:
            name, value = pair.split("=", 1)
            cookies[name.strip()] = value.strip()
    return cookies


class GeminiWebAgent(BaseAgent):
    def __init__(self):
        super().__init__("Gemini", "reviewer")
        session = get_session("gemini")
        self.api_key = session.get("api_key", "")
        self.model = session.get("model", "gemini-2.5-flash")
        self.cookies = session.get("cookies", {})

    def is_ready(self) -> bool:
        return bool(self.api_key) or bool(self.cookies)

    def _execute_api(self, prompt: str) -> AgentResult:
        """Execute using official API key (free from Google AI Studio)."""
        models_to_try = [self.model, "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-pro"]
        seen = set()
        models_to_try = [m for m in models_to_try if not (m in seen or seen.add(m))]

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
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

    def _execute_web(self, prompt: str) -> AgentResult:
        """Execute using browser cookies (Gemini Advanced subscription)."""
        try:
            # Build cookie string for request
            cookie_str = "; ".join(f"{k}={v}" for k, v in self.cookies.items())

            headers = {
                "Content-Type": "application/json",
                "Cookie": cookie_str,
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Origin": "https://gemini.google.com",
                "Referer": "https://gemini.google.com/",
                "X-Same-Domain": "1",
            }

            # Gemini web API endpoint
            url = "https://gemini.google.com/api/generate"

            payload = {
                "prompt": prompt,
            }

            # Try the BardWebAPI-style request
            # Gemini uses a specific endpoint pattern
            bard_url = "https://gemini.google.com/_/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate"

            # Build the request body in Gemini's expected format
            req_body = json.dumps([None, json.dumps([[prompt], None, None, None, None, None, None, [1]])])

            form_data = {
                "f.req": req_body,
                "at": "",  # Will be extracted from cookies or page
            }

            response = requests.post(
                bard_url,
                headers={
                    "Cookie": cookie_str,
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "https://gemini.google.com",
                    "Referer": "https://gemini.google.com/",
                    "X-Same-Domain": "1",
                },
                data=form_data,
                timeout=120,
            )

            if response.status_code in (401, 403):
                return AgentResult(self.name, self.role, "", False,
                                  "Gemini cookies expired or invalid. Re-copy cookies from browser:\n"
                                  "DevTools -> Application -> Cookies -> gemini.google.com")

            if response.status_code == 429:
                return AgentResult(self.name, self.role, "", False,
                                  "Gemini rate limit hit. Try again later.")

            response.raise_for_status()

            # Parse the response - Gemini returns a complex nested structure
            resp_text = response.text
            # Remove the initial )]}' line if present
            if resp_text.startswith(")]}'"):
                resp_text = resp_text.split("\n", 1)[1] if "\n" in resp_text else resp_text[4:]

            try:
                # Try to parse the streaming response format
                lines = resp_text.strip().split("\n")
                for line in lines:
                    line = line.strip()
                    if not line or not line.startswith("["):
                        continue
                    try:
                        data = json.loads(line)
                        # Navigate the nested structure to find the response text
                        if isinstance(data, list) and len(data) > 0:
                            inner = data[0]
                            if isinstance(inner, list) and len(inner) > 2:
                                inner_str = inner[2]
                                if isinstance(inner_str, str):
                                    parsed = json.loads(inner_str)
                                    if isinstance(parsed, list) and len(parsed) > 4:
                                        candidates = parsed[4]
                                        if isinstance(candidates, list) and len(candidates) > 0:
                                            candidate = candidates[0]
                                            if isinstance(candidate, list) and len(candidate) > 1:
                                                parts = candidate[1]
                                                if isinstance(parts, list) and len(parts) > 0:
                                                    text_part = parts[0]
                                                    if isinstance(text_part, list) and len(text_part) > 0:
                                                        text = text_part[0]
                                                        if isinstance(text, str) and text.strip():
                                                            return AgentResult(self.name, self.role, text.strip(), True)
                    except (json.JSONDecodeError, IndexError, TypeError):
                        continue

                # If structured parsing failed, try to extract any readable text
                return AgentResult(self.name, self.role, "", False,
                                  "Could not parse Gemini web response. Try using API key instead:\n"
                                  "Get free key at: https://aistudio.google.com/apikey")

            except Exception as e:
                return AgentResult(self.name, self.role, "", False, f"Failed to parse Gemini response: {e}")

        except requests.exceptions.Timeout:
            return AgentResult(self.name, self.role, "", False, "Gemini request timed out")
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "403" in error_msg:
                return AgentResult(self.name, self.role, "", False,
                                  "Gemini cookies expired. Re-copy from browser.")
            return AgentResult(self.name, self.role, "", False, f"Gemini web error: {error_msg}")

    def execute(self, prompt: str, context: str = "") -> AgentResult:
        if not self.is_ready():
            return AgentResult(self.name, self.role, "", False,
                             "Gemini not set up. Choose one:\n"
                             "Option A (API Key - recommended): Get free key at https://aistudio.google.com/apikey\n"
                             "Option B (Browser Cookies): Copy cookies from gemini.google.com via DevTools")

        full_prompt = self.build_prompt(
            prompt, context,
            "Review code thoroughly. Find bugs, security issues, performance problems. Be specific with line references."
        )

        # Priority: cookies (Advanced subscription) -> API key
        if self.cookies:
            result = self._execute_web(full_prompt)
            if not result.success and self.api_key:
                # Fall back to API key if cookies fail
                return self._execute_api(full_prompt)
            return result
        else:
            return self._execute_api(full_prompt)
