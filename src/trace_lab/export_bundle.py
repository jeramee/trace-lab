from __future__ import annotations

from pathlib import Path
from typing import Any
import zipfile

from .io import read_json, sha256_file, write_json
from .profile_registry import SIMULATED_LAB_BUNDLE_PROFILE, require_profile
from .records import now
from .validate import validate_run

EXPORT_MANIFEST_NAME = "trace_lab_export_manifest.json"
EXPORT_BUNDLE_VALIDATION_RESULT_SUFFIX = ".validation.json"

OPTIONAL_VIEW_FILES = [
    "validation_result.json",
    "run_state_summary.json",
    "review_summary.json",
    "adapter_boundary_summary.json",
    "runtime_environment_summary.json",
    "execution_policy_summary.json",
    "telemetry_profile_summary.json",
    "ingestion_preview_summary.json",
    "provenance_summary.json",
    "run_closeout_summary.json",
    "claim_ledger_summary.json",
    "operator_review_packet_summary.json",
    "replay_plan_summary.json",
    "audit_index_summary.json",
    "validation_recipe_summary.json",
    "trace_lab_report.md",
    "trace_lab_report.md.validation.json",
]

BOUNDARY_NOTES = [
    "evidence != truth",
    "operational validation != scientific validity",
    "approval record != agent permission",
    "dry-run != physical execution",
    "NeuML handoff != claim promotion",
    "simulated adapter != hardware adapter",
]


