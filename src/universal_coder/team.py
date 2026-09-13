from __future__ import annotations
import concurrent.futures
from dataclasses import dataclass
from universal_coder.models import Message

@dataclass
class AgentOpinion:
    role: str
    content: str
    provider: str

class TeamRunner:
    """Lightweight multi-agent coordinator: parallel specialists produce independent plans/reviews."""
    def __init__(self, providers: dict[str, object], max_workers: int = 3):
        self.providers = providers
        self.max_workers = max_workers

    def _ask(self, role: str, provider, objective: str, context: str) -> AgentOpinion:
        prompts = {
            "architect": "Analyze the repository and design the smallest robust implementation plan. Do not edit files.",
            "tester": "Analyze the objective from a testing/verification perspective. Identify edge cases and exact tests to run. Do not edit files.",
            "reviewer": "Analyze likely failure modes, security issues, regressions, and integration concerns. Do not edit files.",
        }
        system = f"You are the {role} specialist on a software engineering team. {prompts[role]}"
        user = f"Objective:\n{objective}\n\nRepository context:\n{context[:30000]}"
        response = provider.generate([Message('system', system), Message('user', user)], [])
        return AgentOpinion(role, response.message.content or '', getattr(provider, 'name', role))

    def consult(self, objective: str, context: str, roles=None) -> list[AgentOpinion]:
        roles = roles or ["architect", "tester", "reviewer"]
        items = [(r, self.providers[r]) for r in roles if r in self.providers]
        if not items:
            return []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(self.max_workers, len(items))) as pool:
            futures = [pool.submit(self._ask, r, p, objective, context) for r, p in items]
            return [f.result() for f in futures]

    @staticmethod
    def synthesize(opinions: list[AgentOpinion]) -> str:
        if not opinions:
            return ''
        chunks = []
        for o in opinions:
            chunks.append(f"[{o.role} / {o.provider}]\n{o.content}")
        return "\n\n".join(chunks)
