from dataclasses import dataclass
import os

@dataclass
class Config:
    provider: str = "openai-compatible"
    model: str = "llama3.1"
    base_url: str = "http://localhost:11434/v1"
    api_key: str = ""
    max_steps: int = 30
    command_timeout: int = 120
    max_output: int = 12000
    auto_verify: bool = True
    sandbox_mode: str = "trusted"
    max_request_bytes: int = 1_000_000
    max_concurrent_runs: int = 2

    def validate(self):
        if self.provider not in {"mock", "openai-compatible", "openai-responses", "anthropic", "gemini", "auto"}:
            raise ValueError("unsupported provider")
        if not self.model or len(self.model) > 512:
            raise ValueError("invalid model")
        if self.max_steps < 1 or self.max_steps > 1000:
            raise ValueError("max_steps must be between 1 and 1000")
        if self.command_timeout < 1 or self.command_timeout > 86400:
            raise ValueError("command_timeout out of range")
        if self.max_output < 256 or self.max_output > 10_000_000:
            raise ValueError("max_output out of range")
        if self.sandbox_mode not in {"trusted", "isolated"}:
            raise ValueError("invalid sandbox_mode")
        return self

    @classmethod
    def from_env(cls):
        return cls(
            provider=os.getenv("CODER_PROVIDER", "openai-compatible"),
            model=os.getenv("CODER_MODEL", "llama3.1"),
            base_url=os.getenv("CODER_BASE_URL", "http://localhost:11434/v1"),
            api_key=os.getenv("CODER_API_KEY", ""),
            max_steps=int(os.getenv("CODER_MAX_STEPS", "30")),
            command_timeout=int(os.getenv("CODER_COMMAND_TIMEOUT", "120")),
            sandbox_mode=os.getenv("CODER_SANDBOX_MODE", "trusted"),
            max_request_bytes=int(os.getenv("CODER_MAX_REQUEST_BYTES", "1000000")),
            max_concurrent_runs=max(1, int(os.getenv("CODER_MAX_CONCURRENT_RUNS", "2"))),
        ).validate()
