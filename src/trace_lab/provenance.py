from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import read_json, sha256_file, write_json
from .records import now

PROVENANCE_FILE = "provenance_manifest.json"
PROVENANCE_SUMMARY_FILE = "provenance_summary.json"

BOUNDARY_NOTES = [
    "evidence != truth",
    "operational validation != scientific validity",
    "approval record != agent permission",
    "dry-run != physical execution",
    "NeuML handoff != claim promotion",
    "simulated adapter != hardware adapter",
]

PROVENANCE_REQUIRED_RECORDS = [
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
]

PROVENANCE_REQUIRED_ARTIFACTS = ["telemetry/simulated_flow_sensor_A.csv"]


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
        "origin": "trace_lab_simulated_demo_generator",
        "creation_mode": "local_simulation_scaffold",
        "authority_scope": "operational_evidence_only",
        "agent_approved": False,
        "scientific_truth_validated": False,
        "physical_execution_completed": False,
        "state_promoted": False,
    }
    if path.exists():
        entry["hash"] = sha256_file(path)
        if relative_path.endswith(".json"):
            try:
                entry["record_type"] = read_json(path).get("record_type")
            except Exception as exc:  # noqa: BLE001 - represented as provenance evidence
                entry["provenance_errors"] = [f"Cannot read JSON record: {exc}"]
    return entry


def build_provenance_manifest(run_dir: str | Path, *, created_at: str | None = None) -> dict[str, Any]:
    """Build local provenance metadata for TraceLab-generated run evidence.

    Provenance records generator/source information for the simulated evidence
    files only. It does not validate scientific truth, approve execution, call
    hardware, or promote durable claims.
    """

    run_dir = Path(run_dir)
    records = [_entry(run_dir, path, kind="json_record") for path in PROVENANCE_REQUIRED_RECORDS]
    artifacts = [_entry(run_dir, path, kind="data_artifact") for path in PROVENANCE_REQUIRED_ARTIFACTS]
    missing = [item["path"] for item in [*records, *artifacts] if not item.get("exists")]

    return {
        "record_type": "provenance_manifest",
        "created_at": created_at or now(),
        "provenance_scope": "operational_trace_provenance_only",
        "source_system": "trace_lab_v0_1_simulated_scaffold",
        "record_count": len(records),
        "artifact_count": len(artifacts),
        "records": records,
        "artifacts": artifacts,
        "missing": missing,
        "known_gaps": [
            "Provenance records local TraceLab scaffold generation only.",
            "Provenance does not validate scientific truth.",
            "Provenance does not imply human review completion.",
            "Provenance does not prove hardware readiness.",
        ],
        "not_proven_claims": [
            "scientific truth",
            "human review completion",
            "hardware readiness",
            "claim promotion",
        ],
        "authority_flags": {
            "agent_approved": False,
            "physical_execution_completed": False,
            "scientific_truth_validated": False,
            "state_promoted": False,
            "claims_promoted": False,
            "external_source_ingested": False,
            "human_review_completed": False,
        },
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": "Provenance manifest records local evidence origin only; it does not validate scientific truth, execute hardware, approve actions, or promote claims.",
    }


def write_provenance_manifest(
    run_dir: str | Path,
    *,
    force: bool = False,
    created_at: str | None = None,
) -> Path:
    run_dir = Path(run_dir)
    path = run_dir / PROVENANCE_FILE
    if path.exists() and not force:
        raise FileExistsError(
            "TraceLab refuses to overwrite provenance_manifest.json without force=True. "
            "This prevents silent replacement of provenance evidence."
        )
    write_json(path, build_provenance_manifest(run_dir, created_at=created_at))
    return path


