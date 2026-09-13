import os, tempfile
from pathlib import Path
import pytest
from universal_coder.workspace import Workspace
from universal_coder.sandbox import CommandExecutor, SandboxConfig
from universal_coder.security import token_ok

def test_token_constant_time_semantics():
    assert token_ok('abc','abc'); assert not token_ok('bad','abc'); assert token_ok('','')

def test_workspace_rejects_symlink(tmp_path):
    ws=Workspace(tmp_path/'w'); outside=tmp_path/'outside'; outside.mkdir()
    (ws.root/'link').symlink_to(outside, target_is_directory=True)
    with pytest.raises(PermissionError): ws.path('link/secret.txt')

def test_trusted_executor_scrubs_credentials(tmp_path, monkeypatch):
    root=tmp_path/'w'; root.mkdir(); monkeypatch.setenv('TEST_API_KEY','should-not-leak')
    ex=CommandExecutor(root,SandboxConfig(mode='trusted'))
    ok,out,err=ex.run("python -c 'import os; print(os.getenv(\"TEST_API_KEY\",\"missing\"))'")
    assert ok and 'missing' in out

def test_workspace_allowlist(tmp_path):
    from universal_coder.security import workspace_allowed
    root = tmp_path / 'allowed'; root.mkdir()
    inside = root / 'repo'; inside.mkdir()
    outside = tmp_path / 'outside'; outside.mkdir()
    assert workspace_allowed(str(inside), (str(root),))
    assert not workspace_allowed(str(outside), (str(root),))


def test_config_validation_rejects_bad_limits(monkeypatch):
    from universal_coder.config import Config
    monkeypatch.setenv('CODER_MAX_STEPS', '0')
    with pytest.raises(ValueError): Config.from_env()


def test_output_limit_is_enforced(tmp_path):
    root=tmp_path/'w'; root.mkdir()
    ex=CommandExecutor(root,SandboxConfig(mode='trusted', max_output=256, timeout=5))
    ok,out,err=ex.run("python -c 'print(\"x\"*100000)'")
    assert not ok and 'output limit exceeded' in err
