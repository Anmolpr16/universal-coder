from universal_coder.persistence import RunStore

def test_run_store_resumable(tmp_path):
    store=RunStore(tmp_path / "runs.json")
    store.save("abc","fix bug","execute",{"steps":2})
    assert store.resumable("abc")["objective"] == "fix bug"
    store.save("abc","fix bug","complete",{"steps":3})
    assert store.resumable("abc") is None


def test_run_store_paused_is_resumable(tmp_path):
    store=RunStore(tmp_path / "runs.json")
    store.save("paused","continue work","paused",{"steps":4})
    assert store.resumable("paused")["phase"] == "paused"


def test_agent_cancel_before_first_step(tmp_path):
    import threading
    from universal_coder.agent import Agent
    from universal_coder.workspace import Workspace
    from universal_coder.providers.mock import MockProvider
    from universal_coder.persistence import RunStore
    event=threading.Event(); event.set()
    agent=Agent(MockProvider(), Workspace(tmp_path), store=RunStore(tmp_path / "runs.json"))
    result=agent.run("do nothing", cancel_event=event)
    assert "cancelled" in result.lower()


def test_agent_deadline_pauses_before_execution(tmp_path):
    from universal_coder.agent import Agent
    from universal_coder.workspace import Workspace
    from universal_coder.providers.mock import MockProvider
    from universal_coder.persistence import RunStore
    store=RunStore(tmp_path / "runs.json")
    agent=Agent(MockProvider(), Workspace(tmp_path), store=store)
    result=agent.run("do nothing", deadline_seconds=0)
    assert "deadline" in result.lower()
