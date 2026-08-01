#!/usr/bin/env python3
"""
AI Team REST API

Exposes the same AI Team tools that mcp_server.py exposes over MCP/stdio
(Claude Code only, one machine), but as plain HTTP/JSON endpoints so they
can be called from anywhere: your Android app, n8n, curl, a browser, etc.

Run:
    python3 api_server.py
    (or)  api_server.cmd            [Windows]

On first run it generates an API key and writes it to .env as AITEAM_API_KEY.
Every request (except /health) must send it back as the "X-API-Key" header.

Config (env vars, can go in .env):
    AITEAM_API_KEY       shared secret required on every request (auto-generated if unset)
    AITEAM_API_HOST       bind address (default 0.0.0.0 - reachable from your LAN)
    AITEAM_API_PORT       port (default 8642)
    AITEAM_CORS_ORIGINS   comma-separated allowed origins (default "*")

Note: generate_video / generate_audio are not exposed here — in mcp_server.py
they only return instructions telling Claude Code to call the Higgsfield MCP
tool itself, which doesn't exist outside a Claude Code session.
"""

import os
import secrets
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv, set_key

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if not os.path.exists(ENV_PATH):
    open(ENV_PATH, "a").close()
load_dotenv(ENV_PATH)

API_KEY = os.environ.get("AITEAM_API_KEY")
if not API_KEY:
    API_KEY = secrets.token_urlsafe(32)
    set_key(ENV_PATH, "AITEAM_API_KEY", API_KEY)
    print(f"[api_server] Generated API key and saved it to {ENV_PATH}")
    print(f"[api_server] AITEAM_API_KEY={API_KEY}")

HOST = os.environ.get("AITEAM_API_HOST", "0.0.0.0")
PORT = int(os.environ.get("AITEAM_API_PORT", "8642"))
CORS_ORIGINS = [o.strip() for o in os.environ.get("AITEAM_CORS_ORIGINS", "*").split(",")]

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Reuse the exact same tool functions the MCP server exposes — @mcp.tool()
# returns the original function unchanged, so this is not a reimplementation.
import mcp_server as tools

app = FastAPI(
    title="AI Team API",
    description="HTTP wrapper around the AI Team MCP tools (ChatGPT/Gemini/Perplexity/image gen).",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    if not x_api_key or not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key header")


class AskRequest(BaseModel):
    task: str
    context: str = ""
    files: Optional[list] = None


class LoginRequest(BaseModel):
    service: str
    token: str
    token2: str = ""


class ChatRequest(BaseModel):
    task: str
    context: str = ""


class ImageRequest(BaseModel):
    prompt: str
    width: int = 1024
    height: int = 1024
    model: str = "flux"


class DalleRequest(BaseModel):
    prompt: str
    size: str = "1024x1024"
    quality: str = "standard"


@app.get("/health")
def health():
    """Unauthenticated reachability check."""
    return {"status": "ok"}


@app.get("/status", dependencies=[Depends(require_api_key)])
def status():
    return {"result": tools.ai_team_status()}


@app.post("/login", dependencies=[Depends(require_api_key)])
def login(req: LoginRequest):
    return {"result": tools.ai_team_login(req.service, req.token, req.token2)}


@app.post("/ask/chatgpt", dependencies=[Depends(require_api_key)])
def ask_chatgpt(req: AskRequest):
    return {"result": tools.ask_chatgpt(req.task, req.context, req.files)}


@app.post("/ask/gemini", dependencies=[Depends(require_api_key)])
def ask_gemini(req: AskRequest):
    return {"result": tools.ask_gemini(req.task, req.context, req.files)}


@app.post("/ask/perplexity", dependencies=[Depends(require_api_key)])
def ask_perplexity(req: AskRequest):
    return {"result": tools.ask_perplexity(req.task, req.context, req.files)}


@app.post("/team/run", dependencies=[Depends(require_api_key)])
def team_run(req: AskRequest):
    return {"result": tools.ai_team_run(req.task, req.context, req.files)}


@app.post("/chat", dependencies=[Depends(require_api_key)])
def chat(req: ChatRequest):
    return {"result": tools.ai_team_chat(req.task, req.context)}


@app.post("/image/generate", dependencies=[Depends(require_api_key)])
def image_generate(req: ImageRequest):
    return {"result": tools.generate_image(req.prompt, req.width, req.height, req.model)}


@app.post("/image/dalle", dependencies=[Depends(require_api_key)])
def image_dalle(req: DalleRequest):
    return {"result": tools.generate_image_dalle(req.prompt, req.size, req.quality)}


if __name__ == "__main__":
    import uvicorn

    print(f"[api_server] Listening on http://{HOST}:{PORT}  (Ctrl+C to stop)")
    if HOST == "0.0.0.0":
        print("[api_server] Reachable on your LAN at http://<this-machine's-IP>:%d" % PORT)
    uvicorn.run(app, host=HOST, port=PORT)
