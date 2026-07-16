"""Perplexity agent - uses your Perplexity Pro/Max subscription via browser session cookies.

How it works:
- You copy ALL your cookies from browser DevTools (one time)
- This agent sends requests to Perplexity's internal API using those cookies
- Same models you get in the browser (Pro Search, Deep Research, etc.)
- Uses curl_cffi with Chrome impersonation to bypass Cloudflare fingerprinting

How to get cookies (choose one method):

Method A - Cookie header string (easiest):
1. Log into perplexity.ai in your browser
2. Open DevTools (F12) → Network tab → click any request to perplexity.ai
3. Find the "Cookie:" request header → copy the ENTIRE value
4. Use ai_team_login with service='perplexity', token='<paste cookie string>'

Method B - JSON dict:
1. Log into perplexity.ai in your browser
2. Open DevTools → Application → Cookies → perplexity.ai
3. Copy ALL cookie name/value pairs as JSON: {"cookie1": "val1", "cookie2": "val2", ...}
4. Use ai_team_login with service='perplexity', token='<paste JSON>'
"""

from .base import BaseAgent, AgentResult
from .session_store import get_session


def parse_cookie_string(cookie_str: str) -> dict:
    """Parse a raw Cookie header string into a dict.
    Input: 'name1=value1; name2=value2; name3=value3'
    Output: {'name1': 'value1', 'name2': 'value2', 'name3': 'value3'}
    """
    cookies = {}
    for pair in cookie_str.split(";"):
        pair = pair.strip()
        if "=" in pair:
            name, value = pair.split("=", 1)
            cookies[name.strip()] = value.strip()
    return cookies


class PerplexityWebAgent(BaseAgent):
    def __init__(self):
        super().__init__("Perplexity", "researcher")
        session = get_session("perplexity")
        self.cookies = session.get("cookies", {})
        # Legacy: single session token
        if not self.cookies and session.get("session_token"):
            self.cookies = {"next-auth.session-token": session["session_token"]}
            if session.get("csrf_token"):
                self.cookies["next-auth.csrf-token"] = session["csrf_token"]
        # Legacy API key support
        self.api_key = session.get("api_key", "")

    def is_ready(self) -> bool:
        return bool(self.cookies) or bool(self.api_key)

    def _execute_web(self, prompt: str) -> AgentResult:
        """Execute using browser session cookies (free with Pro subscription)."""
        try:
            from perplexity import Client

            client = Client(self.cookies)
            response = client.search(
                prompt,
                mode="pro",
                sources=["web"],
                stream=False,
                language="en-US",
            )

            if isinstance(response, dict):
                answer = response.get("answer", "")
                sources = response.get("web_results", [])
                if sources:
                    answer += "\n\n--- Sources ---\n"
                    for i, src in enumerate(sources, 1):
                        url = src.get("url", "")
                        title = src.get("name", src.get("title", ""))
                        answer += f"[{i}] {title}: {url}\n"
                if answer.strip():
                    return AgentResult(self.name, self.role, answer.strip(), True)
                return AgentResult(self.name, self.role, str(response), True)
            else:
                return AgentResult(self.name, self.role, str(response), True)

        except AssertionError as e:
            return AgentResult(self.name, self.role, "", False,
                             f"Perplexity assertion error: {e}\n"
                             "This usually means cookies are invalid or expired. Re-copy from browser.")
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "403" in error_msg or "unauthorized" in error_msg.lower():
                return AgentResult(self.name, self.role, "", False,
                                 "Session expired. Re-copy ALL cookies from browser:\n"
                                 "DevTools → Network → click request → copy Cookie header value")
            return AgentResult(self.name, self.role, "", False, f"Perplexity web error: {error_msg}")

    def _execute_labs(self, prompt: str) -> AgentResult:
        """Execute using LabsClient (anonymous, no cookies needed, limited models)."""
        try:
            from perplexity import LabsClient

            client = LabsClient()
            response = client.ask(prompt, model="sonar-pro")

            if isinstance(response, dict):
                answer = response.get("output", response.get("answer", str(response)))
                return AgentResult(self.name, self.role, str(answer).strip(), True)
            return AgentResult(self.name, self.role, str(response).strip(), True)

        except Exception as e:
            return AgentResult(self.name, self.role, "", False, f"Perplexity Labs error: {e}")

    def _execute_api(self, prompt: str) -> AgentResult:
        """Execute using paid API key (legacy support)."""
        import requests as req

        try:
            response = req.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "sonar",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 4096,
                },
                timeout=120,
            )

            if response.status_code in (401, 403):
                return AgentResult(self.name, self.role, "", False,
                                 "Invalid API key. Get one at: https://www.perplexity.ai/settings/api")

            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]

            citations = data.get("citations", [])
            if citations:
                content += "\n\n--- Sources ---\n"
                for i, url in enumerate(citations, 1):
                    content += f"[{i}] {url}\n"

            return AgentResult(self.name, self.role, content.strip(), True)

        except Exception as e:
            return AgentResult(self.name, self.role, "", False, str(e))

    def execute(self, prompt: str, context: str = "") -> AgentResult:
        if not self.is_ready():
            return AgentResult(self.name, self.role, "", False,
                             "Perplexity not set up. Login with your browser cookies:\n"
                             "1. Go to perplexity.ai → DevTools (F12) → Network tab\n"
                             "2. Click any request to perplexity.ai\n"
                             "3. Copy the entire 'Cookie' request header value\n"
                             "4. Use ai_team_login with service='perplexity', token='<paste cookie string>'")

        full_prompt = self.build_prompt(
            prompt, context,
            "Research this topic thoroughly. Find relevant docs, examples, best practices. Cite sources with URLs."
        )

        # Priority: cookies (Pro) → API key → Labs (anonymous fallback)
        if self.cookies:
            result = self._execute_web(full_prompt)
            if not result.success and "expired" in (result.error or "").lower():
                # Fall back to Labs if cookies expired
                return self._execute_labs(full_prompt)
            return result
        elif self.api_key:
            return self._execute_api(full_prompt)
        else:
            return self._execute_labs(full_prompt)
