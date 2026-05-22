from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import read_json, sha256_file, write_json
from .records import now

CLAIM_LEDGER_FILE = "claim_ledger_manifest.json"
CLAIM_LEDGER_SUMMARY_FILE = "claim_ledger_summary.json"

BOUNDARY_NOTES = [
    "evidence != truth",
    "operational validation != scientific validity",
    "approval record != agent permission",
    "dry-run != physical execution",
    "NeuML handoff != claim promotion",
    "simulated adapter != hardware adapter",
]

REQUIRED_NOT_PROVEN_CLAIMS = [
    "scientific truth",
    "physical safety validation",
    "hardware readiness",
    "human review completion",
    "durable claim promotion",
]

SUPPORTING_EVIDENCE_DEFAULTS = [
    "evidence_packet_manifest.json",
    "validation_record.json",
    "review_record.json",
    "execution_policy_manifest.json",
    "run_closeout_manifest.json",
]


def _safe_relative_path(raw_path: object) -> tuple[Path | None, str | None]:
    if not raw_path or not isinstance(raw_path, str):
        return None, "path is missing or not a string"
    candidate = Path(raw_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None, f"path must stay inside run directory: {raw_path}"
    return candidate, None


def _supporting_entry(run_dir: Path, relative_path: str) -> dict[str, Any]:
    path = run_dir / relative_path
    entry: dict[str, Any] = {
        "path": relative_path,
        "exists": path.exists(),
        "claim_scope": "operational_trace_claim_boundary_only",
    }
    if path.exists():
        entry["hash"] = sha256_file(path)
        if relative_path.endswith(".json"):
            try:
                entry["record_type"] = read_json(path).get("record_type")
            except Exception as exc:  # noqa: BLE001 - represented as claim-ledger evidence
                entry["claim_errors"] = [f"Cannot read JSON record: {exc}"]
    return entry


def build_claim_ledger_manifest(run_dir: str | Path, *, created_at: str | None = None) -> dict[str, Any]:
    """Build a local claim-boundary ledger for the simulated run.

    The ledger distinguishes operational evidence claims from claims that remain
    unproven. It does not validate scientific truth, approve actions, execute
    hardware, complete human review, or promote durable claims.
    """

    run_dir = Path(run_dir)
    supporting_evidence = [_supporting_entry(run_dir, path) for path in SUPPORTING_EVIDENCE_DEFAULTS]
    missing = [item["path"] for item in supporting_evidence if not item.get("exists")]

    return {
        "record_type": "claim_ledger_manifest",
        "created_at": created_at or now(),
        "claim_ledger_scope": "operational_trace_claim_boundary_only",
        "lifecycle_scope": "operational_simulation_only",
        "claim_ledger_status": "claim_boundaries_recorded" if not missing else "blocked_by_missing_supporting_evidence",
        "supporting_evidence": supporting_evidence,
        "supported_operational_claims": [
            {
                "claim": "TraceLab generated a local simulated evidence packet.",
                "claim_status": "supported_as_operational_trace_evidence_only",
                "source": "evidence_packet_manifest.json",
                "scientific_truth_validated": False,
                "claims_promoted": False,
            },
            {
                "claim": "TraceLab recorded simulated telemetry shape metadata.",
                "claim_status": "supported_as_operational_trace_evidence_only",
                "source": "telemetry_profile_manifest.json",
                "scientific_truth_validated": False,
                "claims_promoted": False,
            },
            {
                "claim": "TraceLab reached a local operator-review/export stop-line.",
                "claim_status": "supported_as_operational_trace_evidence_only",
                "source": "run_closeout_manifest.json",
                "scientific_truth_validated": False,
                "claims_promoted": False,
            },
        ],
        "not_proven_claims": REQUIRED_NOT_PROVEN_CLAIMS,
        "prohibited_claims": [
            {"claim": "scientific truth", "claimed": False},
            {"claim": "physical safety validation", "claimed": False},
            {"claim": "hardware readiness", "claimed": False},
            {"claim": "human review completion", "claimed": False},
            {"claim": "durable claim promotion", "claimed": False},
            {"claim": "external ingestion completed", "claimed": False},
        ],
        "known_gaps": [
            "Claim ledger is a local boundary record only.",
            "Operational evidence is not scientific truth.",
            "Human review is still required before durable claims.",
            "No hardware readiness or physical safety validation is performed.",
        ],
        "authority_flags": {
            "agent_approved": False,
            "human_review_completed": False,
            "physical_execution_completed": False,
            "scientific_truth_validated": False,
            "state_promoted": False,
            "claims_promoted": False,
            "hardware_access_performed": False,
            "network_calls_performed": False,
            "package_installation_performed": False,
            "external_ingestion_performed": False,
        },
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": "Claim ledger records local claim boundaries only; it does not validate scientific truth, complete human review, execute hardware, or promote claims.",
    }


def write_claim_ledger_manifest(
    run_dir: str | Path,
    *,
    force: bool = False,
    created_at: str | None = None,
) -> Path:
    run_dir = Path(run_dir)
    path = run_dir / CLAIM_LEDGER_FILE
    if path.exists() and not force:
        raise FileExistsError(
            "TraceLab refuses to overwrite claim_ledger_manifest.json without force=True. "
            "This prevents silent replacement of claim-boundary evidence."
        )
    write_json(path, build_claim_ledger_manifest(run_dir, created_at=created_at))
    return path


def validate_claim_ledger_manifest(
    run_dir: str | Path,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run_dir = Path(run_dir)
    errors: list[str] = []
    unsafe: list[str] = []

    if manifest is None:
        path = run_dir / CLAIM_LEDGER_FILE
        if not path.exists():
            return {
                "record_type": "claim_ledger_validation",
                "claim_ledger_validation_status": "failed_claim_ledger_checks",
                "claim_errors": [f"Missing claim ledger manifest: {CLAIM_LEDGER_FILE}"],
                "unsafe": [],
                "authority_note": "Claim ledger validation checks local claim-boundary evidence only.",
            }
        try:
            manifest = read_json(path)
        except Exception as exc:  # noqa: BLE001
            return {
                "record_type": "claim_ledger_validation",
                "claim_ledger_validation_status": "failed_claim_ledger_checks",
                "claim_errors": [f"Cannot read claim ledger manifest: {exc}"],
                "unsafe": [],
                "authority_note": "Claim ledger validation checks local claim-boundary evidence only.",
            }

    if not isinstance(manifest, dict):
        errors.append("claim_ledger_manifest.json must be a JSON object.")
    else:
        if manifest.get("record_type") != "claim_ledger_manifest":
            errors.append("claim_ledger_manifest.json record_type must be claim_ledger_manifest.")
        if manifest.get("claim_ledger_scope") != "operational_trace_claim_boundary_only":
            errors.append("claim_ledger_manifest.json claim_ledger_scope must be operational_trace_claim_boundary_only.")
        if manifest.get("lifecycle_scope") != "operational_simulation_only":
            errors.append("claim_ledger_manifest.json lifecycle_scope must be operational_simulation_only.")
        if manifest.get("claim_ledger_status") not in {"claim_boundaries_recorded", "blocked_by_missing_supporting_evidence"}:
            errors.append("claim_ledger_manifest.json claim_ledger_status has an unknown value.")

        flags = manifest.get("authority_flags", {})
        for flag_name in (
            "agent_approved",
            "human_review_completed",
            "physical_execution_completed",
            "scientific_truth_validated",
            "state_promoted",
            "claims_promoted",
            "hardware_access_performed",
            "network_calls_performed",
            "package_installation_performed",
            "external_ingestion_performed",
        ):
            if flags.get(flag_name):
                unsafe.append(f"claim_ledger_manifest.json cannot set {flag_name}=true in v0.1 simulation.")

        supporting_evidence = manifest.get("supporting_evidence", [])
        if not isinstance(supporting_evidence, list):
            errors.append("claim_ledger_manifest.json supporting_evidence must be a list.")
        else:
            seen_paths = {item.get("path") for item in supporting_evidence if isinstance(item, dict)}
            for required_path in SUPPORTING_EVIDENCE_DEFAULTS:
                if required_path not in seen_paths:
                    errors.append(f"claim_ledger_manifest.json supporting_evidence missing required path: {required_path}")
            for index, item in enumerate(supporting_evidence):
                if not isinstance(item, dict):
                    errors.append(f"claim_ledger_manifest.json supporting_evidence[{index}] is not an object.")
                    continue
                candidate, path_error = _safe_relative_path(item.get("path"))
                if path_error:
                    errors.append(f"claim_ledger_manifest.json supporting_evidence[{index}] {path_error}.")
                    continue
                path = run_dir / candidate
                if not path.exists():
                    errors.append(f"claim_ledger_manifest.json supporting_evidence[{index}] points to missing path: {candidate.as_posix()}")
                    continue
                expected_hash = item.get("hash")
                if not expected_hash:
                    errors.append(f"claim_ledger_manifest.json supporting_evidence[{index}] has no hash: {candidate.as_posix()}")
                elif sha256_file(path) != expected_hash:
                    errors.append(f"claim_ledger_manifest.json supporting_evidence[{index}] hash mismatch: {candidate.as_posix()}")
                if item.get("claim_scope") != "operational_trace_claim_boundary_only":
                    errors.append(f"claim_ledger_manifest.json supporting_evidence[{index}] claim_scope must be operational_trace_claim_boundary_only.")

        for section_name in ("supported_operational_claims", "prohibited_claims"):
            values = manifest.get(section_name, [])
            if not isinstance(values, list):
                errors.append(f"claim_ledger_manifest.json {section_name} must be a list.")
                continue
            for index, item in enumerate(values):
                if not isinstance(item, dict):
                    errors.append(f"claim_ledger_manifest.json {section_name}[{index}] is not an object.")
                    continue
                if item.get("scientific_truth_validated"):
                    unsafe.append(f"claim_ledger_manifest.json {section_name}[{index}] cannot validate scientific truth.")
                if item.get("claims_promoted") or item.get("claimed") is True:
                    unsafe.append(f"claim_ledger_manifest.json {section_name}[{index}] cannot promote or assert prohibited claims.")

        not_proven = manifest.get("not_proven_claims", [])
        if not isinstance(not_proven, list):
            errors.append("claim_ledger_manifest.json not_proven_claims must be a list.")
        else:
            for claim in REQUIRED_NOT_PROVEN_CLAIMS:
                if claim not in not_proven:
                    errors.append(f"claim_ledger_manifest.json not_proven_claims missing required claim: {claim}")

        boundary_notes = manifest.get("boundary_notes", [])
        for note in BOUNDARY_NOTES:
            if note not in boundary_notes:
                errors.append(f"claim_ledger_manifest.json missing boundary note: {note}")

    return {
        "record_type": "claim_ledger_validation",
        "claim_ledger_validation_status": "passed_claim_ledger_checks" if not errors and not unsafe else "failed_claim_ledger_checks",
        "claim_errors": errors,
        "unsafe": unsafe,
        "authority_note": "Claim ledger validation checks local claim-boundary metadata only; it does not validate scientific truth or promote claims.",
    }


def build_claim_ledger_summary(run_dir: str | Path) -> dict[str, Any]:
    run_dir = Path(run_dir)
    manifest_path = run_dir / CLAIM_LEDGER_FILE
    if manifest_path.exists():
        try:
            manifest = read_json(manifest_path)
        except Exception:  # noqa: BLE001
            manifest = {}
    else:
        manifest = build_claim_ledger_manifest(run_dir)

    validation = validate_claim_ledger_manifest(run_dir, manifest)
    return {
        "record_type": "claim_ledger_summary",
        "created_at": now(),
        "claim_ledger_scope": "operational_trace_claim_boundary_only",
        "lifecycle_scope": "operational_simulation_only",
        "claim_summary_status": "claim_boundaries_recorded" if validation.get("claim_ledger_validation_status") == "passed_claim_ledger_checks" else "blocked_by_claim_boundary_errors",
        "supported_operational_claim_count": len(manifest.get("supported_operational_claims", [])) if isinstance(manifest, dict) else 0,
        "not_proven_claim_count": len(manifest.get("not_proven_claims", [])) if isinstance(manifest, dict) else 0,
        "prohibited_claim_count": len(manifest.get("prohibited_claims", [])) if isinstance(manifest, dict) else 0,
        "claim_errors": validation.get("claim_errors", []),
        "unsafe": validation.get("unsafe", []),
        "authority_flags": {
            "agent_approved": False,
            "human_review_completed": False,
            "physical_execution_completed": False,
            "scientific_truth_validated": False,
            "state_promoted": False,
            "claims_promoted": False,
            "hardware_access_performed": False,
            "network_calls_performed": False,
            "package_installation_performed": False,
            "external_ingestion_performed": False,
        },
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": "Claim ledger summary is an operator-facing claim-boundary view only; it does not validate scientific truth, complete human review, execute hardware, or promote claims.",
    }


def write_claim_ledger_summary(run_dir: str | Path, *, force: bool = False) -> Path:
    run_dir = Path(run_dir)
    path = run_dir / CLAIM_LEDGER_SUMMARY_FILE
    if path.exists() and not force:
        raise FileExistsError(
            "TraceLab refuses to overwrite claim_ledger_summary.json without force=True. "
            "This prevents silent replacement of claim-ledger summary evidence."
        )
    write_json(path, build_claim_ledger_summary(run_dir))
    return path
