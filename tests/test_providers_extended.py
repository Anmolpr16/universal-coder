from universal_coder.providers.gemini import GeminiProvider
from universal_coder.providers.openai_responses import OpenAIResponsesProvider
from universal_coder.models import Message

def test_gemini_normalization():
    p=GeminiProvider("x")
    system, contents=p._contents([Message("system","be precise"), Message("user","hello")])
    assert system == ["be precise"]
    assert contents[0]["role"] == "user"
    assert p._tools([{ "function": {"name":"read_file","parameters":{"type":"object"}} }])[0]["functionDeclarations"][0]["name"] == "read_file"

def test_openai_responses_normalization():
    p=OpenAIResponsesProvider("x")
    payload=p._input([Message("user","hello")])
    assert payload[0]["role"] == "user"
    assert payload[0]["content"][0]["type"] == "input_text"
    assert p._tools([{ "function": {"name":"run_command","parameters":{"type":"object"}} }])[0]["type"] == "function"
