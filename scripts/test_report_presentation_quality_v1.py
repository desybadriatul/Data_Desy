"""Regression checks for client-facing report presentation quality v1."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from reporting.task2.renderers.evidence_link_helper import (  # noqa: E402
    client_evidence_card,
    evidence_cta_label,
    validate_client_facing_presentation_package,
)


def main() -> None:
    assert evidence_cta_label({"channel": "Online Media", "source_url": "https://example.com/a"}) == "Buka artikel ↗"
    assert evidence_cta_label({"channel": "TikTok", "source_url": "https://tiktok.com/@a/video/1"}) == "Lihat post ↗"
    assert evidence_cta_label({"channel": "TikTok", "source_url": "https://tiktok.com/@a/video/1?commentId=9"}) == "Lihat komentar ↗"
    print("NATURAL_EVIDENCE_LABELS_OK")

    card = client_evidence_card({
        "title": "Contoh artikel",
        "media_name": "Media A",
        "channel": "Online Media",
        "sentiment": "negative",
        "source_url": "https://example.com/article",
    })
    assert card["link_label"] == "Buka artikel ↗"
    assert card["evidence_link"]["url"] == "https://example.com/article"
    assert "source_url" not in card
    assert "evidence_id" not in card
    print("CLIENT_EVIDENCE_CARD_OK")

    good_mmr = {
        "slides": [
            {"section": "Header", "title": "MAINSTREAM MEDIA REPORT"},
            {"section": "Executive Summary", "title": "EXECUTIVE SUMMARY", "first_evidence": card},
            {"section": "Media Response Action Plan", "title": "MEDIA RESPONSE ACTION PLAN", "actions": [{"supporting_evidence": card}]},
        ]
    }
    good = validate_client_facing_presentation_package(good_mmr, report_type="mainstream_media_report")
    assert good["status"] == "PASS", good
    print("MMR_CLIENT_FACING_PACKAGE_OK")

    bad_ca = {
        "slides": [
            {"section": "Header / Report Identity", "title": "COMPETITIVE ANALYSIS"},
            {"section": "Executive Summary", "title": "EXECUTIVE SUMMARY"},
            {
                "section": "Competitive Action Plan",
                "title": "COMPETITIVE ACTION PLAN",
                "cards": [{"evidence_id": "E01", "source_url": "https://example.com/raw", "text": "lihat E01"}],
            },
        ]
    }
    bad = validate_client_facing_presentation_package(bad_ca, report_type="competitive_analysis")
    assert bad["status"] == "FAIL", bad
    assert bad["errors"], bad
    print("CLIENT_FACING_REJECTS_AUDIT_IDS_AND_RAW_URLS_OK")

    print("REPORT_PRESENTATION_QUALITY_V1_OK")


if __name__ == "__main__":
    main()
