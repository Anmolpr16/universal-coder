import subprocess
from universal_coder.autonomous import AutonomousPipeline
from universal_coder.providers.mock import MockProvider


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=True)


def test_autonomous_pipeline_falls_back_safely(tmp_path):
    git(tmp_path, "init")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "main.py").write_text("print('ok')\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "base")
    result = AutonomousPipeline(lambda role: MockProvider(), tmp_path, max_steps=2).run("inspect the project", verify=False)
    assert result.ok
    assert result.selected_role in {"coder", "tester", "reviewer"}
    assert result.plan.tasks


def test_worktree_diff_includes_new_files(tmp_path):
    from universal_coder.worktrees import WorktreeManager
    git(tmp_path, "init")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "a.txt").write_text("base\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "base")
    with WorktreeManager(tmp_path) as manager:
        wt = manager.create("coder")
        (wt.path / "new.py").write_text("print('new')\n")
        diff = manager.diff(wt)
        assert "new.py" in diff
        assert "print('new')" in diff
