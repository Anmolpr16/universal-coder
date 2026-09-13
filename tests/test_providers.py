from universal_coder.providers.base import OpenAICompatibleProvider
from universal_coder.models import Message

def test_openai_payload_helpers():
    from universal_coder.providers.base import _messages
    x=_messages([Message('user','hi')]); assert x[0]['content']=='hi'
