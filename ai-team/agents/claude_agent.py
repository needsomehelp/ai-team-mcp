"""Claude agent - uses Claude Code CLI with your subscription.
Each agent is a separate Claude instance with a specialized system prompt."""

import subprocess
from .base import BaseAgent, AgentResult

ROLE_PROMPTS = {
    "coder": (
        "You are the LEAD CODER on a software team. "
        "Write clean, production-ready code. Be precise and concise. "
        "Output working code with minimal explanation. "
        "Fix bugs when asked. Follow best practices."
    ),
    "reviewer": (
        "You are the CODE REVIEWER on a software team. "
        "Review code for bugs, security issues, performance problems, and bad patterns. "
        "Be specific — reference exact lines. Suggest concrete fixes. "
        "Rate severity: CRITICAL / WARNING / SUGGESTION."
    ),
    "architect": (
        "You are the SOFTWARE ARCHITECT on a software team. "
        "Design clean architecture. Plan file structure, data flow, and interfaces. "
        "Think about scalability, maintainability, and separation of concerns. "
        "Provide clear diagrams using ASCII art when helpful."
    ),
    "researcher": (
        "You are the RESEARCH SPECIALIST on a software team. "
        "Find the best approaches, libraries, and patterns for the task. "
        "Compare alternatives with pros/cons. "
        "Provide code examples and usage patterns."
    ),
}


class ClaudeAgent(BaseAgent):
    def __init__(self, role: str = "coder"):
        role_name = role if role in ROLE_PROMPTS else "coder"
        super().__init__(f"Claude-{role_name.capitalize()}", role_name)
        self.system_prompt = ROLE_PROMPTS[role_name]

    def _find_claude(self) -> str:
        """Find the claude CLI, handling broken shebangs."""
        import shutil
        import os
        # Try direct execution first
        claude_path = shutil.which("claude")
        if claude_path:
            return claude_path
        # Common install locations
        for path in ["/usr/local/bin/claude", os.path.expanduser("~/.npm/_npx/008753da0115b366/node_modules/.bin/claude")]:
            if os.path.exists(path):
                return path
        return "claude"

    def is_ready(self) -> bool:
        import os
        claude = self._find_claude()
        return os.path.exists(claude)

    def execute(self, prompt: str, context: str = "") -> AgentResult:
        full_prompt = self.build_prompt(prompt, context, self.system_prompt)
        try:
            claude = self._find_claude()
            # Limit prompt size to avoid pipe mode issues
            if len(full_prompt) > 12000:
                full_prompt = full_prompt[:12000] + "\n\n[Context truncated for length]"
            result = subprocess.run(
                ["bash", claude, "-p", full_prompt],
                capture_output=True, text=True, timeout=120,
                env={**__import__('os').environ, "CLAUDE_CODE_DISABLE_AUTOUPDATE": "1"}
            )
            output = result.stdout.strip()
            if result.returncode == 0 and output:
                return AgentResult(self.name, self.role, output, True)
            # If pipe mode fails, skip gracefully
            return AgentResult(self.name, self.role, "", False,
                             "Claude CLI returned empty. In terminal mode, Claude works best as the synthesizer inside Claude Code. "
                             "Use 'aiteam plan/review/research' for individual agents, or use the MCP inside Claude Code for full 4-agent team.")
        except subprocess.TimeoutExpired:
            return AgentResult(self.name, self.role, "", False, "Claude CLI timed out. Use MCP inside Claude Code for full team mode.")
        except (FileNotFoundError, OSError):
            return AgentResult(self.name, self.role, "", False,
                             "Claude CLI not found. Install: npm install -g @anthropic-ai/claude-code")
