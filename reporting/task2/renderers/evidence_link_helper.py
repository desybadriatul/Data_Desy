"""Client-facing evidence link helpers for report render packages.

These helpers keep audit identifiers and full URLs available for data packs while
making PPT-facing evidence natural to read: "Buka artikel" for mainstream media,
"Lihat post" for social posts, and "Lihat komentar" for comment deep-links.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

RAW_URL_FIELD_NAMES = {
    "source_url",
    "top_article_url",
    "article_url",
    "url",
    "link_url",
    "full_url",
    "display_url",
    "evidence_urls",
}

AUDIT_ID_FIELD_NAMES = {
    "evidence_id",
    "original_evidence_id",
    "audit_evidence_id",
    "audit_label",
    "evidence_ref",
    "evidence_refs",
}

INTERNAL_TEXT_PATTERNS = (
    "evidence id",
    "url lengkap",
    "full url",
    "raw url",
    "appendix url",
    "main deck memakai",
    "raw topic extraction",
    "classification coverage",
    "issue coverage baru",
    "do not place raw urls",
    "source_url",
    "evidence_registry",
    "data pack",
)

SOCIAL_CHANNELS = {
    "instagram",
    "ig",
    "tiktok",
    "twitter",
    "x",
    "facebook",
    "fb",
    "youtube",
    "yt",
    "threads",
}

ARTICLE_CHANNELS = {
    "online media",
    "online",
    "printmedia",
    "printed media",
    "print media",
    "print",
    "media online",
    "portal berita",
}

COMMENT_URL_MARKERS = ("commentid=", "/comment/", "reply", "comment")


def clean_text(value: Any, limit: int | None = None) -> str:
    text = " ".join(str(value or "").strip().split())
    if limit and len(text) > limit:
        return text[: max(0, limit - 1)].rstrip() + "…"
    return text


def first_url(row: Mapping[str, Any]) -> str | None:
    for key in ("source_url", "top_article_url", "article_url", "url", "link_url", "full_url", "display_url"):
        value = row.get(key)
        if value:
            return str(value).strip()
    link = row.get("evidence_link")
    if isinstance(link, Mapping) and link.get("url"):
        return str(link.get("url")).strip()
    return None


def channel_kind(row: Mapping[str, Any]) -> str:
    url = (first_url(row) or "").casefold()
    channel = clean_text(row.get("channel") or row.get("media_type") or row.get("source") or row.get("platform")).casefold()
    if any(marker in url for marker in COMMENT_URL_MARKERS):
        return "comment"
    if channel in ARTICLE_CHANNELS or "news" in channel or "media" in channel:
        return "article"
    if channel in SOCIAL_CHANNELS:
        return "social"
    if any(domain in url for domain in ("tiktok.com", "instagram.com", "twitter.com", "x.com", "facebook.com", "youtube.com", "youtu.be", "threads.net")):
        return "social"
    if url:
        return "link"
    return "missing"


def evidence_cta_label(row: Mapping[str, Any]) -> str:
    kind = channel_kind(row)
    if kind == "article":
        return "Buka artikel ↗"
    if kind == "comment":
        return "Lihat komentar ↗"
    if kind == "social":
        return "Lihat post ↗"
    if kind == "link":
        return "Buka link ↗"
    return "Link tidak tersedia"


def evidence_link(row: Mapping[str, Any]) -> dict[str, Any] | None:
    url = first_url(row)
    if not url:
        return None
    return {"label": evidence_cta_label(row), "url": url}


def client_evidence_card(row: Mapping[str, Any], *, text_limit: int = 150, include_metric: bool = True) -> dict[str, Any]:
    """Return a PPT-facing evidence card with natural CTA and no visible audit ID/raw URL."""
    link = evidence_link(row)
    card: dict[str, Any] = {
        "title": clean_text(row.get("title") or row.get("top_article_title") or row.get("content"), text_limit),
        "media_name": clean_text(row.get("media_name") or row.get("top_article_media") or row.get("author") or row.get("source"), 80),
        "channel": clean_text(row.get("channel") or row.get("media_type"), 60),
        "sentiment": clean_text(row.get("sentiment") or row.get("dominant_sentiment"), 40),
        "topic": clean_text(row.get("issue_label") or row.get("topic") or row.get("top_issue") or row.get("topic_extraction"), 90),
        "snippet": clean_text(row.get("content_snippet") or row.get("snippet") or row.get("content"), 220),
        "evidence_link": link,
        "link_label": (link or {}).get("label") or "Link tidak tersedia",
    }
    if include_metric:
        for key in ("engagement", "interactions", "pr_value", "ad_value", "article_count", "count_content"):
            if row.get(key) is not None:
                card[key] = row.get(key)
    return {k: v for k, v in card.items() if v not in (None, "", [])}


def strip_client_visible_audit(value: Any, *, keep_evidence_link_url: bool = True) -> Any:
    """Remove raw URL/audit fields from client-facing slide payloads.

    `evidence_link.url` is preserved because renderers need it to create a
    hyperlink behind natural text. Raw URLs outside evidence_link are removed.
    """
    if isinstance(value, list):
        return [strip_client_visible_audit(item, keep_evidence_link_url=keep_evidence_link_url) for item in value]
    if isinstance(value, tuple):
        return tuple(strip_client_visible_audit(item, keep_evidence_link_url=keep_evidence_link_url) for item in value)
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, child in value.items():
            key_s = str(key)
            if key_s in AUDIT_ID_FIELD_NAMES:
                continue
            if key_s in RAW_URL_FIELD_NAMES:
                continue
            if key_s in {"must_show_url", "must_show_evidence_url", "requires_url_in_ppt"}:
                out[key_s] = False
                continue
            if key_s == "evidence_link" and isinstance(child, Mapping):
                label = clean_text(child.get("label")) or "Buka link ↗"
                url = clean_text(child.get("url"))
                out[key_s] = {"label": label, "url": url} if keep_evidence_link_url and url else {"label": label}
                continue
            out[key_s] = strip_client_visible_audit(child, keep_evidence_link_url=keep_evidence_link_url)
        return out
    return value


def contains_internal_wording(text: Any) -> bool:
    value = clean_text(text).casefold()
    return any(pattern in value for pattern in INTERNAL_TEXT_PATTERNS)


def _walk(value: Any):
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def validate_client_facing_presentation_package(package: Mapping[str, Any], *, report_type: str) -> dict[str, Any]:
    """Lightweight render-package QA for client-facing PPT payloads."""
    errors: list[str] = []
    warnings: list[str] = []
    slides = package.get("slides") or []
    if not isinstance(slides, list) or not slides:
        errors.append("Package has no slides.")
    visible_text_parts: list[str] = []
    raw_url_outside_evidence_link = 0
    audit_id_field_count = 0
    natural_link_count = 0

    for slide in slides if isinstance(slides, list) else []:
        for node in _walk(slide):
            is_evidence_link_node = set(node.keys()).issubset({"label", "url"}) and "url" in node and "label" in node
            for key, value in node.items():
                key_s = str(key)
                if key_s in AUDIT_ID_FIELD_NAMES:
                    audit_id_field_count += 1
                if key_s in RAW_URL_FIELD_NAMES and not is_evidence_link_node:
                    raw_url_outside_evidence_link += 1
                if key_s == "evidence_link" and isinstance(value, Mapping):
                    label = clean_text(value.get("label"))
                    url = clean_text(value.get("url"))
                    if label in {"Buka artikel ↗", "Lihat post ↗", "Lihat komentar ↗", "Buka link ↗"} and url:
                        natural_link_count += 1
                elif isinstance(value, str) and not (is_evidence_link_node and key_s == "url"):
                    visible_text_parts.append(value)

    visible_text = "\n".join(visible_text_parts)
    lower_visible = visible_text.casefold()
    if raw_url_outside_evidence_link:
        errors.append(f"Found {raw_url_outside_evidence_link} raw URL field(s) outside evidence_link in slides.")
    if audit_id_field_count:
        errors.append(f"Found {audit_id_field_count} audit/evidence ID field(s) in client-facing slides.")
    if any(token in lower_visible for token in ("http://", "https://", "www.")):
        errors.append("Visible slide text contains raw URL string.")
    if any(pattern in lower_visible for pattern in INTERNAL_TEXT_PATTERNS):
        errors.append("Visible slide text contains internal/debug wording.")
    if natural_link_count == 0:
        warnings.append("No natural evidence hyperlinks found in slide payload.")

    sections = [clean_text((slide or {}).get("section")) for slide in slides if isinstance(slide, Mapping)]
    if report_type == "competitive_analysis":
        expected_first = ["Header / Report Identity", "Executive Summary", "Competitive Action Plan"]
        if sections[:3] != expected_first:
            errors.append(f"Competitive Analysis first sections must be {expected_first}; got {sections[:3]}.")
    if report_type == "mainstream_media_report":
        expected_first = ["Header", "Executive Summary", "Media Response Action Plan"]
        normalized = ["Header" if sec.startswith("Header") else sec for sec in sections[:3]]
        if normalized != expected_first:
            errors.append(f"MMR first sections must be {expected_first}; got {sections[:3]}.")

    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "natural_link_count": natural_link_count,
        "slide_count": len(slides) if isinstance(slides, list) else 0,
    }
