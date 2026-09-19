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
    @patch("agents.chatgpt_agent.ChatGPTWebAgent._get_client")
    def test_execute_success(self, mock_client, mock_session):
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
        mock_client.return_value.post.return_value = mock_response

        agent = ChatGPTWebAgent()
        result = agent.execute("test")
        assert result.success is True
        assert "Hello from ChatGPT" in result.content

    @patch("agents.chatgpt_agent.get_session", return_value={"access_token": "expired"})
    @patch("requests.post")
    def test_execute_auth_expired(self, mock_client, mock_session):
        from agents.chatgpt_agent import ChatGPTWebAgent
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_client.return_value.post.return_value = mock_response

        agent = ChatGPTWebAgent()
        result = agent.execute("test")
        assert result.success is False
        assert "expired" in result.error.lower()

    @patch("agents.chatgpt_agent.get_session", return_value={"access_token": "fake"})
    @patch("agents.chatgpt_agent.ChatGPTWebAgent._get_client")
    def test_execute_timeout(self, mock_client, mock_session):
        from agents.chatgpt_agent import ChatGPTWebAgent
        import requests
        mock_client.return_value.post.side_effect = requests.exceptions.Timeout()

        agent = ChatGPTWebAgent()
        result = agent.execute("test")
        assert result.success is False
        assert "timed out" in result.error.lower()

    @patch("agents.chatgpt_agent.get_session", return_value={"access_token": "fake"})
    @patch("agents.chatgpt_agent.ChatGPTWebAgent._get_client")
    def test_execute_image_generation(self, mock_client, mock_session):
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
        mock_client.return_value.post.return_value = mock_response

        # Mock the file download URL fetch
        mock_dl_response = MagicMock()
        mock_dl_response.status_code = 200
        mock_dl_response.json.return_value = {"download_url": "https://files.oaistatic.com/img.png"}
        mock_client.return_value.get.return_value = mock_dl_response

        agent = ChatGPTWebAgent()
        result = agent.execute("generate an image of a cat")
        assert result.success is True
        assert "https://files.oaistatic.com/img.png" in result.content

    @patch("agents.chatgpt_agent.get_session", return_value={"access_token": "fake"})
    @patch("agents.chatgpt_agent.ChatGPTWebAgent._get_client")
    def test_execute_image_and_text(self, mock_client, mock_session):
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
        mock_client.return_value.post.return_value = mock_response

        mock_dl_response = MagicMock()
        mock_dl_response.status_code = 200
        mock_dl_response.json.return_value = {"download_url": "https://files.oaistatic.com/cat.png"}
        mock_client.return_value.get.return_value = mock_dl_response

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


# ── Image input (vision) ─────────────────────────────────────

class TestLoadImages:
    """These bytes get uploaded to a third-party model, so the content check is the
    load-bearing part: only real images may leave the machine."""

    PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32

    def _png(self, tmp_path, name="shot.png"):
        p = tmp_path / name
        p.write_bytes(self.PNG)
        return str(p)

    def test_loads_a_real_image(self, tmp_path):
        from agents.base import load_images
        images, notes = load_images([self._png(tmp_path)])
        assert notes == []
        assert len(images) == 1
        assert images[0]["mime"] == "image/png"
        assert images[0]["name"] == "shot.png"
        assert images[0]["data"] == self.PNG

    def test_sniffs_content_not_extension(self, tmp_path):
        """A secrets file renamed to .png must not be uploaded."""
        from agents.base import load_images
        fake = tmp_path / "totally_an_image.png"
        fake.write_text("OPENAI_API_KEY=sk-secret")
        images, notes = load_images([str(fake)])
        assert images == []
        assert "not a PNG/JPEG/GIF/WEBP image" in notes[0]

    def test_detects_jpeg_with_wrong_extension(self, tmp_path):
        from agents.base import load_images
        p = tmp_path / "photo.txt"
        p.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 32)
        images, _ = load_images([str(p)])
        assert len(images) == 1 and images[0]["mime"] == "image/jpeg"

    def test_oversized_image_is_skipped(self, tmp_path):
        from agents.base import load_images, MAX_IMAGE_BYTES
        big = tmp_path / "big.png"
        big.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * MAX_IMAGE_BYTES)
        images, notes = load_images([str(big)])
        assert images == []
        assert "exceeds" in notes[0]

    def test_missing_file_is_reported_not_raised(self, tmp_path):
        from agents.base import load_images
        images, notes = load_images([str(tmp_path / "nope.png")])
        assert images == []
        assert "not found" in notes[0]

    def test_caps_the_number_of_images(self, tmp_path):
        from agents.base import load_images, MAX_IMAGES
        paths = [self._png(tmp_path, f"s{i}.png") for i in range(MAX_IMAGES + 2)]
        images, notes = load_images(paths)
        assert len(images) == MAX_IMAGES
        assert len(notes) == 2

    def test_empty_input_is_harmless(self):
        from agents.base import load_images
        assert load_images(None) == ([], [])
        assert load_images([]) == ([], [])


