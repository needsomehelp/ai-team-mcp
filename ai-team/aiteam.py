#!/usr/bin/env python3
"""
AI TEAM CLI - 4 different AI subscriptions working as one coding team.

  Claude Code   = Lead Coder     (your Claude subscription)
  ChatGPT Plus  = Architect      (your ChatGPT subscription)
  Gemini Adv    = Code Reviewer  (your Gemini subscription)
  Perplexity Pro= Researcher     (your Perplexity subscription)

SETUP (one time per service):
    python3 aiteam.py login chatgpt
    python3 aiteam.py login gemini
    python3 aiteam.py login perplexity
    (Claude uses your CLI login - already done)

USAGE:
    aiteam "fix the failing test"                           # Coding agent: reads, edits, runs, iterates
    aiteam "add a /health endpoint" --yes                    #   --yes skips the per-change approval
    python3 aiteam.py chat                                  # Interactive chat (ChatGPT+Gemini+Perplexity)
    python3 aiteam.py team "Build a REST API with auth"     # All 4 agents
    python3 aiteam.py code "Fix the login bug"              # Claude only
    python3 aiteam.py review "Check main.py for issues"     # Gemini only
    python3 aiteam.py plan "Design a caching layer"         # ChatGPT only
    python3 aiteam.py research "Best Python web frameworks" # Perplexity only
    python3 aiteam.py status                                # See who's logged in
"""

import sys
import os
import re
import time
import difflib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Windows consoles default to cp1252, so the box-drawing banner raises
# UnicodeEncodeError and kills the CLI the moment output is piped or redirected.
if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

from agents.team import AgentTeam
from agents.session_store import save_session
from agents.base import read_files_for_context


# ── Colors ──
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"
    BG_GREEN = "\033[42m"
    BG_RED = "\033[41m"


AGENT_INFO = {
    "claude":     {"role": "coder",      "color": C.GREEN,   "label": "Claude Code",    "service": "Lead Coder"},
    "chatgpt":    {"role": "architect",  "color": C.CYAN,    "label": "ChatGPT Plus",   "service": "Architect"},
    "gemini":     {"role": "reviewer",   "color": C.YELLOW,  "label": "Gemini Advanced","service": "Code Reviewer"},
    "perplexity": {"role": "researcher", "color": C.MAGENTA, "label": "Perplexity Pro", "service": "Researcher"},
}

ROLE_MAP = {
    "code": "coder", "coder": "coder", "write": "coder", "fix": "coder", "claude": "coder",
    "review": "reviewer", "check": "reviewer", "audit": "reviewer", "gemini": "reviewer",
    "plan": "architect", "design": "architect", "architect": "architect", "chatgpt": "architect",
    "research": "researcher", "search": "researcher", "find": "researcher", "perplexity": "researcher",
}


def print_banner():
    print(f"""
{C.BOLD}  ┌─────────────────────────────────────────┐
  │         AI TEAM CLI                     │
  │   4 AI subscriptions = 1 coding team    │
  └─────────────────────────────────────────┘{C.RESET}
""")


def print_result(label: str, result):
    if result and result.success:
        print(f"\n{'='*70}")
        print(f"{C.GREEN}{C.BOLD} {result.agent_name} {C.RESET}{C.DIM} [{label}]{C.RESET}")
        print(f"{'='*70}")
        print(result.content)
    elif result:
        print(f"\n{'='*70}")
        print(f"{C.RED}{C.BOLD} {result.agent_name} - FAILED {C.RESET}{C.DIM} [{label}]{C.RESET}")
        print(f"{'='*70}")
        print(f"{C.RED}{result.error}{C.RESET}")
    print()


