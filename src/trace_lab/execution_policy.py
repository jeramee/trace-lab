from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import read_json, write_json
from .records import now

EXECUTION_POLICY_FILE = "execution_policy_manifest.json"
EXECUTION_POLICY_SUMMARY_FILE = "execution_policy_summary.json"

BOUNDARY_NOTES = [
    "evidence != truth",
    "operational validation != scientific validity",
    "approval record != agent permission",
    "dry-run != physical execution",
    "NeuML handoff != claim promotion",
    "simulated adapter != hardware adapter",
]


def build_execution_policy_manifest(*, created_at: str | None = None) -> dict[str, Any]:
    """Build the v0.1 execution/retry policy record.

    This is a policy boundary artifact only. It does not execute actions, approve
    actions, retry actions, validate scientific truth, or promote claims.
    """

    return {
        "record_type": "execution_policy_manifest",
        "created_at": created_at or now(),
        "policy_scope": "operational_simulation_only",
        "execution_mode": "simulated",
        "physical_execution_allowed": False,
        "automatic_retry_allowed": False,
        "automatic_retry_performed": False,
        "retry_attempt_count": 0,
        "hidden_retry_allowed": False,
        "human_approval_required_for_retry": True,
        "agent_can_approve_retry": False,
        "agent_can_execute_physical_action": False,
        "agent_can_promote_claims": False,
        "network_calls_allowed": False,
        "package_installation_allowed": False,
        "hardware_access_allowed": False,
        "allowed_actions": ["capture_simulated_flow"],
        "blocked_actions": [
            "physical_device_execution",
            "hardware_driver_call",
            "gui_automation",
            "silent_retry",
            "claim_promotion",
            "scientific_truth_validation",
        ],
        "authority_flags": {
            "agent_approved": False,
            "physical_execution_completed": False,
            "scientific_truth_validated": False,
            "state_promoted": False,
            "claims_promoted": False,
            "automatic_retry_performed": False,
            "hidden_retry_performed": False,
            "hardware_access_performed": False,
            "network_calls_performed": False,
            "package_installation_performed": False,
        },
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": "Execution policy is a simulation-only control boundary; it does not approve, execute hardware, retry silently, validate scientific truth, or promote claims.",
    }


