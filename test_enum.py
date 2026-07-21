from enum import Enum
from pydantic import BaseModel

class CycleStatus(str, Enum):
    RUNNING = "RUNNING"
    REVERSE_MODE = "REVERSE_MODE"

class CycleState(BaseModel):
    status: CycleStatus

state = CycleState(status=CycleStatus.RUNNING)

if state.status in ["RUNNING", "REVERSE_MODE"]:
    print("Enum in list of strings: True")
else:
    print("Enum in list of strings: False")

if state.status == CycleStatus.RUNNING:
    print("Enum == Enum: True")
else:
    print("Enum == Enum: False")
