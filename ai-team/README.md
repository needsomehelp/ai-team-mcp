# AI Team MCP

**Your AI engineering team in the terminal.**

Turn your AI subscriptions (Claude, ChatGPT, Gemini, Perplexity) into one coordinated coding team. One command. Four AI experts. Zero tab-switching.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)]()
[![MCP](https://img.shields.io/badge/MCP-Compatible-orange.svg)]()
[![Open Source](https://img.shields.io/badge/Open%20Source-free-red.svg)]()

---

## The Problem

You're building software and you have subscriptions to multiple AI models. But using them means:

```
Open ChatGPT tab → copy code → Open Claude tab → paste → Open Gemini → paste → Open Perplexity → search → manually merge everything
```

## The Solution

```bash
aiteam team "Build a FastAPI auth system with JWT"
# All 4 AIs collaborate automatically. Done.
```

---

## How It Works

Each AI has a specialized role on your team:

| AI | Role | Best For |
|----|------|----------|
| Claude | Lead Coder | Implementation, debugging, refactoring |
| ChatGPT | Architect | System design, planning, API design |
| Gemini | Code Reviewer | Bug detection, security audit, optimization |
| Perplexity | Researcher | Latest docs, libraries, best practices |

### Pipeline

```
Perplexity (Research)
    |
    v
ChatGPT (Architecture)
    |
    v
Claude (Implementation)
    |
    v
Gemini (Code Review)
    |
    v
Final Result
```

### Architecture

```
                    You (Terminal / Claude Code)
                              |
                       AI Team MCP Server
                              |
          +----------+--------+--------+-----------+
          |          |                 |            |
       Claude    ChatGPT           Gemini     Perplexity
       (Coder)   (Architect)      (Reviewer)  (Researcher)
          |          |                 |            |
          +----------+--------+--------+-----------+
                              |
                       Combined Result
```

---

## Installation

```bash
# Clone the repo
git clone https://github.com/AjmalBuilds/ai-team-mcp.git
cd ai-team-mcp

# Install dependencies
pip install -r requirements.txt

# Check status
python3 aiteam.py status
```

### Global CLI (optional)

```bash
chmod +x aiteam.sh
ln -s "$(pwd)/aiteam.sh" /usr/local/bin/aiteam

# Now use from anywhere
aiteam status
```

### MCP Server (for Claude Code)

```bash
claude mcp add ai-team -s user python3 /path/to/ai-team-mcp/mcp_server.py
```

Once registered, just tell Claude Code things like:
- "Ask ChatGPT to design the database schema"
- "Have Gemini review this code"
- "Research the latest Next.js changes with Perplexity"
- "Run the full AI team on this feature"

---

## Setup Your API Keys

Each AI uses **your own subscription**. No middleman, no extra costs.

### ChatGPT (your Plus/Pro subscription)

You can login with either an **access token** or **browser cookies** — try the access token first, fall back to cookies if blocked.

**Option A: Access Token (quickest)**

1. Open [chatgpt.com](https://chatgpt.com) and make sure you're logged in
2. Go to [chatgpt.com/api/auth/session](https://chatgpt.com/api/auth/session)
3. Copy the `accessToken` value from the JSON

```bash
python3 aiteam.py login chatgpt
# Paste your access token when prompted
```

**Option B: Browser Cookies (more stable, beats Cloudflare blocks)**

1. Open [chatgpt.com](https://chatgpt.com) in your browser (logged in)
2. Open DevTools (Cmd+Option+I on Mac, F12 on Windows)
3. Go to **Network** tab → click any request to chatgpt.com
4. Find the **Cookie** header in Request Headers
5. Copy the entire cookie string

```bash
python3 aiteam.py login chatgpt
# Paste the cookie string when prompted
```

> **Note:** Tokens and cookies expire periodically. If ChatGPT stops working, re-login with a fresh token/cookie.
> **Moving to a new computer?** Sessions are tied to your browser — re-run the login steps on each machine. Do NOT copy `sessions.json` across machines; get fresh credentials instead.

### Gemini (free API key)

1. Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy the key (starts with `AIza...`)

```bash
python3 aiteam.py login gemini
# Paste your API key when prompted
```

> **Free tier:** 500 requests/day for Gemini Flash, 25/day for Pro. Same models as Gemini Advanced.

### Perplexity (API key or browser cookies)

**Option A: API Key (easiest, ~$0.001 per query)**

1. Go to [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api)
2. Click **"Generate API Key"**
3. Copy the key (starts with `pplx-...`)

```bash
python3 aiteam.py login perplexity
# Paste your API key when prompted
```

**Option B: Browser Cookies (free with Pro subscription)**

1. Open [perplexity.ai](https://perplexity.ai) in your browser (logged into Pro)
2. Open DevTools (Cmd+Option+I on Mac, F12 on Windows)
3. Go to **Network** tab
4. Click any request to perplexity.ai
5. Find the **Cookie** header in Request Headers
6. Copy the entire cookie string

```bash
python3 aiteam.py login perplexity
# Paste the cookie string when prompted
```

### Claude

Claude uses your existing Claude Code CLI login. No extra setup needed.

```bash
# If not logged in yet:
claude login
```

---

## CLI Commands

### Server Control

| Command | Description |
|---------|-------------|
| `aiteam start` | Start the MCP server |
| `aiteam stop` | Stop the MCP server |
| `aiteam restart` | Restart the server |
| `aiteam status` | Check all agent status |
| `aiteam logs` | View server logs |

### Run Agents

| Command | Agent | Description |
|---------|-------|-------------|
| `aiteam team "task"` | All 4 | Full pipeline (research → design → code → review) |
| `aiteam plan "task"` | ChatGPT | Architecture and system design |
| `aiteam review "task"` | Gemini | Code review, bugs, security |
| `aiteam research "task"` | Perplexity | Latest docs, libraries, best practices |
| `aiteam code "task"` | Claude | Implementation and coding |

### Auth

| Command | Description |
|---------|-------------|
| `aiteam login chatgpt` | Login to ChatGPT |
| `aiteam login gemini` | Login to Gemini |
| `aiteam login perplexity` | Login to Perplexity |
| `aiteam logout SERVICE` | Logout from a service |

---

## Examples

### Full Team Pipeline

```bash
aiteam team "Build a REST API with authentication using FastAPI"
```

This runs:
1. **Perplexity** researches latest FastAPI auth patterns
2. **ChatGPT** designs the architecture and file structure
3. **Claude** implements the code
4. **Gemini** reviews for bugs, security issues, and improvements

### Individual Agents

```bash
# Research latest technologies
aiteam research "Best Python web frameworks 2025"

# Design a system
aiteam plan "Microservice architecture for an e-commerce platform"

# Review code
aiteam review "Check my auth middleware for security vulnerabilities"

# Write code
aiteam code "Implement WebSocket real-time notifications"
```

### From Claude Code (MCP)

Just talk naturally:

```
> Ask Perplexity about the latest Stripe API changes
> Have ChatGPT design a caching layer for our API
> Get Gemini to review the trading bot code
> Run the full team on building a notification system
```

---

## MCP Tools

When used as an MCP server, these tools are available:

| Tool | Description |
|------|-------------|
| `ai_team_status` | Check which agents are ready |
| `ai_team_login` | Save login credentials for a service |
| `ask_chatgpt` | Send a task to ChatGPT |
| `ask_gemini` | Send a task to Gemini |
| `ask_perplexity` | Send a task to Perplexity |
| `ai_team_run` | Run the full 4-agent pipeline |
| `ai_team_chat` | Collaborate with ChatGPT as a team |

---

## Project Structure

```
ai-team-mcp/
├── agents/
│   ├── base.py              # Base agent class
│   ├── claude_agent.py       # Claude Code integration
│   ├── chatgpt_agent.py      # ChatGPT API agent
│   ├── gemini_agent.py       # Gemini API agent
│   ├── perplexity_agent.py   # Perplexity agent
│   ├── session_store.py      # Secure credential storage
│   └── team.py               # Team coordinator & pipeline
├── mcp_server.py             # MCP server for Claude Code
├── aiteam.py                 # CLI interface
├── aiteam.sh                 # Global shell command
├── config.json               # Agent configuration
├── sessions.example.json     # Example credentials template
├── requirements.txt          # Python dependencies
└── README.md
```

---

## Security

- **Your keys stay local.** Credentials are stored in `sessions.json` on your machine only.
- **`sessions.json` is gitignored.** It will never be committed to the repo.
- **No data is sent to us.** All API calls go directly to the AI providers (OpenAI, Google, Perplexity).
- **Open source.** Audit the code yourself.

---

## Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Ideas for contributions

- Additional AI providers (Mistral, Llama, etc.)
- Better orchestration strategies
- Improved prompts for each role
- VS Code / JetBrains extensions
- Web dashboard
- Cost tracking per agent

---

## License

MIT License. Free to use, modify, and distribute.

---

<p align="center">
<b>One Team. Four AIs. Better Software.</b>
<br><br>
If you find this useful, give it a star!
</p>
