from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reporting.enrichment import spokesperson_report_adapter as adapter
from reporting.task1.builders.mainstream_media_report import MainstreamMediaReportBuilder
from reporting.task2.renderers.mainstream_media_report_renderer import (
    _normalized_spokesperson_rows,
)


def _candidate(post_id: int, title: str, url: str, pr_value: int) -> dict:
    return {
        "canonical_post_id": post_id,
        "source_campaign": "Aqua",
        "date": "2025-10-22",
        "channel": "Online Media",
        "media_name": f"Media {post_id}",
        "title": title,
        "content": title,
        "content_snippet": title,
        "source_url": url,
        "sentiment": "neutral",
        "ad_value": pr_value // 3,
        "pr_value": pr_value,
        "readership": 1000 + post_id,
        "issue_assignment": {
            "classification_status": "classified",
            "primary_topic_id": "source_water",
            "primary_topic_label": "Sumber Air",
        },
    }


def _result(post_id: int, name: str, *, status: str = "relevant", represented_campaign=None) -> dict:
    return {
        "canonical_post_id": post_id,
        "status": status,
        "source": "llm_enriched",
        "confidence": "high",
        "reason": "Named person is attributed in the article.",
        "spokespersons": [] if not name else [
            {
                "spokesperson_name": name,
                "spokesperson_role": "Gubernur Jawa Barat",
                "organization": "Pemerintah Provinsi Jawa Barat",
                "spokesperson_type": "government_official",
                "represented_campaign": represented_campaign,
                "evidence_sentence": f"{name} menjelaskan hasil sidak.",
                "confidence": "high",
            }
        ],
    }


def main() -> None:
    candidates = [
        _candidate(101, "Dedi Mulyadi menjelaskan sidak sumber air", "https://example.com/101", 100),
        _candidate(102, "Dedi Mulyadi memberi keterangan resmi", "https://example.com/102", 900),
        _candidate(103, "Dr Aqua menjawab pertanyaan iklan", "https://example.com/103", 800),
        _candidate(104, "Berita kriminal Lampung yang tidak terkait", "https://example.com/104", 700),
        _candidate(105, "KDM atau Dedi Mulyadi kembali menjelaskan sidak", "https://example.com/105", 300),
    ]
    cached = {
        "101": [_result(101, "Dedi")],
        "102": [_result(102, "Dedi Mulyadi")],
        "103": [_result(103, "Dr Aqua", represented_campaign="Aqua")],
        "104": [_result(104, "Jaka", status="not_relevant")],
        "105": [_result(105, "KDM")],
    }

    original_exact_loader = adapter.load_exact_spokesperson_results
    original_id_loader = adapter.load_spokesperson_results_by_ids
    adapter.load_exact_spokesperson_results = lambda candidates: {
        f"{item['canonical_post_id']}::{item.get('content_hash') or ''}": cached[str(item["canonical_post_id"])][0]
        for item in candidates
        if str(item.get("canonical_post_id")) in cached
    }
    adapter.load_spokesperson_results_by_ids = lambda ids: {
        str(key): cached[str(key)] for key in ids if str(key) in cached
    }
    try:
        overview = adapter.build_mmr_spokesperson_overview(
            candidates=candidates,
            brand_universe=["Aqua"],
            load_cache=True,
            top_n=10,
        )
        campaign_safe = adapter.build_spokesperson_report_views(
            candidates=candidates,
            brand_universe=["Aqua"],
            load_cache=True,
            top_n=10,
        )
    finally:
        adapter.load_exact_spokesperson_results = original_exact_loader
        adapter.load_spokesperson_results_by_ids = original_id_loader

    rows = overview["rows"]
    assert len(rows) == 1, rows
    row = rows[0]
    assert row["spokesperson"] == "Dedi Mulyadi", row
    assert row["article_count"] == 3, row
    assert set(row["aliases_merged"]) == {"Dedi", "KDM"}, row
    assert row["top_article_url"] == "https://example.com/102", row
    assert row["top_article_title"] == "Dedi Mulyadi memberi keterangan resmi", row
    assert row["source"] == "spokesperson_enrichment_cache", row
    assert overview["readiness"]["excluded_from_report_counts"]["brand_persona"] == 1
    assert all(item["spokesperson"] not in {"Dr Aqua", "Jaka"} for item in rows)

    # Campaign-safe by-brand view must not assign government officials to Aqua
    # only because the articles were collected under the Aqua campaign.
    top_by_brand = campaign_safe["qualitative_views"]["ql_top_spokespersons_by_brand"]["rows"]
    assert all(item.get("spokesperson_name") != "Dedi Mulyadi" for item in top_by_brand)
    assert all(item.get("spokesperson_name") != "Dr Aqua" for item in top_by_brand)

    report_input = {
        "quantitative_views": {
            "qt_mm_spokesperson_overview": {
                "rows": rows,
                "metadata": {"status": "READY"},
            }
        }
    }
    rendered = _normalized_spokesperson_rows(report_input)
    assert len(rendered) == 1, rendered
    assert rendered[0]["spokesperson"] == "Dedi Mulyadi"
    assert rendered[0]["top_article_url"] == "https://example.com/102"

    builder_source = inspect.getsource(MainstreamMediaReportBuilder._add_spokesperson_overview)
    assert "build_mmr_spokesperson_overview" in builder_source
    assert 'grouped[str(article["spokesperson"])]' not in builder_source
    assert "classification_status" in builder_source

    print("MMR_CACHE_SOURCE_USED_OK")
    print("MMR_ALIAS_NORMALIZATION_OK")
    print("MMR_BRAND_PERSONA_EXCLUDED_OK")
    print("MMR_OFF_TOPIC_EXCLUDED_OK")
    print("MMR_EVIDENCE_URL_ROW_INTEGRITY_OK")
    print("MMR_SPOKESPERSON_CACHE_INTEGRATION_V1_OK")


if __name__ == "__main__":
    main()
