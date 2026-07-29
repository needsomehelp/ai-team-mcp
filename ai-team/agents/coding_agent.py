"""Autonomous coding agent — the execution loop the chat mode was missing.

Plain chat can only emit text, which is why asking ChatGPT to "start the server"
produced instructions instead of action. Here the model emits tool calls, this
module executes them against the real project, and the results are fed back so it
can iterate: read a file, change it, run the tests, read the traceback, fix it.

ChatGPT drives (no Claude anywhere in this loop). Gemini reviews the final diff.
Perplexity is only consulted when the model explicitly asks for research.

Safety: every write and every shell command is diffed/echoed and needs your yes
unless you pass --yes. Paths can't escape the project and credential files are
never readable or writable — this is a remote model steering your filesystem.
"""

import os
import re
import subprocess
import sys
import difflib

from .base import _is_secret_file


def _platform_note() -> str:
    """Tell the model what machine it is on. Without this it emits `python3`,
    `cat`, and heredocs on Windows, where none of them exist."""
    if sys.platform == "win32":
        return ("\nMACHINE: Windows. Commands run through cmd.exe. Use `python`, NOT "
                "`python3`. `cat`, `touch`, `ls`, heredocs and POSIX redirection are "
                "unavailable — use `dir`, `type`, or better, the WRITE request.\n")
    return "\nMACHINE: Unix-like. Commands run through /bin/sh.\n"


# ── The protocol the model must speak ─────────────────────────

TOOL_PROTOCOL = """You are one half of a two-part system.

You do NOT execute anything yourself — that is correct and expected. You emit
REQUEST LINES. A separate program (the harness) parses your output, performs the
action on the user's machine, and sends you the real result in the next message.

So: writing `<<<RUN: pytest>>>` is NOT a claim that you ran pytest. It is a request
asking the harness to run it. The harness does the running; you do the deciding.
Refusing to emit a request line stalls the system — there is no one else to ask.
You do not need the user to paste files: request them and they arrive.

Emit one or more request lines, then stop and wait for results:

<<<LIST: .>>>                      list files in a directory
<<<READ: path/to/file.py>>>        read a file
<<<SEARCH: some text>>>            find which files contain some text
<<<RUN: python -m pytest -q>>>     run a shell command in the project root
<<<APPEND: path/to/file.md>>>      add text to the END of an existing file
...text to add...
<<<ENDWRITE>>>
<<<REPLACE: path/to/file.py>>>     change one exact passage, leaving the rest alone
<<<OLD>>>
the exact existing text to find
<<<NEW>>>
what it becomes
<<<ENDWRITE>>>
<<<WRITE: path/to/file.py>>>       create a NEW file, or fully rewrite a small one
...entire file content...
<<<ENDWRITE>>>
<<<DONE>>>                         finished — say what you did in a sentence

Rules:
- Every request except WRITE must fit on ONE line. A <<<RUN: ...>>> spanning several
  lines is not parsed at all and silently does nothing.
- To create or change a file you MUST use <<<WRITE:>>>. Never write files through the
  shell — no heredocs (<<'EOF'), no `cat >>`, no `echo >`, no output redirection.
  Those are not parsed, and they do not work on this machine anyway.
- <<<ENDWRITE>>> closes a WRITE block and NOTHING else. There is no general-purpose
  end marker. Never put an end marker after READ, LIST, SEARCH or RUN — those are
  complete on their own line. A stray end marker is ignored and wastes a step.
- Investigate before editing. READ a file before you change it.
- Do not read the same file twice. Read it once, then make the change.
- PREFER APPEND or REPLACE on any file that already exists. WRITE replaces the whole
  file, so anything you leave out is DELETED. Adding a section to a long README means
  APPEND, not WRITE — a rewrite that drops existing sections is a failed task.
- REPLACE needs the OLD text to match the file exactly, character for character.
- WRITE takes the COMPLETE new file. Never write "..." or "unchanged".
- After changing code, RUN the tests or the script to prove it works.
- If a command fails, read the error and fix it. That's the point of the loop.
- One step at a time. Emit a few calls, look at the results, then continue.
- Emit <<<DONE>>> only when the task is actually finished and verified.
"""

