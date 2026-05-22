from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import read_json, sha256_file, write_json
from .records import now

VALIDATION_RECIPE_MANIFEST_FILE = "validation_recipe_manifest.json"
VALIDATION_RECIPE_SUMMARY_FILE = "validation_recipe_summary.json"

BOUNDARY_NOTES = [
    "evidence != truth",
    "operational validation != scientific validity",
    "approval record != agent permission",
    "dry-run != physical execution",
    "NeuML handoff != claim promotion",
    "simulated adapter != hardware adapter",
]

RECIPE_INPUT_FILES = [
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
    "replay_plan_manifest.json",
    "audit_index_manifest.json",
    "neuml_handoff_manifest.json",
]

RECIPE_ARTIFACT_FILES = [
    "telemetry/simulated_flow_sensor_A.csv",
]

REQUIRED_RECIPE_COMMAND_IDS = [
    "validate_run",
    "write_state_summary",
    "write_review_summary",
    "write_adapter_summary",
    "write_environment_summary",
    "write_policy_summary",
    "write_telemetry_profile",
    "write_ingestion_preview",
    "write_provenance_summary",
    "write_closeout_summary",
    "write_claim_summary",
    "write_review_packet",
    "write_replay_plan",
    "write_audit_index",
    "write_report",
    "verify_report",
    "export_bundle",
    "verify_bundle",
    "build_neuml_handoff",
]

VALIDATION_COMMAND_TEMPLATES = [
    ("validate_run", "python -m trace_lab.cli validate --run-dir <run_dir>"),
    ("write_state_summary", "python -m trace_lab.cli state-summary --run-dir <run_dir> --write"),
    ("write_review_summary", "python -m trace_lab.cli review-summary --run-dir <run_dir> --write"),
    ("write_adapter_summary", "python -m trace_lab.cli adapter-summary --run-dir <run_dir> --write"),
    ("write_environment_summary", "python -m trace_lab.cli environment-summary --run-dir <run_dir> --write"),
    ("write_policy_summary", "python -m trace_lab.cli policy-summary --run-dir <run_dir> --write"),
    ("write_telemetry_profile", "python -m trace_lab.cli telemetry-profile --run-dir <run_dir> --write"),
    ("write_ingestion_preview", "python -m trace_lab.cli ingestion-preview --run-dir <run_dir> --write"),
    ("write_provenance_summary", "python -m trace_lab.cli provenance-summary --run-dir <run_dir> --write"),
    ("write_closeout_summary", "python -m trace_lab.cli closeout-summary --run-dir <run_dir> --write"),
    ("write_claim_summary", "python -m trace_lab.cli claim-summary --run-dir <run_dir> --write"),
    ("write_review_packet", "python -m trace_lab.cli review-packet --run-dir <run_dir> --write"),
    ("write_replay_plan", "python -m trace_lab.cli replay-plan --run-dir <run_dir> --write"),
    ("write_audit_index", "python -m trace_lab.cli audit-index --run-dir <run_dir> --write"),
    ("write_report", "python -m trace_lab.cli report --run-dir <run_dir> --write"),
    ("verify_report", "python -m trace_lab.cli verify-report --run-dir <run_dir> --write-result"),
    ("export_bundle", "python -m trace_lab.cli export-bundle --run-dir <run_dir> --out <bundle.zip>"),
    ("verify_bundle", "python -m trace_lab.cli verify-bundle --bundle <bundle.zip> --write-result"),
    ("build_neuml_handoff", "python -m trace_lab.cli build-neuml-handoff --run-dir <run_dir>"),
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
        "recipe_scope": "local_validation_checklist_only",
    }
    if path.exists():
        entry["hash"] = sha256_file(path)
        entry["size_bytes"] = path.stat().st_size
        if relative_path.endswith(".json"):
            try:
                entry["record_type"] = read_json(path).get("record_type")
            except Exception as exc:  # noqa: BLE001 - represented as checklist evidence
                entry["recipe_errors"] = [f"Cannot read JSON record: {exc}"]
    return entry


def _command_entry(command_id: str, command_template: str) -> dict[str, Any]:
    return {
        "command_id": command_id,
        "command_template": command_template,
        "command_scope": "local_operator_validation_checklist_only",
        "command_executed": False,
        "expected_result_scope": "operational_shape_check_only",
        "executes_hardware": False,
        "calls_network": False,
        "installs_packages": False,
        "validates_scientific_truth": False,
        "approves_execution": False,
        "promotes_claims": False,
        "promotes_state": False,
    }


