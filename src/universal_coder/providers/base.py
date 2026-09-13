"""Provider adapters with one internal protocol.

The runtime speaks Message/ModelResponse/StreamChunk. Provider-specific wire
formats stay in this module, making local and hosted models interchangeable.
"""
from __future__ import annotations
import json, urllib.request, urllib.error
from typing import Iterator
from universal_coder.models import Message, ModelResponse, ModelCapabilities, StreamChunk


def _tool_call_dict(c, i=0):
    fn = c.get('function', c) if isinstance(c, dict) else {}
    args = fn.get('arguments', {})
    if not isinstance(args, str): args = json.dumps(args, separators=(',', ':'))
    return {'id': c.get('id', f'call_{i}'), 'type': 'function',
            'function': {'name': fn.get('name'), 'arguments': args}}


def _messages(messages):
    out=[]
    for m in messages:
        x={'role':m.role,'content':m.content}
        if m.tool_calls:
            x['tool_calls']=[_tool_call_dict(c,i) for i,c in enumerate(m.tool_calls)]
        if m.tool_call_id: x['tool_call_id']=m.tool_call_id
        out.append(x)
    return out


def _parse_tool_calls(obj):
    choices=obj.get('choices') or []
    if not choices: return Message('assistant',obj.get('output','') or '')
    msg=choices[0].get('message') or {}
    calls=[]
    for c in msg.get('tool_calls') or []:
        fn=c.get('function',{})
        calls.append({'id':c.get('id'), 'function':{'name':fn.get('name'),'arguments':fn.get('arguments','{}')}})
    return Message('assistant',msg.get('content') or '',calls)

class HTTPProvider:
    capabilities = ModelCapabilities(tool_calling=True)
    def __init__(self, base_url, api_key, model, name='http'):
        self.base_url=base_url.rstrip('/'); self.api_key=api_key or ''; self.model=model; self.name=name
    def _request(self,url,payload,headers,stream=False):
        data=json.dumps(payload).encode(); req=urllib.request.Request(url,data=data,headers=headers,method='POST')
        try:
            return urllib.request.urlopen(req,timeout=300)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f'provider HTTP {e.code}: {e.read().decode(errors="replace")[:4000]}')
    def _post(self,url,payload,headers):
        with self._request(url,payload,headers) as r: return json.loads(r.read().decode())

class OpenAICompatibleProvider(HTTPProvider):
    capabilities=ModelCapabilities(tool_calling=True,streaming=True,vision=True,structured_output=True)
    def __init__(self, base_url, api_key, model): super().__init__(base_url,api_key,model,'openai-compatible')
    def _headers(self):
        h={'Content-Type':'application/json'}
        if self.api_key: h['Authorization']='Bearer '+self.api_key
        return h
    def generate(self,messages,tools):
        payload={'model':self.model,'messages':_messages(messages),'tools':tools,'tool_choice':'auto'}
        obj=self._post(self.base_url+'/chat/completions',payload,self._headers())
        return ModelResponse(_parse_tool_calls(obj),obj.get('usage',{}),obj)
    def stream(self,messages,tools)->Iterator[StreamChunk]:
        payload={'model':self.model,'messages':_messages(messages),'tools':tools,'tool_choice':'auto','stream':True}
        with self._request(self.base_url+'/chat/completions',payload,self._headers(),True) as r:
            for raw in r:
                line=raw.decode(errors='replace').strip()
                if not line.startswith('data:'): continue
                data=line[5:].strip()
                if data=='[DONE]': yield StreamChunk(done=True); return
                try: obj=json.loads(data)
                except json.JSONDecodeError: continue
                choice=(obj.get('choices') or [{}])[0]; delta=choice.get('delta') or {}
                calls=[]
                for c in delta.get('tool_calls') or []:
                    fn=c.get('function',{})
                    calls.append({'id':c.get('id'),'index':c.get('index',0),'function':{'name':fn.get('name'),'arguments':fn.get('arguments','')}})
                yield StreamChunk(delta.get('content') or '',calls,choice.get('finish_reason') is not None,obj.get('usage',{}),obj)

