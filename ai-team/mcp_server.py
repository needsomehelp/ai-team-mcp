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

import re
import sys
import os
from typing import Optional

# Add project root to path so agents can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP

from agents.session_store import save_session, get_session
from agents.base import read_files_for_context, save_temp_image, load_images
from agents.claude_agent import ClaudeAgent
import agents.chatgpt_agent as _chatgpt_module
from agents.chatgpt_agent import ChatGPTWebAgent
from agents.gemini_agent import GeminiWebAgent
from agents.perplexity_agent import PerplexityWebAgent
from agents.team import AgentTeam


def _with_files(context: str, files: Optional[list]) -> str:
    """Prepend read-only contents of `files` (repo paths) to an agent's context so it
    sees your real code instead of guessing signatures. Secrets are stripped out."""
    if not files:
        return context or ""
    file_text, notes = read_files_for_context(files, os.getcwd())
    prefix = ""
    if file_text:
        prefix += file_text + "\n\n"
    if notes:
        prefix += "[file notes] " + "; ".join(notes) + "\n\n"
    return prefix + (context or "")

def _get_chatgpt() -> "ChatGPTWebAgent":
    """Instantiate the ChatGPT agent. In dev mode (AITEAM_DEV=1) reload the module first
    so code edits take effect without restarting the server. The rate-limiter state now
    lives in agents.base (not reloaded), so reloading here no longer resets the throttle."""
    if os.environ.get("AITEAM_DEV"):
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
        from agents.chatgpt_agent import ChatGPTWebAgent
        existing = get_session("chatgpt")

        def _as_cookies(raw):
            """Read a JSON dict or a `name=val; name2=val2` Cookie header.
            Returns {} for anything else, e.g. a bare access token."""
            if not raw:
                return {}
            try:
                parsed = _json.loads(raw)
                if isinstance(parsed, dict):
                    return {str(k): str(v) for k, v in parsed.items()}
            except (ValueError, TypeError):
                pass
            if ";" in raw and "=" in raw:
                from agents.perplexity_agent import parse_cookie_string
                return parse_cookie_string(raw) or {}
            return {}

        cookies = _as_cookies(token)
        # token2 lets one call carry both halves, in either order: whichever
        # argument doesn't parse as cookies is taken as the access token.
        extra = _as_cookies(token2)
        if extra:
            cookies = {**cookies, **extra}
        elif token2:
            existing["access_token"] = token2
        if cookies and not _as_cookies(token):
            existing["access_token"] = token

        if cookies:
            # Merge, so adding cf_clearance later doesn't wipe the session cookie.
            merged = dict(existing.get("cookies") or {})
            merged.update(cookies)
            existing["cookies"] = merged
            if merged.get("oai-did"):
                existing["device_id"] = merged["oai-did"]
            save_session("chatgpt", existing)
            msg = f"ChatGPT logged in with {len(merged)} browser cookies! You can now use ask_chatgpt."
            missing = [c for c in ChatGPTWebAgent.KEY_COOKIES if c not in merged]
            if missing:
                msg += ("\nStill missing (Turnstile 403s are likely without these): "
                        + ", ".join(missing))
            return msg

        # Otherwise treat as access token
        existing["access_token"] = token
        save_session("chatgpt", existing)
        msg = "ChatGPT logged in successfully! You can now use ask_chatgpt."
        if not existing.get("cookies"):
            msg += ("\nNote: no browser cookies saved. If /conversation 403s with a "
                    "Turnstile demand, a token refresh will NOT fix it -- add cookies "
                    "instead: ai_team_login(service='chatgpt', token='<Cookie header "
                    "from a logged-in chatgpt.com tab>').")
        return msg
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

            def _save_pplx_cookies(cookies):
                """Merge onto what's stored (so a later cf_clearance-only paste
                doesn't wipe the session token), then confirm the cookies actually
                authenticate -- an expired paste otherwise fails silently, with
                Perplexity answering as an anonymous visitor."""
                from agents.perplexity_agent import PerplexityWebAgent
                existing = get_session("perplexity")
                merged = dict(existing.get("cookies") or {})
                merged.update(cookies)
                existing["cookies"] = merged
                save_session("perplexity", existing)

                msg = f"Perplexity saved {len(merged)} cookies ({len(cookies)} from this paste)."
                missing = [c for c in PerplexityWebAgent.KEY_COOKIES if c not in merged]
                if missing:
                    msg += "\nMissing key cookies: " + ", ".join(missing)
                ok, detail = PerplexityWebAgent.check_auth(merged)
                if ok:
                    msg += f"\nVerified logged in as {detail} -- you can now use ask_perplexity."
                else:
                    msg += (f"\nNOT authenticated ({detail}). Re-copy the whole Cookie header "
                            "from a logged-in perplexity.ai tab in one go.")
                return msg

            try:
                cookies = _json.loads(token)
                if isinstance(cookies, dict):
                    return _save_pplx_cookies({str(k): str(v) for k, v in cookies.items()})
            except (ValueError, TypeError):
                pass
            # Try as cookie header string (name1=val1; name2=val2)
            if "=" in token and ";" in token:
                from agents.perplexity_agent import parse_cookie_string
                return _save_pplx_cookies(parse_cookie_string(token))
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
    "generate image", "create image", "make image", "render image",
    "text to image", "image of", "picture of", "photo of", "illustration of",
    "generate a picture", "make a picture", "create a picture",
    "draw an image", "draw a picture", "draw me a picture", "draw me an image",
)