def build_validation_recipe_manifest(run_dir: str | Path, *, created_at: str | None = None) -> dict[str, Any]:
    """Build a local validation checklist for a simulated TraceLab run.

    The validation recipe is a command checklist only. It records local commands
    an operator can run to re-check the evidence shape. It does not execute the
    commands, call hardware, call networks, install packages, validate
    scientific truth, approve execution, or promote claims.
    """

    run_dir = Path(run_dir)
    inputs = [_input_entry(run_dir, path, kind="json_record") for path in RECIPE_INPUT_FILES]
    artifacts = [_input_entry(run_dir, path, kind="data_artifact") for path in RECIPE_ARTIFACT_FILES]
    missing = [item["path"] for item in [*inputs, *artifacts] if not item.get("exists")]
    commands = [_command_entry(command_id, template) for command_id, template in VALIDATION_COMMAND_TEMPLATES]

    return {
        "record_type": "validation_recipe_manifest",
        "created_at": created_at or now(),
        "validation_recipe_scope": "local_validation_checklist_only",
        "lifecycle_scope": "operational_simulation_only",
        "validation_recipe_status": "ready_for_local_operator_validation" if not missing else "blocked_by_missing_recipe_inputs",
        "recipe_execution_status": "not_executed",
        "recipe_performed": False,
        "commands_executed": False,
        "automatic_retry_performed": False,
        "network_calls_performed": False,
        "hardware_access_performed": False,
        "package_installation_performed": False,
        "physical_execution_completed": False,
        "scientific_truth_validated": False,
        "approval_granted": False,
        "claims_promoted": False,
        "state_promoted": False,
        "input_count": len(inputs),
        "artifact_count": len(artifacts),
        "command_count": len(commands),
        "recipe_inputs": inputs,
        "recipe_artifacts": artifacts,
        "missing": missing,
        "validation_commands": commands,
        "required_command_ids": REQUIRED_RECIPE_COMMAND_IDS,
        "known_gaps": [
            "Validation recipe is a local command checklist only.",
            "Validation recipe writer does not execute commands.",
            "Validation recipe does not install packages, call networks, call hardware, or validate scientific truth.",
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
            "recipe_performed": False,
            "commands_executed": False,
            "automatic_retry_performed": False,
            "network_calls_performed": False,
            "hardware_access_performed": False,
            "package_installation_performed": False,
            "physical_execution_completed": False,
            "scientific_truth_validated": False,
            "approval_granted": False,
            "state_promoted": False,
            "claims_promoted": False,
        },
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": "Validation recipe is a local operator checklist only; it does not execute commands, validate scientific truth, call hardware, or promote claims.",
    }


def write_validation_recipe_manifest(
    run_dir: str | Path,
    *,
    force: bool = False,
    created_at: str | None = None,
) -> Path:
    run_dir = Path(run_dir)
    path = run_dir / VALIDATION_RECIPE_MANIFEST_FILE
    if path.exists() and not force:
        raise FileExistsError(
            "TraceLab refuses to overwrite validation_recipe_manifest.json without force=True. "
            "This prevents silent replacement of validation checklist evidence."
        )
    write_json(path, build_validation_recipe_manifest(run_dir, created_at=created_at))
    return path


