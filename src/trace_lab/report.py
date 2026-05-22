from __future__ import annotations

from pathlib import Path
from typing import Any

from .adapter_policy import build_adapter_boundary_summary
from .io import read_json, write_json
from .records import now
from .review import build_review_summary
from .run_state import build_run_state_summary
from .runtime_environment import build_runtime_environment_summary
from .execution_policy import build_execution_policy_summary
from .telemetry_profile import build_telemetry_profile_summary, TELEMETRY_PROFILE_SUMMARY_FILE
from .ingestion_preview import build_ingestion_preview_summary, INGESTION_PREVIEW_SUMMARY_FILE
from .provenance import build_provenance_summary, PROVENANCE_SUMMARY_FILE
from .closeout import build_run_closeout_summary, CLOSEOUT_SUMMARY_FILE
from .claim_ledger import build_claim_ledger_summary, CLAIM_LEDGER_SUMMARY_FILE
from .operator_review_packet import build_operator_review_packet_summary, OPERATOR_REVIEW_PACKET_SUMMARY_FILE
from .replay_plan import build_replay_plan_summary, REPLAY_PLAN_SUMMARY_FILE
from .audit_index import build_audit_index_summary, AUDIT_INDEX_SUMMARY_FILE
from .validation_recipe import build_validation_recipe_summary, VALIDATION_RECIPE_SUMMARY_FILE
from .validate import validate_run

REPORT_FILE = "trace_lab_report.md"
REPORT_VALIDATION_RESULT_SUFFIX = ".validation.json"

BOUNDARY_NOTES = [
    "evidence != truth",
    "operational validation != scientific validity",
    "approval record != agent permission",
    "dry-run != physical execution",
    "NeuML handoff != claim promotion",
    "simulated adapter != hardware adapter",
]


def _read_optional_json(run_dir: Path, name: str) -> dict[str, Any]:
    path = run_dir / name
    if not path.exists():
        return {}
    try:
        return read_json(path)
    except Exception:  # noqa: BLE001 - report model records absence/malformed indirectly
        return {}


def build_report_model(run_dir: str | Path) -> dict[str, Any]:
    """Build a local operator-facing report model for a TraceLab run.

    The report model is only a readability layer over existing evidence. It does
    not approve execution, validate scientific truth, execute hardware, call
    networks, install packages, or promote claims.
    """

    run_dir = Path(run_dir)
    validation_result = validate_run(run_dir)
    request = _read_optional_json(run_dir, "experiment_request.json")
    lab_run = _read_optional_json(run_dir, "lab_run_record.json")
    handoff = _read_optional_json(run_dir, "neuml_handoff_manifest.json")
    export_manifest = _read_optional_json(run_dir, "trace_lab_export_manifest.json")

    return {
        "record_type": "trace_lab_report_model",
        "created_at": now(),
        "report_scope": "operator_readability_only",
        "lifecycle_scope": "operational_simulation_only",
        "run_dir": str(run_dir),
        "request_id": request.get("request_id"),
        "run_id": lab_run.get("run_id"),
        "validation_status": validation_result.get("validation_status"),
        "validation_error_buckets": {
            key: validation_result.get(key, [])
            for key in [
                "missing",
                "json_errors",
                "unsafe",
                "telemetry_errors",
                "evidence_errors",
                "record_errors",
                "state_errors",
                "handoff_errors",
                "manifest_errors",
                "review_errors",
                "adapter_errors",
                "environment_errors",
                "policy_errors",
                "telemetry_profile_errors",
                "ingestion_errors",
                "provenance_errors",
                "closeout_errors",
                "claim_errors",
                "review_packet_errors",
                "replay_errors",
                "audit_errors",
                "recipe_errors",
            ]
        },
        "state_summary": build_run_state_summary(run_dir),
        "review_summary": build_review_summary(run_dir),
        "adapter_summary": build_adapter_boundary_summary(run_dir),
        "runtime_environment_summary": build_runtime_environment_summary(run_dir),
        "execution_policy_summary": build_execution_policy_summary(run_dir),
        "telemetry_profile_summary": build_telemetry_profile_summary(run_dir),
        "ingestion_preview_summary": build_ingestion_preview_summary(run_dir),
        "provenance_summary": build_provenance_summary(run_dir),
        "closeout_summary": build_run_closeout_summary(run_dir),
        "claim_ledger_summary": build_claim_ledger_summary(run_dir),
        "operator_review_packet_summary": build_operator_review_packet_summary(run_dir),
        "replay_plan_summary": build_replay_plan_summary(run_dir),
        "audit_index_summary": build_audit_index_summary(run_dir),
        "validation_recipe_summary": build_validation_recipe_summary(run_dir),
        "handoff_status": handoff.get("handoff_status"),
        "handoff_possible_consumers": handoff.get("possible_consumers", []),
        "export_status": export_manifest.get("export_status"),
        "authority_flags": {
            "agent_approved": False,
            "physical_execution_completed": False,
            "scientific_truth_validated": False,
            "state_promoted": False,
            "claims_promoted": False,
            "network_calls_performed": False,
            "package_installation_performed": False,
            "hardware_access_performed": False,
        },
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": "TraceLab reports are local readability artifacts only; they do not validate scientific truth, execute hardware, approve actions, or promote claims.",
    }


