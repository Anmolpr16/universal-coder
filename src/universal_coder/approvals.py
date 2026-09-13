from __future__ import annotations
from dataclasses import dataclass

@dataclass
class ApprovalPolicy:
    interactive: bool=False
    allow_commands: bool=True
    allow_writes: bool=True
    allow_deletes: bool=False
    def check(self, action, target):
        if action=='delete' and not self.allow_deletes:return False
        if action=='command' and not self.allow_commands:return False
        if action=='write' and not self.allow_writes:return False
        if not self.interactive:return True
        answer=input(f'[approval] allow {action}: {target}? [y/N] ').strip().lower()
        return answer in {'y','yes'}
