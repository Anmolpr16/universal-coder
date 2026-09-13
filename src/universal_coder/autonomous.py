from __future__ import annotations
import concurrent.futures
from dataclasses import dataclass
from pathlib import Path
from universal_coder.agent import Agent
from universal_coder.events import EventBus
from universal_coder.integration import Integrator
from universal_coder.parallel import ParallelCoder, AgentResult
from universal_coder.persistence import RunStore
from universal_coder.planning import TaskPlanner, TaskPlan
from universal_coder.review import Reviewer
from universal_coder.router import ModelRouter
from universal_coder.team import TeamRunner
from universal_coder.verification import Verifier
from universal_coder.workspace import Workspace

@dataclass
class CandidateScore:
    role: str
    score: int
    rationale: str

@dataclass
class AutonomousResult:
    ok: bool
    output: str
    plan: TaskPlan
    candidates: list[AgentResult]
    selected_role: str | None
    review: str = ""

class AutonomousPipeline:
    """End-to-end coordinator: plan -> consult -> parallel implement -> arbitrate -> repair -> verify."""
    def __init__(self, provider_factory, root: str | Path, max_steps=40, command_timeout=120, events=None, store=None):
        self.provider_factory = provider_factory
        self.root = Path(root).resolve()
        self.max_steps = max_steps
        self.command_timeout = command_timeout
        self.events = events or EventBus()
        self.store = store or RunStore(self.root / ".universal-coder" / "runs.json")

    def _provider(self, role="coder"):
        return self.provider_factory(role)

    def _arbitrate(self, objective, results: list[AgentResult]) -> tuple[str | None, list[CandidateScore]]:
        if not results:
            return None, []
        reviewer = Reviewer(self._provider("reviewer"))
        def score(r):
            text = reviewer.review(objective, r.diff)
            import re
            match = re.search(r"SCORE\s*:\s*(\d{1,3})", text, re.I)
            value = max(0, min(100, int(match.group(1)))) if match else (70 if r.ok and r.diff.strip() else 0)
            return CandidateScore(r.role, value, text)
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(3, len(results))) as pool:
            scores = list(pool.map(score, results))
        scores.sort(key=lambda x: x.score, reverse=True)
        return scores[0].role if scores else None, scores

    def run(self, objective: str, verify=True, max_repair_cycles=2) -> AutonomousResult:
        ws = Workspace(self.root)
        context = "\n".join(ws.tree())
        self.events.emit("pipeline.started", objective=objective)
        plan = TaskPlanner(self._provider("architect")).plan(objective, context)
        self.events.emit("pipeline.planned", tasks=plan.tasks)

        opinions = TeamRunner({r: self._provider(r) for r in ("architect", "tester", "reviewer")}).consult(objective, context)
        synthesis = TeamRunner.synthesize(opinions)
        implementation_objective = objective + "\n\nIMPLEMENTATION PLAN:\n- " + "\n- ".join(plan.tasks)
        if synthesis:
            implementation_objective += "\n\nADVISORY TEAM FINDINGS:\n" + synthesis[:30000]

        assignments = {
            "coder": implementation_objective + "\nImplement the complete change and tests.",
            "tester": implementation_objective + "\nPrioritize regression tests and verification while implementing the change.",
            "reviewer": implementation_objective + "\nImplement defensively, prioritizing correctness, security, and integration risks.",
        }
        candidates: list[AgentResult] = []
        try:
            candidates = ParallelCoder(self.provider_factory, max_workers=3, events=self.events).run(self.root, assignments)
        except RuntimeError:
            self.events.emit("pipeline.parallel_unavailable")

        selected_role = None
        review_text = ""
        if candidates:
            selected_role, scores = self._arbitrate(objective, candidates)
            self.events.emit("pipeline.arbitrated", selected_role=selected_role,
                             scores=[{"role": s.role, "score": s.score} for s in scores])
            selected = next((r for r in candidates if r.role == selected_role), None)
            if selected and selected.diff:
                integration = Integrator(self.root).apply_diff(selected.diff, selected.role)
                if not integration.ok:
                    self.events.emit("pipeline.integration_failed", error=integration.message)
                    selected_role = None
                else:
                    self.events.emit("pipeline.integrated", role=selected.role)

        # If parallel execution is unavailable, the primary coder is the explicit safe fallback.
        if selected_role is None:
            selected_role = "coder"
            self.events.emit("pipeline.fallback", role=selected_role)

        # Always finish in the real workspace with the primary agent. This repairs integration
        # issues, fills gaps, and performs final verification instead of trusting a candidate.
        agent = Agent(self._provider("coder"), self.root, self.max_steps, self.command_timeout,
                      events=self.events, store=self.store, reviewer=Reviewer(self._provider("reviewer")))
        final_objective = implementation_objective
        if selected_role:
            final_objective += f"\nA parallel candidate ({selected_role}) was integrated. Inspect its changes, repair any defects, and finish the objective."
        else:
            final_objective += "\nNo parallel implementation was safely integrated. Implement the objective directly."
        output = agent.run(final_objective, verify=verify, review=False)
        ok = not output.startswith("Agent stopped at")
        if verify:
            report = Verifier(ws, self.command_timeout).run()
            ok = ok and (not report.checks or report.ok)
            if report.checks:
                review_text = report.summary()
        self.events.emit("pipeline.completed", ok=ok, selected_role=selected_role)
        return AutonomousResult(ok, output, plan, candidates, selected_role, review_text)
