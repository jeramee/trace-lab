from __future__ import annotations
from pathlib import Path
import json
from .io import sha256_file
from .run_state import validate_run_state_chain
from .neuml_handoff import REQUIRED_HANDOFF_RECORDS, TELEMETRY_DATA_CANDIDATES
from .run_manifest import validate_run_manifest
from .review import validate_review_record
from .adapter_policy import validate_adapter_boundary
from .runtime_environment import validate_runtime_environment_manifest
from .execution_policy import validate_execution_policy_manifest
from .telemetry_profile import validate_telemetry_profile_manifest
from .ingestion_preview import validate_ingestion_preview_manifest
from .provenance import validate_provenance_manifest
from .closeout import validate_run_closeout_manifest
from .claim_ledger import validate_claim_ledger_manifest
from .operator_review_packet import validate_operator_review_packet_manifest
from .replay_plan import validate_replay_plan_manifest
from .audit_index import validate_audit_index_manifest
from .validation_recipe import validate_validation_recipe_manifest

REQUIRED = [
    "experiment_request.json",
    "run_plan.json",
    "adapter_capability_manifest.json",
    "approval_record.json",
    "dry_run_record.json",
    "adapter_action_record.json",
    "telemetry_manifest.json",
    "telemetry_profile_manifest.json",
    "ingestion_preview_manifest.json",
    "provenance_manifest.json",
    "run_closeout_manifest.json",
    "claim_ledger_manifest.json",
    "operator_review_packet_manifest.json",
    "replay_plan_manifest.json",
    "audit_index_manifest.json",
    "validation_recipe_manifest.json",
    "validation_record.json",
    "lab_run_record.json",
    "evidence_packet_manifest.json",
    "review_record.json",
    "run_state_chain.json",
    "runtime_environment_manifest.json",
    "execution_policy_manifest.json",
    "neuml_handoff_manifest.json",
    "run_manifest.json",
]

EXPECTED_RECORD_TYPES = {
    "experiment_request.json": "experiment_request",
    "run_plan.json": "run_plan",
    "adapter_capability_manifest.json": "adapter_capability_manifest",
    "approval_record.json": "approval_record",
    "dry_run_record.json": "dry_run_record",
    "adapter_action_record.json": "adapter_action_record",
    "telemetry_manifest.json": "telemetry_manifest",
    "telemetry_profile_manifest.json": "telemetry_profile_manifest",
    "ingestion_preview_manifest.json": "ingestion_preview_manifest",
    "provenance_manifest.json": "provenance_manifest",
    "run_closeout_manifest.json": "run_closeout_manifest",
    "claim_ledger_manifest.json": "claim_ledger_manifest",
    "operator_review_packet_manifest.json": "operator_review_packet_manifest",
    "replay_plan_manifest.json": "replay_plan_manifest",
    "audit_index_manifest.json": "audit_index_manifest",
    "validation_recipe_manifest.json": "validation_recipe_manifest",
    "validation_record.json": "validation_record",
    "lab_run_record.json": "lab_run_record",
    "evidence_packet_manifest.json": "evidence_packet_manifest",
    "review_record.json": "review_record",
    "run_state_chain.json": "run_state_chain",
    "runtime_environment_manifest.json": "runtime_environment_manifest",
    "execution_policy_manifest.json": "execution_policy_manifest",
    "neuml_handoff_manifest.json": "neuml_handoff_manifest",
    "run_manifest.json": "run_manifest",
}

EVIDENCE_REQUIRED_RECORDS = [
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
    "review_record.json",
    "run_state_chain.json",
    "runtime_environment_manifest.json",
    "execution_policy_manifest.json",
]


OPTIONAL_REPORT_FILE = "trace_lab_report.md"

