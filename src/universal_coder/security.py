from __future__ import annotations
import hmac, ipaddress, os
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class SecurityConfig:
    auth_token: str = ""
    max_request_bytes: int = 1_000_000
    max_concurrent_runs: int = 2
    max_objective_chars: int = 20_000
    max_workspace_chars: int = 2_000
    require_auth_on_loopback: bool = False
    allowed_workspace_roots: tuple[str, ...] = ()

    @classmethod
    def from_env(cls):
        roots = tuple(x for x in os.getenv("CODER_WORKSPACE_ROOTS", "").split(os.pathsep) if x)
        return cls(
            auth_token=os.getenv("CODER_AUTH_TOKEN", ""),
            max_request_bytes=max(1024, int(os.getenv("CODER_MAX_REQUEST_BYTES", "1000000"))),
            max_concurrent_runs=max(1, int(os.getenv("CODER_MAX_CONCURRENT_RUNS", "2"))),
            max_objective_chars=max(100, int(os.getenv("CODER_MAX_OBJECTIVE_CHARS", "20000"))),
            max_workspace_chars=max(64, int(os.getenv("CODER_MAX_WORKSPACE_CHARS", "2000"))),
            require_auth_on_loopback=os.getenv("CODER_REQUIRE_AUTH", "0").lower() in {"1","true","yes"},
            allowed_workspace_roots=roots,
        )

def token_ok(provided: str, expected: str) -> bool:
    if not expected:
        return True
    return bool(provided) and hmac.compare_digest(provided, expected)

def is_loopback(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False

def workspace_allowed(workspace: str, roots: tuple[str, ...]) -> bool:
    """Return whether a requested workspace is inside one of the configured roots."""
    if not roots:
        return False
    try:
        candidate = Path(workspace).expanduser().resolve()
        return any(candidate == root or root in candidate.parents
                   for root in (Path(r).expanduser().resolve() for r in roots))
    except (OSError, RuntimeError, ValueError):
        return False
