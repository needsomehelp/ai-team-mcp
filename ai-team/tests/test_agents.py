"""Smoke tests for AI Team agent code.

These tests verify agent initialization, readiness checks, error handling,
and response parsing WITHOUT making real API calls. External calls are
mocked so tests run fast and offline.
"""

from unittest.mock import patch, MagicMock

from agents.base import BaseAgent, AgentResult
from agents.session_store import save_session, get_session, remove_session
from agents.gemini_agent import parse_cookie_string


# ── AgentResult ──────────────────────────────────────────────

class TestAgentResult:
    def test_success_result(self):
        r = AgentResult("Test", "coder", "hello", True)
        assert r.success is True
        assert r.content == "hello"
        assert r.error == ""

    def test_failure_result(self):
        r = AgentResult("Test", "coder", "", False, "something broke")
        assert r.success is False
        assert r.error == "something broke"


# ── BaseAgent ────────────────────────────────────────────────

class TestBaseAgent:
    def test_build_prompt_with_context(self):
        class DummyAgent(BaseAgent):
            def execute(self, prompt, context=""):
                return AgentResult(self.name, self.role, "", True)
            def is_ready(self):
                return True

        agent = DummyAgent("Dummy", "coder")
        prompt = agent.build_prompt("do stuff", "project ctx", "be great")
        assert "do stuff" in prompt
        assert "project ctx" in prompt
        assert "be great" in prompt

    def test_build_prompt_without_context(self):
        class DummyAgent(BaseAgent):
            def execute(self, prompt, context=""):
                return AgentResult(self.name, self.role, "", True)
            def is_ready(self):
                return True

        agent = DummyAgent("Dummy", "coder")
        prompt = agent.build_prompt("do stuff", "", "be great")
        assert "do stuff" in prompt
        assert "PROJECT CONTEXT" not in prompt


# ── Session Store ────────────────────────────────────────────

class TestSessionStore:
    def test_save_and_get(self, tmp_path):
        sessions_file = tmp_path / "sessions.json"
        with patch("agents.session_store.SESSIONS_FILE", str(sessions_file)):
            save_session("test_svc", {"key": "val"})
            result = get_session("test_svc")
            assert result == {"key": "val"}

    def test_get_missing_service(self, tmp_path):
        sessions_file = tmp_path / "sessions.json"
        with patch("agents.session_store.SESSIONS_FILE", str(sessions_file)):
            result = get_session("nonexistent")
            assert result == {}

    def test_remove_session(self, tmp_path):
        sessions_file = tmp_path / "sessions.json"
        with patch("agents.session_store.SESSIONS_FILE", str(sessions_file)):
            save_session("to_remove", {"key": "val"})
            remove_session("to_remove")
            assert get_session("to_remove") == {}


# ── Cookie Parsing ───────────────────────────────────────────

class TestCookieParsing:
    def test_parse_cookie_string(self):
        cookies = parse_cookie_string("name1=val1; name2=val2; name3=val3")
        assert cookies == {"name1": "val1", "name2": "val2", "name3": "val3"}

    def test_parse_empty_string(self):
        cookies = parse_cookie_string("")
        assert cookies == {}

    def test_parse_single_cookie(self):
        cookies = parse_cookie_string("session=abc123")
        assert cookies == {"session": "abc123"}

    def test_parse_cookie_with_equals_in_value(self):
        cookies = parse_cookie_string("token=abc=def=ghi; other=val")
        assert cookies["token"] == "abc=def=ghi"
        assert cookies["other"] == "val"


# ── ChatGPT Agent ────────────────────────────────────────────

