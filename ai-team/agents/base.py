"""Base agent class for all AI team members."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AgentResult:
    agent_name: str
    role: str
    content: str
    success: bool
    error: str = ""


class BaseAgent(ABC):
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role

    @abstractmethod
    def execute(self, prompt: str, context: str = "") -> AgentResult:
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        pass

    def build_prompt(self, task: str, context: str, role_instruction: str) -> str:
        parts = [
            f"You are the {self.role} on a software team.",
            role_instruction,
            "FORMAT: bullet points only, max 200 words, no preamble, no filler.",
        ]
        if context:
            # Cap context at 800 chars — just enough for agents to understand the project
            parts.append(f"\n--- PROJECT ---\n{context[:800]}\n---")
        parts.append(f"\n--- TASK ---\n{task}")
        return "\n".join(parts)
