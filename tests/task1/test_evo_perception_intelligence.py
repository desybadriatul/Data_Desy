from __future__ import annotations

from copy import deepcopy

import pytest

from reporting.task1.base_builder import BuildRequest
from reporting.task1.builders import evo_perception_intelligence as evo_builder
from reporting.task2.renderers import (
    evo_perception_intelligence_report_renderer as evo_renderer,
)
from reporting.task2.workflows import (
    evo_perception_intelligence_report_workflow as evo_workflow,
)


ATTRIBUTE_MAP = {
    "map_id": "test_map_v1",
    "map_version": "1.0",
    "map_name": "Test Map",
    "map_source": "client_approved",
    "category": "test",
    "attributes": [
        {
            "attribute_id": "ATTR_EXP_RELIABILITY",
            "attribute": "Reliability",
            "driver": "Experience",
            "working_definition": "Works consistently.",
            "positive_cues": [],
            "negative_cues": [],
            "exclusion_cues": [],
        },
        {
            "attribute_id": "ATTR_VAL_ACCOUNTABILITY",
            "attribute": "Accountability",
            "driver": "Values",
            "working_definition": "Owns problems honestly.",
            "positive_cues": [],
            "negative_cues": [],
            "exclusion_cues": [],
        },
        {
            "attribute_id": "ATTR_OFF_AFFORDABILITY",
            "attribute": "Affordability",
            "driver": "Offer",
            "working_definition": "Fair value for money.",
            "positive_cues": [],
            "negative_cues": [],
            "exclusion_cues": [],
        },
    ],
}


def _post(
    brand: str,
    attribute_id: str,
    label: str,
    driver: str,
    sentiment: str,
    interactions: int,
    source_type: str,
) -> dict:
    key = f"{brand}-{attribute_id}-{interactions}"
    return {
        "project_name": brand,
        "canonical_key": f"url:https://example.com/{key}",
        "content_hash": key,
        "title": f"{brand} {label}",
        "content": f"Evidence about {label} for {brand}.",
        "url": f"https://example.com/{key}",
        "sentiment": sentiment,
        "interactions": interactions,
        "views": interactions * 10,
        "source_type": source_type,
        "eligible": True,
        "evo_attribute_assignment": {
            "classification_status": "classified",
            "primary_attribute_id": attribute_id,
            "primary_attribute_label": label,
            "primary_driver": driver,
            "issue_name": label,
            "confidence": 0.9,
        },
    }


@pytest.fixture
def enriched_payload() -> dict:
    posts = [
        _post("Focus", "ATTR_EXP_RELIABILITY", "Reliability", "Experience", "negative", 20, "social"),
        _post("Focus", "ATTR_VAL_ACCOUNTABILITY", "Accountability", "Values", "positive", 15, "owned"),
        _post("Focus", "ATTR_OFF_AFFORDABILITY", "Affordability", "Offer", "neutral", 10, "earned"),
        _post("Benchmark", "ATTR_EXP_RELIABILITY", "Reliability", "Experience", "positive", 30, "earned"),
        _post("Benchmark", "ATTR_VAL_ACCOUNTABILITY", "Accountability", "Values", "neutral", 12, "social"),
        _post("Benchmark", "ATTR_OFF_AFFORDABILITY", "Affordability", "Offer", "positive", 25, "owned"),
    ]
    return {
        "focus_brand": "Focus",
        "scope": {
            "brand_universe": ["Focus", "Benchmark"],
            "missing_campaigns": [],
        },
        "attribute_map": deepcopy(ATTRIBUTE_MAP),
        "posts": posts,
        "classification_audit": {
            "basis": "canonical_unique_post",
            "population_total": 6,
            "sampled_total": 6,
            "classified_tagged_total": 6,
            "not_relevant_total": 0,
            "unmapped_review_total": 0,
            "unclassified_total": 0,
            "reconciliation": True,
            "population_coverage_pct": 100.0,
            "attribute_basis_total": 6,
        },
    }


def _build(monkeypatch: pytest.MonkeyPatch, enriched_payload: dict) -> dict:
    monkeypatch.setattr(
        evo_builder,
        "get_evo_enriched_scope_posts",
        lambda **_: deepcopy(enriched_payload),
    )
    builder = evo_builder.EVOPerceptionIntelligenceBuilder()
    request = BuildRequest(
        project_name="Focus",
        start_date="2026-07-01",
        end_date="2026-07-07",
        confirmed_intent_id="test:evo",
        client_brand="Focus",
        competitor_brands=("Benchmark",),
        metric_readiness={"status": "PASS", "basis": "test canonical posts"},
        data_health={"status": "PASS", "canonical_posts": 6},
        scope={
            "primary_reader": "Management",
            "desired_perception": "Reliable and fair",
        },
    )
    return builder.build(request)


