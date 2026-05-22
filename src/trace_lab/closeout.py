from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import read_json, sha256_file, write_json
from .records import now

CLOSEOUT_FILE = "run_closeout_manifest.json"
CLOSEOUT_SUMMARY_FILE = "run_closeout_summary.json"

BOUNDARY_NOTES = [
    "evidence != truth",
    "operational validation != scientific validity",
    "approval record != agent permission",
    "dry-run != physical execution",
    "NeuML handoff != claim promotion",
    "simulated adapter != hardware adapter",
]

CLOSEOUT_REQUIRED_RECORDS = [
    "experiment_request.json",
    "run_plan.json",
    "adapter_capability_manifest.json",
    "approval_record.json",
    "dry_run_record.json",
    "adapter_action_record.json",
    "telemetry_manifest.json",
    "telemetry_profile_manifest.json",
    "ingestion_preview_manifest.json",
    "provenance_manifest.json",
    "validation_record.json",
    "lab_run_record.json",
    "evidence_packet_manifest.json",
    "review_record.json",
    "run_state_chain.json",
    "runtime_environment_manifest.json",
    "execution_policy_manifest.json",
    "neuml_handoff_manifest.json",
]

CLOSEOUT_REQUIRED_ARTIFACTS = ["telemetry/simulated_flow_sensor_A.csv"]


