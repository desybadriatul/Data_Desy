"""Regression compatibility checks for global relevance/taxonomy evolution v1 hotfix.

Run from repo root:
    python scripts/test_global_relevance_regression_compat_hotfix_v1.py
"""
from __future__ import annotations

from pathlib import Path
import inspect
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _taxonomy() -> dict:
    return {
        "taxonomy_version": "test_topic_v1",
        "taxonomy_name": "Test Topic",
        "description": "Test taxonomy",
        "topics": [
            {"topic_id": "issue", "label": "Issue", "description": "Issue"},
            {"topic_id": "other_emerging_topic", "label": "Other", "description": "Other"},
            {"topic_id": "not_relevant", "label": "Not relevant", "description": "Not relevant"},
        ],
    }


def test_topic_hash_server_managed_and_emerging_guard() -> None:
    from reporting.enrichment.topic_result_validator import (
        TopicResultValidationError,
        validate_topic_batch_results,
    )

    batch = {
        "post_refs": [
            {
                "canonical_key": "id:1",
                "content_hash": "trusted_hash",
                "canonical_post_id": 1,
            }
        ]
    }

    for supplied_hash in (None, "TYPO_HASH"):
        result = {
            "canonical_key": "id:1",
            "primary_topic_id": "issue",
            "classification_status": "classified",
            "confidence": "high",
        }
        if supplied_hash is not None:
            result["content_hash"] = supplied_hash
        normalized = validate_topic_batch_results(
            batch=batch,
            taxonomy=_taxonomy(),
            results=[result],
        )
        assert normalized[0]["content_hash"] == "trusted_hash"

    try:
        validate_topic_batch_results(
            batch=batch,
            taxonomy=_taxonomy(),
            results=[
                {
                    "canonical_key": "id:1",
                    "primary_topic_id": "other_emerging_topic",
                    "classification_status": "classified",
                    "confidence": "high",
                }
            ],
        )
    except TopicResultValidationError as exc:
        assert "review_needed" in str(exc)
    else:
        raise AssertionError("classified other_emerging_topic should be blocked")

    normalized = validate_topic_batch_results(
        batch=batch,
        taxonomy=_taxonomy(),
        results=[
            {
                "canonical_key": "id:1",
                "primary_topic_id": "other_emerging_topic",
                "classification_status": "review_needed",
                "confidence": "medium",
                "emerging_topic_detail": "CEO Personal Branding",
            }
        ],
    )
    assert normalized[0]["content_hash"] == "trusted_hash"
    assert normalized[0]["classification_status"] == "review_needed"


def test_mmr_builder_keeps_spokesperson_cache_integration() -> None:
    import reporting.task1.builders.mainstream_media_report as builder

    source = inspect.getsource(builder)
    assert "build_mmr_spokesperson_overview" in source
    assert "apply_global_relevance_filter" in source
    assert "extract_taxonomy_evolution_candidates" in source


if __name__ == "__main__":
    test_topic_hash_server_managed_and_emerging_guard()
    print("TOPIC_HASH_SERVER_MANAGED_WITH_EMERGING_GUARD_OK")
    test_mmr_builder_keeps_spokesperson_cache_integration()
    print("MMR_BUILDER_SPOKESPERSON_CACHE_AND_RELEVANCE_OK")
    print("GLOBAL_RELEVANCE_REGRESSION_COMPAT_HOTFIX_V1_OK")
