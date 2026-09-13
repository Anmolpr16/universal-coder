from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from universal_coder.agent import Agent
from universal_coder.events import EventBus
from universal_coder.worktrees import WorktreeManager, Worktree


@dataclass
class AgentResult:
    role: str
    ok: bool
    output: str
    diff: str
    worktree: Path


class ParallelCoder:
    """Run independent implementation agents in isolated Git worktrees."""

    def __init__(self, provider_factory: Callable[[str], object], max_workers: int = 3, events=None):
        self.provider_factory = provider_factory
        self.max_workers = max_workers
        self.events = events or EventBus()

    def _run_one(self, manager: WorktreeManager, role: str, objective: str) -> AgentResult:
        wt = manager.create(role)
        self.events.emit("parallel.started", role=role, path=str(wt.path))
        try:
            provider = self.provider_factory(role)
            agent = Agent(provider, wt.path, events=self.events)
            output = agent.run(objective, verify=True)
            diff = manager.diff(wt)
            ok = not output.startswith("Agent stopped at")
            self.events.emit("parallel.completed", role=role, ok=ok)
            return AgentResult(role, ok, output, diff, wt.path)
        except Exception as exc:
            self.events.emit("parallel.failed", role=role, error=str(exc))
            return AgentResult(role, False, str(exc), manager.diff(wt), wt.path)

    def run(self, root: str | Path, assignments: dict[str, str]) -> list[AgentResult]:
        if not assignments:
            return []
        with WorktreeManager(root) as manager:
            if not manager.supported():
                raise RuntimeError("parallel coding requires a Git repository with a committed base")
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(self.max_workers, len(assignments))) as pool:
                futures = [pool.submit(self._run_one, manager, role, objective)
                           for role, objective in assignments.items()]
                return [f.result() for f in futures]
