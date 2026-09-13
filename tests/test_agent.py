import tempfile
from universal_coder.agent import Agent
from universal_coder.providers.mock import MockProvider

def test_agent():
    with tempfile.TemporaryDirectory() as d:
        assert 'Mock provider' in Agent(MockProvider(),d).run('test',verify=False)
