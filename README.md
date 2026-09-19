<p align="center">
  <h1 align="center">AI Team MCP</h1>
  <p align="center"><b>Multi-model MCP server for Claude Code — use ChatGPT, Gemini &amp; Perplexity with no API keys</b></p>
  <p align="center">Stop copy-pasting between four AI tabs.<br>Give Claude Code a team meeting instead.</p>
</p>

<p align="center">
  <a href="https://github.com/needsomehelp/ai-team-mcp/stargazers"><img src="https://img.shields.io/github/stars/needsomehelp/ai-team-mcp?style=social" alt="Stars"></a>
  <a href="https://github.com/needsomehelp/ai-team-mcp/actions"><img src="https://github.com/needsomehelp/ai-team-mcp/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="#"><img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python"></a>
  <a href="#"><img src="https://img.shields.io/badge/Protocol-MCP-orange.svg" alt="MCP"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License"></a>
  <a href="#"><img src="https://img.shields.io/badge/API%20Keys-Not%20Required-red.svg" alt="No API Keys"></a>
</p>

---

## The problem

You pay for ChatGPT Plus. And Gemini Advanced. And Perplexity Pro. And Claude.

Then you spend your day being a human message bus between all four of them —
copy the code into ChatGPT, paste the critique into Gemini, alt-tab to
Perplexity because one of them hallucinated an API that shipped in 2023.

**You already own the subscriptions. Why are you buying API credits to use them?**

---

## What AI Team MCP does

It turns Claude Code into the team lead and the other three into specialists it
can actually call — over your existing browser sessions, so nothing goes on a
metered API bill.

```text
You: "Design the auth for this, then tear it apart"

  Claude Code (Team Lead)
        |
        |  calls a standup
        v
  ┌─────────────────────────────────────────────┐
  │  Perplexity   "python-jose is deprecated,   │
  │  (Research)    here's what shipped in 2026" │
  │                                             │
  │  ChatGPT      "Split the middleware, your   │
  │  (Architect)   refresh flow has a race"     │
  │                                             │
  │  Gemini       "2 security holes, 1 timing   │
  │  (Reviewer)    attack in the token compare" │
  └─────────────────────────────────────────────┘
        |
        v
  Claude writes the code, merges the notes, ships one answer.
```

One prompt. Four subscriptions you already pay for. Zero tab-switching.

---

## Use ChatGPT, Gemini and Perplexity without API keys

| AI | Role | Auth | Costs you |
|----|------|------|-----------|
| **Claude** | Lead Coder — implementation, debugging, synthesis | Claude Code CLI login | your Claude sub |
| **ChatGPT** | Architect — system design, planning, trade-offs | browser session token | your Plus/Pro sub |
| **Gemini** | Reviewer — code review, bugs, security | browser cookie | your Advanced sub |
| **Perplexity** | Researcher — latest docs, real-time info | browser cookie | your Pro sub |

No provider API key is required for any of the four. There's no gateway key, no
proxy and no account to create. Credentials sit in a gitignored `sessions.json`
on your machine, and every request goes to the provider's own servers.