def test_evo_builder_is_registry_valid_and_excludes_focus_from_best_brand(
    monkeypatch: pytest.MonkeyPatch,
    enriched_payload: dict,
) -> None:
    report_input = _build(monkeypatch, enriched_payload)

    assert report_input["validation"]["status"] == "PASS"
    attributes = report_input["quantitative_views"]["qt_evo_attribute_scorecard"]["rows"]
    focus_rows = [row for row in attributes if row["Brand"] == "Focus"]
    assert len(focus_rows) == len(ATTRIBUTE_MAP["attributes"])
    assert all(row["Best Brand"] == "Benchmark" for row in focus_rows)
    assert all(row["Best Brand"] != "Focus" for row in focus_rows)

    reliability = next(row for row in focus_rows if row["Attribute ID"] == "ATTR_EXP_RELIABILITY")
    assert reliability["Attribute Score"] == 0.0
    assert reliability["Best Brand Score"] == 100.0
    assert reliability["Attribute Gap"] == 100.0
    assert reliability["Whitespace"] is True


def test_evo_builder_separates_journey_stages_and_freezes_metrics(
    monkeypatch: pytest.MonkeyPatch,
    enriched_payload: dict,
) -> None:
    report_input = _build(monkeypatch, enriched_payload)
    journey = report_input["quantitative_views"]["qt_evo_journey_matrix"]["rows"]
    focus = next(row for row in journey if row["Brand"] == "Focus")

    assert focus["Awareness"] == 1
    assert focus["Engagement"] == 1
    assert focus["Perception Impact"] == 1
    assert report_input["evo"]["metric_manifest"]["attribute_score_formula"].startswith(
        "count_sentiment_point"
    )


def test_evo_builder_matches_campaign_names_case_insensitively(
    monkeypatch: pytest.MonkeyPatch,
    enriched_payload: dict,
) -> None:
    for post in enriched_payload["posts"]:
        post["project_name"] = str(post["project_name"]).lower()

    report_input = _build(monkeypatch, enriched_payload)
    summary = report_input["quantitative_views"]["qt_evo_brand_summary"]["rows"]

    assert next(row for row in summary if row["Brand"] == "Focus")["Total Tagged Posts"] == 3
    assert next(row for row in summary if row["Brand"] == "Benchmark")["Total Tagged Posts"] == 3


def test_evo_renderer_builds_preview_and_package(
    monkeypatch: pytest.MonkeyPatch,
    enriched_payload: dict,
) -> None:
    report_input = _build(monkeypatch, enriched_payload)
    monkeypatch.setattr(
        evo_renderer,
        "get_report_input",
        lambda _: deepcopy(report_input),
    )

    preview = evo_renderer.build_evo_report_data_preview(
        report_input["report_input_id"]
    )
    package = evo_renderer.build_evo_report_package(
        report_input["report_input_id"],
        audience_context="Management",
    )

    assert preview["success"] is True
    assert "EVO Perception Intelligence Preview" in preview["markdown"]
    assert package["success"] is True
    assert package["report_type_id"] == "evo_perception_intelligence"
    assert len(package["slides"]) >= 8
    assert package["audit_pack"]["evo_metric_manifest"]


def test_evo_workflow_enforces_audience_and_benchmark() -> None:
    audience_gate = evo_workflow.create_evo_perception_intelligence_report_workflow(
        project_name="Focus",
        focus_brand="Focus",
        start_date="2026-07-01",
        end_date="2026-07-07",
        competitor_brands=["Benchmark"],
        primary_reader="",
    )
    benchmark_gate = evo_workflow.create_evo_perception_intelligence_report_workflow(
        project_name="Focus",
        focus_brand="Focus",
        start_date="2026-07-01",
        end_date="2026-07-07",
        competitor_brands=[],
        primary_reader="Management",
    )

    assert audience_gate["workflow_status"] == "NEEDS_AUDIENCE"
    assert benchmark_gate["workflow_status"] == "NEEDS_BENCHMARK"


def test_evo_workflow_returns_claude_classification_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        evo_workflow,
        "get_evo_attribute_enrichment_status",
        lambda **_: {
            "success": True,
            "attribute_map": {"map_id": "test_map_v1"},
            "per_brand": [{"brand": "Focus", "remaining_to_target": 2}],
        },
    )
    monkeypatch.setattr(
        evo_workflow,
        "get_unclassified_evo_attribute_batch",
        lambda **_: {
            "success": True,
            "workflow_status": "NEEDS_AUTO_EVO_ATTRIBUTE_CLASSIFICATION",
            "batch_id": "batch-1",
            "posts": [{"canonical_key": "one"}],
        },
    )

    result = evo_workflow.create_evo_perception_intelligence_report_workflow(
        project_name="Focus",
        focus_brand="Focus",
        start_date="2026-07-01",
        end_date="2026-07-07",
        competitor_brands=["Benchmark"],
        primary_reader="Management",
    )

    assert result["workflow_status"] == "NEEDS_AUTO_EVO_ATTRIBUTE_CLASSIFICATION"
    assert result["requires_claude_action"] is True
    assert result["attribute_batch"]["batch_id"] == "batch-1"
