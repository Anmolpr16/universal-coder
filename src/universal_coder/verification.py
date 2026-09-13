from dataclasses import dataclass, field
import subprocess
from universal_coder.workspace import Workspace

@dataclass
class Check:
    name: str
    command: str
    ok: bool = False
    output: str = ''

@dataclass
class VerificationReport:
    checks: list[Check] = field(default_factory=list)
    @property
    def ok(self): return bool(self.checks) and all(c.ok for c in self.checks)
    def summary(self):
        return '\n'.join(f"{'PASS' if c.ok else 'FAIL'} {c.name}: {c.output[-2000:]}" for c in self.checks)

class Verifier:
    def __init__(self, ws: Workspace, timeout=120): self.ws=ws; self.timeout=timeout
    def detect(self):
        checks=[]
        if (self.ws.root/'pyproject.toml').exists() or (self.ws.root/'pytest.ini').exists(): checks.append(Check('pytest','python -m pytest -q'))
        elif (self.ws.root/'package.json').exists(): checks.append(Check('npm test','npm test -- --runInBand'))
        elif (self.ws.root/'Cargo.toml').exists(): checks.append(Check('cargo test','cargo test'))
        elif (self.ws.root/'go.mod').exists(): checks.append(Check('go test','go test ./...'))
        return checks
    def run(self, commands=None):
        checks=self.detect() if commands is None else [Check(f'check-{i+1}',c) for i,c in enumerate(commands)]
        if not checks: return VerificationReport([])
        for c in checks:
            try:
                p=subprocess.run(c.command,shell=True,cwd=self.ws.root,text=True,capture_output=True,timeout=self.timeout)
                c.ok=p.returncode==0; c.output=(p.stdout+p.stderr)[-12000:]
            except Exception as e: c.output=f'{type(e).__name__}: {e}'
        return VerificationReport(checks)
