from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reporting.enrichment.global_relevance_filter import apply_global_relevance_filter
from reporting.enrichment.taxonomy_evolution import extract_taxonomy_evolution_candidates
from reporting.enrichment.topic_result_validator import (
    TopicResultValidationError,
    validate_topic_batch_results,
)


def test_global_noise_filter_known_ambiguous_brands() -> None:
    rows = [
        {"brand": "Bluebird", "title": "Keladi Blue Bird ready stok", "content": "Tanaman hias blue bird murah", "_cogan_campaign_scope": "Bluebird"},
        {"brand": "Bluebird", "author": "@bluebirdgroup", "content": "Bluebird hadirkan promo perjalanan bandara"},
        {"brand": "Aqua", "content": "Aqua farming program expands in coastal villages", "_cogan_campaign_scope": "Aqua"},
        {"brand": "Pristine", "content": "A pristine beach with untouched wilderness", "_cogan_campaign_scope": "Pristine"},
        {"brand": "Le Minerale", "content": "Le Minerale dukung event olahraga keluarga"},
    ]
    result = apply_global_relevance_filter(
        rows,
        project_name="Bluebird",
        report_type_id="daily_social_media_report",
        client_brand="Bluebird",
        brand_universe=["Bluebird", "Aqua", "Pristine", "Le Minerale"],
        scope={},
    )
    summary = result["summary"]
    assert summary["raw_count"] == 5
    assert summary["excluded_count"] == 3
    assert summary["clean_count"] == 2
    noise_types = {row["noise_type"] for row in result["excluded_rows"]}
    assert "bluebird_plant_or_bird" in noise_types
    assert "aqua_non_brand_context" in noise_types
    assert "pristine_generic_adjective" in noise_types
    print("GLOBAL_RELEVANCE_KNOWN_NOISE_OK")


def test_resale_noise_default_excluded_but_can_be_allowed() -> None:
    row = {"brand": "Bluebird", "content": "Jual mobil bekas ex taksi Bluebird Avanza Transmover murah"}
    blocked = apply_global_relevance_filter(
        [row],
        project_name="Bluebird",
        report_type_id="daily_social_media_report",
        client_brand="Bluebird",
        brand_universe=["Bluebird"],
        scope={},
    )
    assert blocked["summary"]["excluded_count"] == 1
    assert blocked["excluded_rows"][0]["noise_type"] == "fleet_resale_ex_armada"

    allowed = apply_global_relevance_filter(
        [row],
        project_name="Bluebird",
        report_type_id="daily_social_media_report",
        client_brand="Bluebird",
        brand_universe=["Bluebird"],
        scope={"include_resale_market": True},
    )
    assert allowed["summary"]["excluded_count"] == 0
    assert allowed["summary"]["clean_count"] == 1
    print("GLOBAL_RELEVANCE_RESALE_SCOPE_OK")


def test_ambiguous_campaign_without_brand_mention_excluded() -> None:
    rows = [
        {"brand": "Pristine", "content": "hah seriusan??", "_cogan_campaign_scope": "Pristine"},
        {"brand": "Aqua", "content": "Timnas U17 bersama #AquaDulu", "_cogan_campaign_scope": "Aqua"},
    ]
    result = apply_global_relevance_filter(
        rows,
        project_name="Le Minerale",
        report_type_id="competitive_analysis",
        client_brand="Le Minerale",
        brand_universe=["Le Minerale", "Aqua", "Pristine"],
        scope={},
    )
    assert result["summary"]["excluded_count"] == 1
    assert result["summary"]["clean_count"] == 1
    assert result["excluded_rows"][0]["noise_type"] == "missing_brand_mention_for_ambiguous_campaign"
    print("GLOBAL_RELEVANCE_AMBIGUOUS_CAMPAIGN_OK")


def test_topic_result_validator_forces_review_needed_for_emerging_topic() -> None:
    taxonomy = {
        "taxonomy_version": "bluebird_v1",
        "taxonomy_name": "Bluebird topic taxonomy",
        "description": "test",
        "topics": [
            {"topic_id": "kecelakaan", "label": "Kecelakaan", "description": "Insiden keselamatan"},
            {"topic_id": "other_emerging_topic", "label": "Topik Baru", "description": "Relevan tapi belum ada slot"},
            {"topic_id": "not_relevant", "label": "Tidak Relevan", "description": "Noise"},
        ],
    }
    batch = {"post_refs": [{"canonical_key": "url:a", "content_hash": "hash-a", "canonical_post_id": 1}]}
    bad = [
        {
            "canonical_key": "url:a",
            "content_hash": "hash-a",
            "primary_topic_id": "other_emerging_topic",
            "classification_status": "classified",
            "confidence": "medium",
            "classification_reason": "CEO personal branding",
        }
    ]
    try:
        validate_topic_batch_results(batch=batch, taxonomy=taxonomy, results=bad)
    except TopicResultValidationError:
        pass
    else:
        raise AssertionError("classified other_emerging_topic should fail")

    good = [
        {
            "canonical_key": "url:a",
            "content_hash": "hash-a",
            "primary_topic_id": "other_emerging_topic",
            "classification_status": "review_needed",
            "confidence": "medium",
            "classification_reason": "New cluster",
            "emerging_topic_detail": "CEO Personal Branding",
        }
    ]
    normalized = validate_topic_batch_results(batch=batch, taxonomy=taxonomy, results=good)
    assert normalized[0]["classification_status"] == "review_needed"
    assert normalized[0]["emerging_topic_detail"] == "CEO Personal Branding"
    print("TOPIC_VALIDATOR_EMERGING_REVIEW_NEEDED_OK")


def test_taxonomy_evolution_candidate_extraction() -> None:
    rows = [
        {
            "title": "CEO Bluebird jadi supir taxi",
            "content": "Personal branding ala CEO Bluebird",
            "sentiment": "positive",
            "interactions": 14928,
            "topic_assignment": {
                "classification_status": "review_needed",
                "primary_topic_id": "other_emerging_topic",
                "primary_topic_label": "Topik Baru",
                "emerging_topic_detail": "CEO Personal Branding",
                "classification_reason": "Figur CEO dan leadership narrative",
            },
        },
        {
            "title": "CEO Bluebird story",
            "content": "Netizen membahas CEO sebagai driver",
            "sentiment": "neutral",
            "interactions": 120,
            "topic_assignment": {
                "classification_status": "review_needed",
                "primary_topic_id": "other_emerging_topic",
                "primary_topic_label": "Topik Baru",
                "emerging_topic_detail": "CEO Personal Branding",
            },
        },
    ]
    result = extract_taxonomy_evolution_candidates(rows, taxonomy_version="bluebird_v1")
    assert result["status"] == "HAS_CANDIDATES"
    assert result["candidate_count"] == 1
    candidate = result["candidates"][0]
    assert candidate["candidate_topic_id"] == "ceo_personal_branding"
    assert candidate["evidence_count"] == 2
    assert len(candidate["example_rows"]) == 2
    print("TAXONOMY_EVOLUTION_CANDIDATES_OK")


if __name__ == "__main__":
    test_global_noise_filter_known_ambiguous_brands()
    test_resale_noise_default_excluded_but_can_be_allowed()
    test_ambiguous_campaign_without_brand_mention_excluded()
    test_topic_result_validator_forces_review_needed_for_emerging_topic()
    test_taxonomy_evolution_candidate_extraction()
    print("GLOBAL_RELEVANCE_AND_TAXONOMY_EVOLUTION_V1_OK")
