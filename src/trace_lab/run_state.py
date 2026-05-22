from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import read_json, write_json
from .records import now

ALLOWED_RUN_STATE_SEQUENCE = [
    "requested",
    "planned",
    "approved_for_simulation_only",
    "dry_run_checked",
    "simulated_action_recorded",
    "telemetry_recorded",
    "evidence_packet_built",
    "operationally_validated",
    "review_required",
    "handoff_prepared",
]

STATE_RECORD_MAP = {
    "requested": "experiment_request.json",
    "planned": "run_plan.json",
    "approved_for_simulation_only": "approval_record.json",
    "dry_run_checked": "dry_run_record.json",
    "simulated_action_recorded": "adapter_action_record.json",
    "telemetry_recorded": "telemetry_manifest.json",
    "evidence_packet_built": "evidence_packet_manifest.json",
    "operationally_validated": "validation_record.json",
    "review_required": "review_record.json",
    "handoff_prepared": "neuml_handoff_manifest.json",
}

BOUNDARY_NOTES = [
    "evidence != truth",
    "operational validation != scientific validity",
    "approval record != agent permission",
    "dry-run != physical execution",
    "NeuML handoff != claim promotion",
    "simulated adapter != hardware adapter",
]

_FORBIDDEN_STATE_TEXT = [
    "physical_execution",
    "hardware_execution",
    "hardware_executed",
    "scientific_truth",
    "truth_validated",
    "claim_promotion",
    "claim_promoted",
    "state_promoted",
    "promoted_claim",
]


def build_run_state_chain() -> dict[str, Any]:
    """Return the fixed v0.1 simulation-only operational lifecycle.

    The chain is intentionally deterministic. It describes which evidence record
    supports each lifecycle state, but it does not turn operational validation
    into scientific truth or promotion authority.
    """

    return {
        "record_type": "run_state_chain",
        "contract_version": "trace_lab.run_state.v0_1",
        "created_at": now(),
        "lifecycle_scope": "operational_simulation_only",
        "terminal_state": "handoff_prepared",
        "states": [
            {
                "state_index": index,
                "state": state,
                "supported_by": STATE_RECORD_MAP[state],
                "status": "recorded",
                "physical_execution_completed": False,
                "scientific_truth_validated": False,
                "state_promoted": False,
            }
            for index, state in enumerate(ALLOWED_RUN_STATE_SEQUENCE)
        ],
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": "Run-state validation is operational trace validation only; it does not approve hardware execution, validate scientific truth, or promote claims.",
    }


def write_run_state_chain(run_dir: str | Path) -> Path:
    run_dir = Path(run_dir)
    path = run_dir / "run_state_chain.json"
    write_json(path, build_run_state_chain())
    return path


def _state_name(item: Any) -> str | None:
    if isinstance(item, dict):
        value = item.get("state")
        return value if isinstance(value, str) else None
    return None


def _has_forbidden_state_text(state_name: str | None) -> bool:
    if not state_name:
        return False
    normalized = state_name.lower().replace("-", "_").replace(" ", "_")
    return any(term in normalized for term in _FORBIDDEN_STATE_TEXT)


def validate_run_state_chain(run_dir: str | Path, chain: dict[str, Any], parsed_records: dict[str, dict]) -> list[str]:
    """Validate the v0.1 state-machine contract against run records."""

    run_dir = Path(run_dir)
    errors: list[str] = []

    if not isinstance(chain, dict):
        return ["run_state_chain.json is not a JSON object."]

    if chain.get("record_type") != "run_state_chain":
        errors.append("run_state_chain.json record_type must be 'run_state_chain'.")
    if chain.get("lifecycle_scope") != "operational_simulation_only":
        errors.append("run_state_chain.json lifecycle_scope must be operational_simulation_only.")
    if chain.get("terminal_state") != "handoff_prepared":
        errors.append("run_state_chain.json terminal_state must be handoff_prepared.")

    states = chain.get("states")
    if not isinstance(states, list):
        return errors + ["run_state_chain.json states must be a list."]

    names = [_state_name(item) for item in states]
    valid_names = [name for name in names if name]
    allowed = set(ALLOWED_RUN_STATE_SEQUENCE)
    allowed_index = {state: index for index, state in enumerate(ALLOWED_RUN_STATE_SEQUENCE)}

    for index, item in enumerate(states):
        if not isinstance(item, dict):
            errors.append(f"run_state_chain.json states[{index}] is not an object.")
            continue
        name = _state_name(item)
        if not name:
            errors.append(f"run_state_chain.json states[{index}] has no state name.")
            continue
        if _has_forbidden_state_text(name):
            errors.append(f"run_state_chain.json state implies forbidden authority or physical execution: {name}")
        if name not in allowed:
            errors.append(f"run_state_chain.json contains unknown state: {name}")
            continue

        expected_supported_by = STATE_RECORD_MAP[name]
        if item.get("supported_by") != expected_supported_by:
            errors.append(
                f"run_state_chain.json state {name} must be supported_by {expected_supported_by}."
            )
        if item.get("physical_execution_completed") is not False:
            errors.append(f"run_state_chain.json state {name} cannot claim physical execution.")
        if item.get("scientific_truth_validated") is not False:
            errors.append(f"run_state_chain.json state {name} cannot claim scientific truth validation.")
        if item.get("state_promoted") is not False:
            errors.append(f"run_state_chain.json state {name} cannot claim state promotion.")

        supported_path = run_dir / expected_supported_by
        if not supported_path.exists() or expected_supported_by not in parsed_records:
            errors.append(
                f"run_state_chain.json state {name} is not supported by existing record {expected_supported_by}."
            )

    for required in ALLOWED_RUN_STATE_SEQUENCE:
        if required not in valid_names:
            errors.append(f"run_state_chain.json missing required state: {required}")

    seen: set[str] = set()
    for name in valid_names:
        if name in seen:
            errors.append(f"run_state_chain.json contains duplicate state: {name}")
        seen.add(name)

    known_order = [allowed_index[name] for name in valid_names if name in allowed_index]
    for previous, current in zip(known_order, known_order[1:]):
        if current < previous:
            errors.append("run_state_chain.json contains a backward transition.")
        elif current > previous + 1:
            errors.append("run_state_chain.json contains a skipped state transition.")

    positions = {name: index for index, name in enumerate(valid_names)}
    if (
        "handoff_prepared" in positions
        and "review_required" in positions
        and positions["handoff_prepared"] < positions["review_required"]
    ):
        errors.append("run_state_chain.json cannot prepare handoff before review_required.")
    if (
        "operationally_validated" in positions
        and "evidence_packet_built" in positions
        and positions["operationally_validated"] < positions["evidence_packet_built"]
    ):
        errors.append("run_state_chain.json cannot validate operationally before evidence_packet_built.")

    errors.extend(_validate_state_record_semantics(parsed_records))
    return errors