def build_markdown_report(run_dir: str | Path) -> str:
    """Build a human-readable Markdown report from local TraceLab evidence."""

    model = build_report_model(run_dir)
    states = model["state_summary"].get("states", [])
    error_buckets = model["validation_error_buckets"]
    non_empty_errors = {key: value for key, value in error_buckets.items() if value}

    lines = [
        "# TraceLab Local Evidence Report",
        "",
        "## Scope",
        "",
        "This report is an operator-facing readability artifact for a simulated TraceLab run.",
        "It does not validate scientific truth, execute hardware, approve actions, or promote claims.",
        "",
        "## Boundary notes",
        "",
    ]
    lines.extend(f"- {note}" for note in model["boundary_notes"])
    lines.extend([
        "",
        "## Run summary",
        "",
        f"- Lifecycle scope: `{model['lifecycle_scope']}`",
        f"- Request ID: `{model.get('request_id')}`",
        f"- Run ID: `{model.get('run_id')}`",
        f"- Validation status: `{model.get('validation_status')}`",
        f"- Handoff status: `{model.get('handoff_status')}`",
        "",
        "## State chain",
        "",
    ])
    lines.extend(f"{index}. `{state}`" for index, state in enumerate(states, start=1))
    lines.extend([
        "",
        "## Review gate",
        "",
        f"- Review status: `{model['review_summary'].get('review_status')}`",
        f"- Human review required: `{model['review_summary'].get('human_review_required')}`",
        f"- Human review completed: `{model['review_summary'].get('human_review_completed')}`",
        f"- Agent reviewed: `{model['review_summary'].get('agent_reviewed')}`",
        "",
        "## Adapter boundary",
        "",
        f"- Adapter status: `{model['adapter_summary'].get('adapter_boundary_status')}`",
        f"- Adapter mode: `{model['adapter_summary'].get('adapter_mode')}`",
        f"- Physical execution completed: `{model['adapter_summary'].get('physical_execution_completed')}`",
        "",
        "## Runtime environment",
        "",
        f"- Python: `{model['runtime_environment_summary'].get('python_version')}`",
        f"- Platform: `{model['runtime_environment_summary'].get('platform_system')}`",
        f"- Package installation performed: `{model['runtime_environment_summary'].get('package_installation_performed')}`",
        f"- Network calls performed: `{model['runtime_environment_summary'].get('network_calls_performed')}`",
        f"- Hardware access performed: `{model['runtime_environment_summary'].get('hardware_access_performed')}`",
        "",
        "## Execution policy",
        "",
        f"- Policy status: `{model['execution_policy_summary'].get('policy_summary_status')}`",
        f"- Execution mode: `{model['execution_policy_summary'].get('execution_mode')}`",
        f"- Physical execution allowed: `{model['execution_policy_summary'].get('physical_execution_allowed')}`",
        f"- Automatic retry allowed: `{model['execution_policy_summary'].get('automatic_retry_allowed')}`",
        f"- Retry attempt count: `{model['execution_policy_summary'].get('retry_attempt_count')}`",
        "",
        "## Telemetry profile",
        "",
        f"- Profile status: `{model['telemetry_profile_summary'].get('telemetry_profile_status')}`",
        f"- Validation status: `{model['telemetry_profile_summary'].get('telemetry_profile_validation_status')}`",
        f"- Data file count: `{model['telemetry_profile_summary'].get('data_file_count')}`",
        f"- Total row count: `{model['telemetry_profile_summary'].get('total_row_count')}`",
        "",
        "## Ingestion preview",
        "",
        f"- Preview status: `{model['ingestion_preview_summary'].get('ingestion_preview_status')}`",
        f"- Text candidates: `{model['ingestion_preview_summary'].get('text_index_candidate_count')}`",
        f"- Telemetry candidates: `{model['ingestion_preview_summary'].get('telemetry_data_candidate_count')}`",
        f"- Report candidates: `{model['ingestion_preview_summary'].get('report_candidate_count')}`",
        "",
        "## Provenance",
        "",
        f"- Provenance status: `{model['provenance_summary'].get('provenance_summary_status')}`",
        f"- Source system: `{model['provenance_summary'].get('source_system')}`",
        f"- Record count: `{model['provenance_summary'].get('record_count')}`",
        f"- Artifact count: `{model['provenance_summary'].get('artifact_count')}`",
        "",
        "## Run closeout",
        "",
        f"- Closeout status: `{model['closeout_summary'].get('closeout_summary_status')}`",
        f"- Record count: `{model['closeout_summary'].get('record_count')}`",
        f"- Artifact count: `{model['closeout_summary'].get('artifact_count')}`",
        f"- Required next actions: `{model['closeout_summary'].get('required_next_actions')}`",
        "",
        "## Claim ledger",
        "",
        f"- Claim status: `{model['claim_ledger_summary'].get('claim_summary_status')}`",
        f"- Supported operational claims: `{model['claim_ledger_summary'].get('supported_operational_claim_count')}`",
        f"- Not-proven claims: `{model['claim_ledger_summary'].get('not_proven_claim_count')}`",
        f"- Prohibited claims: `{model['claim_ledger_summary'].get('prohibited_claim_count')}`",
        "",
        "## Operator review packet",
        "",
        f"- Packet status: `{model['operator_review_packet_summary'].get('packet_summary_status')}`",
        f"- Human review required: `{model['operator_review_packet_summary'].get('human_review_required')}`",
        f"- Human review completed: `{model['operator_review_packet_summary'].get('human_review_completed')}`",
        f"- Required items: `{model['operator_review_packet_summary'].get('required_item_count')}`",
        f"- Optional items: `{model['operator_review_packet_summary'].get('optional_item_count')}`",
        "",
        "## Replay plan",
        "",
        f"- Replay status: `{model['replay_plan_summary'].get('replay_plan_summary_status')}`",
        f"- Replay execution status: `{model['replay_plan_summary'].get('replay_execution_status')}`",
        f"- Replay performed: `{model['replay_plan_summary'].get('replay_performed')}`",
        f"- Replay steps: `{model['replay_plan_summary'].get('replay_step_count')}`",
        "",
        "## Audit index",
        "",
        f"- Audit index status: `{model['audit_index_summary'].get('audit_index_summary_status')}`",
        f"- Indexed items: `{model['audit_index_summary'].get('item_count')}`",
        f"- Missing required items: `{model['audit_index_summary'].get('missing_required')}`",
        "",
        "## Validation recipe",
        "",
        f"- Recipe status: `{model['validation_recipe_summary'].get('validation_recipe_summary_status')}`",
        f"- Recipe scope: `{model['validation_recipe_summary'].get('validation_recipe_scope')}`",
        f"- Command count: `{model['validation_recipe_summary'].get('command_count')}`",
        "",
        "## Validation buckets",
        "",
    ])
    if non_empty_errors:
        for key, values in sorted(non_empty_errors.items()):
            lines.append(f"- `{key}`: {values}")
    else:
        lines.append("- No operational validation errors were reported.")

    lines.extend([
        "",
        "## Authority flags",
        "",
    ])
    for key, value in sorted(model["authority_flags"].items()):
        lines.append(f"- `{key}`: `{str(value).lower()}`")

    lines.extend([
        "",
        "## Not proven",
        "",
        "- Scientific truth",
        "- Physical safety validation",
        "- Hardware readiness",
        "- Durable claim promotion",
        "",
    ])
    return "\n".join(lines)