⚠️ **The honest caveat:** this works by reusing your browser session against each
provider's internal web endpoints — the same ones their web apps use. It is not
an official API, it is not covered by their developer terms, and it *will* break
when they change things. [Read the disclaimer](#disclaimer) before you depend on
it for anything load-bearing. For Gemini there's a stable official alternative
(a free AI Studio key) if you'd rather not.

---

## Install AI Team MCP in Claude Code

**Step 1 — clone and install**

```bash
git clone https://github.com/needsomehelp/ai-team-mcp.git
cd ai-team-mcp/ai-team
pip install -r requirements.txt
```

**Step 2 — register the MCP server**

```bash
claude mcp add ai-team -s user python3 $(pwd)/mcp_server.py
```

**Step 3 — log the team in** (each is a one-time browser copy, details below)

```
> Use ai_team_login with service='chatgpt', token='<access token>'
> Use ai_team_login with service='gemini', token='<__Secure-1PSID cookie>'
> Use ai_team_login with service='perplexity', token='<Cookie header>'
```

**Step 4 — verify**

```bash
claude mcp list
# ai-team ✓ Connected
```

Then just talk:

```
> "Ask ChatGPT to design a caching layer"
> "Have Gemini review this file for security issues"
> "Research the latest Stripe API with Perplexity"
> "Run the full AI team on building auth"
```

---

## The highlights

**🧠 Four specialists, one prompt.** `ai_team_run` fans a task out to research →
architecture → code → review and hands back one merged answer, not four walls of
text.

**🔑 No API keys, no new bills.** Browser-session auth against subscriptions you
already pay for. Your ChatGPT Plus, Gemini Advanced and Perplexity Pro already
cover this.

**👀 They can see your screenshots.** Pass images to ChatGPT or Gemini — a broken
UI, an error dialog, a whiteboard photo — and they actually look at it. Up to 4
images, 5 MB each, uploaded the same way the web app does, so your subscription
covers it. (Same caveat as everything else here: it rides on internal endpoints
and can break.)

**📂 They can read your actual code.** Every agent tool takes a `files` list, so
you get a review of *your* repo instead of a hypothetical. Secret files
(`.env*`, `sessions.json`) are skipped automatically.

**🎨 It generates images.** `generate_image` goes through your ChatGPT Plus
subscription (DALL·E), and falls back to free Pollinations/Flux if you're not
logged in — so it works either way. `generate_video` and `generate_audio` are
hand-off shims: they hand the prompt to a Higgsfield MCP connector if you have
one attached, and do nothing useful if you don't.

**⚡ Built to spend fewer tokens, not more.** Team mode is routed, not reflexive
— simple questions call zero agents. Agent replies are capped at 150 words each
and Claude synthesizes instead of quoting. Whether that beats a solo answer
depends on your task; the design goal is that it usually does.

**🖥️ Works outside Claude Code.** Full CLI (`aiteam team "..."`) and a REST API
server, so the same team is scriptable from anywhere.

**✅ 105 tests and CI.** ruff + pytest on every push.

---

## Before and after

| Without AI Team | With AI Team |
|----------------|-------------|
| One model does everything | 4 specialists collaborate |
| No architecture phase | ChatGPT designs the system first |
| No code review | Gemini reviews every output |
| Hallucinated APIs, docs from 2023 | Perplexity checks what's true today |
| You are the copy-paste layer | Automatic orchestration |
| You merge everything yourself | Claude synthesizes the final answer |
| Needs paid API keys | Uses subscriptions you already own |

---

## How browser-based MCP authentication works

Each agent reuses the session your browser already holds. You copy one value per
provider, once; it lands in `sessions.json` on your machine and is sent straight
to that provider. Nothing is relayed anywhere else.

| Service | What you copy | Where it lives |
|---------|--------------|----------------|
| ChatGPT | session access token | `sessions.json` (gitignored) |
| Gemini | `__Secure-1PSID` cookie | `sessions.json` (gitignored) |
| Perplexity | full `Cookie` header | `sessions.json` (gitignored) |
| Claude | nothing — uses your Claude Code login | — |

### ChatGPT MCP server setup

1. Log into [chatgpt.com](https://chatgpt.com)
2. Open `https://chatgpt.com/api/auth/session` in the same browser
3. Copy the `accessToken` value
4. `Use ai_team_login with service='chatgpt', token='<paste>'`

> Expires after a few weeks — repeat to refresh. If you hit a Turnstile 403, a
> new token won't help; paste the `Cookie` header from a logged-in tab instead
> and the two will be merged.

### Gemini MCP server setup

1. Log into [gemini.google.com](https://gemini.google.com)
2. DevTools (`F12`) → **Application** → **Cookies** → `gemini.google.com`
3. Copy `__Secure-1PSID`, and `__Secure-1PSIDTS` in the same sitting
4. `Use ai_team_login with service='gemini', token='<paste 1PSID>'`

> Copy both in one go. `1PSIDTS` rotates every few hours and stops matching an
> older `1PSID`, which silently downgrades you to an anonymous session.
>
> **Alternative:** a free [Google AI Studio](https://aistudio.google.com/apikey)
> key (500 req/day) works too and never expires.

### Perplexity MCP server setup

1. Log into [perplexity.ai](https://perplexity.ai)
2. DevTools (`F12`) → **Network** → click any `perplexity.ai` request
3. Copy the entire **Cookie** request header
4. `Use ai_team_login with service='perplexity', token='<paste>'`

> The cookie that matters is `__Secure-next-auth.session-token`. Login verifies
> the paste immediately and tells you which account it resolved to, so an expired
> copy fails loudly instead of quietly answering as a logged-out visitor.
>
> On Windows you can skip the copy entirely:
> `python tools/import_perplexity_cookies.py brave` pulls them out of the browser
> (needs an elevated shell for Brave/Edge).

### Claude setup

Already using Claude Code? You're done. Otherwise `claude login`.

### Verify all agents

```bash
python3 aiteam.py status
```

```
AI TEAM STATUS
========================================
  Claude Code          READY
  ChatGPT Plus         READY
  Gemini Advanced      READY
  Perplexity Pro       READY
```

---

## Usage

### From Claude Code (recommended)

Talk normally:

```
> Ask ChatGPT to design the database schema for a todo app
> Have Gemini review auth.py and middleware.py for security issues
> Get Perplexity to research best practices for Redis caching
> Run the full AI team on implementing OAuth2
```

#### Team mode

Say **`aiteam start`** to activate it, **`aiteam stop`** to leave. Team mode is
*routed*, not reflexive — Claude only pulls in an agent when the task actually
benefits, so a one-line question stays a one-line question.

### CLI

| Command | What it does |
|---------|-------------|
| `python3 aiteam.py team "task"` | Full pipeline: research → design → code → review |
| `python3 aiteam.py plan "task"` | ChatGPT designs architecture |
| `python3 aiteam.py review "task"` | Gemini reviews for bugs & security |
| `python3 aiteam.py research "task"` | Perplexity researches latest info |
| `python3 aiteam.py code "task"` | Claude implements |
| `python3 aiteam.py status` | Check which agents are ready |
| `python3 aiteam.py login <service>` | Log into a service |

```bash
cd ai-team-mcp/ai-team
chmod +x aiteam.sh
ln -s "$(pwd)/aiteam.sh" /usr/local/bin/aiteam

aiteam team "Build a REST API with auth"
```

### REST API

`api_server.py` exposes the same team over HTTP, for scripts and other tools.

---

## MCP tools

| Tool | Description |
|------|-------------|
| `ai_team_status` | Check which agents are online and ready |
| `ai_team_login` | Save and verify credentials for a service |
| `ask_chatgpt` | Task for ChatGPT — architecture, planning; takes `files` and `images` |
| `ask_gemini` | Task for Gemini — review, security; takes `files` and `images` |
| `ask_perplexity` | Task for Perplexity — research, docs; takes `files` |
| `ai_team_run` | Full 4-agent pipeline |
| `ai_team_chat` | Back-and-forth collaboration with ChatGPT |
| `generate_image` | Images via your ChatGPT Plus sub, free Pollinations/Flux fallback |
| `generate_image_dalle` | DALL·E 3 direct — **the one tool that needs an API key** (`sk-...`) |
| `generate_video` | Hands the prompt to an attached Higgsfield MCP connector |
| `generate_audio` | Hands the prompt to an attached Higgsfield MCP connector |

---

## Architecture

```
                    You (Terminal / Claude Code)
                              |
                       AI Team MCP Server
                              |
          +----------+--------+--------+-----------+
          |          |                 |            |
       Claude    ChatGPT           Gemini     Perplexity
      (Coder)   (Architect)     (Reviewer)  (Researcher)
          |          |                 |            |
          +----------+--------+--------+-----------+
                              |
                       Combined Result
```

```
ai-team-mcp/
├── ai-team/
│   ├── agents/
│   │   ├── base.py              # Base agent, image loading helpers
│   │   ├── claude_agent.py      # Claude Code integration
│   │   ├── chatgpt_agent.py     # ChatGPT (session token + cookies)
│   │   ├── gemini_agent.py      # Gemini (gemini-webapi + API key)
│   │   ├── perplexity_agent.py  # Perplexity (cookies + API key)
│   │   ├── session_store.py     # Local credential storage
│   │   └── team.py              # Coordinator & pipeline
│   ├── tools/
│   │   └── import_perplexity_cookies.py
│   ├── tests/                   # 105 tests
│   ├── mcp_server.py            # MCP server (11 tools)
│   ├── api_server.py            # REST API
│   ├── aiteam.py                # CLI
│   └── sessions.example.json    # Credentials template
├── .github/workflows/ci.yml     # ruff + pytest
└── CLAUDE.md                    # Team mode routing rules
```

---

## Try these prompts

```
"Build a Stripe payment integration"
"Design a scalable notification system"
"Review this codebase for SQL injection vulnerabilities"
"Research the latest changes in React 19"
"Compare Redis vs Memcached for session storage"
"Here's a screenshot of the bug — ask Gemini what's wrong with this layout"
"Generate a hero image for the landing page"
```

---

## Security and subscription privacy

- **Your credentials stay local.** Stored only in `sessions.json` on your machine.
- **`sessions.json` is gitignored**, along with its `.bak` siblings.
- **No data is sent to us.** Every call goes straight to the provider.
- **No middleman.** No proxy, no relay, no account.
- **Secret files are never uploaded.** `.env*` and `sessions.json` are filtered
  out of the `files` parameter before anything is sent.
- **Open source.** Audit every line yourself.

---

## Troubleshooting browser sessions

| Problem | Fix |
|---------|-----|
| ChatGPT "Unauthorized" | Fresh token from `chatgpt.com/api/auth/session` |
| ChatGPT 403 / Turnstile | Not a token problem — paste the `Cookie` header instead |
| Gemini works for text but images fail | `1PSID`/`1PSIDTS` mismatch — re-copy both together |
| Perplexity answers like a stranger | Session cookie expired; check `perplexity.ai/api/auth/session` returns a `user` |
| MCP not found | `claude mcp add ai-team -s user python3 /path/to/mcp_server.py` |
| `ModuleNotFoundError` | `pip install -r requirements.txt` |
| Agent "NOT LOGGED IN" | Run the login step for that service |

---

## FAQ

**Do I need an OpenAI, Google or Perplexity API key?**
No. That's the whole point. It uses the browser sessions behind subscriptions you
already pay for. A Google AI Studio key is supported for Gemini as an *optional*
alternative, not a requirement.

**Does this cost anything on top of my subscriptions?**
No. There's no hosted service, no proxy and no account. It's MIT-licensed code
running on your machine.

**Will it work in Cursor / Windsurf / other MCP clients?**
It's a standard MCP server, so in principle yes — but it's developed and tested
against Claude Code, and team mode's routing rules live in `CLAUDE.md`.

**Won't running four models cost more tokens?**
Usually less, in practice. Agents are only called when the task benefits, replies
are capped at 150 words, and Claude synthesizes rather than repeating them.

**How long do the logins last?**
ChatGPT tokens a few weeks, Gemini cookies hours to days, Perplexity until you
sign out. Each is a 30-second re-copy, and `ai_team_login` now tells you straight
away whether the paste actually authenticated.

**Is browser-cookie auth against the providers' terms?**
It uses your own account, for your own personal use — see the disclaimer below.
If that's a concern for your situation, use official API keys instead.

---

## Roadmap

- [x] Claude Code integration (MCP)
- [x] ChatGPT Plus (browser session token + cookies)
- [x] Gemini Advanced (browser cookies via gemini-webapi)
- [x] Perplexity Pro (browser cookies)
- [x] Full team pipeline (research → design → code → review)
- [x] Image input (vision) for ChatGPT and Gemini
- [x] Image generation (ChatGPT/DALL-E + free fallback)
- [x] CLI + REST API server
- [x] 105 automated tests + CI
- [ ] Grok integration
- [ ] DeepSeek integration
- [ ] Local LLM support (Ollama, LM Studio)
- [ ] Web dashboard
- [ ] VS Code extension
- [ ] Conversation memory
- [ ] Streaming responses

---

## Contributing

PRs welcome — see [CONTRIBUTING.md](ai-team/CONTRIBUTING.md).

**Good first issues:** new providers (Grok, DeepSeek, Mistral, Ollama), better
orchestration strategies, editor extensions, a web dashboard, streaming responses.

---

## Disclaimer

This project uses **unofficial browser-cookie authentication** for ChatGPT,
Gemini and Perplexity, built on reverse-engineered internal endpoints and
third-party libraries (`gemini-webapi`, `perplexity`). Providers change those
endpoints without notice and things will break; when they do, update the
dependencies — the upstream libraries are actively maintained.

For Gemini there's a stable, supported alternative: a free API key from
[Google AI Studio](https://aistudio.google.com/apikey).

This is for **personal use with your own subscriptions**. Credentials are stored
locally and never transmitted to any third party.

---

## License

MIT. Free to use, modify and distribute.

---

<p align="center">
<b>Stop asking one AI to do everything.<br>Give it colleagues.</b>
<br><br>
<a href="https://github.com/needsomehelp/ai-team-mcp">⭐ Star this repo</a> if it saves you a tab.
<br>
<a href="https://github.com/needsomehelp/ai-team-mcp/issues">Report a bug</a> · <a href="https://github.com/needsomehelp/ai-team-mcp/pulls">Submit a PR</a> · <a href="https://github.com/needsomehelp/ai-team-mcp/discussions">Discussions</a>
</p>
