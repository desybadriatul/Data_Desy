"""Regression tests for MMR latency/cache/scope fix v1.

Run from repo root:
    python scripts/test_mmr_latency_cache_fix_v1.py
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def test_topic_hash_is_server_managed() -> None:
    from reporting.enrichment.topic_result_validator import validate_topic_batch_results

    batch = {
        "post_refs": [
            {
                "canonical_key": "id:1",
                "content_hash": "trusted_hash",
                "canonical_post_id": 1,
            }
        ]
    }
    taxonomy = {
        "taxonomy_version": "test_topic_v1",
        "taxonomy_name": "Test Topic",
        "description": "Test taxonomy",
        "topics": [
            {"topic_id": "issue", "label": "Issue", "description": "Issue"},
            {
                "topic_id": "other_emerging_topic",
                "label": "Other",
                "description": "Other",
            },
            {
                "topic_id": "not_relevant",
                "label": "Not relevant",
                "description": "Not relevant",
            },
        ],
    }

    for supplied_hash in (None, "TYPO_HASH"):
        result: dict[str, Any] = {
            "canonical_key": "id:1",
            "primary_topic_id": "issue",
            "classification_status": "classified",
            "confidence": "high",
        }
        if supplied_hash is not None:
            result["content_hash"] = supplied_hash

        normalized = validate_topic_batch_results(
            batch=batch,
            taxonomy=taxonomy,
            results=[result],
        )
        assert normalized[0]["content_hash"] == "trusted_hash"


def test_spokesperson_hash_is_server_managed() -> None:
    import reporting.enrichment.spokesperson_enrichment_workflow as workflow

    original_fetch = workflow.fetch_spokesperson_candidates_by_ids
    original_save = workflow.save_spokesperson_enrichment_results
    captured: dict[str, Any] = {}

    try:
        workflow.fetch_spokesperson_candidates_by_ids = lambda ids: [
            {
                "canonical_post_id": 1,
                "content_hash": "trusted_hash",
                "title": "Example",
            }
        ]

        def fake_save(response: Any, **kwargs: Any) -> dict[str, Any]:
            captured["response"] = response
            captured["candidates"] = kwargs.get("candidates")
            return {"saved": 1, "skipped": 0}

        workflow.save_spokesperson_enrichment_results = fake_save
        saved = workflow.save_spokesperson_enrichment_batch_response(
            {
                "results": [
                    {
                        "canonical_post_id": 1,
                        "status": "not_relevant",
                        "source": "llm_checked",
                        "confidence": "high",
                        "spokespersons": [],
                    }
                ]
            }
        )

        assert saved["success"] is True
        assert captured["response"]["results"][0]["content_hash"] == "trusted_hash"
        assert captured["candidates"][0]["content_hash"] == "trusted_hash"
    finally:
        workflow.fetch_spokesperson_candidates_by_ids = original_fetch
        workflow.save_spokesperson_enrichment_results = original_save



def test_empty_topic_relevant_scope_does_not_fall_back_to_all_articles() -> None:
    from reporting.enrichment.spokesperson_enrichment_workflow import (
        prepare_spokesperson_enrichment_batch,
    )

    result = prepare_spokesperson_enrichment_batch(
        client_brand="Aqua",
        start_date="2025-10-22",
        end_date="2025-10-23",
        canonical_post_ids=[],
    )
    assert result["workflow_status"] == "NOT_APPLICABLE"
    assert result["selected_count"] == 0
    assert result["topic_relevant_candidate_filter_applied"] is True

def test_mmr_hard_stop_target() -> None:
    from reporting.task2.workflows.mainstream_media_report_workflow import (
        _effective_issue_target,
    )

    assert _effective_issue_target(464, 0.10, 50, 100) == 50
    assert _effective_issue_target(80, 0.10, 50, 100) == 50
    assert _effective_issue_target(30, 0.10, 50, 100) == 30


def test_topic_runs_before_spokesperson_and_scope_is_locked() -> None:
    import reporting.enrichment.spokesperson_enrichment_workflow as spk_workflow
    import reporting.task2.workflows.mainstream_media_report_workflow as mmr_workflow

    original_topic_status = mmr_workflow._topic_status
    original_candidate_ids = mmr_workflow._classified_spokesperson_candidate_ids
    original_prepare_report_input = mmr_workflow.prepare_report_input
    original_prepare_spokesperson = spk_workflow.prepare_spokesperson_enrichment_batch
    captured: dict[str, Any] = {}

    try:
        mmr_workflow._topic_status = lambda **kwargs: {
            "status": "READY",
            "topic_eligible_posts": 100,
            "classified": 50,
            "not_relevant": 0,
            "review_needed": 0,
            "unclassified": 50,
        }
        mmr_workflow._classified_spokesperson_candidate_ids = lambda **kwargs: [11, 22]

        def should_not_build_report(*args: Any, **kwargs: Any) -> Any:
            raise AssertionError(
                "prepare_report_input must not run before spokesperson cache is ready"
            )

        mmr_workflow.prepare_report_input = should_not_build_report

        def fake_prepare_spokesperson(**kwargs: Any) -> dict[str, Any]:
            captured.update(kwargs)
            return {
                "success": True,
                "workflow_status": "NEEDS_AUTO_SPOKESPERSON_ENRICHMENT",
                "prompt_batches": [{"batch_no": 1}],
            }

        spk_workflow.prepare_spokesperson_enrichment_batch = fake_prepare_spokesperson

        result = mmr_workflow.create_mainstream_media_report_workflow(
            project_name="KDM Sidak Pabrik Air",
            start_date="2025-10-22",
            end_date="2025-10-23",
            audience="Management Aqua",
            issue_taxonomy_version="kdm_issue_v1",
        )

        assert result["workflow_status"] == "NEEDS_AUTO_SPOKESPERSON_ENRICHMENT"
        assert result["locked_scope"]["channels"] == ["Online Media", "Printmedia"]
        assert captured["canonical_post_ids"] == [11, 22]
        assert result["auto_issue_policy"]["target_issue_processed_articles"] == 50
        assert result["auto_issue_policy"]["allow_auto_expand"] is False
    finally:
        mmr_workflow._topic_status = original_topic_status
        mmr_workflow._classified_spokesperson_candidate_ids = original_candidate_ids
        mmr_workflow.prepare_report_input = original_prepare_report_input
        spk_workflow.prepare_spokesperson_enrichment_batch = original_prepare_spokesperson


def main() -> None:
    test_topic_hash_is_server_managed()
    print("TOPIC_HASH_SERVER_MANAGED_OK")

    test_spokesperson_hash_is_server_managed()
    print("SPOKESPERSON_HASH_SERVER_MANAGED_OK")

    test_empty_topic_relevant_scope_does_not_fall_back_to_all_articles()
    print("MMR_EMPTY_RELEVANT_SCOPE_OK")

    test_mmr_hard_stop_target()
    print("MMR_HARD_STOP_TARGET_OK")

    test_topic_runs_before_spokesperson_and_scope_is_locked()
    print("MMR_TOPIC_BEFORE_SPOKESPERSON_OK")

    print("MMR_LATENCY_CACHE_FIX_V1_OK")


if __name__ == "__main__":
    main()
