"""Regression test for CA client-facing strategic QA package quality."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import psycopg  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    import types

    psycopg_mod = types.ModuleType("psycopg")
    psycopg_mod.__path__ = []
    rows_mod = types.ModuleType("psycopg.rows")
    rows_mod.dict_row = None
    types_mod = types.ModuleType("psycopg.types")
    types_mod.__path__ = []
    json_mod = types.ModuleType("psycopg.types.json")

    class Jsonb:
        def __init__(self, value):
            self.value = value

    json_mod.Jsonb = Jsonb
    sys.modules.setdefault("psycopg", psycopg_mod)
    sys.modules.setdefault("psycopg.rows", rows_mod)
    sys.modules.setdefault("psycopg.types", types_mod)
    sys.modules.setdefault("psycopg.types.json", json_mod)

from reporting.task2.renderers import competitive_analysis_report_renderer as renderer


def _view(rows, metadata=None):
    return {"metadata": metadata or {"status": "READY"}, "rows": rows}


def _mock_report_input():
    return {
        "report_input_id": "ri_ca_strategic_qa_v1",
        "report_type_id": "competitive_analysis",
        "context": {
            "project_name": "Le Minerale Competitive Analysis",
            "period": {"start_date": "2026-06-21", "end_date": "2026-06-23"},
            "channels": ["TikTok", "Instagram", "Twitter"],
            "client_brand": "Le Minerale",
            "competitor_brands": ["Aqua", "Aquviva"],
        },
        "validation": {"status": "PASS", "missing_views": [], "warnings": [], "errors": []},
        "metric_readiness": {"status": "READY"},
        "data_health": {},
        "limitations": ["Window 3 hari; narrative signal directional."],
        "evidence_log": [],
        "quantitative_views": {
            "qt_ca_brand_status": _view([
                {"brand": "Le Minerale", "tag": "client"},
                {"brand": "Aqua", "tag": "competitor"},
                {"brand": "Aquviva", "tag": "competitor"},
            ]),
            "qt_ca_kpi_summary_by_brand": _view([
                {"brand": "Le Minerale", "count_content": 565, "sum_engagement": 92896, "sum_interactions": 92896, "engagement_per_content": 164},
                {"brand": "Aqua", "count_content": 629, "sum_engagement": 303767, "sum_interactions": 303767, "engagement_per_content": 483},
                {"brand": "Aquviva", "count_content": 65, "sum_engagement": 17942, "sum_interactions": 17942, "engagement_per_content": 276},
            ]),
            "qt_ca_brand_volume_engagement": _view([
                {"brand": "Aqua", "count_content": 629, "engagement": 303767, "sov_pct": 50.0, "soe_pct": 73.3, "engagement_per_content": 483},
                {"brand": "Le Minerale", "count_content": 565, "engagement": 92896, "sov_pct": 44.9, "soe_pct": 22.4, "engagement_per_content": 164},
                {"brand": "Aquviva", "count_content": 65, "engagement": 17942, "sov_pct": 5.2, "soe_pct": 4.3, "engagement_per_content": 276},
            ]),
            "qt_ca_sentiment_by_brand": _view([
                {"brand": "Le Minerale", "sentiment": "negative", "count_content": 109, "engagement": 42649},
                {"brand": "Le Minerale", "sentiment": "positive", "count_content": 195, "engagement": 37206},
                {"brand": "Aqua", "sentiment": "positive", "count_content": 171, "engagement": 240000},
            ]),
            "qt_ca_channel_mix_by_brand": _view([
                {"brand": "Aqua", "channel": "Instagram", "count_content": 48, "engagement": 288325},
                {"brand": "Le Minerale", "channel": "TikTok", "count_content": 238, "engagement": 57497},
            ]),
            "qt_ca_content_type_by_brand": _view([
                {"brand": "Aqua", "media_type": "Carousel", "count_content": 15, "engagement": 222430},
                {"brand": "Le Minerale", "media_type": "TikTok", "count_content": 238, "engagement": 57497},
            ]),
        },
        "qualitative_views": {
            "ql_ca_top_social_posts_by_brand": _view([
                {"brand": "Aqua", "author": "sehataqua", "channel": "Instagram", "sentiment": "positive", "engagement": 186645, "topic": "Timnas U-17", "content": "Konten Timnas U-17 Sehat AQUA", "source_url": "https://www.instagram.com/p/testaqua/"},
                {"brand": "Le Minerale", "author": "waterstationslawi", "channel": "TikTok", "sentiment": "positive", "engagement": 26354, "topic": "UGC", "content": "makasii ya yang uda pada mampirr #leminerale", "source_url": "https://www.tiktok.com/@water/video/1"},
                {"brand": "Le Minerale", "author": "kyyneedhedon", "channel": "TikTok", "sentiment": "negative", "engagement": 26485, "topic": "Meme negatif", "content": "pertamax sama turbo mahal, pake le minerale aja", "source_url": "https://www.tiktok.com/@kyy/video/2"},
                # Same cross-brand row duplicated under wrong brands; renderer should merge and infer Aquviva from content.
                {"brand": "Le Minerale", "author": "Marketing Mentor Indonesia", "channel": "Instagram", "sentiment": "positive", "engagement": 15992, "topic": "Unclassified / Needs LLM", "content": "AQUVIVA silent killer di red ocean AMDK", "source_url": "https://www.instagram.com/p/aquviva/"},
                {"brand": "Aqua", "author": "Marketing Mentor Indonesia", "channel": "Instagram", "sentiment": "positive", "engagement": 15992, "topic": "Unclassified / Needs LLM", "content": "AQUVIVA silent killer di red ocean AMDK", "source_url": "https://www.instagram.com/p/aquviva/"},
            ]),
            "ql_ca_positive_negative_highlights": _view([
                {"brand": "Le Minerale", "author": "waterstationslawi", "channel": "TikTok", "sentiment": "positive", "engagement": 26354, "content": "makasii ya yang uda pada mampirr #leminerale", "source_url": "https://www.tiktok.com/@water/video/1"},
                {"brand": "Le Minerale", "author": "kyyneedhedon", "channel": "TikTok", "sentiment": "negative", "engagement": 26485, "content": "pertamax sama turbo mahal, pake le minerale aja", "source_url": "https://www.tiktok.com/@kyy/video/2"},
                {"brand": "Le Minerale", "author": "leminerale_id", "channel": "TikTok", "sentiment": "negative", "engagement": 8, "content": "bukan air alam murni tapi air keringat orang lain", "source_url": "https://www.tiktok.com/@leminerale_id/video/3?commentId=1"},
            ]),
            "ql_ca_topic_sentiment_by_brand": _view([
                {"brand": "Le Minerale", "topic": "Unclassified / Needs LLM", "sentiment": "negative", "engagement": 100, "count_content": 5, "content": "internal label should not show", "source_url": "https://www.tiktok.com/@user/video/456"},
                {"brand": "Le Minerale", "topic": "Keluhan rasa", "sentiment": "negative", "engagement": 90, "count_content": 4, "content": "rasa berubah", "source_url": "https://www.tiktok.com/@user/video/457"},
            ], metadata={"status": "READY", "coverage_pct": 10.2}),
            "ql_ca_top_authors_by_brand": _view([
                {"brand": "Le Minerale", "author": "Marketing Mentor Indonesia", "channel": "Instagram", "sentiment": "positive", "engagement": 15992, "content": "AQUVIVA silent killer di red ocean AMDK", "source_url": "https://www.instagram.com/p/aquviva/"},
                {"brand": "Aqua", "author": "Marketing Mentor Indonesia", "channel": "Instagram", "sentiment": "positive", "engagement": 15992, "content": "AQUVIVA silent killer di red ocean AMDK", "source_url": "https://www.instagram.com/p/aquviva/"},
            ]),
        },
    }


def test_ca_strategic_qa_v1() -> None:
    original_get = renderer.get_report_input
    original_outline = renderer.build_report_outline_from_id
    try:
        renderer.get_report_input = lambda _report_input_id: _mock_report_input()
        renderer.build_report_outline_from_id = lambda *_args, **_kwargs: {"outline_id": "ro_test", "outline_status": "READY"}
        package = renderer.build_competitive_analysis_report_package(
            "ri_ca_strategic_qa_v1",
            audience_context="Management",
            allow_partial=True,
        )
    finally:
        renderer.get_report_input = original_get
        renderer.build_report_outline_from_id = original_outline

    assert package["success"] is True
    assert package["render_package_version"].endswith("v4_strategic_qa")
    assert package["quality_checks"]["client_facing_policy"]["status"] == "PASS"
    assert package["quality_checks"]["strategic_qa"]["status"] == "PASS", package["quality_checks"]["strategic_qa"]

    action_slide = package["slides"][2]
    assert action_slide["section"] == "Competitive Action Plan"
    action_text = str(action_slide)
    assert "SOV 44,9%" in action_text
    assert "SOE 22,4%" in action_text
    assert "SOV 0,0%" not in action_text
    assert "SOE 0,0%" not in action_text

    mitigate = next(card for card in action_slide["cards"] if card["action_type"] == "Mitigate Competitive Risk")
    ev = mitigate["supporting_evidence"]
    assert ev["sentiment"] == "negative"
    assert "pertamax" in str(ev).casefold() or "keringat" in str(ev).casefold()
    assert "makasii" not in str(ev).casefold()

    concentration_slide = next(slide for slide in package["slides"] if slide["title"] == "CONCENTRATION CHECK")
    aqua = next(card for card in concentration_slide["cards"] if card["brand"] == "Aqua")
    assert aqua["top_post_share_pct"] >= 60
    assert "sistemik" in aqua["readout"].casefold()

    playbook_slide = next(slide for slide in package["slides"] if slide["section"] == "Best Practices & Competitive Playbook")
    playbook_text = str(playbook_slide).casefold()
    assert "unclassified / needs llm" not in playbook_text
    assert playbook_text.count("marketing mentor indonesia") <= 1
    assert "'brand': 'le minerale'" not in playbook_text or "aquviva silent killer" not in playbook_text

    visible = str(package["slides"]).casefold()
    assert "evidence id" not in visible
    assert "url lengkap" not in visible


if __name__ == "__main__":
    test_ca_strategic_qa_v1()
    print("CA_STRATEGIC_QA_V1_OK")
