import subprocess
from universal_coder.worktrees import WorktreeManager
from universal_coder.integration import Integrator


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=True)


def test_worktree_create_and_diff(tmp_path):
    git(tmp_path, "init")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "a.txt").write_text("one\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "base")
    with WorktreeManager(tmp_path) as manager:
        assert manager.supported()
        wt = manager.create("coder")
        (wt.path / "a.txt").write_text("two\n")
        diff = manager.diff(wt)
        assert "two" in diff


def test_integrator_applies_patch(tmp_path):
    git(tmp_path, "init")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "a.txt").write_text("one\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "base")
    diff = subprocess.run(["git", "diff", "HEAD"], cwd=tmp_path, text=True, capture_output=True).stdout
    # Create a patch through git's object model.
    (tmp_path / "a.txt").write_text("two\n")
    diff = git(tmp_path, "diff").stdout
    git(tmp_path, "checkout", "--", "a.txt")
    result = Integrator(tmp_path).apply_diff(diff)
    assert result.ok
    assert (tmp_path / "a.txt").read_text() == "two\n"
