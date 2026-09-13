from __future__ import annotations
import subprocess
from pathlib import Path

class Git:
    def __init__(self, root: str|Path, timeout=60): self.root=Path(root); self.timeout=timeout
    def run(self, *args, check=True):
        p=subprocess.run(['git',*args],cwd=self.root,text=True,capture_output=True,timeout=self.timeout)
        if check and p.returncode: raise RuntimeError((p.stderr or p.stdout).strip())
        return p.stdout.strip(), p.stderr.strip(), p.returncode
    def available(self): return (self.root/'.git').exists() or self.run('rev-parse','--git-dir',check=False)[2]==0
    def status(self): return self.run('status','--short',check=False)[0]
    def diff(self): return self.run('diff',check=False)[0]
    def branch(self): return self.run('branch','--show-current',check=False)[0]
    def checkpoint(self, label='universal-coder'):
        if not self.available(): return None
        # Commit only if there are changes; never stage automatically without explicit agent permission.
        if not self.status(): return self.run('rev-parse','HEAD',check=False)[0] or None
        self.run('add','-A')
        self.run('commit','-m',label)
        return self.run('rev-parse','HEAD')[0]
    def restore(self, ref):
        if ref: self.run('reset','--hard',ref)
