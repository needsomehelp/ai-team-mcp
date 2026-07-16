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

from agents.session_store import save_session, get_session, list_sessions
from agents.claude_agent import ClaudeAgent
from agents.chatgpt_agent import ChatGPTWebAgent
from agents.gemini_agent import GeminiWebAgent
from agents.perplexity_agent import PerplexityWebAgent
from agents.team import AgentTeam

mcp = FastMCP("ai-team")


@mcp.tool()
def ai_team_status() -> str:
    """Check which AI agents are logged in and ready (Claude, ChatGPT, Gemini, Perplexity)."""
    agents = {
        "Claude Code": ("cli", ClaudeAgent().is_ready()),
        "ChatGPT Plus": ("web", ChatGPTWebAgent().is_ready()),
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
        save_session("chatgpt", {"access_token": token})
        return "ChatGPT logged in successfully! You can now use ask_chatgpt."
    elif service == "gemini":
        # Check if it's an API key (starts with AIza) or browser cookies
        if token.startswith("AIza"):
            save_session("gemini", {"api_key": token, "model": "gemini-2.5-flash"})
            return "Gemini logged in with API key! You can now use ask_gemini."
        else:
            # Try as JSON cookies dict
            import json as _json
            try:
                cookies = _json.loads(token)
                if isinstance(cookies, dict):
                    # Merge: keep API key if already set, add cookies
                    existing = get_session("gemini")
                    existing["cookies"] = cookies
                    save_session("gemini", existing)
                    return (f"Gemini logged in with {len(cookies)} browser cookies! Using your Advanced subscription.\n"
                            "You can now use ask_gemini.")
            except (ValueError, TypeError):
                pass
            # Try as cookie header string (name1=val1; name2=val2)
            if "=" in token and ";" in token:
                from agents.gemini_agent import parse_cookie_string
                cookies = parse_cookie_string(token)
                existing = get_session("gemini")
                existing["cookies"] = cookies
                save_session("gemini", existing)
                return (f"Gemini logged in with {len(cookies)} browser cookies! Using your Advanced subscription.\n"
                        "You can now use ask_gemini.")
            # Assume it's an API key even without AIza prefix
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
    return f"Unknown service: {service}. Use: chatgpt, gemini, or perplexity"


@mcp.tool()
def ask_chatgpt(task: str, context: str = "") -> str:
    """Send a task to ChatGPT (using your Plus/Pro subscription). Best for: architecture design, system planning, complex reasoning."""
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

    output_lines = ["FULL TEAM PIPELINE RESULTS", "=" * 50]

    succeeded = 0
    for label, result in results:
        output_lines.append(f"\n--- {label} ---")
        if result and result.success:
            output_lines.append(result.content)
            succeeded += 1
        elif result:
            output_lines.append(f"FAILED: {result.error}")
        else:
            output_lines.append("SKIPPED")

    output_lines.append(f"\n{'=' * 50}")
    output_lines.append(f"Summary: {succeeded}/{len(results)} agents completed successfully")

    return "\n".join(output_lines)


@mcp.tool()
def ai_team_chat(task: str, context: str = "") -> str:
    """Collaborate with ChatGPT as a team. Sends the task to ChatGPT and returns its
    response so Claude can combine it with its own analysis for a unified team answer.
    Use this when the user invokes /aiteam mode."""
    chatgpt = ChatGPTWebAgent()
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
    agents = {
        "chatgpt": ChatGPTWebAgent,
        "gemini": GeminiWebAgent,
        "perplexity": PerplexityWebAgent,
    }

    agent_class = agents.get(service)
    if not agent_class:
        return f"Unknown service: {service}"

    agent = agent_class()
    if not agent.is_ready():
        return (f"{agent.name} is not logged in. Use ai_team_login tool first.\n"
                f"Service: {service}")

    result = agent.execute(task, context)
    if result.success:
        return f"--- {result.agent_name} ({result.role}) ---\n\n{result.content}"
    return f"{result.agent_name} failed: {result.error}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
