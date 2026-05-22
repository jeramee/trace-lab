from __future__ import annotations

from pathlib import Path
from typing import Any
import csv

from .io import read_json, sha256_file, write_json
from .records import now

TELEMETRY_PROFILE_FILE = "telemetry_profile_manifest.json"
TELEMETRY_PROFILE_SUMMARY_FILE = "telemetry_profile_summary.json"

BOUNDARY_NOTES = [
    "evidence != truth",
    "operational validation != scientific validity",
    "approval record != agent permission",
    "dry-run != physical execution",
    "NeuML handoff != claim promotion",
    "simulated adapter != hardware adapter",
]


def _safe_relative_path(raw_path: object) -> tuple[Path | None, str | None]:
    if not raw_path or not isinstance(raw_path, str):
        return None, "path is missing or not a string"
    candidate = Path(raw_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None, f"path must stay inside run directory: {raw_path}"
    return candidate, None


def _profile_csv(run_dir: Path, relative_path: str, declared_hash: str | None) -> dict[str, Any]:
    path = run_dir / relative_path
    profile: dict[str, Any] = {
        "path": relative_path,
        "declared_hash": declared_hash,
        "exists": path.exists(),
        "data_shape_only": True,
        "scientific_truth_validated": False,
        "claims_promoted": False,
    }

    if not path.exists():
        profile["profile_errors"] = [f"Telemetry data file missing: {relative_path}"]
        return profile

    actual_hash = sha256_file(path)
    profile["actual_hash"] = actual_hash
    profile["hash_matches_telemetry_manifest"] = (not declared_hash) or actual_hash == declared_hash

    row_count = 0
    empty_value_count = 0
    numeric_candidates: dict[str, list[float]] = {}

    try:
        with path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            columns = list(reader.fieldnames or [])
            for column in columns:
                numeric_candidates[column] = []
            for row in reader:
                row_count += 1
                for column in columns:
                    raw_value = row.get(column, "")
                    if raw_value == "":
                        empty_value_count += 1
                        continue
                    try:
                        numeric_candidates[column].append(float(raw_value))
                    except ValueError:
                        pass
    except Exception as exc:  # noqa: BLE001 - profile records parse failure as evidence
        profile["profile_errors"] = [f"Telemetry CSV profile failed: {relative_path}: {exc}"]
        return profile

    numeric_columns: dict[str, dict[str, float | int]] = {}
    for column, values in numeric_candidates.items():
        if values and len(values) == row_count:
            numeric_columns[column] = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
            }

    profile.update(
        {
            "column_names": columns,
            "column_count": len(columns),
            "row_count": row_count,
            "empty_value_count": empty_value_count,
            "numeric_columns": numeric_columns,
            "profile_errors": [] if profile["hash_matches_telemetry_manifest"] else [
                f"Telemetry profile hash does not match telemetry manifest: {relative_path}"
            ],
        }
    )
    return profile


def build_telemetry_profile_manifest(run_dir: str | Path, *, created_at: str | None = None) -> dict[str, Any]:
    """Build a data-shape profile for simulated telemetry files.

    The profile records local CSV shape and hashes only. It does not validate
    scientific truth, infer meaning, approve execution, call hardware, or
    promote claims.
    """

    run_dir = Path(run_dir)
    telemetry_manifest_path = run_dir / "telemetry_manifest.json"
    profile_errors: list[str] = []
    data_profiles: list[dict[str, Any]] = []

    if not telemetry_manifest_path.exists():
        profile_errors.append("telemetry_manifest.json is required before telemetry profiling.")
        telemetry_manifest = {}
    else:
        try:
            telemetry_manifest = read_json(telemetry_manifest_path)
        except Exception as exc:  # noqa: BLE001 - represented in profile evidence
            profile_errors.append(f"Cannot read telemetry_manifest.json: {exc}")
            telemetry_manifest = {}

    for index, item in enumerate(telemetry_manifest.get("data_files", [])):
        if not isinstance(item, dict):
            profile_errors.append(f"telemetry_manifest.json data_files[{index}] is not an object.")
            continue

        candidate, path_error = _safe_relative_path(item.get("path"))
        if path_error:
            profile_errors.append(f"telemetry_manifest.json data_files[{index}] {path_error}.")
            continue

        relative_path = candidate.as_posix()
        profile = _profile_csv(run_dir, relative_path, item.get("hash"))
        data_profiles.append(profile)
        profile_errors.extend(profile.get("profile_errors", []))

    manifest = {
        "record_type": "telemetry_profile_manifest",
        "created_at": created_at or now(),
        "profile_scope": "operational_data_shape_only",
        "telemetry_manifest_path": "telemetry_manifest.json",
        "profile_status": (
            "profiled_simulated_telemetry" if not profile_errors else "telemetry_profile_has_errors"
        ),
        "data_file_count": len(data_profiles),
        "data_profiles": data_profiles,
        "profile_errors": profile_errors,
        "known_gaps": [
            "Telemetry profile records local file shape only.",
            "Telemetry profile does not validate scientific truth.",
            "Telemetry profile does not infer sensor correctness.",
            "Telemetry profile does not prove hardware readiness.",
        ],
        "not_proven_claims": [
            "scientific truth",
            "sensor accuracy",
            "hardware readiness",
            "claim promotion",
        ],
        "authority_flags": {
            "agent_approved": False,
            "physical_execution_completed": False,
            "scientific_truth_validated": False,
            "state_promoted": False,
            "claims_promoted": False,
            "hardware_access_performed": False,
        },
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": (
            "Telemetry profile is local data-shape evidence only; it does not validate "
            "scientific truth, execute hardware, or promote claims."
        ),
    }
    return manifest


