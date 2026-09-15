from pathlib import Path
import subprocess
import universal_coder


def test_release_metadata_and_runtime_assets():
    assert universal_coder.__version__ == "2.1.0"
    assert Path("Dockerfile").is_file()
    assert Path("docker-compose.yml").is_file()
    assert Path("install.sh").is_file()
    assert Path("LICENSE").is_file()
    assert Path(".env.example").is_file()
    assert Path("docs/FINAL_RELEASE.md").is_file()


def test_cli_mock_installable_entrypoint():
    env = dict(__import__("os").environ)
    env["PYTHONPATH"] = str(Path("src").resolve())
    p = subprocess.run(
        ["python", "-m", "universal_coder.cli", "run", "health check", "--provider", "mock", "--no-verify"],
        text=True, capture_output=True, env=env, timeout=20,
    )
    assert p.returncode == 0, p.stderr
    assert "runtime is operational" in p.stdout
