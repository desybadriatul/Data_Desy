from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

try:
    from reporting.enrichment.spokesperson_enrichment_store import (
        load_spokesperson_results_by_ids,
        summarize_spokesperson_results,
    )
except Exception:  # pragma: no cover - keeps this adapter import-safe in partial installs
    load_spokesperson_results_by_ids = None  # type: ignore
    summarize_spokesperson_results = None  # type: ignore


ADAPTER_VERSION = "spokesperson_report_adapter_v2_campaign_safe"
UNATTRIBUTED_CAMPAIGN = None


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _candidate_id(candidate: Mapping[str, Any]) -> str:
    for key in ("canonical_post_id", "source_row_id", "id", "post_id"):
        value = candidate.get(key)
        if _clean_text(value):
            return _clean_text(value)
    return ""


def _result_id(result: Mapping[str, Any]) -> str:
    for key in ("canonical_post_id", "source_row_id", "id", "post_id"):
        value = result.get(key)
        if _clean_text(value):
            return _clean_text(value)
    return ""


def _source_campaign(candidate: Mapping[str, Any] | None = None, result: Mapping[str, Any] | None = None) -> str:
    """Campaign/tag that made the article enter the report scope.

    This is intentionally separate from `represented_campaign`.
    Example: an article can be in campaign "Aqua" because it mentions aqua farming,
    while a spokesperson inside it represents no beverage brand.
    """

    candidates = []
    if candidate:
        candidates.append(candidate)
    if result:
        meta = result.get("candidate_metadata")
        if isinstance(meta, Mapping):
            candidates.append(meta)

    for item in candidates:
        for key in (
            "source_campaign",
            "campaign_scope",
            "campaign",
            "brand",
            "requested_campaign",
            "_cogan_campaign_scope",
            "_cogan_requested_campaign",
        ):
            value = item.get(key)
            if _clean_text(value):
                return _clean_text(value)

        campaigns = item.get("matched_campaigns") or item.get("campaigns")
        if isinstance(campaigns, list) and campaigns:
            first = _clean_text(campaigns[0])
            if first:
                return first
        if _clean_text(campaigns):
            return _clean_text(campaigns).split(",")[0].strip()

    return "(unknown)"


def _represented_campaign(spokesperson: Mapping[str, Any]) -> str | None:
    """Return the LLM/manual represented_campaign exactly as a safe grouping field.

    Critical rule: NEVER default this to source campaign / candidate brand.
    If enrichment intentionally returned null/empty, it means the person should
    not be counted as a spokesperson for the tagged campaign.
    """

    value = _clean_text(spokesperson.get("represented_campaign"))
    return value or None


def _candidate_meta(candidate: Mapping[str, Any] | None, result: Mapping[str, Any] | None = None) -> dict[str, Any]:
    meta_from_cache = result.get("candidate_metadata") if isinstance(result, Mapping) else None
    if not candidate and isinstance(meta_from_cache, Mapping):
        candidate = meta_from_cache
    if not candidate:
        return {}

    return {
        "canonical_post_id": _candidate_id(candidate) or (_result_id(result) if isinstance(result, Mapping) else None),
        "source_campaign": _source_campaign(candidate, result),
        "date": candidate.get("date") or candidate.get("post_date") or candidate.get("published_at"),
        "channel": candidate.get("channel") or candidate.get("media_type"),
        "media_name": candidate.get("media_name") or candidate.get("author") or candidate.get("publisher"),
        "title": candidate.get("title"),
        "url": candidate.get("url"),
        "ad_value": candidate.get("ad_value"),
        "pr_value": candidate.get("pr_value"),
        "readership": candidate.get("readership"),
        "spokesperson_raw": candidate.get("spokesperson_raw"),
    }


def index_candidates(candidates: Iterable[Mapping[str, Any]] | None) -> dict[str, Mapping[str, Any]]:
    indexed: dict[str, Mapping[str, Any]] = {}
    for candidate in candidates or []:
        cid = _candidate_id(candidate)
        if cid:
            indexed[cid] = candidate
    return indexed


