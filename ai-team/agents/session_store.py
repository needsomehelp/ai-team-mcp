"""Secure local storage for browser session tokens."""

import json
import os

SESSIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sessions.json")


def load_sessions() -> dict:
    if os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_session(service: str, token_data: dict):
    sessions = load_sessions()
    sessions[service] = token_data
    with open(SESSIONS_FILE, "w") as f:
        json.dump(sessions, f, indent=2)


def get_session(service: str) -> dict:
    sessions = load_sessions()
    return sessions.get(service, {})


def remove_session(service: str):
    sessions = load_sessions()
    sessions.pop(service, None)
    with open(SESSIONS_FILE, "w") as f:
        json.dump(sessions, f, indent=2)


def list_sessions() -> dict:
    return load_sessions()
