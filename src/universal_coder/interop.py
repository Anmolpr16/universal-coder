"""Secure tool interoperability layer: native tools, plugins, and MCP-style stdio servers."""
from __future__ import annotations
import json, os, subprocess, threading
from dataclasses import dataclass, field
from typing import Any

@dataclass
class ToolGrant:
    allow: set[str] = field(default_factory=set)
    deny: set[str] = field(default_factory=set)
    def permits(self, name: str) -> bool:
        if name in self.deny: return False
        return not self.allow or name in self.allow

class StdioToolServer:
    """Minimal JSON-RPC 2.0/MCP-compatible stdio client.

    The server is started explicitly by the user. No arbitrary command supplied
    by a model is executed by this class.
    """
    def __init__(self, command: list[str], name: str, env: dict[str,str]|None=None, grant: ToolGrant|None=None):
        if not command: raise ValueError('empty tool server command')
        self.command=command; self.name=name; self.env=env or {}; self.grant=grant or ToolGrant(); self.proc=None; self._id=0; self._lock=threading.Lock()
    def start(self):
        if self.proc and self.proc.poll() is None: return
        env=os.environ.copy(); env.update(self.env)
        self.proc=subprocess.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, env=env, bufsize=1)
        self._request('initialize', {'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'universal-coder','version':'1.0.0'}})
        self._notify('notifications/initialized', {})
    def _write(self,obj):
        assert self.proc and self.proc.stdin
        self.proc.stdin.write(json.dumps(obj,separators=(',',':'))+'\n'); self.proc.stdin.flush()
    def _read(self, ident):
        assert self.proc and self.proc.stdout
        while True:
            line=self.proc.stdout.readline()
            if not line: raise RuntimeError(f'tool server {self.name} exited')
            msg=json.loads(line)
            if msg.get('id')==ident: return msg
    def _request(self,method,params):
        with self._lock:
            self._id+=1; ident=self._id; self._write({'jsonrpc':'2.0','id':ident,'method':method,'params':params}); msg=self._read(ident)
        if 'error' in msg: raise RuntimeError(str(msg['error']))
        return msg.get('result',{})
    def _notify(self,method,params):
        with self._lock: self._write({'jsonrpc':'2.0','method':method,'params':params})
    def tools(self):
        self.start(); result=self._request('tools/list',{}); return result.get('tools',[])
    def call(self,name,args):
        if not self.grant.permits(name): raise PermissionError(f'tool denied: {name}')
        self.start(); result=self._request('tools/call',{'name':name,'arguments':args})
        content=result.get('content',[]); text=[]
        for item in content:
            if item.get('type')=='text': text.append(item.get('text',''))
            else: text.append(json.dumps(item,ensure_ascii=False))
        return '\n'.join(text), not bool(result.get('isError',False))
    def close(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()

class ToolBroker:
    """Combines native and external tools behind one schema/call interface."""
    def __init__(self, native, grant: ToolGrant|None=None):
        self.native=native; self.grant=grant or ToolGrant(); self.servers: list[StdioToolServer]=[]; self._owners={}
    def add_server(self, server: StdioToolServer):
        for schema in server.tools():
            fn=schema.get('function',schema); name=fn.get('name')
            if not name or name in self._owners or name in {x.get('function',{}).get('name') for x in self.native.schemas()}: raise ValueError(f'duplicate/invalid external tool: {name}')
            self._owners[name]=server
        self.servers.append(server)
    def schemas(self):
        out=list(self.native.schemas())
        for s in self.servers: out.extend(s.tools())
        return out
    def call(self,name,args):
        if not self.grant.permits(name):
            from universal_coder.tools.core import ToolResult
            return ToolResult(False,'',f'external tool denied: {name}')
        if name in self._owners:
            try:
                text,ok=self._owners[name].call(name,args)
                from universal_coder.tools.core import ToolResult
                return ToolResult(ok,text,'' if ok else 'external tool returned an error')
            except Exception as e:
                from universal_coder.tools.core import ToolResult
                return ToolResult(False,'',f'{type(e).__name__}: {e}')
        return self.native.call(name,args)
    def close(self):
        for s in self.servers: s.close()
