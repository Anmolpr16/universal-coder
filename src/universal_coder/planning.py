from __future__ import annotations
from dataclasses import dataclass
from universal_coder.models import Message

@dataclass
class TaskPlan:
    objective: str
    tasks: list[str]
    rationale: str = ""

class TaskPlanner:
    """Provider-assisted task decomposition with a deterministic fallback."""
    def __init__(self, provider):
        self.provider = provider

    def plan(self, objective: str, context: str = "") -> TaskPlan:
        prompt = (
            "Decompose this coding request into 2-6 concrete implementation tasks. "
            "Return one task per line prefixed exactly with '- '. Do not edit files. "
            "Keep tasks executable and ordered.\n\nObjective:\n" + objective +
            "\n\nRepository context:\n" + context[:20000]
        )
        try:
            response = self.provider.generate([
                Message("system", "You are a senior software architect creating an implementation plan."),
                Message("user", prompt),
            ], [])
            lines = [x[2:].strip() for x in response.message.content.splitlines() if x.strip().startswith("- ")]
            if lines:
                return TaskPlan(objective, lines[:6], "provider")
        except Exception:
            pass
        return TaskPlan(objective, [
            "Inspect the relevant implementation and existing tests",
            "Implement the smallest correct change",
            "Add or update regression tests",
            "Run the project's verification suite and repair failures",
        ], "deterministic fallback")