# Models drift back into chat mode after a few turns and start printing bash
# snippets for the user to run. Repeating the rule at the END of the prompt, where
# it is freshest, cut the wasted steps on a fix-the-bug task from 11 to 2.
TURN_REMINDER = """

--- YOUR TURN (step {step} of {total}) ---
Emit request lines now. A markdown ```bash block is not parsed and does nothing —
only <<<RUN: ...>>> reaches the harness. Do not ask the user to paste files or run
commands; request them yourself. If the task is done AND verified, emit <<<DONE>>>."""

DONE_CHALLENGE = """
[harness] You emitted <<<DONE>>> but you have not written a single file or run a
single command — only read things. Reading is not doing. The task is not finished.
Make the actual change now with <<<WRITE: path>>>...<<<ENDWRITE>>>, then verify it.
If you are certain the task genuinely requires no changes, emit <<<DONE>>> again and
state in one line why nothing needed to change.
"""

NO_TOOLS_NUDGE = """
[harness] Step {step} contained no request lines, so nothing happened and the task
did not advance. You are not being asked to claim you executed anything — only to
emit a request line that this program will execute for you. Any output shown above
is genuine output the harness already produced from your earlier requests.
Emit one now: <<<READ: file>>>, <<<LIST: .>>>, <<<RUN: cmd>>>,
<<<WRITE: file>>>...<<<END>>>, or <<<DONE>>>.
"""

_END = r"<<<END(?:WRITE|APPEND|REPLACE)?>>>"

ACTION_RE = re.compile(
    # REPLACE and APPEND come first: they are the safe edits, and both must be tried
    # before the generic WRITE alternative so their bodies aren't swallowed.
    r"<<<REPLACE:\s*(?P<rpath>[^>\n]+?)\s*>>>\r?\n<<<OLD>>>\r?\n(?P<rold>.*?)\r?\n"
    r"<<<NEW>>>\r?\n(?P<rnew>.*?)\r?\n?" + _END +
    r"|<<<APPEND:\s*(?P<apath>[^>\n]+?)\s*>>>\r?\n(?P<abody>.*?)\r?\n?" + _END +
    # Accept ENDWRITE or a bare END as the write terminator: models reliably emit
    # whichever they remember, and rejecting one silently drops the whole edit.
    r"|<<<WRITE:\s*(?P<wpath>[^>\n]+?)\s*>>>\r?\n(?P<wbody>.*?)\r?\n?" + _END +
    r"|<<<(?P<verb>READ|LIST|RUN|SEARCH):\s*(?P<arg>[^>\n]+?)\s*>>>"
    r"|<<<(?P<done>DONE)>>>",
    re.S,
)

# Models treat <<<END>>> as a generic "end of my request" marker and append it after
# READ/LIST/RUN too. Those leftovers are noise — strip them from the displayed prose
# rather than showing the user a stray marker.
STRAY_END_RE = re.compile(r"<<<END(?:WRITE)?>>>")

# An opener that ACTION_RE could not match — almost always a RUN carrying a
# multi-line heredoc, or a WRITE whose terminator never arrived. Silently dropping
# these is what made runs look like the agent "did nothing".
MALFORMED_RE = re.compile(r"<<<\s*(?:WRITE|READ|LIST|RUN|SEARCH)\b", re.I)

MALFORMED_NUDGE = """
[harness] Your last message contained a request that could not be parsed, so it was
discarded and nothing ran. The usual causes:
  - a <<<RUN: ...>>> spread over multiple lines (it must be ONE line), or
  - shell file-writing (heredoc, `cat >>`, `echo >`), which is not supported, or
  - a <<<WRITE:>>> with no closing <<<ENDWRITE>>>.
To change a file, use exactly this shape and nothing else:
<<<WRITE: path/to/file.ext>>>
(the complete new file content)
<<<ENDWRITE>>>
"""

# Commands that are never worth the risk of a model typo, even with approval.
_BLOCKED = (
    "rm -rf /", "rm -rf ~", ":(){", "mkfs", "format c:", "del /f /s /q c:\\",
    "shutdown", "reboot", "diskpart", "git push", "git commit", "git reset --hard",
)

MAX_OUTPUT = 4000


class C:
    RESET = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
    GREEN = "\033[92m"; YELLOW = "\033[93m"; RED = "\033[91m"; CYAN = "\033[96m"


