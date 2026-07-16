<p align="center">
  <h1 align="center">AI Team</h1>
  <p align="center"><b>Turn Claude Code into a full software engineering team.</b></p>
  <p align="center">Claude writes code. ChatGPT designs architecture. Gemini reviews. Perplexity researches.<br>All inside one MCP server. All from your terminal.</p>
</p>

<p align="center">
  <a href="https://github.com/needsomehelp/Team-/stargazers"><img src="https://img.shields.io/github/stars/needsomehelp/Team-?style=social" alt="Stars"></a>
  <a href="#"><img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python"></a>
  <a href="#"><img src="https://img.shields.io/badge/MCP-Compatible-orange.svg" alt="MCP"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License"></a>
  <a href="#"><img src="https://img.shields.io/badge/Cost-Free%20%26%20Open%20Source-red.svg" alt="Free"></a>
</p>

<p align="center"><i>Stop coding with one AI. Start shipping with an entire AI engineering team.</i></p>

---

## Demo

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

## Why AI Team?

You already pay for multiple AI subscriptions. But using them means:

```
Open ChatGPT tab -> copy code -> Open Claude tab -> paste ->
Open Gemini -> paste -> Open Perplexity -> search ->
Manually merge everything -> Repeat forever
```

**That's not a team. That's chaos.**

AI Team fixes this:

| Without AI Team | With AI Team |
|----------------|-------------|
| One model does everything | 4 specialized AI experts collaborate |
| No architecture phase | ChatGPT designs the system first |
| No code review | Gemini reviews every output |
| Hallucinated APIs & outdated docs | Perplexity researches real-time info |
| Manual copy-paste between tabs | Automatic orchestration |
| You merge everything yourself | Claude synthesizes the final result |

---

## Features

- **Claude** remains your coding lead — writes, debugs, refactors
- **ChatGPT** designs architecture, plans systems, evaluates trade-offs
- **Gemini** reviews code for bugs, security flaws, and performance
- **Perplexity** researches latest docs, libraries, and best practices
- **Parallel execution** — agents work simultaneously when possible
- **MCP compatible** — works natively inside Claude Code
- **CLI included** — also works standalone from any terminal
- **Your keys stay local** — credentials never leave your machine
- **Open source** — audit every line of code

---

## Quick Start (2 minutes)

### Step 1: Clone & Install

```bash
git clone https://github.com/needsomehelp/Team-.git
cd Team-/ai-team
pip install -r requirements.txt
```

### Step 2: Add to Claude Code

```bash
claude mcp add ai-team -s user python3 /absolute/path/to/Team-/ai-team/mcp_server.py
```

> Replace `/absolute/path/to/` with the actual path where you cloned the repo.

### Step 3: Verify it works

```bash
claude mcp list
```

You should see `ai-team` in the list. Done! Now just talk to Claude Code:

```
> "Ask ChatGPT to design a caching layer"
> "Have Gemini review this code"
> "Research the latest Stripe API with Perplexity"
> "Run the full AI team on building auth"
```

---

## Authentication Setup

Each AI uses **your own subscription**. No middleman, no extra costs, no API proxy.

| Service | Auth Method | Cost |
|---------|------------|------|
| ChatGPT | Browser session token | Free (uses your Plus/Pro sub) |
| Gemini | API key | Free (Google AI Studio) |
| Perplexity | API key or browser cookies | Free with Pro / ~$0.001 per query via API |
| Claude | CLI login | Free (uses your Claude Code sub) |

---

### ChatGPT Setup

> **Important:** This uses your ChatGPT web session — NOT the OpenAI API. No API key needed.

