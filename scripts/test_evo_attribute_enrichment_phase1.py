"""Pure regression checks for EVO attribute enrichment Phase 1."""

from __future__ import annotations

from reporting.enrichment.evo_attribute_sampling import (
    effective_evo_sample_target,
    select_stratified_posts,
)
from reporting.enrichment.evo_attribute_contract import seed_attribute_map
from reporting.enrichment.evo_attribute_result_validator import (
    EVOAttributeResultValidationError,
    validate_evo_attribute_batch_results,
)


def _post(index: int, *, channel: str, sentiment: str, week: str, tier_hint: int) -> dict:
    return {
        "project_name": "Brand A",
        "campaign_id": 1,
        "canonical_post_id": index,
        "canonical_key": f"post:{index}",
        "content_hash": f"hash-{index}",
        "post_date": f"2026-07-{(index % 20) + 1:02d}",
        "period_bucket": week,
        "channel": channel,
        "channel_norm": channel,
        "sentiment": sentiment,
        "content_type": "video" if index % 2 else "article",
        "source_type": "social" if channel != "online_media" else "mainstream",
        "title": f"Title {index}",
        "content": f"Content {index}",
        "url": f"https://example.com/{index}",
        "interactions": 1000 - tier_hint,
        "views": 2000 - tier_hint,
        "eligible": True,
    }


def test_targets() -> None:
    assert effective_evo_sample_target(12) == 12
    assert effective_evo_sample_target(100) == 30
    assert effective_evo_sample_target(500) == 50
    assert effective_evo_sample_target(2_000) == 100
    assert effective_evo_sample_target(100_000) == 100
    assert effective_evo_sample_target(100_000, requested_target=300) == 300


def test_stratified_selection() -> None:
    population = []
    channels = ["instagram", "tiktok", "x", "online_media"]
    sentiments = ["positive", "neutral", "negative"]
    for index in range(1, 121):
        population.append(
            _post(
                index,
                channel=channels[index % len(channels)],
                sentiment=sentiments[index % len(sentiments)],
                week=f"week_{index % 4 + 1}",
                tier_hint=index,
            )
        )
    existing = population[:20]
    candidates = population[20:]
    selected = select_stratified_posts(
        population_posts=population,
        candidate_posts=candidates,
        existing_sampled_posts=existing,
        select_count=30,
    )
    assert len(selected) == 30
    assert len({(p["canonical_key"], p["content_hash"]) for p in selected}) == 30
    assert all(p.get("sample_reasons") for p in selected)
    assert len({p["sentiment"] for p in selected}) >= 2
    assert len({p["channel_norm"] for p in selected}) >= 3
    assert len({p["period_bucket"] for p in selected}) >= 3


def test_result_validation() -> None:
    batch = {
        "post_refs": [
            {
                "project_name": "Brand A",
                "campaign_id": 1,
                "canonical_post_id": 1,
                "canonical_key": "post:1",
                "content_hash": "hash-1",
            }
        ]
    }
    results = [
        {
            "canonical_key": "post:1",
            "content_hash": "hash-1",
            "issue_name": "Service failed during payment",
            "primary_attribute_id": "ATTR_EXP_RELIABILITY",
            "secondary_attribute_id": None,
            "classification_status": "classified",
            "classification_confidence": 0.88,
            "classification_rationale": "The post explicitly reports a failed service.",
        }
    ]
    normalized = validate_evo_attribute_batch_results(
        batch=batch,
        attribute_map=seed_attribute_map(),
        results=results,
    )
    assert normalized[0]["primary_driver"] == "Experience"
    assert normalized[0]["primary_attribute_label"] == "Reliability / Performance"

    invalid = [dict(results[0], primary_attribute_id="ATTR_UNKNOWN")]
    try:
        validate_evo_attribute_batch_results(
            batch=batch,
            attribute_map=seed_attribute_map(),
            results=invalid,
        )
    except EVOAttributeResultValidationError:
        pass
    else:
        raise AssertionError("Unknown attribute_id should be rejected.")


def main() -> None:
    test_targets()
    test_stratified_selection()
    test_result_validation()
    print("EVO_ATTRIBUTE_ENRICHMENT_PHASE1_OK")


if __name__ == "__main__":
    main()
