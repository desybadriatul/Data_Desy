from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reporting.task2.renderers.daily_social_media_report_renderer import _daily_client_polish_package_v1
from reporting.task2.renderers.competitive_analysis_report_renderer import _ca_client_polish_package_v1
from reporting.task2.renderers.mainstream_media_report_renderer import _mmr_client_polish_package_v1
from reporting.task2.renderers.render_quality_gate import validate_render_package_quality_gate


def _visible(obj) -> str:
    return str(obj)


def test_daily_client_language_polish() -> None:
    package = {
        "report_type_id": "daily_social_media_report",
        "slides": [
            {"section": "Thematic Topics", "title": "TEMA PERCAKAPAN", "components": [
                {"type": "card", "topic": "Tidak relevan", "text": "Konten ulang tahun anak — tidak membicarakan produk."}
            ]},
            {"section": "Daily Action Plan", "title": "DAILY ACTION PLAN", "cards": [
                {"action_type": "Prepare Response", "focus_area": "P3I", "recommended_action": "Siapkan penjelasan berbasis regulasi"}
            ]},
            {"section": "Footer / Disclaimer", "title": "SUMBER & CATATAN", "components": [
                {"type": "note", "text": "200 konten berstatus relevansi dengan tingkat keyakinan rendah. Konten tersebut tetap dihitung dan ditandai untuk audit."}
            ]},
        ],
    }
    out = _daily_client_polish_package_v1(package)
    visible = _visible(out)
    assert "Tidak relevan" not in visible
    assert "Penyebutan brand insidental" in visible
    assert "SINYAL AWAL TEMA PERCAKAPAN" in visible
    assert "1-page internal Q&A" in visible
    assert "Catatan kualitas relevansi" in visible


def test_ca_client_polish() -> None:
    package = {
        "report_type_id": "competitive_analysis",
        "client_brand": "Le Minerale",
        "slides": [
            {"section": "Competitive Action Plan", "title": "COMPETITIVE ACTION PLAN", "cards": [
                {"action_type": "Exploit White Space", "recommended_action": "Ambil whitespace dari format/channel.", "supporting_evidence": {"brand": "Aqua", "sentiment": "positive", "content": "mitra dagang", "evidence_link": {"label": "Lihat post ↗", "url": "https://example.com"}}}
            ]},
            {"section": "Competitive Landscape Evidence", "title": "CONCENTRATION CHECK"},
        ],
    }
    out = _ca_client_polish_package_v1(package)
    visible = _visible(out)
    assert "mitra dagang" not in visible.lower()
    assert "akun retail/komersial pihak ketiga" in visible
    assert "product proof" in visible
    card = out["slides"][0]["cards"][0]
    assert card["evidence_link"]["url"] == "https://example.com"
    assert card["link_label"].startswith("Lihat post")


def test_mmr_client_polish() -> None:
    package = {
        "report_type_id": "mainstream_media_report",
        "slides": [
            {"section": "Media Response Action Plan", "title": "MEDIA RESPONSE ACTION PLAN", "cards": [
                {"action_type": "Activate Spokesperson", "focus_area": "Dedi Mulyadi", "rationale": "old"}
            ]},
            {"section": "Media Contributors", "title": "MEDIA CONTRIBUTORS", "cards": [
                {"media_name": "RMOL", "priority": "HIGH", "dominant_framing": "regulator"}
            ]},
        ],
    }
    out = _mmr_client_polish_package_v1(package)
    visible = _visible(out)
    assert "Aqua/Danone technical spokesperson" in visible
    assert "external_framing_actor" in visible
    assert "follow_up_mode" in visible


def test_quality_gate_blocks_unpolished_daily() -> None:
    bad = {
        "report_type_id": "daily_social_media_report",
        "slides": [
            {"section": "Executive Summary", "title": "EXECUTIVE SUMMARY"},
            {"section": "Daily Action Plan", "title": "Daily Action Plan", "text": "Tidak relevan"},
        ],
    }
    result = validate_render_package_quality_gate(bad, report_type="daily_social_media_report")
    assert result["status"] == "FAIL"
    assert any("tidak relevan" in err.casefold() for err in result["errors"])


def main() -> None:
    test_daily_client_language_polish()
    print("DAILY_CLIENT_LANGUAGE_POLISH_OK")
    test_ca_client_polish()
    print("CA_ACTION_POLISH_OK")
    test_mmr_client_polish()
    print("MMR_ACTION_WORDING_POLISH_OK")
    test_quality_gate_blocks_unpolished_daily()
    print("RENDER_GATE_CLIENT_POLISH_BLOCKS_UNPOLISHED_OK")
    print("REPORT_CLIENT_POLISH_V1_OK")


if __name__ == "__main__":
    main()
