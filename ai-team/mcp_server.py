#!/usr/bin/env python3
"""
AI Team MCP Server

Exposes the AI Team (Claude + ChatGPT + Gemini + Perplexity) as MCP tools
that can be used from any Claude Code project.

Install:
    claude mcp add ai-team python3 /path/to/ai-team/mcp_server.py

Then use from Claude Code:
    "Ask ChatGPT to design the architecture for this feature"
    "Have Gemini review this code"
    "Get Perplexity to research best practices for caching"
    "Run the full AI team on this task"
"""

import sys
import os

# Add project root to path so agents can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP

from agents.session_store import save_session, get_session
from agents.claude_agent import ClaudeAgent
import agents.chatgpt_agent as _chatgpt_module
from agents.chatgpt_agent import ChatGPTWebAgent
from agents.gemini_agent import GeminiWebAgent
from agents.perplexity_agent import PerplexityWebAgent
from agents.team import AgentTeam

def _get_chatgpt() -> "ChatGPTWebAgent":
    """Always reload the chatgpt agent module so code changes take effect without restart."""
    import importlib
    importlib.reload(_chatgpt_module)
    return _chatgpt_module.ChatGPTWebAgent()

mcp = FastMCP("ai-team")


@mcp.tool()
def ai_team_status() -> str:
    """Check which AI agents are logged in and ready (Claude, ChatGPT, Gemini, Perplexity)."""
    agents = {
        "Claude Code": ("cli", ClaudeAgent().is_ready()),
        "ChatGPT Plus": ("web", _get_chatgpt().is_ready()),
        "Gemini Advanced": ("web", GeminiWebAgent().is_ready()),
        "Perplexity Pro": ("web", PerplexityWebAgent().is_ready()),
    }

    lines = ["AI TEAM STATUS", "=" * 40]
    for name, (method, ready) in agents.items():
        status = "READY" if ready else "NOT LOGGED IN"
        lines.append(f"  {name:20s} {status}")

    not_ready = [n for n, (_, r) in agents.items() if not r and n != "Claude Code"]
    if not_ready:
        lines.append("")
        lines.append("To log in, use the ai_team_login tool with:")
        lines.append("  ChatGPT:    go to https://chatgpt.com/api/auth/session, copy accessToken")
        lines.append("  Gemini:     Option A: free API key at https://aistudio.google.com/apikey")
        lines.append("              Option B: browser cookies from gemini.google.com (Advanced sub)")
        lines.append("  Perplexity: browser DevTools → Network → right-click request → Copy as cURL → paste Cookie header value")

    return "\n".join(lines)


