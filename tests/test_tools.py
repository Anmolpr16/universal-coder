import tempfile
from universal_coder.workspace import Workspace
from universal_coder.tools import ToolRegistry

def test_tools():
    with tempfile.TemporaryDirectory() as d:
        t=ToolRegistry(Workspace(d)); assert t.call('write_file',{'path':'x.txt','content':'ok'}).ok; assert t.call('read_file',{'path':'x.txt'}).output=='ok'