def validate_provenance_manifest(
    run_dir: str | Path,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run_dir = Path(run_dir)
    errors: list[str] = []
    unsafe: list[str] = []

    if manifest is None:
        path = run_dir / PROVENANCE_FILE
        if not path.exists():
            return {
                "record_type": "provenance_validation",
                "provenance_validation_status": "failed_provenance_checks",
                "provenance_errors": [f"Missing provenance manifest: {PROVENANCE_FILE}"],
                "unsafe": [],
                "authority_note": "Provenance validation checks local evidence-origin metadata only.",
            }
        try:
            manifest = read_json(path)
        except Exception as exc:  # noqa: BLE001
            return {
                "record_type": "provenance_validation",
                "provenance_validation_status": "failed_provenance_checks",
                "provenance_errors": [f"Cannot read provenance manifest: {exc}"],
                "unsafe": [],
                "authority_note": "Provenance validation checks local evidence-origin metadata only.",
            }

    if manifest.get("record_type") != "provenance_manifest":
        errors.append("provenance_manifest.json record_type must be provenance_manifest.")
    if manifest.get("provenance_scope") != "operational_trace_provenance_only":
        errors.append("provenance_manifest.json provenance_scope must be operational_trace_provenance_only.")
    if manifest.get("source_system") != "trace_lab_v0_1_simulated_scaffold":
        errors.append("provenance_manifest.json source_system must be trace_lab_v0_1_simulated_scaffold.")

    flags = manifest.get("authority_flags", {})
    for flag_name in (
        "agent_approved",
        "physical_execution_completed",
        "scientific_truth_validated",
        "state_promoted",
        "claims_promoted",
        "external_source_ingested",
        "human_review_completed",
    ):
        if flags.get(flag_name):
            unsafe.append(f"provenance_manifest.json cannot set {flag_name}=true in v0.1 simulation.")

    for section_name, required_paths in [
        ("records", PROVENANCE_REQUIRED_RECORDS),
        ("artifacts", PROVENANCE_REQUIRED_ARTIFACTS),
    ]:
        items = manifest.get(section_name, [])
        if not isinstance(items, list):
            errors.append(f"provenance_manifest.json {section_name} must be a list.")
            continue

        seen_paths = {item.get("path") for item in items if isinstance(item, dict)}
        for required_path in required_paths:
            if required_path not in seen_paths:
                errors.append(f"provenance_manifest.json {section_name} missing required path: {required_path}")

        for index, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"provenance_manifest.json {section_name}[{index}] is not an object.")
                continue

            candidate, path_error = _safe_relative_path(item.get("path"))
            if path_error:
                errors.append(f"provenance_manifest.json {section_name}[{index}] {path_error}.")
                continue

            path = run_dir / candidate
            if not path.exists():
                errors.append(f"provenance_manifest.json {section_name}[{index}] points to missing path: {candidate.as_posix()}")
                continue

            expected_hash = item.get("hash")
            if not expected_hash:
                errors.append(f"provenance_manifest.json {section_name}[{index}] has no hash: {candidate.as_posix()}")
            elif sha256_file(path) != expected_hash:
                errors.append(f"provenance_manifest.json {section_name}[{index}] hash mismatch: {candidate.as_posix()}")

            if item.get("origin") != "trace_lab_simulated_demo_generator":
                errors.append(f"provenance_manifest.json {section_name}[{index}] origin must be trace_lab_simulated_demo_generator.")
            if item.get("creation_mode") != "local_simulation_scaffold":
                errors.append(f"provenance_manifest.json {section_name}[{index}] creation_mode must be local_simulation_scaffold.")
            if item.get("authority_scope") != "operational_evidence_only":
                errors.append(f"provenance_manifest.json {section_name}[{index}] authority_scope must be operational_evidence_only.")

            for flag_name in (
                "agent_approved",
                "scientific_truth_validated",
                "physical_execution_completed",
                "state_promoted",
            ):
                if item.get(flag_name):
                    unsafe.append(f"provenance_manifest.json {section_name}[{index}] cannot set {flag_name}=true.")

    if manifest.get("missing"):
        errors.append(f"provenance_manifest.json declares missing provenance paths: {manifest.get('missing')}")

    boundary_notes = manifest.get("boundary_notes", [])
    for note in BOUNDARY_NOTES:
        if note not in boundary_notes:
            errors.append(f"provenance_manifest.json missing boundary note: {note}")

    return {
        "record_type": "provenance_validation",
        "provenance_validation_status": "passed_provenance_checks" if not errors and not unsafe else "failed_provenance_checks",
        "provenance_errors": errors,
        "unsafe": unsafe,
        "authority_note": "Provenance validation checks local evidence-origin metadata only; it does not validate scientific truth or promote claims.",
    }


def build_provenance_summary(run_dir: str | Path) -> dict[str, Any]:
    run_dir = Path(run_dir)
    manifest_path = run_dir / PROVENANCE_FILE
    if manifest_path.exists():
        try:
            manifest = read_json(manifest_path)
        except Exception:  # noqa: BLE001
            manifest = {}
    else:
        manifest = build_provenance_manifest(run_dir)

    validation = validate_provenance_manifest(run_dir, manifest)
    return {
        "record_type": "provenance_summary",
        "created_at": now(),
        "provenance_scope": "operational_trace_provenance_only",
        "provenance_summary_status": (
            "provenance_recorded"
            if validation.get("provenance_validation_status") == "passed_provenance_checks"
            else "blocked_by_provenance_errors"
        ),
        "source_system": manifest.get("source_system"),
        "record_count": manifest.get("record_count", 0),
        "artifact_count": manifest.get("artifact_count", 0),
        "provenance_errors": validation.get("provenance_errors", []),
        "unsafe": validation.get("unsafe", []),
        "authority_flags": {
            "agent_approved": False,
            "physical_execution_completed": False,
            "scientific_truth_validated": False,
            "state_promoted": False,
            "claims_promoted": False,
            "external_source_ingested": False,
            "human_review_completed": False,
        },
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": "Provenance summary is a local evidence-origin trace view only; it does not validate scientific truth, approve execution, or promote claims.",
    }


def write_provenance_summary(run_dir: str | Path, *, force: bool = False) -> Path:
    run_dir = Path(run_dir)
    path = run_dir / PROVENANCE_SUMMARY_FILE
    if path.exists() and not force:
        raise FileExistsError(
            "TraceLab refuses to overwrite provenance_summary.json without force=True. "
            "This prevents silent replacement of provenance summary evidence."
        )
    write_json(path, build_provenance_summary(run_dir))
    return path
