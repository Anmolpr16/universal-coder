from __future__ import annotations
import os, shutil, sys, urllib.parse
from dataclasses import dataclass
from universal_coder.config import Config

@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str

def run_checks() -> list[Check]:
    out: list[Check] = []
    try:
        c = Config.from_env(); out.append(Check("configuration", True, f"provider={c.provider}, model={c.model}, sandbox={c.sandbox_mode}"))
    except Exception as e:
        out.append(Check("configuration", False, f"{type(e).__name__}: {e}")); c = None
    for name in ("docker", "podman"):
        found = shutil.which(name)
        out.append(Check(name, bool(found), found or "not installed"))
    roots = os.getenv("CODER_WORKSPACE_ROOTS", "")
    out.append(Check("workspace allowlist", bool(roots), roots or "not configured; required for remote API"))
    base = os.getenv("CODER_BASE_URL", "")
    if base:
        try:
            u = urllib.parse.urlparse(base); ok = u.scheme in {"http", "https"} and bool(u.netloc)
            out.append(Check("provider endpoint", ok, base if ok else "invalid URL"))
        except ValueError as e: out.append(Check("provider endpoint", False, str(e)))
    else: out.append(Check("provider endpoint", True, "not required for mock/externally configured providers"))
    out.append(Check("python", sys.version_info >= (3,11), sys.version.split()[0]))
    return out

def main() -> int:
    checks = run_checks()
    for c in checks: print(f"[{ 'PASS' if c.ok else 'WARN' }] {c.name}: {c.detail}")
    # Doctor warns rather than failing on optional deployment capabilities.
    return 0