def _is_image_request(task: str) -> bool:
    t = task.lower()
    return any(re.search(rf"\b{re.escape(kw)}\b", t) for kw in _IMAGE_KEYWORDS)


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


def _pollinations_fallback(prompt: str, width: int = 1024, height: int = 1024, model: str = "flux") -> str:
    """Free, keyless image fallback. Downloads to a pruned temp dir when possible and
    returns a formatted result for Claude to display. Shared by ask_chatgpt and
    generate_image so the fallback path lives in one place."""
    import urllib.parse
    import requests as _req

    encoded = urllib.parse.quote(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?model={model}&width={width}&height={height}&nologo=true&enhance=true"
    )
    try:
        r = _req.get(url, timeout=60, stream=True)
        if r.status_code == 200:
            ext = "png" if "png" in r.headers.get("content-type", "") else "jpg"
            path = save_temp_image(b"".join(r.iter_content(8192)), ext)
            return (
                f"[Pollinations/{model}]\n\n"
                f"URL: {url}\n"
                f"Saved to: {path}\n\n"
                f"Claude: read {path} and display the image to the user."
            )
    except Exception:
        pass
    return (
        f"[Pollinations/{model}]\n\n"
        f"URL: {url}\n\n"
        f"Claude: fetch this URL and display the image to the user."
    )


@mcp.tool()
def ask_chatgpt(task: str, context: str = "", files: Optional[list] = None,
                images: Optional[list] = None) -> str:
    """Send a task to ChatGPT (using your Plus/Pro subscription).
    Best for: architecture, planning, reasoning, image generation, AND reading images.
    For images: ChatGPT generates via DALL-E, we fetch the CDN URL, Claude displays it.
    No API key needed — uses your existing ChatGPT Plus session token.
    files: optional list of repo file paths (relative to the project) to read and include
           so ChatGPT sees your real code. Secret files (.env*, sessions.json) are skipped.
    images: optional list of local image paths (PNG/JPEG/GIF/WEBP) to attach so ChatGPT can
           see them — uploaded to your ChatGPT account the same way the web app does, so the
           subscription covers it. Absolute paths anywhere on disk are fine. Max 4, 5MB each.
    """
    if images:
        # An attached image means "look at this", never "draw me one" — skip the
        # generate-an-image branch even when the wording sounds like a request for art.
        return _do_ask("chatgpt", task, _with_files(context, files), images)

    if _is_image_request(task):
        agent = _get_chatgpt()
        if not agent.is_ready():
            return "ChatGPT not logged in. Use ai_team_login(service='chatgpt', token='...')"

        result = agent.generate_image(task)

        if result.success and "Saved to:" in result.content:
            # Downloaded with the session's own auth. Checked before the URL case:
            # a chatgpt.com asset URL 403s outside the agent, so "fetch this URL"
            # is not an instruction Claude can actually carry out.
            return (
                f"{result.content}\n\n"
                "Claude: read the saved file above and display the image to the user."
            )

        if result.success and "Image URL:" in result.content:
            # Publicly fetchable URL (e.g. DALL-E API) — Claude can fetch it.
            return (
                f"{result.content}\n\n"
                "Claude: fetch the Image URL above and display it to the user."
            )

        # ChatGPT didn't generate — fall back to DALL-E API if key exists, else Pollinations
        dalle_result = _dalle3(task)
        if "Image URL:" in dalle_result:
            return dalle_result

        # Final fallback: Pollinations (free, no key)
        return _pollinations_fallback(task)

    return _do_ask("chatgpt", task, _with_files(context, files))


