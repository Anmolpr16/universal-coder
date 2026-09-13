from universal_coder.routing import RoutedProvider
from universal_coder.router import ModelRouter
from universal_coder.models import ModelResponse, Message

class P:
    def __init__(self,name,ok): self.name=name; self.ok=ok
    def generate(self,m,t):
        if not self.ok: raise RuntimeError('down')
        return ModelResponse(Message('assistant','ok'))

def test_router_failover():
    r=ModelRouter(); r.register(P('bad',False), priority=100); r.register(P('good',True), priority=90)
    assert RoutedProvider(r).generate([],[]).message.content=='ok'
