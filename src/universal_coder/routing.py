"""Provider routing and failover utilities."""
from universal_coder.router import ModelRouter
from universal_coder.models import StreamChunk, ModelResponse

class RoutedProvider:
    def __init__(self, router: ModelRouter): self.router=router; self.name='router'; self.capabilities=getattr(router.choose(), 'capabilities', None) if router.providers else None
    def generate(self,messages,tools):
        errors=[]
        for info in self.router.ordered({'tool_calling'} if tools else set()):
            try: return info.provider.generate(messages,tools)
            except Exception as exc: errors.append(f'{info.name}: {type(exc).__name__}: {exc}')
        raise RuntimeError('all model providers failed: '+' | '.join(errors))
    def stream(self,messages,tools):
        errors=[]
        for info in self.router.ordered({'streaming'}):
            try:
                yield from info.provider.stream(messages,tools); return
            except Exception as exc: errors.append(f'{info.name}: {type(exc).__name__}: {exc}')
        raise RuntimeError('all streaming providers failed: '+' | '.join(errors))