# ── LOGIN FLOW ──
def cmd_login(service: str):
    print_banner()

    if service == "claude":
        print(f"  Claude uses the CLI directly. Just run:{C.GREEN} claude{C.RESET}")
        print(f"  If not logged in, run:{C.GREEN} claude login{C.RESET}")
        return

    if service == "chatgpt":
        print(f"""{C.BOLD}  LOGIN: ChatGPT Plus{C.RESET}

  Step 1: Open {C.CYAN}https://chatgpt.com{C.RESET} in your browser (make sure you're logged in)

  Step 2: Open DevTools:
          Mac: {C.BOLD}Cmd + Option + I{C.RESET}
          Windows: {C.BOLD}F12{C.RESET}

  Step 3: Go to the {C.BOLD}Application{C.RESET} tab (or Storage tab)

  Step 4: In the left sidebar, click {C.BOLD}Cookies > https://chatgpt.com{C.RESET}

  Step 5: Find the cookie named {C.BOLD}__Secure-next-auth.session-token{C.RESET}
          (If you don't see it, try: Network tab > type "session" in filter >
           click any request > look in Request Headers for "Authorization: Bearer ...")

  {C.YELLOW}Alternative (easier):{C.RESET}
  Step 5b: Go to {C.CYAN}https://chatgpt.com/api/auth/session{C.RESET}
           Copy the {C.BOLD}accessToken{C.RESET} value from the JSON
""")
        token = input("  Paste your access token here: ").strip()
        if token:
            save_session("chatgpt", {"access_token": token})
            print(f"\n  {C.GREEN}ChatGPT logged in successfully!{C.RESET}")
        else:
            print(f"\n  {C.RED}No token provided.{C.RESET}")
        return

    if service == "gemini":
        print(f"""{C.BOLD}  LOGIN: Gemini (Free API Key){C.RESET}

  Step 1: Open {C.CYAN}https://aistudio.google.com/apikey{C.RESET} in your browser

  Step 2: Sign in with your Google account (same one as Gemini Advanced)

  Step 3: Click {C.BOLD}"Create API Key"{C.RESET}

  Step 4: Copy the API key (starts with AIza...)

  {C.GREEN}This is FREE — 500 requests/day for Gemini Flash, 25/day for Pro{C.RESET}
  {C.DIM}Same models as your Gemini Advanced subscription{C.RESET}
""")
        api_key = input("  Paste your API key: ").strip()
        if api_key:
            save_session("gemini", {"api_key": api_key, "model": "gemini-2.5-flash"})
            print(f"\n  {C.GREEN}Gemini logged in successfully!{C.RESET}")
        else:
            print(f"\n  {C.RED}No key provided.{C.RESET}")
        return

    if service == "perplexity":
        print(f"""{C.BOLD}  LOGIN: Perplexity (API Key){C.RESET}

  Step 1: Open {C.CYAN}https://www.perplexity.ai/settings/api{C.RESET} (logged into your Pro account)

  Step 2: Click {C.BOLD}"Generate API Key"{C.RESET}

  Step 3: Copy the key (starts with pplx-...)

  {C.GREEN}Pricing: ~$0.001 per query (sonar) = $1 for 1000 searches{C.RESET}
  {C.DIM}Much cheaper than any subscription, and it always works{C.RESET}
""")
        api_key = input("  Paste your API key: ").strip()
        if api_key:
            save_session("perplexity", {"api_key": api_key, "model": "sonar"})
            print(f"\n  {C.GREEN}Perplexity logged in successfully!{C.RESET}")
        else:
            print(f"\n  {C.RED}No key provided.{C.RESET}")
        return

    print(f"  {C.RED}Unknown service: {service}{C.RESET}")
    print("  Available: chatgpt, gemini, perplexity, claude")


# ── STATUS ──
def cmd_status(team: AgentTeam):
    print_banner()
    status = team.get_agent_status()

    for service, info in AGENT_INFO.items():
        role = info["role"]
        ready = status.get(role, False)
        color = info["color"]
        indicator = f"{C.GREEN}READY{C.RESET}" if ready else f"{C.RED}NOT LOGGED IN{C.RESET}"
        print(f"  {color}{info['label']:20s}{C.RESET} {info['service']:15s} {indicator}")

    print()
    not_ready = [s for s, i in AGENT_INFO.items() if not status.get(i["role"], False)]
    if not_ready:
        print(f"  {C.DIM}To log in:{C.RESET}")
        for s in not_ready:
            if s != "claude":
                print(f"    python3 aiteam.py login {s}")
            else:
                print("    claude login")
    else:
        print(f"  {C.GREEN}{C.BOLD}All agents ready! Run: python3 aiteam.py team \"your task\"{C.RESET}")


