from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import read_json, sha256_file, write_json
from .records import now

AUDIT_INDEX_MANIFEST_FILE = "audit_index_manifest.json"
AUDIT_INDEX_SUMMARY_FILE = "audit_index_summary.json"

CORE_RECORDS = [
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

BOUNDARY_MANIFESTS = [
    "ingestion_preview_manifest.json",
    "provenance_manifest.json",
    "run_closeout_manifest.json",
    "claim_ledger_manifest.json",
    "operator_review_packet_manifest.json",
    "replay_plan_manifest.json",
    "audit_index_manifest.json",
    "neuml_handoff_manifest.json",
    "run_manifest.json",
]

OPTIONAL_SUMMARIES = [
    "validation_result.json",
    "run_state_summary.json",
    "review_summary.json",
    "adapter_boundary_summary.json",
    "runtime_environment_summary.json",
    "execution_policy_summary.json",
    "telemetry_profile_summary.json",
    "ingestion_preview_summary.json",
    "provenance_summary.json",
    "run_closeout_summary.json",
    "claim_ledger_summary.json",
    "operator_review_packet_summary.json",
    "replay_plan_summary.json",
    "audit_index_summary.json",
]

REPORT_FILES = [
    "trace_lab_report.md",
    "trace_lab_report.md.validation.json",
]

TELEMETRY_ARTIFACTS = [
    "telemetry/simulated_flow_sensor_A.csv",
]

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


def _entry(run_dir: Path, relative_path: str, *, category: str, role: str) -> dict[str, Any]:
    path = run_dir / relative_path
    item: dict[str, Any] = {
        "path": relative_path,
        "category": category,
        "role": role,
        "exists": path.exists(),
    }
    if path.exists():
        item["hash"] = sha256_file(path)
        item["size_bytes"] = path.stat().st_size
        if path.suffix == ".json":
            try:
                item["record_type"] = read_json(path).get("record_type")
            except Exception as exc:  # noqa: BLE001 - evidence artifact records the parse problem
                item["record_error"] = str(exc)
    return item


def _build_items(run_dir: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in CORE_RECORDS:
        items.append(_entry(run_dir, path, category="core_record", role="required operational trace record"))
    for path in BOUNDARY_MANIFESTS:
        items.append(_entry(run_dir, path, category="boundary_manifest", role="required boundary or index manifest"))
    for path in TELEMETRY_ARTIFACTS:
        items.append(_entry(run_dir, path, category="telemetry_artifact", role="simulation telemetry artifact"))
    for path in OPTIONAL_SUMMARIES:
        if (run_dir / path).exists():
            items.append(_entry(run_dir, path, category="operator_summary", role="optional operator-facing summary"))
    for path in REPORT_FILES:
        if (run_dir / path).exists():
            items.append(_entry(run_dir, path, category="operator_report", role="optional readability/report artifact"))
    return items


def build_audit_index_manifest(run_dir: str | Path, *, created_at: str | None = None) -> dict[str, Any]:
    """Build a local artifact navigation index for a TraceLab simulated run.

    The audit index is not a scientific result, approval, promotion, or replay.
    It is only a local map of evidence files and their current hashes.
    """

    run_dir = Path(run_dir)
    items = _build_items(run_dir)
    missing_required = [
        item["path"]
        for item in items
        if item["category"] in {"core_record", "boundary_manifest", "telemetry_artifact"}
        and not item.get("exists")
        and item["path"] != AUDIT_INDEX_MANIFEST_FILE
    ]

    return {
        "record_type": "audit_index_manifest",
        "created_at": created_at or now(),
        "audit_index_scope": "operational_simulation_only",
        "audit_index_status": "local_artifact_index_recorded",
        "item_count": len(items),
        "missing_required": missing_required,
        "items": items,
        "category_counts": {
            "core_record": sum(1 for item in items if item["category"] == "core_record"),
            "boundary_manifest": sum(1 for item in items if item["category"] == "boundary_manifest"),
            "telemetry_artifact": sum(1 for item in items if item["category"] == "telemetry_artifact"),
            "operator_summary": sum(1 for item in items if item["category"] == "operator_summary"),
            "operator_report": sum(1 for item in items if item["category"] == "operator_report"),
        },
        "authority_flags": {
            "agent_approved": False,
            "human_review_completed": False,
            "physical_execution_completed": False,
            "scientific_truth_validated": False,
            "state_promoted": False,
            "claims_promoted": False,
            "replay_executed": False,
            "network_calls_performed": False,
            "package_installation_performed": False,
            "hardware_access_performed": False,
        },
        "known_gaps": [
            "Audit index is local file navigation only.",
            "Audit index does not prove scientific truth.",
            "Audit index does not complete human review.",
            "Audit index does not replay or execute hardware actions.",
        ],
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": "Audit index manifests are local artifact maps only; they do not validate scientific truth, complete review, execute replay, or promote claims.",
    }


def write_audit_index_manifest(run_dir: str | Path, *, force: bool = False) -> Path:
    run_dir = Path(run_dir)
    path = run_dir / AUDIT_INDEX_MANIFEST_FILE
    if path.exists() and not force:
        raise FileExistsError(
            "TraceLab refuses to overwrite audit_index_manifest.json without force=True. "
            "This prevents silent replacement of artifact navigation evidence."
        )
    write_json(path, build_audit_index_manifest(run_dir))
    return path


def validate_audit_index_manifest(run_dir: str | Path, manifest: dict[str, Any] | None) -> dict[str, list[str]]:
    run_dir = Path(run_dir)
    errors: list[str] = []
    unsafe: list[str] = []

    if manifest is None:
        return {
            "audit_errors": ["audit_index_manifest.json is missing."],
            "unsafe": [],
        }

    if not isinstance(manifest, dict):
        return {
            "audit_errors": ["audit_index_manifest.json is not a JSON object."],
            "unsafe": [],
        }

    if manifest.get("record_type") != "audit_index_manifest":
        errors.append("audit_index_manifest.json record_type must be 'audit_index_manifest'.")
    if manifest.get("audit_index_scope") != "operational_simulation_only":
        errors.append("audit_index_manifest.json audit_index_scope must be operational_simulation_only.")
    if manifest.get("audit_index_status") != "local_artifact_index_recorded":
        errors.append("audit_index_manifest.json audit_index_status must be local_artifact_index_recorded.")

    flags = manifest.get("authority_flags", {})
    for flag in [
        "agent_approved",
        "human_review_completed",
        "physical_execution_completed",
        "scientific_truth_validated",
        "state_promoted",
        "claims_promoted",
        "replay_executed",
        "network_calls_performed",
        "package_installation_performed",
        "hardware_access_performed",
    ]:
        if flags.get(flag):
            unsafe.append(f"audit_index_manifest.json cannot set {flag}=true in v0.1 simulation.")

    items = manifest.get("items", [])
    if not isinstance(items, list):
        return {"audit_errors": errors + ["audit_index_manifest.json items must be a list."], "unsafe": unsafe}

    paths_seen: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"audit_index_manifest.json items[{index}] is not an object.")
            continue
        candidate, path_error = _safe_relative_path(item.get("path"))
        if path_error:
            errors.append(f"audit_index_manifest.json items[{index}] {path_error}.")
            continue

        relative = candidate.as_posix()
        paths_seen.add(relative)
        expected_exists = (run_dir / candidate).exists()
        # The audit index cannot hash itself before it is written, and it is
        # normally written before the final run_manifest.json refresh. Treat
        # false->true existence drift for those two index files as expected
        # bootstrap behavior rather than evidence corruption.
        bootstrap_path = relative in {AUDIT_INDEX_MANIFEST_FILE, "run_manifest.json"}
        bootstrap_self_reference = (
            bootstrap_path
            and item.get("exists") is False
            and expected_exists is True
        )
        if item.get("exists") != expected_exists and not bootstrap_self_reference:
            errors.append(f"audit_index_manifest.json exists drift for {relative}.")
            continue

        # audit_index_manifest.json and run_manifest.json are self/final-index
        # files whose hashes can legitimately change as index files are
        # refreshed. Their presence is tracked above; drift detection for their
        # hashes is owned by run_manifest.json, not by this self-referential map.
        if bootstrap_path:
            continue

        if expected_exists:
            expected_hash = item.get("hash")
            if not expected_hash:
                errors.append(f"audit_index_manifest.json missing hash for existing path: {relative}")
            elif sha256_file(run_dir / candidate) != expected_hash:
                errors.append(f"audit_index_manifest.json hash mismatch: {relative}")

    for required in [*CORE_RECORDS, *BOUNDARY_MANIFESTS, *TELEMETRY_ARTIFACTS]:
        if required not in paths_seen:
            errors.append(f"audit_index_manifest.json items missing required path: {required}")

    declared_count = manifest.get("item_count")
    if declared_count != len(items):
        errors.append("audit_index_manifest.json item_count does not match items length.")

    return {"audit_errors": errors, "unsafe": unsafe}


def build_audit_index_summary(run_dir: str | Path) -> dict[str, Any]:
    run_dir = Path(run_dir)
    manifest = build_audit_index_manifest(run_dir)
    validation = validate_audit_index_manifest(run_dir, manifest)
    audit_errors = validation.get("audit_errors", [])
    unsafe = validation.get("unsafe", [])
    return {
        "record_type": "audit_index_summary",
        "created_at": now(),
        "audit_index_summary_status": "local_artifact_index_ready" if not audit_errors and not unsafe else "audit_index_has_errors",
        "audit_index_scope": "operator_navigation_only",
        "item_count": manifest["item_count"],
        "category_counts": manifest["category_counts"],
        "missing_required": manifest["missing_required"],
        "audit_errors": audit_errors,
        "unsafe": unsafe,
        "authority_flags": manifest["authority_flags"],
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": "Audit index summary is an operator-facing navigation view only; it does not validate scientific truth, complete review, execute replay, or promote claims.",
    }


def write_audit_index_summary(run_dir: str | Path, *, force: bool = False) -> Path:
    run_dir = Path(run_dir)
    path = run_dir / AUDIT_INDEX_SUMMARY_FILE
    if path.exists() and not force:
        raise FileExistsError(
            "TraceLab refuses to overwrite audit_index_summary.json without force=True. "
            "This prevents silent replacement of operator navigation evidence."
        )
    write_json(path, build_audit_index_summary(run_dir))
    return path
