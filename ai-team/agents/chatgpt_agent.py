"""ChatGPT agent - uses your ChatGPT Plus/Pro subscription via session token.

How it works:
- You copy your session token from browser DevTools (one time)
- This agent sends requests to ChatGPT's internal API using that token
- Same models you get in the browser (GPT-4o, o1, etc.)
"""

import json
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

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Origin": "https://chatgpt.com",
            "Referer": "https://chatgpt.com/",
        }

    def execute(self, prompt: str, context: str = "") -> AgentResult:
        if not self.is_ready():
            return AgentResult(self.name, self.role, "", False,
                             "ChatGPT not logged in. Run: python3 aiteam.py login chatgpt")

        full_prompt = self.build_prompt(
            prompt, context,
            "Design clean architecture. Plan file structure, data flow, and interfaces. Think step by step."
        )

        import uuid
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

            if response.status_code == 401 or response.status_code == 403:
                return AgentResult(self.name, self.role, "", False,
                                 "Session expired. Run: python3 aiteam.py login chatgpt")

            response.raise_for_status()

            # Parse SSE stream to get final response
            full_text = ""
            for line in response.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    msg = data.get("message", {})
                    if msg.get("author", {}).get("role") == "assistant":
                        parts = msg.get("content", {}).get("parts", [])
                        if parts:
                            full_text = parts[0]
                except (json.JSONDecodeError, KeyError):
                    continue

            if full_text.strip():
                return AgentResult(self.name, self.role, full_text.strip(), True)
            return AgentResult(self.name, self.role, "", False, "Empty response from ChatGPT")

        except requests.exceptions.Timeout:
            return AgentResult(self.name, self.role, "", False, "ChatGPT request timed out")
        except Exception as e:
            return AgentResult(self.name, self.role, "", False, str(e))