class AnthropicProvider(HTTPProvider):
    capabilities=ModelCapabilities(tool_calling=True,streaming=True,vision=True)
    def __init__(self, api_key, model, base_url='https://api.anthropic.com/v1'): super().__init__(base_url,api_key,model,'anthropic')
    def _native_messages(self,messages):
        out=[]
        pending=[]
        for m in messages:
            if m.role=='system': continue
            if m.role=='tool':
                pending.append({'type':'tool_result','tool_use_id':m.tool_call_id,'content':m.content})
                continue
            if pending:
                out.append({'role':'user','content':pending}); pending=[]
            if m.role=='assistant' and m.tool_calls:
                blocks=[]
                if m.content: blocks.append({'type':'text','text':m.content})
                for c in m.tool_calls:
                    fn=c.get('function',c); args=fn.get('arguments',{})
                    if isinstance(args,str):
                        try: args=json.loads(args)
                        except json.JSONDecodeError: args={}
                    blocks.append({'type':'tool_use','id':c.get('id'),'name':fn.get('name'),'input':args})
                out.append({'role':'assistant','content':blocks})
            else:
                out.append({'role':m.role if m.role in ('user','assistant') else 'user','content':m.content})
        if pending: out.append({'role':'user','content':pending})
        return out
    def _tools(self,tools):
        return [{'name':t['function']['name'],'description':t['function'].get('description',''),'input_schema':t['function']['parameters']} for t in tools]
    def _headers(self): return {'Content-Type':'application/json','x-api-key':self.api_key,'anthropic-version':'2023-06-01'}
    def _payload(self,messages,tools,stream=False):
        system='\n'.join(m.content for m in messages if m.role=='system')
        p={'model':self.model,'max_tokens':8192,'messages':self._native_messages(messages),'tools':self._tools(tools)}
        if system: p['system']=system
        if stream: p['stream']=True
        return p
    def generate(self,messages,tools):
        obj=self._post(self.base_url+'/messages',self._payload(messages,tools),self._headers())
        text=''; calls=[]
        for b in obj.get('content',[]):
            if b.get('type')=='text': text+=b.get('text','')
            elif b.get('type')=='tool_use': calls.append({'id':b.get('id'),'function':{'name':b.get('name'),'arguments':b.get('input',{})}})
        return ModelResponse(Message('assistant',text,calls),obj.get('usage',{}),obj)
    def stream(self,messages,tools)->Iterator[StreamChunk]:
        tool_state={}
        with self._request(self.base_url+'/messages',self._payload(messages,tools,True),self._headers(),True) as r:
            for raw in r:
                line=raw.decode(errors='replace').strip()
                if not line.startswith('data:'): continue
                try: obj=json.loads(line[5:].strip())
                except json.JSONDecodeError: continue
                typ=obj.get('type'); delta=obj.get('delta') or {}
                if typ=='content_block_start':
                    block=obj.get('content_block') or {}
                    if block.get('type')=='tool_use':
                        idx=obj.get('index',len(tool_state)); tool_state[idx]={'id':block.get('id'),'function':{'name':block.get('name'),'arguments':''}}
                elif typ=='content_block_delta':
                    if delta.get('type')=='text_delta': yield StreamChunk(delta.get('text',''),raw=obj)
                    elif delta.get('type')=='input_json_delta':
                        idx=obj.get('index',0); state=tool_state.setdefault(idx,{'id':None,'function':{'name':'','arguments':''}})
                        state['function']['arguments'] += delta.get('partial_json','')
                        yield StreamChunk(tool_calls=[{'id':state['id'],'index':idx,'function':{'name':state['function']['name'],'arguments':delta.get('partial_json','')}}],raw=obj)
                elif typ=='message_delta': yield StreamChunk(done=delta.get('stop_reason') is not None,usage=obj.get('usage',{}),raw=obj)
                elif typ=='message_stop': yield StreamChunk(done=True,raw=obj); return
