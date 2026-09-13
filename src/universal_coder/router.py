from dataclasses import dataclass
from typing import Any
from universal_coder.models import ModelCapabilities

@dataclass
class ProviderInfo:
    name: str
    provider: Any
    priority: int = 0
    capabilities: set[str] | None = None

class ModelRouter:
    """Capability-aware provider router with deterministic priority and failover."""
    def __init__(self, providers=None): self.providers=list(providers or [])
    def register(self, provider, priority=0, capabilities=None, name=None):
        caps=set(capabilities or set())
        if not caps:
            pc=getattr(provider,'capabilities',None)
            if pc:
                caps={k for k,v in vars(pc).items() if v}
        self.providers.append(ProviderInfo(name or provider.name,provider,priority,caps))
    def choose(self, required=None, preferred=None):
        required=set(required or set())
        candidates=[p for p in self.providers if required <= (p.capabilities or set())]
        if not candidates: candidates=self.providers
        if preferred:
            exact=[p for p in candidates if p.name==preferred or getattr(p.provider,'name','')==preferred]
            if exact: return max(exact,key=lambda p:p.priority).provider
        if not candidates: raise RuntimeError('no model providers registered')
        return max(candidates,key=lambda p:p.priority).provider
    def ordered(self, required=None):
        required=set(required or set())
        c=[p for p in self.providers if required <= (p.capabilities or set())]
        return sorted(c or self.providers,key=lambda p:p.priority,reverse=True)
    def names(self): return [p.name for p in self.providers]