def _safe_manifest_path(raw_path: object) -> str | None:
    if not raw_path or not isinstance(raw_path, str):
        return None
    candidate = Path(raw_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    return candidate.as_posix()


def _source_files_from_run_manifest(run_dir: Path) -> list[str]:
    manifest_path = run_dir / "run_manifest.json"
    if not manifest_path.exists():
        return []

    manifest = read_json(manifest_path)
    paths: list[str] = []
    for section in ("records", "artifacts"):
        for item in manifest.get(section, []):
            if not isinstance(item, dict):
                continue
            safe_path = _safe_manifest_path(item.get("path"))
            if safe_path and (run_dir / safe_path).exists() and safe_path not in paths:
                paths.append(safe_path)

    if (run_dir / "run_manifest.json").exists() and "run_manifest.json" not in paths:
        paths.append("run_manifest.json")

    for name in OPTIONAL_VIEW_FILES:
        if (run_dir / name).exists() and name not in paths:
            paths.append(name)

    return sorted(paths)


def build_export_manifest(run_dir: str | Path) -> dict[str, Any]:
    """Build a local ZIP export manifest for a validated TraceLab run.

    The export manifest is a packaging record only. It does not install
    packages, call networks, call hardware, validate scientific truth, or
    promote claims.
    """

    run_dir = Path(run_dir)
    validation_result = validate_run(run_dir)
    source_files = _source_files_from_run_manifest(run_dir)
    selected_profile = require_profile(SIMULATED_LAB_BUNDLE_PROFILE)

    bundle_files: list[dict[str, Any]] = []
    for relative_path in source_files:
        path = run_dir / relative_path
        bundle_files.append(
            {
                "path": relative_path,
                "size_bytes": path.stat().st_size,
                "hash": sha256_file(path),
            }
        )

    return {
        "record_type": "trace_lab_export_manifest",
        "created_at": now(),
        "export_scope": "operational_simulation_only",
        "selected_profile": selected_profile["name"],
        "profile_evidence_meaning": selected_profile["evidence_meaning"],
        "profile_stop_lines": selected_profile["stop_lines"],
        "export_status": (
            "ready_for_local_zip_export"
            if validation_result.get("validation_status") == "passed_operational_checks"
            else "blocked_by_failed_operational_checks"
        ),
        "source_validation_status": validation_result.get("validation_status"),
        "bundle_manifest_path": EXPORT_MANIFEST_NAME,
        "bundle_file_count": len(bundle_files),
        "bundle_files": bundle_files,
        "known_gaps": [
            "Export is local packaging only.",
            "No NeuML/txtai/PaperAI execution is performed by TraceLab export.",
            "No scientific truth validation is performed by TraceLab export.",
            "No hardware access is performed by TraceLab export.",
        ],
        "not_proven_claims": [
            "scientific truth",
            "physical safety validation",
            "hardware readiness",
            "claim promotion",
        ],
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
        "authority_note": "Export bundle manifests are packaging evidence only; they do not validate scientific truth or promote claims.",
    }


def write_export_bundle(
    run_dir: str | Path,
    out_zip: str | Path,
    *,
    force: bool = False,
) -> Path:
    """Write a local evidence bundle ZIP for a validated TraceLab run."""

    run_dir = Path(run_dir)
    out_zip = Path(out_zip)

    if out_zip.exists() and not force:
        raise FileExistsError(
            "TraceLab refuses to overwrite an existing export bundle without --force. "
            "This prevents silent replacement of exported evidence."
        )

    validation_result = validate_run(run_dir)
    if validation_result.get("validation_status") != "passed_operational_checks":
        raise ValueError(
            "TraceLab refuses to export a run that failed operational validation. "
            f"validation_status={validation_result.get('validation_status')}"
        )

    manifest = build_export_manifest(run_dir)
    source_files = [item["path"] for item in manifest["bundle_files"]]

    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for relative_path in source_files:
            bundle.write(run_dir / relative_path, arcname=relative_path)
        bundle.writestr(EXPORT_MANIFEST_NAME, __import__("json").dumps(manifest, indent=2, sort_keys=True) + "\n")

    return out_zip


def _manifest_file_names(bundle: zipfile.ZipFile) -> set[str]:
    return {name for name in bundle.namelist() if not name.endswith("/")}


def validate_export_bundle(bundle_zip: str | Path) -> dict[str, Any]:
    """Validate a local TraceLab export ZIP without unpacking or executing it.

    This is a packaging-integrity check only. It does not validate scientific
    truth, call hardware, call networks, install packages, or promote claims.
    """

    bundle_zip = Path(bundle_zip)
    errors: list[str] = []

    if not bundle_zip.exists():
        return {
            "record_type": "trace_lab_export_bundle_validation",
            "created_at": now(),
            "bundle_path": str(bundle_zip),
            "bundle_validation_status": "failed_export_bundle_checks",
            "export_bundle_errors": [f"Export bundle missing: {bundle_zip}"],
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
            "authority_note": "Export bundle validation checks local package integrity only; it does not validate scientific truth or promote claims.",
        }

    manifest: dict[str, Any] = {}
    names: set[str] = set()

    try:
        with zipfile.ZipFile(bundle_zip) as bundle:
            names = _manifest_file_names(bundle)
            if EXPORT_MANIFEST_NAME not in names:
                errors.append(f"Missing export manifest: {EXPORT_MANIFEST_NAME}")
            else:
                try:
                    manifest = __import__("json").loads(bundle.read(EXPORT_MANIFEST_NAME).decode("utf-8"))
                except Exception as exc:  # noqa: BLE001 - report malformed bundle content
                    errors.append(f"Export manifest is not valid JSON: {exc}")

            if manifest:
                if manifest.get("record_type") != "trace_lab_export_manifest":
                    errors.append("Export manifest record_type must be trace_lab_export_manifest.")
                if manifest.get("export_scope") != "operational_simulation_only":
                    errors.append("Export manifest export_scope must be operational_simulation_only.")
                if manifest.get("export_status") != "ready_for_local_zip_export":
                    errors.append("Export manifest export_status must be ready_for_local_zip_export.")
                if manifest.get("source_validation_status") != "passed_operational_checks":
                    errors.append("Export manifest source_validation_status must be passed_operational_checks.")

                flags = manifest.get("authority_flags", {})
                for flag_name in (
                    "agent_approved",
                    "physical_execution_completed",
                    "scientific_truth_validated",
                    "state_promoted",
                    "claims_promoted",
                    "network_calls_performed",
                    "package_installation_performed",
                    "hardware_access_performed",
                ):
                    if flags.get(flag_name) is not False:
                        errors.append(f"Export manifest authority flag must remain false: {flag_name}")

                bundle_files = manifest.get("bundle_files", [])
                if not isinstance(bundle_files, list):
                    errors.append("Export manifest bundle_files must be a list.")
                    bundle_files = []

                declared_paths: set[str] = set()
                for index, item in enumerate(bundle_files):
                    if not isinstance(item, dict):
                        errors.append(f"Export manifest bundle_files[{index}] is not an object.")
                        continue

                    safe_path = _safe_manifest_path(item.get("path"))
                    if safe_path is None:
                        errors.append(f"Export manifest bundle_files[{index}] has an unsafe path.")
                        continue

                    declared_paths.add(safe_path)
                    if safe_path not in names:
                        errors.append(f"Export bundle missing declared file: {safe_path}")
                        continue

                    data = bundle.read(safe_path)
                    size_bytes = item.get("size_bytes")
                    if isinstance(size_bytes, int) and len(data) != size_bytes:
                        errors.append(f"Export bundle size mismatch: {safe_path}")

                    expected_hash = item.get("hash")
                    if expected_hash:
                        import hashlib

                        actual_hash = hashlib.sha256(data).hexdigest()
                        if actual_hash != expected_hash:
                            errors.append(f"Export bundle hash mismatch: {safe_path}")

                if manifest.get("bundle_file_count") != len(bundle_files):
                    errors.append("Export manifest bundle_file_count does not match bundle_files length.")

                allowed_names = declared_paths | {EXPORT_MANIFEST_NAME}
                unexpected_names = sorted(names - allowed_names)
                if unexpected_names:
                    errors.append(f"Export bundle contains unexpected files: {unexpected_names}")

    except zipfile.BadZipFile as exc:
        errors.append(f"Export bundle is not a valid ZIP file: {exc}")

    return {
        "record_type": "trace_lab_export_bundle_validation",
        "created_at": now(),
        "bundle_path": str(bundle_zip),
        "bundle_validation_status": (
            "passed_export_bundle_checks" if not errors else "failed_export_bundle_checks"
        ),
        "export_manifest_path": EXPORT_MANIFEST_NAME,
        "bundle_file_count": manifest.get("bundle_file_count", 0) if manifest else 0,
        "export_bundle_errors": errors,
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
        "authority_note": "Export bundle validation checks local package integrity only; it does not validate scientific truth or promote claims.",
    }


def default_export_bundle_validation_result_path(bundle_zip: str | Path) -> Path:
    """Return the default sidecar path for a bundle verification result."""

    bundle_zip = Path(bundle_zip)
    return bundle_zip.with_name(bundle_zip.name + EXPORT_BUNDLE_VALIDATION_RESULT_SUFFIX)


def write_export_bundle_validation_result(
    bundle_zip: str | Path,
    *,
    out_path: str | Path | None = None,
    force: bool = False,
) -> Path:
    """Persist a local bundle verification result as a sidecar JSON record.

    The sidecar is evidence about ZIP-package integrity only. It does not
    unpack or execute the bundle, call networks, call hardware, validate
    scientific truth, or promote claims.
    """

    result_path = Path(out_path) if out_path is not None else default_export_bundle_validation_result_path(bundle_zip)

    if result_path.exists() and not force:
        raise FileExistsError(
            "TraceLab refuses to overwrite an existing export-bundle validation result "
            "without --force-result. This prevents silent replacement of verification evidence."
        )

    result = validate_export_bundle(bundle_zip)
    result["result_scope"] = "local_export_bundle_integrity_only"
    result["result_path"] = str(result_path)
    result["sidecar_for_bundle"] = str(Path(bundle_zip))
    result["package_execution_performed"] = False
    result["bundle_unpacked"] = False
    result["network_calls_performed"] = False
    result["hardware_access_performed"] = False
    result["scientific_truth_validated"] = False
    result["claims_promoted"] = False
    result["authority_note"] = (
        "Export bundle validation result is local sidecar evidence only; it does not "
        "unpack or execute the bundle, validate scientific truth, or promote claims."
    )

    write_json(result_path, result)
    return result_path