def _safe_relative_path(raw_path: object) -> tuple[Path | None, str | None]:
    if not raw_path or not isinstance(raw_path, str):
        return None, "path is missing or not a string"

    candidate = Path(raw_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None, f"path must stay inside run directory: {raw_path}"

    return candidate, None


def _entry(run_dir: Path, relative_path: str, *, kind: str) -> dict[str, Any]:
    path = run_dir / relative_path
    entry: dict[str, Any] = {
        "path": relative_path,
        "kind": kind,
        "exists": path.exists(),
        "closeout_scope": "operational_trace_closeout_only",
    }
    if path.exists():
        entry["hash"] = sha256_file(path)
        if relative_path.endswith(".json"):
            try:
                entry["record_type"] = read_json(path).get("record_type")
            except Exception as exc:  # noqa: BLE001 - represented as closeout evidence
                entry["closeout_errors"] = [f"Cannot read JSON record: {exc}"]
    return entry


def build_run_closeout_manifest(run_dir: str | Path, *, created_at: str | None = None) -> dict[str, Any]:
    """Build a local run closeout manifest for the simulated trace.

    This manifest is a mechanical stop-line record. It says the generated
    simulated trace has enough local evidence for operator review/export. It
    does not approve the experiment, complete human review, validate scientific
    truth, execute hardware, or promote claims.
    """

    run_dir = Path(run_dir)
    records = [_entry(run_dir, path, kind="json_record") for path in CLOSEOUT_REQUIRED_RECORDS]
    artifacts = [_entry(run_dir, path, kind="data_artifact") for path in CLOSEOUT_REQUIRED_ARTIFACTS]
    missing = [item["path"] for item in [*records, *artifacts] if not item.get("exists")]

    return {
        "record_type": "run_closeout_manifest",
        "created_at": created_at or now(),
        "closeout_scope": "operational_trace_closeout_only",
        "closeout_status": "ready_for_operator_review_and_local_export" if not missing else "blocked_by_missing_trace_evidence",
        "lifecycle_scope": "operational_simulation_only",
        "record_count": len(records),
        "artifact_count": len(artifacts),
        "records": records,
        "artifacts": artifacts,
        "missing": missing,
        "required_next_actions": [
            "operator_trace_review",
            "optional_local_export_verification",
            "optional_external_ingestion_outside_tracelab",
        ],
        "known_gaps": [
            "Closeout is a local operational stop-line only.",
            "Human review is still required before durable claims.",
            "No scientific truth validation is performed.",
            "No hardware access or physical execution is performed.",
        ],
        "not_proven_claims": [
            "scientific truth",
            "human review completion",
            "hardware readiness",
            "claim promotion",
        ],
        "authority_flags": {
            "agent_approved": False,
            "human_review_completed": False,
            "physical_execution_completed": False,
            "scientific_truth_validated": False,
            "state_promoted": False,
            "claims_promoted": False,
            "hardware_access_performed": False,
            "network_calls_performed": False,
            "package_installation_performed": False,
            "automatic_retry_performed": False,
        },
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": "Run closeout is an operational trace stop-line only; it does not validate scientific truth, complete human review, execute hardware, or promote claims.",
    }


def write_run_closeout_manifest(
    run_dir: str | Path,
    *,
    force: bool = False,
    created_at: str | None = None,
) -> Path:
    run_dir = Path(run_dir)
    path = run_dir / CLOSEOUT_FILE
    if path.exists() and not force:
        raise FileExistsError(
            "TraceLab refuses to overwrite run_closeout_manifest.json without force=True. "
            "This prevents silent replacement of closeout evidence."
        )
    write_json(path, build_run_closeout_manifest(run_dir, created_at=created_at))
    return path


def validate_run_closeout_manifest(
    run_dir: str | Path,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run_dir = Path(run_dir)
    errors: list[str] = []
    unsafe: list[str] = []

    if manifest is None:
        path = run_dir / CLOSEOUT_FILE
        if not path.exists():
            return {
                "record_type": "run_closeout_validation",
                "closeout_validation_status": "failed_closeout_checks",
                "closeout_errors": [f"Missing run closeout manifest: {CLOSEOUT_FILE}"],
                "unsafe": [],
                "authority_note": "Run closeout validation checks local operational stop-line evidence only.",
            }
        try:
            manifest = read_json(path)
        except Exception as exc:  # noqa: BLE001
            return {
                "record_type": "run_closeout_validation",
                "closeout_validation_status": "failed_closeout_checks",
                "closeout_errors": [f"Cannot read run closeout manifest: {exc}"],
                "unsafe": [],
                "authority_note": "Run closeout validation checks local operational stop-line evidence only.",
            }

    if manifest.get("record_type") != "run_closeout_manifest":
        errors.append("run_closeout_manifest.json record_type must be run_closeout_manifest.")
    if manifest.get("closeout_scope") != "operational_trace_closeout_only":
        errors.append("run_closeout_manifest.json closeout_scope must be operational_trace_closeout_only.")
    if manifest.get("lifecycle_scope") != "operational_simulation_only":
        errors.append("run_closeout_manifest.json lifecycle_scope must be operational_simulation_only.")
    if manifest.get("closeout_status") not in {
        "ready_for_operator_review_and_local_export",
        "blocked_by_missing_trace_evidence",
    }:
        errors.append("run_closeout_manifest.json closeout_status has an unknown value.")

    flags = manifest.get("authority_flags", {})
    for flag_name in (
        "agent_approved",
        "human_review_completed",
        "physical_execution_completed",
        "scientific_truth_validated",
        "state_promoted",
        "claims_promoted",
        "hardware_access_performed",
        "network_calls_performed",
        "package_installation_performed",
        "automatic_retry_performed",
    ):
        if flags.get(flag_name):
            unsafe.append(f"run_closeout_manifest.json cannot set {flag_name}=true in v0.1 simulation.")

    for section_name, required_paths in [
        ("records", CLOSEOUT_REQUIRED_RECORDS),
        ("artifacts", CLOSEOUT_REQUIRED_ARTIFACTS),
    ]:
        items = manifest.get(section_name, [])
        if not isinstance(items, list):
            errors.append(f"run_closeout_manifest.json {section_name} must be a list.")
            continue

        seen_paths = {item.get("path") for item in items if isinstance(item, dict)}
        for required_path in required_paths:
            if required_path not in seen_paths:
                errors.append(f"run_closeout_manifest.json {section_name} missing required path: {required_path}")

        for index, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"run_closeout_manifest.json {section_name}[{index}] is not an object.")
                continue

            candidate, path_error = _safe_relative_path(item.get("path"))
            if path_error:
                errors.append(f"run_closeout_manifest.json {section_name}[{index}] {path_error}.")
                continue

            path = run_dir / candidate
            if not path.exists():
                errors.append(f"run_closeout_manifest.json {section_name}[{index}] points to missing path: {candidate.as_posix()}")
                continue

            expected_hash = item.get("hash")
            if not expected_hash:
                errors.append(f"run_closeout_manifest.json {section_name}[{index}] has no hash: {candidate.as_posix()}")
            elif sha256_file(path) != expected_hash:
                errors.append(f"run_closeout_manifest.json {section_name}[{index}] hash mismatch: {candidate.as_posix()}")

            if item.get("closeout_scope") != "operational_trace_closeout_only":
                errors.append(f"run_closeout_manifest.json {section_name}[{index}] closeout_scope must be operational_trace_closeout_only.")

    if manifest.get("missing"):
        errors.append(f"run_closeout_manifest.json declares missing closeout paths: {manifest.get('missing')}")

    boundary_notes = manifest.get("boundary_notes", [])
    for note in BOUNDARY_NOTES:
        if note not in boundary_notes:
            errors.append(f"run_closeout_manifest.json missing boundary note: {note}")

    return {
        "record_type": "run_closeout_validation",
        "closeout_validation_status": "passed_closeout_checks" if not errors and not unsafe else "failed_closeout_checks",
        "closeout_errors": errors,
        "unsafe": unsafe,
        "authority_note": "Run closeout validation checks local operational stop-line evidence only; it does not validate scientific truth or promote claims.",
    }


def build_run_closeout_summary(run_dir: str | Path) -> dict[str, Any]:
    run_dir = Path(run_dir)
    manifest_path = run_dir / CLOSEOUT_FILE
    if manifest_path.exists():
        try:
            manifest = read_json(manifest_path)
        except Exception:  # noqa: BLE001
            manifest = {}
    else:
        manifest = build_run_closeout_manifest(run_dir)

    validation = validate_run_closeout_manifest(run_dir, manifest)
    return {
        "record_type": "run_closeout_summary",
        "created_at": now(),
        "closeout_scope": "operational_trace_closeout_only",
        "lifecycle_scope": "operational_simulation_only",
        "closeout_summary_status": (
            "ready_for_operator_review_and_local_export"
            if validation.get("closeout_validation_status") == "passed_closeout_checks"
            else "blocked_by_closeout_errors"
        ),
        "record_count": manifest.get("record_count", 0),
        "artifact_count": manifest.get("artifact_count", 0),
        "closeout_errors": validation.get("closeout_errors", []),
        "unsafe": validation.get("unsafe", []),
        "required_next_actions": [
            "operator_trace_review",
            "optional_local_export_verification",
            "optional_external_ingestion_outside_tracelab",
        ],
        "authority_flags": {
            "agent_approved": False,
            "human_review_completed": False,
            "physical_execution_completed": False,
            "scientific_truth_validated": False,
            "state_promoted": False,
            "claims_promoted": False,
            "hardware_access_performed": False,
            "network_calls_performed": False,
            "package_installation_performed": False,
            "automatic_retry_performed": False,
        },
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": "Run closeout summary is an operator-facing stop-line view only; it does not validate scientific truth, complete human review, execute hardware, or promote claims.",
    }


def write_run_closeout_summary(run_dir: str | Path, *, force: bool = False) -> Path:
    run_dir = Path(run_dir)
    path = run_dir / CLOSEOUT_SUMMARY_FILE
    if path.exists() and not force:
        raise FileExistsError(
            "TraceLab refuses to overwrite run_closeout_summary.json without force=True. "
            "This prevents silent replacement of closeout summary evidence."
        )
    write_json(path, build_run_closeout_summary(run_dir))
    return path
