from __future__ import annotations
import json, threading, uuid, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from universal_coder.agent import Agent
from universal_coder.config import Config
from universal_coder.providers import OpenAICompatibleProvider, AnthropicProvider, MockProvider, GeminiProvider, OpenAIResponsesProvider
from universal_coder.events import EventBus
from universal_coder.gateway import sse
from universal_coder.persistence import RunStore
from universal_coder.security import SecurityConfig, token_ok, is_loopback, workspace_allowed
from universal_coder.router import ModelRouter
from universal_coder.routing import RoutedProvider
import ssl
from universal_coder import __version__


def provider_from_config(c):
    if c.provider == 'anthropic':
        return AnthropicProvider(c.api_key, c.model)
    if c.provider == 'mock':
        return MockProvider()
    if c.provider == 'gemini':
        return GeminiProvider(c.api_key, c.model, c.base_url if c.base_url != 'http://localhost:11434/v1' else 'https://generativelanguage.googleapis.com/v1beta')
    if c.provider == 'openai-responses':
        return OpenAIResponsesProvider(c.api_key, c.model, c.base_url if c.base_url != 'http://localhost:11434/v1' else 'https://api.openai.com/v1')
    primary = OpenAICompatibleProvider(c.base_url, c.api_key, c.model)
    if c.provider != 'auto':
        return primary
    router = ModelRouter()
    router.register(primary, priority=100, name='primary')
    for i, url in enumerate(filter(None, os.getenv('CODER_FALLBACK_URLS', '').split(','))):
        router.register(OpenAICompatibleProvider(url.strip(), c.api_key, c.model), priority=90-i, name=f'fallback-{i+1}')
    return RoutedProvider(router)


class RunManager:
    def __init__(self, store, limit=2):
        self.store=store; self.sem=threading.BoundedSemaphore(limit); self.active={}; self.lock=threading.Lock()
    def start(self, objective, workspace, config, verify=True, stream=False, events=None):
        if not self.sem.acquire(blocking=False): raise RuntimeError('maximum concurrent runs reached')
        run_id=uuid.uuid4().hex
        events=events or EventBus()
        def work():
            try:
                self.active[run_id]='running'
                result=Agent(provider_from_config(config), workspace, config.max_steps, config.command_timeout, events=events, store=self.store, sandbox_mode=config.sandbox_mode).run(objective,verify,stream=stream)
                self.active[run_id]='completed'; return result
            except Exception as e:
                self.active[run_id]='failed'; raise
            finally:
                self.sem.release()
        thread=threading.Thread(target=work,daemon=True)
        with self.lock:
            self.active[run_id]=thread
        thread.start()
        return run_id, thread
    def status(self, run_id):
        with self.lock:
            value=self.active.get(run_id)
        record=self.store.get(run_id)
        if isinstance(value, str):
            status=value
        elif record and record.get('phase') in {'complete', 'failed'}:
            status=record['phase']
        elif value is not None:
            status='running'
        else:
            status=record.get('phase','unknown') if record else 'not_found'
        return {'id':run_id,'status':status,'record':record}

