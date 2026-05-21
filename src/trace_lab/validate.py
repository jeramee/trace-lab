from __future__ import annotations
from pathlib import Path
import json

REQUIRED = [
    "experiment_request.json",
    "run_plan.json",
    "adapter_capability_manifest.json",
    "approval_record.json",
    "dry_run_record.json",
    "adapter_action_record.json",
    "telemetry_manifest.json",
    "validation_record.json",
    "lab_run_record.json",
    "evidence_packet_manifest.json",
    "review_record.json",
]

def validate_run(run_dir: str | Path) -> dict:
    run_dir = Path(run_dir)
    missing = [name for name in REQUIRED if not (run_dir / name).exists()]
    json_errors = []
    parsed = {}
    for path in run_dir.glob("*.json"):
        try:
            parsed[path.name] = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            json_errors.append(f"{path.name}: {exc}")
    unsafe = []
    action = parsed.get("adapter_action_record.json", {})
    if action.get("physical_execution_completed"):
        unsafe.append("Physical execution is not allowed in v0.1 simulation.")
    status = "passed_operational_checks" if not missing and not json_errors and not unsafe else "failed_operational_checks"
    return {
        "record_type": "trace_lab_validation_result",
        "validation_status": status,
        "missing": missing,
        "json_errors": json_errors,
        "unsafe": unsafe,
        "authority_note": "Operational checks are not scientific validation.",
    }