class TestChatGPTAgent:
    @patch("agents.chatgpt_agent.get_session", return_value={})
    def test_not_ready_without_token(self, mock_session):
        from agents.chatgpt_agent import ChatGPTWebAgent
        agent = ChatGPTWebAgent()
        assert agent.is_ready() is False

    @patch("agents.chatgpt_agent.get_session", return_value={"access_token": "fake"})
    def test_ready_with_token(self, mock_session):
        from agents.chatgpt_agent import ChatGPTWebAgent
        agent = ChatGPTWebAgent()
        assert agent.is_ready() is True

    @patch("agents.chatgpt_agent.get_session", return_value={})
    def test_execute_not_ready(self, mock_session):
        from agents.chatgpt_agent import ChatGPTWebAgent
        agent = ChatGPTWebAgent()
        result = agent.execute("test prompt")
        assert result.success is False
        assert "not logged in" in result.error.lower()

    @patch("agents.chatgpt_agent.get_session", return_value={"access_token": "fake"})
    @patch("requests.post")
    def test_execute_success(self, mock_post, mock_session):
        from agents.chatgpt_agent import ChatGPTWebAgent
        # Simulate SSE stream response — iter_lines with decode_unicode=True returns str
        sse_lines = [
            'data: {"message": {"author": {"role": "assistant"}, "content": {"parts": ["Hello from ChatGPT"]}}}',
            'data: [DONE]',
        ]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.iter_lines.return_value = sse_lines
        mock_post.return_value = mock_response

        agent = ChatGPTWebAgent()
        result = agent.execute("test")
        assert result.success is True
        assert "Hello from ChatGPT" in result.content

    @patch("agents.chatgpt_agent.get_session", return_value={"access_token": "expired"})
    @patch("requests.post")
    def test_execute_auth_expired(self, mock_post, mock_session):
        from agents.chatgpt_agent import ChatGPTWebAgent
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        agent = ChatGPTWebAgent()
        result = agent.execute("test")
        assert result.success is False
        assert "expired" in result.error.lower()

    @patch("agents.chatgpt_agent.get_session", return_value={"access_token": "fake"})
    @patch("requests.post")
    def test_execute_timeout(self, mock_post, mock_session):
        from agents.chatgpt_agent import ChatGPTWebAgent
        import requests
        mock_post.side_effect = requests.exceptions.Timeout()

        agent = ChatGPTWebAgent()
        result = agent.execute("test")
        assert result.success is False
        assert "timed out" in result.error.lower()

    @patch("agents.chatgpt_agent.get_session", return_value={"access_token": "fake"})
    @patch("requests.get")
    @patch("requests.post")
    def test_execute_image_generation(self, mock_post, mock_get, mock_session):
        """ChatGPT returns image_asset_pointer — agent resolves it to a download URL."""
        from agents.chatgpt_agent import ChatGPTWebAgent

        sse_lines = [
            'data: {"message": {"author": {"role": "assistant"}, "content": {"parts": [{"content_type": "image_asset_pointer", "asset_pointer": "file-service://file-abc123"}]}}}',
            'data: [DONE]',
        ]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.iter_lines.return_value = sse_lines
        mock_post.return_value = mock_response

        # Mock the file download URL fetch
        mock_dl_response = MagicMock()
        mock_dl_response.status_code = 200
        mock_dl_response.json.return_value = {"download_url": "https://files.oaistatic.com/img.png"}
        mock_get.return_value = mock_dl_response

        agent = ChatGPTWebAgent()
        result = agent.execute("generate an image of a cat")
        assert result.success is True
        assert "https://files.oaistatic.com/img.png" in result.content

    @patch("agents.chatgpt_agent.get_session", return_value={"access_token": "fake"})
    @patch("requests.get")
    @patch("requests.post")
    def test_execute_image_and_text(self, mock_post, mock_get, mock_session):
        """ChatGPT returns both text and an image — both appear in result."""
        from agents.chatgpt_agent import ChatGPTWebAgent

        sse_lines = [
            'data: {"message": {"author": {"role": "assistant"}, "content": {"parts": ["Here is your image:", {"content_type": "image_asset_pointer", "asset_pointer": "file-service://file-xyz"}]}}}',
            'data: [DONE]',
        ]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.iter_lines.return_value = sse_lines
        mock_post.return_value = mock_response

        mock_dl_response = MagicMock()
        mock_dl_response.status_code = 200
        mock_dl_response.json.return_value = {"download_url": "https://files.oaistatic.com/cat.png"}
        mock_get.return_value = mock_dl_response

        agent = ChatGPTWebAgent()
        result = agent.execute("draw a cat")
        assert result.success is True
        assert "Here is your image:" in result.content
        assert "https://files.oaistatic.com/cat.png" in result.content


# ── Gemini Agent ─────────────────────────────────────────────

