<p align="center">
  <h1 align="center">AI Team MCP</h1>
  <p align="center"><b>One prompt. Four AI minds. Better code.</b></p>
  <p align="center">Claude writes code. ChatGPT designs architecture. Gemini reviews. Perplexity researches.<br>All inside one MCP server. All from your terminal.</p>
</p>

<p align="center">
  <a href="https://github.com/needsomehelp/ai-team-mcp/stargazers"><img src="https://img.shields.io/github/stars/needsomehelp/ai-team-mcp?style=social" alt="Stars"></a>
  <a href="https://github.com/needsomehelp/ai-team-mcp/actions"><img src="https://github.com/needsomehelp/ai-team-mcp/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="#"><img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python"></a>
  <a href="#"><img src="https://img.shields.io/badge/Protocol-MCP-orange.svg" alt="MCP"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License"></a>
  <a href="#"><img src="https://img.shields.io/badge/API%20Keys-Not%20Required-red.svg" alt="No API Keys"></a>
</p>

<p align="center"><i>Stop coding with one AI. Start shipping with an entire AI engineering team.</i></p>

---

## Why Four AI Models?

Each AI has a different strength. AI Team MCP uses them all:

| AI | Role | What It Does Best |
|----|------|-------------------|
| **Claude** | Lead Coder | Implementation, debugging, refactoring |
| **ChatGPT** | Architect | System design, planning, trade-offs |
| **Gemini** | Reviewer | Code review, bugs, security analysis |
| **Perplexity** | Researcher | Latest docs, libraries, real-time info |

**All use your existing browser subscriptions. No API keys required.**

---

## How It Works

```
You: "Build a FastAPI auth system with JWT"

   Perplexity (Researcher)     "Latest FastAPI-Security + python-jose patterns..."
        |
        v
   ChatGPT (Architect)         "Here's the folder structure, middleware design..."
        |
        v
   Claude (Lead Coder)         *writes production-ready code*
        |
        v
   Gemini (Reviewer)           "Found 2 security issues, 1 optimization..."
        |
        v
   Final Result                Production code, reviewed and researched.
```

**One prompt. Four AI experts. Zero tab-switching.**

---

## Quick Start (2 minutes)

### Step 1: Clone & Install

```bash
git clone https://github.com/needsomehelp/ai-team-mcp.git
cd ai-team-mcp/ai-team
pip install -r requirements.txt
```

### Step 2: Add to Claude Code

```bash
claude mcp add ai-team -s user python3 $(pwd)/mcp_server.py
```

### Step 3: Log in your agents

```
> Use ai_team_login with service='chatgpt', token='<your access token>'
> Use ai_team_login with service='gemini', token='<your __Secure-1PSID cookie>'
> Use ai_team_login with service='perplexity', token='<your cookie string>'
```

### Step 4: Verify

```bash
claude mcp list
# Should show: ai-team ✓ Connected
```

Now just talk to Claude Code:

```
> "Ask ChatGPT to design a caching layer"
> "Have Gemini review this code"
> "Research the latest Stripe API with Perplexity"
> "Run the full AI team on building auth"
```

---

## Without AI Team vs With AI Team

| Without AI Team | With AI Team |
|----------------|-------------|
| One model does everything | 4 specialized AI experts collaborate |
| No architecture phase | ChatGPT designs the system first |
| No code review | Gemini reviews every output |
| Hallucinated APIs & outdated docs | Perplexity researches real-time info |
| Manual copy-paste between tabs | Automatic orchestration |
| You merge everything yourself | Claude synthesizes the final result |
| Needs expensive API keys | Uses your existing browser subscriptions |

---

## Features

- **4 AI agents** working together on every task
- **Browser cookie auth** — uses your existing subscriptions (ChatGPT Plus, Gemini Advanced, Perplexity Pro)
- **No API keys required** — zero extra cost
- **Parallel execution** — agents work simultaneously when possible
- **Pipeline mode** — Research → Architecture → Code → Review
- **MCP compatible** — works natively inside Claude Code
- **CLI included** — also works standalone from any terminal
- **Your keys stay local** — credentials never leave your machine
- **62 tests** — full smoke test coverage for all agents
- **CI pipeline** — automated linting and testing

---

## Authentication Setup

Each AI uses **your own subscription** via browser cookies. No middleman, no extra costs.

