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
from .base import BaseAgent, AgentResult, save_temp_image, rate_limit
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
        # Optional proxy to bypass IP blocks: "http://user:pass@host:port" or "socks5://host:port"
        self.proxy = session.get("proxy", "")

    def _rate_limit(self):
        """Ensure at least 10 seconds between requests to avoid 'unusual activity' detection.
        State lives in base (survives dev-mode module reloads)."""
        rate_limit("chatgpt", 10.0)

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
                    return (
                        "ChatGPT web API blocked: 'Unusual activity detected'. "
                        "This is triggered by too many rapid requests on the account. "
                        "Wait 24-48 hours without hitting /conversation and it will clear. "
                        "Text chat still works via the OpenAI API path."
                    )
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

    def _is_api_key(self) -> bool:
        """True if token is a real OpenAI API key (sk-...) — supports full API including images."""
        return self.access_token.startswith("sk-")

    def _is_jwt_token(self) -> bool:
        """True if token is a ChatGPT web session JWT (eyJ...).
        These work with api.openai.com/v1/chat/completions (model.request scope)
        but NOT with /v1/images/generations — use web conversation for images instead.
        """
        return self.access_token.startswith("eyJ")

    def _api_headers(self):
        """Headers for the official OpenAI API."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _send_conversation(self, prompt: str, model: str = "auto") -> "requests.Response":
        """Send a message via ChatGPT web (session token path) and return the streaming response."""
        self._rate_limit()
        sentinel = self._get_sentinel_token()
        payload = {
            "action": "next",
            "messages": [{
                "id": str(uuid.uuid4()),
                "author": {"role": "user"},
                "content": {"content_type": "text", "parts": [prompt]},
            }],
            "parent_message_id": str(uuid.uuid4()),
            "model": model,
            "timezone_offset_min": -330,
            "history_and_training_disabled": False,
            "conversation_mode": {"kind": "primary_assistant"},
        }
        headers = self._headers()
        if sentinel:
            headers["openai-sentinel-chat-requirements-token"] = sentinel
        kwargs = dict(
            headers=headers,
            cookies=self.cookies or None,
            json=payload,
            stream=True,
            timeout=180,
        )
        if self.proxy:
            kwargs["proxies"] = {"http": self.proxy, "https": self.proxy}
        if _CURL_CFFI:
            kwargs["impersonate"] = "chrome131"
        return requests.post(f"{self.BASE_URL}/conversation", **kwargs)

    def _call_api(self, messages: list, model: str = "gpt-4o", max_tokens: int = 1000) -> str:
        """Call OpenAI API directly — only works with a real sk-... API key."""
        import requests as std_requests
        resp = std_requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=self._api_headers(),
            json={"model": model, "messages": messages, "max_tokens": max_tokens},
            timeout=60,
        )
        if resp.status_code == 401:
            raise Exception("Invalid API key. Use a real OpenAI API key (sk-...) or a web session token.")
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def generate_image(self, prompt: str) -> AgentResult:
        """Generate image via DALL-E 3.

        - sk-... API key → api.openai.com/v1/images/generations (direct, full access)
        - eyJ... JWT token → ChatGPT web conversation (DALL-E triggered via GPT-4o)
        - cookies/session → ChatGPT web conversation
        """
        if not self.is_ready():
            return AgentResult(self.name, self.role, "", False,
                             "ChatGPT not logged in. Run: python3 aiteam.py login chatgpt")

        # --- Path 1: real sk-... API key ---
        if self._is_api_key():
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

        # --- Path 2: eyJ... JWT → OpenAI Responses API with image_generation tool ---
        if self._is_jwt_token():
            try:
                import requests as std_requests
                resp = std_requests.post(
                    "https://api.openai.com/v1/responses",
                    headers=self._api_headers(),
                    json={
                        "model": "gpt-4o",
                        "tools": [{"type": "image_generation"}],
                        "input": f"Generate an image: {prompt}",
                    },
                    timeout=120,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    # Extract image from output blocks
                    for block in data.get("output", []):
                        if block.get("type") == "image_generation_call":
                            b64 = block.get("result", "")
                            if b64:
                                # Save base64 image to a pruned temp dir
                                import base64
                                tmp_path = save_temp_image(base64.b64decode(b64), "png")
                                return AgentResult(self.name, self.role,
                                                 f"Image generated by DALL-E via ChatGPT.\nSaved to: {tmp_path}", True)
                        elif block.get("type") == "message":
                            for part in block.get("content", []):
                                if part.get("type") == "image_url":
                                    url = part.get("image_url", {}).get("url", "")
                                    if url:
                                        return AgentResult(self.name, self.role, f"Image URL: {url}", True)
                elif resp.status_code == 404:
                    pass  # Responses API not available, fall through to web path
                else:
                    pass  # Fall through
            except Exception:
                pass  # Fall through to web conversation path

        # --- Path 3: browser cookies → web conversation (DALL-E via GPT-4o) ---
        try:
            response = self._send_conversation(f"Please generate an image: {prompt}", model="gpt-4o")
            if response.status_code in (401, 403):
                return AgentResult(self.name, self.role, "", False,
                                 self._get_error_msg(response))
            response.raise_for_status()
            text, image_urls = self._parse_sse_stream(response)
            if image_urls:
                lines = ([text] if text else []) + [f"Image URL: {u}" for u in image_urls]
                return AgentResult(self.name, self.role, "\n".join(lines), True)
            if text:
                return AgentResult(self.name, self.role, text, False,
                                 "ChatGPT responded with text instead of an image. Try rephrasing.")
            return AgentResult(self.name, self.role, "", False,
                             "ChatGPT did not generate an image. It may need DALL-E access.")
        except Exception as e:
            return AgentResult(self.name, self.role, "", False, str(e))

    @staticmethod
    def _error_text(e: Exception) -> str:
        """Human-readable error. A bare requests Timeout stringifies to '' (curl_cffi and
        stdlib both), which tells the user nothing — surface it explicitly."""
        if "timeout" in type(e).__name__.lower() or "timed out" in str(e).lower():
            return "Request to ChatGPT timed out. Try again in a moment."
        return str(e) or type(e).__name__

    def execute(self, prompt: str, context: str = "") -> AgentResult:
        if not self.is_ready():
            return AgentResult(self.name, self.role, "", False,
                             "ChatGPT not logged in. Run: python3 aiteam.py login chatgpt")

        full_prompt = self.build_prompt(
            prompt, context,
            "Design clean architecture. Plan file structure, data flow, and interfaces. Think step by step."
        )

        # --- Path 1: sk-... API key OR eyJ... JWT (both work with /v1/chat/completions) ---
        if self._is_api_key() or self._is_jwt_token():
            try:
                text = self._call_api([{"role": "user", "content": full_prompt}])
                return AgentResult(self.name, self.role, text, True)
            except Exception as e:
                return AgentResult(self.name, self.role, "", False, str(e))

        # --- Path 2: web session token / browser cookies ---
        try:
            response = self._send_conversation(full_prompt)
            if response.status_code in (401, 403):
                return AgentResult(self.name, self.role, "", False,
                                 self._get_error_msg(response))
            response.raise_for_status()
            text, image_urls = self._parse_sse_stream(response)
            if image_urls:
                url_block = "\n".join(f"Image URL: {u}" for u in image_urls)
                combined = f"{text}\n\n{url_block}".strip() if text else url_block
                return AgentResult(self.name, self.role, combined, True)
            if text:
                return AgentResult(self.name, self.role, text, True)
            return AgentResult(self.name, self.role, "", False, "Empty response from ChatGPT")
        except Exception as e:
            return AgentResult(self.name, self.role, "", False, self._error_text(e))