@mcp.tool()
def ai_team_login(service: str, token: str, token2: str = "") -> str:
    """Save login token for an AI service. Services: chatgpt, gemini, perplexity.
    For ChatGPT: go to https://chatgpt.com/api/auth/session and copy the accessToken value.
    For Gemini: Option A (API key): get free key at https://aistudio.google.com/apikey. Option B (browser cookies): copy cookies from gemini.google.com via DevTools.
    For Perplexity: browser DevTools → Network → click any perplexity.ai request → copy the Cookie header value as token. Or paste all cookies as JSON dict."""
    if service == "chatgpt":
        import json as _json
        existing = get_session("chatgpt")
        # Try as JSON cookies dict
        try:
            cookies = _json.loads(token)
            if isinstance(cookies, dict):
                existing["cookies"] = cookies
                save_session("chatgpt", existing)
                return f"ChatGPT logged in with {len(cookies)} browser cookies! You can now use ask_chatgpt."
        except (ValueError, TypeError):
            pass
        # Try as cookie header string (name1=val1; name2=val2; ...)
        if ";" in token and "=" in token:
            from agents.perplexity_agent import parse_cookie_string
            cookies = parse_cookie_string(token)
            if cookies:
                existing["cookies"] = cookies
                save_session("chatgpt", existing)
                return f"ChatGPT logged in with {len(cookies)} browser cookies! You can now use ask_chatgpt."
        # Otherwise treat as access token
        existing["access_token"] = token
        save_session("chatgpt", existing)
        return "ChatGPT logged in successfully! You can now use ask_chatgpt."
    elif service == "gemini":
        # Detect: cookie string (has ; and =, multiple pairs), JSON dict, or API key
        # Cookie strings have multiple semicolons with key=value pairs
        import json as _json

        # Try as JSON cookies dict first
        try:
            cookies = _json.loads(token)
            if isinstance(cookies, dict):
                existing = get_session("gemini")
                existing["cookies"] = cookies
                save_session("gemini", existing)
                return (f"Gemini logged in with {len(cookies)} browser cookies! Using your Advanced subscription.\n"
                        "You can now use ask_gemini.")
        except (ValueError, TypeError):
            pass

        # Try as cookie header string (name1=val1; name2=val2; ...)
        # Cookie strings have multiple ; separators — API keys don't
        if ";" in token and "=" in token:
            from agents.gemini_agent import parse_cookie_string
            cookies = parse_cookie_string(token)
            if len(cookies) > 1:  # Real cookie strings have many pairs
                existing = get_session("gemini")
                existing["cookies"] = cookies
                save_session("gemini", existing)
                return (f"Gemini logged in with {len(cookies)} browser cookies! Using your Advanced subscription.\n"
                        "You can now use ask_gemini.")

        # Otherwise treat as API key
        save_session("gemini", {"api_key": token, "model": "gemini-2.5-flash"})
        return "Gemini logged in with API key! You can now use ask_gemini."
    elif service == "perplexity":
        if token.startswith("pplx-"):
            # Official API key
            save_session("perplexity", {"api_key": token, "model": "sonar"})
            return "Perplexity logged in with API key! You can now use ask_perplexity."
        else:
            # Browser cookies (free with Pro/Max subscription)
            # Accept: JSON dict, cookie header string, or single session token
            import json as _json
            try:
                cookies = _json.loads(token)
                if isinstance(cookies, dict):
                    save_session("perplexity", {"cookies": cookies})
                    return (f"Perplexity logged in with {len(cookies)} cookies! Using your Pro subscription.\n"
                            "You can now use ask_perplexity.")
            except (ValueError, TypeError):
                pass
            # Try as cookie header string (name1=val1; name2=val2)
            if "=" in token and ";" in token:
                from agents.perplexity_agent import parse_cookie_string
                cookies = parse_cookie_string(token)
                save_session("perplexity", {"cookies": cookies})
                return (f"Perplexity logged in with {len(cookies)} cookies! Using your Pro subscription.\n"
                        "You can now use ask_perplexity.")
            # Single session token fallback
            session_data = {"session_token": token}
            if token2:
                session_data["csrf_token"] = token2
            save_session("perplexity", session_data)
            return ("Perplexity logged in with session token! You can now use ask_perplexity.")
    elif service == "openai":
        save_session("openai", {"api_key": token})
        return "OpenAI API key saved. You can now use generate_image_dalle for DALL-E 3 images."
    return f"Unknown service: {service}. Use: chatgpt, gemini, perplexity, or openai"


_IMAGE_KEYWORDS = (
    "generate image", "create image", "make image", "draw", "render image",
    "text to image", "image of", "picture of", "photo of", "illustration of",
    "generate a picture", "make a picture", "create a picture",
)


def _is_image_request(task: str) -> bool:
    t = task.lower()
    return any(kw in t for kw in _IMAGE_KEYWORDS)


def _dalle3(prompt: str, size: str = "1024x1024", quality: str = "standard") -> str:
    """Call DALL-E 3 via OpenAI API — the same model ChatGPT uses internally."""
    import requests as _req

    session = get_session("openai")
    api_key = session.get("api_key", "")
    if not api_key:
        return (
            "DALL-E 3 needs an OpenAI API key (this is what ChatGPT uses for images internally).\n\n"
            "Get one free at: https://platform.openai.com/api-keys\n"
            "Then run: ai_team_login(service='openai', token='sk-...')\n\n"
            "After that, all image requests via ask_chatgpt will use DALL-E 3 directly."
        )
    try:
        resp = _req.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "dall-e-3", "prompt": prompt, "n": 1, "size": size, "quality": quality},
            timeout=120,
        )
        if resp.status_code in (401, 403):
            return "Invalid OpenAI API key. Update with: ai_team_login(service='openai', token='sk-...')"
        if resp.status_code == 400:
            err = resp.json().get("error", {}).get("message", "Bad request")
            return f"DALL-E 3 rejected the prompt: {err}"
        resp.raise_for_status()
        data = resp.json()
        url = data["data"][0]["url"]
        revised = data["data"][0].get("revised_prompt", "")
        note = f"\nRevised prompt: {revised}" if revised and revised != prompt else ""
        return (
            f"[DALL-E 3 via ChatGPT/OpenAI]\n\n"
            f"Image URL: {url}{note}\n\n"
            f"Note: URL expires in 1 hour — open now or download to keep."
        )
    except Exception as e:
        return f"DALL-E 3 error: {e}"