class TestAgentsWithoutVision:
    """Agents that can't send images must say so — an answer that never saw the
    screenshot but doesn't admit it is worse than an error."""

    IMG = [{"path": "x.png", "name": "x.png", "data": b"", "mime": "image/png",
            "ext": "png", "width": 1, "height": 1}]

    def test_perplexity_reports_no_image_support(self):
        from agents.perplexity_agent import PerplexityWebAgent
        r = PerplexityWebAgent().execute("what is this", images=self.IMG)
        assert r.success is False
        assert "cannot accept image input" in r.error

    def test_claude_cli_reports_no_image_support(self):
        from agents.claude_agent import ClaudeAgent
        r = ClaudeAgent().execute("what is this", images=self.IMG)
        assert r.success is False
        assert "cannot accept image input" in r.error


class TestImageSize:
    """ChatGPT's upload API needs real pixel dimensions; zeros make it ignore the image."""

    def test_png_dimensions(self):
        import struct, zlib
        from agents.base import image_size
        def chunk(tag, data):
            c = tag + data
            return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))
        png = (b"\x89PNG\r\n\x1a\n"
               + chunk(b"IHDR", struct.pack(">IIBBBBB", 320, 240, 8, 2, 0, 0, 0)))
        assert image_size(png) == (320, 240)

    def test_gif_dimensions(self):
        import struct
        from agents.base import image_size
        assert image_size(b"GIF89a" + struct.pack("<HH", 64, 48)) == (64, 48)

    def test_jpeg_dimensions_from_sof(self):
        import struct
        from agents.base import image_size
        # SOI, a padding segment, then SOF0 carrying height/width.
        jpeg = (b"\xff\xd8\xff\xe0" + struct.pack(">H", 4) + b"\x00\x00"
                + b"\xff\xc0" + struct.pack(">H", 11) + b"\x08"
                + struct.pack(">HH", 200, 150) + b"\x00\x00\x00")
        assert image_size(jpeg) == (150, 200)

    def test_unknown_bytes_are_zero_not_an_exception(self):
        from agents.base import image_size
        assert image_size(b"not an image at all") == (0, 0)
        assert image_size(b"") == (0, 0)