| Service | What You Need | Cost |
|---------|--------------|------|
| ChatGPT | Session token from browser | Free (your Plus/Pro sub) |
| Gemini | `__Secure-1PSID` cookie from browser | Free (your Advanced sub) |
| Perplexity | Cookie string from browser | Free (your Pro sub) |
| Claude | Already logged into Claude Code | Free (your Claude sub) |

---

### ChatGPT Setup

1. Log into [chatgpt.com](https://chatgpt.com) in your browser
2. Open this URL in the same browser: `https://chatgpt.com/api/auth/session`
3. Copy the `accessToken` value (the long string)
4. In Claude Code: `Use ai_team_login with service='chatgpt', token='<paste>'`

> Token expires after a few weeks. Just repeat these steps to refresh.

---

### Gemini Setup

1. Log into [gemini.google.com](https://gemini.google.com) in your browser
2. Open DevTools (`F12`) → **Application** → **Cookies** → `gemini.google.com`
3. Find `__Secure-1PSID` — copy its value
4. *(Optional)* Also copy `__Secure-1PSIDTS` for longer sessions
5. In Claude Code: `Use ai_team_login with service='gemini', token='<paste 1PSID value>'`

> Uses the `gemini-webapi` library under the hood. Your Gemini Advanced subscription gives you access to the latest models.

**Alternative:** You can also use a free API key from [Google AI Studio](https://aistudio.google.com/apikey) (500 req/day).

---

### Perplexity Setup

1. Log into [perplexity.ai](https://perplexity.ai) in your browser
2. Open DevTools (`F12`) → **Network** tab
3. Click any request to `perplexity.ai`
4. Find the **Cookie** request header → copy the entire value
5. In Claude Code: `Use ai_team_login with service='perplexity', token='<paste>'`

> Uses your Pro/Max subscription. Cookies expire when you log out.

---

### Claude Setup

Claude uses your existing Claude Code CLI login. If you're already using Claude Code, you're done.

```bash
# Only if not logged in yet:
claude login
```

---

### Verify All Agents

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

### From Claude Code (MCP) — Recommended

Just talk naturally:

```
> Ask ChatGPT to design the database schema for a todo app
> Have Gemini review this file for security issues
> Get Perplexity to research best practices for Redis caching
> Run the full AI team on implementing OAuth2
```

#### Team Mode

Say **`aiteam start`** in Claude Code to activate team mode. Every response becomes a team effort — Claude automatically consults all agents before answering.

Say **`aiteam stop`** to return to normal.

### CLI Commands

| Command | What it does |
|---------|-------------|
| `python3 aiteam.py team "task"` | Full pipeline: research → design → code → review |
| `python3 aiteam.py plan "task"` | ChatGPT designs architecture |
| `python3 aiteam.py review "task"` | Gemini reviews for bugs & security |
| `python3 aiteam.py research "task"` | Perplexity researches latest info |
| `python3 aiteam.py code "task"` | Claude implements |
| `python3 aiteam.py status` | Check which agents are ready |
| `python3 aiteam.py login <service>` | Login to a service |

#### Global CLI (optional)

```bash
cd ai-team-mcp/ai-team
chmod +x aiteam.sh
ln -s "$(pwd)/aiteam.sh" /usr/local/bin/aiteam

# Now use from anywhere:
aiteam team "Build a REST API with auth"
```

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

### MCP Tools

| Tool | Description |
|------|-------------|
| `ai_team_status` | Check which agents are online and ready |
| `ai_team_login` | Save login credentials for a service |
| `ask_chatgpt` | Send a task to ChatGPT (architecture/planning) |
| `ask_gemini` | Send a task to Gemini (code review/security) |
| `ask_perplexity` | Send a task to Perplexity (research/docs) |
| `ai_team_run` | Run the full 4-agent pipeline |
| `ai_team_chat` | Collaborate with ChatGPT in team mode |

---

## Examples

```bash
# Full team pipeline
aiteam team "Build a REST API with authentication using FastAPI"

# Individual agents
aiteam research "Best Python ORMs in 2026"
aiteam plan "Microservice architecture for e-commerce"
aiteam review "Check my auth middleware for security vulnerabilities"
aiteam code "Implement WebSocket real-time notifications"
```

### Try These Prompts in Claude Code

```
"Build a Stripe payment integration"
"Design a scalable notification system"
"Review this codebase for SQL injection vulnerabilities"
"Research the latest changes in React 19"
"Compare Redis vs Memcached for session storage"
"Build a CI/CD pipeline for this project"
```

---

## Project Structure

```
ai-team-mcp/
├── ai-team/
│   ├── agents/
│   │   ├── base.py              # Base agent class
│   │   ├── claude_agent.py      # Claude Code integration
│   │   ├── chatgpt_agent.py     # ChatGPT (session token)
│   │   ├── gemini_agent.py      # Gemini (gemini-webapi + API key)
│   │   ├── perplexity_agent.py  # Perplexity (cookies + API key)
│   │   ├── session_store.py     # Secure credential storage
│   │   └── team.py              # Team coordinator & pipeline
│   ├── tests/
│   │   ├── test_agents.py       # 43 agent smoke tests
│   │   ├── test_prime.py        # Demo module tests
│   │   └── conftest.py          # Test configuration
│   ├── mcp_server.py            # MCP server (7 tools)
│   ├── aiteam.py                # CLI interface
│   ├── aiteam.sh                # Global shell command
│   ├── requirements.txt         # Python dependencies
│   └── sessions.example.json    # Credentials template
├── .github/workflows/ci.yml     # CI pipeline (ruff + pytest)
├── CLAUDE.md                    # Team mode instructions
└── README.md
```

---

## Security

- **Your keys stay local.** Credentials stored in `sessions.json` on your machine only.
- **`sessions.json` is gitignored.** Never committed to the repo.
- **No data sent to us.** All API calls go directly to AI providers.
- **No middleman.** No proxy server, no third-party relay.
- **Open source.** Audit every line of code yourself.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| ChatGPT "Unauthorized" | Get fresh token from `chatgpt.com/api/auth/session` |
| Gemini not responding | Re-copy `__Secure-1PSID` cookie from browser |
| Perplexity 401 error | Re-copy cookies from DevTools → Network tab |
| MCP not found | Run `claude mcp add ai-team -s user python3 /path/to/mcp_server.py` |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| Agent "NOT LOGGED IN" | Run login step for that service |

---

## Roadmap

- [x] Claude Code integration (MCP)
- [x] ChatGPT Plus (browser session token)
- [x] Gemini Advanced (browser cookies via gemini-webapi)
- [x] Perplexity Pro (browser cookies)
- [x] Full team pipeline (research → design → code → review)
- [x] CLI interface
- [x] Team mode for Claude Code
- [x] 62 automated tests + CI pipeline
- [ ] Grok integration
- [ ] DeepSeek integration
- [ ] Local LLM support (Ollama, LM Studio)
- [ ] Web dashboard
- [ ] VS Code extension
- [ ] Conversation memory
- [ ] Streaming responses

---

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](ai-team/CONTRIBUTING.md) for details.

### Good First Issues

- New AI provider integrations (Grok, DeepSeek, Mistral, Ollama)
- Better orchestration strategies
- VS Code / JetBrains extensions
- Web dashboard
- Streaming responses

---

## Disclaimer

This project uses **unofficial browser cookie authentication** for ChatGPT, Gemini, and Perplexity. These methods rely on reverse-engineered internal APIs and third-party libraries (`gemini-webapi`, `perplexity`). They may break at any time if providers change their internal endpoints. When they break, update the dependencies — the upstream libraries are actively maintained.

For Gemini, you can alternatively use a **free official API key** from [Google AI Studio](https://aistudio.google.com/apikey) which is stable and supported.

This tool is for **personal use** with your own subscriptions. Your credentials are stored locally and never transmitted to any third party.

---

## License

MIT License. Free to use, modify, and distribute.

---

<p align="center">
<b>Stop asking one AI to do everything.<br>Build an AI engineering team instead.</b>
<br><br>
<a href="https://github.com/needsomehelp/ai-team-mcp">⭐ Star this repo</a> if it saves you time.
<br>
<a href="https://github.com/needsomehelp/ai-team-mcp/issues">Report a bug</a> · <a href="https://github.com/needsomehelp/ai-team-mcp/pulls">Submit a PR</a> · <a href="https://github.com/needsomehelp/ai-team-mcp/discussions">Discussions</a>
</p>