def validate_validation_recipe_manifest(run_dir: str | Path, manifest: dict[str, Any] | None) -> dict[str, list[str]]:
    run_dir = Path(run_dir)
    errors: list[str] = []
    unsafe: list[str] = []

    if manifest is None:
        return {
            "recipe_errors": ["validation_recipe_manifest.json is missing."],
            "unsafe": [],
        }

    if not isinstance(manifest, dict):
        return {
            "recipe_errors": ["validation_recipe_manifest.json is not a JSON object."],
            "unsafe": [],
        }

    if manifest.get("record_type") != "validation_recipe_manifest":
        errors.append("validation_recipe_manifest.json record_type must be 'validation_recipe_manifest'.")
    if manifest.get("validation_recipe_scope") != "local_validation_checklist_only":
        errors.append("validation_recipe_manifest.json validation_recipe_scope must be local_validation_checklist_only.")
    if manifest.get("lifecycle_scope") != "operational_simulation_only":
        errors.append("validation_recipe_manifest.json lifecycle_scope must be operational_simulation_only.")
    if manifest.get("recipe_execution_status") != "not_executed":
        errors.append("validation_recipe_manifest.json recipe_execution_status must be not_executed.")

    for flag in [
        "recipe_performed",
        "commands_executed",
        "automatic_retry_performed",
        "network_calls_performed",
        "hardware_access_performed",
        "package_installation_performed",
        "physical_execution_completed",
        "scientific_truth_validated",
        "approval_granted",
        "state_promoted",
        "claims_promoted",
    ]:
        if manifest.get(flag):
            unsafe.append(f"validation_recipe_manifest.json cannot set {flag}=true.")

    flags = manifest.get("authority_flags", {})
    if not isinstance(flags, dict):
        errors.append("validation_recipe_manifest.json authority_flags must be an object.")
    else:
        for flag in [
            "agent_approved",
            "recipe_performed",
            "commands_executed",
            "automatic_retry_performed",
            "network_calls_performed",
            "hardware_access_performed",
            "package_installation_performed",
            "physical_execution_completed",
            "scientific_truth_validated",
            "approval_granted",
            "state_promoted",
            "claims_promoted",
        ]:
            if flags.get(flag):
                unsafe.append(f"validation_recipe_manifest.json authority_flags cannot set {flag}=true.")

    commands = manifest.get("validation_commands", [])
    if not isinstance(commands, list):
        errors.append("validation_recipe_manifest.json validation_commands must be a list.")
        commands = []

    command_ids = set()
    for index, command in enumerate(commands):
        if not isinstance(command, dict):
            errors.append(f"validation_recipe_manifest.json validation_commands[{index}] is not an object.")
            continue
        command_id = command.get("command_id")
        if isinstance(command_id, str):
            command_ids.add(command_id)
        else:
            errors.append(f"validation_recipe_manifest.json validation_commands[{index}] command_id must be a string.")

        for flag in [
            "command_executed",
            "executes_hardware",
            "calls_network",
            "installs_packages",
            "validates_scientific_truth",
            "approves_execution",
            "promotes_claims",
            "promotes_state",
        ]:
            if command.get(flag):
                unsafe.append(
                    f"validation_recipe_manifest.json validation_commands[{index}] cannot set {flag}=true."
                )

    for required_id in REQUIRED_RECIPE_COMMAND_IDS:
        if required_id not in command_ids:
            errors.append(f"validation_recipe_manifest.json missing required validation command: {required_id}")

    if manifest.get("command_count") != len(commands):
        errors.append("validation_recipe_manifest.json command_count does not match validation_commands length.")

    for field_name in ["recipe_inputs", "recipe_artifacts"]:
        values = manifest.get(field_name, [])
        if not isinstance(values, list):
            errors.append(f"validation_recipe_manifest.json {field_name} must be a list.")
            continue
        for index, item in enumerate(values):
            if not isinstance(item, dict):
                errors.append(f"validation_recipe_manifest.json {field_name}[{index}] is not an object.")
                continue
            candidate, path_error = _safe_relative_path(item.get("path"))
            if path_error:
                errors.append(f"validation_recipe_manifest.json {field_name}[{index}] {path_error}.")
                continue
            artifact_path = run_dir / candidate
            if not artifact_path.exists():
                errors.append(
                    f"validation_recipe_manifest.json {field_name}[{index}] points to missing path: {candidate.as_posix()}"
                )
                continue
            expected_hash = item.get("hash")
            if expected_hash and sha256_file(artifact_path) != expected_hash:
                errors.append(f"validation_recipe_manifest.json hash mismatch for {candidate.as_posix()}")

    return {"recipe_errors": errors, "unsafe": unsafe}


def build_validation_recipe_summary(run_dir: str | Path) -> dict[str, Any]:
    run_dir = Path(run_dir)
    manifest_path = run_dir / VALIDATION_RECIPE_MANIFEST_FILE
    manifest = read_json(manifest_path) if manifest_path.exists() else None
    validation = validate_validation_recipe_manifest(run_dir, manifest)
    recipe_errors = validation.get("recipe_errors", [])
    unsafe = validation.get("unsafe", [])
    commands = manifest.get("validation_commands", []) if isinstance(manifest, dict) else []

    return {
        "record_type": "validation_recipe_summary",
        "created_at": now(),
        "validation_recipe_summary_status": (
            "ready_for_local_operator_validation"
            if not recipe_errors and not unsafe
            else "blocked_by_validation_recipe_errors"
        ),
        "validation_recipe_scope": "local_validation_checklist_only",
        "lifecycle_scope": "operational_simulation_only",
        "command_count": len(commands),
        "required_command_ids": REQUIRED_RECIPE_COMMAND_IDS,
        "recipe_errors": recipe_errors,
        "unsafe": unsafe,
        "authority_flags": {
            "agent_approved": False,
            "recipe_performed": False,
            "commands_executed": False,
            "hardware_access_performed": False,
            "network_calls_performed": False,
            "package_installation_performed": False,
            "physical_execution_completed": False,
            "scientific_truth_validated": False,
            "state_promoted": False,
            "claims_promoted": False,
        },
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": "Validation recipe summary is a local command checklist summary only; it does not execute commands, validate scientific truth, call hardware, or promote claims.",
    }


def write_validation_recipe_summary(run_dir: str | Path, *, force: bool = False) -> Path:
    run_dir = Path(run_dir)
    path = run_dir / VALIDATION_RECIPE_SUMMARY_FILE
    if path.exists() and not force:
        raise FileExistsError(
            "TraceLab refuses to overwrite validation_recipe_summary.json without force=True. "
            "This prevents silent replacement of validation checklist summary evidence."
        )
    write_json(path, build_validation_recipe_summary(run_dir))
    return path
