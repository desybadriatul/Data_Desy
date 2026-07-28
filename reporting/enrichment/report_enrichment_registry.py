"""Shared enrichment requirements for report workflows.

This registry is the single source of truth for deciding which enrichment
services a report may run. Public report tools stay report-specific, while the
workflow reads this registry so Claude does not need to infer whether topic or
spokesperson processing is required.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


class ReportEnrichmentRegistryError(ValueError):
    """Raised when a report type is unknown or requests a forbidden service."""


REPORT_ENRICHMENT_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "daily_social_media_report": {
        "topic": {
            "enabled": True,
            "mode": "smart_sample",
            "hard_max_items": 100,
            "allow_auto_expand": False,
        },
        "spokesperson": {
            "enabled": False,
            "run_after_topic_ready": False,
        },
    },
    "competitive_analysis": {
        "topic": {
            "enabled": True,
            "mode": "balanced_cross_brand_sample",
            "hard_max_items": 150,
            "allow_auto_expand": False,
        },
        "spokesperson": {
            "enabled": False,
            "run_after_topic_ready": False,
        },
    },
    "mainstream_media_report": {
        "topic": {
            "enabled": True,
            "mode": "smart_sample",
            "hard_max_items": 100,
            "allow_auto_expand": False,
        },
        "spokesperson": {
            "enabled": True,
            "run_after_topic_ready": True,
            "eligible_topic_statuses": ["classified"],
        },
    },
    "evo_perception_intelligence": {
        "topic": {
            "enabled": False,
            "mode": "none",
            "hard_max_items": 0,
            "allow_auto_expand": False,
        },
        "spokesperson": {
            "enabled": False,
            "run_after_topic_ready": False,
        },
        "attribute": {
            "enabled": True,
            "mode": "incremental_stratified_sample",
            "hard_max_items": 100,
            "default_ratio": 0.10,
            "default_min_per_brand": 30,
            "default_initial_max_per_brand": 100,
            "maximum_incremental_target_per_brand": 1000,
            "allow_auto_expand": True,
        },
    },
}


def get_report_enrichment_requirements(report_type_id: str) -> dict[str, Any]:
    """Return an isolated requirements snapshot for one report type."""
    key = str(report_type_id or "").strip()
    if key not in REPORT_ENRICHMENT_REQUIREMENTS:
        raise ReportEnrichmentRegistryError(
            f"Unknown report_type_id '{key}'. Available: "
            + ", ".join(sorted(REPORT_ENRICHMENT_REQUIREMENTS))
        )
    snapshot = deepcopy(REPORT_ENRICHMENT_REQUIREMENTS[key])
    snapshot.setdefault(
        "attribute",
        {
            "enabled": False,
            "mode": "none",
            "hard_max_items": 0,
            "allow_auto_expand": False,
        },
    )
    return {"report_type_id": key, **snapshot}


def enrichment_enabled(report_type_id: str, enrichment_name: str) -> bool:
    """Return whether topic/spokesperson enrichment is enabled for a report."""
    requirements = get_report_enrichment_requirements(report_type_id)
    name = str(enrichment_name or "").strip().casefold()
    if name not in {"topic", "spokesperson", "attribute"}:
        raise ReportEnrichmentRegistryError(
            f"Unknown enrichment '{enrichment_name}'. Use topic, spokesperson, or attribute."
        )
    return bool((requirements.get(name) or {}).get("enabled"))


def clamp_enrichment_target(
    report_type_id: str,
    enrichment_name: str,
    requested_target: int,
) -> int:
    """Apply the registry hard cap without silently expanding a target."""
    requirements = get_report_enrichment_requirements(report_type_id)
    name = str(enrichment_name or "").strip().casefold()
    policy = requirements.get(name) or {}
    if not policy.get("enabled"):
        return 0
    target = max(0, int(requested_target or 0))
    hard_max = policy.get("hard_max_items")
    if hard_max is None:
        return target
    return min(target, max(0, int(hard_max)))


def validate_enrichment_request(
    report_type_id: str,
    *,
    topic_requested: bool = False,
    spokesperson_requested: bool = False,
    attribute_requested: bool = False,
) -> dict[str, Any]:
    """Validate a proposed plan and return the canonical registry snapshot."""
    requirements = get_report_enrichment_requirements(report_type_id)
    if topic_requested and not bool(requirements["topic"]["enabled"]):
        raise ReportEnrichmentRegistryError(
            f"{report_type_id} is not allowed to run topic enrichment."
        )
    if spokesperson_requested and not bool(requirements["spokesperson"]["enabled"]):
        raise ReportEnrichmentRegistryError(
            f"{report_type_id} is not allowed to run spokesperson enrichment."
        )
    if attribute_requested and not bool(requirements["attribute"]["enabled"]):
        raise ReportEnrichmentRegistryError(
            f"{report_type_id} is not allowed to run attribute enrichment."
        )
    return requirements


__all__ = [
    "REPORT_ENRICHMENT_REQUIREMENTS",
    "ReportEnrichmentRegistryError",
    "clamp_enrichment_target",
    "enrichment_enabled",
    "get_report_enrichment_requirements",
    "validate_enrichment_request",
]
