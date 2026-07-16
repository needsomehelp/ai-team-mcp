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
    python3 aiteam.py team "Build a REST API with auth"     # All 4 agents
    python3 aiteam.py code "Fix the login bug"              # Claude only
    python3 aiteam.py review "Check main.py for issues"     # Gemini only
    python3 aiteam.py plan "Design a caching layer"         # ChatGPT only
    python3 aiteam.py research "Best Python web frameworks" # Perplexity only
    python3 aiteam.py status                                # See who's logged in
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.team import AgentTeam
from agents.session_store import save_session


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
