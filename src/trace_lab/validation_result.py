from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import write_json
from .records import now
from .validate import validate_run

VALIDATION_RESULT_FILE = "validation_result.json"
_RESULT_BUCKETS = [
    "missing",
    "json_errors",
    "telemetry_errors",
    "telemetry_profile_errors",
    "record_errors",
    "evidence_errors",
    "state_errors",
    "handoff_errors",
    "manifest_errors",
    "review_errors",
    "adapter_errors",
    "environment_errors",
    "report_errors",
    "policy_errors",
    "ingestion_errors",
    "provenance_errors",
    "closeout_errors",
    "claim_errors",
    "review_packet_errors",
    "replay_errors",
    "audit_errors",
    "recipe_errors",
    "unsafe",
]


def build_validation_result_record(run_dir: str | Path, result: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a persisted operator-facing validation-result artifact.

    This record preserves the distinction between mechanical operational checks and
    scientific truth. It is a report artifact only; it does not approve runs,
    execute hardware, retry actions, or promote claims.
    """

    result = result or validate_run(run_dir)
    result_buckets = {name: list(result.get(name, [])) for name in _RESULT_BUCKETS}
    failed_bucket_names = [name for name, values in result_buckets.items() if values]

    return {
        "record_type": "trace_lab_validation_result_record",
        "created_at": now(),
        "result_source": "trace_lab.validate.validate_run",
        "source_result_record_type": result.get("record_type"),
        "validation_status": result.get("validation_status"),
        "validation_scope": "operational_simulation_only",
        "result_buckets": result_buckets,
        "failed_bucket_names": failed_bucket_names,
        "authority_flags": {
            "agent_approved": False,
            "physical_execution_completed": False,
            "scientific_truth_validated": False,
            "state_promoted": False,
            "claims_promoted": False,
            "automatic_retry_performed": False,
        },
        "boundary_notes": [
            "evidence != truth",
            "operational validation != scientific validity",
            "approval record != agent permission",
            "dry-run != physical execution",
            "NeuML handoff != claim promotion",
            "simulated adapter != hardware adapter",
        ],
        "authority_note": "Persisted validation results are operational trace evidence only; they do not validate scientific truth or promote claims.",
    }


def write_validation_result_record(
    run_dir: str | Path,
    result: dict[str, Any] | None = None,
    *,
    force: bool = False,
) -> Path:
    """Write validation_result.json, refusing silent overwrite by default."""

    run_dir = Path(run_dir)
    path = run_dir / VALIDATION_RESULT_FILE
    if path.exists() and not force:
        raise FileExistsError(
            "TraceLab refuses to overwrite validation_result.json without --force-result. "
            "This prevents silent replacement of validation evidence."
        )

    write_json(path, build_validation_result_record(run_dir, result))
    return path