# ── SINGLE AGENT ──
def cmd_single(team: AgentTeam, role: str, task: str):
    print_banner()
    agent = team.agents.get(role)
    print(f"  {C.DIM}Task: {task}{C.RESET}")
    print(f"  {C.DIM}Agent: {agent.name if agent else role}{C.RESET}")
    print(f"  {C.DIM}Working...{C.RESET}")

    start = time.time()
    result = team.run_single(role, task)
    elapsed = time.time() - start

    print_result(role, result)
    print(f"  {C.DIM}Completed in {elapsed:.1f}s{C.RESET}")


# ── FULL TEAM PIPELINE ──
def cmd_team(team: AgentTeam, task: str):
    print_banner()
    status = team.get_agent_status()
    ready_count = sum(1 for v in status.values() if v)

    print(f"  {C.BOLD}FULL TEAM PIPELINE{C.RESET} ({ready_count}/4 agents ready)")
    print(f"  {C.DIM}Task: {task}{C.RESET}")
    print()

    # Show which agents will participate
    steps = [
        ("Step 1", "researcher", "Perplexity", "Research"),
        ("Step 1", "architect",  "ChatGPT",    "Architecture"),
        ("Step 2", "coder",      "Claude",     "Implementation"),
        ("Step 3", "reviewer",   "Gemini",     "Code Review"),
    ]
    for step, role, name, desc in steps:
        ready = status.get(role, False)
        indicator = f"{C.GREEN}GO{C.RESET}" if ready else f"{C.RED}SKIP{C.RESET}"
        print(f"  {C.DIM}{step}:{C.RESET} {name:12s} -> {desc:20s} [{indicator}]")

    print(f"\n  {C.DIM}Working...{C.RESET}")

    start = time.time()
    results = team.run_pipeline(task)
    elapsed = time.time() - start

    for label, result in results:
        print_result(label, result)

    # Summary
    succeeded = sum(1 for _, r in results if r and r.success)
    total = len(results)
    print(f"{'='*70}")
    print(f"  {C.BOLD}TEAM SUMMARY{C.RESET}")
    print(f"  {succeeded}/{total} agents completed successfully")
    print(f"  Total time: {elapsed:.1f}s")
    print(f"{'='*70}")


# ── INTERACTIVE CHAT ──

CHAT_HELP = f"""
  {C.BOLD}Commands{C.RESET}
    {C.CYAN}/help{C.RESET}              show this help
    {C.CYAN}/status{C.RESET}            which agents are online
    {C.CYAN}/all <msg>{C.RESET}         force the whole team (research + code + review)
    {C.CYAN}/chatgpt <msg>{C.RESET}     ask one agent directly
                       {C.DIM}(also /gemini, /perplexity, /review, /plan, /research){C.RESET}
    {C.CYAN}/file <path>{C.RESET}       attach a file so the team can see your real code
    {C.CYAN}/files{C.RESET}             list attached files ({C.CYAN}/files clear{C.RESET} to drop them)
    {C.CYAN}/review on|off{C.RESET}     Gemini auto-reviews code ChatGPT writes (default: on)
    {C.CYAN}/clear{C.RESET}             wipe the conversation history
    {C.CYAN}/exit{C.RESET}              quit

  {C.BOLD}Anything else{C.RESET} is auto-routed: ChatGPT writes code and answers,
  Gemini reviews it, Perplexity supplies current facts. Name a file in your message
  ("check aiteam.py") and it gets read in automatically.

  {C.BOLD}File edits{C.RESET} are shown as a diff and only written after you confirm.
"""

# Chat runs on the three web agents only — no Claude CLI in the loop.
# ChatGPT leads (writes the code and the final answer), Gemini reviews it,
# Perplexity supplies current facts.
LEAD, REVIEWER, RESEARCHER = "architect", "reviewer", "researcher"

# ChatGPT emits whole files in this envelope; the CLI diffs and applies them.
FILE_BLOCK_RE = re.compile(r"<<<FILE:\s*(.+?)\s*>>>\r?\n(.*?)\r?\n?<<<END>>>", re.S)

CODER_INSTRUCTION = (
    "You are the lead engineer. Answer the user directly and concisely.\n"
    "When you create or change a file, output the COMPLETE new file contents like this:\n"
    "<<<FILE: relative/path.py>>>\n"
    "...entire file...\n"
    "<<<END>>>\n"
    "Rules: one block per file; paths relative to the project root; never abbreviate "
    "with '...' or 'unchanged' — emit the whole file. Keep prose outside the blocks to "
    "a few sentences. If no file needs changing, write no blocks."
)

