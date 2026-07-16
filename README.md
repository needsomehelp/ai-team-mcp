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
Open ChatGPT tab -> copy code -> Open Claude tab -> paste -> Open Gemini -> paste -> Open Perplexity -> search -> manually merge everything
```

**That's not a team. That's chaos.**

## The Solution

```bash
aiteam team "Build a FastAPI auth system with JWT"
# All 4 AIs collaborate automatically. Done.
```

One prompt. Multiple experts. One final solution.

---

## How It Works

Each AI has a specialized role on your team:

| AI | Role | Best For |
|----|------|----------|
| **Claude** | Lead Coder | Implementation, debugging, refactoring |
| **ChatGPT** | Architect | System design, planning, API design |
| **Gemini** | Code Reviewer | Bug detection, security audit, optimization |
| **Perplexity** | Researcher | Latest docs, libraries, best practices |

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

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/needsomehelp/AIteam.git
cd AIteam/ai-team

# Install dependencies
pip install -r requirements.txt
```

### 2. Add to Claude Code (MCP Server)

```bash
claude mcp add ai-team -s user python3 /full/path/to/AIteam/ai-team/mcp_server.py
```

That's it! Now Claude Code can orchestrate your entire AI team.

### 3. Setup API Keys

Each AI uses **your own subscription**. No middleman, no extra costs.

#### ChatGPT (your Plus/Pro subscription)

1. Open [chatgpt.com](https://chatgpt.com) and log in
2. Go to [chatgpt.com/api/auth/session](https://chatgpt.com/api/auth/session)
3. Copy the `accessToken` value from the JSON

```bash
python3 aiteam.py login chatgpt
# Paste your access token when prompted
```

> **Note:** This token expires periodically. Re-login with a fresh token when needed.

#### Gemini (free API key)

1. Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy the key (starts with `AIza...`)

```bash
python3 aiteam.py login gemini
# Paste your API key when prompted
```

> **Free tier:** 500 requests/day for Gemini Flash, 25/day for Pro.

#### Perplexity (API key or browser cookies)

**Option A: API Key (~$0.001 per query)**

1. Go to [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api)
2. Click **"Generate API Key"**
3. Copy the key (starts with `pplx-...`)

```bash
python3 aiteam.py login perplexity
# Paste your API key when prompted
```

**Option B: Browser Cookies (free with Pro subscription)**

1. Open [perplexity.ai](https://perplexity.ai) (logged into Pro)
2. Open DevTools (Cmd+Option+I / F12)
3. Go to **Network** tab, click any request to perplexity.ai
4. Copy the **Cookie** header value

```bash
python3 aiteam.py login perplexity
# Paste the cookie string when prompted
```

#### Claude

Claude uses your existing Claude Code CLI login. No extra setup:

```bash
claude login
```

### 4. Verify Setup

```bash
python3 aiteam.py status
```

You should see all agents as **READY**.

---

## Usage

### CLI Commands

| Command | Description |
|---------|-------------|
| `aiteam team "task"` | Full pipeline: research -> design -> code -> review |
| `aiteam plan "task"` | ChatGPT designs architecture |
| `aiteam review "task"` | Gemini reviews code |
| `aiteam research "task"` | Perplexity researches latest info |
| `aiteam code "task"` | Claude implements |
| `aiteam status` | Check all agent status |
| `aiteam login <service>` | Login to ChatGPT/Gemini/Perplexity |

### Global CLI (optional)

```bash
chmod +x aiteam.sh
ln -s "$(pwd)/aiteam.sh" /usr/local/bin/aiteam

# Now use from anywhere
aiteam status
aiteam team "Build a REST API"
```

### From Claude Code (MCP)

Just talk naturally:

```
> Ask ChatGPT to design the database schema
> Have Gemini review this code for security issues
> Research the latest Next.js changes with Perplexity
> Run the full AI team on building a notification system
```

### Team Mode in Claude Code

Add this to your project's `CLAUDE.md`:

```markdown
When the user says "aiteam start":
- Activate TEAM MODE
- On every response, consult ChatGPT, Gemini, and Perplexity before replying
- Synthesize all responses into one unified answer
```

Then just type `aiteam start` in Claude Code and every response becomes a team effort.

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

---

## Why AI Team?

| Traditional (One AI) | AI Team |
|----------------------|---------|
| One model, one opinion | 4 models, 4 expert perspectives |
| Manual copy-paste between tabs | Automatic orchestration |
| No built-in review | Gemini reviews every output |
| No research step | Perplexity researches first |
| Sequential, slow | Parallel execution |
| You merge everything | Claude synthesizes automatically |

---

## Project Structure

```
AIteam/
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
├── CLAUDE.md
└── README.md
```

---

## MCP Tools Reference

When used as an MCP server in Claude Code, these tools are available:

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

## Security

- **Your keys stay local.** Credentials are stored in `sessions.json` on your machine only.
- **`sessions.json` is gitignored.** Never committed to the repo.
- **No data sent to us.** All API calls go directly to the AI providers (OpenAI, Google, Perplexity).
- **Open source.** Audit the code yourself.

---

## Roadmap

- [x] Claude Code integration
- [x] ChatGPT (Plus/Pro)
- [x] Gemini (API + Advanced)
- [x] Perplexity (API + Pro)
- [x] Full team pipeline
- [x] MCP server
- [x] CLI interface
- [ ] Grok integration
- [ ] DeepSeek integration
- [ ] Local LLM support (Ollama)
- [ ] Web dashboard
- [ ] VS Code extension
- [ ] Cost tracking per agent

---

## Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes
4. Push and open a Pull Request

See [CONTRIBUTING.md](ai-team/CONTRIBUTING.md) for details.

---

## License

MIT License. Free to use, modify, and distribute.

---

<p align="center">
<b>Stop asking one AI to do everything.<br>Build an AI engineering team instead.</b>
<br><br>
If this saves you time, give it a <a href="https://github.com/needsomehelp/AIteam">star</a>!
</p>
