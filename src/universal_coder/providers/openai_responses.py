from __future__ import annotations
import json, urllib.request, urllib.error
from universal_coder.models import Message, ModelResponse, ModelCapabilities, StreamChunk

class OpenAIResponsesProvider:
    """OpenAI Responses API adapter for first-party OpenAI models."""
    name="openai-responses"
    capabilities=ModelCapabilities(tool_calling=True, streaming=True, vision=True, structured_output=True)
    def __init__(self, api_key, model="gpt-5", base_url="https://api.openai.com/v1"):
        self.api_key=api_key or ""; self.model=model; self.base_url=base_url.rstrip("/")
    def _headers(self): return {"Content-Type":"application/json","Authorization":"Bearer "+self.api_key}
    def _input(self,messages):
        out=[]
        for m in messages:
            if m.role=="system": continue
            if m.role=="tool": out.append({"type":"function_call_output","call_id":m.tool_call_id,"output":m.content}); continue
            content=[]
            if m.content: content.append({"type":"input_text" if m.role=="user" else "output_text","text":m.content})
            if m.role=="assistant" and m.tool_calls:
                for c in m.tool_calls:
                    f=c.get("function",c); args=f.get("arguments",{})
                    if not isinstance(args,str): args=json.dumps(args,separators=(",",":"))
                    out.append({"type":"function_call","call_id":c.get("id"),"name":f.get("name"),"arguments":args})
            if content: out.append({"role":m.role,"content":content})
        return out
    def _tools(self,tools):
        return [{"type":"function","name":t["function"]["name"],"description":t["function"].get("description",""),"parameters":t["function"].get("parameters",{"type":"object"}),"strict":False} for t in tools]
    def _post(self,payload):
        req=urllib.request.Request(self.base_url+"/responses",data=json.dumps(payload).encode(),headers=self._headers(),method="POST")
        try:
            with urllib.request.urlopen(req,timeout=300) as r:return json.loads(r.read().decode())
        except urllib.error.HTTPError as e: raise RuntimeError(f"OpenAI HTTP {e.code}: {e.read().decode(errors='replace')[:4000]}")
    def _parse(self,obj):
        text=obj.get("output_text",""); calls=[]
        for item in obj.get("output",[]):
            if item.get("type")=="function_call": calls.append({"id":item.get("call_id") or item.get("id"),"function":{"name":item.get("name"),"arguments":item.get("arguments","{}")}})
            elif item.get("type")=="message":
                for part in item.get("content",[]):
                    if part.get("type") in ("output_text","text"): text += part.get("text","")
        return Message("assistant",text,calls)
    def generate(self,messages,tools):
        payload={"model":self.model,"input":self._input(messages),"store":False}
        if tools: payload["tools"]=self._tools(tools); payload["tool_choice"]="auto"
        obj=self._post(payload); return ModelResponse(self._parse(obj),obj.get("usage",{}),obj)
    def stream(self,messages,tools):
        payload={"model":self.model,"input":self._input(messages),"store":False,"stream":True}
        if tools: payload["tools"]=self._tools(tools); payload["tool_choice"]="auto"
        req=urllib.request.Request(self.base_url+"/responses",data=json.dumps(payload).encode(),headers=self._headers(),method="POST")
        try:
            with urllib.request.urlopen(req,timeout=300) as r:
                calls={}
                for raw in r:
                    line=raw.decode(errors="replace").strip()
                    if not line.startswith("data:"): continue
                    try: e=json.loads(line[5:].strip())
                    except json.JSONDecodeError: continue
                    typ=e.get("type","")
                    if typ=="response.output_text.delta": yield StreamChunk(text=e.get("delta","") ,raw=e); continue
                    if typ=="response.function_call_arguments.delta":
                        idx=e.get("output_index",0); c=calls.setdefault(idx,{"id":e.get("item_id"),"function":{"name":"","arguments":""}}); c["function"]["arguments"]+=e.get("delta",""); yield StreamChunk(tool_calls=[dict(c,index=idx)],raw=e); continue
                    if typ=="response.function_call_arguments.done":
                        idx=e.get("output_index",0); c=calls.setdefault(idx,{"id":e.get("call_id") or e.get("item_id"),"function":{"name":e.get("name"),"arguments":""}}); c["id"]=e.get("call_id") or c.get("id"); c["function"]["name"]=e.get("name") or c["function"].get("name"); c["function"]["arguments"]=e.get("arguments",c["function"].get("arguments","")); yield StreamChunk(tool_calls=[dict(c,index=idx)],raw=e)
                    if typ=="response.completed": yield StreamChunk(done=True,raw=e)
        except urllib.error.HTTPError as e: raise RuntimeError(f"OpenAI HTTP {e.code}: {e.read().decode(errors='replace')[:4000]}")
