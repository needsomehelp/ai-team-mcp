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

    def _fetch_image_url(self, file_id: str) -> str:
        """Resolve a ChatGPT file-service asset pointer to a real download URL."""
        # file_id arrives as "file-service://file-XXXX" — strip prefix
        clean_id = file_id.replace("file-service://", "")
        try:
            resp = requests.get(
                f"{self.BASE_URL}/files/{clean_id}/download",
                headers=self._headers(accept="application/json"),
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("download_url", "")
        except Exception:
            pass
        return ""

    def _parse_sse_stream(self, response):
        """Parse the SSE stream, collecting text and resolving image URLs."""
        full_text = ""
        image_urls = []

        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            data_str = line[6:]
            if data_str == "[DONE]":
                break
            try:
                data = json.loads(data_str)
                msg = data.get("message", {})
                if msg.get("author", {}).get("role") != "assistant":
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

    def execute(self, prompt: str, context: str = "") -> AgentResult:
        if not self.is_ready():
            return AgentResult(self.name, self.role, "", False,
                             "ChatGPT not logged in. Run: python3 aiteam.py login chatgpt")

        full_prompt = self.build_prompt(
            prompt, context,
            "Design clean architecture. Plan file structure, data flow, and interfaces. Think step by step."
        )

        message_id = str(uuid.uuid4())
        parent_id = str(uuid.uuid4())

        payload = {
            "action": "next",
            "messages": [{
                "id": message_id,
                "author": {"role": "user"},
                "content": {"content_type": "text", "parts": [full_prompt]},
            }],
            "parent_message_id": parent_id,
            "model": "auto",
            "timezone_offset_min": -330,
            "history_and_training_disabled": False,
            "conversation_mode": {"kind": "primary_assistant"},
        }

        try:
            response = requests.post(
                f"{self.BASE_URL}/conversation",
                headers=self._headers(),
                json=payload,
                stream=True,
                timeout=180,
            )

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
