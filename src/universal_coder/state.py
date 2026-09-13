from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import json, time

class Phase(str,Enum): INIT='init'; CONTEXT='context'; EXECUTE='execute'; VERIFY='verify'; COMPLETE='complete'; FAILED='failed'
@dataclass
class RunState:
    objective: str
    phase: Phase=Phase.INIT
    steps: int=0
    events: list[dict[str,Any]]=field(default_factory=list)
    result: str=''
    def dump(self): return json.dumps(self.__dict__ | {'phase':self.phase.value},default=str)
