from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _daily_row(day: str, posts: int, interactions: int, negative: int = 5, positive: int = 30, top1: int = 50):
    neutral = max(0, posts - negative - positive)
    return {
        "date": day,
        "posts": posts,
        "interactions": interactions,
        "views": interactions * 10,
        "positive_posts": positive,
        "negative_posts": negative,
        "neutral_posts": neutral,
        "classified_posts": posts,
        "unclassified_posts": 0,
        "eng_positive": max(0, interactions - top1),
        "eng_negative": top1 if negative else 0,
        "eng_neutral": 0,
        "top1_interactions": top1,
        "top1_canonical_key": "canonical-top",
        "top1_title": "top post",
        "top1_author": "author",
        "top1_sentiment": "negative" if negative else "positive",
        "distinct_authors": max(1, posts // 2),
        "interactions_available_posts": posts,
        "views_available_posts": posts,
    }


def main() -> None:
    import anomaly
    import anomaly_tools
    from database import anomaly_queries

    detector_names = {item["name"] for item in anomaly.list_detectors()}
    expected = {
        "volume_spike",
        "interactions_spike",
        "views_spike",
        "volume_drop",
        "sustained_elevation",
        "engagement_concentration",
        "engagement_rate_outlier",
        "views_interactions_ratio",
        "sentiment_divergence",
        "negative_share_spike",
        "single_author_flood",
        "coordinated_burst",
        "new_author_surge",
        "trigger_term_appearance",
        "noise_contamination",
        "coverage_gap",
        "unclassified_surge",
    }
    missing = expected - detector_names
    assert not missing, f"Missing detectors: {sorted(missing)}"
    assert len(detector_names) >= 17
    print("ANOMALY_DETECTOR_REGISTRY_OK")

    base = date(2026, 1, 1)
    daily = [
        _daily_row((base + timedelta(days=i)).isoformat(), 50, 500, negative=5, positive=30, top1=50)
        for i in range(20)
    ]
    daily.append(
        _daily_row((base + timedelta(days=20)).isoformat(), 120, 20000, negative=20, positive=70, top1=15000)
    )
    ctx = anomaly.ScanContext(daily=daily, sensitivity="medium")
    result = anomaly.run_scan(ctx)
    found = {item["detector"] for item in result["findings"]}
    assert "interactions_spike" in found
    assert "engagement_concentration" in found
    assert "sentiment_divergence" in found
    print("ANOMALY_ENGINE_SYNTHETIC_SCAN_OK")

    catalog = anomaly_tools.list_anomaly_detectors()
    assert catalog["found"] is True
    assert catalog["total_detectors"] >= 17
    assert "known_limits" in catalog
    print("ANOMALY_TOOLS_IMPORT_AND_CATALOG_OK")

    # Query layer should expose the frame collectors/config methods without changing db.py.
    for name in [
        "daily_frame",
        "author_daily_frame",
        "duplicate_clusters",
        "term_daily_frame",
        "collect_frames",
        "get_anomaly_config",
        "set_anomaly_config",
    ]:
        assert hasattr(anomaly_queries, name), f"missing anomaly_queries.{name}"
    print("ANOMALY_QUERY_LAYER_IMPORT_OK")

    server_text = (ROOT / "server.py").read_text(encoding="utf-8")
    assert "mcp.tool()(scan_anomalies)" in server_text
    assert "mcp.tool()(list_anomaly_detectors)" in server_text
    assert "mcp.tool()(configure_anomaly_terms)" in server_text
    print("ANOMALY_SERVER_REGISTRATION_OK")

    print("ANOMALY_DETECTION_V1_OK")


if __name__ == "__main__":
    main()
