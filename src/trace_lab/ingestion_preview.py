from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import read_json, write_json
from .records import now

INGESTION_PREVIEW_FILE = "ingestion_preview_manifest.json"
INGESTION_PREVIEW_SUMMARY_FILE = "ingestion_preview_summary.json"

BOUNDARY_NOTES = [
    "evidence != truth",
    "operational validation != scientific validity",
    "approval record != agent permission",
    "dry-run != physical execution",
    "NeuML handoff != claim promotion",
    "simulated adapter != hardware adapter",
]

TEXT_INDEX_CANDIDATE_DEFAULTS = [
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
    "neuml_handoff_manifest.json",
    "trace_lab_report.md",
]

TELEMETRY_DATA_CANDIDATE_DEFAULTS = [
    "telemetry/simulated_flow_sensor_A.csv",
]

REPORT_CANDIDATE_DEFAULTS = [
    "trace_lab_report.md",
    "trace_lab_report.md.validation.json",
    "evidence_packet_manifest.json",
    "review_record.json",
    "validation_record.json",
    "telemetry_profile_manifest.json",
]


def _safe_relative_path(raw_path: object) -> tuple[str | None, str | None]:
    if not raw_path or not isinstance(raw_path, str):
        return None, "candidate path is missing or not a string"

    candidate = Path(raw_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None, f"candidate path must stay inside run directory: {raw_path}"

    return candidate.as_posix(), None


def _existing_candidates(run_dir: Path, paths: list[str]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for raw_path in paths:
        safe_path, path_error = _safe_relative_path(raw_path)
        if path_error:
            candidates.append(
                {
                    "path": raw_path,
                    "exists": False,
                    "candidate_errors": [path_error],
                }
            )
            continue

        path = run_dir / safe_path
        candidates.append(
            {
                "path": safe_path,
                "exists": path.exists(),
                "kind": "text" if safe_path.endswith((".json", ".md")) else "data",
            }
        )
    return candidates


def build_ingestion_preview_manifest(run_dir: str | Path, *, created_at: str | None = None) -> dict[str, Any]:
    """Build a local ingestion preview manifest.

    This manifest describes which local TraceLab records could be indexed later
    by a separate tool. It performs no ingestion, no model calls, no network
    calls, no hardware access, no package installation, no scientific truth
    validation, and no claim promotion.
    """

    run_dir = Path(run_dir)
    handoff_path = run_dir / "neuml_handoff_manifest.json"
    handoff: dict[str, Any] = {}
    if handoff_path.exists():
        try:
            handoff = read_json(handoff_path)
        except Exception:  # noqa: BLE001 - represented by validation
            handoff = {}

    text_candidates = handoff.get("text_index_candidates") or TEXT_INDEX_CANDIDATE_DEFAULTS
    telemetry_candidates = handoff.get("telemetry_data_candidates") or TELEMETRY_DATA_CANDIDATE_DEFAULTS
    report_candidates = handoff.get("report_candidates") or REPORT_CANDIDATE_DEFAULTS

    text_candidate_entries = _existing_candidates(run_dir, list(text_candidates))
    telemetry_candidate_entries = _existing_candidates(run_dir, list(telemetry_candidates))
    report_candidate_entries = _existing_candidates(run_dir, list(report_candidates))

    candidate_count = (
        len(text_candidate_entries)
        + len(telemetry_candidate_entries)
        + len(report_candidate_entries)
    )

    return {
        "record_type": "ingestion_preview_manifest",
        "created_at": created_at or now(),
        "preview_scope": "local_index_preview_only",
        "source_handoff_manifest": "neuml_handoff_manifest.json",
        "candidate_count": candidate_count,
        "text_index_candidates": text_candidate_entries,
        "telemetry_data_candidates": telemetry_candidate_entries,
        "report_candidates": report_candidate_entries,
        "recommended_consumers": [
            "future txtai indexing tool",
            "future PaperAI/PaperETL ingestion tool",
            "future evidence search interface",
        ],
        "known_gaps": [
            "No external ingestion is performed by TraceLab.",
            "No NeuML/txtai/PaperAI service is called by TraceLab.",
            "No model call is performed by TraceLab.",
            "No scientific truth validation is performed by TraceLab.",
        ],
        "not_proven_claims": [
            "scientific truth",
            "index quality",
            "retrieval relevance",
            "claim promotion",
        ],
        "authority_flags": {
            "agent_approved": False,
            "physical_execution_completed": False,
            "scientific_truth_validated": False,
            "state_promoted": False,
            "claims_promoted": False,
            "network_calls_performed": False,
            "model_calls_performed": False,
            "external_ingestion_performed": False,
            "package_installation_performed": False,
        },
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": "Ingestion preview lists local index candidates only; it does not call external tools, validate scientific truth, or promote claims.",
    }


def write_ingestion_preview_manifest(run_dir: str | Path, *, force: bool = False) -> Path:
    run_dir = Path(run_dir)
    path = run_dir / INGESTION_PREVIEW_FILE
    if path.exists() and not force:
        raise FileExistsError(
            "TraceLab refuses to overwrite ingestion_preview_manifest.json without force=True. "
            "This prevents silent replacement of ingestion-preview evidence."
        )

    write_json(path, build_ingestion_preview_manifest(run_dir))
    return path


def validate_ingestion_preview_manifest(run_dir: str | Path, manifest: dict[str, Any]) -> list[str]:
    run_dir = Path(run_dir)
    errors: list[str] = []

    if not isinstance(manifest, dict):
        return ["ingestion_preview_manifest.json is not a JSON object."]

    if manifest.get("record_type") != "ingestion_preview_manifest":
        errors.append("ingestion_preview_manifest.json record_type must be 'ingestion_preview_manifest'.")
    if manifest.get("preview_scope") != "local_index_preview_only":
        errors.append("ingestion_preview_manifest.json preview_scope must be local_index_preview_only.")
    if manifest.get("source_handoff_manifest") != "neuml_handoff_manifest.json":
        errors.append("ingestion_preview_manifest.json source_handoff_manifest must be neuml_handoff_manifest.json.")
    if not (run_dir / "neuml_handoff_manifest.json").exists():
        errors.append("ingestion_preview_manifest.json requires neuml_handoff_manifest.json to exist.")

    flags = manifest.get("authority_flags", {})
    for flag in [
        "agent_approved",
        "physical_execution_completed",
        "scientific_truth_validated",
        "state_promoted",
        "claims_promoted",
        "network_calls_performed",
        "model_calls_performed",
        "external_ingestion_performed",
        "package_installation_performed",
    ]:
        if flags.get(flag):
            errors.append(f"ingestion_preview_manifest.json cannot set {flag}=true in v0.1 simulation.")

    candidate_sections = [
        "text_index_candidates",
        "telemetry_data_candidates",
        "report_candidates",
    ]
    actual_candidate_count = 0
    for section in candidate_sections:
        candidates = manifest.get(section)
        if not isinstance(candidates, list):
            errors.append(f"ingestion_preview_manifest.json {section} must be a list.")
            continue

        actual_candidate_count += len(candidates)
        for index, item in enumerate(candidates):
            if not isinstance(item, dict):
                errors.append(f"ingestion_preview_manifest.json {section}[{index}] must be an object.")
                continue

            safe_path, path_error = _safe_relative_path(item.get("path"))
            if path_error:
                errors.append(f"ingestion_preview_manifest.json {section}[{index}] {path_error}.")
                continue

            if item.get("exists") and not (run_dir / safe_path).exists():
                errors.append(f"ingestion_preview_manifest.json {section}[{index}] points to missing path: {safe_path}")

            candidate_errors = item.get("candidate_errors", [])
            if candidate_errors:
                errors.append(f"ingestion_preview_manifest.json {section}[{index}] declares candidate errors: {candidate_errors}")

    if manifest.get("candidate_count") != actual_candidate_count:
        errors.append(
            "ingestion_preview_manifest.json candidate_count does not match listed candidates."
        )

    boundary_notes = manifest.get("boundary_notes", [])
    for note in BOUNDARY_NOTES:
        if note not in boundary_notes:
            errors.append(f"ingestion_preview_manifest.json missing boundary note: {note}")

    return errors


def build_ingestion_preview_summary(run_dir: str | Path) -> dict[str, Any]:
    run_dir = Path(run_dir)
    manifest_path = run_dir / INGESTION_PREVIEW_FILE
    if manifest_path.exists():
        try:
            manifest = read_json(manifest_path)
        except Exception:  # noqa: BLE001 - summary records validation failure
            manifest = {}
    else:
        manifest = build_ingestion_preview_manifest(run_dir)

    errors = validate_ingestion_preview_manifest(run_dir, manifest)
    text_count = len(manifest.get("text_index_candidates", [])) if isinstance(manifest, dict) else 0
    telemetry_count = len(manifest.get("telemetry_data_candidates", [])) if isinstance(manifest, dict) else 0
    report_count = len(manifest.get("report_candidates", [])) if isinstance(manifest, dict) else 0

    return {
        "record_type": "ingestion_preview_summary",
        "created_at": now(),
        "preview_scope": "local_index_preview_only",
        "ingestion_preview_status": (
            "ready_for_future_local_indexing"
            if not errors
            else "blocked_by_ingestion_preview_errors"
        ),
        "text_index_candidate_count": text_count,
        "telemetry_data_candidate_count": telemetry_count,
        "report_candidate_count": report_count,
        "ingestion_errors": errors,
        "authority_flags": {
            "network_calls_performed": False,
            "model_calls_performed": False,
            "external_ingestion_performed": False,
            "scientific_truth_validated": False,
            "claims_promoted": False,
        },
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": "Ingestion preview summary is a local trace view only; it does not call external tools, validate scientific truth, or promote claims.",
    }


def write_ingestion_preview_summary(run_dir: str | Path, *, force: bool = False) -> Path:
    run_dir = Path(run_dir)
    path = run_dir / INGESTION_PREVIEW_SUMMARY_FILE
    if path.exists() and not force:
        raise FileExistsError(
            "TraceLab refuses to overwrite ingestion_preview_summary.json without force=True. "
            "This prevents silent replacement of ingestion-preview summary evidence."
        )

    write_json(path, build_ingestion_preview_summary(run_dir))
    return path
