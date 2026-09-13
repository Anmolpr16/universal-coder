from dataclasses import dataclass

@dataclass
class PermissionPolicy:
    allow_write: bool=True
    allow_delete: bool=False
    allow_command: bool=True
    allow_network: bool=False
    require_approval_for_delete: bool=True
    require_approval_for_command: bool=False

class PermissionManager:
    def __init__(self, policy=None, approval=None): self.policy=policy or PermissionPolicy(); self.approval=approval or (lambda action: False)
    def check(self, action, detail=''):
        p=self.policy
        if action=='write': return p.allow_write
        if action=='delete': return p.allow_delete and (not p.require_approval_for_delete or self.approval(f'{action}:{detail}'))
        if action=='command': return p.allow_command and (not p.require_approval_for_command or self.approval(f'{action}:{detail}'))
        if action=='network': return p.allow_network
        return False
