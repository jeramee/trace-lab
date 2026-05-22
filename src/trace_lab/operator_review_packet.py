from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import read_json, sha256_file, write_json
from .records import now

OPERATOR_REVIEW_PACKET_MANIFEST_FILE = "operator_review_packet_manifest.json"
OPERATOR_REVIEW_PACKET_SUMMARY_FILE = "operator_review_packet_summary.json"

PACKET_REQUIRED_FILES = [
    "experiment_request.json",
    "run_plan.json",
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
    "telemetry/simulated_flow_sensor_A.csv",
]

OPTIONAL_PACKET_FILES = [
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
    "trace_lab_report.md",
    "trace_lab_report.md.validation.json",
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


def _packet_item(run_dir: Path, relative_path: str, *, required: bool) -> dict[str, Any]:
    path = run_dir / relative_path
    item: dict[str, Any] = {
        "path": relative_path,
        "required": required,
        "exists": path.exists(),
    }
    if path.exists():
        item["hash"] = sha256_file(path)
        item["size_bytes"] = path.stat().st_size
        if path.suffix == ".json":
            try:
                item["record_type"] = read_json(path).get("record_type")
            except Exception as exc:  # noqa: BLE001 - recorded as packet evidence
                item["record_error"] = str(exc)
    return item


def build_operator_review_packet_manifest(run_dir: str | Path, *, created_at: str | None = None) -> dict[str, Any]:
    """Build a local human-review packet manifest for a simulated TraceLab run.

    The packet is a navigation/checklist artifact for a human operator. It does
    not complete human review, validate scientific truth, approve hardware
    execution, or promote claims.
    """

    run_dir = Path(run_dir)
    required_items = [_packet_item(run_dir, name, required=True) for name in PACKET_REQUIRED_FILES]
    optional_items = [
        _packet_item(run_dir, name, required=False)
        for name in OPTIONAL_PACKET_FILES
        if (run_dir / name).exists()
    ]

    missing_required = [item["path"] for item in required_items if not item.get("exists")]

    return {
        "record_type": "operator_review_packet_manifest",
        "created_at": created_at or now(),
        "packet_scope": "human_operator_review_packet_only",
        "packet_status": "ready_for_human_review_queue" if not missing_required else "blocked_missing_required_evidence",
        "human_review_required": True,
        "human_review_completed": False,
        "agent_reviewed": False,
        "automatic_promotion_allowed": False,
        "claims_promoted": [],
        "state_promoted": False,
        "required_item_count": len(required_items),
        "optional_item_count": len(optional_items),
        "missing_required": missing_required,
        "packet_items": required_items + optional_items,
        "review_queue_notes": [
            "Packet is local navigation evidence for human review.",
            "Packet does not complete human review.",
            "Packet does not validate scientific truth.",
            "Packet does not approve physical execution.",
            "Packet does not promote claims or durable state.",
        ],
        "authority_flags": {
            "agent_approved": False,
            "agent_reviewed": False,
            "human_review_completed": False,
            "physical_execution_completed": False,
            "scientific_truth_validated": False,
            "state_promoted": False,
            "claims_promoted": False,
            "hardware_access_performed": False,
        },
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": "Operator review packet is a local review-navigation artifact only; it does not complete review, validate truth, execute hardware, or promote claims.",
    }


def write_operator_review_packet_manifest(
    run_dir: str | Path,
    *,
    force: bool = False,
) -> Path:
    """Write operator_review_packet_manifest.json, refusing silent overwrite."""

    run_dir = Path(run_dir)
    path = run_dir / OPERATOR_REVIEW_PACKET_MANIFEST_FILE
    if path.exists() and not force:
        raise FileExistsError(
            "TraceLab refuses to overwrite operator_review_packet_manifest.json without force=True. "
            "This prevents silent replacement of human-review packet evidence."
        )

    write_json(path, build_operator_review_packet_manifest(run_dir))
    return path


def validate_operator_review_packet_manifest(
    run_dir: str | Path,
    manifest: dict[str, Any] | None,
) -> dict[str, list[str]]:
    """Validate the local operator review packet manifest.

    This is an operational packet-completeness check only. It does not validate
    scientific truth, complete human review, approve hardware, or promote claims.
    """

    run_dir = Path(run_dir)
    errors: list[str] = []
    unsafe: list[str] = []

    if manifest is None:
        return {
            "review_packet_errors": ["Missing operator review packet manifest: operator_review_packet_manifest.json"],
            "unsafe": [],
        }

    if not isinstance(manifest, dict):
        return {"review_packet_errors": ["operator_review_packet_manifest.json is not a JSON object."], "unsafe": []}

    if manifest.get("record_type") != "operator_review_packet_manifest":
        errors.append("operator_review_packet_manifest.json record_type must be operator_review_packet_manifest.")
    if manifest.get("packet_scope") != "human_operator_review_packet_only":
        errors.append("operator_review_packet_manifest.json packet_scope must be human_operator_review_packet_only.")
    if manifest.get("human_review_required") is not True:
        errors.append("operator_review_packet_manifest.json must require human review.")
    if manifest.get("human_review_completed"):
        unsafe.append("Operator review packet cannot claim human_review_completed=true.")
    if manifest.get("agent_reviewed"):
        unsafe.append("Operator review packet cannot claim agent_reviewed=true.")
    if manifest.get("automatic_promotion_allowed"):
        unsafe.append("Operator review packet cannot allow automatic promotion.")
    if manifest.get("claims_promoted"):
        unsafe.append("Operator review packet cannot promote claims.")
    if manifest.get("state_promoted"):
        unsafe.append("Operator review packet cannot promote durable state.")

    flags = manifest.get("authority_flags", {})
    for flag in [
        "agent_approved",
        "agent_reviewed",
        "human_review_completed",
        "physical_execution_completed",
        "scientific_truth_validated",
        "state_promoted",
        "claims_promoted",
        "hardware_access_performed",
    ]:
        if flags.get(flag):
            unsafe.append(f"operator_review_packet_manifest.json cannot set {flag}=true in v0.1 simulation.")

    packet_items = manifest.get("packet_items", [])
    if not isinstance(packet_items, list):
        return {"review_packet_errors": errors + ["operator_review_packet_manifest.json packet_items must be a list."], "unsafe": unsafe}

    indexed_items = {item.get("path"): item for item in packet_items if isinstance(item, dict)}
    for required in PACKET_REQUIRED_FILES:
        if required not in indexed_items:
            errors.append(f"operator_review_packet_manifest.json packet_items missing required file: {required}")

    for index, item in enumerate(packet_items):
        if not isinstance(item, dict):
            errors.append(f"operator_review_packet_manifest.json packet_items[{index}] is not an object.")
            continue

        candidate, path_error = _safe_relative_path(item.get("path"))
        if path_error:
            errors.append(f"operator_review_packet_manifest.json packet_items[{index}] {path_error}.")
            continue

        item_path = run_dir / candidate
        if item.get("required") and not item_path.exists():
            errors.append(f"operator_review_packet_manifest.json required packet item missing: {candidate.as_posix()}")
            continue

        if item_path.exists():
            expected_hash = item.get("hash")
            if expected_hash and sha256_file(item_path) != expected_hash:
                errors.append(f"operator_review_packet_manifest.json packet item hash mismatch: {candidate.as_posix()}")

    if errors and manifest.get("packet_status") == "ready_for_human_review_queue":
        errors.append("operator_review_packet_manifest.json packet_status cannot be ready when packet errors exist.")
    if not errors and manifest.get("packet_status") != "ready_for_human_review_queue":
        errors.append("operator_review_packet_manifest.json packet_status must be ready_for_human_review_queue when complete.")

    return {"review_packet_errors": errors, "unsafe": unsafe}


def build_operator_review_packet_summary(run_dir: str | Path) -> dict[str, Any]:
    """Build an operator-facing summary of the human-review packet."""

    run_dir = Path(run_dir)
    manifest_path = run_dir / OPERATOR_REVIEW_PACKET_MANIFEST_FILE
    manifest = read_json(manifest_path) if manifest_path.exists() else None
    validation = validate_operator_review_packet_manifest(run_dir, manifest)

    packet_items = manifest.get("packet_items", []) if isinstance(manifest, dict) else []
    required_count = sum(1 for item in packet_items if isinstance(item, dict) and item.get("required"))
    optional_count = sum(1 for item in packet_items if isinstance(item, dict) and not item.get("required"))

    return {
        "record_type": "operator_review_packet_summary",
        "created_at": now(),
        "packet_scope": "human_operator_review_packet_only",
        "packet_summary_status": (
            "ready_for_human_review_queue"
            if not validation["review_packet_errors"] and not validation["unsafe"]
            else "blocked_by_review_packet_errors"
        ),
        "human_review_required": True,
        "human_review_completed": False,
        "agent_reviewed": False,
        "automatic_promotion_allowed": False,
        "required_item_count": required_count,
        "optional_item_count": optional_count,
        "review_packet_errors": validation["review_packet_errors"],
        "unsafe": validation["unsafe"],
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": "Operator review packet summary is a local review-navigation view only; it does not complete review, validate scientific truth, execute hardware, or promote claims.",
    }


def write_operator_review_packet_summary(
    run_dir: str | Path,
    *,
    force: bool = False,
) -> Path:
    """Write operator_review_packet_summary.json, refusing silent overwrite."""

    run_dir = Path(run_dir)
    path = run_dir / OPERATOR_REVIEW_PACKET_SUMMARY_FILE
    if path.exists() and not force:
        raise FileExistsError(
            "TraceLab refuses to overwrite operator_review_packet_summary.json without force=True. "
            "This prevents silent replacement of human-review packet summary evidence."
        )

    write_json(path, build_operator_review_packet_summary(run_dir))
    return path