class Handler(BaseHTTPRequestHandler):
    server_version=f'UniversalCoder/{__version__}'
    def _send(self,code,obj):
        data=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(code); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(data))); self.send_header('X-Content-Type-Options','nosniff'); self.end_headers(); self.wfile.write(data)
    def _authorized(self):
        if is_loopback(self.server.bind_host) and not self.server.security.require_auth_on_loopback and not self.server.security.auth_token:
            return True
        expected=self.server.security.auth_token
        if token_ok(self.headers.get('Authorization','').removeprefix('Bearer ').strip(), expected): return True
        self._send(401,{'ok':False,'error':'unauthorized'}); return False
    def do_GET(self):
        if self.path=='/health': return self._send(200,{'ok':True,'service':'universal-coder','version':__version__})
        if not self._authorized(): return
        if self.path=='/capabilities': return self._send(200,{'streaming_events':True,'resumable_state':True,'providers':['mock','openai-compatible','openai-responses','anthropic','gemini'],'transport':['http','sse']})
        if self.path.startswith('/runs/'):
            return self._send(200,self.server.manager.status(self.path.split('/',2)[2]))
        self._send(404,{'error':'not found'})
    def _body(self):
        raw=self.headers.get('Content-Length')
        if raw is None: raise ValueError('Content-Length is required')
        try: n=int(raw)
        except ValueError: raise ValueError('invalid Content-Length')
        if n<0 or n>self.server.security.max_request_bytes: raise ValueError('request too large')
        if self.headers.get('Content-Type','').split(';',1)[0].lower() != 'application/json': raise ValueError('Content-Type must be application/json')
        body=json.loads(self.rfile.read(n))
        if not isinstance(body,dict): raise ValueError('JSON object required')
        return body
    def do_POST(self):
        if self.path not in ('/run','/stream'): return self._send(404,{'error':'not found'})
        if not self._authorized(): return
        try:
            body=self._body(); c=Config.from_env();
            for key in ('provider','model','base_url'):
                if key in body: setattr(c,key,body[key])
            # API keys are intentionally taken from the server environment, not accepted over HTTP.
            objective=body['objective']; workspace=body.get('workspace','.')
            if not isinstance(objective,str) or not objective.strip(): raise ValueError('objective must be a non-empty string')
            if len(objective) > self.server.security.max_objective_chars: raise ValueError('objective too long')
            if not isinstance(workspace,str) or not workspace.strip(): raise ValueError('workspace must be a non-empty string')
            if len(workspace) > self.server.security.max_workspace_chars: raise ValueError('workspace path too long')
            if not workspace_allowed(workspace, self.server.security.allowed_workspace_roots):
                raise PermissionError('workspace is outside configured CODER_WORKSPACE_ROOTS')
            if 'sandbox' in body: c.sandbox_mode=body['sandbox']
            c.validate()
            if not is_loopback(self.server.bind_host) and c.sandbox_mode == 'trusted': c.sandbox_mode='isolated'
            events=EventBus()
            if self.path=='/stream':
                self.send_response(200); self.send_header('Content-Type','text/event-stream'); self.send_header('Cache-Control','no-cache'); self.send_header('Connection','keep-alive'); self.send_header('X-Content-Type-Options','nosniff'); self.end_headers()
                def emit(event):
                    try:self.wfile.write(sse(event)); self.wfile.flush()
                    except Exception:pass
                events.subscribe(emit)
                run_id,thread=self.server.manager.start(objective,workspace,c,body.get('verify',True),True,events)
                events.emit('run.accepted',run_id=run_id)
                thread.join(); self.wfile.write(f'event: done\ndata: {json.dumps(self.server.manager.status(run_id))}\n\n'.encode()); self.wfile.flush(); return
            run_id,thread=self.server.manager.start(objective,workspace,c,body.get('verify',True),False,events)
            return self._send(202,{'ok':True,'run_id':run_id,'status_url':f'/runs/{run_id}'})
        except KeyError: self._send(400,{'ok':False,'error':'objective is required'})
        except Exception as e: self._send(400,{'ok':False,'error':f'{type(e).__name__}: {e}'})
    def log_message(self,*args): pass

def serve(host='127.0.0.1',port=8765):
    security=SecurityConfig.from_env()
    if (security.require_auth_on_loopback or not is_loopback(host)) and not security.auth_token:
        raise RuntimeError('CODER_AUTH_TOKEN is required when authentication is enabled or server is non-loopback')
    cert=os.getenv('CODER_TLS_CERT'); key=os.getenv('CODER_TLS_KEY')
    if (cert and not key) or (key and not cert): raise RuntimeError('CODER_TLS_CERT and CODER_TLS_KEY must be supplied together')
    if not is_loopback(host) and not (cert and key):
        raise RuntimeError('non-loopback server requires TLS (CODER_TLS_CERT/CODER_TLS_KEY)')
    roots=security.allowed_workspace_roots or (os.getcwd(),)
    security=SecurityConfig(**{**security.__dict__, 'allowed_workspace_roots': tuple(roots)})
    root_store=RunStore('.universal-coder/runs.json')
    httpd=ThreadingHTTPServer((host,port),Handler); httpd.security=security; httpd.manager=RunManager(root_store,security.max_concurrent_runs); httpd.bind_host=host
    if cert and key:
        ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.minimum_version=ssl.TLSVersion.TLSv1_2; ctx.load_cert_chain(cert,key); httpd.socket=ctx.wrap_socket(httpd.socket,server_side=True)
    httpd.serve_forever()
