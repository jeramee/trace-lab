from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import read_json, sha256_file, write_json
from .records import now

RUN_MANIFEST_FILE = "run_manifest.json"

CORE_RECORD_FILES = [
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
    "run_state_chain.json",
    "runtime_environment_manifest.json",
    "execution_policy_manifest.json",
    "telemetry_profile_manifest.json",
    "ingestion_preview_manifest.json",
    "provenance_manifest.json",
    "run_closeout_manifest.json",
    "claim_ledger_manifest.json",
    "operator_review_packet_manifest.json",
    "replay_plan_manifest.json",
    "audit_index_manifest.json",
    "validation_recipe_manifest.json",
    "neuml_handoff_manifest.json",
]

CORE_ARTIFACT_FILES = ["telemetry/simulated_flow_sensor_A.csv"]

BOUNDARY_NOTES = [
    "evidence != truth",
    "operational validation != scientific validity",
    "approval record != agent permission",
    "dry-run != physical execution",
    "NeuML handoff != claim promotion",
    "simulated adapter != hardware adapter",
]


def _safe_relative_path(raw_path: object) -> tuple[Path | None, str | None]:
    if not raw_path or not isinstance(raw_path, str):
        return None, "path is missing or not a string"

    candidate = Path(raw_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None, f"path must stay inside run directory: {raw_path}"

    return candidate, None


def _record_entry(run_dir: Path, relative_path: str) -> dict[str, Any]:
    path = run_dir / relative_path
    entry: dict[str, Any] = {"path": relative_path, "exists": path.exists()}
    if path.exists():
        entry["hash"] = sha256_file(path)
        try:
            entry["record_type"] = read_json(path).get("record_type")
        except Exception as exc:  # noqa: BLE001 - represented as manifest evidence
            entry["record_error"] = str(exc)
    return entry


def _artifact_entry(run_dir: Path, relative_path: str) -> dict[str, Any]:
    path = run_dir / relative_path
    entry: dict[str, Any] = {"path": relative_path, "exists": path.exists()}
    if path.exists():
        entry["hash"] = sha256_file(path)
    return entry


def build_run_manifest(run_dir: str | Path) -> dict[str, Any]:
    """Build a deterministic hash index for TraceLab v0.1 run evidence.

    The run manifest is a mechanical drift-detection artifact. It records the
    JSON records and telemetry artifacts that belong to the simulated run. It
    does not approve the run, validate scientific truth, execute hardware, or
    promote claims.
    """

    run_dir = Path(run_dir)
    records = [_record_entry(run_dir, name) for name in CORE_RECORD_FILES]
    artifacts = [_artifact_entry(run_dir, name) for name in CORE_ARTIFACT_FILES]
    missing = [item["path"] for item in [*records, *artifacts] if not item.get("exists")]

    return {
        "record_type": "run_manifest",
        "created_at": now(),
        "manifest_scope": "operational_simulation_only",
        "record_count": len(records),
        "artifact_count": len(artifacts),
        "records": records,
        "artifacts": artifacts,
        "missing": missing,
        "authority_flags": {
            "agent_approved": False,
            "physical_execution_completed": False,
            "scientific_truth_validated": False,
            "state_promoted": False,
            "claims_promoted": False,
            "automatic_retry_performed": False,
        },
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": "Run manifest hashes are operational drift evidence only; they do not validate scientific truth or promote claims.",
    }


def write_run_manifest(run_dir: str | Path, *, force: bool = False) -> Path:
    """Write run_manifest.json, refusing silent overwrite by default."""

    run_dir = Path(run_dir)
    path = run_dir / RUN_MANIFEST_FILE
    if path.exists() and not force:
        raise FileExistsError(
            "TraceLab refuses to overwrite run_manifest.json without force=True. "
            "This prevents silent replacement of run evidence hashes."
        )

    write_json(path, build_run_manifest(run_dir))
    return path


def validate_run_manifest(run_dir: str | Path, manifest: dict[str, Any]) -> list[str]:
    """Validate run_manifest.json against current files on disk."""

    run_dir = Path(run_dir)
    errors: list[str] = []

    if not isinstance(manifest, dict):
        return ["run_manifest.json is not a JSON object."]

    if manifest.get("record_type") != "run_manifest":
        errors.append("run_manifest.json record_type must be 'run_manifest'.")
    if manifest.get("manifest_scope") != "operational_simulation_only":
        errors.append("run_manifest.json manifest_scope must be operational_simulation_only.")

    flags = manifest.get("authority_flags", {})
    for flag in [
        "agent_approved",
        "physical_execution_completed",
        "scientific_truth_validated",
        "state_promoted",
        "claims_promoted",
        "automatic_retry_performed",
    ]:
        if flags.get(flag):
            errors.append(f"run_manifest.json cannot set {flag}=true in v0.1 simulation.")

    records = manifest.get("records", [])
    if not isinstance(records, list):
        return errors + ["run_manifest.json records must be a list."]

    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list):
        errors.append("run_manifest.json artifacts must be a list.")
        artifacts = []

    record_paths = {item.get("path") for item in records if isinstance(item, dict)}
    for required in CORE_RECORD_FILES:
        if required not in record_paths:
            errors.append(f"run_manifest.json records missing required record: {required}")

    artifact_paths = {item.get("path") for item in artifacts if isinstance(item, dict)}
    for required in CORE_ARTIFACT_FILES:
        if required not in artifact_paths:
            errors.append(f"run_manifest.json artifacts missing required artifact: {required}")

    for collection_name, items in [("records", records), ("artifacts", artifacts)]:
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"run_manifest.json {collection_name}[{index}] is not an object.")
                continue

            candidate, path_error = _safe_relative_path(item.get("path"))
            if path_error:
                errors.append(f"run_manifest.json {collection_name}[{index}] {path_error}.")
                continue

            path = run_dir / candidate
            if not path.exists():
                errors.append(f"run_manifest.json {collection_name}[{index}] points to missing path: {candidate.as_posix()}")
                continue

            expected_hash = item.get("hash")
            if not expected_hash:
                errors.append(f"run_manifest.json {collection_name}[{index}] has no hash: {candidate.as_posix()}")
            elif sha256_file(path) != expected_hash:
                errors.append(f"run_manifest.json {collection_name}[{index}] hash mismatch: {candidate.as_posix()}")

    missing = manifest.get("missing", [])
    if missing:
        errors.append(f"run_manifest.json declares missing evidence paths: {missing}")

    return errors
