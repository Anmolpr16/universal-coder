"""Command execution backends with an explicit trust boundary."""
from __future__ import annotations
import os, shutil, signal, subprocess, selectors
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class SandboxConfig:
    mode: str = "trusted"  # trusted | isolated
    timeout: int = 120
    max_output: int = 12000
    network: bool = False
    memory: str = "1g"
    cpus: str = "2"
    pids: int = 256

class CommandExecutor:
    def __init__(self, root: Path, config: SandboxConfig):
        self.root = Path(root).resolve(); self.config = config
        if config.mode not in {"trusted", "isolated"}:
            raise ValueError("sandbox mode must be 'trusted' or 'isolated'")
        if config.timeout < 1 or config.max_output < 256 or config.pids < 1:
            raise ValueError("invalid sandbox limits")
        if config.mode == "isolated" and shutil.which("docker") is None and shutil.which("podman") is None:
            raise RuntimeError("isolated sandbox requires Docker or Podman")

    def run(self, command: str) -> tuple[bool, str, str]:
        if not command.strip():
            return False, "", "empty command"
        if self.config.mode == "trusted":
            argv = ["/bin/sh", "-lc", command]
            env = self._env()
            cwd = self.root
        else:
            runtime = shutil.which("docker") or shutil.which("podman")
            image = os.getenv("CODER_SANDBOX_IMAGE", "python:3.12-slim")
            argv = [runtime, "run", "--rm", "--init", "--read-only",
                    "--cap-drop=ALL", "--security-opt=no-new-privileges",
                    "--network=none" if not self.config.network else "--network=host",
                    "--cpus", self.config.cpus, "--memory", self.config.memory,
                    "--pids-limit", str(self.config.pids),
                    "-v", f"{self.root}:/workspace:rw", "-w", "/workspace"]
            if self.config.network is False:
                argv += ["--tmpfs", "/tmp:rw,nosuid,nodev,noexec,size=256m"]
            try:
                if hasattr(os, "getuid") and hasattr(os, "getgid"):
                    argv += ["--user", f"{os.getuid()}:{os.getgid()}"]
            except OSError:
                pass
            argv += [image, "/bin/sh", "-lc", command]
            env = self._env()
            cwd = None
        return self._run_bounded(argv, env, cwd)

    def _run_bounded(self, argv, env, cwd):
        try:
            p = subprocess.Popen(argv, cwd=cwd, text=False, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, env=env, start_new_session=True)
            chunks: list[bytes] = []
            total = 0
            sel = selectors.DefaultSelector()
            assert p.stdout is not None
            sel.register(p.stdout, selectors.EVENT_READ)
            deadline = __import__('time').monotonic() + self.config.timeout
            truncated = False
            while True:
                remaining = deadline - __import__('time').monotonic()
                if remaining <= 0:
                    self._terminate(p)
                    return False, self._decode(b''.join(chunks)), f"command timed out after {self.config.timeout}s"
                events = sel.select(min(remaining, 0.25))
                for key, _ in events:
                    data = key.fileobj.read(65536)
                    if not data:
                        sel.unregister(key.fileobj)
                        continue
                    room = max(0, self.config.max_output - total)
                    if room:
                        chunks.append(data[:room]); total += min(len(data), room)
                    if len(data) > room or total >= self.config.max_output:
                        truncated = True
                        self._terminate(p)
                        break
                if truncated:
                    break
                if p.poll() is not None and not events:
                    break
            try:
                p.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._terminate(p)
            output = self._decode(b''.join(chunks))
            if truncated:
                output += "\n[output truncated at configured limit]"
                return False, output, "output limit exceeded"
            return p.returncode == 0, output, "" if p.returncode == 0 else f"exit code {p.returncode}"
        except OSError as e:
            return False, "", f"executor error: {e}"

    @staticmethod
    def _decode(data: bytes) -> str:
        return data.decode("utf-8", errors="replace")

    @staticmethod
    def _terminate(p: subprocess.Popen):
        try:
            if os.name == "posix":
                os.killpg(p.pid, signal.SIGKILL)
            else:
                p.kill()
        except (ProcessLookupError, OSError):
            pass

    def _env(self):
        blocked = ("API_KEY", "TOKEN", "PASSWORD", "SECRET", "PRIVATE_KEY", "CREDENTIAL")
        env = {k: v for k, v in os.environ.items() if not any(x in k.upper() for x in blocked)}
        env.update({"PWD": str(self.root), "HOME": "/tmp"})
        return env
