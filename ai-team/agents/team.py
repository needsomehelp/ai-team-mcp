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

    def get_project_context(self, max_chars: int = 6000) -> str:
        """Gather project context from the working directory."""
        context_parts = []

        try:
            result = subprocess.run(
                ["find", ".", "-maxdepth", "2", "-not", "-path", "*/node_modules/*",
                 "-not", "-path", "*/.git/*", "-not", "-path", "*/__pycache__/*",
                 "-not", "-path", "*/sessions/*"],
                capture_output=True, text=True, cwd=self.project_dir, timeout=5
            )
            if result.stdout:
                context_parts.append(f"PROJECT FILES:\n{result.stdout[:1500]}")
        except Exception:
            pass

        for readme in ["README.md", "readme.md"]:
            path = os.path.join(self.project_dir, readme)
            if os.path.exists(path):
                with open(path, "r") as f:
                    context_parts.append(f"README:\n{f.read()[:1200]}")
                break

        for pkg_file in ["package.json", "requirements.txt", "Cargo.toml", "go.mod", "Makefile"]:
            path = os.path.join(self.project_dir, pkg_file)
            if os.path.exists(path):
                with open(path, "r") as f:
                    context_parts.append(f"{pkg_file}:\n{f.read()[:800]}")

        return "\n\n".join(context_parts)[:max_chars]

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
        """Full team pipeline:
        1. Perplexity researches the topic
        2. ChatGPT designs the architecture
        3. Claude codes the implementation
        4. Gemini reviews the code

        Each step feeds into the next.
        """
        if not context:
            context = self.get_project_context()

        pipeline_results = []

        # Step 1: Research + Architecture in parallel (Perplexity + ChatGPT)
        parallel_results = self.run_parallel({
            "researcher": f"Research best approaches, libraries, and patterns for: {task}",
            "architect": f"Design the architecture and file structure for: {task}",
        }, context)

        pipeline_results.append(("research [Perplexity]", parallel_results.get("researcher")))
        pipeline_results.append(("architecture [ChatGPT]", parallel_results.get("architect")))

        # Build enriched context from step 1
        enriched = context
        for _, result in pipeline_results:
            if result and result.success:
                enriched += f"\n\n--- {result.agent_name} says ---\n{result.content[:3000]}"

        # Step 2: Claude codes the implementation
        code_result = self.run_single("coder", task, enriched)
        pipeline_results.append(("implementation [Claude]", code_result))

        # Step 3: Gemini reviews the code
        if code_result and code_result.success:
            review_context = enriched + f"\n\n--- CODE TO REVIEW ---\n{code_result.content[:4000]}"
            review_result = self.run_single(
                "reviewer",
                f"Review this implementation for bugs, security issues, and improvements: {task}",
                review_context
            )
            pipeline_results.append(("review [Gemini]", review_result))

        return pipeline_results
