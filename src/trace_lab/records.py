from __future__ import annotations
from datetime import datetime, timezone

def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def default_authority_flags() -> dict:
    return {
        "correctness_proven": False,
        "state_promoted": False,
        "physical_execution_completed": False,
        "safety_validated": False,
        "human_approved": False,
    }