class CodingAgent:
    """Runs ChatGPT in a read/write/run loop against the project."""

    def __init__(self, team, project_dir: str, auto_approve: bool = False,
                 max_steps: int = 14, review: bool = True):
        self.team = team
        self.root = os.path.abspath(project_dir)
        self.auto = auto_approve
        self.max_steps = max_steps
        self.review = review
        self.changed_files = {}   # path -> (before, after)
        self._seen = {}           # repeated read/list requests -> step first served
        self._did_work = False    # has anything beyond reading actually happened?

    # ── path safety ──

    def _safe(self, rel_path: str):
        """Resolve inside the project or refuse. Returns (abs_path, error)."""
        rel = rel_path.strip().strip('"').strip("'").replace("\\", "/")
        abs_path = os.path.abspath(os.path.join(self.root, rel))
        if os.path.commonpath([abs_path, self.root]) != self.root:
            return None, f"refused: {rel} is outside the project"
        if _is_secret_file(os.path.basename(abs_path)):
            return None, f"refused: {rel} holds credentials"
        return abs_path, None

    # ── tools ──

    def _tool_list(self, arg: str) -> str:
        abs_path, err = self._safe(arg or ".")
        if err:
            return err
        if not os.path.isdir(abs_path):
            return f"not a directory: {arg}"
        skip = {".git", "__pycache__", "venv", ".venv", "node_modules"}
        out = []
        for name in sorted(os.listdir(abs_path)):
            if name in skip:
                continue
            full = os.path.join(abs_path, name)
            out.append(f"{name}/" if os.path.isdir(full) else name)
        return "\n".join(out) or "(empty)"

    def _tool_read(self, arg: str) -> str:
        abs_path, err = self._safe(arg)
        if err:
            return err
        if not os.path.isfile(abs_path):
            return f"not found: {arg}"
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        if len(text) > MAX_OUTPUT:
            text = text[:MAX_OUTPUT] + "\n[truncated]"
        return text

    def _tool_search(self, arg: str) -> str:
        hits, skip = [], {".git", "__pycache__", "venv", ".venv", "node_modules"}
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in skip]
            for name in filenames:
                if _is_secret_file(name) or not name.endswith(
                        (".py", ".md", ".txt", ".json", ".js", ".ts", ".toml", ".cfg")):
                    continue
                full = os.path.join(dirpath, name)
                try:
                    with open(full, "r", encoding="utf-8", errors="replace") as f:
                        for i, line in enumerate(f, 1):
                            if arg in line:
                                rel = os.path.relpath(full, self.root).replace("\\", "/")
                                hits.append(f"{rel}:{i}: {line.strip()[:120]}")
                                break
                except OSError:
                    continue
                if len(hits) >= 40:
                    return "\n".join(hits) + "\n[more matches truncated]"
        return "\n".join(hits) or f"no matches for: {arg}"

    def _tool_run(self, cmd: str) -> str:
        low = cmd.lower()
        if any(b in low for b in _BLOCKED):
            return "refused: destructive command blocked"
        print(f"  {C.YELLOW}$ {cmd}{C.RESET}")
        if not self._confirm(f"  {C.BOLD}Run this command? [y/N]{C.RESET} "):
            return "user declined to run this command"
        try:
            proc = subprocess.run(cmd, shell=True, cwd=self.root, capture_output=True,
                                  text=True, timeout=180)
        except subprocess.TimeoutExpired:
            return "command timed out after 180s"
        except OSError as e:
            return f"could not run: {e}"
        self._did_work = True
        out = (proc.stdout or "") + (proc.stderr or "")
        out = out.strip() or "(no output)"
        if len(out) > MAX_OUTPUT:
            out = out[:MAX_OUTPUT] + "\n[truncated]"
        print(f"  {C.DIM}exit {proc.returncode}{C.RESET}")
        return f"exit code {proc.returncode}\n{out}"

    def _tool_write(self, rel_path: str, body: str) -> str:
        abs_path, err = self._safe(rel_path)
        if err:
            print(f"  {C.RED}{err}{C.RESET}")
            return err
        old = ""
        if os.path.isfile(abs_path):
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                old = f.read()
        new = body if body.endswith("\n") else body + "\n"
        # A whole-file rewrite that loses a third of the file is almost never what
        # was asked for -- it is the model failing to reproduce content it should
        # have left alone. Observed live: "add instructions to the README" came back
        # as a rewrite that deleted 65% of it, including every setup section.
        if old and len(new) < len(old) * 0.7:
            lost = 100 - int(len(new) / len(old) * 100)
            msg = (f"REFUSED: this WRITE would delete {lost}% of {rel_path} "
                   f"({len(old)} -> {len(new)} bytes). You are rewriting a file you "
                   f"should be editing. Use <<<APPEND: {rel_path}>>> to add to it, or "
                   f"<<<REPLACE: {rel_path}>>> to change one passage.")
            print(f"  {C.RED}refused: would delete {lost}% of {rel_path}{C.RESET}")
            if self.auto:
                return msg
            print(f"  {C.YELLOW}Only accept this if a full rewrite is genuinely "
                  f"intended.{C.RESET}")
            if not self._confirm(f"  {C.BOLD}Really shrink {rel_path} by {lost}%? [y/N]{C.RESET} "):
                return msg
        if old == new:
            print(f"  {C.DIM}{rel_path} already identical — nothing to write{C.RESET}")
            return f"{rel_path} already had exactly this content — no change"
        if not self._show_diff(rel_path, old, new):
            return f"{rel_path} unchanged"
        if not self._confirm(f"  {C.BOLD}Write {rel_path}? [y/N]{C.RESET} "):
            return f"user declined the change to {rel_path}"
        os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
        with open(abs_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new)
        before = self.changed_files.get(rel_path, (old, None))[0]
        self.changed_files[rel_path] = (before, new)
        self._did_work = True
        print(f"  {C.GREEN}wrote {rel_path}{C.RESET}")
        return f"wrote {rel_path} ({len(new.splitlines())} lines)"

    def _tool_append(self, rel_path: str, body: str) -> str:
        """Add to the end of a file without touching what is already there."""
        abs_path, err = self._safe(rel_path)
        if err:
            print(f"  {C.RED}{err}{C.RESET}")
            return err
        if not os.path.isfile(abs_path):
            return f"{rel_path} does not exist — use WRITE to create it"
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            old = f.read()
        addition = body if body.endswith("\n") else body + "\n"
        new = old + ("" if old.endswith("\n") or not old else "\n") + addition
        return self._commit(abs_path, rel_path, old, new, "appended to")

    def _tool_replace(self, rel_path: str, old_text: str, new_text: str) -> str:
        """Swap one exact passage, leaving the rest of the file untouched."""
        abs_path, err = self._safe(rel_path)
        if err:
            print(f"  {C.RED}{err}{C.RESET}")
            return err
        if not os.path.isfile(abs_path):
            return f"{rel_path} does not exist — use WRITE to create it"
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            old = f.read()
        count = old.count(old_text)
        if count == 0:
            print(f"  {C.RED}REPLACE: text not found in {rel_path}{C.RESET}")
            return (f"the OLD text was not found in {rel_path}. It must match the file "
                    f"exactly, character for character. READ the file and copy the "
                    f"passage verbatim.")
        if count > 1:
            print(f"  {C.RED}REPLACE: text appears {count}x in {rel_path}{C.RESET}")
            return (f"the OLD text appears {count} times in {rel_path}, so the edit is "
                    f"ambiguous. Include more surrounding lines to make it unique.")
        return self._commit(abs_path, rel_path, old, old.replace(old_text, new_text),
                            "edited")

    def _commit(self, abs_path: str, rel_path: str, old: str, new: str, verb: str) -> str:
        """Shared diff/confirm/write tail for append and replace."""
        if old == new:
            print(f"  {C.DIM}{rel_path} unchanged{C.RESET}")
            return f"{rel_path} was already in that state"
        if not self._show_diff(rel_path, old, new):
            return f"{rel_path} unchanged"
        if not self._confirm(f"  {C.BOLD}Apply to {rel_path}? [y/N]{C.RESET} "):
            return f"user declined the change to {rel_path}"
        with open(abs_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new)
        before = self.changed_files.get(rel_path, (old, None))[0]
        self.changed_files[rel_path] = (before, new)
        self._did_work = True
        print(f"  {C.GREEN}{verb} {rel_path}{C.RESET}")
        return f"{verb} {rel_path} ({len(new.splitlines())} lines now)"

    # ── ui helpers ──

    def _confirm(self, prompt: str) -> bool:
        if self.auto:
            return True
        try:
            return input(prompt).strip().lower() in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            return False

    @staticmethod
    def _show_diff(path: str, old: str, new: str) -> bool:
        diff = list(difflib.unified_diff(old.splitlines(), new.splitlines(),
                                         fromfile=f"a/{path}", tofile=f"b/{path}",
                                         lineterm=""))
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

    # ── the loop ──

    def _dispatch(self, match, step: int = 0) -> tuple:
        """Execute one parsed tool call. Returns (label, result) or None for DONE."""
        if match.group("done"):
            return None
        if match.group("rpath") is not None:
            path = match.group("rpath")
            print(f"  {C.DIM}replace in {path}{C.RESET}")
            return (f"REPLACE {path}",
                    self._tool_replace(path, match.group("rold"), match.group("rnew")))
        if match.group("apath") is not None:
            path = match.group("apath")
            print(f"  {C.DIM}append to {path}{C.RESET}")
            return f"APPEND {path}", self._tool_append(path, match.group("abody"))
        if match.group("wpath") is not None:
            path = match.group("wpath")
            return f"WRITE {path}", self._tool_write(path, match.group("wbody"))
        verb, arg = match.group("verb").upper(), match.group("arg")

        # Re-reading an unchanged file returns identical bytes, so the transcript
        # grows without new information and the model loops on it forever. Answer
        # the repeat with a pointer instead of the content.
        if verb in ("READ", "LIST"):
            key = f"{verb}:{arg}"
            if key in self._seen and arg not in self.changed_files:
                print(f"  {C.YELLOW}{verb.lower()} {arg} (already done — not repeating){C.RESET}")
                return (f"{verb} {arg}",
                        f"You already ran this at step {self._seen[key]} and the result is "
                        f"earlier in this transcript; the file has not changed since. Do not "
                        f"request it again — use what you have and make the edit now.")
            self._seen[key] = step

        if verb == "READ":
            print(f"  {C.DIM}read {arg}{C.RESET}")
            return f"READ {arg}", self._tool_read(arg)
        if verb == "LIST":
            print(f"  {C.DIM}list {arg}{C.RESET}")
            return f"LIST {arg}", self._tool_list(arg)
        if verb == "SEARCH":
            print(f"  {C.DIM}search {arg!r}{C.RESET}")
            return f"SEARCH {arg}", self._tool_search(arg)
        return f"RUN {arg}", self._tool_run(arg)

    def run(self, task: str) -> bool:
        # Drivers in preference order. ChatGPT is the strongest coder here but
        # sometimes refuses the protocol outright, reading a request line as a claim
        # to have executed something; when that happens we hand the wheel to Gemini
        # rather than burning the whole step budget arguing with it.
        candidates = [self.team.agents[r] for r in ("architect", "reviewer", "researcher")
                      if r in self.team.agents and self.team.agents[r].is_ready()]
        if not candidates:
            print(f"  {C.RED}No agent is logged in — run: python aiteam.py status{C.RESET}")
            return False
        brain = candidates[0]

        print(f"  {C.BOLD}TASK{C.RESET} {task}")
        print(f"  {C.DIM}{brain.name} is driving · "
              f"{'auto-approving' if self.auto else 'asking before each write/command'}{C.RESET}\n")

        transcript = ""
        finished = False
        idle_turns = 0
        done_challenged = 0
        for step in range(1, self.max_steps + 1):
            print(f"  {C.DIM}── step {step}/{self.max_steps}{C.RESET}")
            prompt = f"{TOOL_PROTOCOL}{_platform_note()}\n--- TASK ---\n{task}"
            if transcript:
                prompt += f"\n\n--- WHAT HAS HAPPENED SO FAR ---\n{transcript[-12000:]}"
            else:
                prompt += f"\n\n--- PROJECT FILES ---\n{self._tool_list('.')}"
            prompt += TURN_REMINDER.format(step=step, total=self.max_steps)

            result = brain.execute(prompt, "")
            if not result.success:
                print(f"  {C.RED}{brain.name} failed: {result.error}{C.RESET}")
                return False

            matches = list(ACTION_RE.finditer(result.content))
            prose = STRAY_END_RE.sub("", ACTION_RE.sub("", result.content)).strip()
            if prose:
                print(f"  {C.CYAN}{prose[:600]}{C.RESET}")

            # A mangled request is a different failure from chatting, and needs a
            # different correction — say exactly what was wrong with the syntax.
            if MALFORMED_RE.search(prose):
                print(f"  {C.YELLOW}unparseable request (multi-line RUN or shell "
                      f"file-write) — correcting{C.RESET}")
                transcript += MALFORMED_NUDGE
                if not matches:
                    continue

            if not matches:
                # No tool calls: the model lapsed into chatting. Nudge, and give up
                # rather than burn the whole budget if it keeps doing it.
                idle_turns += 1
                if idle_turns >= 2 and len(candidates) > 1:
                    candidates.pop(0)
                    brain = candidates[0]
                    idle_turns = 0
                    print(f"  {C.YELLOW}driver won't use the protocol — handing over to "
                          f"{brain.name}{C.RESET}")
                    continue
                if idle_turns >= 4:
                    print(f"  {C.RED}{brain.name} kept replying with prose instead of "
                          f"request lines — stopping.{C.RESET}")
                    break
                print(f"  {C.YELLOW}(no request lines — nudging){C.RESET}")
                transcript += NO_TOOLS_NUDGE.format(step=step)
                continue
            idle_turns = 0

            premature_done = False
            for m in matches:
                dispatched = self._dispatch(m, step)
                if dispatched is None:
                    # Reading a repo and then declaring victory is the most common
                    # failure here. Challenge a DONE that changed and ran nothing;
                    # accept it the second time, since some tasks need no changes.
                    if not self._did_work and done_challenged < 2:
                        done_challenged += 1
                        premature_done = True
                    else:
                        print(f"  {C.GREEN}agent reports the task is complete{C.RESET}")
                        finished = True
                    break
                label, output = dispatched
                # Frame results as harness output. Left as a bare "[RUN x]\noutput"
                # the model reads its own transcript as hypothetical and starts
                # insisting it has no way to run anything.
                transcript += (f"\n[step {step}] You called: {label}\n"
                               f"[harness executed it on the real machine — actual output]\n"
                               f"{output}\n")
            if premature_done:
                print(f"  {C.YELLOW}claimed done without changing anything — "
                      f"pushing back{C.RESET}")
                transcript += DONE_CHALLENGE
                continue
            if finished:
                break
        else:
            print(f"\n  {C.YELLOW}Hit the {self.max_steps}-step limit without finishing.{C.RESET}")

        self._final_report(task)
        return finished

    def _final_report(self, task: str):
        if not self.changed_files:
            print(f"\n  {C.DIM}No files were changed.{C.RESET}\n")
            return

        print(f"\n  {C.BOLD}Files changed{C.RESET}")
        for path in self.changed_files:
            print(f"    {C.GREEN}{path}{C.RESET}")

        reviewer = self.team.agents.get("reviewer")
        if not (self.review and reviewer and reviewer.is_ready()):
            print()
            return

        diff_text = ""
        for path, (before, after) in self.changed_files.items():
            diff_text += "\n".join(difflib.unified_diff(
                (before or "").splitlines(), (after or "").splitlines(),
                fromfile=f"a/{path}", tofile=f"b/{path}", lineterm="")) + "\n"

        print(f"\n  {C.DIM}{reviewer.name} reviewing the diff...{C.RESET}")
        rev = reviewer.execute(
            "Review this diff for real bugs, security issues and edge cases. Be brief "
            "and specific. Rate findings CRITICAL / WARNING / SUGGESTION. If it looks "
            f"correct, say so in one line.\n\nTask was: {task}\n\n{diff_text[:9000]}", "")
        if rev.success:
            print(f"\n{C.YELLOW}{C.BOLD}{rev.name if hasattr(rev, 'name') else reviewer.name} >{C.RESET} {rev.content}\n")
        else:
            print(f"  {C.DIM}({reviewer.name} unavailable){C.RESET}\n")
