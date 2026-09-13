from dataclasses import dataclass
from typing import Any, Callable

@dataclass
class Plugin:
    name: str
    version: str
    tools: list[dict[str,Any]]
    handlers: dict[str,Callable]

class PluginRegistry:
    def __init__(self): self.plugins={}; self.tools={}
    def register(self, plugin: Plugin):
        if plugin.name in self.plugins: raise ValueError('plugin already registered')
        for t in plugin.tools:
            name=t.get('function',{}).get('name') or t.get('name')
            if not name or name in self.tools: raise ValueError(f'invalid/duplicate tool: {name}')
            self.tools[name]=plugin.handlers[name]
        self.plugins[plugin.name]=plugin
    def schemas(self): return [t for p in self.plugins.values() for t in p.tools]
    def call(self,name,args):
        if name not in self.tools: raise KeyError(name)
        return self.tools[name](args)
