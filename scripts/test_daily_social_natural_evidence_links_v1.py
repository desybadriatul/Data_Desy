from pathlib import Path
import sys
import types

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Local CI/sandbox may not have psycopg installed. The renderer test does not
# touch database functions, so provide a tiny import-time stub only when needed.
if "psycopg" not in sys.modules:
    psycopg = types.ModuleType("psycopg")
    rows = types.ModuleType("psycopg.rows")
    rows.dict_row = object()
    types_mod = types.ModuleType("psycopg.types")
    json_mod = types.ModuleType("psycopg.types.json")
    class Jsonb:  # pragma: no cover - import stub only
        def __init__(self, value):
            self.value = value
    json_mod.Jsonb = Jsonb
    sys.modules["psycopg"] = psycopg
    sys.modules["psycopg.rows"] = rows
    sys.modules["psycopg.types"] = types_mod
    sys.modules["psycopg.types.json"] = json_mod

from reporting.task2.renderers.daily_social_media_report_renderer import _daily_naturalize_client_visible_package
from reporting.task2.renderers.render_quality_gate import validate_render_package_quality_gate


def _visible_strings(value):
    if isinstance(value, dict):
        out = []
        for k, v in value.items():
            if str(k) in {"url", "source_url", "full_url"}:
                continue
            out.extend(_visible_strings(v))
        return out
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(_visible_strings(item))
        return out
    if isinstance(value, str):
        return [value]
    return []


def test_daily_social_natural_evidence_links_v1():
    report_input = {
        "views": {
            "ql_dsm_content_evidence": [
                {
                    "author": "Test Author",
                    "channel": "Instagram",
                    "sentiment": "negative",
                    "topic_label": "Keluhan Layanan",
                    "interactions": 12,
                    "views": 100,
                    "source_url": "https://instagram.com/p/test/",
                    "content_snippet": "Keluhan layanan test.",
                }
            ],
            "qt_dsm_top_authors_ranked": [],
            "ql_dsm_topic_evidence": [],
        }
    }
    old_package = {
        "success": True,
        "report_type_id": "daily_social_media_report",
        "slides": [
            {
                "slide_id": "dsm_02_executive_summary",
                "title": "EXECUTIVE SUMMARY",
                "components": [],
            },
            {
                "slide_id": "dsm_03_daily_action_plan",
                "title": "DAILY ACTION PLAN",
                "components": [
                    {
                        "type": "action_plan_cards",
                        "items": [
                            {
                                "priority": "HIGH",
                                "action_type": "Respond to Risk",
                                "recommended_action": "Siapkan respons.",
                                "supporting_evidence": "S01 — Test Author / Instagram",
                                "evidence_id": "S01",
                                "evidence_refs": [
                                    {
                                        "evidence_id": "S01",
                                        "source_label": "Test Author / Instagram",
                                        "source_url": "https://instagram.com/p/test/",
                                        "channel": "Instagram",
                                        "sentiment": "negative",
                                    }
                                ],
                            }
                        ],
                    },
                    {"type": "action_plan_instruction", "text": "Evidence ID saja, URL di appendix."},
                ],
                "speaker_notes": "Use Evidence ID S01 and keep URL penuh in Appendix.",
            },
            {
                "slide_id": "dsm_09_evidence_appendix",
                "title": "APPENDIX — EVIDENCE ID & FULL URL",
                "components": [
                    {
                        "type": "evidence_url_table",
                        "items": [
                            {
                                "evidence_id": "S01",
                                "source_label": "Test Author / Instagram",
                                "sentiment": "negative",
                                "interactions": 12,
                                "source_url": "https://instagram.com/p/test/",
                            }
                        ],
                    }
                ],
            },
        ],
        "ppt_style_brief": {"must_follow": ["Use Evidence IDs on main slides."]},
        "claude_instructions": ["Render Evidence IDs on main slides."],
    }

    # The new gate must reject visible S## IDs.
    old_gate = validate_render_package_quality_gate(old_package, report_type="daily_social_media_report")
    assert old_gate["status"] == "FAIL", old_gate
    assert any("audit evidence" in err.casefold() or "internal/system" in err.casefold() for err in old_gate["errors"]), old_gate

    new_package = _daily_naturalize_client_visible_package(old_package, report_input)
    assert new_package["success"] is True, new_package.get("blocked_errors")
    assert new_package["render_quality_gate"]["status"] == "PASS", new_package["render_quality_gate"]

    visible = "\n".join(_visible_strings(new_package["slides"]))
    assert "S01" not in visible
    assert "Evidence ID" not in visible
    assert "Full URL" not in visible
    assert "URL penuh" not in visible
    assert "https://" not in visible
    assert "Lihat post ↗" in visible

    action = new_package["slides"][1]["components"][0]["items"][0]
    assert action["evidence_link"]["label"] == "Lihat post ↗"
    assert action["evidence_link"]["url"] == "https://instagram.com/p/test/"

    print("DAILY_SOCIAL_NATURAL_EVIDENCE_LINKS_V1_OK")


if __name__ == "__main__":
    test_daily_social_natural_evidence_links_v1()
