from universal_coder.team import TeamRunner
from universal_coder.models import ModelResponse, Message

class P:
    def __init__(self, name): self.name=name
    def generate(self, messages, tools):
        return ModelResponse(Message('assistant', self.name+' ok'))

def test_team_consults_parallel_specialists():
    ps={k:P(k) for k in ('architect','tester','reviewer')}
    out=TeamRunner(ps).consult('do x','tree')
    assert {x.role for x in out} == {'architect','tester','reviewer'}
    assert 'architect ok' in TeamRunner.synthesize(out)