def normalize_cached_results(cached_results: Any) -> list[dict[str, Any]]:
    """Accept cache payload shapes and return flat result rows.

    Supported shapes:
    - {"results": [...]} / {"rows": [...]} / {"cached_results": [...]} / {"data": [...]}
    - list[dict]
    - single result dict
    - load_spokesperson_results_by_ids() shape: {canonical_post_id: [result, ...]}
    - load_cached_spokesperson_results() shape: {cache_key: result}
    """

    if not cached_results:
        return []

    if isinstance(cached_results, list):
        return [dict(item) for item in cached_results if isinstance(item, Mapping)]

    if isinstance(cached_results, Mapping):
        for key in ("results", "rows", "cached_results", "data"):
            value = cached_results.get(key)
            if isinstance(value, list):
                return [dict(item) for item in value if isinstance(item, Mapping)]

        if _result_id(cached_results):
            return [dict(cached_results)]

        flattened: list[dict[str, Any]] = []
        for value in cached_results.values():
            if isinstance(value, list):
                flattened.extend(dict(item) for item in value if isinstance(item, Mapping))
            elif isinstance(value, Mapping):
                flattened.append(dict(value))
        return flattened

    return []


def load_cached_spokesperson_results(
    candidates: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Load cache by canonical_post_id. Returns [] when store is unavailable."""

    if load_spokesperson_results_by_ids is None:
        return []

    ids = [_candidate_id(candidate) for candidate in candidates]
    ids = [item for item in ids if item]
    if not ids:
        return []

    loaded = load_spokesperson_results_by_ids(ids)  # type: ignore[misc]
    return normalize_cached_results(loaded)


def _number(value: Any) -> float:
    try:
        if value in (None, ""):
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def _brand_set(brand_universe: Iterable[str] | None) -> set[str]:
    return {_clean_text(item).casefold() for item in brand_universe or [] if _clean_text(item)}


def build_spokesperson_report_views(
    *,
    candidates: Iterable[Mapping[str, Any]] | None = None,
    cached_results: Any = None,
    brand_universe: Iterable[str] | None = None,
    load_cache: bool = True,
    top_n: int = 15,
) -> dict[str, Any]:
    """Build reusable spokesperson views for MMR/SFIR/other reports.

    Safety rules:
    - `source_campaign` = campaign/tag that selected the article.
    - `represented_campaign` = campaign the named person explicitly represents.
    - This adapter never fills missing `represented_campaign` from source campaign.
    - Top spokesperson by brand is grouped only by non-empty `represented_campaign`.
    """

    candidate_list = [dict(item) for item in candidates or []]
    candidate_by_id = index_candidates(candidate_list)

    result_rows = normalize_cached_results(cached_results)
    if not result_rows and load_cache and candidate_list:
        result_rows = load_cached_spokesperson_results(candidate_list)

    result_by_id: dict[str, dict[str, Any]] = {
        _result_id(row): row for row in result_rows if _result_id(row)
    }

    requested_ids = {_candidate_id(candidate) for candidate in candidate_list if _candidate_id(candidate)}
    cached_ids = set(result_by_id.keys())
    missing_ids = sorted(requested_ids - cached_ids)

    mentions: list[dict[str, Any]] = []
    status_counter: Counter[str] = Counter()
    source_campaign_counter: dict[str, Counter[str]] = defaultdict(Counter)
    represented_campaign_counter: dict[str, Counter[str]] = defaultdict(Counter)
    spokesperson_counter: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    off_scope_speaker_count = 0
    brands_normalized = _brand_set(brand_universe)

    for result in result_rows:
        rid = _result_id(result)
        candidate = candidate_by_id.get(rid)
        meta = _candidate_meta(candidate, result)
        source_campaign = _source_campaign(candidate, result)
        status = _clean_text(result.get("status")) or "unknown"
        source = _clean_text(result.get("source")) or "unknown"
        confidence = _clean_text(result.get("confidence")) or "unknown"

        status_counter[status] += 1
        source_campaign_counter[source_campaign]["articles_cached"] += 1
        source_campaign_counter[source_campaign][status] += 1

        speakers = [sp for sp in _as_list(result.get("spokespersons")) if isinstance(sp, Mapping)]
        if not speakers:
            mentions.append(
                {
                    **meta,
                    "source_campaign": source_campaign,
                    "brand": None,
                    "status": status,
                    "source": source,
                    "confidence": confidence,
                    "spokesperson_name": None,
                    "spokesperson_role": None,
                    "organization": None,
                    "spokesperson_type": None,
                    "represented_campaign": None,
                    "is_representing_source_campaign": False,
                    "evidence_sentence": result.get("reason") or result.get("evidence_sentence"),
                }
            )
            continue

        article_has_represented_source = False
        article_has_any_represented = False

        for sp in speakers:
            represented_campaign = _represented_campaign(sp)
            name = _clean_text(sp.get("spokesperson_name")) or _clean_text(sp.get("name"))
            role = _clean_text(sp.get("spokesperson_role")) or _clean_text(sp.get("role"))
            org = _clean_text(sp.get("organization"))
            sp_type = _clean_text(sp.get("spokesperson_type")) or "other"
            sp_confidence = _clean_text(sp.get("confidence")) or confidence
            is_representing_source = bool(
                represented_campaign
                and source_campaign
                and represented_campaign.casefold() == source_campaign.casefold()
            )

            if represented_campaign:
                article_has_any_represented = True
                represented_campaign_counter[represented_campaign]["spokesperson_mentions"] += 1
                if name:
                    represented_campaign_counter[represented_campaign]["named_spokesperson_mentions"] += 1
            else:
                off_scope_speaker_count += 1

            if is_representing_source:
                article_has_represented_source = True

            row = {
                **meta,
                "source_campaign": source_campaign,
                "brand": represented_campaign,
                "status": status,
                "source": source,
                "confidence": sp_confidence,
                "spokesperson_name": name or None,
                "spokesperson_role": role or None,
                "organization": org or None,
                "spokesperson_type": sp_type,
                "represented_campaign": represented_campaign,
                "is_representing_source_campaign": is_representing_source,
                "evidence_sentence": sp.get("evidence_sentence") or result.get("reason"),
            }
            mentions.append(row)

            # Critical: aggregate top by represented_campaign only. Do not put
            # source-campaign-only or null represented_campaign speakers into brand top list.
            if name and represented_campaign:
                if brands_normalized and represented_campaign.casefold() not in brands_normalized:
                    # Keep mention row for audit, but avoid top-by-brand pollution
                    # when report requested a specific brand universe.
                    continue
                key = (represented_campaign, name.casefold(), role.casefold(), org.casefold())
                aggregate = spokesperson_counter.setdefault(
                    key,
                    {
                        "brand": represented_campaign,
                        "represented_campaign": represented_campaign,
                        "spokesperson_name": name,
                        "spokesperson_role": role or None,
                        "organization": org or None,
                        "spokesperson_type": sp_type,
                        "article_count": 0,
                        "mention_count": 0,
                        "high_confidence_mentions": 0,
                        "total_ad_value": 0,
                        "total_pr_value": 0,
                        "example_evidence": row.get("evidence_sentence"),
                        "example_title": row.get("title"),
                        "example_url": row.get("url"),
                    },
                )
                aggregate["mention_count"] += 1
                aggregate["article_count"] += 1
                aggregate["total_ad_value"] += _number(row.get("ad_value"))
                aggregate["total_pr_value"] += _number(row.get("pr_value"))
                if sp_confidence == "high":
                    aggregate["high_confidence_mentions"] += 1

        if article_has_represented_source:
            source_campaign_counter[source_campaign]["articles_with_source_campaign_spokesperson"] += 1
        if article_has_any_represented:
            source_campaign_counter[source_campaign]["articles_with_any_represented_spokesperson"] += 1

    summary_by_source_campaign: list[dict[str, Any]] = []
    brands = list(brand_universe or [])
    for brand in sorted(set(brands) | set(source_campaign_counter.keys())):
        counter = source_campaign_counter.get(brand, Counter())
        represented = represented_campaign_counter.get(brand, Counter())
        summary_by_source_campaign.append(
            {
                "source_campaign": brand,
                "brand": brand,
                "articles_cached": int(counter.get("articles_cached", 0)),
                "relevant_articles": int(counter.get("relevant", 0)),
                "not_relevant_articles": int(counter.get("not_relevant", 0)),
                "review_needed_articles": int(counter.get("review_needed", 0)),
                "articles_with_source_campaign_spokesperson": int(counter.get("articles_with_source_campaign_spokesperson", 0)),
                "articles_with_any_represented_spokesperson": int(counter.get("articles_with_any_represented_spokesperson", 0)),
                "represented_campaign_mentions": int(represented.get("spokesperson_mentions", 0)),
                "named_spokesperson_mentions": int(represented.get("named_spokesperson_mentions", 0)),
            }
        )

    top_spokespersons = sorted(
        spokesperson_counter.values(),
        key=lambda item: (
            item.get("mention_count", 0),
            item.get("high_confidence_mentions", 0),
            item.get("total_ad_value", 0),
        ),
        reverse=True,
    )[: max(1, int(top_n))]

    unattributed_named_speaker_count = sum(
        1 for row in mentions if row.get("spokesperson_name") and not row.get("represented_campaign")
    )

    readiness = {
        "adapter_version": ADAPTER_VERSION,
        "selected_candidate_count": len(candidate_list),
        "cached_article_count": len(result_rows),
        "missing_candidate_count": len(missing_ids),
        "missing_candidate_ids": missing_ids[:100],
        "status_counts": dict(status_counter),
        "unattributed_named_speaker_count": unattributed_named_speaker_count,
        "off_scope_or_unrepresented_speaker_count": off_scope_speaker_count,
        "ready_for_report": len(missing_ids) == 0 if candidate_list else bool(result_rows),
        "note": (
            "Spokesperson views are cache-derived. represented_campaign is never inferred from source_campaign. "
            "Rows with represented_campaign=null are audit/limitation rows, not brand spokespersons."
        ),
    }

    if summarize_spokesperson_results is not None:
        try:
            readiness["cache_summary"] = summarize_spokesperson_results(result_rows)  # type: ignore[misc]
        except Exception:
            pass

    return {
        "adapter_version": ADAPTER_VERSION,
        "spokesperson_readiness": readiness,
        "quantitative_views": {
            "qt_spokesperson_summary_by_brand": {
                "view_id": "qt_spokesperson_summary_by_brand",
                "rows": summary_by_source_campaign,
                "metadata": {
                    "source": "spokesperson_enrichment_cache",
                    "grouping": "source_campaign with represented_campaign safety counts",
                },
            }
        },
        "qualitative_views": {
            "ql_spokesperson_mentions": {
                "view_id": "ql_spokesperson_mentions",
                "rows": mentions,
                "metadata": {
                    "source": "spokesperson_enrichment_cache",
                    "represented_campaign_policy": "preserve_null_do_not_infer_from_source_campaign",
                },
            },
            "ql_top_spokespersons_by_brand": {
                "view_id": "ql_top_spokespersons_by_brand",
                "rows": top_spokespersons,
                "metadata": {
                    "source": "spokesperson_enrichment_cache",
                    "grouping": "represented_campaign_only",
                    "excludes": "null represented_campaign and out-of-brand-universe speakers",
                },
            },
        },
    }


def attach_spokesperson_views(
    report_input: dict[str, Any],
    *,
    candidates: Iterable[Mapping[str, Any]] | None = None,
    cached_results: Any = None,
    brand_universe: Iterable[str] | None = None,
    load_cache: bool = True,
) -> dict[str, Any]:
    """Attach spokesperson cache views into a Task 1 report_input dict."""

    views = build_spokesperson_report_views(
        candidates=candidates,
        cached_results=cached_results,
        brand_universe=brand_universe,
        load_cache=load_cache,
    )

    report_input.setdefault("metric_readiness", {})["spokesperson_enrichment"] = views["spokesperson_readiness"]
    report_input.setdefault("quantitative_views", {}).update(views["quantitative_views"])
    report_input.setdefault("qualitative_views", {}).update(views["qualitative_views"])
    report_input.setdefault("scope", {}).setdefault("spokesperson_policy", {})
    report_input["scope"]["spokesperson_policy"].update(
        {
            "adapter_version": ADAPTER_VERSION,
            "source": "spokesperson_enrichment_cache",
            "online_media_print_only": True,
            "represented_campaign_policy": "never_infer_from_source_campaign",
        }
    )
    return report_input


__all__ = [
    "ADAPTER_VERSION",
    "build_spokesperson_report_views",
    "attach_spokesperson_views",
    "load_cached_spokesperson_results",
    "normalize_cached_results",
]
