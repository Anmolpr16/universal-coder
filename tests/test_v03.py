from pathlib import Path
from universal_coder.persistence import RunStore
from universal_coder.approvals import ApprovalPolicy
from universal_coder.git import Git

def test_store(tmp_path):
    s=RunStore(tmp_path/'r.db'); s.save(1,'x','execute',{'a':1}); assert s.get(1)['objective']=='x'
def test_approval():
    assert not ApprovalPolicy(allow_deletes=False).check('delete','x')
def test_git_no_repo(tmp_path):
    g=Git(tmp_path); assert not g.available()
