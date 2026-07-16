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
import requests
from .base import BaseAgent, AgentResult
from .session_store import get_session


class ChatGPTWebAgent(BaseAgent):
    BASE_URL = "https://chatgpt.com/backend-api"

    def __init__(self):
        super().__init__("ChatGPT", "architect")
        session = get_session("chatgpt")
        self.access_token = session.get("access_token", "")

    def is_ready(self) -> bool:
        return bool(self.access_token)

    def _headers(self, accept="text/event-stream"):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": accept,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Origin": "https://chatgpt.com",
            "Referer": "https://chatgpt.com/",
        }

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
            resp = requests.get(
                f"{self.BASE_URL}/files/{clean_id}/download",
                headers=self._headers(accept="application/json"),
                timeout=30,
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

    def _send_conversation(self, prompt: str, model: str = "auto") -> requests.Response:
        """Send a message to ChatGPT and return the streaming response."""
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
        return requests.post(
            f"{self.BASE_URL}/conversation",
            headers=self._headers(),
            json=payload,
            stream=True,
            timeout=180,
        )

    def generate_image(self, prompt: str) -> AgentResult:
        """Ask ChatGPT (GPT-4o + DALL-E) to generate an image and return the CDN URL."""
        if not self.is_ready():
            return AgentResult(self.name, self.role, "", False,
                             "ChatGPT not logged in. Run: python3 aiteam.py login chatgpt")

        # Use gpt-4o explicitly — "auto" may not trigger DALL-E
        # Phrase the request so GPT-4o routes to DALL-E
        image_prompt = f"Please generate an image: {prompt}"

        try:
            response = self._send_conversation(image_prompt, model="gpt-4o")

            if response.status_code in (401, 403):
                return AgentResult(self.name, self.role, "", False,
                                 "Session expired. Run: python3 aiteam.py login chatgpt")
            response.raise_for_status()

            text, image_urls = self._parse_sse_stream(response)

            if image_urls:
                # Fetch the image bytes using auth headers (URL requires session token)
                fetched_urls = []
                for img_url in image_urls:
                    try:
                        r = requests.get(
                            img_url,
                            headers=self._headers(accept="image/*"),
                            timeout=60,
                            stream=True,
                        )
                        if r.status_code == 200:
                            import tempfile
                            ext = "png" if "png" in r.headers.get("content-type", "") else "jpg"
                            tmp = tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False)
                            for chunk in r.iter_content(8192):
                                tmp.write(chunk)
                            tmp.close()
                            fetched_urls.append((img_url, tmp.name))
                    except Exception:
                        fetched_urls.append((img_url, ""))

                lines = []
                if text:
                    lines.append(text)
                for cdn_url, local_path in fetched_urls:
                    lines.append(f"Image URL: {cdn_url}")
                    if local_path:
                        lines.append(f"Saved to: {local_path}")
                return AgentResult(self.name, self.role, "\n".join(lines), True)

            # GPT-4o responded with text only (didn't trigger DALL-E)
            if text:
                return AgentResult(self.name, self.role, text, False,
                                 "ChatGPT responded with text instead of generating an image.")

            return AgentResult(self.name, self.role, "", False,
                             "ChatGPT did not generate an image. It may need DALL-E access.")

        except requests.exceptions.Timeout:
            return AgentResult(self.name, self.role, "", False, "ChatGPT request timed out")
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
            response = self._send_conversation(full_prompt)

            if response.status_code in (401, 403):
                return AgentResult(self.name, self.role, "", False,
                                 "Session expired. Run: python3 aiteam.py login chatgpt")

            response.raise_for_status()

            text, image_urls = self._parse_sse_stream(response)

            # Build combined result — text + image URLs if any were generated
            if image_urls:
                url_block = "\n".join(f"Image URL: {u}" for u in image_urls)
                combined = f"{text}\n\n{url_block}".strip() if text else url_block
                return AgentResult(self.name, self.role, combined, True)

            if text:
                return AgentResult(self.name, self.role, text, True)

            return AgentResult(self.name, self.role, "", False, "Empty response from ChatGPT")

        except requests.exceptions.Timeout:
            return AgentResult(self.name, self.role, "", False, "ChatGPT request timed out")
        except Exception as e:
            return AgentResult(self.name, self.role, "", False, str(e))
