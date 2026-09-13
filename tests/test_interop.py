import json, sys, textwrap
from pathlib import Path
from universal_coder.interop import StdioToolServer, ToolBroker, ToolGrant
from universal_coder.tools.core import ToolRegistry
from universal_coder.workspace import Workspace

def make_server(tmp_path):
    script=tmp_path/'server.py'
    script.write_text(textwrap.dedent('''
        import json,sys
        for line in sys.stdin:
            m=json.loads(line); method=m.get('method')
            if method=='initialize': r={'protocolVersion':'2025-06-18','capabilities':{'tools':{}},'serverInfo':{'name':'test','version':'1'}}
            elif method=='tools/list': r={'tools':[{'name':'echo','description':'echo','inputSchema':{'type':'object','properties':{'text':{'type':'string'}}}}]}
            elif method=='tools/call': r={'content':[{'type':'text','text':m['params']['arguments']['text']}]}
            else: continue
            if 'id' in m: print(json.dumps({'jsonrpc':'2.0','id':m['id'],'result':r}),flush=True)
    '''))
    return [sys.executable,str(script)]

def test_stdio_tool_server_and_grant(tmp_path):
    s=StdioToolServer(make_server(tmp_path),'test',grant=ToolGrant(allow={'echo'}))
    assert s.tools()[0]['name']=='echo'
    assert s.call('echo',{'text':'ok'})==('ok',True)
    s.close()

def test_broker_denies_external_tool(tmp_path):
    native=ToolRegistry(Workspace(tmp_path))
    b=ToolBroker(native, ToolGrant(allow={'list_files'}))
    s=StdioToolServer(make_server(tmp_path),'test',grant=ToolGrant(allow={'echo'}))
    b.add_server(s)
    r=b.call('echo',{'text':'x'}); assert not r.ok and 'denied' in r.error
    b.close()
