from universal_coder.providers.gemini import GeminiProvider
from universal_coder.providers.openai_responses import OpenAIResponsesProvider
from universal_coder.models import Message


def test_gemini_normalization():
    p = GeminiProvider("x")
    system, contents = p._contents(
        [Message("system", "be precise"), Message("user", "hello")]
    )

    assert system == ["be precise"]
    assert contents[0]["role"] == "user"
    assert p._tools(
        [{"function": {"name": "read_file", "parameters": {"type": "object"}}}]
    )[0]["functionDeclarations"][0]["name"] == "read_file"


def test_openai_responses_normalization():
    p = OpenAIResponsesProvider("x")
    payload = p._input([Message("user", "hello")])

    assert payload[0]["role"] == "user"
    assert payload[0]["content"][0]["type"] == "input_text"
    assert p._tools(
        [{"function": {"name": "run_command", "parameters": {"type": "object"}}}]
    )[0]["type"] == "function"


def test_gemini_thought_signature_round_trip():
    p = GeminiProvider("x")

    messages = [
        Message(
            "assistant",
            tool_calls=[
                {
                    "id": "call-1",
                    "thought_signature": "signature-123",
                    "function": {
                        "name": "read_file",
                        "arguments": {"path": "example.py"},
                    },
                }
            ],
        )
    ]

    system, contents = p._contents(messages)

    assert system == []
    function_part = contents[0]["parts"][0]
    assert function_part["functionCall"]["name"] == "read_file"
    assert function_part["functionCall"]["args"] == {"path": "example.py"}
    assert function_part["thoughtSignature"] == "signature-123"


def test_gemini_429_retry_uses_retry_delay(monkeypatch):
    p = GeminiProvider("x")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"ok": true}'

    import urllib.error

    errors = [
        urllib.error.HTTPError(
            "https://example.invalid",
            429,
            "Too Many Requests",
            {},
            None,
        )
    ]

    retry_body = (
        b'{"error":{"details":[{"@type":'
        b'"type.googleapis.com/google.rpc.RetryInfo",'
        b'"retryDelay":"7s"}]}}'
    )

    def fake_read():
        return retry_body

    def fake_urlopen(req, timeout=300):
        if errors:
            error = errors.pop(0)
            error.read = fake_read
            raise error
        return FakeResponse()

    sleeps = []

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("time.sleep", lambda value: sleeps.append(value))

    result = p._request("models/test:generateContent", {})

    assert result == {"ok": True}
    assert sleeps == [7.0]
