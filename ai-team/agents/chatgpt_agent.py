"""ChatGPT agent - uses your ChatGPT Plus/Pro subscription via session token.

How it works:
- You copy your session token from browser DevTools (one time)
- This agent sends requests to ChatGPT's internal API using that token
- Same models you get in the browser (GPT-4o, o1, etc.)
- Supports text responses AND image generation (DALL-E via GPT-4o)

Image generation:
- ChatGPT generates images via DALL-E internally
- This agent detects image_asset_pointer parts in the SSE stream
- Fetches the download URL from ChatGPT's files API
- Returns the actual image URL usable in any browser/app
"""

import json
import uuid
try:
    from curl_cffi import requests
    _CURL_CFFI = True
except ImportError:
    import requests
    _CURL_CFFI = False
from .base import BaseAgent, AgentResult
from .session_store import get_session


class ChatGPTWebAgent(BaseAgent):
    BASE_URL = "https://chatgpt.com/backend-api"

    def __init__(self):
        super().__init__("ChatGPT", "architect")
        session = get_session("chatgpt")
        self.access_token = session.get("access_token", "")
        self.cookies = session.get("cookies", {})
        self.device_id = session.get("device_id", self.cookies.get("oai-did", ""))
        self.build_number = session.get("build_number", "")
        self.client_version = session.get("client_version", "")

    def is_ready(self) -> bool:
        return bool(self.access_token)

    def _headers(self, accept="text/event-stream"):
        h = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": accept,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Origin": "https://chatgpt.com",
            "Referer": "https://chatgpt.com/",
            "sec-ch-ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "oai-language": "en-US",
        }
        if self.device_id:
            h["oai-device-id"] = self.device_id
        if self.build_number:
            h["oai-client-build-number"] = self.build_number
        if self.client_version:
            h["oai-client-version"] = self.client_version
        return h

    def _get_sentinel_token(self) -> str:
        """Fetch the chat-requirements sentinel token needed for /conversation."""
        try:
            kwargs = dict(
                headers=self._headers(accept="application/json"),
                cookies=self.cookies or None,
                timeout=15,
            )
            if _CURL_CFFI:
                kwargs["impersonate"] = "chrome131"
            resp = requests.post(
                f"{self.BASE_URL}/sentinel/chat-requirements",
                json={},
                **kwargs,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("token", "")
        except Exception:
            pass
        return ""

    def _get_error_msg(self, response) -> str:
        """Extract real error from response body instead of guessing."""
        try:
            body = response.json()
            detail = body.get("detail", "")
            if detail:
                if "Unusual activity" in detail:
                    return f"Cloudflare blocked request (temporary): {detail[:120]}. Wait a few minutes and try again."
                return detail[:200]
        except Exception:
            pass
        if response.status_code == 401:
            return "Session expired. Run: python3 aiteam.py login chatgpt"
        return f"HTTP {response.status_code} error from ChatGPT"

    def _fetch_image_url(self, asset_pointer: str) -> str:
        """Resolve a ChatGPT asset pointer to a real download URL.
        Handles both schemes:
          - sediment://file_XXXX  (current format)
          - file-service://file-XXXX  (older format)
        """
        # Strip known scheme prefixes to get the raw file ID
        clean_id = asset_pointer
        for prefix in ("sediment://", "file-service://"):
            if clean_id.startswith(prefix):
                clean_id = clean_id[len(prefix):]
                break

        try:
            # Try current endpoint: estuary/content
            get_kwargs = dict(
                headers=self._headers(accept="application/json"),
                cookies=self.cookies or None,
                timeout=30,
            )
            if _CURL_CFFI:
                get_kwargs["impersonate"] = "chrome131"
            resp = requests.get(
                f"{self.BASE_URL}/files/{clean_id}/download",
                **get_kwargs,
            )
            if resp.status_code == 200:
                data = resp.json()
                url = data.get("download_url", "")
                if url:
                    return url
        except Exception:
            pass
        # Fallback: direct estuary content URL (used by ChatGPT web app)
        return f"{self.BASE_URL}/estuary/content?id={clean_id}"

    def _parse_sse_stream(self, response):
        """Parse the SSE stream, collecting text and resolving image URLs."""
        full_text = ""
        image_urls = []

        all_lines = list(response.iter_lines(decode_unicode=True))
        for line in all_lines:
            if not line or not line.startswith("data: "):
                continue
            data_str = line[6:]
            if data_str == "[DONE]":
                break
            try:
                data = json.loads(data_str)
                msg = data.get("message", {})
                # Accept assistant messages and tool/system messages that carry image data
                role = msg.get("author", {}).get("role", "")
                if role not in ("assistant", "tool", ""):
                    continue

                content = msg.get("content", {})
                parts = content.get("parts", [])

                for part in parts:
                    if isinstance(part, str) and part.strip():
                        full_text = part  # keep the latest (most complete) text chunk
                    elif isinstance(part, dict):
                        content_type = part.get("content_type", "")
                        # Image asset returned by DALL-E via GPT-4o
                        if content_type == "image_asset_pointer":
                            asset_pointer = part.get("asset_pointer", "")
                            if asset_pointer:
                                url = self._fetch_image_url(asset_pointer)
                                if url and url not in image_urls:
                                    image_urls.append(url)

            except (json.JSONDecodeError, KeyError):
                continue

        return full_text.strip(), image_urls

    def _api_headers(self):
        """Headers for the official OpenAI API (bypasses Cloudflare WAF)."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _call_api(self, messages: list, model: str = "gpt-4o", max_tokens: int = 1000) -> str:
        """Call OpenAI API directly — works with the session access token."""
        import requests as std_requests
        resp = std_requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=self._api_headers(),
            json={"model": model, "messages": messages, "max_tokens": max_tokens},
            timeout=60,
        )
        if resp.status_code == 401:
            raise Exception("Session expired. Refresh token at https://chatgpt.com/api/auth/session")
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def generate_image(self, prompt: str) -> AgentResult:
        """Generate image via DALL-E 3 using the session token."""
        if not self.is_ready():
            return AgentResult(self.name, self.role, "", False,
                             "ChatGPT not logged in. Run: python3 aiteam.py login chatgpt")
        try:
            import requests as std_requests
            resp = std_requests.post(
                "https://api.openai.com/v1/images/generations",
                headers=self._api_headers(),
                json={"model": "dall-e-3", "prompt": prompt, "n": 1, "size": "1024x1024"},
                timeout=60,
            )
            resp.raise_for_status()
            url = resp.json()["data"][0]["url"]
            return AgentResult(self.name, self.role, f"Image URL: {url}", True)
        except Exception as e:
            return AgentResult(self.name, self.role, "", False, str(e))

    def execute(self, prompt: str, context: str = "") -> AgentResult:
        if not self.is_ready():
            return AgentResult(self.name, self.role, "", False,
                             "ChatGPT not logged in. Run: python3 aiteam.py login chatgpt")

        full_prompt = self.build_prompt(
            prompt, context,
            "Design clean architecture. Plan file structure, data flow, and interfaces. Think step by step."
        )

        try:
            text = self._call_api([{"role": "user", "content": full_prompt}])
            return AgentResult(self.name, self.role, text, True)
        except requests.exceptions.Timeout:
            return AgentResult(self.name, self.role, "", False, "ChatGPT request timed out")
        except Exception as e:
            return AgentResult(self.name, self.role, "", False, str(e))