class TestChatGPTVision:
    """Images must ride the Plus/Pro subscription (web upload), not API credits."""

    IMG = {"path": "x.png", "name": "x.png", "data": b"PNGBYTES",
           "mime": "image/png", "ext": "png", "width": 320, "height": 240}

    def _agent(self):
        from agents.chatgpt_agent import ChatGPTWebAgent
        agent = ChatGPTWebAgent()
        agent.access_token = "eyJfake"
        return agent

    def test_subscription_upload_is_tried_before_the_api(self):
        agent = self._agent()
        stream = MagicMock()
        stream.status_code = 200

        with patch.object(agent, "_upload_image", return_value=("file-123", "")) as up, \
             patch.object(agent, "_send_conversation", return_value=stream) as send, \
             patch.object(agent, "_parse_sse_stream", return_value=("Magenta", [])), \
             patch.object(agent, "_call_api") as api:
            result = agent.execute("what colour?", images=[self.IMG])

        assert result.success is True
        assert result.content == "Magenta"
        up.assert_called_once()
        # The billing-limited API path must not be touched when the upload works.
        api.assert_not_called()
        assert send.call_args.kwargs["images"] == [("file-123", self.IMG)]

    def test_attachment_metadata_accompanies_the_pointer(self):
        """The asset pointer alone renders the image but never shows it to the model."""
        agent = self._agent()
        captured = {}

        def fake_post(url, headers=None, json=None, stream=None, timeout=None):
            captured["payload"] = json
            resp = MagicMock()
            resp.status_code = 200
            return resp

        with patch.object(agent, "_rate_limit"), \
             patch.object(agent, "_get_sentinel_token", return_value=("t", "p")), \
             patch.object(agent, "_get_client") as client:
            client.return_value.post.side_effect = fake_post
            agent._send_conversation("look", images=[("file-123", self.IMG)])

        message = captured["payload"]["messages"][0]
        assert message["content"]["content_type"] == "multimodal_text"
        pointer = message["content"]["parts"][0]
        assert pointer["asset_pointer"] == "file-service://file-123"
        assert (pointer["width"], pointer["height"]) == (320, 240)
        assert message["content"]["parts"][-1] == "look"
        attachment = message["metadata"]["attachments"][0]
        assert attachment["id"] == "file-123"
        assert attachment["mimeType"] == "image/png"

    def test_upload_failure_surfaces_instead_of_answering_blind(self):
        agent = self._agent()
        from agents.chatgpt_agent import ChatGPTWebAgent
        ChatGPTWebAgent._api_quota_exhausted = True  # no API credits, as on a Plus plan
        try:
            with patch.object(agent, "_upload_image", return_value=("", "blob upload failed (500)")):
                result = agent.execute("what colour?", images=[self.IMG])
        finally:
            ChatGPTWebAgent._api_quota_exhausted = False

        assert result.success is False
        assert "could not read the image" in result.error
        assert "blob upload failed" in result.error

    def test_api_key_path_inlines_data_uris(self):
        import base64
        agent = self._agent()
        agent.access_token = "sk-realkey"
        captured = {}

        def fake_call_api(messages, **kw):
            captured["messages"] = messages
            return "I see magenta."

        with patch.object(agent, "_call_api", side_effect=fake_call_api), \
             patch.object(agent, "_upload_image") as up:
            result = agent.execute("what colour?", images=[self.IMG])

        assert result.success is True
        # A real API key has quota, so the upload round-trips are pointless.
        up.assert_not_called()
        content = captured["messages"][0]["content"]
        assert content[0]["type"] == "text"
        expected = "data:image/png;base64," + base64.b64encode(b"PNGBYTES").decode()
        assert content[1]["image_url"]["url"] == expected


