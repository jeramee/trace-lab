from __future__ import annotations
from pathlib import Path
import json
from .io import sha256_file

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
    "neuml_handoff_manifest.json",
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
    telemetry_errors = []
    telemetry = parsed.get("telemetry_manifest.json", {})
    for index, item in enumerate(telemetry.get("data_files", [])):
        rel_path = item.get("path") if isinstance(item, dict) else None
        if not rel_path or not isinstance(rel_path, str):
            telemetry_errors.append(f"telemetry_manifest.json data_files[{index}] has no relative path.")
            continue

        candidate = Path(rel_path)
        if candidate.is_absolute() or ".." in candidate.parts:
            telemetry_errors.append(f"Telemetry path must stay inside run directory: {rel_path}")
            continue

        telemetry_path = run_dir / candidate
        if not telemetry_path.exists():
            telemetry_errors.append(f"Telemetry file missing: {rel_path}")
            continue

        expected_hash = item.get("hash")
        if expected_hash and sha256_file(telemetry_path) != expected_hash:
            telemetry_errors.append(f"Telemetry file hash mismatch: {rel_path}")

    missing_channels = telemetry.get("missing_channels", [])
    if missing_channels:
        telemetry_errors.append(f"Telemetry manifest declares missing channels: {missing_channels}")

    action = parsed.get("adapter_action_record.json", {})
    if action.get("physical_execution_completed"):
        unsafe.append("Physical execution is not allowed in v0.1 simulation.")

    capability = parsed.get("adapter_capability_manifest.json", {})
    if capability.get("can_execute_physical_actions"):
        unsafe.append("Adapters cannot claim physical execution capability in v0.1 simulation.")

    handoff = parsed.get("neuml_handoff_manifest.json", {})
    handoff_flags = handoff.get("authority_flags", {})
    unsafe_handoff_flags = [
        "agent_approved",
        "scientific_truth_validated",
        "physical_execution_completed",
        "state_promoted",
        "handoff_promotes_claims",
    ]
    for flag in unsafe_handoff_flags:
        if handoff_flags.get(flag):
            unsafe.append(f"NeuML handoff cannot set {flag}=true in v0.1 simulation.")

    status = (
        "passed_operational_checks"
        if not missing and not json_errors and not unsafe and not telemetry_errors
        else "failed_operational_checks"
    )
    return {
        "record_type": "trace_lab_validation_result",
        "validation_status": status,
        "missing": missing,
        "json_errors": json_errors,
        "telemetry_errors": telemetry_errors,
        "unsafe": unsafe,
        "authority_note": "Operational checks are not scientific validation.",
    }