**Step 1:** Log into [chatgpt.com](https://chatgpt.com) in your browser

**Step 2:** Open this URL in the same browser:

```
https://chatgpt.com/api/auth/session
```

**Step 3:** You'll see JSON like this:

```json
{
  "accessToken": "eyJhbGciOiJSUzI1NiIsInR5cCI6Ikp..."
}
```

**Step 4:** Copy ONLY the token value (the long string after `"accessToken":`)

**Step 5:** Save it:

```bash
python3 aiteam.py login chatgpt
# Paste your access token when prompted
```

> **Token expires?** If ChatGPT stops working, just repeat these steps to get a fresh token. This happens after you log out or after a few weeks.

> **Getting "Unauthorized"?** Make sure you're logged into ChatGPT first, then refresh the `/api/auth/session` page.

---

### Gemini Setup

> **Free!** Google gives you 500 requests/day on Gemini Flash, 25/day on Pro.

**Step 1:** Go to [Google AI Studio](https://aistudio.google.com/apikey)

**Step 2:** Sign in with your Google account

**Step 3:** Click **"Create API Key"**

**Step 4:** Copy the key (starts with `AIza...`)

**Step 5:** Save it:

```bash
python3 aiteam.py login gemini
# Paste your API key when prompted
```

> **Multiple Google accounts?** Make sure you're signed into the correct account before creating the key.

---

### Perplexity Setup

Choose one of two methods:

#### Option A: API Key (Recommended)

**Step 1:** Go to [Perplexity API Settings](https://www.perplexity.ai/settings/api)

**Step 2:** Click **"Generate API Key"**

**Step 3:** Copy the key (starts with `pplx-...`)

**Step 4:** Save it:

```bash
python3 aiteam.py login perplexity
# Paste your API key when prompted
```

> Costs ~$0.001 per query. You may need to add credits.

#### Option B: Browser Cookies (Free with Pro)

**Step 1:** Open [perplexity.ai](https://perplexity.ai) and make sure you're logged in

**Step 2:** Open DevTools:
- **Mac:** `Cmd + Option + I`
- **Windows/Linux:** `F12`

**Step 3:** Go to the **Network** tab

**Step 4:** Click on any request to `perplexity.ai`

**Step 5:** In the request headers, find **Cookie** and copy the entire value

**Step 6:** Save it:

```bash
python3 aiteam.py login perplexity
# Paste the cookie string when prompted
```

> Cookies expire when you log out. Re-export if Perplexity stops working.

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

Expected output:

```
AI TEAM STATUS
========================================
  Claude Code          READY
  ChatGPT Plus         READY
  Gemini Advanced      READY
  Perplexity Pro       READY
```

All four should show **READY**. If any show **NOT LOGGED IN**, re-run the login step for that service.

---

## Usage

### From Claude Code (MCP) — Recommended

Once installed, just talk naturally:

```
> Ask ChatGPT to design the database schema for a todo app
> Have Gemini review this file for security issues
> Get Perplexity to research best practices for Redis caching
> Run the full AI team on implementing OAuth2
```

#### Team Mode

Add this to your project's `CLAUDE.md` to enable automatic team collaboration:

```markdown
When the user says "aiteam start":
- Activate TEAM MODE
- On every response, consult ChatGPT, Gemini, and Perplexity before replying
- Synthesize all responses into one unified answer
```

Then just type **`aiteam start`** and every response becomes a team effort.

### CLI Commands

Use directly from the terminal:

| Command | What it does |
|---------|-------------|
| `python3 aiteam.py team "task"` | Full pipeline: research -> design -> code -> review |
| `python3 aiteam.py plan "task"` | ChatGPT designs architecture |
| `python3 aiteam.py review "task"` | Gemini reviews for bugs & security |
| `python3 aiteam.py research "task"` | Perplexity researches latest info |
| `python3 aiteam.py code "task"` | Claude implements |
| `python3 aiteam.py status` | Check which agents are ready |
| `python3 aiteam.py login <service>` | Login to a service |

#### Global CLI (optional)

```bash
cd Team-/ai-team
chmod +x aiteam.sh
ln -s "$(pwd)/aiteam.sh" /usr/local/bin/aiteam

# Now use from anywhere:
aiteam status
aiteam team "Build a REST API with auth"
```

---

## Examples

### Full Team Pipeline

```bash
aiteam team "Build a REST API with authentication using FastAPI"
```

What happens:
1. **Perplexity** researches latest FastAPI auth patterns and libraries
2. **ChatGPT** designs the architecture, folder structure, and API endpoints
3. **Claude** implements production-ready code
4. **Gemini** reviews for bugs, security issues, and performance improvements

### Individual Agents

```bash
# Research latest technologies
aiteam research "Best Python ORMs in 2025"

# Design a system
aiteam plan "Microservice architecture for an e-commerce platform"

# Review code for issues
aiteam review "Check my auth middleware for security vulnerabilities"

# Write code
aiteam code "Implement WebSocket real-time notifications"
```

### Example Prompts to Try

```
"Build a Stripe payment integration"
"Design a scalable notification system"
"Review this codebase for SQL injection vulnerabilities"
"Research the latest changes in React 19"
"Implement JWT auth with refresh tokens"
"Optimize these database queries for performance"
"Build a CI/CD pipeline for this project"
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

### MCP Tools Reference

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

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| ChatGPT returns "Unauthorized" | Token expired or not logged in | Log into chatgpt.com, get a fresh token from `/api/auth/session` |
| ChatGPT returns empty response | Wrong token copied | Copy only the `accessToken` value, not the full JSON |
| Gemini returns 403 | Invalid or disabled API key | Generate a new key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| Gemini quota exceeded | Free tier limit reached | Wait 24 hours for reset, or upgrade |
| Perplexity returns 401 | Invalid API key or expired cookies | Re-generate API key or re-export cookies |
| Claude MCP not found | Wrong path in `claude mcp add` | Run `claude mcp list` to check, re-add with correct absolute path |
| `ModuleNotFoundError` | Missing dependencies | Run `pip install -r requirements.txt` |
| Agent shows "NOT LOGGED IN" | Credentials not saved | Run `python3 aiteam.py login <service>` |

### Verification Checklist

- [ ] `claude mcp list` shows `ai-team`
- [ ] `python3 aiteam.py status` shows all agents as READY
- [ ] ChatGPT token is fresh (not expired)
- [ ] Gemini API key starts with `AIza...`
- [ ] Perplexity key starts with `pplx-...` (if using API)

---

## FAQ

**Do I need an OpenAI API key?**
No. AI Team uses your ChatGPT web session, not the OpenAI API. Your Plus/Pro subscription is enough.

**Is Gemini really free?**
Yes. Google AI Studio gives free API access: 500 requests/day (Flash), 25/day (Pro).

**Can I use it without all 4 agents?**
Yes. Any agent you don't log in will be skipped. You can use just Claude + ChatGPT, or any combination.

**Does it send my code to all AIs?**
Only when you ask it to. Individual agent calls only go to that one AI. The full pipeline sends the task through all four.

**Where are my credentials stored?**
In `sessions.json` on your local machine only. It's gitignored and never uploaded anywhere.

**Can I add my own AI agents?**
Yes! Extend `agents/base.py` and add your agent. PRs welcome.

---

## Project Structure

```
Team-/
├── ai-team/
│   ├── agents/
│   │   ├── base.py              # Base agent class
│   │   ├── claude_agent.py      # Claude Code integration
│   │   ├── chatgpt_agent.py     # ChatGPT agent
│   │   ├── gemini_agent.py      # Gemini agent
│   │   ├── perplexity_agent.py  # Perplexity agent
│   │   ├── session_store.py     # Secure credential storage
│   │   └── team.py              # Team coordinator & pipeline
│   ├── mcp_server.py            # MCP server for Claude Code
│   ├── aiteam.py                # CLI interface
│   ├── aiteam.sh                # Global shell command
│   ├── config.json              # Agent configuration
│   ├── requirements.txt         # Python dependencies
│   └── sessions.example.json    # Credentials template
├── CLAUDE.md                    # Team mode instructions
└── README.md
```

---

## Security

- **Your keys stay local.** Credentials are stored in `sessions.json` on your machine only.
- **`sessions.json` is gitignored.** It will never be committed to the repo.
- **No data sent to us.** All API calls go directly to the AI providers (OpenAI, Google, Perplexity).
- **No middleman.** No proxy server, no third-party relay.
- **Open source.** Audit every line of code yourself.

---

## Roadmap

- [x] Claude Code integration (MCP)
- [x] ChatGPT (Plus/Pro via browser session)
- [x] Gemini (API key via Google AI Studio)
- [x] Perplexity (API + browser cookies)
- [x] Full team pipeline (research -> design -> code -> review)
- [x] CLI interface
- [x] Team mode for Claude Code
- [ ] Grok integration
- [ ] DeepSeek integration
- [ ] Local LLM support (Ollama, LM Studio)
- [ ] Web dashboard
- [ ] VS Code extension
- [ ] Cost tracking per agent
- [ ] Custom agent roles

---

## Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes
4. Push and open a Pull Request

See [CONTRIBUTING.md](ai-team/CONTRIBUTING.md) for details.

### Ideas for Contributions

- New AI provider integrations (Grok, DeepSeek, Mistral, Ollama)
- Better orchestration strategies
- Improved prompts for each agent role
- VS Code / JetBrains extensions
- Web dashboard
- Documentation improvements

---

## License

MIT License. Free to use, modify, and distribute.

---

<p align="center">
<b>Stop asking one AI to do everything.<br>Build an AI engineering team instead.</b>
<br><br>
<a href="https://github.com/needsomehelp/Team-">Star this repo</a> if it saves you time.
<br>
<a href="https://github.com/needsomehelp/Team-/issues">Report a bug</a> · <a href="https://github.com/needsomehelp/Team-/pulls">Submit a PR</a>
</p>