RESEARCH_INSTRUCTION = "Give current facts, libraries and sources. Bullets only, no preamble."
REVIEW_INSTRUCTION = (
    "Review this for real bugs, security issues and edge cases. Be specific and brief. "
    "Rate each finding CRITICAL / WARNING / SUGGESTION. If it looks correct, say so in one line."
)

_RESEARCH_WORDS = ("research", "latest", "docs", "library", "compare", "best practice",
                   "which package", "how do people", "current", "2025", "2026")
_REVIEW_WORDS = ("review", "audit", "security", "bug", "vulnerab", "is this safe",
                 "check this", "what's wrong", "whats wrong")
_CODE_WORDS = ("code", "implement", "build", "write", "fix", "refactor", "add ",
               "create", "edit", "change", "update", "rename", "test")

# Paths the team is never allowed to overwrite, even if it proposes them.
_PROTECTED = ("sessions.json", ".env")


def _has_word(text: str, words) -> bool:
    """Match on word starts, not bare substrings. Plain `in` misroutes constantly --
    "latest" contains "test", "address" contains "add" -- which sent research
    questions down the code path."""
    return any(re.search(r"\b" + re.escape(w), text) for w in words)


def _chat_route(msg: str) -> list:
    """Pick teammates for a chat message. The lead answers unless the message is
    purely a research or review request."""
    m = msg.lower()
    wants_research = _has_word(m, _RESEARCH_WORDS)
    wants_review = _has_word(m, _REVIEW_WORDS)
    wants_code = _has_word(m, _CODE_WORDS)

    if wants_review and not wants_code:
        return [REVIEWER]
    if wants_research and not wants_code:
        return [RESEARCHER]

    roles = [LEAD]
    if wants_research:
        roles.insert(0, RESEARCHER)
    if wants_code or wants_review:
        roles.append(REVIEWER)
    return roles


_PATH_RE = re.compile(r"[\w.][\w./\\-]*\.[A-Za-z0-9]{1,6}")


def _mentioned_files(msg: str, project_dir: str) -> list:
    """Project files named in the message — attached automatically so 'check X.py' works."""
    hits = []
    for tok in _PATH_RE.findall(msg):
        p = tok.strip(".,;:)ّ\"'")
        if os.path.isfile(os.path.join(project_dir, p)) and p not in hits:
            hits.append(p)
    return hits


def _history_context(history: list, turns: int = 6, budget: int = 3000) -> str:
    """Last few exchanges, so the team can follow a multi-turn conversation."""
    lines = [f"{h['who']}: {h['text']}" for h in history[-turns:]]
    return "\n".join(lines)[-budget:]


def _show_diff(path: str, old: str, new: str) -> bool:
    """Print a coloured unified diff. Returns False if the file is unchanged."""
    old_lines, new_lines = old.splitlines(), new.splitlines()
    diff = list(difflib.unified_diff(old_lines, new_lines,
                                     fromfile=f"a/{path}", tofile=f"b/{path}", lineterm=""))
    if not diff:
        return False
    print(f"\n  {C.BOLD}{path}{C.RESET} {C.DIM}({'new file' if not old else 'modified'}){C.RESET}")
    for line in diff[2:]:
        if line.startswith("+"):
            print(f"  {C.GREEN}{line}{C.RESET}")
        elif line.startswith("-"):
            print(f"  {C.RED}{line}{C.RESET}")
        elif line.startswith("@@"):
            print(f"  {C.CYAN}{line}{C.RESET}")
        else:
            print(f"  {C.DIM}{line}{C.RESET}")
    return True


def _preview_file_blocks(blocks: list, project_dir: str) -> list:
    """Validate proposed files and print their diffs. Returns the writable ones.

    Nothing escapes the project root and credential files stay untouchable — these
    edits come from a remote model."""
    root = os.path.abspath(project_dir)
    pending = []
    for path, content in blocks:
        path = path.strip().replace("\\", "/")
        abs_path = os.path.abspath(os.path.join(root, path))
        if os.path.commonpath([abs_path, root]) != root:
            print(f"  {C.RED}refused {path}: outside the project{C.RESET}")
            continue
        base = os.path.basename(abs_path).lower()
        if any(base == p or base.startswith(p) for p in _PROTECTED):
            print(f"  {C.RED}refused {path}: credential file{C.RESET}")
            continue
        old = ""
        if os.path.isfile(abs_path):
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                old = f.read()
        if _show_diff(path, old, content):
            pending.append((abs_path, path, content))
    return pending