class TestGeminiAgent:
    @patch("agents.gemini_agent.get_session", return_value={})
    def test_not_ready_without_credentials(self, mock_session):
        from agents.gemini_agent import GeminiWebAgent
        agent = GeminiWebAgent()
        assert agent.is_ready() is False

    @patch("agents.gemini_agent.get_session", return_value={"api_key": "fake-key"})
    def test_ready_with_api_key(self, mock_session):
        from agents.gemini_agent import GeminiWebAgent
        agent = GeminiWebAgent()
        assert agent.is_ready() is True

    @patch("agents.gemini_agent.get_session", return_value={"cookies": {"sid": "abc"}})
    def test_ready_with_cookies(self, mock_session):
        from agents.gemini_agent import GeminiWebAgent
        agent = GeminiWebAgent()
        assert agent.is_ready() is True

    @patch("agents.gemini_agent.get_session", return_value={})
    def test_execute_not_ready(self, mock_session):
        from agents.gemini_agent import GeminiWebAgent
        agent = GeminiWebAgent()
        result = agent.execute("test")
        assert result.success is False
        assert "not set up" in result.error.lower()

    @patch("agents.gemini_agent.get_session", return_value={"api_key": "fake-key"})
    @patch("requests.post")
    def test_api_success(self, mock_post, mock_session):
        from agents.gemini_agent import GeminiWebAgent
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Gemini says hi"}]}}]
        }
        mock_post.return_value = mock_response

        agent = GeminiWebAgent()
        result = agent.execute("test")
        assert result.success is True
        assert "Gemini says hi" in result.content

    @patch("agents.gemini_agent.get_session", return_value={"api_key": "fake-key"})
    @patch("requests.post")
    def test_api_invalid_key(self, mock_post, mock_session):
        from agents.gemini_agent import GeminiWebAgent
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        agent = GeminiWebAgent()
        result = agent.execute("test")
        assert result.success is False
        assert "invalid api key" in result.error.lower()

    @patch("agents.gemini_agent.get_session", return_value={"api_key": "fake-key"})
    @patch("requests.post")
    def test_api_rate_limit(self, mock_post, mock_session):
        from agents.gemini_agent import GeminiWebAgent
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response

        agent = GeminiWebAgent()
        result = agent.execute("test")
        assert result.success is False
        assert "rate limit" in result.error.lower()

    @patch("agents.gemini_agent.get_session", return_value={"cookies": {"__Secure-1PSID": "fake"}, "api_key": "fallback-key"})
    @patch("agents.gemini_agent.GeminiWebAgent._execute_web", return_value=AgentResult("Gemini", "reviewer", "", False, "web failed"))
    @patch("requests.post")
    def test_web_failure_falls_back_to_api(self, mock_post, mock_web, mock_session):
        from agents.gemini_agent import GeminiWebAgent
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Fallback response"}]}}]
        }
        mock_post.return_value = mock_response

        agent = GeminiWebAgent()
        result = agent.execute("test")
        assert result.success is True
        assert "Fallback response" in result.content


# ── Perplexity Agent ─────────────────────────────────────────

class TestPerplexityAgent:
    @patch("agents.perplexity_agent.get_session", return_value={})
    def test_not_ready_without_credentials(self, mock_session):
        from agents.perplexity_agent import PerplexityWebAgent
        agent = PerplexityWebAgent()
        assert agent.is_ready() is False

    @patch("agents.perplexity_agent.get_session", return_value={"cookies": {"session": "abc"}})
    def test_ready_with_cookies(self, mock_session):
        from agents.perplexity_agent import PerplexityWebAgent
        agent = PerplexityWebAgent()
        assert agent.is_ready() is True

    @patch("agents.perplexity_agent.get_session", return_value={"api_key": "pplx-abc"})
    def test_ready_with_api_key(self, mock_session):
        from agents.perplexity_agent import PerplexityWebAgent
        agent = PerplexityWebAgent()
        assert agent.is_ready() is True

    @patch("agents.perplexity_agent.get_session", return_value={})
    def test_execute_not_ready(self, mock_session):
        from agents.perplexity_agent import PerplexityWebAgent
        agent = PerplexityWebAgent()
        result = agent.execute("test")
        assert result.success is False
        assert "not set up" in result.error.lower()

    @patch("agents.perplexity_agent.get_session", return_value={"api_key": "pplx-abc"})
    @patch("requests.post")
    def test_api_success(self, mock_post, mock_session):
        from agents.perplexity_agent import PerplexityWebAgent
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Research results here"}}],
            "citations": [],
        }
        mock_post.return_value = mock_response

        agent = PerplexityWebAgent()
        result = agent.execute("test")
        assert result.success is True
        assert "Research results" in result.content

    @patch("agents.perplexity_agent.get_session", return_value={"api_key": "pplx-abc"})
    @patch("requests.post")
    def test_api_invalid_key(self, mock_post, mock_session):
        from agents.perplexity_agent import PerplexityWebAgent
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        agent = PerplexityWebAgent()
        result = agent.execute("test")
        assert result.success is False
        assert "invalid api key" in result.error.lower()


