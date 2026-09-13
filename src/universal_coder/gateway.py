"""Transport-neutral streaming helpers for Universal Coder."""
from __future__ import annotations
import json
from universal_coder.events import Event


def sse(event: Event) -> bytes:
    payload = json.dumps({"type": event.type, "timestamp": event.timestamp, **event.data}, ensure_ascii=False)
    return f"event: {event.type}\ndata: {payload}\n\n".encode("utf-8")
