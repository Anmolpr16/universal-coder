from universal_coder.models import Message, ModelCapabilities, StreamChunk
from universal_coder.router import ModelRouter
from universal_coder.routing import RoutedProvider
from universal_coder.providers.mock import MockProvider

def test_capability_router():
    r=ModelRouter(); r.register(MockProvider(), priority=5)
    assert r.choose({"streaming"}).name == "mock"

def test_mock_stream():
    chunks=list(MockProvider().stream([Message("user","x")], []))
    assert chunks[-1].done and "runtime" in "".join(x.text for x in chunks)

def test_stream_chunk_contract():
    c=StreamChunk(text="x",done=True)
    assert c.done and c.text=="x"