def _validate_state_record_semantics(parsed: dict[str, dict]) -> list[str]:
    errors: list[str] = []
    request = parsed.get("experiment_request.json", {})
    plan = parsed.get("run_plan.json", {})
    approval = parsed.get("approval_record.json", {})
    dry_run = parsed.get("dry_run_record.json", {})
    action = parsed.get("adapter_action_record.json", {})
    telemetry = parsed.get("telemetry_manifest.json", {})
    evidence = parsed.get("evidence_packet_manifest.json", {})
    validation = parsed.get("validation_record.json", {})
    review = parsed.get("review_record.json", {})
    handoff = parsed.get("neuml_handoff_manifest.json", {})

    if request and request.get("status") != "created":
        errors.append("State requested requires experiment_request.json status=created.")
    if plan and plan.get("status") != "proposed":
        errors.append("State planned requires run_plan.json status=proposed.")
    if approval and approval.get("decision") != "approved_for_simulation_only":
        errors.append("State approved_for_simulation_only requires approval_record.json decision=approved_for_simulation_only.")
    if plan and plan.get("dry_run_required") is not True:
        errors.append("State dry_run_checked requires run_plan.json dry_run_required=true.")
    if dry_run and dry_run.get("dry_run_status") != "passed":
        errors.append("State dry_run_checked requires dry_run_record.json dry_run_status=passed.")
    if action and action.get("execution_mode") != "simulated":
        errors.append("State simulated_action_recorded requires adapter_action_record.json execution_mode=simulated.")
    if telemetry and telemetry.get("telemetry_status") != "complete_for_simulation":
        errors.append("State telemetry_recorded requires telemetry_manifest.json telemetry_status=complete_for_simulation.")
    if evidence and evidence.get("record_type") != "evidence_packet_manifest":
        errors.append("State evidence_packet_built requires evidence_packet_manifest.json.")
    if validation and validation.get("validation_scope") != "operational_simulation_only":
        errors.append("State operationally_validated requires validation_record.json validation_scope=operational_simulation_only.")
    if review and review.get("decision") != "review_required":
        errors.append("State review_required requires review_record.json decision=review_required.")
    if review and review.get("review_status") != "pending_human_trace_review":
        errors.append("State review_required requires review_record.json review_status=pending_human_trace_review.")
    if review and review.get("human_review_required") is not True:
        errors.append("State review_required requires review_record.json human_review_required=true.")
    if handoff and handoff.get("handoff_status") != "prepared_for_future_ingestion_only":
        errors.append("State handoff_prepared requires neuml_handoff_manifest.json handoff_status=prepared_for_future_ingestion_only.")

    return errors


def build_run_state_summary(run_dir: str | Path) -> dict[str, Any]:
    run_dir = Path(run_dir)
    chain_path = run_dir / "run_state_chain.json"
    if chain_path.exists():
        chain = read_json(chain_path)
    else:
        chain = {}

    parsed: dict[str, dict] = {}
    for name in STATE_RECORD_MAP.values():
        path = run_dir / name
        if path.exists():
            try:
                parsed[name] = read_json(path)
            except Exception:
                parsed[name] = {}

    state_errors = validate_run_state_chain(run_dir, chain, parsed)
    states = chain.get("states", []) if isinstance(chain, dict) else []
    state_names = [item.get("state") for item in states if isinstance(item, dict)]

    return {
        "record_type": "run_state_summary",
        "state_summary_status": "complete_simulation_only" if not state_errors else "failed_operational_checks",
        "lifecycle_scope": "operational_simulation_only",
        "state_count": len(state_names),
        "states": state_names,
        "terminal_state": state_names[-1] if state_names else None,
        "state_errors": state_errors,
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": "State summary is an operator-facing trace view only; it does not validate scientific truth, execute hardware, or promote claims.",
    }


def write_run_state_summary(run_dir: str | Path) -> Path:
    run_dir = Path(run_dir)
    path = run_dir / "run_state_summary.json"
    write_json(path, build_run_state_summary(run_dir))
    return path
