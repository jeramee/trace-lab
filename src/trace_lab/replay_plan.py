from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import read_json, sha256_file, write_json
from .records import now

REPLAY_PLAN_FILE = "replay_plan_manifest.json"
REPLAY_PLAN_SUMMARY_FILE = "replay_plan_summary.json"

BOUNDARY_NOTES = [
    "evidence != truth",
    "operational validation != scientific validity",
    "approval record != agent permission",
    "dry-run != physical execution",
    "NeuML handoff != claim promotion",
    "simulated adapter != hardware adapter",
]

REPLAY_INPUT_FILES = [
    "experiment_request.json",
    "run_plan.json",
    "adapter_capability_manifest.json",
    "approval_record.json",
    "dry_run_record.json",
    "adapter_action_record.json",
    "telemetry_manifest.json",
    "telemetry_profile_manifest.json",
    "validation_record.json",
    "lab_run_record.json",
    "evidence_packet_manifest.json",
    "review_record.json",
    "run_state_chain.json",
    "runtime_environment_manifest.json",
    "execution_policy_manifest.json",
    "ingestion_preview_manifest.json",
    "provenance_manifest.json",
    "run_closeout_manifest.json",
    "claim_ledger_manifest.json",
    "operator_review_packet_manifest.json",
    "neuml_handoff_manifest.json",
]

REPLAY_ARTIFACT_FILES = ["telemetry/simulated_flow_sensor_A.csv"]

REPLAY_STEP_TEMPLATES = [
    {
        "step_id": "validate_run",
        "command_template": "python -m trace_lab.cli validate --run-dir <run_dir>",
        "step_scope": "local_operator_replay_checklist_only",
        "executes_hardware": False,
        "validates_scientific_truth": False,
        "promotes_claims": False,
    },
    {
        "step_id": "write_state_summary",
        "command_template": "python -m trace_lab.cli state-summary --run-dir <run_dir> --write",
        "step_scope": "local_operator_replay_checklist_only",
        "executes_hardware": False,
        "validates_scientific_truth": False,
        "promotes_claims": False,
    },
    {
        "step_id": "write_operator_review_packet",
        "command_template": "python -m trace_lab.cli review-packet --run-dir <run_dir> --write",
        "step_scope": "local_operator_replay_checklist_only",
        "executes_hardware": False,
        "validates_scientific_truth": False,
        "promotes_claims": False,
    },
    {
        "step_id": "write_report",
        "command_template": "python -m trace_lab.cli report --run-dir <run_dir> --write",
        "step_scope": "local_operator_replay_checklist_only",
        "executes_hardware": False,
        "validates_scientific_truth": False,
        "promotes_claims": False,
    },
    {
        "step_id": "export_bundle",
        "command_template": "python -m trace_lab.cli export-bundle --run-dir <run_dir> --out <bundle.zip>",
        "step_scope": "local_operator_replay_checklist_only",
        "executes_hardware": False,
        "validates_scientific_truth": False,
        "promotes_claims": False,
    },
    {
        "step_id": "verify_bundle",
        "command_template": "python -m trace_lab.cli verify-bundle --bundle <bundle.zip>",
        "step_scope": "local_operator_replay_checklist_only",
        "executes_hardware": False,
        "validates_scientific_truth": False,
        "promotes_claims": False,
    },
]


