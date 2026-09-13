from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from universal_coder.worktrees import WorktreeManager


@dataclass
class IntegrationResult:
    ok: bool
    applied_role: str | None
    message: str


class Integrator:
    """Safely apply one selected agent patch to the main workspace."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()

    def apply_diff(self, diff: str, role: str = "agent") -> IntegrationResult:
        if not diff.strip():
            return IntegrationResult(False, None, "selected agent produced no diff")
        check = subprocess.run(["git", "apply", "--check", "--3way", "-"], cwd=self.root,
                               input=diff, text=True, capture_output=True)
        if check.returncode:
            return IntegrationResult(False, None, (check.stderr or check.stdout).strip())
        proc = subprocess.run(["git", "apply", "--3way", "-"], cwd=self.root,
                              input=diff, text=True, capture_output=True)
        if proc.returncode:
            return IntegrationResult(False, None, (proc.stderr or proc.stdout).strip())
        return IntegrationResult(True, role, "patch applied")
