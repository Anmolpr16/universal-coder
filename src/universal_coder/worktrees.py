from __future__ import annotations

import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from universal_coder.git import Git


@dataclass
class Worktree:
    path: Path
    branch: str
    base_ref: str


class WorktreeManager:
    """Create isolated Git worktrees for concurrent coding agents."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.git = Git(self.root)
        self._created: list[Worktree] = []

    def supported(self) -> bool:
        return self.git.available() and bool(self.git.run("rev-parse", "HEAD", check=False)[0])

    def create(self, label: str = "agent") -> Worktree:
        if not self.supported():
            raise RuntimeError("isolated worktrees require a Git repository with at least one commit")
        base = self.git.run("rev-parse", "HEAD")[0]
        branch = f"uc/{label}-{uuid.uuid4().hex[:8]}"
        path = Path(tempfile.mkdtemp(prefix="universal-coder-"))
        # The target directory must not already contain files.
        shutil.rmtree(path)
        self.git.run("worktree", "add", "-b", branch, str(path), base)
        wt = Worktree(path, branch, base)
        self._created.append(wt)
        return wt

    def diff(self, wt: Worktree) -> str:
        # Mark untracked files as intent-to-add so the base-vs-working-tree diff
        # includes newly created source/test files without staging their contents.
        g = Git(wt.path)
        g.run("add", "-N", "--", ".", check=False)
        return g.run("diff", wt.base_ref, check=False)[0]

    def status(self, wt: Worktree) -> str:
        return Git(wt.path).status()

    def remove(self, wt: Worktree, delete_branch: bool = True) -> None:
        subprocess.run(["git", "worktree", "remove", "--force", str(wt.path)], cwd=self.root,
                       text=True, capture_output=True, check=False)
        if delete_branch:
            subprocess.run(["git", "branch", "-D", wt.branch], cwd=self.root,
                           text=True, capture_output=True, check=False)
        try:
            self._created.remove(wt)
        except ValueError:
            pass

    def cleanup(self) -> None:
        for wt in list(self._created):
            self.remove(wt)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.cleanup()
