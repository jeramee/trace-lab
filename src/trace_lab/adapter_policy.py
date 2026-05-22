from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import read_json, write_json
from .records import now

ADAPTER_BOUNDARY_SUMMARY_FILE = "adapter_boundary_summary.json"
SIMULATED_ADAPTER_ID = "simulated_adapter_v0_1"
SIMULATION_ONLY_MODE = "simulation_only"
SIMULATED_EXECUTION_MODE = "simulated"
SIMULATED_EXECUTION_STATUS = "completed_simulated"
DRY_RUN_STATUS_PASSED = "passed"

BOUNDARY_NOTES = [
    "evidence != truth",
    "operational validation != scientific validity",
    "approval record != agent permission",
    "dry-run != physical execution",
    "NeuML handoff != claim promotion",
    "simulated adapter != hardware adapter",
]

FORBIDDEN_ADAPTER_FIELDS = [
    "hardware_api",
    "hardware_endpoint",
    "device_endpoint",
    "device_path",
    "serial_port",
    "labview_vi_path",
    "opcua_endpoint",
    "modbus_address",
    "driver_module",
]


def _field_is_present(value: object) -> bool:
    return value not in (None, "", [], {}, False)


def _planned_action_types(plan: dict[str, Any]) -> set[str]:
    return {
        step.get("action_type")
        for step in plan.get("steps", [])
        if isinstance(step, dict) and step.get("action_type")
    }


def _check_forbidden_fields(record_name: str, record: dict[str, Any]) -> tuple[list[str], list[str]]:
    adapter_errors: list[str] = []
    unsafe: list[str] = []

    for field in FORBIDDEN_ADAPTER_FIELDS:
        if _field_is_present(record.get(field)):
            unsafe.append(f"{record_name} cannot declare {field} in v0.1 simulation.")

    return adapter_errors, unsafe


def validate_adapter_boundary(
    capability: dict[str, Any],
    dry_run: dict[str, Any],
    action: dict[str, Any],
    plan: dict[str, Any] | None = None,
) -> dict[str, list[str]]:
    """Validate the TraceLab v0.1 simulated-adapter boundary.

    This function checks the adapter evidence contract only. It does not call a
    hardware adapter, test physical safety, approve execution, validate
    scientific truth, or promote claims.
    """

    adapter_errors: list[str] = []
    unsafe: list[str] = []
    plan = plan or {}

    for name, record, expected_type in [
        ("adapter_capability_manifest.json", capability, "adapter_capability_manifest"),
        ("dry_run_record.json", dry_run, "dry_run_record"),
        ("adapter_action_record.json", action, "adapter_action_record"),
    ]:
        if not isinstance(record, dict):
            adapter_errors.append(f"{name} must be a JSON object.")
            continue
        if record.get("record_type") != expected_type:
            adapter_errors.append(f"{name} record_type must be {expected_type}.")
        field_errors, field_unsafe = _check_forbidden_fields(name, record)
        adapter_errors.extend(field_errors)
        unsafe.extend(field_unsafe)

    adapter_id = capability.get("adapter_id")
    if adapter_id != SIMULATED_ADAPTER_ID:
        adapter_errors.append(f"adapter_capability_manifest.json adapter_id must be {SIMULATED_ADAPTER_ID}.")
    if capability.get("mode") != SIMULATION_ONLY_MODE:
        unsafe.append("adapter_capability_manifest.json mode must be simulation_only in v0.1.")
    if capability.get("can_observe") is not True:
        adapter_errors.append("adapter_capability_manifest.json must set can_observe=true.")
    if capability.get("can_dry_run") is not True:
        adapter_errors.append("adapter_capability_manifest.json must set can_dry_run=true.")
    if capability.get("can_execute_physical_actions") is not False:
        unsafe.append("adapter_capability_manifest.json must set can_execute_physical_actions=false.")
    if capability.get("requires_human_approval") is not True:
        adapter_errors.append("adapter_capability_manifest.json must set requires_human_approval=true.")

    for name, record in [
        ("dry_run_record.json", dry_run),
        ("adapter_action_record.json", action),
    ]:
        if record.get("adapter_id") != adapter_id:
            adapter_errors.append(f"{name} adapter_id must match adapter_capability_manifest.json.")

    if dry_run.get("dry_run_status") != DRY_RUN_STATUS_PASSED:
        adapter_errors.append("dry_run_record.json dry_run_status must be passed for the v0.1 demo trace.")
    if dry_run.get("physical_execution_completed") is not False:
        unsafe.append("dry_run_record.json must set physical_execution_completed=false.")

    if action.get("execution_mode") != SIMULATED_EXECUTION_MODE:
        unsafe.append("adapter_action_record.json execution_mode must be simulated.")
    if action.get("execution_status") != SIMULATED_EXECUTION_STATUS:
        adapter_errors.append("adapter_action_record.json execution_status must be completed_simulated.")
    if action.get("physical_execution_completed") is not False:
        unsafe.append("adapter_action_record.json must set physical_execution_completed=false.")

    planned = _planned_action_types(plan)
    for name, record in [
        ("dry_run_record.json", dry_run),
        ("adapter_action_record.json", action),
    ]:
        action_type = record.get("action_type")
        if action_type and planned and action_type not in planned:
            adapter_errors.append(f"{name} action_type is not declared in run_plan.json steps.")

    if dry_run.get("action_type") and action.get("action_type") and dry_run.get("action_type") != action.get("action_type"):
        adapter_errors.append("dry_run_record.json and adapter_action_record.json action_type values must match.")

    if dry_run.get("parameters") != action.get("parameters"):
        adapter_errors.append("dry_run_record.json parameters must match adapter_action_record.json parameters.")

    return {"adapter_errors": adapter_errors, "unsafe": unsafe}