def validate_execution_policy_manifest(policy: dict[str, Any]) -> dict[str, list[str]]:
    """Validate the execution/retry policy boundary for TraceLab v0.1."""

    policy_errors: list[str] = []
    unsafe: list[str] = []

    if not isinstance(policy, dict):
        return {
            "policy_errors": ["execution_policy_manifest.json is not a JSON object."],
            "unsafe": [],
        }

    if policy.get("record_type") != "execution_policy_manifest":
        policy_errors.append("execution_policy_manifest.json record_type must be execution_policy_manifest.")
    if policy.get("policy_scope") != "operational_simulation_only":
        policy_errors.append("execution_policy_manifest.json policy_scope must be operational_simulation_only.")
    if policy.get("execution_mode") != "simulated":
        policy_errors.append("execution_policy_manifest.json execution_mode must be simulated.")

    false_required = [
        "physical_execution_allowed",
        "automatic_retry_allowed",
        "automatic_retry_performed",
        "hidden_retry_allowed",
        "agent_can_approve_retry",
        "agent_can_execute_physical_action",
        "agent_can_promote_claims",
        "network_calls_allowed",
        "package_installation_allowed",
        "hardware_access_allowed",
    ]
    for field in false_required:
        if policy.get(field) is not False:
            unsafe.append(f"execution_policy_manifest.json must keep {field}=false in v0.1 simulation.")

    if policy.get("human_approval_required_for_retry") is not True:
        policy_errors.append("execution_policy_manifest.json must require human approval for any retry boundary.")
    if policy.get("retry_attempt_count") != 0:
        unsafe.append("execution_policy_manifest.json retry_attempt_count must remain 0 in v0.1 demo runs.")

    allowed_actions = policy.get("allowed_actions", [])
    if not isinstance(allowed_actions, list):
        policy_errors.append("execution_policy_manifest.json allowed_actions must be a list.")
    elif "capture_simulated_flow" not in allowed_actions:
        policy_errors.append("execution_policy_manifest.json allowed_actions must include capture_simulated_flow.")

    blocked_actions = policy.get("blocked_actions", [])
    if not isinstance(blocked_actions, list):
        policy_errors.append("execution_policy_manifest.json blocked_actions must be a list.")
    else:
        for blocked in [
            "physical_device_execution",
            "hardware_driver_call",
            "gui_automation",
            "silent_retry",
            "claim_promotion",
            "scientific_truth_validation",
        ]:
            if blocked not in blocked_actions:
                policy_errors.append(f"execution_policy_manifest.json blocked_actions missing {blocked}.")

    flags = policy.get("authority_flags", {})
    if not isinstance(flags, dict):
        policy_errors.append("execution_policy_manifest.json authority_flags must be an object.")
        flags = {}

    for flag in [
        "agent_approved",
        "physical_execution_completed",
        "scientific_truth_validated",
        "state_promoted",
        "claims_promoted",
        "automatic_retry_performed",
        "hidden_retry_performed",
        "hardware_access_performed",
        "network_calls_performed",
        "package_installation_performed",
    ]:
        if flags.get(flag):
            unsafe.append(f"execution_policy_manifest.json cannot set authority_flags.{flag}=true in v0.1 simulation.")

    notes = policy.get("boundary_notes", [])
    if not isinstance(notes, list):
        policy_errors.append("execution_policy_manifest.json boundary_notes must be a list.")
    else:
        for note in BOUNDARY_NOTES:
            if note not in notes:
                policy_errors.append(f"execution_policy_manifest.json boundary_notes missing: {note}")

    return {"policy_errors": policy_errors, "unsafe": unsafe}


def build_execution_policy_summary(run_dir: str | Path) -> dict[str, Any]:
    """Build an operator-facing summary of the execution/retry boundary."""

    run_dir = Path(run_dir)
    policy_path = run_dir / EXECUTION_POLICY_FILE
    if policy_path.exists():
        policy = read_json(policy_path)
    else:
        policy = {}

    validation = validate_execution_policy_manifest(policy)
    policy_errors = validation.get("policy_errors", [])
    unsafe = validation.get("unsafe", [])

    return {
        "record_type": "execution_policy_summary",
        "created_at": now(),
        "policy_summary_status": "simulation_policy_intact" if not policy_errors and not unsafe else "failed_simulation_policy_checks",
        "policy_scope": policy.get("policy_scope"),
        "execution_mode": policy.get("execution_mode"),
        "physical_execution_allowed": policy.get("physical_execution_allowed"),
        "automatic_retry_allowed": policy.get("automatic_retry_allowed"),
        "automatic_retry_performed": policy.get("automatic_retry_performed"),
        "retry_attempt_count": policy.get("retry_attempt_count"),
        "hidden_retry_allowed": policy.get("hidden_retry_allowed"),
        "human_approval_required_for_retry": policy.get("human_approval_required_for_retry"),
        "policy_errors": policy_errors,
        "unsafe": unsafe,
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": "Execution policy summary is an operator-facing trace view only; it does not approve, retry, execute hardware, validate scientific truth, or promote claims.",
    }


def write_execution_policy_summary(run_dir: str | Path, *, force: bool = True) -> Path:
    run_dir = Path(run_dir)
    path = run_dir / EXECUTION_POLICY_SUMMARY_FILE
    if path.exists() and not force:
        raise FileExistsError(
            "TraceLab refuses to overwrite execution_policy_summary.json without force=True."
        )
    write_json(path, build_execution_policy_summary(run_dir))
    return path
