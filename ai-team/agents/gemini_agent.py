"""Gemini agent - supports two authentication methods:

1. Browser Cookies (uses your Gemini Advanced subscription) - via gemini-webapi
2. API Key (free from Google AI Studio) - uses official Generative Language API

Browser Cookies setup (uses your Gemini Advanced subscription):
    1. Log into gemini.google.com in your browser
    2. Open DevTools (F12) -> Application -> Cookies -> gemini.google.com
    3. Copy the value of '__Secure-1PSID' cookie
    4. (Optional) Also copy '__Secure-1PSIDTS' for extended session
    5. Use ai_team_login with service='gemini', token='<paste cookie value>'

API Key setup:
    Get free key at https://aistudio.google.com/apikey
    Free tier: 500 req/day (Flash), 25/day (Pro)
"""

import asyncio
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
        # Extract the specific cookies needed by gemini-webapi
        self.secure_1psid = self.cookies.get("__Secure-1PSID", "")
        self.secure_1psidts = self.cookies.get("__Secure-1PSIDTS", "")

    def is_ready(self) -> bool:
        return bool(self.api_key) or bool(self.secure_1psid) or bool(self.cookies)

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
        """Execute using browser cookies via gemini-webapi (Gemini Advanced subscription)."""
        try:
            from gemini_webapi import GeminiClient

            async def _run():
                client = GeminiClient(
                    secure_1psid=self.secure_1psid,
                    secure_1psidts=self.secure_1psidts,
                )
                await client.init(auto_close=False, auto_refresh=False)
                try:
                    response = await client.generate_content(prompt)
                    return response.text if response and response.text else ""
                finally:
                    await client.close()

            # Run async code in sync context
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # Already in an async context — run in a new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    text = pool.submit(lambda: asyncio.run(_run())).result(timeout=120)
            else:
                text = asyncio.run(_run())

            if text and text.strip():
                return AgentResult(self.name, self.role, text.strip(), True)
            return AgentResult(self.name, self.role, "", False, "Empty response from Gemini")

        except ImportError:
            return AgentResult(self.name, self.role, "", False,
                              "gemini-webapi not installed. Run: pip install gemini-webapi\n"
                              "Or use API key instead: https://aistudio.google.com/apikey")
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "403" in error_msg or "UNAUTHENTICATED" in error_msg:
                return AgentResult(self.name, self.role, "", False,
                                  "Gemini cookies expired. Get fresh ones:\n"
                                  "1. Go to gemini.google.com -> DevTools (F12) -> Application -> Cookies\n"
                                  "2. Copy __Secure-1PSID value\n"
                                  "3. Use ai_team_login with service='gemini', token='<paste>'")
            return AgentResult(self.name, self.role, "", False, f"Gemini web error: {error_msg}")

    def execute(self, prompt: str, context: str = "") -> AgentResult:
        if not self.is_ready():
            return AgentResult(self.name, self.role, "", False,
                             "Gemini not set up. Choose one:\n"
                             "Option A (Browser Cookies - uses your Advanced subscription):\n"
                             "  1. Go to gemini.google.com -> DevTools (F12) -> Application -> Cookies\n"
                             "  2. Copy __Secure-1PSID value\n"
                             "  3. Use ai_team_login with service='gemini', token='<paste>'\n"
                             "Option B (API Key - free): Get key at https://aistudio.google.com/apikey")

        full_prompt = self.build_prompt(
            prompt, context,
            "Review code thoroughly. Find bugs, security issues, performance problems. Be specific with line references."
        )

        # Priority: cookies (Advanced subscription) -> API key
        if self.secure_1psid:
            result = self._execute_web(full_prompt)
            if not result.success and self.api_key:
                return self._execute_api(full_prompt)
            return result
        else:
            return self._execute_api(full_prompt)