def _safe_relative_artifact_path(raw_path: object) -> tuple[Path | None, str | None]:
    if not raw_path or not isinstance(raw_path, str):
        return None, "artifact has no relative path"

    candidate = Path(raw_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None, f"artifact path must stay inside run directory: {raw_path}"

    return candidate, None


def _validate_hashed_artifacts(run_dir: Path, artifacts: list, source_name: str) -> list[str]:
    errors = []
    for index, item in enumerate(artifacts):
        if not isinstance(item, dict):
            errors.append(f"{source_name} artifacts[{index}] is not an object.")
            continue

        candidate, path_error = _safe_relative_artifact_path(item.get("path"))
        if path_error:
            errors.append(f"{source_name} artifacts[{index}] {path_error}.")
            continue

        artifact_path = run_dir / candidate
        if not artifact_path.exists():
            errors.append(f"Evidence artifact missing: {candidate.as_posix()}")
            continue

        expected_hash = item.get("hash")
        if expected_hash and sha256_file(artifact_path) != expected_hash:
            errors.append(f"Evidence artifact hash mismatch: {candidate.as_posix()}")

    return errors


def validate_run(run_dir: str | Path) -> dict:
    run_dir = Path(run_dir)
    missing = [name for name in REQUIRED if not (run_dir / name).exists()]
    json_errors = []
    parsed = {}
    for path in run_dir.glob("*.json"):
        try:
            parsed[path.name] = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            json_errors.append(f"{path.name}: {exc}")

    unsafe = []
    telemetry_errors = []
    telemetry_profile_errors = []
    record_errors = []
    evidence_errors = []
    state_errors = []
    handoff_errors = []
    manifest_errors = []
    review_errors = []
    adapter_errors = []
    environment_errors = []
    report_errors = []
    policy_errors = []
    ingestion_errors = []
    provenance_errors = []
    closeout_errors = []
    claim_errors = []
    review_packet_errors = []
    replay_errors = []
    audit_errors = []
    recipe_errors = []

    for name, expected_type in EXPECTED_RECORD_TYPES.items():
        if name in parsed and parsed[name].get("record_type") != expected_type:
            record_errors.append(
                f"{name} has record_type={parsed[name].get('record_type')!r}; expected {expected_type!r}."
            )

    request = parsed.get("experiment_request.json", {})
    plan = parsed.get("run_plan.json", {})
    approval = parsed.get("approval_record.json", {})
    dry_run = parsed.get("dry_run_record.json", {})
    action = parsed.get("adapter_action_record.json", {})
    telemetry = parsed.get("telemetry_manifest.json", {})
    telemetry_profile = parsed.get("telemetry_profile_manifest.json", {})
    validation = parsed.get("validation_record.json", {})
    lab_run = parsed.get("lab_run_record.json", {})
    evidence = parsed.get("evidence_packet_manifest.json", {})
    review = parsed.get("review_record.json", {})
    capability = parsed.get("adapter_capability_manifest.json", {})
    handoff = parsed.get("neuml_handoff_manifest.json", {})
    run_manifest = parsed.get("run_manifest.json", {})
    run_state_chain = parsed.get("run_state_chain.json", {})
    runtime_environment = parsed.get("runtime_environment_manifest.json", {})
    execution_policy = parsed.get("execution_policy_manifest.json", {})
    ingestion_preview = parsed.get("ingestion_preview_manifest.json", {})
    provenance = parsed.get("provenance_manifest.json", {})
    closeout = parsed.get("run_closeout_manifest.json", {})
    claim_ledger = parsed.get("claim_ledger_manifest.json", {})
    operator_review_packet = parsed.get("operator_review_packet_manifest.json", {})
    replay_plan = parsed.get("replay_plan_manifest.json", {})
    audit_index = parsed.get("audit_index_manifest.json", {})
    validation_recipe = parsed.get("validation_recipe_manifest.json", {})

    review_validation = validate_review_record(review)
    review_errors.extend(review_validation.get("review_errors", []))
    unsafe.extend(review_validation.get("unsafe", []))

    adapter_validation = validate_adapter_boundary(capability, dry_run, action, plan)
    adapter_errors.extend(adapter_validation.get("adapter_errors", []))
    unsafe.extend(adapter_validation.get("unsafe", []))

    runtime_validation = validate_runtime_environment_manifest(runtime_environment)
    environment_errors.extend(runtime_validation.get("environment_errors", []))
    unsafe.extend(runtime_validation.get("unsafe", []))

    policy_validation = validate_execution_policy_manifest(execution_policy)
    policy_errors.extend(policy_validation.get("policy_errors", []))
    unsafe.extend(policy_validation.get("unsafe", []))

    telemetry_profile_validation = validate_telemetry_profile_manifest(run_dir, telemetry_profile)
    telemetry_profile_errors.extend(telemetry_profile_validation.get("telemetry_profile_errors", []))
    unsafe.extend(telemetry_profile_validation.get("unsafe", []))

    ingestion_validation = validate_ingestion_preview_manifest(run_dir, ingestion_preview)
    ingestion_errors.extend(ingestion_validation)

    provenance_validation = validate_provenance_manifest(run_dir, provenance)
    provenance_errors.extend(provenance_validation.get("provenance_errors", []))
    unsafe.extend(provenance_validation.get("unsafe", []))

    closeout_validation = validate_run_closeout_manifest(run_dir, closeout if "run_closeout_manifest.json" in parsed else None)
    closeout_errors.extend(closeout_validation.get("closeout_errors", []))
    unsafe.extend(closeout_validation.get("unsafe", []))

    claim_validation = validate_claim_ledger_manifest(run_dir, claim_ledger if "claim_ledger_manifest.json" in parsed else None)
    claim_errors.extend(claim_validation.get("claim_errors", []))
    unsafe.extend(claim_validation.get("unsafe", []))

    packet_validation = validate_operator_review_packet_manifest(
        run_dir,
        operator_review_packet if "operator_review_packet_manifest.json" in parsed else None,
    )
    review_packet_errors.extend(packet_validation.get("review_packet_errors", []))
    unsafe.extend(packet_validation.get("unsafe", []))

    replay_validation = validate_replay_plan_manifest(
        run_dir,
        replay_plan if "replay_plan_manifest.json" in parsed else None,
    )
    replay_errors.extend(replay_validation.get("replay_errors", []))
    unsafe.extend(replay_validation.get("unsafe", []))

    audit_validation = validate_audit_index_manifest(
        run_dir,
        audit_index if "audit_index_manifest.json" in parsed else None,
    )
    audit_errors.extend(audit_validation.get("audit_errors", []))
    unsafe.extend(audit_validation.get("unsafe", []))

    recipe_validation = validate_validation_recipe_manifest(
        run_dir,
        validation_recipe if "validation_recipe_manifest.json" in parsed else None,
    )
    recipe_errors.extend(recipe_validation.get("recipe_errors", []))
    unsafe.extend(recipe_validation.get("unsafe", []))

    if (run_dir / OPTIONAL_REPORT_FILE).exists():
        from .report import validate_markdown_report

        report_validation = validate_markdown_report(run_dir)
        report_errors.extend(report_validation.get("report_errors", []))
        unsafe.extend(report_validation.get("unsafe", []))

    request_id = request.get("request_id")
    plan_id = plan.get("run_plan_id")
    run_id = lab_run.get("run_id")
    plan_action_types = {
        step.get("action_type")
        for step in plan.get("steps", [])
        if isinstance(step, dict) and step.get("action_type")
    }

    if request_id and plan.get("request_id") != request_id:
        record_errors.append("run_plan.json request_id does not match experiment_request.json.")
    if plan_id and approval.get("run_plan_id") != plan_id:
        record_errors.append("approval_record.json run_plan_id does not match run_plan.json.")
    if request_id and lab_run.get("request_id") != request_id:
        record_errors.append("lab_run_record.json request_id does not match experiment_request.json.")
    if plan_id and lab_run.get("run_plan_id") != plan_id:
        record_errors.append("lab_run_record.json run_plan_id does not match run_plan.json.")
    if run_id and telemetry.get("run_id") != run_id:
        record_errors.append("telemetry_manifest.json run_id does not match lab_run_record.json.")
    if run_id and evidence.get("run_id") != run_id:
        record_errors.append("evidence_packet_manifest.json run_id does not match lab_run_record.json.")
    if run_id and review.get("run_id") != run_id:
        record_errors.append("review_record.json run_id does not match lab_run_record.json.")

    if plan.get("approval_required") is not True:
        record_errors.append("run_plan.json must require approval in v0.1 simulation.")
    if plan.get("dry_run_required") is not True:
        record_errors.append("run_plan.json must require dry-run in v0.1 simulation.")

    if approval.get("decision") != "approved_for_simulation_only":
        record_errors.append("approval_record.json must approve simulation only.")
    if approval.get("approval_scope") != "simulation_only":
        record_errors.append("approval_record.json approval_scope must be simulation_only.")
    if approval.get("physical_execution_allowed") is not False:
        unsafe.append("Approval records cannot allow physical execution in v0.1 simulation.")

    if dry_run.get("action_type") and dry_run.get("action_type") not in plan_action_types:
        record_errors.append("dry_run_record.json action_type is not declared in run_plan.json steps.")
    if action.get("action_type") and action.get("action_type") not in plan_action_types:
        record_errors.append("adapter_action_record.json action_type is not declared in run_plan.json steps.")

    if "adapter_action_record.json" not in lab_run.get("action_record_refs", []):
        record_errors.append("lab_run_record.json must reference adapter_action_record.json.")
    if "telemetry_manifest.json" not in lab_run.get("telemetry_manifest_refs", []):
        record_errors.append("lab_run_record.json must reference telemetry_manifest.json.")

    evidence_records = set(evidence.get("records", []))
    for name in EVIDENCE_REQUIRED_RECORDS:
        if name not in evidence_records:
            evidence_errors.append(f"evidence_packet_manifest.json does not include required record: {name}")

    telemetry_artifacts = telemetry.get("data_files", [])
    for index, item in enumerate(telemetry_artifacts):
        if not isinstance(item, dict):
            telemetry_errors.append(f"telemetry_manifest.json data_files[{index}] is not an object.")
            continue

        candidate, path_error = _safe_relative_artifact_path(item.get("path"))
        if path_error:
            telemetry_errors.append(f"telemetry_manifest.json data_files[{index}] {path_error}.")
            continue

        telemetry_path = run_dir / candidate
        if not telemetry_path.exists():
            telemetry_errors.append(f"Telemetry file missing: {candidate.as_posix()}")
            continue

        expected_hash = item.get("hash")
        if expected_hash and sha256_file(telemetry_path) != expected_hash:
            telemetry_errors.append(f"Telemetry file hash mismatch: {candidate.as_posix()}")

    missing_channels = telemetry.get("missing_channels", [])
    if missing_channels:
        telemetry_errors.append(f"Telemetry manifest declares missing channels: {missing_channels}")

    evidence_errors.extend(_validate_hashed_artifacts(run_dir, evidence.get("artifacts", []), "evidence_packet_manifest.json"))

    state_errors.extend(validate_run_state_chain(run_dir, run_state_chain, parsed))

    if dry_run.get("physical_execution_completed"):
        unsafe.append("Dry-run records cannot claim physical execution in v0.1 simulation.")
    if action.get("physical_execution_completed"):
        unsafe.append("Physical execution is not allowed in v0.1 simulation.")
    if action.get("execution_mode") != "simulated":
        unsafe.append("Adapter action execution_mode must remain simulated in v0.1.")
    if lab_run.get("physical_execution_completed"):
        unsafe.append("Lab run records cannot claim physical execution in v0.1 simulation.")
    if validation.get("scientific_truth_validated"):
        unsafe.append("Operational validation cannot claim scientific truth in v0.1 simulation.")
    if review.get("state_promoted"):
        unsafe.append("Review records cannot promote durable state in v0.1 simulation.")
    if review.get("claims_promoted"):
        unsafe.append("Review records cannot promote claims in v0.1 simulation.")

    if capability.get("can_execute_physical_actions"):
        unsafe.append("Adapters cannot claim physical execution capability in v0.1 simulation.")


    if run_manifest:
        manifest_errors.extend(validate_run_manifest(run_dir, run_manifest))

    if handoff:
        if handoff.get("handoff_status") != "prepared_for_future_ingestion_only":
            handoff_errors.append("neuml_handoff_manifest.json handoff_status must be prepared_for_future_ingestion_only.")
        if handoff.get("evidence_packet_path") != "evidence_packet_manifest.json":
            handoff_errors.append("neuml_handoff_manifest.json evidence_packet_path must reference evidence_packet_manifest.json.")

        handoff_records = set(handoff.get("records_included", []))
        for name in REQUIRED_HANDOFF_RECORDS:
            if name not in handoff_records:
                handoff_errors.append(f"neuml_handoff_manifest.json records_included missing required record: {name}")

        handoff_telemetry = set(handoff.get("telemetry_data_candidates", []))
        for name in TELEMETRY_DATA_CANDIDATES:
            if name not in handoff_telemetry:
                handoff_errors.append(f"neuml_handoff_manifest.json telemetry_data_candidates missing required artifact: {name}")

        for field_name in ["records_included", "text_index_candidates", "telemetry_data_candidates", "report_candidates"]:
            values = handoff.get(field_name, [])
            if not isinstance(values, list):
                handoff_errors.append(f"neuml_handoff_manifest.json {field_name} must be a list.")
                continue
            for index, value in enumerate(values):
                candidate, path_error = _safe_relative_artifact_path(value)
                if path_error:
                    handoff_errors.append(f"neuml_handoff_manifest.json {field_name}[{index}] {path_error}.")
                    continue
                if candidate and not (run_dir / candidate).exists():
                    handoff_errors.append(f"neuml_handoff_manifest.json {field_name}[{index}] points to missing path: {candidate.as_posix()}")

    handoff_flags = handoff.get("authority_flags", {})
    unsafe_handoff_flags = [
        "agent_approved",
        "scientific_truth_validated",
        "physical_execution_completed",
        "state_promoted",
        "handoff_promotes_claims",
    ]
    for flag in unsafe_handoff_flags:
        if handoff_flags.get(flag):
            unsafe.append(f"NeuML handoff cannot set {flag}=true in v0.1 simulation.")

    status = (
        "passed_operational_checks"
        if not missing and not json_errors and not unsafe and not telemetry_errors and not telemetry_profile_errors and not record_errors and not evidence_errors and not state_errors and not handoff_errors and not manifest_errors and not review_errors and not adapter_errors and not environment_errors and not report_errors and not policy_errors and not ingestion_errors and not provenance_errors and not closeout_errors and not claim_errors and not review_packet_errors and not replay_errors and not audit_errors and not recipe_errors
        else "failed_operational_checks"
    )
    return {
        "record_type": "trace_lab_validation_result",
        "validation_status": status,
        "missing": missing,
        "json_errors": json_errors,
        "telemetry_errors": telemetry_errors,
        "telemetry_profile_errors": telemetry_profile_errors,
        "record_errors": record_errors,
        "evidence_errors": evidence_errors,
        "state_errors": state_errors,
        "handoff_errors": handoff_errors,
        "manifest_errors": manifest_errors,
        "review_errors": review_errors,
        "adapter_errors": adapter_errors,
        "environment_errors": environment_errors,
        "report_errors": report_errors,
        "policy_errors": policy_errors,
        "ingestion_errors": ingestion_errors,
        "provenance_errors": provenance_errors,
        "closeout_errors": closeout_errors,
        "claim_errors": claim_errors,
        "review_packet_errors": review_packet_errors,
        "replay_errors": replay_errors,
        "audit_errors": audit_errors,
        "recipe_errors": recipe_errors,
        "unsafe": unsafe,
        "authority_note": "Operational checks are not scientific validation.",
    }