class TestGeminiVision:
    def test_images_are_passed_to_the_uploader(self, tmp_path):
        """The cookie/subscription path must hand the file to generate_content."""
        from agents.gemini_agent import GeminiWebAgent
        p = tmp_path / "shot.png"
        p.write_bytes(b"\x89PNG\r\n\x1a\n")
        images = [{"path": str(p), "name": "shot.png", "data": b"",
                   "mime": "image/png", "ext": "png"}]

        agent = GeminiWebAgent()
        agent.cookies = {"__Secure-1PSID": "x"}
        agent.secure_1psid = "x"

        captured = {}

        class FakeResponse:
            text = "I see a red square."

        class FakeClient:
            def __init__(self, **kw):
                pass
            async def init(self, **kw):
                pass
            async def generate_content(self, prompt, files=None, **kw):
                captured["files"] = files
                captured["prompt"] = prompt
                return FakeResponse()
            async def close(self):
                pass

        fake_module = MagicMock()
        fake_module.GeminiClient = FakeClient
        with patch.dict("sys.modules", {"gemini_webapi": fake_module}):
            result = agent.execute("What is in this image?", images=images)

        assert result.success is True
        assert captured["files"] == [str(p)]
        assert "shot.png" in captured["prompt"]

    def test_no_images_sends_files_as_none(self, tmp_path):
        """An empty list must not be passed through as files=[]."""
        from agents.gemini_agent import GeminiWebAgent
        agent = GeminiWebAgent()
        agent.cookies = {"__Secure-1PSID": "x"}
        agent.secure_1psid = "x"
        captured = {}

        class FakeResponse:
            text = "hello"

        class FakeClient:
            def __init__(self, **kw):
                pass
            async def init(self, **kw):
                pass
            async def generate_content(self, prompt, files=None, **kw):
                captured["files"] = files
                return FakeResponse()
            async def close(self):
                pass

        fake_module = MagicMock()
        fake_module.GeminiClient = FakeClient
        with patch.dict("sys.modules", {"gemini_webapi": fake_module}):
            agent.execute("hi")
        assert captured["files"] is None

    def test_api_path_encodes_inline_data(self, tmp_path):
        """The API-key path must send inline_data parts before the text part."""
        import base64
        from agents.gemini_agent import GeminiWebAgent
        agent = GeminiWebAgent()
        agent.api_key = "test-key"
        agent.secure_1psid = ""
        images = [{"path": "x.png", "name": "x.png", "data": b"IMGBYTES",
                   "mime": "image/png", "ext": "png"}]

        captured = {}

        def fake_post(url, json=None, timeout=None):
            captured["payload"] = json
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {
                "candidates": [{"content": {"parts": [{"text": "ok"}]}}]
            }
            return resp

        with patch("agents.gemini_agent.requests.post", side_effect=fake_post):
            result = agent.execute("describe", images=images)

        assert result.success is True
        parts = captured["payload"]["contents"][0]["parts"]
        assert parts[0]["inline_data"]["mime_type"] == "image/png"
        assert parts[0]["inline_data"]["data"] == base64.b64encode(b"IMGBYTES").decode()
        assert "text" in parts[-1]


class TestPerplexityResponseParsing:
    """The subscription (cookie) path returns a nested `blocks` envelope. Reading only
    the old flat keys yielded an empty answer and dumped the whole raw dict as if it
    had succeeded."""

    def _parse(self, response):
        from agents.perplexity_agent import PerplexityWebAgent
        return PerplexityWebAgent._parse_response(response)

    def test_parses_the_nested_blocks_shape(self):
        answer, sources = self._parse({
            "blocks": [
                {"intended_usage": "ask_text",
                 "markdown_block": {"progress": "DONE", "chunks": ["OK"], "answer": "OK"}},
                {"intended_usage": "web_results",
                 "web_result_block": {"web_results": [{"name": "Docs", "url": "https://x.dev"}]}},
            ],
        })
        assert answer == "OK"
        assert sources[0]["url"] == "https://x.dev"

    def test_falls_back_to_streamed_chunks(self):
        answer, _ = self._parse({
            "blocks": [{"markdown_block": {"chunks": ["Hel", "lo"]}}],
        })
        assert answer == "Hello"

    def test_still_reads_the_old_flat_shape(self):
        answer, sources = self._parse({
            "answer": "flat answer",
            "web_results": [{"name": "Old", "url": "https://old.dev"}],
        })
        assert answer == "flat answer"
        assert sources[0]["url"] == "https://old.dev"

    def test_unrecognised_shape_yields_nothing_to_report(self):
        answer, sources = self._parse({"backend_uuid": "abc", "blocks": []})
        assert answer == ""
        assert sources == []

    def test_unparseable_response_fails_instead_of_dumping_raw_json(self):
        from agents.perplexity_agent import PerplexityWebAgent
        agent = PerplexityWebAgent()
        agent.cookies = {"session": "x"}
        fake_client = MagicMock()
        fake_client.Client.return_value.search.return_value = {"backend_uuid": "abc"}
        with patch.dict("sys.modules", {"perplexity": fake_client}):
            result = agent._execute_web("hi")
        assert result.success is False
        assert "backend_uuid" not in result.error