def _write_pending(pending: list):
    """Write the previewed files, but only after an explicit yes."""
    if not pending:
        return
    try:
        answer = input(f"\n  {C.BOLD}Apply {len(pending)} file change(s)? [y/N]{C.RESET} ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = "n"
    if answer not in ("y", "yes"):
        print(f"  {C.DIM}skipped — nothing written{C.RESET}\n")
        return

    for abs_path, path, content in pending:
        os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
        with open(abs_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content if content.endswith("\n") else content + "\n")
        print(f"  {C.GREEN}wrote {path}{C.RESET}")
    print()


def _chat_turn(team: AgentTeam, msg: str, history: list, project_ctx: str,
               attached: dict, force_roles, auto_review: bool):
    status = team.get_agent_status()
    roles = [r for r in (force_roles or _chat_route(msg)) if status.get(r)]
    if not roles:
        print(f"  {C.RED}No agent available for that. Try /status.{C.RESET}\n")
        return

    # Pull in any project file the user named, so "check X.py" actually sees X.py.
    auto = _mentioned_files(msg, team.project_dir)
    file_ctx = dict(attached)
    if auto:
        text, _ = read_files_for_context(auto, team.project_dir)
        if text:
            file_ctx["_auto"] = text
            print(f"  {C.DIM}reading {', '.join(auto)}{C.RESET}")

    parts = [project_ctx]
    if file_ctx:
        parts.append("\n\n".join(file_ctx.values()))
    convo = _history_context(history)
    if convo:
        parts.append(f"--- CONVERSATION SO FAR ---\n{convo}")
    context = "\n\n".join(p for p in parts if p)

    start = time.time()
    contributors, transcript = [], []

    # 1. Research first — its findings feed the lead.
    if RESEARCHER in roles:
        print(f"  {C.DIM}{team.agents[RESEARCHER].name} researching...{C.RESET}")
        res = team.run_single(RESEARCHER, f"{RESEARCH_INSTRUCTION}\n\n{msg}", context)
        if res.success:
            contributors.append(res.agent_name)
            transcript.append((res.agent_name, C.MAGENTA, res.content))
            context += f"\n\n--- RESEARCH ({res.agent_name}) ---\n{res.content[:2500]}"
        else:
            print(f"  {C.DIM}({res.agent_name} unavailable: {res.error[:80]}){C.RESET}")

    # 2. Lead answers / writes the code.
    lead_result, blocks = None, []
    if LEAD in roles:
        print(f"  {C.DIM}{team.agents[LEAD].name} working...{C.RESET}")
        lead_result = team.run_single(LEAD, f"{CODER_INSTRUCTION}\n\n--- USER ---\n{msg}", context)
        if lead_result.success:
            contributors.append(lead_result.agent_name)
            blocks = FILE_BLOCK_RE.findall(lead_result.content)
        else:
            print(f"  {C.DIM}({lead_result.agent_name} failed: {lead_result.error[:100]}){C.RESET}")

    # 3. Show the lead's answer and the diff now, so the review below refers to code
    #    the user has already seen.
    if lead_result and lead_result.success:
        prose = FILE_BLOCK_RE.sub("", lead_result.content).strip()
        print(f"\n{C.BOLD}{C.GREEN}team >{C.RESET} {prose if prose else '(files below)'}")
    pending = _preview_file_blocks(blocks, team.project_dir) if blocks else []

    # 4. Reviewer checks the code — the proposed files if there are any, else the topic.
    if REVIEWER in roles and (auto_review or force_roles == [REVIEWER]):
        if blocks:
            subject = "\n\n".join(f"=== {p} ===\n{c}" for p, c in blocks)[:8000]
        elif lead_result and lead_result.success:
            subject = lead_result.content[:6000]
        else:
            subject = msg
        print(f"  {C.DIM}{team.agents[REVIEWER].name} reviewing...{C.RESET}")
        # Proposed blocks are self-contained, so skip the context to save tokens.
        # Without them the reviewer needs `context` — that's where the file the user
        # named actually lives, and passing "" left it reviewing a filename alone.
        rev = team.run_single(REVIEWER, f"{REVIEW_INSTRUCTION}\n\n{subject}",
                              "" if blocks else context)
        if rev.success:
            contributors.append(rev.agent_name)
            transcript.append((rev.agent_name, C.YELLOW, rev.content))
        else:
            print(f"  {C.DIM}({rev.agent_name} unavailable: {rev.error[:80]}){C.RESET}")

    if not contributors:
        print(f"\n  {C.RED}No agent could answer.{C.RESET}\n")
        return

    # 5. Teammate sections, then the write confirmation last.
    for name, color, content in transcript:
        print(f"\n{color}{C.BOLD}{name} >{C.RESET} {content}")
    print()

    _write_pending(pending)

    print(f"  {C.DIM}— {', '.join(contributors)} · {time.time() - start:.1f}s{C.RESET}\n")

    answer = (lead_result.content if lead_result and lead_result.success else "")
    answer += "\n" + "\n".join(c for _, _, c in transcript)
    history.append({"who": "user", "text": msg})
    history.append({"who": "team", "text": answer[:2000]})


def cmd_chat(team: AgentTeam):
    # gemini_webapi logs two loguru lines on every single call, which buries the
    # conversation. Auth state is still visible through /status.
    try:
        from loguru import logger as _loguru
        _loguru.disable("gemini_webapi")
    except ImportError:
        pass

    print_banner()
    status = team.get_agent_status()
    online = [AGENT_INFO[s]["label"] for s, i in AGENT_INFO.items()
              if i["role"] != "coder" and status.get(i["role"])]
    print(f"  {C.BOLD}CHAT MODE{C.RESET} {C.DIM}— type /help for commands, /exit to quit{C.RESET}")
    print(f"  {C.DIM}Online: {', '.join(online) if online else 'nobody — run: python aiteam.py status'}{C.RESET}")
    print(f"  {C.DIM}ChatGPT codes · Gemini reviews · Perplexity researches{C.RESET}\n")

    project_ctx = team.get_project_context()
    history, attached, auto_review = [], {}, True

    while True:
        try:
            msg = input(f"{C.BOLD}you >{C.RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n  {C.DIM}bye{C.RESET}")
            return
        if not msg:
            continue

        force_roles = None
        if msg.startswith("/"):
            bits = msg[1:].split(maxsplit=1)
            cmd = bits[0].lower() if bits else ""
            rest = bits[1].strip() if len(bits) > 1 else ""

            if cmd in ("exit", "quit", "q"):
                print(f"  {C.DIM}bye{C.RESET}")
                return
            if cmd == "help":
                print(CHAT_HELP)
                continue
            if cmd == "status":
                cmd_status(team)
                print()
                continue
            if cmd == "clear":
                history.clear()
                print(f"  {C.DIM}conversation cleared{C.RESET}\n")
                continue
            if cmd == "review" and rest.lower() in ("on", "off"):
                auto_review = rest.lower() == "on"
                print(f"  {C.DIM}Gemini auto-review {'on' if auto_review else 'off'}{C.RESET}\n")
                continue
            if cmd == "file":
                if not rest:
                    print(f"  {C.RED}Usage: /file path/to/file.py{C.RESET}\n")
                    continue
                text, notes = read_files_for_context([rest], team.project_dir)
                for n in notes:
                    print(f"  {C.YELLOW}{n}{C.RESET}")
                if text:
                    attached[rest] = text
                    print(f"  {C.GREEN}attached {rest}{C.RESET} {C.DIM}({len(text)} chars){C.RESET}\n")
                else:
                    print()
                continue
            if cmd == "files":
                if rest.lower() == "clear":
                    attached.clear()
                    print(f"  {C.DIM}attachments cleared{C.RESET}\n")
                elif attached:
                    for p in attached:
                        print(f"  {C.DIM}- {p}{C.RESET}")
                    print()
                else:
                    print(f"  {C.DIM}no files attached{C.RESET}\n")
                continue
            if cmd in ("all", "team"):
                if not rest:
                    print(f"  {C.RED}Usage: /all <your question>{C.RESET}\n")
                    continue
                force_roles, msg = [RESEARCHER, LEAD, REVIEWER], rest
            elif cmd in ROLE_MAP:
                role = ROLE_MAP[cmd]
                if role == "coder":
                    print(f"  {C.DIM}Chat runs on ChatGPT, Gemini and Perplexity — "
                          f"Claude isn't in the loop. Use /chatgpt to write code.{C.RESET}\n")
                    continue
                if not rest:
                    print(f"  {C.RED}Usage: /{cmd} <your question>{C.RESET}\n")
                    continue
                force_roles, msg = [role], rest
            else:
                print(f"  {C.RED}Unknown command: /{cmd}{C.RESET} {C.DIM}— try /help{C.RESET}\n")
                continue

        try:
            _chat_turn(team, msg, history, project_ctx, attached, force_roles, auto_review)
        except KeyboardInterrupt:
            print(f"\n  {C.DIM}(interrupted){C.RESET}\n")


def cmd_build(team: AgentTeam, task: str, auto: bool):
    """Autonomous coding agent — ChatGPT reads, edits and runs; Gemini reviews."""
    from agents.coding_agent import CodingAgent

    print_banner()
    try:
        from loguru import logger as _loguru
        _loguru.disable("gemini_webapi")
    except ImportError:
        pass

    start = time.time()
    agent = CodingAgent(team, team.project_dir, auto_approve=auto)
    try:
        done = agent.run(task)
    except KeyboardInterrupt:
        print(f"\n  {C.YELLOW}stopped{C.RESET}\n")
        return
    print(f"  {C.DIM}{'finished' if done else 'stopped early'} in {time.time() - start:.1f}s{C.RESET}\n")


# Everything the dispatcher handles explicitly; anything else is treated as a
# prompt for the coding agent.
KNOWN_COMMANDS = {
    "status", "chat", "repl", "help", "--help", "-h", "login", "logout",
    "build", "do", "agent", "team", "full", "pipeline", "all", *ROLE_MAP,
}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1].lower()
    project_dir = os.getcwd()
    team = AgentTeam(project_dir)

    if command == "status":
        cmd_status(team)
        return

    if command in ("chat", "repl"):
        cmd_chat(team)
        return

    # `build` is the autonomous coding agent. A bare prompt means the same thing,
    # so `aiteam.py "fix the failing test"` behaves like calling claude directly.
    if command in ("build", "do", "agent") or command not in KNOWN_COMMANDS:
        args = sys.argv[1:] if command not in KNOWN_COMMANDS else sys.argv[2:]
        auto = False
        if "--yes" in args:
            auto = True
            args = [a for a in args if a != "--yes"]
        task = " ".join(args).strip()
        if not task:
            print(f"{C.RED}Give it something to do.{C.RESET}")
            print(f'Example: python aiteam.py build "make the failing test pass"')
            return
        cmd_build(team, task, auto)
        return

    if command in ("help", "--help", "-h"):
        print(__doc__)
        return

    if command == "login":
        if len(sys.argv) < 3:
            print(f"{C.RED}Specify a service: chatgpt, gemini, perplexity, claude{C.RESET}")
            return
        cmd_login(sys.argv[2].lower())
        return

    if command == "logout":
        if len(sys.argv) < 3:
            print(f"{C.RED}Specify a service: chatgpt, gemini, perplexity{C.RESET}")
            return
        from agents.session_store import remove_session
        remove_session(sys.argv[2].lower())
        print(f"  {C.GREEN}Logged out of {sys.argv[2]}{C.RESET}")
        return

    # All other commands need a task
    if len(sys.argv) < 3:
        print(f"{C.RED}Please provide a task description.{C.RESET}")
        print(f'Example: python3 aiteam.py {command} "Build a REST API"')
        return

    task = " ".join(sys.argv[2:])

    if command in ("team", "full", "pipeline", "all"):
        cmd_team(team, task)
    elif command in ROLE_MAP:
        cmd_single(team, ROLE_MAP[command], task)
    else:
        print(f"{C.RED}Unknown command: {command}{C.RESET}")
        print(__doc__)


if __name__ == "__main__":
    main()