# ── Claude Agent ─────────────────────────────────────────────

class TestClaudeAgent:
    def test_default_role(self):
        from agents.claude_agent import ClaudeAgent
        agent = ClaudeAgent()
        assert agent.role == "coder"
        assert "Claude-Coder" in agent.name

    def test_custom_role(self):
        from agents.claude_agent import ClaudeAgent
        agent = ClaudeAgent(role="reviewer")
        assert agent.role == "reviewer"

    def test_invalid_role_defaults_to_coder(self):
        from agents.claude_agent import ClaudeAgent
        agent = ClaudeAgent(role="nonexistent")
        assert agent.role == "coder"

    @patch("subprocess.run")
    def test_execute_success(self, mock_run):
        from agents.claude_agent import ClaudeAgent
        mock_run.return_value = MagicMock(returncode=0, stdout="Code output here")
        agent = ClaudeAgent()
        with patch.object(agent, "_find_claude", return_value="/usr/local/bin/claude"):
            result = agent.execute("write hello world")
            assert result.success is True
            assert "Code output" in result.content

    @patch("subprocess.run")
    def test_execute_empty_output(self, mock_run):
        from agents.claude_agent import ClaudeAgent
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        agent = ClaudeAgent()
        with patch.object(agent, "_find_claude", return_value="/usr/local/bin/claude"):
            result = agent.execute("test")
            assert result.success is False

    def test_execute_cli_not_found(self):
        from agents.claude_agent import ClaudeAgent
        agent = ClaudeAgent()
        with patch.object(agent, "_find_claude", return_value="/nonexistent/claude"):
            with patch("subprocess.run", side_effect=FileNotFoundError()):
                result = agent.execute("test")
                assert result.success is False
                assert "not found" in result.error.lower()


# ── AgentTeam ────────────────────────────────────────────────

class TestAgentTeam:
    def test_init_creates_all_agents(self):
        from agents.team import AgentTeam
        team = AgentTeam()
        assert "coder" in team.agents
        assert "architect" in team.agents
        assert "reviewer" in team.agents
        assert "researcher" in team.agents

    def test_get_agent_status(self):
        from agents.team import AgentTeam
        team = AgentTeam()
        status = team.get_agent_status()
        assert isinstance(status, dict)
        assert set(status.keys()) == {"coder", "architect", "reviewer", "researcher"}
        for v in status.values():
            assert isinstance(v, bool)

    def test_run_single_unknown_role(self):
        from agents.team import AgentTeam
        team = AgentTeam()
        result = team.run_single("nonexistent", "test")
        assert result.success is False
        assert "no agent" in result.error.lower()

    def test_service_name_mapping(self):
        from agents.team import AgentTeam
        team = AgentTeam()
        assert team._service_name("coder") == "claude"
        assert team._service_name("architect") == "chatgpt"
        assert team._service_name("reviewer") == "gemini"
        assert team._service_name("researcher") == "perplexity"

    def test_route_task_research_only(self):
        from agents.team import AgentTeam
        roles = AgentTeam.route_task("research best Python ORMs")
        assert roles == ["researcher"]

    def test_route_task_review_only(self):
        from agents.team import AgentTeam
        roles = AgentTeam.route_task("review this code for security bugs")
        assert "reviewer" in roles
        assert "researcher" not in roles

    def test_route_task_fix_skips_research(self):
        from agents.team import AgentTeam
        roles = AgentTeam.route_task("fix the login bug")
        assert "researcher" not in roles
        assert "architect" not in roles

    def test_route_task_full_pipeline_for_build(self):
        from agents.team import AgentTeam
        roles = AgentTeam.route_task("build a REST API with authentication")
        assert set(roles) == {"researcher", "architect", "coder", "reviewer"}


# ── MCP Server Tools ────────────────────────────────────────

class TestMCPTools:
    def test_status_tool_returns_string(self):
        import sys
        sys.path.insert(0, "/Users/mac/Downloads/all ai model/ai-team")
        from mcp_server import ai_team_status
        result = ai_team_status()
        assert isinstance(result, str)
        assert "AI TEAM STATUS" in result
        assert "Claude Code" in result

    def test_login_unknown_service(self):
        from mcp_server import ai_team_login
        result = ai_team_login(service="unknown", token="abc")
        assert "Unknown service" in result
