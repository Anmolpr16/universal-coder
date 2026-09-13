from dataclasses import dataclass, field
from typing import Any, Protocol, Iterator

@dataclass
class Message:
    role: str
    content: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_call_id: str | None = None

@dataclass
class ModelResponse:
    message: Message
    usage: dict[str, Any] = field(default_factory=dict)
    raw: Any = None

@dataclass(frozen=True)
class ModelCapabilities:
    tool_calling: bool = False
    streaming: bool = False
    vision: bool = False
    structured_output: bool = False
    context_window: int | None = None

@dataclass
class StreamChunk:
    text: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    done: bool = False
    usage: dict[str, Any] = field(default_factory=dict)
    raw: Any = None

class ModelProvider(Protocol):
    name: str
    capabilities: ModelCapabilities
    def generate(self, messages: list[Message], tools: list[dict[str, Any]]) -> ModelResponse: ...
    def stream(self, messages: list[Message], tools: list[dict[str, Any]]) -> Iterator[StreamChunk]: ...