class TestTeamImageRouting:
    """A screenshot must not take out the text-only steps of the pipeline."""

    IMG = [{"path": "x.png", "name": "x.png", "data": b"PNGBYTES",
            "mime": "image/png", "ext": "png", "width": 10, "height": 10}]

    def _team(self):
        from agents.team import AgentTeam
        team = AgentTeam(".")
        for agent in team.agents.values():
            agent.execute = MagicMock(
                return_value=AgentResult(agent.name, "x", "done", True))
            agent.is_ready = MagicMock(return_value=True)
        return team

    def test_only_vision_agents_receive_images(self):
        team = self._team()
        team.run_parallel({"architect": "design", "researcher": "research"},
                          "ctx", self.IMG)
        # ChatGPT sees images; Perplexity is text-only and must get None.
        assert team.agents["architect"].execute.call_args[0][2] == self.IMG
        assert team.agents["researcher"].execute.call_args[0][2] is None

    def test_text_only_agent_gets_none_via_run_single(self):
        team = self._team()
        team.run_single("coder", "build it", "ctx", self.IMG)
        assert team.agents["coder"].execute.call_args[0][2] is None

    def test_reviewer_is_added_when_nothing_routed_can_see(self):
        """'fix ...' routes to coder+reviewer; 'research ...' routes to researcher only,
        which would silently ignore an attached image."""
        team = self._team()
        results = team.run_pipeline("research the latest caching libraries", "ctx", self.IMG)
        labels = [label for label, _ in results]
        assert any("Gemini" in l for l in labels)
        assert team.agents["reviewer"].execute.call_args[0][2] == self.IMG

    def test_no_images_leaves_routing_untouched(self):
        team = self._team()
        results = team.run_pipeline("research the latest caching libraries", "ctx")
        assert [l for l, _ in results] == ["research [Perplexity]"]


# ── Coding agent safety ──────────────────────────────────────

class TestCodingAgentGuards:
    """This agent writes files and runs shell commands on the user's machine from a
    remote model's output, so the guards are the load-bearing part."""

    def _agent(self, tmp_path):
        from agents.coding_agent import CodingAgent
        return CodingAgent(team=MagicMock(), project_dir=str(tmp_path), auto_approve=True)

    def test_paths_cannot_escape_the_project(self, tmp_path):
        agent = self._agent(tmp_path)
        _, err = agent._safe("../../etc/passwd")
        assert "outside the project" in err

    def test_credential_files_are_untouchable(self, tmp_path):
        agent = self._agent(tmp_path)
        for name in ("sessions.json", ".env", ".env.local", "id.pem"):
            _, err = agent._safe(name)
            assert err and "credentials" in err

    def test_destructive_commands_are_blocked(self, tmp_path):
        agent = self._agent(tmp_path)
        assert "refused" in agent._tool_run("rm -rf /")
        assert "refused" in agent._tool_run("git push origin main")

    def test_read_refuses_secrets_but_allows_normal_files(self, tmp_path):
        (tmp_path / "sessions.json").write_text("{}", encoding="utf-8")
        (tmp_path / "ok.py").write_text("x = 1\n", encoding="utf-8")
        agent = self._agent(tmp_path)
        assert "credentials" in agent._tool_read("sessions.json")
        assert "x = 1" in agent._tool_read("ok.py")

    def test_write_applies_and_is_tracked(self, tmp_path):
        agent = self._agent(tmp_path)
        result = agent._tool_write("new/mod.py", "y = 2")
        assert "wrote" in result
        assert (tmp_path / "new" / "mod.py").read_text(encoding="utf-8") == "y = 2\n"
        assert "new/mod.py" in agent.changed_files

    def test_protocol_parses_every_request_form(self):
        from agents.coding_agent import ACTION_RE
        text = ("<<<LIST: .>>> <<<READ: a.py>>> <<<RUN: pytest -q>>>"
                "<<<WRITE: b.py>>>\nprint(1)\n<<<END>>><<<DONE>>>")
        found = list(ACTION_RE.finditer(text))
        assert len(found) == 5
        assert found[3].group("wpath") == "b.py"
        assert found[3].group("wbody") == "print(1)"
        assert found[4].group("done") == "DONE"
