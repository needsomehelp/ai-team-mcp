"""Base agent class for all AI team members."""

import glob
import os
import struct
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


# --- Image input (vision) ---------------------------------------------------
# Limits kept deliberately tight: these bytes are uploaded to a third-party model,
# and the web/subscription paths are far less forgiving about size than the APIs.
MAX_IMAGES = 4
MAX_IMAGE_BYTES = 5 * 1024 * 1024

# Magic-byte signatures -> (mime, ext). Sniffing the header rather than trusting the
# extension is what stops a renamed .env (or any non-image) from being uploaded.
_IMAGE_MAGIC = (
    (b"\x89PNG\r\n\x1a\n", "image/png", "png"),
    (b"\xff\xd8\xff", "image/jpeg", "jpg"),
    (b"GIF87a", "image/gif", "gif"),
    (b"GIF89a", "image/gif", "gif"),
)


def _sniff_image(head: bytes):
    """Return (mime, ext) for image bytes, or None if this isn't an image we support."""
    for magic, mime, ext in _IMAGE_MAGIC:
        if head.startswith(magic):
            return mime, ext
    # WEBP is RIFF<4-byte size>WEBP, so it can't be matched by a flat prefix.
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp", "webp"
    return None


def image_size(data: bytes):
    """Parse (width, height) straight out of an image header. Returns (0, 0) if unknown.

    Hand-rolled because Pillow isn't a dependency, and ChatGPT's upload API wants real
    pixel dimensions on the attachment -- sending zeros makes it treat the image as a
    generic file and the model never looks at it."""
    try:
        # PNG: IHDR width/height are two big-endian uint32 right after the signature.
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", data[16:24])

        # GIF: logical screen descriptor, little-endian uint16 pair.
        if data[:6] in (b"GIF87a", b"GIF89a"):
            return struct.unpack("<HH", data[6:10])

        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            chunk = data[12:16]
            if chunk == b"VP8X":
                w = int.from_bytes(data[24:27], "little") + 1
                h = int.from_bytes(data[27:30], "little") + 1
                return w, h
            if chunk == b"VP8 ":
                w, h = struct.unpack("<HH", data[26:30])
                return w & 0x3FFF, h & 0x3FFF
            if chunk == b"VP8L":
                bits = int.from_bytes(data[21:25], "little")
                return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1

        # JPEG: walk the marker segments to the start-of-frame, which carries the size.
        if data[:3] == b"\xff\xd8\xff":
            i, n = 2, len(data)
            while i + 9 < n:
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                # SOF0-SOF15, excluding DHT(C4)/JPG(C8)/DAC(CC) which aren't frames.
                if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                    h, w = struct.unpack(">HH", data[i + 5:i + 9])
                    return w, h
                if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                    i += 2  # standalone markers carry no length field
                    continue
                i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    except (struct.error, IndexError, ValueError):
        pass
    return 0, 0


def load_images(paths, budget=MAX_IMAGES):
    """Load local image files so an agent can actually see them.

    Unlike read_files_for_context, images are NOT confined to the project dir —
    screenshots normally live in Pictures/, Downloads/ or a temp dir, and naming
    the path is an explicit user action. The guard here is content-based instead:
    a file only leaves the machine if its bytes really are a PNG/JPEG/GIF/WEBP.

    Returns (images, notes) where each image is
    {"path", "name", "data" (bytes), "mime", "ext"} and notes lists what was skipped.
    """
    images, notes = [], []
    for p in paths or []:
        if not p:
            continue
        if len(images) >= budget:
            notes.append(f"{p} (skipped: max {budget} images per request)")
            continue
        abs_path = os.path.abspath(os.path.expanduser(str(p)))
        if not os.path.isfile(abs_path):
            notes.append(f"{p} (skipped: not found)")
            continue
        try:
            size = os.path.getsize(abs_path)
            if size > MAX_IMAGE_BYTES:
                notes.append(f"{p} (skipped: {size // 1024}KB exceeds the "
                             f"{MAX_IMAGE_BYTES // (1024 * 1024)}MB limit)")
                continue
            with open(abs_path, "rb") as f:
                data = f.read()
        except OSError as e:
            notes.append(f"{p} (skipped: {e})")
            continue
        sniffed = _sniff_image(data[:16])
        if not sniffed:
            notes.append(f"{p} (skipped: not a PNG/JPEG/GIF/WEBP image)")
            continue
        mime, ext = sniffed
        width, height = image_size(data)
        images.append({
            "path": abs_path,
            "name": os.path.basename(abs_path),
            "data": data,
            "mime": mime,
            "ext": ext,
            "width": width,
            "height": height,
        })
    return images, notes


def no_image_support(agent_name: str, reason: str) -> str:
    """Standard note for an agent that was handed images it cannot send.

    Said out loud rather than dropped silently -- an answer that never saw the
    screenshot but doesn't say so is worse than an error."""
    return (f"{agent_name} cannot accept image input on the current auth path: {reason}")


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
    def execute(self, prompt: str, context: str = "", images: list = None) -> AgentResult:
        """`images` is the list returned by load_images(); agents that can't send
        images must report it via no_image_support() rather than ignore them."""
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        pass

    def supports_images(self) -> bool:
        """Whether this agent can actually be sent image input.

        The team pipeline uses this to route attachments only to agents that can see
        them -- handing images to one that can't would fail that whole step, so a
        screenshot would take out the researcher and coder along with it."""
        return False

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