@mcp.tool()
def ask_gemini(task: str, context: str = "", files: Optional[list] = None,
               images: Optional[list] = None) -> str:
    """Send a task to Gemini (using your Advanced subscription). Best for: code review,
    finding bugs, security analysis, AND looking at images (screenshots, mockups, error
    dialogs, photos, diagrams).
    files: optional list of repo file paths (relative to the project) to read and include
           so Gemini reviews your real code. Secret files (.env*, sessions.json) are skipped.
    images: optional list of local image paths (PNG/JPEG/GIF/WEBP) to attach so Gemini can
           actually see them. Absolute paths anywhere on disk are fine (e.g. a screenshot in
           Pictures or Downloads). Max 4 images, 5MB each. ask_chatgpt takes images too;
           Perplexity does not."""
    return _do_ask("gemini", task, _with_files(context, files), images)


@mcp.tool()
def ask_perplexity(task: str, context: str = "", files: Optional[list] = None) -> str:
    """Send a task to Perplexity (using your Pro subscription). Best for: research, finding docs, examples, best practices.
    files: optional list of repo file paths (relative to the project) to read and include."""
    return _do_ask("perplexity", task, _with_files(context, files))


@mcp.tool()
def ai_team_run(task: str, context: str = "", files: Optional[list] = None,
                images: Optional[list] = None) -> str:
    """Run the full AI team pipeline on a task.
    Pipeline: Perplexity researches -> ChatGPT designs architecture ->
    Claude implements -> Gemini reviews. Each step feeds into the next.
    Skips agents that aren't logged in.
    files: optional list of repo file paths (relative to the project) to read and feed the
           whole team — this is what stops the coder step from hallucinating your real
           signatures. Secret files (.env*, sessions.json) are skipped.
    images: optional list of local image paths (PNG/JPEG/GIF/WEBP), e.g. a screenshot or
           mockup to build from. Only ChatGPT and Gemini can see images, so they get the
           attachments and describe them for the text-only steps. Max 4, 5MB each."""
    loaded, image_notes = load_images(images)
    if images and not loaded:
        return "No usable images: " + "; ".join(image_notes)

    team = AgentTeam(os.getcwd())
    results = team.run_pipeline(task, _with_files(context, files), loaded)

    output_lines = []
    if loaded:
        seen = ", ".join(i["name"] for i in loaded)
        output_lines.append(f"[images] {seen} — sent to ChatGPT and Gemini "
                            "(Perplexity and the Claude coder step are text-only)")
    if image_notes:
        output_lines.append("[image notes] " + "; ".join(image_notes))
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
    # Step 1: Try ChatGPT/DALL-E first (uses your Plus subscription)
    agent = _get_chatgpt()
    if agent.is_ready():
        result = agent.generate_image(prompt)
        # Accept either form. Gating on "Image URL:" alone used to drop a
        # successfully saved image on the floor and fall through to Pollinations,
        # because the local-save paths never emit that prefix.
        if result.success and ("Saved to:" in result.content
                               or "Image URL:" in result.content):
            return (
                f"[ChatGPT/DALL-E]\n\n"
                f"{result.content}\n\n"
                f"Claude: read the saved file path above (or fetch the Image URL) "
                f"and display the image to the user."
            )

    # Step 2: Fallback to Pollinations (free, no key needed)
    return _pollinations_fallback(prompt, width, height, model)


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


def _do_ask(service, task, context="", images=None):
    if service == "chatgpt":
        agent = _get_chatgpt()
    elif service == "gemini":
        agent = GeminiWebAgent()
    elif service == "perplexity":
        agent = PerplexityWebAgent()
    else:
        return f"Unknown service: {service}"
    if not agent.is_ready():
        return (f"{agent.name} is not logged in. Use ai_team_login tool first.\n"
                f"Service: {service}")

    loaded, image_notes = load_images(images)
    if images and not loaded:
        # Every image was rejected -- answering from the text alone would look like
        # the agent had seen them, so stop and say what happened instead.
        return f"[{agent.name}] no usable images: " + "; ".join(image_notes)

    result = agent.execute(task, context, images=loaded)
    if result.success:
        # Cap at 4000 chars — preserves full code reviews and research without unbounded bloat
        content = result.content[:4000]
        if len(result.content) > 4000:
            content += "\n[truncated — ask for more if needed]"
        header = f"[{result.agent_name}]"
        if loaded:
            header += f" (saw {len(loaded)} image(s): " + ", ".join(i["name"] for i in loaded) + ")"
        if image_notes:
            header += "\n[image notes] " + "; ".join(image_notes)
        return f"{header}\n{content}"
    return f"[{result.agent_name} failed]: {result.error}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
