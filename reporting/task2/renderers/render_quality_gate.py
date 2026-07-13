"""Final render-package quality gate for client-facing report decks.

This validator is intentionally stricter than schema/link checks. It blocks
packages that are technically renderable but unsafe for client-facing decks:
wrong section order, visible audit codes/raw URLs, internal system wording,
failed sub-checks, and known strategic QA regressions.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any
import re

REPORT_RENDER_QA_GATE_VERSION = "render_package_quality_gate_v1"

RAW_URL_RE = re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE)
AUDIT_ID_RE = re.compile(r"\b(?:E|T|P|S)\d{2}\b")

INTERNAL_VISIBLE_PHRASES = (
    "unclassified / needs llm",
    "needs llm",
    "raw topic extraction",
    "evidence id",
    "url lengkap",
    "full url",
    "source_url",
    "classification coverage",
    "raw url",
    "appendix / data pack",
    "url penuh",
    "quality_checks",
    "evidence_registry",
)

URL_FIELD_NAMES = {
    "url",
    "href",
    "source_url",
    "full_url",
    "raw_url",
    "link_url",
    "post_url",
    "article_url",
    "evidence_url",
    "display_url",
}

AUDIT_FIELD_NAMES = {
    "audit_evidence_id",
    "evidence_id",
    "evidence_registry",
    "quality_checks",
    "render_quality_gate",
    "source_url",
    "full_url",
    "url",
    "href",
    "link_url",
}

VISIBLE_KEYS_HINT = {
    "title",
    "subtitle",
    "headline",
    "body",
    "summary",
    "text",
    "label",
    "content",
    "snippet",
    "quote",
    "interpretation",
    "rationale",
    "recommended_action",
    "supporting_evidence",
    "expected_impact",
    "focus_area",
    "action_type",
    "priority",
    "source_label",
    "issue_label",
    "media_name",
    "brand",
    "campaign",
    "author",
    "topic",
    "dominant_framing",
    "role",
    "implication",
}

ACTION_SECTION_BY_REPORT_TYPE = {
    "competitive_analysis": "Competitive Action Plan",
    "mainstream_media_report": "Media Response Action Plan",
    "daily_social_media_report": "Daily Action Plan",
    "industry_trend": "Industry Action Plan",
    "brand_content_effectiveness": "Strategic Recommendations & Action Plan",
    "spokesperson_intelligence": "Spokesperson Action Plan",
}

EXECUTIVE_SECTION_TITLES = {"Executive Summary", "EXECUTIVE SUMMARY"}
NATURAL_CTA_LABELS = {"Buka artikel", "Lihat post", "Lihat komentar", "Buka post"}


def _is_natural_cta_label(value: Any) -> bool:
    """Return True for natural evidence CTA labels with optional arrows/suffixes.

    Renderer helpers often emit labels such as `Lihat post ↗`. The gate should
    normalize that as the same natural CTA as `Lihat post`, while still
    rejecting audit labels like `E04` or raw URL text.
    """
    label = _clean(value)
    if not label:
        return False
    label_lc = label.casefold()
    return any(label_lc == base.casefold() or label_lc.startswith(base.casefold() + " ") for base in NATURAL_CTA_LABELS)


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _casefold(value: Any) -> str:
    return _clean(value).casefold()


def _num(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    try:
        text = str(value).replace("%", "").replace(",", ".")
        return float(text)
    except Exception:
        return 0.0


def _slides(package: Mapping[str, Any]) -> list[Any]:
    slides = package.get("slides") or []
    return slides if isinstance(slides, list) else []


def _walk_visible_strings(value: Any, parent_key: str | None = None) -> list[str]:
    """Collect strings likely to be visible on client slides.

    URL fields and audit metadata are allowed to exist structurally because they
    power hyperlinks/data packs. They are not allowed to leak as visible text.
    """
    if isinstance(value, Mapping):
        out: list[str] = []
        for key, child in value.items():
            key_text = _clean(key)
            key_lc = key_text.casefold()
            if key_lc in AUDIT_FIELD_NAMES or key_lc in URL_FIELD_NAMES:
                continue
            # recurse through containers even when the key is not a known visible
            # field, because cards/lists may have arbitrary display keys.
            out.extend(_walk_visible_strings(child, key_lc))
        return out
    if isinstance(value, list):
        out: list[str] = []
        for child in value:
            out.extend(_walk_visible_strings(child, parent_key))
        return out
    if isinstance(value, str):
        text = _clean(value)
        if not text:
            return []
        # Skip strings that are pure URL values even if nested under a generic key.
        if RAW_URL_RE.fullmatch(text):
            return []
        return [text]
    return []


def _flatten_dicts(value: Any) -> list[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        out: list[Mapping[str, Any]] = [value]
        for child in value.values():
            out.extend(_flatten_dicts(child))
        return out
    if isinstance(value, list):
        out: list[Mapping[str, Any]] = []
        for child in value:
            out.extend(_flatten_dicts(child))
        return out
    return []


def _check_sub_quality_checks(package: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    checks = package.get("quality_checks") or {}
    if not isinstance(checks, Mapping):
        return errors
    for name, result in checks.items():
        if name == REPORT_RENDER_QA_GATE_VERSION:
            continue
        if isinstance(result, Mapping) and _clean(result.get("status")).upper() == "FAIL":
            detail = result.get("errors") or result.get("error") or "unknown error"
            errors.append(f"Sub quality check failed: {name}: {detail}")
    return errors


def _check_action_plan_order(package: Mapping[str, Any], report_type: str) -> list[str]:
    slides = _slides(package)
    action_section = ACTION_SECTION_BY_REPORT_TYPE.get(report_type)
    if not action_section or not slides:
        return []
    exec_idx = None
    action_idx = None
    for idx, slide in enumerate(slides):
        if not isinstance(slide, Mapping):
            continue
        section = _clean(slide.get("section"))
        title = _clean(slide.get("title"))
        if exec_idx is None and (section in EXECUTIVE_SECTION_TITLES or title in EXECUTIVE_SECTION_TITLES):
            exec_idx = idx
        if action_idx is None and (section == action_section or title.casefold() == action_section.casefold()):
            action_idx = idx
    errors: list[str] = []
    if exec_idx is None:
        errors.append("Missing Executive Summary slide/section.")
    if action_idx is None:
        errors.append(f"Missing required Action Plan section: {action_section}.")
    if exec_idx is not None and action_idx is not None and action_idx <= exec_idx:
        errors.append("Action Plan must appear immediately after Executive Summary in section order.")
    # Allow extra slides under Executive Summary only when section remains Executive Summary.
    return errors


def _check_client_facing_text(package: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    visible_strings: list[str] = []
    for slide in _slides(package):
        visible_strings.extend(_walk_visible_strings(slide))
    visible_blob = "\n".join(visible_strings)
    visible_lc = visible_blob.casefold()

    raw_url_hits = [s for s in visible_strings if RAW_URL_RE.search(s)]
    if raw_url_hits:
        errors.append(f"Visible raw URL leaked into client-facing slides: {raw_url_hits[:3]}")

    audit_id_hits = []
    for s in visible_strings:
        for match in AUDIT_ID_RE.findall(s):
            # Permit event age labels like U17 because regex does not match U17.
            audit_id_hits.append(match)
    if audit_id_hits:
        errors.append(f"Visible audit evidence IDs leaked into client-facing slides: {sorted(set(audit_id_hits))[:8]}")

    for phrase in INTERNAL_VISIBLE_PHRASES:
        if phrase in visible_lc:
            errors.append(f"Internal/system wording leaked into client-facing slides: {phrase}")
    return errors


def _check_natural_evidence_ctas(package: Mapping[str, Any]) -> list[str]:
    """If slides contain hyperlink URL fields, they must be paired with natural labels."""
    errors: list[str] = []
    has_url = False
    has_natural_label = False
    for obj in _flatten_dicts(_slides(package)):
        url = None
        for key in URL_FIELD_NAMES:
            if obj.get(key):
                url = obj.get(key)
                break
        if url:
            has_url = True
            label = _clean(obj.get("label") or obj.get("text") or obj.get("link_text") or obj.get("cta") or obj.get("evidence_label"))
            if _is_natural_cta_label(label):
                has_natural_label = True
    # Do not fail no-evidence reports. Fail only when the package carries URL-backed slide objects but no natural CTA exists.
    if has_url and not has_natural_label:
        errors.append("URL-backed evidence exists on slides but no natural CTA label found (Buka artikel/Lihat post/Lihat komentar).")
    return errors


def _ca_client_metric_row(package: Mapping[str, Any]) -> Mapping[str, Any] | None:
    client = _casefold(package.get("client_brand"))
    if not client:
        return None
    for slide in _slides(package):
        if not isinstance(slide, Mapping):
            continue
        for key in ("brand_volume_engagement", "table", "kpi_summary_by_brand"):
            rows = slide.get(key)
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, Mapping):
                    continue
                brand = _casefold(row.get("brand") or row.get("campaign") or row.get("Campaign"))
                if brand == client:
                    return row
    return None


def _check_competitive_analysis_strategic(package: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    slides = _slides(package)
    client = _clean(package.get("client_brand"))
    client_row = _ca_client_metric_row(package)
    client_has_content = bool(client_row and _num(client_row.get("content") or client_row.get("count_content") or client_row.get("Count of Content")))

    # Known fatal regression: client metrics rendered as 0.0 in action cards while source metrics exist.
    action_slide = next((s for s in slides if isinstance(s, Mapping) and _clean(s.get("section")) == "Competitive Action Plan"), {})
    action_visible = "\n".join(_walk_visible_strings(action_slide))
    if client_has_content and ("SOV 0,0%" in action_visible or "SOE 0,0%" in action_visible or "SOV 0.0%" in action_visible or "SOE 0.0%" in action_visible):
        errors.append("CA Action Plan renders client SOV/SOE as 0.0 despite available client content metrics.")

    # Mitigate Competitive Risk must not cite positive/neutral evidence.
    cards = action_slide.get("cards") if isinstance(action_slide, Mapping) else None
    if isinstance(cards, list):
        for card in cards:
            if not isinstance(card, Mapping):
                continue
            if _clean(card.get("action_type")) == "Mitigate Competitive Risk":
                ev = card.get("supporting_evidence") or card.get("evidence") or {}
                if isinstance(ev, Mapping):
                    sentiment = _casefold(ev.get("sentiment"))
                    ev_brand = _casefold(ev.get("brand") or ev.get("campaign"))
                    if sentiment and sentiment not in {"negative", "negatif"}:
                        errors.append("CA Mitigate Competitive Risk uses non-negative evidence.")
                    if client and ev_brand and ev_brand != _casefold(client):
                        errors.append("CA Mitigate Competitive Risk evidence is not attributed to the client brand.")

    if not any(isinstance(s, Mapping) and _clean(s.get("title")).casefold() == "concentration check" for s in slides):
        errors.append("CA package missing Concentration Check slide for outlier-aware SOE interpretation.")
    return errors


def _check_mmr_strategic(package: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    slides = _slides(package)
    action_slide = next((s for s in slides if isinstance(s, Mapping) and _clean(s.get("section")) == "Media Response Action Plan"), {})
    cards = action_slide.get("cards") or action_slide.get("actions") if isinstance(action_slide, Mapping) else []
    allowed_actions = {
        "Prioritize Issue Response",
        "Strengthen Positive Narrative",
        "Prepare Holding Statement",
        "Activate Spokesperson",
        "Target Media Contributors",
    }
    if isinstance(cards, list):
        for card in cards:
            if not isinstance(card, Mapping):
                continue
            action_type = _clean(card.get("action_type") or card.get("Action Type"))
            if action_type and action_type not in allowed_actions:
                errors.append(f"MMR Action Plan uses non-taxonomy action type: {action_type}")
            if action_type and not _clean(card.get("rationale") or card.get("Rationale")):
                errors.append("MMR Action Plan card missing rationale.")
    return errors


def validate_render_package_quality_gate(
    package: Mapping[str, Any],
    *,
    report_type: str | None = None,
) -> dict[str, Any]:
    report_type = report_type or _clean(package.get("report_type_id"))
    errors: list[str] = []
    warnings: list[str] = []

    errors.extend(_check_sub_quality_checks(package))
    errors.extend(_check_action_plan_order(package, report_type))
    errors.extend(_check_client_facing_text(package))
    errors.extend(_check_natural_evidence_ctas(package))

    if report_type == "competitive_analysis":
        errors.extend(_check_competitive_analysis_strategic(package))
    elif report_type == "mainstream_media_report":
        errors.extend(_check_mmr_strategic(package))

    return {
        "version": REPORT_RENDER_QA_GATE_VERSION,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "blocked_if_fail": True,
    }


def apply_render_package_quality_gate(
    package: Mapping[str, Any],
    *,
    report_type: str | None = None,
) -> dict[str, Any]:
    """Attach final render QA. If it fails, return a blocked package.

    This prevents Claude/PPT renderers from treating a technically valid but
    strategically unsafe package as client-ready.
    """
    out = deepcopy(dict(package))
    gate = validate_render_package_quality_gate(out, report_type=report_type)
    checks = dict(out.get("quality_checks") or {})
    checks[REPORT_RENDER_QA_GATE_VERSION] = gate
    out["quality_checks"] = checks
    out["render_quality_gate"] = gate
    if gate["status"] != "PASS":
        out["success"] = False
        out["workflow_status"] = "BLOCKED_BY_RENDER_QA"
        out["blocked_reason"] = "Render package failed client-facing and/or strategic QA. Fix package before PPT generation."
        out["blocked_errors"] = gate["errors"]
    return out


# ---------------------------------------------------------------------------
# report_client_polish_v1: extra client-language QA checks.
# ---------------------------------------------------------------------------
_VALIDATE_RENDER_PACKAGE_QUALITY_GATE_BEFORE_CLIENT_POLISH_V1 = validate_render_package_quality_gate
REPORT_CLIENT_POLISH_V1_GATE = True

_CLIENT_POLISH_FORBIDDEN_VISIBLE_PHRASES_V1 = (
    "tidak relevan",
    "evidence id & full url",
)


def _check_report_client_polish_v1(package: Mapping[str, Any], report_type: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    visible_strings: list[str] = []
    for slide in _slides(package):
        visible_strings.extend(_walk_visible_strings(slide))
    visible_blob = "\n".join(visible_strings)
    visible_lc = visible_blob.casefold()

    for phrase in _CLIENT_POLISH_FORBIDDEN_VISIBLE_PHRASES_V1:
        if phrase in visible_lc:
            errors.append(f"Client-facing wording is not polished: {phrase}")

    if report_type == "daily_social_media_report":
        if "klasifikasi tema" in visible_lc and "10%" in visible_lc and "sinyal awal" not in visible_lc and "early" not in visible_lc:
            warnings.append("Daily theme coverage appears low but slide does not clearly say early signal.")
        if "konteks brand rendah" in visible_lc and "directional" not in visible_lc:
            warnings.append("Daily low-context relevance is mentioned without directional-read caveat.")

    if report_type == "competitive_analysis":
        if "mitra dagang" in visible_lc or " partner" in visible_lc:
            errors.append("CA may overclaim third-party relationship as mitra/partner.")
        action_slide = next((s for s in _slides(package) if isinstance(s, Mapping) and _clean(s.get("section")) == "Competitive Action Plan"), {})
        action_blob = "\n".join(_walk_visible_strings(action_slide)).casefold()
        if "exploit white space" in action_blob and "product proof" not in action_blob and "pembuktian" not in action_blob:
            warnings.append("CA Exploit White Space action lacks concrete narrative angles.")

    if report_type == "mainstream_media_report":
        action_slide = next((s for s in _slides(package) if isinstance(s, Mapping) and _clean(s.get("section")) == "Media Response Action Plan"), {})
        action_blob = "\n".join(_walk_visible_strings(action_slide)).casefold()
        if "activate spokesperson" in action_blob and "dedi mulyadi" in action_blob:
            errors.append("MMR Activate Spokesperson should not focus on external actor Dedi Mulyadi; use brand/technical spokesperson.")
        if "dasar klarifikasi terkuat" in visible_lc:
            warnings.append("MMR technical third-party wording may overclaim validation strength.")
    return errors, warnings


def validate_render_package_quality_gate(
    package: Mapping[str, Any],
    *,
    report_type: str | None = None,
) -> dict[str, Any]:  # override report_client_polish_v1
    result = dict(_VALIDATE_RENDER_PACKAGE_QUALITY_GATE_BEFORE_CLIENT_POLISH_V1(package, report_type=report_type))
    rt = report_type or _clean(package.get("report_type_id"))
    errors = list(result.get("errors") or [])
    warnings = list(result.get("warnings") or [])
    extra_errors, extra_warnings = _check_report_client_polish_v1(package, rt)
    errors.extend(extra_errors)
    warnings.extend(extra_warnings)
    result["errors"] = errors
    result["warnings"] = warnings
    result["status"] = "PASS" if not errors else "FAIL"
    result["version"] = str(result.get("version") or REPORT_RENDER_QA_GATE_VERSION) + "+client_polish_v1"
    return result
