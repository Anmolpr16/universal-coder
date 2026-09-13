from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

@dataclass
class Event:
    type: str
    data: dict[str,Any]=field(default_factory=dict)
    timestamp: str=field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class EventBus:
    def __init__(self): self.listeners=[]
    def subscribe(self, fn:Callable[[Event],None]): self.listeners.append(fn)
    def emit(self,type,**data):
        e=Event(type,data)
        for fn in list(self.listeners):
            try: fn(e)
            except Exception: pass
        return e
