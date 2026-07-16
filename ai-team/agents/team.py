"""Multi-agent team coordinator.
Uses REAL different AI services - each with your subscription:
  - Claude Code CLI  = Lead Coder
  - ChatGPT Plus     = Architect
  - Gemini Advanced  = Code Reviewer
  - Perplexity Pro   = Researcher
"""

import os
import subprocess
import concurrent.futures
from .claude_agent import ClaudeAgent
from .chatgpt_agent import ChatGPTWebAgent
from .gemini_agent import GeminiWebAgent
from .perplexity_agent import PerplexityWebAgent
from .base import AgentResult


class AgentTeam:
    """Coordinates 4 different AI services working on a single task."""

    def __init__(self, project_dir: str = "."):
        self.project_dir = os.path.abspath(project_dir)
        self.agents = {
            "coder": ClaudeAgent(),
            "architect": ChatGPTWebAgent(),
            "reviewer": GeminiWebAgent(),
            "researcher": PerplexityWebAgent(),
        }

    def get_agent_status(self) -> dict:
        """Check which agents are logged in and ready."""
        return {name: agent.is_ready() for name, agent in self.agents.items()}

    def get_project_context(self, max_chars: int = 1500) -> str:
        """Gather minimal project context — just enough for agents to orient themselves."""
        context_parts = []

        try:
            result = subprocess.run(
                ["find", ".", "-maxdepth", "2", "-not", "-path", "*/node_modules/*",
                 "-not", "-path", "*/.git/*", "-not", "-path", "*/__pycache__/*",
                 "-not", "-path", "*/sessions/*"],
                capture_output=True, text=True, cwd=self.project_dir, timeout=5
            )
            if result.stdout:
                context_parts.append(f"FILES:\n{result.stdout[:600]}")
        except Exception:
            pass

        for pkg_file in ["requirements.txt", "package.json", "go.mod"]:
            path = os.path.join(self.project_dir, pkg_file)
            if os.path.exists(path):
                with open(path, "r") as f:
                    context_parts.append(f"{pkg_file}:\n{f.read()[:400]}")
                break

        return "\n\n".join(context_parts)[:max_chars]

    @staticmethod
    def route_task(task: str) -> list:
        """Return only the agent roles needed for this task — avoids calling all 4 for simple tasks."""
        task_lower = task.lower()

        # Research only
        if any(w in task_lower for w in ["research", "find", "latest", "what is", "docs", "library", "compare", "best practice"]):
            return ["researcher"]

        # Architecture/design only
        if any(w in task_lower for w in ["design", "architect", "structure", "plan", "schema", "database", "system"]):
            return ["architect"]

        # Code review only
        if any(w in task_lower for w in ["review", "security", "bug", "audit", "check", "vulnerability"]):
            return ["reviewer"]

        # Simple fix/edit — just coder, maybe reviewer
        if any(w in task_lower for w in ["fix", "refactor", "rename", "move", "delete", "update", "change"]):
            return ["coder", "reviewer"]

        # Full pipeline for build/implement tasks
        return ["researcher", "architect", "coder", "reviewer"]

    def run_single(self, role: str, task: str, context: str = "") -> AgentResult:
        """Run a single agent on a task."""
        agent = self.agents.get(role)
        if not agent:
            return AgentResult(f"Unknown-{role}", role, "", False, f"No agent for role: {role}")
        if not agent.is_ready():
            return AgentResult(agent.name, role, "", False,
                             f"{agent.name} not logged in. Run: python3 aiteam.py login {self._service_name(role)}")
        if not context:
            context = self.get_project_context()
        return agent.execute(task, context)

    def _service_name(self, role: str) -> str:
        return {"coder": "claude", "architect": "chatgpt", "reviewer": "gemini", "researcher": "perplexity"}.get(role, role)

    def run_parallel(self, tasks: dict, context: str = "") -> dict:
        """Run multiple agents in parallel."""
        if not context:
            context = self.get_project_context()

        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}
            for role, task in tasks.items():
                agent = self.agents.get(role)
                if agent and agent.is_ready():
                    futures[executor.submit(agent.execute, task, context)] = role
                elif agent:
                    results[role] = AgentResult(agent.name, role, "", False,
                                              f"{agent.name} not logged in. Run: python3 aiteam.py login {self._service_name(role)}")

            for future in concurrent.futures.as_completed(futures):
                role = futures[future]
                try:
                    results[role] = future.result()
                except Exception as e:
                    results[role] = AgentResult(f"Agent-{role}", role, "", False, str(e))

        return results

    def run_pipeline(self, task: str, context: str = "") -> list:
        """Smart pipeline — routes to only the agents needed, passes compressed summaries between steps."""
        if not context:
            context = self.get_project_context()

        roles = self.route_task(task)
        pipeline_results = []

        # Step 1: Research + Architecture in parallel (only if routed)
        parallel_tasks = {}
        if "researcher" in roles:
            parallel_tasks["researcher"] = f"Key facts, libraries, patterns for: {task}. Bullets only."
        if "architect" in roles:
            parallel_tasks["architect"] = f"File structure and interfaces for: {task}. Bullets only."

        if parallel_tasks:
            parallel_results = self.run_parallel(parallel_tasks, context)
            for role, label in [("researcher", "research [Perplexity]"), ("architect", "architecture [ChatGPT]")]:
                if role in parallel_tasks:
                    pipeline_results.append((label, parallel_results.get(role)))

        # Build enriched context — cap each agent's contribution at 800 chars to save tokens
        enriched = context
        for _, result in pipeline_results:
            if result and result.success:
                enriched += f"\n\n[{result.agent_name}]: {result.content[:800]}"

        # Step 2: Claude codes (only if routed)
        code_result = None
        if "coder" in roles:
            code_result = self.run_single("coder", task, enriched)
            pipeline_results.append(("implementation [Claude]", code_result))

        # Step 3: Gemini reviews (only if routed + code exists)
        if "reviewer" in roles and code_result and code_result.success:
            # Only send the code, not the full enriched context — Gemini only needs to review
            review_result = self.run_single(
                "reviewer",
                f"Review for bugs and security issues:\n{code_result.content[:2000]}",
                "",
            )
            pipeline_results.append(("review [Gemini]", review_result))
        elif "reviewer" in roles and not code_result:
            # Review-only task (no coder step)
            review_result = self.run_single("reviewer", task, context)
            pipeline_results.append(("review [Gemini]", review_result))

        return pipeline_results
