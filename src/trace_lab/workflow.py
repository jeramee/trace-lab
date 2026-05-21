from __future__ import annotations
from pathlib import Path
import csv
from .io import write_json, sha256_file
from .records import now, default_authority_flags
from .adapters import SimulatedAdapter

def run_simulated_experiment(out: str | Path) -> Path:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "telemetry").mkdir(exist_ok=True)
    adapter = SimulatedAdapter()
    created = now()

    request = {
        "record_type": "experiment_request",
        "request_id": "request_demo_001",
        "created_at": created,
        "research_question": "Can a simulated flow reading be captured as traceable evidence?",
        "status": "created",
        "authority_flags": default_authority_flags(),
    }
    plan = {
        "record_type": "run_plan",
        "run_plan_id": "plan_demo_001",
        "request_id": request["request_id"],
        "steps": [{"step_id": "step_001", "action_type": "capture_simulated_flow"}],
        "approval_required": True,
        "dry_run_required": True,
        "status": "proposed",
    }
    approval = {
        "record_type": "approval_record",
        "approval_id": "approval_demo_001",
        "run_plan_id": plan["run_plan_id"],
        "decision": "approved_for_simulation_only",
        "approval_scope": "simulation_only",
        "physical_execution_allowed": False,
    }
    dry_run = adapter.dry_run("capture_simulated_flow", {"duration_seconds": 3})
    action = adapter.simulate_action("action_demo_001", "capture_simulated_flow", {"duration_seconds": 3})

    telemetry_file = out / "telemetry" / "simulated_flow_sensor_A.csv"
    with telemetry_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["t", "flow"])
        writer.writeheader()
        for i in range(3):
            writer.writerow({"t": i, "flow": 1.0 + i * 0.1})

    telemetry = {
        "record_type": "telemetry_manifest",
        "telemetry_manifest_id": "telemetry_demo_001",
        "run_id": "run_demo_001",
        "data_files": [{"path": "telemetry/simulated_flow_sensor_A.csv", "hash": sha256_file(telemetry_file)}],
        "missing_channels": [],
        "telemetry_status": "complete_for_simulation",
    }
    validation = {
        "record_type": "validation_record",
        "validation_id": "validation_demo_001",
        "checks": [
            {"check_id": "telemetry_file_exists", "status": "passed"},
            {"check_id": "physical_execution_not_allowed", "status": "passed"},
        ],
        "validation_scope": "operational_simulation_only",
        "scientific_truth_validated": False,
    }
    lab_run = {
        "record_type": "lab_run_record",
        "run_id": "run_demo_001",
        "request_id": request["request_id"],
        "run_plan_id": plan["run_plan_id"],
        "action_record_refs": ["adapter_action_record.json"],
        "telemetry_manifest_refs": ["telemetry_manifest.json"],
        "status": "completed_simulated",
        "physical_execution_completed": False,
    }
    review = {
        "record_type": "review_record",
        "review_id": "review_demo_001",
        "run_id": lab_run["run_id"],
        "decision": "review_required",
        "claims_promoted": [],
        "state_promoted": False,
    }

    records = {
        "experiment_request.json": request,
        "run_plan.json": plan,
        "adapter_capability_manifest.json": adapter.capability_manifest(),
        "approval_record.json": approval,
        "dry_run_record.json": dry_run,
        "adapter_action_record.json": action,
        "telemetry_manifest.json": telemetry,
        "validation_record.json": validation,
        "lab_run_record.json": lab_run,
        "review_record.json": review,
    }
    for name, data in records.items():
        write_json(out / name, data)

    evidence_manifest = {
        "record_type": "evidence_packet_manifest",
        "run_id": lab_run["run_id"],
        "created_at": created,
        "records": sorted(records),
        "artifacts": [{"path": "telemetry/simulated_flow_sensor_A.csv", "hash": sha256_file(telemetry_file)}],
        "known_gaps": ["Simulation only. No hardware integration."],
        "not_proven_claims": ["Scientific truth", "physical safety validation", "hardware readiness"],
    }
    write_json(out / "evidence_packet_manifest.json", evidence_manifest)

    handoff = {
        "record_type": "neuml_handoff_manifest",
        "handoff_status": "future_adapter_note",
        "possible_consumers": ["evidence-ai-core", "run-lab", "txtai", "paperai"],
        "authority_note": "Handoff does not promote claims.",
    }
    write_json(out / "neuml_handoff_manifest.json", handoff)
    return out
