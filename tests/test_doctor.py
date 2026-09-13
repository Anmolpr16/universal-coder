from universal_coder.doctor import run_checks

def test_doctor_runs(monkeypatch):
    monkeypatch.setenv("CODER_PROVIDER", "mock")
    checks = run_checks()
    assert any(c.name == "configuration" and c.ok for c in checks)