@mcp.tool()
def ask_chatgpt(task: str, context: str = "") -> str:
    """Send a task to ChatGPT (using your Plus/Pro subscription).
    Best for: architecture, planning, reasoning, AND image generation.
    For images: ChatGPT generates via DALL-E, we fetch the CDN URL, Claude displays it.
    No API key needed — uses your existing ChatGPT Plus session token.
    """
    if _is_image_request(task):
        agent = _get_chatgpt()
        if not agent.is_ready():
            return "ChatGPT not logged in. Use ai_team_login(service='chatgpt', token='...')"

        result = agent.generate_image(task)

        if result.success and "Image URL:" in result.content:
            # Got a real URL from ChatGPT/DALL-E — tell Claude to fetch it
            return (
                f"{result.content}\n\n"
                "Claude: fetch the Image URL above and display it to the user."
            )

        # ChatGPT didn't generate — fall back to DALL-E API if key exists, else Pollinations
        dalle_result = _dalle3(task)
        if "Image URL:" in dalle_result:
            return dalle_result

        # Final fallback: Pollinations (free, no key)
        import urllib.parse
        import requests as _req
        encoded = urllib.parse.quote(task)
        url = f"https://image.pollinations.ai/prompt/{encoded}?model=flux&width=1024&height=1024&nologo=true&enhance=true"
        try:
            r = _req.head(url, timeout=45, allow_redirects=True)
            if r.status_code == 200:
                return f"Image URL: {url}\n\nClaude: fetch this URL and display the image."
        except Exception:
            pass
        return f"Image URL: {url}\n\nClaude: fetch this URL and display the image."

    return _do_ask("chatgpt", task, context)


@mcp.tool()
def ask_gemini(task: str, context: str = "") -> str:
    """Send a task to Gemini (using your Advanced subscription). Best for: code review, finding bugs, security analysis."""
    return _do_ask("gemini", task, context)


@mcp.tool()
def ask_perplexity(task: str, context: str = "") -> str:
    """Send a task to Perplexity (using your Pro subscription). Best for: research, finding docs, examples, best practices."""
    return _do_ask("perplexity", task, context)


@mcp.tool()
def ai_team_run(task: str, context: str = "") -> str:
    """Run the full AI team pipeline on a task.
    Pipeline: Perplexity researches -> ChatGPT designs architecture ->
    Claude implements -> Gemini reviews. Each step feeds into the next.
    Skips agents that aren't logged in."""
    team = AgentTeam(os.getcwd())
    results = team.run_pipeline(task, context)

    output_lines = []
    succeeded = 0
    for label, result in results:
        if result and result.success:
            # Cap each agent at 3000 chars in pipeline output
            content = result.content[:3000]
            if len(result.content) > 3000:
                content += "\n[truncated]"
            output_lines.append(f"[{label}]\n{content}")
            succeeded += 1
        elif result:
            output_lines.append(f"[{label}] failed: {result.error[:100]}")

    output_lines.append(f"\n{succeeded}/{len(results)} agents completed.")
    return "\n\n".join(output_lines)


@mcp.tool()
def generate_image(prompt: str, width: int = 1024, height: int = 1024, model: str = "flux") -> str:
    """Generate an image using ChatGPT/DALL-E (primary) with Pollinations as fallback.
    Priority: 1) ChatGPT DALL-E (your Plus subscription, no API key needed)
              2) Pollinations/Flux (free, always works)
    Args:
        prompt: Description of the image (be detailed for best results)
        width:  Image width in pixels (default 1024)
        height: Image height in pixels (default 1024)
        model:  Fallback model — 'flux' (default), 'turbo', 'flux-realism'
    """
    import urllib.parse
    import requests as _req

    # Step 1: Try ChatGPT/DALL-E first (uses your Plus subscription)
    agent = _get_chatgpt()
    if agent.is_ready():
        result = agent.generate_image(prompt)
        if result.success and "Image URL:" in result.content:
            return (
                f"[ChatGPT/DALL-E]\n\n"
                f"{result.content}\n\n"
                f"Claude: read the saved file path above and display the image to the user."
            )

    # Step 2: Fallback to Pollinations (free, no key needed)
    encoded = urllib.parse.quote(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?model={model}&width={width}&height={height}&nologo=true&enhance=true"
    )
    try:
        r = _req.get(url, timeout=60, stream=True)
        if r.status_code == 200:
            import tempfile
            ext = "png" if "png" in r.headers.get("content-type", "") else "jpg"
            tmp = tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False)
            for chunk in r.iter_content(8192):
                tmp.write(chunk)
            tmp.close()
            return (
                f"[Pollinations/{model}]\n\n"
                f"URL: {url}\n"
                f"Saved to: {tmp.name}\n\n"
                f"Claude: read {tmp.name} and display the image to the user."
            )
    except Exception:
        pass

    return (
        f"[Pollinations/{model}]\n\n"
        f"URL: {url}\n\n"
        f"Claude: fetch this URL and display the image to the user."
    )


