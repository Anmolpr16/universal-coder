import json
from universal_coder.events import Event
from universal_coder.gateway import sse

def test_sse_event():
    raw=sse(Event('run.started', {'run_id': 7}))
    assert raw.startswith(b'event: run.started')
    assert json.loads(raw.split(b'data: ',1)[1].split(b'\n',1)[0])['run_id']==7
