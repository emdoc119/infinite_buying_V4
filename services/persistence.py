import os
import json
from typing import Dict
from domain.models import CycleState

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cycles_db.json")

def load_cycles() -> Dict[str, CycleState]:
    """Load cycles from JSON file on startup."""
    cycles = {}
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                for cycle_id, cycle_data in data.items():
                    try:
                        cycles[cycle_id] = CycleState.parse_obj(cycle_data)
                    except Exception as e:
                        print(f"[Persistence] Failed to load cycle {cycle_id}: {e}")
            print(f"[Persistence] Loaded {len(cycles)} cycles from {DB_PATH}")
        except Exception as e:
            print(f"[Persistence] Error loading DB: {e}")
    return cycles

def save_cycles(cycles: Dict[str, CycleState]):
    """Save all cycles to JSON file."""
    try:
        data = {c_id: json.loads(c_state.json()) for c_id, c_state in cycles.items()}
        # Write to temporary file first then rename to prevent corruption on crash
        tmp_path = DB_PATH + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, DB_PATH)
    except Exception as e:
        print(f"[Persistence] Error saving DB: {e}")
