from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import read_json, write_json
from .records import now

REVIEW_RECORD_FILE = "review_record.json"
REVIEW_SUMMARY_FILE = "review_summary.json"
REVIEW_STATUS_PENDING = "pending_human_trace_review"
REVIEW_SCOPE = "operator_trace_review_only"

BOUNDARY_NOTES = [
    "evidence != truth",
    "operational validation != scientific validity",
    "approval record != agent permission",
    "dry-run != physical execution",
    "NeuML handoff != claim promotion",
    "simulated adapter != hardware adapter",
]


def build_review_record(run_id: str, *, created_at: str | None = None) -> dict[str, Any]:
    """Build the v0.1 human-review gate record.

    This record intentionally leaves the run in a human-review-required state.
    It is not a claim approval, truth validation, physical execution approval,
    or durable promotion.
    """

    return {
        "record_type": "review_record",
        "review_id": "review_demo_001",
        "run_id": run_id,
        "created_at": created_at or now(),
        "decision": "review_required",
        "review_status": REVIEW_STATUS_PENDING,
        "review_scope": REVIEW_SCOPE,
        "human_review_required": True,
        "human_review_completed": False,
        "reviewer_role_required": "human_operator_or_researcher",
        "reviewed_by": None,
        "agent_reviewed": False,
        "automatic_promotion_allowed": False,
        "promotion_recommendation": "none",
        "review_findings": [],
        "claims_promoted": [],
        "state_promoted": False,
        "authority_flags": {
            "agent_approved": False,
            "agent_reviewed": False,
            "physical_execution_completed": False,
            "scientific_truth_validated": False,
            "state_promoted": False,
            "claims_promoted": False,
            "automatic_promotion_allowed": False,
        },
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": "Review is a human-required trace checkpoint only; it does not validate scientific truth, approve hardware execution, or promote claims.",
    }


def validate_review_record(review: dict[str, Any]) -> dict[str, list[str]]:
    """Validate v0.1 review-gate semantics.

    Returned errors are operational record errors, not scientific judgments.
    """

    review_errors: list[str] = []
    unsafe: list[str] = []

    if not isinstance(review, dict):
        return {
            "review_errors": ["review_record.json is not a JSON object."],
            "unsafe": [],
        }

    if review.get("record_type") != "review_record":
        review_errors.append("review_record.json record_type must be review_record.")
    if review.get("decision") != "review_required":
        review_errors.append("review_record.json decision must be review_required in v0.1.")
    if review.get("review_status") != REVIEW_STATUS_PENDING:
        review_errors.append(f"review_record.json review_status must be {REVIEW_STATUS_PENDING} in v0.1.")
    if review.get("review_scope") != REVIEW_SCOPE:
        review_errors.append(f"review_record.json review_scope must be {REVIEW_SCOPE}.")
    if review.get("human_review_required") is not True:
        review_errors.append("review_record.json must set human_review_required=true.")
    if review.get("human_review_completed") is not False:
        review_errors.append("review_record.json human_review_completed must remain false in the v0.1 demo trace.")
    if review.get("reviewer_role_required") != "human_operator_or_researcher":
        review_errors.append("review_record.json reviewer_role_required must be human_operator_or_researcher.")
    if review.get("reviewed_by") is not None:
        review_errors.append("review_record.json reviewed_by must remain null until an actual human review workflow exists.")
    if review.get("promotion_recommendation") != "none":
        unsafe.append("Review records cannot recommend claim or state promotion in v0.1 simulation.")
    if review.get("review_findings") not in ([], None):
        review_errors.append("review_record.json review_findings must remain empty in the v0.1 demo trace.")

    if review.get("agent_reviewed") is not False:
        unsafe.append("Review records cannot claim agent_reviewed=true in v0.1 simulation.")
    if review.get("automatic_promotion_allowed") is not False:
        unsafe.append("Review records cannot allow automatic promotion in v0.1 simulation.")
    if review.get("state_promoted") is not False:
        unsafe.append("Review records cannot promote durable state in v0.1 simulation.")
    if review.get("claims_promoted"):
        unsafe.append("Review records cannot promote claims in v0.1 simulation.")

    flags = review.get("authority_flags", {})
    if not isinstance(flags, dict):
        review_errors.append("review_record.json authority_flags must be an object.")
        flags = {}

    for flag in [
        "agent_approved",
        "agent_reviewed",
        "physical_execution_completed",
        "scientific_truth_validated",
        "state_promoted",
        "claims_promoted",
        "automatic_promotion_allowed",
    ]:
        if flags.get(flag):
            unsafe.append(f"Review records cannot set authority_flags.{flag}=true in v0.1 simulation.")

    notes = review.get("boundary_notes", [])
    if not isinstance(notes, list):
        review_errors.append("review_record.json boundary_notes must be a list.")
    else:
        for note in BOUNDARY_NOTES:
            if note not in notes:
                review_errors.append(f"review_record.json boundary_notes missing required boundary: {note}")

    return {"review_errors": review_errors, "unsafe": unsafe}


def build_review_summary(run_dir: str | Path) -> dict[str, Any]:
    """Build an operator-facing review summary without completing the review."""

    run_dir = Path(run_dir)
    path = run_dir / REVIEW_RECORD_FILE
    if path.exists():
        review = read_json(path)
        validation = validate_review_record(review)
    else:
        review = {}
        validation = {"review_errors": ["review_record.json is missing."], "unsafe": []}

    review_errors = list(validation.get("review_errors", []))
    unsafe = list(validation.get("unsafe", []))
    status = (
        REVIEW_STATUS_PENDING
        if path.exists() and not review_errors and not unsafe
        else "invalid_review_gate"
    )

    return {
        "record_type": "review_summary",
        "created_at": now(),
        "review_summary_status": status,
        "review_status": review.get("review_status"),
        "review_scope": review.get("review_scope"),
        "human_review_required": review.get("human_review_required"),
        "human_review_completed": review.get("human_review_completed"),
        "agent_reviewed": review.get("agent_reviewed"),
        "promotion_recommendation": review.get("promotion_recommendation"),
        "review_errors": review_errors,
        "unsafe": unsafe,
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": "Review summary is an operator-facing trace view only; it does not complete human review, validate scientific truth, execute hardware, or promote claims.",
    }


def write_review_summary(run_dir: str | Path) -> Path:
    run_dir = Path(run_dir)
    path = run_dir / REVIEW_SUMMARY_FILE
    write_json(path, build_review_summary(run_dir))
    return path
