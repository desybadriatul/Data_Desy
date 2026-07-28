"""Global deterministic relevance/noise gate for Cogan report inputs.

This module is intentionally conservative: it removes rows that are clearly not
about the requested brand/campaign before KPI, SOV/SOE, sentiment, topic, and
final report evidence are computed. Ambiguous cases are preserved in a review
pool instead of being silently counted as clean data.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Mapping
from copy import deepcopy
from typing import Any


DEFAULT_TEXT_FIELDS = (
    "title", "Title", "headline", "Headline", "judul", "Judul",
    "content", "Content", "caption", "Caption", "body", "Body", "text", "Text",
    "snippet", "Snippet", "author", "Author", "username", "Username",
    "media_name", "Media Name", "source", "Source", "publisher", "Publisher",
)

# Terms that often create false positives when used as campaign names/keywords.
AMBIGUOUS_BRANDS: dict[str, set[str]] = {
    "bluebird": {"bluebird", "blue bird"},
    "blue bird": {"bluebird", "blue bird"},
    "aqua": {"aqua"},
    "pristine": {"pristine"},
    "club": {"club"},
    "apple": {"apple"},
    "orange": {"orange"},
    "target": {"target"},
}

# High precision negative context rules. Keep these deterministic and explainable.
NOISE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("bluebird_plant_or_bird", r"\b(blue\s*bird|bluebird)\b.{0,80}\b(keladi|tanaman|plant|flower|burung|bird|aves|ornamental|hias)\b|\b(keladi|tanaman|plant|flower|burung|bird|ornamental|hias)\b.{0,80}\b(blue\s*bird|bluebird)\b"),
    ("aqua_non_brand_context", r"\b(aqua\s*farming|aquafarming|aqua\s*scap(?:e|ing)|aquascap(?:e|ing)|aquarium|aquatic|aquaculture|aqua\s*culture|aqua\s*park|aqua\s*aerobic|aqua\s*zumba|aqua\s*fitness)\b"),
    ("pristine_generic_adjective", r"\bpristine\b.{0,60}\b(beach|condition|nature|forest|waterfall|lake|river|view|environment|landscape|coast|island|mountain|clean|untouched|wilderness|beauty|snow)\b|\b(beach|condition|nature|forest|waterfall|lake|river|view|environment|landscape|coast|island|mountain|clean|untouched|wilderness|beauty|snow)\b.{0,60}\bpristine\b"),
    ("club_generic_context", r"\b(football|soccer|golf|night|fan|supporters?|members?|motor|book|dance|country|social)\s+club\b|\bclub\s+(football|soccer|golf|night|fan|supporters?|members?|motor|book|dance|country|social)\b"),
    ("apple_food_context", r"\bapple\b.{0,40}\b(fruit|pie|juice|cake|cider|orchard|tree|buah|apel)\b|\b(fruit|pie|juice|cake|cider|orchard|tree|buah|apel)\b.{0,40}\bapple\b"),
    ("orange_generic_context", r"\borange\b.{0,40}\b(fruit|juice|color|colour|jeruk|warna)\b|\b(fruit|juice|color|colour|jeruk|warna)\b.{0,40}\borange\b"),
)

RESALE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("fleet_resale_ex_armada", r"\b(ex\s*(?:armada|fleet|taxi|taksi)|eks\s*(?:armada|taxi|taksi)|bekas\s*(?:taksi|taxi|armada)|transmover|jual\s+mobil\s+bekas|mobil\s+bekas)\b"),
)

OFFICIAL_HINT_PATTERNS = (
    r"@?bluebird(group|id)?\b",
    r"@?sehataqua\b",
    r"@?le\s*minerale\b",
    r"@?aqua\b",
)


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def _casefold_text(value: Any) -> str:
    return normalize_text(value).casefold()


def _iter_terms(value: Any) -> Iterable[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw = re.split(r"[,;|\n]+", value)
        return [item.strip() for item in raw if item.strip()]
    if isinstance(value, Mapping):
        return [str(v).strip() for v in value.values() if str(v).strip()]
    if isinstance(value, Iterable) and not isinstance(value, (bytes, str)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _brand_aliases(brand: str) -> set[str]:
    clean = normalize_text(brand)
    if not clean:
        return set()
    aliases = {clean, clean.replace(" ", ""), clean.replace("-", " ")}
    key = clean.casefold()
    aliases |= AMBIGUOUS_BRANDS.get(key, set())

    compact = normalize_key(clean)
    if compact == "bluebird":
        aliases |= {"bluebird", "blue bird", "bluebird group", "mybluebird", "silver bird", "silverbird", "golden bird", "goldenbird"}
    elif compact == "aqua":
        aliases |= {"aqua", "sehataqua", "sehat aqua", "aqua dulu", "#aquadulu"}
    elif compact == "leminerale":
        aliases |= {"le minerale", "leminerale", "le mineral", "le mineral"}
    elif compact == "aquviva":
        aliases |= {"aquviva", "aquaviva"}
    elif compact == "nestlepurelife":
        aliases |= {"nestle pure life", "nestlé pure life", "pure life"}
    return {normalize_text(item).casefold() for item in aliases if normalize_text(item)}


def _collect_brand_universe(
    *,
    project_name: str,
    client_brand: str | None = None,
    brand_universe: Iterable[str] | None = None,
    scope: Mapping[str, Any] | None = None,
) -> list[str]:
    raw: list[str] = []
    raw.extend(_iter_terms(project_name))
    raw.extend(_iter_terms(client_brand))
    raw.extend(_iter_terms(brand_universe))
    scope = scope or {}
    for key in ("brand", "brands", "client_brand", "brand_universe", "competitor_brands", "competitors", "campaigns"):
        raw.extend(_iter_terms(scope.get(key)))

    result: list[str] = []
    seen: set[str] = set()
    for item in raw:
        text = normalize_text(item)
        if not text:
            continue
        key = normalize_key(text)
        if key not in seen:
            result.append(text)
            seen.add(key)
    return result


def _combined_text(row: Mapping[str, Any], text_fields: Iterable[str] = DEFAULT_TEXT_FIELDS) -> str:
    parts: list[str] = []
    for field in text_fields:
        value = row.get(field)
        if value is not None and str(value).strip():
            parts.append(str(value))
    # Include shallow nested raw payload metadata without being too expensive.
    for nested_key in ("raw", "raw_data", "payload", "metadata"):
        nested = row.get(nested_key)
        if isinstance(nested, Mapping):
            for key in DEFAULT_TEXT_FIELDS:
                value = nested.get(key)
                if value is not None and str(value).strip():
                    parts.append(str(value))
    return _casefold_text(" \n ".join(parts))


def _matched_aliases(text: str, aliases: Iterable[str]) -> list[str]:
    matches: list[str] = []
    for alias in sorted(set(aliases), key=len, reverse=True):
        if not alias:
            continue
        pattern = r"(?<![a-z0-9])" + re.escape(alias.casefold()) + r"(?![a-z0-9])"
        if re.search(pattern, text):
            matches.append(alias)
    return matches


def _is_ambiguous_brand(brand: str) -> bool:
    compact = normalize_key(brand)
    if compact in {"bluebird", "aqua", "pristine", "club", "apple", "orange", "target"}:
        return True
    return _casefold_text(brand) in AMBIGUOUS_BRANDS


def _scope_allows_resale(scope: Mapping[str, Any] | None, analysis_objective: str | None) -> bool:
    scope = scope or {}
    if bool(scope.get("include_resale_market")):
        return True
    haystack = _casefold_text(" ".join(_iter_terms(analysis_objective)) + " " + " ".join(_iter_terms(scope.get("keywords"))))
    return bool(re.search(r"\b(resale|jual\s+mobil|mobil\s+bekas|fleet|eks\s+armada|ex\s+fleet)\b", haystack))


def classify_row_relevance(
    row: Mapping[str, Any],
    *,
    project_name: str,
    report_type_id: str,
    client_brand: str | None = None,
    brand_universe: Iterable[str] | None = None,
    scope: Mapping[str, Any] | None = None,
    analysis_objective: str | None = None,
    row_brand_field: str = "brand",
    text_fields: Iterable[str] = DEFAULT_TEXT_FIELDS,
) -> dict[str, Any]:
    """Return deterministic relevance status for one row."""
    scope = scope or {}
    text = _combined_text(row, text_fields)
    brands = _collect_brand_universe(
        project_name=project_name,
        client_brand=client_brand,
        brand_universe=brand_universe,
        scope=scope,
    )
    row_brand = normalize_text(row.get(row_brand_field))
    if row_brand:
        brands = _collect_brand_universe(
            project_name=project_name,
            client_brand=client_brand,
            brand_universe=[*brands, row_brand],
            scope=scope,
        )

    for noise_type, pattern in NOISE_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return {
                "status": "excluded",
                "is_relevant": False,
                "confidence": "high",
                "noise_type": noise_type,
                "reason": f"Deterministic non-brand context matched: {noise_type}.",
                "matched_brand": row_brand or None,
                "matched_aliases": [],
            }

    if not _scope_allows_resale(scope, analysis_objective):
        for noise_type, pattern in RESALE_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return {
                    "status": "excluded",
                    "is_relevant": False,
                    "confidence": "medium",
                    "noise_type": noise_type,
                    "reason": "Fleet/resale marketplace content is excluded by default unless the report scope explicitly asks for resale/fleet market analysis.",
                    "matched_brand": row_brand or None,
                    "matched_aliases": [],
                }

    aliases_by_brand = {brand: _brand_aliases(brand) for brand in brands}
    matched: dict[str, list[str]] = {
        brand: _matched_aliases(text, aliases)
        for brand, aliases in aliases_by_brand.items()
        if aliases
    }
    matched = {brand: vals for brand, vals in matched.items() if vals}

    if matched:
        best_brand = row_brand or max(matched, key=lambda brand: len(" ".join(matched[brand])))
        return {
            "status": "clean",
            "is_relevant": True,
            "confidence": "high",
            "noise_type": None,
            "reason": "Brand/campaign alias found in title/content/author/source fields.",
            "matched_brand": best_brand,
            "matched_aliases": matched.get(best_brand) or next(iter(matched.values())),
        }

    ambiguous_campaign = any(_is_ambiguous_brand(brand) for brand in brands if brand)
    official_hint = any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in OFFICIAL_HINT_PATTERNS)
    if official_hint:
        return {
            "status": "clean",
            "is_relevant": True,
            "confidence": "medium",
            "noise_type": None,
            "reason": "Official account/source hint matched even though text lacks a plain brand alias.",
            "matched_brand": row_brand or None,
            "matched_aliases": [],
        }

    campaign_scope = normalize_text(row.get("_cogan_campaign_scope") or row.get("_cogan_requested_campaign") or row.get("Campaign"))
    if campaign_scope and not ambiguous_campaign:
        return {
            "status": "clean",
            "is_relevant": True,
            "confidence": "medium",
            "noise_type": None,
            "reason": "Campaign membership retained for non-ambiguous campaign scope.",
            "matched_brand": row_brand or campaign_scope,
            "matched_aliases": [],
        }

    if campaign_scope and ambiguous_campaign:
        return {
            "status": "excluded",
            "is_relevant": False,
            "confidence": "medium",
            "noise_type": "missing_brand_mention_for_ambiguous_campaign",
            "reason": "Ambiguous campaign/brand term has no explicit brand/account alias in the row text; likely campaign-tag noise.",
            "matched_brand": row_brand or campaign_scope,
            "matched_aliases": [],
        }

    return {
        "status": "review",
        "is_relevant": None,
        "confidence": "low",
        "noise_type": "unverified_relevance",
        "reason": "No deterministic brand alias or high-confidence noise rule matched.",
        "matched_brand": row_brand or None,
        "matched_aliases": [],
    }


def apply_global_relevance_filter(
    rows: Iterable[Mapping[str, Any]],
    *,
    project_name: str,
    report_type_id: str,
    client_brand: str | None = None,
    brand_universe: Iterable[str] | None = None,
    scope: Mapping[str, Any] | None = None,
    analysis_objective: str | None = None,
    row_brand_field: str = "brand",
    keep_review_rows: bool = True,
) -> dict[str, Any]:
    """Split rows into clean/excluded/review pools and annotate every row."""
    clean_rows: list[dict[str, Any]] = []
    excluded_rows: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []
    reasons = Counter()

    raw_rows = [dict(row) for row in rows]
    for row in raw_rows:
        result = classify_row_relevance(
            row,
            project_name=project_name,
            report_type_id=report_type_id,
            client_brand=client_brand,
            brand_universe=brand_universe,
            scope=scope,
            analysis_objective=analysis_objective,
            row_brand_field=row_brand_field,
        )
        annotated = deepcopy(row)
        annotated["_cogan_relevance"] = result
        annotated["is_relevant"] = result["is_relevant"]
        annotated["relevance_confidence"] = result["confidence"]
        annotated["noise_type"] = result["noise_type"]
        annotated["noise_reason"] = result["reason"]
        if result["status"] == "clean":
            clean_rows.append(annotated)
        elif result["status"] == "excluded":
            excluded_rows.append(annotated)
            reasons[str(result.get("noise_type") or "excluded")] += 1
        else:
            review_rows.append(annotated)
            reasons[str(result.get("noise_type") or "review")] += 1
            if keep_review_rows:
                clean_rows.append(annotated)

    raw_count = len(raw_rows)
    excluded_count = len(excluded_rows)
    review_count = len(review_rows)
    summary = {
        "status": "READY_WITH_RELEVANCE_FILTER" if (excluded_count or review_count) else "READY",
        "policy": "Global deterministic relevance/noise gate runs before report metrics and evidence views.",
        "report_type_id": report_type_id,
        "raw_count": raw_count,
        "clean_count": len(clean_rows),
        "excluded_count": excluded_count,
        "review_count": review_count,
        "excluded_rate_pct": round(excluded_count * 100 / raw_count, 1) if raw_count else 0,
        "review_rate_pct": round(review_count * 100 / raw_count, 1) if raw_count else 0,
        "keep_review_rows": bool(keep_review_rows),
        "excluded_by_type": dict(reasons),
        "hard_fail_recommended": bool(raw_count and excluded_count * 100 / raw_count >= 60),
    }
    return {
        "clean_rows": clean_rows,
        "excluded_rows": excluded_rows,
        "review_rows": review_rows,
        "summary": summary,
    }


def compact_exclusion_examples(excluded_rows: Iterable[Mapping[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for row in excluded_rows:
        rel = row.get("_cogan_relevance") or {}
        examples.append(
            {
                "noise_type": rel.get("noise_type") or row.get("noise_type"),
                "reason": rel.get("reason") or row.get("noise_reason"),
                "title": normalize_text(row.get("title") or row.get("Title") or row.get("headline") or row.get("Headline"))[:160],
                "content_snippet": normalize_text(row.get("content") or row.get("Content") or row.get("caption") or row.get("Caption"))[:220],
                "source_url": row.get("source_url") or row.get("url") or row.get("URL") or row.get("Link URL"),
            }
        )
        if len(examples) >= limit:
            break
    return examples


__all__ = [
    "apply_global_relevance_filter",
    "classify_row_relevance",
    "compact_exclusion_examples",
    "normalize_text",
]
