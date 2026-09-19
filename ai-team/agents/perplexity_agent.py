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

from .base import BaseAgent, AgentResult, no_image_support, MAX_CONTEXT_CHARS
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
    # Without these, requests still go through -- Perplexity just answers as an
    # anonymous visitor instead of refusing, which is why a stale paste looks like
    # it worked. See _ANON_MARKERS below.
    KEY_COOKIES = ("__Secure-next-auth.session-token", "cf_clearance")

    # Perplexity's reply to a logged-out caller. It comes back as a normal 200 with
    # a normal markdown_block, so nothing else distinguishes it from a real answer.
    _ANON_MARKERS = ("sign up and repeat your request",)

    @staticmethod
    def check_auth(cookies: dict):
        """Ask Perplexity who these cookies belong to.

        Two probes, because Perplexity is migrating off NextAuth: /api/auth/session
        is the legacy one and returns a bare `{}` once the session cookie dies, while
        /rest/user/settings still answers for anonymous visitors -- there, a null
        `subscription_tier` with a zero query count is the giveaway.

        Returns (ok, detail)."""
        try:
            from curl_cffi import requests as cffi_requests

            sess = cffi_requests.Session(impersonate="chrome", cookies=cookies)

            resp = sess.get("https://www.perplexity.ai/api/auth/session", timeout=30)
            data = resp.json() if resp.status_code == 200 else {}
            if isinstance(data, dict) and data.get("user"):
                user = data["user"]
                return True, user.get("email") or "logged in"

            resp = sess.get(
                "https://www.perplexity.ai/rest/user/settings?version=2.18&source=default",
                timeout=30,
            )
            settings = resp.json() if resp.status_code == 200 else {}
            tier = settings.get("subscription_tier") if isinstance(settings, dict) else None
            if tier:
                return True, f"logged in (subscription: {tier})"
            return False, ("anonymous session -- no subscription_tier. The browser profile "
                           "is signed out, or the paste is missing "
                           "__Secure-next-auth.session-token")
        except Exception as e:
            return False, f"could not verify: {e}"

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

    @staticmethod
    def _parse_response(response: dict):
        """Pull (answer, web_results) out of a Perplexity response.

        Handles both shapes. Current responses nest everything in `blocks`
        (markdown_block / web_result_block); older ones had flat `answer` and
        `web_results` keys. Reading only the flat keys silently yields an empty
        answer, which used to fall through to dumping the whole raw envelope."""
        answer = response.get("answer", "") or ""
        sources = response.get("web_results", []) or []

        for block in response.get("blocks", []) or []:
            if not isinstance(block, dict):
                continue
            md = block.get("markdown_block")
            if isinstance(md, dict) and not answer:
                # `answer` is the assembled text; `chunks` is the streamed form of it.
                answer = md.get("answer") or "".join(md.get("chunks") or [])
            web = block.get("web_result_block")
            if isinstance(web, dict) and not sources:
                sources = web.get("web_results") or []

        return answer or "", sources or []

    @staticmethod
    def _build_query(prompt: str, context: str) -> str:
        """Unlike the chat agents, Perplexity's search() sends this text straight into
        its own web search -- it isn't a model just following instructions. Wrapping it
        in build_prompt()'s "You are the researcher... cite sources... best practices"
        framing gets treated as literal search terms, which drags back generic
        docs/versioning pages instead of the real topic (and degrades answer accuracy).
        So skip that framing here and send the task nearly verbatim."""
        if context:
            return f"{prompt}\n\n--- Reference context ---\n{context[:MAX_CONTEXT_CHARS]}"
        return prompt

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
                answer, sources = self._parse_response(response)
                if sources:
                    answer += "\n\n--- Sources ---\n"
                    for i, src in enumerate(sources, 1):
                        url = src.get("url", "")
                        title = src.get("name", src.get("title", ""))
                        answer += f"[{i}] {title}: {url}\n"
                answer = answer.strip()
                if any(m in answer.lower() for m in self._ANON_MARKERS) and len(answer) < 200:
                    # A logged-out session, not a real answer. Reported as "expired"
                    # so execute() falls through to the Labs client.
                    return AgentResult(self.name, self.role, "", False,
                                       "Perplexity answered as a logged-out visitor -- the "
                                       "session cookies have expired. Re-copy the Cookie header "
                                       "from a logged-in perplexity.ai tab and run ai_team_login "
                                       "with service='perplexity'.")
                if answer:
                    return AgentResult(self.name, self.role, answer, True)
                # Returning str(response) here would hand back the entire raw API
                # envelope as a "successful" answer -- pages of UUIDs and metadata
                # with the reply buried inside. Fail loudly instead.
                return AgentResult(self.name, self.role, "", False,
                                   "Could not find an answer in Perplexity's response "
                                   "(its response format may have changed again).")
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

    def execute(self, prompt: str, context: str = "", images: list = None) -> AgentResult:
        if images:
            # The cookie/web and Labs paths have no attachment endpoint wired up here;
            # only api.perplexity.ai accepts image_url blocks, and no api_key is set.
            return AgentResult(self.name, self.role, "", False,
                               no_image_support(self.name, "image input is not wired up yet"))
        if not self.is_ready():
            return AgentResult(self.name, self.role, "", False,
                             "Perplexity not set up. Login with your browser cookies:\n"
                             "1. Go to perplexity.ai → DevTools (F12) → Network tab\n"
                             "2. Click any request to perplexity.ai\n"
                             "3. Copy the entire 'Cookie' request header value\n"
                             "4. Use ai_team_login with service='perplexity', token='<paste cookie string>'")

        full_prompt = self._build_query(prompt, context)

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
