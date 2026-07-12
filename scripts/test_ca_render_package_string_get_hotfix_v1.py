"""Regression test for CA Task 2 package rendering after presentation quality patch."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# The renderer imports the storage module at import time. In local/Railway,
# psycopg is installed. In lightweight CI/sandbox runs, stub only the import
# surface because this test monkeypatches storage access and never opens DB.
try:
    import psycopg  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - dependency shim for lightweight tests
    import types

    psycopg_mod = types.ModuleType("psycopg")
    psycopg_mod.__path__ = []
    rows_mod = types.ModuleType("psycopg.rows")
    rows_mod.dict_row = None
    types_mod = types.ModuleType("psycopg.types")
    types_mod.__path__ = []
    json_mod = types.ModuleType("psycopg.types.json")

    class Jsonb:  # minimal constructor-compatible shim
        def __init__(self, value):
            self.value = value

    json_mod.Jsonb = Jsonb
    sys.modules.setdefault("psycopg", psycopg_mod)
    sys.modules.setdefault("psycopg.rows", rows_mod)
    sys.modules.setdefault("psycopg.types", types_mod)
    sys.modules.setdefault("psycopg.types.json", json_mod)

from reporting.task2.renderers import competitive_analysis_report_renderer as renderer


def _view(rows):
    return {"metadata": {"status": "READY"}, "rows": rows}


def test_ca_render_package_no_string_get_crash() -> None:
    report_input = {
        "report_input_id": "ri_ca_hotfix_v1",
        "report_type_id": "competitive_analysis",
        "context": {
            "project_name": "Le Minerale Competitive Analysis",
            "period": {"start_date": "2026-06-21", "end_date": "2026-06-23"},
            "channels": ["TikTok", "Instagram"],
            "client_brand": "Le Minerale",
            "competitor_brands": ["Aqua", "Aquviva"],
        },
        "validation": {"status": "PASS", "missing_views": [], "warnings": [], "errors": []},
        "metric_readiness": {},
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
                {"brand": "Le Minerale", "count_content": 565, "sum_engagement": 92896, "sum_interactions": 92896, "engagement_per_content": 164, "soe_pct": 22.4},
                {"brand": "Aqua", "count_content": 629, "sum_engagement": 303767, "sum_interactions": 303767, "engagement_per_content": 483, "soe_pct": 73.3},
                {"brand": "Aquviva", "count_content": 65, "sum_engagement": 17942, "sum_interactions": 17942, "engagement_per_content": 276, "soe_pct": 4.3},
            ]),
            "qt_ca_brand_volume_engagement": _view([
                {"brand": "Le Minerale", "count_content": 565, "engagement": 92896, "sov_pct": 44.9, "soe_pct": 22.4},
                {"brand": "Aqua", "count_content": 629, "engagement": 303767, "sov_pct": 50.0, "soe_pct": 73.3},
                {"brand": "Aquviva", "count_content": 65, "engagement": 17942, "sov_pct": 5.2, "soe_pct": 4.3},
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
                {"brand": "Aqua", "author": "sehataqua", "channel": "Instagram", "sentiment": "positive", "engagement": 186645, "content": "Konten Timnas U-17", "source_url": "https://www.instagram.com/p/testaqua/"},
                {"brand": "Le Minerale", "author": "user", "channel": "TikTok", "sentiment": "negative", "engagement": 26485, "content": "Meme Le Minerale viral", "source_url": "https://www.tiktok.com/@user/video/123"},
            ]),
            "ql_ca_positive_negative_highlights": _view([
                {"brand": "Le Minerale", "author": "user", "channel": "TikTok", "sentiment": "negative", "engagement": 26485, "content": "Ajakan pindah brand", "source_url": "https://www.tiktok.com/@user/video/123"},
            ]),
            "ql_ca_topic_sentiment_by_brand": _view([
                {"brand": "Le Minerale", "topic": "Keluhan rasa", "sentiment": "negative", "engagement": 100, "count_content": 5, "content": "rasa berubah", "source_url": "https://www.tiktok.com/@user/video/456"},
            ]),
            "ql_ca_top_authors_by_brand": _view([
                {"brand": "Aqua", "author": "sehataqua", "channel": "Instagram", "sentiment": "positive", "engagement": 186645, "content": "Timnas U-17", "source_url": "https://www.instagram.com/p/testaqua/"},
            ]),
        },
    }

    original_get = renderer.get_report_input
    original_outline = renderer.build_report_outline_from_id
    try:
        renderer.get_report_input = lambda _report_input_id: report_input
        renderer.build_report_outline_from_id = lambda *_args, **_kwargs: {"outline_id": "ro_test", "outline_status": "READY"}
        package = renderer.build_competitive_analysis_report_package(
            "ri_ca_hotfix_v1",
            audience_context="Management",
            allow_partial=True,
        )
    finally:
        renderer.get_report_input = original_get
        renderer.build_report_outline_from_id = original_outline

    assert package["success"] is True
    assert package["quality_checks"]["client_facing_policy"]["status"] == "PASS"
    assert len(package["slides"]) >= 10
    assert package["slides"][2]["section"] == "Competitive Action Plan"


if __name__ == "__main__":
    test_ca_render_package_no_string_get_crash()
    print("CA_RENDER_PACKAGE_STRING_GET_HOTFIX_V1_OK")