def _safe_relative_path(raw_path: object) -> tuple[Path | None, str | None]:
    if not raw_path or not isinstance(raw_path, str):
        return None, "path is missing or not a string"
    candidate = Path(raw_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None, f"path must stay inside run directory: {raw_path}"
    return candidate, None


def _input_entry(run_dir: Path, relative_path: str, *, kind: str) -> dict[str, Any]:
    path = run_dir / relative_path
    entry: dict[str, Any] = {
        "path": relative_path,
        "kind": kind,
        "exists": path.exists(),
        "replay_scope": "local_operator_replay_checklist_only",
    }
    if path.exists():
        entry["hash"] = sha256_file(path)
        entry["size_bytes"] = path.stat().st_size
        if relative_path.endswith(".json"):
            try:
                entry["record_type"] = read_json(path).get("record_type")
            except Exception as exc:  # noqa: BLE001 - represented as replay plan evidence
                entry["replay_errors"] = [f"Cannot read JSON record: {exc}"]
    return entry


def build_replay_plan_manifest(run_dir: str | Path, *, created_at: str | None = None) -> dict[str, Any]:
    """Build a local replay checklist for a simulated TraceLab run.

    The replay plan is a bounded operator checklist. It records local commands
    and required inputs that can help reproduce the simulated evidence shape. It
    does not execute the commands, call hardware, call networks, validate
    scientific truth, retry hidden actions, or promote claims.
    """

    run_dir = Path(run_dir)
    inputs = [_input_entry(run_dir, path, kind="json_record") for path in REPLAY_INPUT_FILES]
    artifacts = [_input_entry(run_dir, path, kind="data_artifact") for path in REPLAY_ARTIFACT_FILES]
    missing = [item["path"] for item in [*inputs, *artifacts] if not item.get("exists")]

    return {
        "record_type": "replay_plan_manifest",
        "created_at": created_at or now(),
        "replay_plan_scope": "local_operator_replay_checklist_only",
        "lifecycle_scope": "operational_simulation_only",
        "replay_plan_status": "ready_for_local_operator_replay" if not missing else "blocked_by_missing_replay_inputs",
        "replay_execution_status": "not_executed",
        "replay_performed": False,
        "automatic_retry_performed": False,
        "network_calls_performed": False,
        "hardware_access_performed": False,
        "package_installation_performed": False,
        "physical_execution_completed": False,
        "scientific_truth_validated": False,
        "claims_promoted": False,
        "state_promoted": False,
        "input_count": len(inputs),
        "artifact_count": len(artifacts),
        "replay_inputs": inputs,
        "replay_artifacts": artifacts,
        "missing": missing,
        "replay_steps": REPLAY_STEP_TEMPLATES,
        "known_gaps": [
            "Replay plan is a local checklist only.",
            "Replay commands are not executed by the manifest writer.",
            "No hardware, network, package install, scientific truth validation, or claim promotion is performed.",
        ],
        "not_proven_claims": [
            "scientific truth",
            "physical safety validation",
            "hardware readiness",
            "human review completion",
            "durable claim promotion",
            "external ingestion completed",
        ],
        "authority_flags": {
            "agent_approved": False,
            "replay_performed": False,
            "automatic_retry_performed": False,
            "network_calls_performed": False,
            "hardware_access_performed": False,
            "package_installation_performed": False,
            "physical_execution_completed": False,
            "scientific_truth_validated": False,
            "state_promoted": False,
            "claims_promoted": False,
        },
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": "Replay plan is a local operator checklist only; it does not execute replay, validate scientific truth, call hardware, or promote claims.",
    }


def write_replay_plan_manifest(
    run_dir: str | Path,
    *,
    force: bool = False,
    created_at: str | None = None,
) -> Path:
    run_dir = Path(run_dir)
    path = run_dir / REPLAY_PLAN_FILE
    if path.exists() and not force:
        raise FileExistsError(
            "TraceLab refuses to overwrite replay_plan_manifest.json without force=True. "
            "This prevents silent replacement of replay checklist evidence."
        )
    write_json(path, build_replay_plan_manifest(run_dir, created_at=created_at))
    return path


def validate_replay_plan_manifest(
    run_dir: str | Path,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run_dir = Path(run_dir)
    errors: list[str] = []
    unsafe: list[str] = []

    if manifest is None:
        path = run_dir / REPLAY_PLAN_FILE
        if not path.exists():
            return {
                "record_type": "replay_plan_validation",
                "replay_plan_validation_status": "failed_replay_plan_checks",
                "replay_errors": [f"Missing replay plan manifest: {REPLAY_PLAN_FILE}"],
                "unsafe": [],
                "authority_note": "Replay plan validation checks local replay-checklist evidence only.",
            }
        try:
            manifest = read_json(path)
        except Exception as exc:  # noqa: BLE001
            return {
                "record_type": "replay_plan_validation",
                "replay_plan_validation_status": "failed_replay_plan_checks",
                "replay_errors": [f"Cannot read replay plan manifest: {exc}"],
                "unsafe": [],
                "authority_note": "Replay plan validation checks local replay-checklist evidence only.",
            }

    if manifest.get("record_type") != "replay_plan_manifest":
        errors.append("replay_plan_manifest.json record_type must be replay_plan_manifest.")
    if manifest.get("replay_plan_scope") != "local_operator_replay_checklist_only":
        errors.append("replay_plan_manifest.json replay_plan_scope must be local_operator_replay_checklist_only.")
    if manifest.get("lifecycle_scope") != "operational_simulation_only":
        errors.append("replay_plan_manifest.json lifecycle_scope must be operational_simulation_only.")
    if manifest.get("replay_execution_status") != "not_executed":
        unsafe.append("replay_plan_manifest.json cannot claim replay execution in v0.1.")

    for field in [
        "replay_performed",
        "automatic_retry_performed",
        "network_calls_performed",
        "hardware_access_performed",
        "package_installation_performed",
        "physical_execution_completed",
        "scientific_truth_validated",
        "claims_promoted",
        "state_promoted",
    ]:
        if manifest.get(field):
            unsafe.append(f"replay_plan_manifest.json cannot set {field}=true in v0.1 simulation.")

    flags = manifest.get("authority_flags", {})
    for flag_name in (
        "agent_approved",
        "replay_performed",
        "automatic_retry_performed",
        "network_calls_performed",
        "hardware_access_performed",
        "package_installation_performed",
        "physical_execution_completed",
        "scientific_truth_validated",
        "state_promoted",
        "claims_promoted",
    ):
        if flags.get(flag_name):
            unsafe.append(f"replay_plan_manifest.json cannot set authority flag {flag_name}=true in v0.1 simulation.")

    for section_name, required_paths in [
        ("replay_inputs", REPLAY_INPUT_FILES),
        ("replay_artifacts", REPLAY_ARTIFACT_FILES),
    ]:
        items = manifest.get(section_name, [])
        if not isinstance(items, list):
            errors.append(f"replay_plan_manifest.json {section_name} must be a list.")
            continue
        seen_paths = {item.get("path") for item in items if isinstance(item, dict)}
        for required_path in required_paths:
            if required_path not in seen_paths:
                errors.append(f"replay_plan_manifest.json {section_name} missing required path: {required_path}")
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"replay_plan_manifest.json {section_name}[{index}] is not an object.")
                continue
            candidate, path_error = _safe_relative_path(item.get("path"))
            if path_error:
                errors.append(f"replay_plan_manifest.json {section_name}[{index}] {path_error}.")
                continue
            path = run_dir / candidate
            if not path.exists():
                errors.append(f"replay_plan_manifest.json {section_name}[{index}] points to missing path: {candidate.as_posix()}")
                continue
            expected_hash = item.get("hash")
            if not expected_hash:
                errors.append(f"replay_plan_manifest.json {section_name}[{index}] has no hash: {candidate.as_posix()}")
            elif sha256_file(path) != expected_hash:
                errors.append(f"replay_plan_manifest.json {section_name}[{index}] hash mismatch: {candidate.as_posix()}")
            if item.get("replay_scope") != "local_operator_replay_checklist_only":
                errors.append(f"replay_plan_manifest.json {section_name}[{index}] replay_scope must be local_operator_replay_checklist_only.")

    steps = manifest.get("replay_steps", [])
    if not isinstance(steps, list) or not steps:
        errors.append("replay_plan_manifest.json replay_steps must be a non-empty list.")
    else:
        for index, step in enumerate(steps):
            if not isinstance(step, dict):
                errors.append(f"replay_plan_manifest.json replay_steps[{index}] is not an object.")
                continue
            command = step.get("command_template")
            if not isinstance(command, str) or not command.startswith("python -m trace_lab.cli "):
                errors.append(f"replay_plan_manifest.json replay_steps[{index}] command_template must use python -m trace_lab.cli.")
            for flag in ("executes_hardware", "validates_scientific_truth", "promotes_claims"):
                if step.get(flag):
                    unsafe.append(f"replay_plan_manifest.json replay_steps[{index}] cannot set {flag}=true.")

    if manifest.get("missing"):
        errors.append(f"replay_plan_manifest.json declares missing replay paths: {manifest.get('missing')}")

    for note in BOUNDARY_NOTES:
        if note not in manifest.get("boundary_notes", []):
            errors.append(f"replay_plan_manifest.json missing boundary note: {note}")

    return {
        "record_type": "replay_plan_validation",
        "replay_plan_validation_status": "passed_replay_plan_checks" if not errors and not unsafe else "failed_replay_plan_checks",
        "replay_errors": errors,
        "unsafe": unsafe,
        "authority_note": "Replay plan validation checks local replay-checklist evidence only; it does not execute replay, validate scientific truth, or promote claims.",
    }


def build_replay_plan_summary(run_dir: str | Path) -> dict[str, Any]:
    run_dir = Path(run_dir)
    manifest_path = run_dir / REPLAY_PLAN_FILE
    manifest = read_json(manifest_path) if manifest_path.exists() else None
    validation = validate_replay_plan_manifest(run_dir, manifest)

    return {
        "record_type": "replay_plan_summary",
        "created_at": now(),
        "replay_plan_scope": "local_operator_replay_checklist_only",
        "lifecycle_scope": "operational_simulation_only",
        "replay_plan_summary_status": (
            "ready_for_local_operator_replay"
            if not validation["replay_errors"] and not validation["unsafe"]
            else "blocked_by_replay_plan_errors"
        ),
        "replay_execution_status": "not_executed",
        "replay_performed": False,
        "automatic_retry_performed": False,
        "input_count": len(manifest.get("replay_inputs", [])) if isinstance(manifest, dict) else 0,
        "artifact_count": len(manifest.get("replay_artifacts", [])) if isinstance(manifest, dict) else 0,
        "replay_step_count": len(manifest.get("replay_steps", [])) if isinstance(manifest, dict) else 0,
        "replay_errors": validation["replay_errors"],
        "unsafe": validation["unsafe"],
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": "Replay plan summary is a local operator checklist view only; it does not execute replay, validate truth, call hardware, or promote claims.",
    }


def write_replay_plan_summary(
    run_dir: str | Path,
    *,
    force: bool = False,
) -> Path:
    run_dir = Path(run_dir)
    path = run_dir / REPLAY_PLAN_SUMMARY_FILE
    if path.exists() and not force:
        raise FileExistsError(
            "TraceLab refuses to overwrite replay_plan_summary.json without force=True. "
            "This prevents silent replacement of replay checklist summary evidence."
        )
    write_json(path, build_replay_plan_summary(run_dir))
    return path
