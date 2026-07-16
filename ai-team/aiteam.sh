#!/bin/bash
# AI Team - Start, Stop & Control all AI MCP agents
# Usage:
#   aiteam start       - Start the MCP server
#   aiteam stop        - Stop the MCP server
#   aiteam status      - Check agent status
#   aiteam restart     - Restart the MCP server
#   aiteam team "task" - Run all 4 agents on a task
#   aiteam plan "task" - Ask ChatGPT (architect)
#   aiteam review "x"  - Ask Gemini (reviewer)
#   aiteam research "x"- Ask Perplexity (researcher)
#   aiteam code "task" - Ask Claude (coder)
#   aiteam login X     - Login to a service

AI_TEAM_DIR="/Users/mac/Downloads/all ai model/ai-team"
PID_FILE="/tmp/ai-team-mcp.pid"
LOG_FILE="/tmp/ai-team-mcp.log"

case "${1}" in
  start)
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "  AI Team MCP is already running (PID: $(cat "$PID_FILE"))"
      echo "  Use: aiteam restart  to restart"
    else
      echo "  Starting AI Team MCP server..."
      cd "$AI_TEAM_DIR"
      python3 mcp_server.py > "$LOG_FILE" 2>&1 &
      echo $! > "$PID_FILE"
      sleep 1
      if kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "  ✅ AI Team MCP started (PID: $(cat "$PID_FILE"))"
        echo "  Log: $LOG_FILE"
        echo ""
        python3 aiteam.py status
      else
        echo "  ❌ Failed to start. Check log: $LOG_FILE"
      fi
    fi
    ;;

  stop)
    if [ -f "$PID_FILE" ]; then
      PID=$(cat "$PID_FILE")
      if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        rm -f "$PID_FILE"
        echo "  ✅ AI Team MCP stopped (PID: $PID)"
      else
        rm -f "$PID_FILE"
        echo "  AI Team MCP was not running (stale PID file cleaned)"
      fi
    else
      # Also kill any running mcp_server.py processes
      PIDS=$(pgrep -f "mcp_server.py" 2>/dev/null)
      if [ -n "$PIDS" ]; then
        echo "$PIDS" | xargs kill 2>/dev/null
        echo "  ✅ AI Team MCP stopped"
      else
        echo "  AI Team MCP is not running"
      fi
    fi
    ;;

  restart)
    "$0" stop
    sleep 1
    "$0" start
    ;;

  status)
    cd "$AI_TEAM_DIR"
    python3 aiteam.py status

    # Also show MCP process status
    echo ""
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "  MCP Server: running (PID: $(cat "$PID_FILE"))"
    else
      PIDS=$(pgrep -f "mcp_server.py" 2>/dev/null)
      if [ -n "$PIDS" ]; then
        echo "  MCP Server: running (PID: $PIDS)"
      else
        echo "  MCP Server: not running as standalone (Claude Code manages it via stdio)"
      fi
    fi
    ;;

  log|logs)
    if [ -f "$LOG_FILE" ]; then
      tail -50 "$LOG_FILE"
    else
      echo "  No log file found"
    fi
    ;;

  team|full|pipeline|all)
    shift
    cd "$AI_TEAM_DIR"
    python3 aiteam.py team "$@"
    ;;

  plan|design|architect|chatgpt)
    shift
    cd "$AI_TEAM_DIR"
    python3 aiteam.py plan "$@"
    ;;

  review|check|audit|gemini)
    shift
    cd "$AI_TEAM_DIR"
    python3 aiteam.py review "$@"
    ;;

  research|search|find|perplexity)
    shift
    cd "$AI_TEAM_DIR"
    python3 aiteam.py research "$@"
    ;;

  code|fix|write|claude)
    shift
    cd "$AI_TEAM_DIR"
    python3 aiteam.py code "$@"
    ;;

  login)
    shift
    cd "$AI_TEAM_DIR"
    python3 aiteam.py login "$@"
    ;;

  logout)
    shift
    cd "$AI_TEAM_DIR"
    python3 aiteam.py logout "$@"
    ;;

  *)
    echo ""
    echo "  ┌─────────────────────────────────────────┐"
    echo "  │         AI TEAM COMMANDS                 │"
    echo "  │   4 AI agents = 1 coding team            │"
    echo "  └─────────────────────────────────────────┘"
    echo ""
    echo "  SERVER:"
    echo "    aiteam start           Start MCP server"
    echo "    aiteam stop            Stop MCP server"
    echo "    aiteam restart         Restart MCP server"
    echo "    aiteam status          Check all agents"
    echo "    aiteam logs            View server logs"
    echo ""
    echo "  AGENTS:"
    echo "    aiteam team \"task\"     Run ALL 4 agents"
    echo "    aiteam plan \"task\"     ChatGPT (architect)"
    echo "    aiteam review \"task\"   Gemini (reviewer)"
    echo "    aiteam research \"q\"    Perplexity (researcher)"
    echo "    aiteam code \"task\"     Claude (coder)"
    echo ""
    echo "  AUTH:"
    echo "    aiteam login chatgpt   Login to ChatGPT"
    echo "    aiteam login gemini    Login to Gemini"
    echo "    aiteam login perplexity Login to Perplexity"
    echo "    aiteam logout SERVICE  Logout from a service"
    echo ""
    ;;
esac
