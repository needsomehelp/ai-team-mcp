# Changelog

## v0.1.0 — Initial Release

- 4 AI agents: Claude (Coder), ChatGPT (Architect), Gemini (Reviewer), Perplexity (Researcher)
- CLI interface (`aiteam.py`) with team/plan/review/research/code commands
- Shell wrapper (`aiteam.sh`) with start/stop/restart/status
- MCP server for Claude Code integration
- Full pipeline: Research -> Architecture -> Implementation -> Review
- Parallel execution support
- Session-based credential storage (local only)
- Gemini model auto-fallback (tries multiple model versions)
- Global CLI install via symlink
- Global MCP registration (`claude mcp add -s user`)
