from __future__ import annotations
import time
import json, urllib.request, urllib.error
from typing import Iterator
from universal_coder.models import Message, ModelResponse, ModelCapabilities, StreamChunk

class GeminiProvider:
    """Google Gemini REST adapter using the GenerateContent API.

    It deliberately uses stdlib HTTP so Universal Coder keeps zero runtime
    Python dependencies. Function calls/results are translated to the internal
    Message protocol.
    """
    capabilities = ModelCapabilities(tool_calling=True, streaming=True, vision=True, structured_output=True)
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-3.8-flash", base_url: str = "https://generativelanguage.googleapis.com/v1beta"):
        self.api_key = api_key or ""
        self.model = model
        self.base_url = base_url.rstrip("/")

    def _headers(self):
        return {"Content-Type": "application/json", "x-goog-api-key": self.api_key}

    def _tools(self, tools):
        declarations=[]
        for t in tools:
            f=t.get("function",t)
            declarations.append({"name":f["name"],"description":f.get("description", ""),"parameters":f.get("parameters", {"type":"object"})})
        return [{"functionDeclarations": declarations}] if declarations else []

    def _contents(self, messages):
        out=[]
        system=[]
        for m in messages:
            if m.role == "system": system.append(m.content); continue
            role = "model" if m.role == "assistant" else "user"
            parts=[]
            if m.content: parts.append({"text":m.content})
            if m.role == "assistant" and m.tool_calls:
                for c in m.tool_calls:
                    f=c.get("function",c); args=f.get("arguments",{})
                    if isinstance(args,str):
                        try: args=json.loads(args)
                        except json.JSONDecodeError: args={}
                    function_call = {
                        "name": f.get("name"),
                        "args": args,
                    }
                    if c.get("id") is not None:
                        function_call["id"] = c["id"]
                    if c.get("thought_signature") is not None:
                        parts.append({
                            "functionCall": function_call,
                            "thoughtSignature": c["thought_signature"],
                        })
                    else:
                        parts.append({"functionCall": function_call})
            if m.role == "tool":
                parts=[{"functionResponse":{"name":m.tool_call_id or "tool","response":{"output":m.content}}}]
                role="user"
            out.append({"role":role,"parts":parts or [{"text":""}]})
        return system,out

    def _request(self, path, payload):
        url = f"{self.base_url}/{path.lstrip('/')}"
        body = json.dumps(payload).encode()

        for attempt in range(3):
            req = urllib.request.Request(
                url,
                data=body,
                headers=self._headers(),
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    return json.loads(r.read().decode())

            except urllib.error.HTTPError as e:
                raw = e.read().decode(errors="replace")

                if e.code != 429 or attempt == 2:
                    raise RuntimeError(
                        f"Gemini HTTP {e.code}: {raw[:4000]}"
                    )

                delay = 2 ** attempt

                try:
                    error = json.loads(raw)
                    retry_delay = (
                        error.get("error", {})
                        .get("details", [])
                    )

                    for detail in retry_delay:
                        if detail.get("@type", "").endswith("RetryInfo"):
                            value = detail.get("retryDelay", "")
                            if value.endswith("s"):
                                delay = max(
                                    delay,
                                    float(value[:-1]),
                                )
                            break
                except (ValueError, TypeError):
                    pass

                time.sleep(delay)

    def generate(self, messages, tools):
        system, contents=self._contents(messages)
        payload={"contents":contents}
        if system: payload["systemInstruction"]={"parts":[{"text":"\n".join(system)}]}
        if tools: payload["tools"]=self._tools(tools)
        obj=self._request(f"models/{self.model}:generateContent",payload)
        text=""; calls=[]
        for part in ((obj.get("candidates") or [{}])[0].get("content") or {}).get("parts",[]):
            if part.get("text"): text += part["text"]
            if part.get("functionCall"):
                fc = part["functionCall"]
                call = {
                    "id": fc.get("id") or f"gemini_call_{len(calls)}",
                    "function": {
                        "name": fc.get("name"),
                        "arguments": fc.get("args", {}),
                    },
                }
                if part.get("thoughtSignature") is not None:
                    call["thought_signature"] = part["thoughtSignature"]
                calls.append(call)
        return ModelResponse(Message("assistant",text,calls), obj.get("usageMetadata",{}), obj)

    def stream(self, messages, tools) -> Iterator[StreamChunk]:
        system, contents=self._contents(messages)
        payload={"contents":contents}
        if system: payload["systemInstruction"]={"parts":[{"text":"\n".join(system)}]}
        if tools: payload["tools"]=self._tools(tools)
        req=urllib.request.Request(f"{self.base_url}/models/{self.model}:streamGenerateContent?alt=sse", data=json.dumps(payload).encode(), headers=self._headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                for raw in r:
                    line=raw.decode(errors="replace").strip()
                    if not line.startswith("data:"): continue
                    try: obj=json.loads(line[5:].strip())
                    except json.JSONDecodeError: continue
                    calls=[]; text=""
                    for part in ((obj.get("candidates") or [{}])[0].get("content") or {}).get("parts",[]):
                        if part.get("text"): text += part["text"]
                        if part.get("functionCall"):
                            fc = part["functionCall"]
                            call = {
                                "id": fc.get("id") or "gemini_call",
                                "index": 0,
                                "function": {
                                    "name": fc.get("name"),
                                    "arguments": json.dumps(
                                        fc.get("args", {}),
                                        separators=(",", ":"),
                                    ),
                                },
                            }
                            if part.get("thoughtSignature") is not None:
                                call["thought_signature"] = part["thoughtSignature"]
                            calls.append(call)
                    yield StreamChunk(text,calls,False,obj.get("usageMetadata",{}),obj)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Gemini HTTP {e.code}: {e.read().decode(errors='replace')[:4000]}")