@mcp.tool()
def generate_image_dalle(prompt: str, size: str = "1024x1024", quality: str = "standard") -> str:
    """Generate an image with DALL-E 3 — the same model ChatGPT uses in the browser.
    Requires OpenAI API key: ai_team_login(service='openai', token='sk-...')
    Args:
        prompt:  Description of the image
        size:    '1024x1024', '1792x1024', or '1024x1792'
        quality: 'standard' or 'hd'
    """
    return _dalle3(prompt, size=size, quality=quality)




@mcp.tool()
def generate_video(prompt: str, model: str = "", duration: int = 4) -> str:
    """Generate a video. Routes to Higgsfield MCP which returns a real video URL.
    ChatGPT and Gemini CANNOT do this through the MCP bridge.
    Args:
        prompt:   Description of the video
        model:    Optional model name (leave empty for default)
        duration: Length in seconds (default: 4)
    """
    return (
        f"[generate_video → Higgsfield]\n\n"
        f"Prompt: {prompt}\n"
        f"Duration: {duration}s\n"
        f"Model: {model or 'default'}\n\n"
        "Claude: call mcp__claude_ai_Higgsfield__generate_video with this prompt and return the video URL."
    )


@mcp.tool()
def generate_audio(prompt: str, duration: int = 10) -> str:
    """Generate audio/music. Routes to Higgsfield MCP which returns a real audio URL.
    ChatGPT and Gemini CANNOT do this through the MCP bridge.
    Args:
        prompt:   Description of the audio or music
        duration: Length in seconds (default: 10)
    """
    return (
        f"[generate_audio → Higgsfield]\n\n"
        f"Prompt: {prompt}\n"
        f"Duration: {duration}s\n\n"
        "Claude: call mcp__claude_ai_Higgsfield__generate_audio with this prompt and return the audio URL."
    )


@mcp.tool()
def ai_team_chat(task: str, context: str = "") -> str:
    """Collaborate with ChatGPT as a team. Sends the task to ChatGPT and returns its
    response so Claude can combine it with its own analysis for a unified team answer.
    Use this when the user invokes /aiteam mode."""
    chatgpt = _get_chatgpt()
    if not chatgpt.is_ready():
        return "ChatGPT is not logged in. Use ai_team_login tool first.\nService: chatgpt"

    prompt = (
        "You are part of an AI team working alongside Claude. "
        "Give your best analysis, suggestions, and ideas on this task. "
        "Be specific and actionable. Claude will combine your input with its own.\n\n"
        f"TASK: {task}"
    )
    if context:
        prompt += f"\n\nCONTEXT:\n{context}"

    result = chatgpt.execute(prompt, context)
    if result.success:
        return f"=== ChatGPT's Input ===\n\n{result.content}"
    return f"ChatGPT failed: {result.error}"


def _do_ask(service, task, context=""):
    if service == "chatgpt":
        agent = _get_chatgpt()
    elif service == "gemini":
        agent = GeminiWebAgent()
    elif service == "perplexity":
        agent = PerplexityWebAgent()
    else:
        return f"Unknown service: {service}"
    agent_class = type(agent)  # noqa — kept for compat
    if not agent.is_ready():
        return (f"{agent.name} is not logged in. Use ai_team_login tool first.\n"
                f"Service: {service}")

    result = agent.execute(task, context)
    if result.success:
        # Cap at 4000 chars — preserves full code reviews and research without unbounded bloat
        content = result.content[:4000]
        if len(result.content) > 4000:
            content += "\n[truncated — ask for more if needed]"
        return f"[{result.agent_name}]\n{content}"
    return f"[{result.agent_name} failed]: {result.error}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
