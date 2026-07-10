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


ADAPTER_VERSION = "spokesperson_report_adapter_v1"


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


def _candidate_brand(candidate: Mapping[str, Any]) -> str:
    for key in ("brand", "campaign", "campaign_scope", "represented_campaign"):
        value = candidate.get(key)
        if _clean_text(value):
            return _clean_text(value)

    campaigns = candidate.get("matched_campaigns") or candidate.get("campaigns")
    if isinstance(campaigns, list) and campaigns:
        return _clean_text(campaigns[0])
    if _clean_text(campaigns):
        return _clean_text(campaigns).split(",")[0].strip()
    return "(unknown)"


def _result_brand(result: Mapping[str, Any], candidate: Mapping[str, Any] | None = None) -> str:
    for sp in _as_list(result.get("spokespersons")):
        if isinstance(sp, Mapping) and _clean_text(sp.get("represented_campaign")):
            return _clean_text(sp.get("represented_campaign"))
    if candidate:
        return _candidate_brand(candidate)
    return "(unknown)"


def _candidate_meta(candidate: Mapping[str, Any] | None) -> dict[str, Any]:
    if not candidate:
        return {}
    return {
        "canonical_post_id": _candidate_id(candidate),
        "brand": _candidate_brand(candidate),
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
    """Accept multiple cache payload shapes and return result rows."""

    if not cached_results:
        return []

    if isinstance(cached_results, Mapping):
        for key in ("results", "rows", "cached_results", "data"):
            value = cached_results.get(key)
            if isinstance(value, list):
                return [dict(item) for item in value if isinstance(item, Mapping)]
        if _result_id(cached_results):
            return [dict(cached_results)]
        return []

    if isinstance(cached_results, list):
        return [dict(item) for item in cached_results if isinstance(item, Mapping)]

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


def build_spokesperson_report_views(
    *,
    candidates: Iterable[Mapping[str, Any]] | None = None,
    cached_results: Any = None,
    brand_universe: Iterable[str] | None = None,
    load_cache: bool = True,
    top_n: int = 15,
) -> dict[str, Any]:
    """Build reusable spokesperson views for MMR/SFIR/other reports.

    This adapter does not call an LLM. It only converts existing cache results
    into report-ready quantitative and qualitative views.
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
    brand_counter: dict[str, Counter[str]] = defaultdict(Counter)
    spokesperson_counter: dict[tuple[str, str, str, str], dict[str, Any]] = {}

    for result in result_rows:
        rid = _result_id(result)
        candidate = candidate_by_id.get(rid)
        meta = _candidate_meta(candidate)
        status = _clean_text(result.get("status")) or "unknown"
        source = _clean_text(result.get("source")) or "unknown"
        confidence = _clean_text(result.get("confidence")) or "unknown"
        brand = _result_brand(result, candidate)

        status_counter[status] += 1
        brand_counter[brand][status] += 1
        brand_counter[brand]["articles_cached"] += 1

        speakers = [sp for sp in _as_list(result.get("spokespersons")) if isinstance(sp, Mapping)]
        if not speakers:
            mentions.append(
                {
                    **meta,
                    "brand": brand,
                    "status": status,
                    "source": source,
                    "confidence": confidence,
                    "spokesperson_name": None,
                    "spokesperson_role": None,
                    "organization": None,
                    "spokesperson_type": None,
                    "represented_campaign": brand,
                    "evidence_sentence": result.get("reason") or result.get("evidence_sentence"),
                }
            )
            continue

        for sp in speakers:
            represented_campaign = _clean_text(sp.get("represented_campaign")) or brand
            name = _clean_text(sp.get("spokesperson_name")) or _clean_text(sp.get("name"))
            role = _clean_text(sp.get("spokesperson_role")) or _clean_text(sp.get("role"))
            org = _clean_text(sp.get("organization"))
            sp_type = _clean_text(sp.get("spokesperson_type")) or "other"
            sp_confidence = _clean_text(sp.get("confidence")) or confidence

            row = {
                **meta,
                "brand": represented_campaign,
                "status": status,
                "source": source,
                "confidence": sp_confidence,
                "spokesperson_name": name or None,
                "spokesperson_role": role or None,
                "organization": org or None,
                "spokesperson_type": sp_type,
                "represented_campaign": represented_campaign,
                "evidence_sentence": sp.get("evidence_sentence") or result.get("reason"),
            }
            mentions.append(row)

            if name:
                key = (represented_campaign, name.casefold(), role.casefold(), org.casefold())
                aggregate = spokesperson_counter.setdefault(
                    key,
                    {
                        "brand": represented_campaign,
                        "spokesperson_name": name,
                        "spokesperson_role": role or None,
                        "organization": org or None,
                        "spokesperson_type": sp_type,
                        "article_count": 0,
                        "mention_count": 0,
                        "high_confidence_mentions": 0,
                        "example_evidence": row.get("evidence_sentence"),
                        "example_title": row.get("title"),
                        "example_url": row.get("url"),
                    },
                )
                aggregate["mention_count"] += 1
                aggregate["article_count"] += 1
                if sp_confidence == "high":
                    aggregate["high_confidence_mentions"] += 1

    summary_by_brand: list[dict[str, Any]] = []
    brands = list(brand_universe or [])
    for brand in sorted(set(brands) | set(brand_counter.keys())):
        counter = brand_counter.get(brand, Counter())
        summary_by_brand.append(
            {
                "brand": brand,
                "articles_cached": int(counter.get("articles_cached", 0)),
                "relevant_articles": int(counter.get("relevant", 0)),
                "not_relevant_articles": int(counter.get("not_relevant", 0)),
                "review_needed_articles": int(counter.get("review_needed", 0)),
                "spokesperson_mentions": sum(1 for row in mentions if row.get("brand") == brand and row.get("spokesperson_name")),
            }
        )

    top_spokespersons = sorted(
        spokesperson_counter.values(),
        key=lambda item: (item.get("mention_count", 0), item.get("high_confidence_mentions", 0)),
        reverse=True,
    )[: max(1, int(top_n))]

    readiness = {
        "adapter_version": ADAPTER_VERSION,
        "selected_candidate_count": len(candidate_list),
        "cached_article_count": len(result_rows),
        "missing_candidate_count": len(missing_ids),
        "missing_candidate_ids": missing_ids[:100],
        "status_counts": dict(status_counter),
        "ready_for_report": len(missing_ids) == 0 if candidate_list else bool(result_rows),
        "note": (
            "Spokesperson views are cache-derived. Run spokesperson enrichment first when missing_candidate_count > 0."
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
                "rows": summary_by_brand,
                "metadata": {"source": "spokesperson_enrichment_cache"},
            }
        },
        "qualitative_views": {
            "ql_spokesperson_mentions": {
                "view_id": "ql_spokesperson_mentions",
                "rows": mentions,
                "metadata": {"source": "spokesperson_enrichment_cache"},
            },
            "ql_top_spokespersons_by_brand": {
                "view_id": "ql_top_spokespersons_by_brand",
                "rows": top_spokespersons,
                "metadata": {"source": "spokesperson_enrichment_cache"},
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
        }
    )
    return report_input


__all__ = [
    "ADAPTER_VERSION",
    "build_spokesperson_report_views",
    "attach_spokesperson_views",
    "load_cached_spokesperson_results",
]
