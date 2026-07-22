"""Secure local storage for browser session tokens."""

import json
import os

SESSIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sessions.json")


def load_sessions() -> dict:
    """Load saved tokens. Returns {} if the file is missing, empty, or corrupt so a
    single bad write can't crash every tool that touches sessions."""
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError, OSError):
            return {}
    return {}


def _write_sessions(sessions: dict):
    """Write atomically (temp file + os.replace) so a crash mid-write can't corrupt
    the only copy of every token."""
    tmp = SESSIONS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(sessions, f, indent=2)
    os.replace(tmp, SESSIONS_FILE)


def save_session(service: str, token_data: dict):
    sessions = load_sessions()
    sessions[service] = token_data
    _write_sessions(sessions)


def get_session(service: str) -> dict:
    sessions = load_sessions()
    return sessions.get(service, {})


def remove_session(service: str):
    sessions = load_sessions()
    sessions.pop(service, None)
    _write_sessions(sessions)


def list_sessions() -> dict:
    return load_sessions()
