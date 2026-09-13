"""Named model profiles for local/cloud endpoints."""
from dataclasses import dataclass, field
from universal_coder.models import ModelCapabilities

@dataclass(frozen=True)
class ModelProfile:
    name: str
    provider: str
    model: str
    base_url: str = ''
    capabilities: ModelCapabilities = field(default_factory=ModelCapabilities)
    priority: int = 0

class ModelRegistry:
    def __init__(self): self._items={}
    def register(self, profile): self._items[profile.name]=profile
    def get(self,name): return self._items[name]
    def all(self): return list(self._items.values())
    def names(self): return list(self._items)
