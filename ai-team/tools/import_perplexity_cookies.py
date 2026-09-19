"""Import Perplexity cookies straight from a local browser into sessions.json.

Brave and Edge store cookies under Chromium's app-bound encryption, so
browser_cookie3 can only decrypt them from an ELEVATED process -- hence the
admin requirement. Chrome on this machine returns an empty jar instead of
raising, which is the same problem wearing a different hat.

Run from an Administrator PowerShell:

    cd "C:\\Users\\subha\\Downloads\\ai-team-mcp\\ai-team"
    venv\\Scripts\\python.exe tools\\import_perplexity_cookies.py

Optional: pass a browser name to skip the others (brave, chrome, edge, firefox).
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SESSIONS = ROOT / "sessions.json"
BROWSERS = ("brave", "chrome", "edge", "firefox")


def load_from(browser: str) -> dict:
    import browser_cookie3

    loader = getattr(browser_cookie3, browser, None)
    if loader is None:
        raise RuntimeError(f"browser_cookie3 has no loader for {browser!r}")
    jar = loader(domain_name="perplexity.ai")
    # Later duplicates win: the host-scoped cookie is the live one when both a
    # .perplexity.ai and a www.perplexity.ai copy exist.
    return {c.name: c.value for c in jar}


def main() -> int:
    from agents.perplexity_agent import PerplexityWebAgent

    wanted = [sys.argv[1].lower()] if len(sys.argv) > 1 else list(BROWSERS)

    cookies, source = {}, None
    for browser in wanted:
        try:
            found = load_from(browser)
        except Exception as e:
            print(f"  {browser:8} failed: {type(e).__name__}: {str(e)[:120]}")
            continue
        print(f"  {browser:8} {len(found)} cookies")
        if PerplexityWebAgent.KEY_COOKIES[0] in found:
            cookies, source = found, browser
            break

    if not cookies:
        print("\nNo browser had __Secure-next-auth.session-token.")
        print("Either none of them is signed into perplexity.ai, or this process")
        print("is not elevated -- re-run it from an Administrator PowerShell.")
        return 1

    print(f"\nFound a session token in {source}. Verifying with Perplexity...")
    ok, detail = PerplexityWebAgent.check_auth(cookies)
    if not ok:
        print(f"NOT authenticated: {detail}")
        print("Sign in at perplexity.ai in that browser, then re-run this.")
        return 1

    existing = {}
    if SESSIONS.exists():
        existing = json.loads(SESSIONS.read_text(encoding="utf-8"))
    entry = existing.get("perplexity") or {}
    merged = dict(entry.get("cookies") or {})
    merged.update(cookies)
    entry["cookies"] = merged
    existing["perplexity"] = entry
    SESSIONS.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    print(f"Saved {len(merged)} cookies to {SESSIONS}")
    print(f"Verified logged in as {detail} -- ask_perplexity should work now.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
