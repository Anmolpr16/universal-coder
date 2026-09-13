import tempfile, pytest
from universal_coder.workspace import Workspace

def test_workspace_boundary_and_io():
    with tempfile.TemporaryDirectory() as d:
        w=Workspace(d); w.write('a.txt','hello'); assert w.read('a.txt')=='hello'
        with pytest.raises(PermissionError): w.path('../escape')