def write_markdown_report(
    run_dir: str | Path,
    out_path: str | Path | None = None,
    *,
    force: bool = False,
) -> Path:
    """Write a local Markdown report for a run that passes operational checks."""

    run_dir = Path(run_dir)
    validation_result = validate_run(run_dir)
    if validation_result.get("validation_status") != "passed_operational_checks":
        raise ValueError(
            "TraceLab refuses to write a report for a run that failed operational validation. "
            f"validation_status={validation_result.get('validation_status')}"
        )

    path = Path(out_path) if out_path else run_dir / REPORT_FILE
    if path.exists() and not force:
        raise FileExistsError(
            "TraceLab refuses to overwrite an existing report without --force. "
            "This prevents silent replacement of operator-facing evidence summaries."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_markdown_report(run_dir), encoding="utf-8")
    return path


REQUIRED_REPORT_PHRASES = [
    "# TraceLab Local Evidence Report",
    "This report is an operator-facing readability artifact for a simulated TraceLab run.",
    "It does not validate scientific truth, execute hardware, approve actions, or promote claims.",
    "## Boundary notes",
    "## Authority flags",
    "## Not proven",
]

REQUIRED_FALSE_AUTHORITY_FLAG_LINES = [
    "`agent_approved`: `false`",
    "`claims_promoted`: `false`",
    "`hardware_access_performed`: `false`",
    "`network_calls_performed`: `false`",
    "`package_installation_performed`: `false`",
    "`physical_execution_completed`: `false`",
    "`scientific_truth_validated`: `false`",
    "`state_promoted`: `false`",
]

