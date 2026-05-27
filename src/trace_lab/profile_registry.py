from __future__ import annotations

from copy import deepcopy
from typing import Any

SIMULATED_LAB_BUNDLE_PROFILE = "simulated_lab_bundle"
AI_ASSISTED_LAB_NOTEBOOK_PROFILE = "ai_assisted_lab_notebook"

PROFILE_REGISTRY: dict[str, dict[str, Any]] = {
    SIMULATED_LAB_BUNDLE_PROFILE: {
        "name": SIMULATED_LAB_BUNDLE_PROFILE,
        "description": "Default simulation-only lab evidence bundle workflow",
        "required_tools": [],
        "evidence_meaning": "Simulated lab/research evidence bundle provenance and verification status",
        "stop_lines": [
            "no real hardware control",
            "no real instrument adapters",
            "no LabVIEW replacement behavior",
            "no scientific truth validation",
            "no claim promotion",
            "no txtai/RAG execution",
            "no ncoder requirement",
        ],
    },
    AI_ASSISTED_LAB_NOTEBOOK_PROFILE: {
        "name": AI_ASSISTED_LAB_NOTEBOOK_PROFILE,
        "description": "AI-assisted lab notebook workflow profile",
        "required_tools": ["ncoder"],
        "evidence_meaning": "AI-assisted notebook coding is workflow provenance only",
        "stop_lines": [
            "not scientific validation",
            "not claim promotion",
            "not required for TraceLab core",
            "no real ncoder execution in v0.2",
        ],
    },
}


def list_profile_names() -> list[str]:
    """Return registered TraceLab profile names in stable order."""

    return sorted(PROFILE_REGISTRY)


def get_profile(name: str) -> dict[str, Any] | None:
    """Return a defensive copy of a registered TraceLab profile."""

    profile = PROFILE_REGISTRY.get(name)
    if profile is None:
        return None
    return deepcopy(profile)


def require_profile(name: str) -> dict[str, Any]:
    """Return a registered profile or raise a narrow name-check error."""

    profile = get_profile(name)
    if profile is None:
        raise ValueError(f"Unknown TraceLab profile: {name}")
    return profile


def is_known_profile(name: str) -> bool:
    """Return whether a profile name is registered.

    This is a name check only. It does not inspect, install, or execute any
    required tools.
    """

    return name in PROFILE_REGISTRY
    