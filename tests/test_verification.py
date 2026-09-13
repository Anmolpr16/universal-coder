import tempfile
from universal_coder.workspace import Workspace
from universal_coder.verification import Verifier

def test_verifier_no_project():
    with tempfile.TemporaryDirectory() as d: assert Verifier(Workspace(d)).run().ok is False