UNSAFE_REPORT_FLAG_LINES = [
    "`agent_approved`: `true`",
    "`claims_promoted`: `true`",
    "`hardware_access_performed`: `true`",
    "`network_calls_performed`: `true`",
    "`package_installation_performed`: `true`",
    "`physical_execution_completed`: `true`",
    "`scientific_truth_validated`: `true`",
    "`state_promoted`: `true`",
]


def default_report_validation_result_path(report_path: str | Path) -> Path:
    """Return the default sidecar path for a report validation result."""

    report_path = Path(report_path)
    return report_path.with_name(report_path.name + REPORT_VALIDATION_RESULT_SUFFIX)


def validate_markdown_report(
    run_dir: str | Path,
    report_path: str | Path | None = None,
) -> dict[str, Any]:
    """Validate a local Markdown report as a readability artifact only.

    This check verifies that the report preserves required TraceLab boundary
    language. It does not validate scientific truth, execute hardware, call
    networks, install packages, approve execution, or promote claims.
    """

    run_dir = Path(run_dir)
    errors: list[str] = []
    unsafe: list[str] = []

    if report_path is None:
        path = run_dir / REPORT_FILE
    else:
        raw_path = Path(report_path)
        if raw_path.is_absolute():
            path = raw_path
            try:
                path.resolve().relative_to(run_dir.resolve())
            except ValueError:
                errors.append(f"Report path must stay inside the run directory: {path}")
        else:
            if ".." in raw_path.parts:
                errors.append(f"Report path must stay inside the run directory: {raw_path}")
            path = run_dir / raw_path

    text = ""
    if not errors:
        if not path.exists():
            errors.append(f"Markdown report missing: {path}")
        elif not path.is_file():
            errors.append(f"Markdown report path is not a file: {path}")
        else:
            text = path.read_text(encoding="utf-8")

    if text:
        for phrase in REQUIRED_REPORT_PHRASES:
            if phrase not in text:
                errors.append(f"Markdown report missing required phrase: {phrase}")
        for note in BOUNDARY_NOTES:
            if f"- {note}" not in text:
                errors.append(f"Markdown report missing boundary note: {note}")
        for line in REQUIRED_FALSE_AUTHORITY_FLAG_LINES:
            if line not in text:
                errors.append(f"Markdown report missing false authority flag line: {line}")
        for line in UNSAFE_REPORT_FLAG_LINES:
            if line in text:
                unsafe.append(f"Markdown report contains unsafe authority flag line: {line}")

    return {
        "record_type": "trace_lab_report_validation",
        "created_at": now(),
        "report_path": str(path),
        "report_scope": "operator_readability_only",
        "lifecycle_scope": "operational_simulation_only",
        "report_validation_status": (
            "passed_report_boundary_checks" if not errors and not unsafe else "failed_report_boundary_checks"
        ),
        "report_errors": errors,
        "unsafe": unsafe,
        "authority_flags": {
            "agent_approved": False,
            "physical_execution_completed": False,
            "scientific_truth_validated": False,
            "state_promoted": False,
            "claims_promoted": False,
            "network_calls_performed": False,
            "package_installation_performed": False,
            "hardware_access_performed": False,
        },
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": "Markdown report validation checks local readability-boundary text only; it does not validate scientific truth or promote claims.",
    }

def write_markdown_report_validation_result(
    run_dir: str | Path,
    report_path: str | Path | None = None,
    *,
    out_path: str | Path | None = None,
    force: bool = False,
) -> Path:
    """Persist a Markdown report validation result sidecar."""

    run_dir = Path(run_dir)
    if report_path is None:
        resolved_report_path = run_dir / REPORT_FILE
    else:
        raw_report_path = Path(report_path)
        resolved_report_path = raw_report_path if raw_report_path.is_absolute() else run_dir / raw_report_path
    result_path = Path(out_path) if out_path is not None else default_report_validation_result_path(resolved_report_path)

    if result_path.exists() and not force:
        raise FileExistsError(
            "TraceLab refuses to overwrite an existing report validation result without --force-result. "
            "This prevents silent replacement of report-boundary verification evidence."
        )

    result = validate_markdown_report(run_dir, resolved_report_path)
    result["result_scope"] = "local_report_readability_boundary_only"
    result["result_path"] = str(result_path)
    result["sidecar_for_report"] = str(resolved_report_path)
    result["package_execution_performed"] = False
    result["network_calls_performed"] = False
    result["hardware_access_performed"] = False
    result["scientific_truth_validated"] = False
    result["claims_promoted"] = False
    result["authority_note"] = (
        "Markdown report validation result is local sidecar evidence only; it does not "
        "validate scientific truth, execute hardware, approve actions, or promote claims."
    )

    write_json(result_path, result)
    return result_path
