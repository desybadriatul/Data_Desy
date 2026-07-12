"""Regression tests for final render package quality gate v1."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reporting.task2.renderers.render_quality_gate import (  # noqa: E402
    apply_render_package_quality_gate,
    validate_render_package_quality_gate,
)


def _base_ca_package() -> dict:
    return {
        "success": True,
        "report_type_id": "competitive_analysis",
        "client_brand": "Le Minerale",
        "quality_checks": {
            "evidence_integrity": {"status": "PASS", "errors": []},
            "client_facing_policy": {"status": "PASS", "errors": []},
            "strategic_qa": {"status": "PASS", "errors": []},
        },
        "slides": [
            {"slide_no": 1, "section": "Header / Report Identity", "title": "COMPETITIVE ANALYSIS"},
            {"slide_no": 2, "section": "Executive Summary", "title": "EXECUTIVE SUMMARY"},
            {
                "slide_no": 3,
                "section": "Competitive Action Plan",
                "title": "COMPETITIVE ACTION PLAN",
                "cards": [
                    {
                        "priority": "HIGH",
                        "action_type": "Mitigate Competitive Risk",
                        "focus_area": "Risiko negatif Le Minerale",
                        "recommended_action": "Tahan eskalasi isu rasa/sumber dengan proof-point singkat.",
                        "rationale": "Konten negatif client memiliki engagement tinggi.",
                        "supporting_evidence": {
                            "brand": "Le Minerale",
                            "sentiment": "negative",
                            "headline": "Keluhan rasa dan sumber",
                            "evidence_cta": {"label": "Lihat post", "url": "https://www.tiktok.com/@a/video/1"},
                        },
                        "expected_impact": "Mengurangi risiko narasi negatif melebar.",
                    }
                ],
            },
            {
                "slide_no": 4,
                "section": "Competitive Landscape Evidence",
                "title": "CONCENTRATION CHECK",
                "cards": [{"brand": "Aqua", "top_share_pct": 61, "interpretation": "event/content-driven"}],
            },
            {
                "slide_no": 5,
                "section": "Competitive Landscape Evidence",
                "title": "COMPETITIVE LANDSCAPE EVIDENCE",
                "table": [
                    {"brand": "Aqua", "content": 629, "sov_pct": 50.0, "soe_pct": 73.3},
                    {"brand": "Le Minerale", "content": 565, "sov_pct": 44.9, "soe_pct": 22.4},
                ],
            },
            {"slide_no": 6, "section": "Scope & Methodology", "title": "SCOPE & METHODOLOGY"},
        ],
    }


def _assert_pass(result: dict, name: str) -> None:
    assert result["status"] == "PASS", f"{name} should PASS, got {result}"


def _assert_fail(result: dict, name: str, needle: str) -> None:
    assert result["status"] == "FAIL", f"{name} should FAIL"
    joined = "\n".join(result.get("errors") or [])
    assert needle.casefold() in joined.casefold(), f"{name} missing expected error {needle!r}: {joined}"


def test_gate_passes_safe_ca_package() -> None:
    result = validate_render_package_quality_gate(_base_ca_package(), report_type="competitive_analysis")
    _assert_pass(result, "safe CA package")
    print("RENDER_QA_SAFE_CA_PACKAGE_OK")


def test_gate_accepts_natural_cta_with_arrow_suffix() -> None:
    package = _base_ca_package()
    package["slides"][2]["cards"][0]["supporting_evidence"]["evidence_cta"] = {
        "label": "Lihat post ↗",
        "url": "https://www.tiktok.com/@a/video/1",
    }
    result = validate_render_package_quality_gate(package, report_type="competitive_analysis")
    _assert_pass(result, "natural CTA with arrow suffix")
    print("RENDER_QA_NATURAL_CTA_ARROW_SUFFIX_OK")


def test_gate_blocks_failed_subcheck() -> None:
    package = _base_ca_package()
    package["quality_checks"]["strategic_qa"] = {"status": "FAIL", "errors": ["bad evidence"]}
    result = validate_render_package_quality_gate(package, report_type="competitive_analysis")
    _assert_fail(result, "failed subcheck", "strategic_qa")
    print("RENDER_QA_FAILED_SUBCHECK_BLOCKED_OK")


def test_gate_blocks_visible_audit_id_and_raw_url() -> None:
    package = _base_ca_package()
    package["slides"][2]["cards"][0]["recommended_action"] = "Review E04 at https://example.com/post"
    result = validate_render_package_quality_gate(package, report_type="competitive_analysis")
    _assert_fail(result, "visible audit/raw URL", "raw URL")
    joined = "\n".join(result.get("errors") or [])
    assert "E04" in joined
    print("RENDER_QA_VISIBLE_AUDIT_AND_RAW_URL_BLOCKED_OK")


def test_gate_blocks_internal_wording() -> None:
    package = _base_ca_package()
    package["slides"][4]["interpretation"] = "Unclassified / Needs LLM topic should be reviewed"
    result = validate_render_package_quality_gate(package, report_type="competitive_analysis")
    _assert_fail(result, "internal wording", "needs llm")
    print("RENDER_QA_INTERNAL_WORDING_BLOCKED_OK")


def test_gate_blocks_false_zero_client_metric() -> None:
    package = _base_ca_package()
    package["slides"][2]["cards"][0]["rationale"] = "Le Minerale memiliki SOV 0,0% dan SOE 0,0%."
    result = validate_render_package_quality_gate(package, report_type="competitive_analysis")
    _assert_fail(result, "false zero client metric", "SOV/SOE")
    print("RENDER_QA_FALSE_ZERO_CLIENT_METRIC_BLOCKED_OK")


def test_gate_blocks_mismatched_risk_evidence() -> None:
    package = _base_ca_package()
    package["slides"][2]["cards"][0]["supporting_evidence"]["sentiment"] = "positive"
    result = validate_render_package_quality_gate(package, report_type="competitive_analysis")
    _assert_fail(result, "mismatched risk evidence", "non-negative")
    print("RENDER_QA_RISK_EVIDENCE_ALIGNMENT_BLOCKED_OK")


def test_apply_gate_blocks_package() -> None:
    package = _base_ca_package()
    package["quality_checks"]["strategic_qa"] = {"status": "FAIL", "errors": ["bad evidence"]}
    out = apply_render_package_quality_gate(package, report_type="competitive_analysis")
    assert out["success"] is False
    assert out["workflow_status"] == "BLOCKED_BY_RENDER_QA"
    assert out["quality_checks"]["render_package_quality_gate_v1"]["status"] == "FAIL"
    print("RENDER_QA_APPLY_GATE_BLOCKS_PACKAGE_OK")


if __name__ == "__main__":
    test_gate_passes_safe_ca_package()
    test_gate_accepts_natural_cta_with_arrow_suffix()
    test_gate_blocks_failed_subcheck()
    test_gate_blocks_visible_audit_id_and_raw_url()
    test_gate_blocks_internal_wording()
    test_gate_blocks_false_zero_client_metric()
    test_gate_blocks_mismatched_risk_evidence()
    test_apply_gate_blocks_package()
    print("RENDER_PACKAGE_QUALITY_GATE_V1_OK")
