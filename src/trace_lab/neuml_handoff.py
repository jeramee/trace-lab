from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .io import read_json, write_json
from .records import now

RECORD_CANDIDATES = [
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
]

OPTIONAL_HANDOFF_RECORDS = [
    "ingestion_preview_manifest.json",
    "provenance_manifest.json",
    "run_closeout_manifest.json",
    "claim_ledger_manifest.json",
    "operator_review_packet_manifest.json",
    "replay_plan_manifest.json",
    "audit_index_manifest.json",
    "validation_recipe_manifest.json",
]

REQUIRED_HANDOFF_RECORDS = list(RECORD_CANDIDATES)
EVIDENCE_PACKET_REFERENCED_RECORDS = [
    name for name in REQUIRED_HANDOFF_RECORDS if name != "evidence_packet_manifest.json"
]

TEXT_INDEX_CANDIDATES = [
    "experiment_request.json",
    "run_plan.json",
    "approval_record.json",
    "adapter_capability_manifest.json",
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
]

TELEMETRY_DATA_CANDIDATES = ["telemetry/simulated_flow_sensor_A.csv"]
REPORT_CANDIDATES = ["evidence_packet_manifest.json", "review_record.json", "validation_record.json", "run_state_chain.json", "runtime_environment_manifest.json", "execution_policy_manifest.json", "telemetry_profile_manifest.json", "ingestion_preview_manifest.json", "provenance_manifest.json", "run_closeout_manifest.json", "claim_ledger_manifest.json", "operator_review_packet_manifest.json", "replay_plan_manifest.json", "audit_index_manifest.json", "validation_recipe_manifest.json", "trace_lab_report.md"]


def _existing_paths(run_dir: Path, paths: Iterable[str]) -> list[str]:
    return [path for path in paths if (run_dir / path).exists()]


def validate_handoff_preconditions(run_dir: str | Path) -> list[str]:
    """Return operational preflight errors for preparing a NeuML handoff.

    This is intentionally a mechanical completeness check. It does not call
    NeuML/txtai/PaperAI, validate scientific truth, approve execution, or
    promote claims.
    """

    run_dir = Path(run_dir)
    errors: list[str] = []

    missing_records = [name for name in REQUIRED_HANDOFF_RECORDS if not (run_dir / name).exists()]
    for name in missing_records:
        errors.append(f"handoff preflight missing required record: {name}")

    evidence_path = run_dir / "evidence_packet_manifest.json"
    if evidence_path.exists():
        try:
            evidence_manifest = read_json(evidence_path)
        except Exception as exc:  # noqa: BLE001 - surfaced as preflight failure text
            errors.append(f"handoff preflight cannot read evidence_packet_manifest.json: {exc}")
            evidence_manifest = {}

        evidence_records = set(evidence_manifest.get("records", []))
        for name in EVIDENCE_PACKET_REFERENCED_RECORDS:
            if name not in evidence_records:
                errors.append(f"handoff preflight evidence packet does not include required record: {name}")
    else:
        evidence_manifest = {}

    telemetry_path = run_dir / "telemetry" / "simulated_flow_sensor_A.csv"
    if not telemetry_path.exists():
        errors.append("handoff preflight missing required telemetry candidate: telemetry/simulated_flow_sensor_A.csv")

    run_state_path = run_dir / "run_state_chain.json"
    if run_state_path.exists():
        try:
            run_state = read_json(run_state_path)
        except Exception as exc:  # noqa: BLE001 - surfaced as preflight failure text
            errors.append(f"handoff preflight cannot read run_state_chain.json: {exc}")
            run_state = {}
        if run_state.get("terminal_state") != "handoff_prepared":
            errors.append("handoff preflight requires run_state_chain.json terminal_state=handoff_prepared")

    known_gaps = evidence_manifest.get("known_gaps", []) if isinstance(evidence_manifest, dict) else []
    if not isinstance(known_gaps, list):
        errors.append("handoff preflight evidence_packet_manifest.json known_gaps must be a list")

    return errors


def build_neuml_handoff_manifest(run_dir: str | Path) -> dict:
    """Build a future-ingestion manifest without calling NeuML, txtai, or PaperAI.

    The manifest is only a boundary artifact. It says what a future consumer may
    index or inspect, while preserving that evidence packets are not proof and
    handoff is not promotion.
    """

    run_dir = Path(run_dir)
    preflight_errors = validate_handoff_preconditions(run_dir)
    if preflight_errors:
        details = "; ".join(preflight_errors)
        raise ValueError(f"TraceLab refuses to prepare NeuML handoff for an incomplete run: {details}")

    evidence_path = run_dir / "evidence_packet_manifest.json"
    evidence_manifest = read_json(evidence_path) if evidence_path.exists() else {}

    records_included = _existing_paths(run_dir, [*RECORD_CANDIDATES, *OPTIONAL_HANDOFF_RECORDS])
    telemetry_candidates = _existing_paths(run_dir, TELEMETRY_DATA_CANDIDATES)

    known_gaps = list(evidence_manifest.get("known_gaps", []))
    if "No NeuML/txtai/PaperAI execution is performed by TraceLab v0.1." not in known_gaps:
        known_gaps.append("No NeuML/txtai/PaperAI execution is performed by TraceLab v0.1.")

    not_proven_claims = list(evidence_manifest.get("not_proven_claims", []))
    for claim in [
        "Handoff consumer correctness",
        "Scientific truth",
        "Physical execution readiness",
        "Durable claim promotion",
    ]:
        if claim not in not_proven_claims:
            not_proven_claims.append(claim)

    return {
        "record_type": "neuml_handoff_manifest",
        "created_at": now(),
        "handoff_status": "prepared_for_future_ingestion_only",
        "possible_consumers": ["txtai", "paperai", "paperetl", "run-lab", "evidence-ai-core"],
        "evidence_packet_path": "evidence_packet_manifest.json",
        "records_included": records_included,
        "text_index_candidates": _existing_paths(run_dir, TEXT_INDEX_CANDIDATES),
        "telemetry_data_candidates": telemetry_candidates,
        "report_candidates": _existing_paths(run_dir, REPORT_CANDIDATES),
        "known_gaps": known_gaps,
        "not_proven_claims": not_proven_claims,
        "recommended_ingestion_hints": {
            "txtai": [
                "Index JSON records as text documents with path metadata.",
                "Index telemetry manifests as metadata before indexing raw telemetry tables.",
            ],
            "paperai": [
                "Use evidence_packet_manifest.json, validation_record.json, and review_record.json as report context.",
                "Preserve not_proven_claims in generated summaries.",
            ],
            "paperetl": [
                "Treat telemetry CSV files as candidate tabular artifacts, not validated scientific datasets.",
            ],
        },
        "authority_flags": {
            "agent_approved": False,
            "scientific_truth_validated": False,
            "physical_execution_completed": False,
            "state_promoted": False,
            "handoff_promotes_claims": False,
        },
        "authority_note": "NeuML handoff is a future-ingestion manifest only; it does not approve, validate truth, execute hardware, or promote claims.",
    }


def write_neuml_handoff_manifest(run_dir: str | Path) -> Path:
    run_dir = Path(run_dir)
    manifest = build_neuml_handoff_manifest(run_dir)
    path = run_dir / "neuml_handoff_manifest.json"
    write_json(path, manifest)
    return path