def write_telemetry_profile_manifest(
    run_dir: str | Path,
    *,
    force: bool = False,
    created_at: str | None = None,
) -> Path:
    run_dir = Path(run_dir)
    path = run_dir / TELEMETRY_PROFILE_FILE

    if path.exists() and not force:
        raise FileExistsError(
            "TraceLab refuses to overwrite an existing telemetry profile manifest without force."
        )

    write_json(path, build_telemetry_profile_manifest(run_dir, created_at=created_at))
    return path


def validate_telemetry_profile_manifest(
    run_dir: str | Path,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate telemetry profile integrity and authority boundaries."""

    run_dir = Path(run_dir)
    errors: list[str] = []
    unsafe: list[str] = []

    if manifest is None:
        path = run_dir / TELEMETRY_PROFILE_FILE
        if not path.exists():
            return {
                "record_type": "telemetry_profile_validation",
                "telemetry_profile_validation_status": "failed_telemetry_profile_checks",
                "telemetry_profile_errors": [f"Missing telemetry profile manifest: {TELEMETRY_PROFILE_FILE}"],
                "unsafe": [],
                "authority_note": "Telemetry profile validation checks local data-shape evidence only.",
            }
        try:
            manifest = read_json(path)
        except Exception as exc:  # noqa: BLE001
            return {
                "record_type": "telemetry_profile_validation",
                "telemetry_profile_validation_status": "failed_telemetry_profile_checks",
                "telemetry_profile_errors": [f"Cannot read telemetry profile manifest: {exc}"],
                "unsafe": [],
                "authority_note": "Telemetry profile validation checks local data-shape evidence only.",
            }

    if manifest.get("record_type") != "telemetry_profile_manifest":
        errors.append("telemetry_profile_manifest.json record_type must be telemetry_profile_manifest.")
    if manifest.get("profile_scope") != "operational_data_shape_only":
        errors.append("telemetry_profile_manifest.json profile_scope must be operational_data_shape_only.")
    if manifest.get("profile_status") != "profiled_simulated_telemetry":
        errors.append("telemetry_profile_manifest.json profile_status must be profiled_simulated_telemetry.")

    flags = manifest.get("authority_flags", {})
    for flag_name in (
        "agent_approved",
        "physical_execution_completed",
        "scientific_truth_validated",
        "state_promoted",
        "claims_promoted",
        "hardware_access_performed",
    ):
        if flags.get(flag_name) is not False:
            unsafe.append(f"Telemetry profile authority flag must remain false: {flag_name}")

    if manifest.get("scientific_truth_validated") or manifest.get("claims_promoted"):
        unsafe.append("Telemetry profile cannot claim scientific truth validation or claim promotion.")

    telemetry_manifest_path = run_dir / "telemetry_manifest.json"
    if telemetry_manifest_path.exists():
        try:
            telemetry_manifest = read_json(telemetry_manifest_path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Cannot read telemetry_manifest.json for profile validation: {exc}")
            telemetry_manifest = {}
    else:
        errors.append("telemetry_profile_manifest.json requires telemetry_manifest.json.")
        telemetry_manifest = {}

    expected_files: dict[str, str | None] = {}
    for index, item in enumerate(telemetry_manifest.get("data_files", [])):
        if not isinstance(item, dict):
            errors.append(f"telemetry_manifest.json data_files[{index}] is not an object.")
            continue
        candidate, path_error = _safe_relative_path(item.get("path"))
        if path_error:
            errors.append(f"telemetry_manifest.json data_files[{index}] {path_error}.")
            continue
        expected_files[candidate.as_posix()] = item.get("hash")

    data_profiles = manifest.get("data_profiles", [])
    if not isinstance(data_profiles, list):
        errors.append("telemetry_profile_manifest.json data_profiles must be a list.")
        data_profiles = []

    seen_paths: set[str] = set()
    for index, profile in enumerate(data_profiles):
        if not isinstance(profile, dict):
            errors.append(f"telemetry_profile_manifest.json data_profiles[{index}] is not an object.")
            continue

        candidate, path_error = _safe_relative_path(profile.get("path"))
        if path_error:
            errors.append(f"telemetry_profile_manifest.json data_profiles[{index}] {path_error}.")
            continue

        relative_path = candidate.as_posix()
        seen_paths.add(relative_path)

        if relative_path not in expected_files:
            errors.append(f"Telemetry profile includes path not declared by telemetry manifest: {relative_path}")

        file_path = run_dir / candidate
        if not file_path.exists():
            errors.append(f"Telemetry profile references missing file: {relative_path}")
            continue

        actual_hash = sha256_file(file_path)
        if profile.get("actual_hash") != actual_hash:
            errors.append(f"Telemetry profile actual_hash mismatch: {relative_path}")
        expected_hash = expected_files.get(relative_path)
        if expected_hash and profile.get("declared_hash") != expected_hash:
            errors.append(f"Telemetry profile declared_hash mismatch: {relative_path}")
        if expected_hash and actual_hash != expected_hash:
            errors.append(f"Telemetry profile source hash mismatch: {relative_path}")
        if profile.get("hash_matches_telemetry_manifest") is not True:
            errors.append(f"Telemetry profile must confirm hash_matches_telemetry_manifest=true: {relative_path}")

        try:
            with file_path.open("r", newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                actual_columns = list(reader.fieldnames or [])
                actual_rows = sum(1 for _ in reader)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Cannot re-profile telemetry file: {relative_path}: {exc}")
            continue

        if profile.get("column_names") != actual_columns:
            errors.append(f"Telemetry profile column_names mismatch: {relative_path}")
        if profile.get("row_count") != actual_rows:
            errors.append(f"Telemetry profile row_count mismatch: {relative_path}")

    for relative_path in expected_files:
        if relative_path not in seen_paths:
            errors.append(f"Telemetry profile missing data profile for: {relative_path}")

    if manifest.get("data_file_count") != len(data_profiles):
        errors.append("telemetry_profile_manifest.json data_file_count does not match data_profiles length.")

    profile_errors = manifest.get("profile_errors", [])
    if profile_errors:
        errors.append(f"Telemetry profile manifest declares profile_errors: {profile_errors}")

    return {
        "record_type": "telemetry_profile_validation",
        "telemetry_profile_validation_status": (
            "passed_telemetry_profile_checks" if not errors and not unsafe else "failed_telemetry_profile_checks"
        ),
        "telemetry_profile_errors": errors,
        "unsafe": unsafe,
        "authority_note": "Telemetry profile validation checks local data-shape evidence only.",
    }


def build_telemetry_profile_summary(run_dir: str | Path) -> dict[str, Any]:
    run_dir = Path(run_dir)
    manifest = build_telemetry_profile_manifest(run_dir)
    validation = validate_telemetry_profile_manifest(run_dir, manifest)
    row_count = sum(
        profile.get("row_count", 0)
        for profile in manifest.get("data_profiles", [])
        if isinstance(profile, dict)
    )

    return {
        "record_type": "telemetry_profile_summary",
        "created_at": now(),
        "summary_scope": "operator_data_shape_view_only",
        "telemetry_profile_status": manifest.get("profile_status"),
        "telemetry_profile_validation_status": validation.get("telemetry_profile_validation_status"),
        "data_file_count": manifest.get("data_file_count", 0),
        "total_row_count": row_count,
        "data_profiles": [
            {
                "path": profile.get("path"),
                "row_count": profile.get("row_count"),
                "column_names": profile.get("column_names", []),
                "hash_matches_telemetry_manifest": profile.get("hash_matches_telemetry_manifest"),
            }
            for profile in manifest.get("data_profiles", [])
            if isinstance(profile, dict)
        ],
        "telemetry_profile_errors": validation.get("telemetry_profile_errors", []),
        "unsafe": validation.get("unsafe", []),
        "boundary_notes": BOUNDARY_NOTES,
        "authority_note": (
            "Telemetry profile summary is an operator-facing data-shape view only; it does "
            "not validate scientific truth, execute hardware, or promote claims."
        ),
    }


def write_telemetry_profile_summary(
    run_dir: str | Path,
    *,
    force: bool = False,
) -> Path:
    run_dir = Path(run_dir)
    path = run_dir / TELEMETRY_PROFILE_SUMMARY_FILE
    if path.exists() and not force:
        raise FileExistsError(
            "TraceLab refuses to overwrite an existing telemetry profile summary without force."
        )
    write_json(path, build_telemetry_profile_summary(run_dir))
    return path
