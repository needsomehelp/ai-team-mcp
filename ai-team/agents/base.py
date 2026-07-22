"""Base agent class for all AI team members."""

import glob
import os
import tempfile
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

# Total budget for context injected into a prompt (raised from 1200 so real file
# contents actually reach the model instead of being sliced off).
MAX_CONTEXT_CHARS = 14000

# Per-agent throttle timestamps, keyed by agent name. This lives in base (which is NOT
# reloaded in dev mode) rather than in an agent module — importlib.reload rebuilds the
# agent class every call and would otherwise reset its class-level timestamp, silently
# defeating the throttle and inviting an "unusual activity" ban.
_LAST_REQUEST_TIME = {}


def rate_limit(key: str, min_interval: float = 10.0):
    """Block until at least `min_interval` seconds have passed since the last call for `key`."""
    elapsed = time.time() - _LAST_REQUEST_TIME.get(key, 0.0)
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    _LAST_REQUEST_TIME[key] = time.time()

# Files whose contents must NEVER be sent to a third-party model (secrets/creds).
_SECRET_NAMES = {"sessions.json", "sessions.example.json"}
_SECRET_PREFIXES = (".env",)              # .env, .env.local, .env.production, ...
_SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx")


def _is_secret_file(name: str) -> bool:
    name = name.lower()
    if name in _SECRET_NAMES:
        return True
    if any(name.startswith(p) for p in _SECRET_PREFIXES):
        return True
    if any(name.endswith(s) for s in _SECRET_SUFFIXES):
        return True
    return False


def read_files_for_context(paths, project_dir, budget=MAX_CONTEXT_CHARS):
    """Read the given files (read-only) and format them for injection into a prompt.

    Security guards — these contents go to a third-party model (OpenAI/Google/Perplexity):
      - paths resolve INSIDE project_dir only (no `../` traversal escapes)
      - known secret files (.env*, sessions.json, *.key/*.pem/...) are always skipped
      - total output is capped at `budget` chars
    Returns (formatted_text, notes) where notes lists any skipped/failed paths.
    """
    project_dir = os.path.abspath(project_dir)
    blocks, notes, used = [], [], 0
    for p in paths or []:
        if not p:
            continue
        abs_path = os.path.abspath(os.path.join(project_dir, p))
        if os.path.commonpath([abs_path, project_dir]) != project_dir:
            notes.append(f"{p} (skipped: outside project)")
            continue
        if _is_secret_file(os.path.basename(abs_path)):
            notes.append(f"{p} (skipped: secrets never leave your machine)")
            continue
        if not os.path.isfile(abs_path):
            notes.append(f"{p} (skipped: not found)")
            continue
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except Exception as e:
            notes.append(f"{p} (skipped: {e})")
            continue
        remaining = budget - used
        if remaining <= 0:
            notes.append(f"{p} (skipped: context budget full)")
            continue
        if len(text) > remaining:
            text = text[:remaining] + "\n[truncated]"
        used += len(text)
        rel = os.path.relpath(abs_path, project_dir)
        blocks.append(f"=== FILE: {rel} ===\n{text}")
    return "\n\n".join(blocks), notes


def save_temp_image(data: bytes, ext: str = "png") -> str:
    """Save generated image bytes to a dedicated temp dir, pruning images older than
    an hour first so temp files don't accumulate forever. Returns the file path.

    (delete=False temp files are needed because Claude reads the file AFTER the tool
    returns — so we can't delete immediately; we prune old ones on the next write.)"""
    d = os.path.join(tempfile.gettempdir(), "aiteam_images")
    os.makedirs(d, exist_ok=True)
    cutoff = time.time() - 3600
    for old in glob.glob(os.path.join(d, "img_*")):
        try:
            if os.path.getmtime(old) < cutoff:
                os.remove(old)
        except OSError:
            pass
    path = os.path.join(d, f"img_{uuid.uuid4().hex}.{ext}")
    with open(path, "wb") as f:
        f.write(data)
    return path


@dataclass
class AgentResult:
    agent_name: str
    role: str
    content: str
    success: bool
    error: str = ""


class BaseAgent(ABC):
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role

    @abstractmethod
    def execute(self, prompt: str, context: str = "") -> AgentResult:
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        pass

    def build_prompt(self, task: str, context: str, role_instruction: str) -> str:
        parts = [
            f"You are the {self.role} on a software team.",
            role_instruction,
            "Be concise and specific. No preamble, no filler, no repetition.",
        ]
        if context:
            parts.append(f"\n--- PROJECT ---\n{context[:MAX_CONTEXT_CHARS]}\n---")
        parts.append(f"\n--- TASK ---\n{task}")
        return "\n".join(parts)
