from pathlib import Path
import os

IGNORED = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules", ".gradle", "build", "dist", ".universal-coder", ".tox", ".mypy_cache", ".ruff_cache"}

class Workspace:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, relative: str) -> Path:
        if not relative or "\x00" in relative:
            raise ValueError("invalid path")
        candidate = self.root / relative
        # Reject symlink traversal explicitly. resolve()-only checks are insufficient
        # for write/delete operations when an attacker can replace a component.
        current = self.root
        for part in Path(relative).parts:
            if part in ("", "."):
                continue
            if part == "..":
                raise PermissionError("path escapes workspace")
            current = current / part
            if current.is_symlink():
                raise PermissionError("symlink traversal is not allowed")
        p = candidate.resolve()
        if p != self.root and self.root not in p.parents:
            raise PermissionError("path escapes workspace")
        return p

    def read(self, relative: str, max_bytes: int = 200_000) -> str:
        p = self.path(relative)
        data = p.read_bytes()
        if len(data) > max_bytes: data = data[:max_bytes]
        return data.decode("utf-8", errors="replace")

    def write(self, relative: str, content: str):
        p = self.path(relative); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def delete(self, relative: str):
        p=self.path(relative)
        if p.is_dir(): raise IsADirectoryError(relative)
        p.unlink()

    def tree(self, limit: int = 1000):
        out=[]
        for p in sorted(self.root.rglob('*')):
            if any(part in IGNORED for part in p.parts): continue
            rel=p.relative_to(self.root)
            if rel.name.startswith('.') and rel.name not in {'.env.example'}: continue
            out.append(str(rel) + ('/' if p.is_dir() else ''))
            if len(out)>=limit: break
        return out

    def snapshot(self):
        # Lightweight deterministic snapshot for rollback. Git is preferred when available.
        import tempfile, shutil
        d=Path(tempfile.mkdtemp(prefix='uc-snapshot-'))
        shutil.copytree(self.root,d/'workspace',ignore=shutil.ignore_patterns(*IGNORED))
        return d/'workspace'

    def restore(self, snapshot: Path):
        import shutil
        for p in list(self.root.iterdir()):
            if p.name in IGNORED: continue
            if p.is_dir(): shutil.rmtree(p)
            else: p.unlink()
        for p in snapshot.iterdir():
            target=self.root/p.name
            if p.is_dir(): shutil.copytree(p,target)
            else: shutil.copy2(p,target)
