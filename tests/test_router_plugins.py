from universal_coder.router import ModelRouter
from universal_coder.plugins import Plugin, PluginRegistry
from universal_coder.models import Message, ModelResponse
class P:
    def __init__(self,name): self.name=name
    def generate(self,*a): return ModelResponse(Message('assistant','ok'))
def test_router_and_plugins():
    r=ModelRouter(); r.register(P('a'),1); r.register(P('b'),2); assert r.choose().name=='b'
    pr=PluginRegistry(); pr.register(Plugin('x','1',[{'type':'function','function':{'name':'hello','parameters':{'type':'object'}}}],{'hello':lambda a:'hi'})); assert pr.call('hello',{})=='hi'