def build_adapter_boundary_summary(run_dir: str | Path) -> dict[str, Any]:
    """Build an operator-facing adapter-boundary summary."""

    run_dir = Path(run_dir)
    capability_path = run_dir / "adapter_capability_manifest.json"
    dry_run_path = run_dir / "dry_run_record.json"
    action_path = run_dir / "adapter_action_record.json"
    plan_path = run_dir / "run_plan.json"

    capability = read_json(capability_path) if capability_path.exists() else {}
    dry_run = read_json(dry_run_path) if dry_run_path.exists() else {}
    action = read_json(action_path) if action_path.exists() else {}
    plan = read_json(plan_path) if plan_path.exists() else {}

    validation = validate_adapter_boundary(capability, dry_run, action, plan)
    adapter_errors = list(validation.get("adapter_errors", []))
    unsafe = list(validation.get("unsafe", []))
    status = "simulation_only_boundary_intact" if not adapter_errors and not unsafe else "invalid_adapter_boundary"

    return {
        "record_type": "adapter_boundary_summary",
        "created_at": now(),
        "adapter_boundary_status": status,
        "adapter_id": capability.get("adapter_id"),
        "adapter_mode": capability.get("mode"),
        "can_execute_physical_actions": capability.get("can_execute_physical_actions"),
        "dry_run_status": dry_run.get("dry_run_status"),
        "execution_mode": action.get("execution_mode"),
        "execution_status": action.get("execution_status"),
        "physical_execution_completed": action.get("physical_execution_completed"),
        "adapter_errors": adapter_errors,
        "unsafe": unsafe,
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": "Adapter boundary summary is an operator-facing trace view only; it does not call hardware, approve execution, validate scientific truth, or promote claims.",
    }


def write_adapter_boundary_summary(run_dir: str | Path) -> Path:
    run_dir = Path(run_dir)
    path = run_dir / ADAPTER_BOUNDARY_SUMMARY_FILE
    write_json(path, build_adapter_boundary_summary(run_dir))
    return path
