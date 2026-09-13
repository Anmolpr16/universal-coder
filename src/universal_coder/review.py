from __future__ import annotations
from universal_coder.models import Message

class Reviewer:
    def __init__(self, provider): self.provider=provider
    def review(self, objective, diff, tools=None):
        prompt=("Review this software change independently. Return PASS if correct, otherwise list concrete defects and required fixes. "
                "Do not edit files.\nObjective:\n"+objective+"\nDiff:\n"+diff[:50000])
        r=self.provider.generate([Message('system','You are an independent senior code reviewer.'),Message('user',prompt)],tools or [])
        return r.message.content
