from __future__ import annotations
import json, time, threading, os
from pathlib import Path

class RunStore:
    """Small atomic JSON store. Safe for multiple threads in one process."""
    def __init__(self, path: str|Path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True); self._lock=threading.RLock()
        if not self.path.exists(): self._write({})
    def _read(self):
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                raise ValueError('run store must contain a JSON object')
            return data
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as e:
            raise RuntimeError(f'run store is corrupted: {e}') from e
    def _write(self,data):
        tmp=self.path.with_suffix(self.path.suffix+'.tmp')
        with tmp.open('w', encoding='utf-8') as f:
            json.dump(data, f, default=str, indent=2)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                # Some mobile/virtual filesystems do not expose fsync; the atomic
                # rename below still prevents readers from seeing partial JSON.
                pass
        tmp.replace(self.path)
    def save(self,run_id,objective,phase,state):
        with self._lock:
            data=self._read(); key=str(run_id); now=time.time(); old=data.get(key,{})
            data[key]={'id':run_id,'objective':objective,'phase':phase,'state':state,'created':old.get('created',now),'updated':now}; self._write(data)
    def get(self,run_id):
        with self._lock:return self._read().get(str(run_id))
    def resumable(self, run_id):
        record = self.get(run_id)
        if not record:
            return None
        return record if record.get('phase') not in {'complete', 'failed'} else None
    def recent(self,limit=20):
        with self._lock:return sorted(self._read().values(),key=lambda x:x.get('updated',0),reverse=True)[:limit]
