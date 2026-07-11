from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from psycopg.rows import dict_row

from reporting.enrichment.topic_batch_builder import _normalise_post
from reporting.enrichment.spokesperson_enrichment import (
    build_spokesperson_enrichment_candidates,
)
from reporting.enrichment.spokesperson_llm_contract import (
    build_spokesperson_extraction_prompt,
    validate_spokesperson_batch_response,
)
from reporting.enrichment.spokesperson_enrichment_store import (
    ensure_spokesperson_enrichment_store,
    save_spokesperson_enrichment_results,
    split_cached_and_missing_candidates,
    summarize_spokesperson_results,
)


WORKFLOW_VERSION = "spokesperson_enrichment_workflow_v2"
DEFAULT_LLM_BATCH_SIZE = 20


class SpokespersonEnrichmentWorkflowError(RuntimeError):
    """Raised when spokesperson enrichment workflow preparation fails."""


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _get_pool() -> Any:
    """Load the PostgreSQL pool used by the Cogan app."""

    try:
        from database.db import get_pool  # type: ignore

        return get_pool()
    except Exception:
        try:
            from database import db  # type: ignore

            return db.get_pool()
        except Exception as exc:  # noqa: BLE001
            raise SpokespersonEnrichmentWorkflowError(
                "Tidak bisa memuat database pool. Pastikan DATABASE_URL sudah tersedia."
            ) from exc


def normalize_campaign_universe(
    client_brand: str | None = None,
    competitors: Iterable[str] | None = None,
    campaign_universe: Iterable[str] | None = None,
) -> list[str]:
    """Return de-duplicated campaign names preserving input order."""

    values: list[str] = []
    if campaign_universe:
        values.extend([str(v) for v in campaign_universe if _clean_text(v)])
    else:
        if _clean_text(client_brand):
            values.append(str(client_brand))
        values.extend([str(v) for v in (competitors or []) if _clean_text(v)])

    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.casefold().strip()
        if key and key not in seen:
            result.append(value.strip())
            seen.add(key)
    return result


def _build_campaign_where(campaigns: Iterable[str]) -> tuple[str, list[str]]:
    clauses: list[str] = []
    params: list[str] = []

    for campaign in campaigns:
        if not _clean_text(campaign):
            continue
        clauses.append("raw ->> 'Campaigns' ILIKE %s")
        params.append(f"%{campaign}%")

    if not clauses:
        raise SpokespersonEnrichmentWorkflowError(
            "campaign_universe wajib diisi untuk spokesperson enrichment."
        )
    return " OR ".join(clauses), params


def fetch_spokesperson_candidate_records(
    *,
    campaign_universe: Iterable[str],
    start_date: str,
    end_date: str,
    canonical_post_ids: Iterable[Any] | None = None,
) -> list[dict[str, Any]]:
    """Fetch Online Media/Print records for campaign scope and normalize them.

    Scope rule:
    - Campaigns is the source of truth.
    - Online Media / Print only.
    - The query intentionally selects raw fields used by _normalise_post.
    """

    campaigns = [c for c in campaign_universe if _clean_text(c)]
    campaign_where, campaign_params = _build_campaign_where(campaigns)
    clean_ids = sorted(
        {int(value) for value in (canonical_post_ids or []) if _clean_text(value).isdigit()}
    )
    id_filter_sql = " AND id = ANY(%s)" if clean_ids else ""

    sql = f"""
        SELECT
          id AS "_cogan_canonical_post_id",
          post_date AS "_cogan_post_date",
          channel AS "_cogan_channel",
          engagement AS "_cogan_interactions",
          url AS "_cogan_url",
          title AS "Title",
          content AS "Content",
          author AS "Author",
          sentiment AS "Sentiment",
          potential_reach AS "potential_reach",
          raw ->> 'Campaigns' AS "Campaigns",
          raw ->> 'Tags' AS "Tags",
          raw ->> 'Dashboard Name' AS "Dashboard Name",
          raw ->> 'Widget Name' AS "Widget Name",
          raw ->> 'Media Name' AS "Media Name",
          raw ->> 'Spokesperson' AS "Spokesperson",
          raw ->> 'Ad Value' AS "Ad Value",
          raw ->> 'PR Value' AS "PR Value",
          raw ->> 'Readership' AS "Readership",
          raw ->> 'Media Type' AS "Media Type",
          raw ->> 'Original Reach' AS "Original Reach",
          raw ->> 'Viral Reach' AS "Viral Reach"
        FROM posts
        WHERE post_date::date BETWEEN %s::date AND %s::date
          AND (
            channel IN ('Online Media', 'Print', 'Print Media', 'Printmedia')
            OR lower(COALESCE(raw ->> 'Media Type', '')) IN ('online media', 'print', 'print media', 'printmedia')
          )
          AND ({campaign_where})
          {id_filter_sql}
    """

    params = [start_date, end_date] + campaign_params
    if clean_ids:
        params.append(clean_ids)
    records: list[dict[str, Any]] = []

    pool = _get_pool()
    try:
        with pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(sql, params)
                for row in cursor.fetchall():
                    records.append(_normalise_post(row))
    except Exception as exc:  # noqa: BLE001
        raise SpokespersonEnrichmentWorkflowError(
            "Gagal mengambil candidate records untuk spokesperson enrichment."
        ) from exc

    return records



def fetch_spokesperson_candidates_by_ids(
    canonical_post_ids: Iterable[Any],
) -> list[dict[str, Any]]:
    """Hydrate canonical article metadata directly from server-side post IDs."""

    clean_ids = sorted(
        {int(value) for value in canonical_post_ids if _clean_text(value).isdigit()}
    )
    if not clean_ids:
        return []

    sql = """
        SELECT
          id AS "_cogan_canonical_post_id",
          post_date AS "_cogan_post_date",
          channel AS "_cogan_channel",
          engagement AS "_cogan_interactions",
          url AS "_cogan_url",
          title AS "Title",
          content AS "Content",
          author AS "Author",
          sentiment AS "Sentiment",
          potential_reach AS "potential_reach",
          raw ->> 'Campaigns' AS "Campaigns",
          raw ->> 'Tags' AS "Tags",
          raw ->> 'Dashboard Name' AS "Dashboard Name",
          raw ->> 'Widget Name' AS "Widget Name",
          raw ->> 'Media Name' AS "Media Name",
          raw ->> 'Spokesperson' AS "Spokesperson",
          raw ->> 'Ad Value' AS "Ad Value",
          raw ->> 'PR Value' AS "PR Value",
          raw ->> 'Readership' AS "Readership",
          raw ->> 'Media Type' AS "Media Type",
          raw ->> 'Original Reach' AS "Original Reach",
          raw ->> 'Viral Reach' AS "Viral Reach"
        FROM posts
        WHERE id = ANY(%s)
    """

    pool = _get_pool()
    try:
        with pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(sql, (clean_ids,))
                return [_normalise_post(row) for row in cursor.fetchall()]
    except Exception as exc:  # noqa: BLE001
        raise SpokespersonEnrichmentWorkflowError(
            "Gagal meng-hydrate candidate spokesperson dari canonical post ID."
        ) from exc


def _hydrate_response_hashes(
    normalized: Mapping[str, Any],
    candidates: Iterable[Mapping[str, Any]] | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Inject trusted content_hash from server-side candidate metadata."""

    candidate_rows = [dict(item) for item in (candidates or [])]
    by_id = {
        _clean_text(item.get("canonical_post_id")): item
        for item in candidate_rows
        if _clean_text(item.get("canonical_post_id"))
    }
    result_ids = [
        _clean_text(item.get("canonical_post_id"))
        for item in (normalized.get("results") or [])
        if _clean_text(item.get("canonical_post_id"))
    ]
    missing_ids = [value for value in result_ids if value not in by_id]
    if missing_ids:
        hydrated = fetch_spokesperson_candidates_by_ids(missing_ids)
        for item in hydrated:
            key = _clean_text(item.get("canonical_post_id"))
            if key:
                by_id[key] = item
                candidate_rows.append(item)

    unresolved = sorted({value for value in result_ids if value not in by_id})
    if unresolved:
        raise SpokespersonEnrichmentWorkflowError(
            "canonical_post_id tidak ditemukan di database: " + ", ".join(unresolved)
        )

    seen: set[str] = set()
    hydrated_results: list[dict[str, Any]] = []
    for item in normalized.get("results") or []:
        row = dict(item)
        canonical_id = _clean_text(row.get("canonical_post_id"))
        if canonical_id in seen:
            raise SpokespersonEnrichmentWorkflowError(
                f"Duplicate canonical_post_id pada hasil spokesperson: {canonical_id}"
            )
        seen.add(canonical_id)
        candidate = by_id[canonical_id]
        row["content_hash"] = candidate.get("content_hash")
        hydrated_results.append(row)

    return {
        "results": hydrated_results,
        "summary": summarize_spokesperson_results(hydrated_results),
    }, candidate_rows

def _chunk_list(items: list[dict[str, Any]], chunk_size: int) -> list[list[dict[str, Any]]]:
    chunk_size = max(1, int(chunk_size or DEFAULT_LLM_BATCH_SIZE))
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def prepare_spokesperson_enrichment_batch(
    *,
    client_brand: str | None = None,
    competitors: Iterable[str] | None = None,
    campaign_universe: Iterable[str] | None = None,
    start_date: str,
    end_date: str,
    sample_pct: float = 0.10,
    min_articles: int = 50,
    max_articles: int = 100,
    llm_batch_size: int = DEFAULT_LLM_BATCH_SIZE,
    include_prompts: bool = True,
    canonical_post_ids: Iterable[Any] | None = None,
) -> dict[str, Any]:
    """Prepare spokesperson enrichment batch for Claude/LLM.

    Returns one of:
    - READY: selected candidates are already cached
    - NEEDS_AUTO_SPOKESPERSON_ENRICHMENT: missing candidates need LLM extraction
    - NOT_APPLICABLE: no eligible Online Media/Print records
    """

    campaigns = normalize_campaign_universe(client_brand, competitors, campaign_universe)
    canonical_filter = (
        list(canonical_post_ids) if canonical_post_ids is not None else None
    )
    if canonical_filter == []:
        return {
            "success": True,
            "workflow_status": "NOT_APPLICABLE",
            "requires_user_action": False,
            "requires_claude_action": False,
            "workflow_version": WORKFLOW_VERSION,
            "campaign_universe": campaigns,
            "start_date": start_date,
            "end_date": end_date,
            "eligible_count": 0,
            "selected_count": 0,
            "cached_count": 0,
            "missing_count": 0,
            "topic_relevant_candidate_filter_applied": True,
            "message": "Tidak ada artikel topic-classified relevant untuk spokesperson enrichment.",
        }
    if not campaigns:
        return {
            "success": False,
            "workflow_status": "NEEDS_CAMPAIGN_SCOPE",
            "requires_user_action": True,
            "requires_claude_action": False,
            "message": "Campaign/client/competitor scope belum tersedia.",
            "workflow_version": WORKFLOW_VERSION,
        }

    ensure_spokesperson_enrichment_store()

    records = fetch_spokesperson_candidate_records(
        campaign_universe=campaigns,
        start_date=start_date,
        end_date=end_date,
        canonical_post_ids=canonical_filter,
    )

    candidate_pack = build_spokesperson_enrichment_candidates(
        records=records,
        campaign_universe=campaigns,
        sample_pct=sample_pct,
        min_articles=min_articles,
        max_articles=max_articles,
    )
    candidates = list(candidate_pack.get("candidates") or [])

    if not candidates:
        return {
            "success": True,
            "workflow_status": "NOT_APPLICABLE",
            "requires_user_action": False,
            "requires_claude_action": False,
            "workflow_version": WORKFLOW_VERSION,
            "campaign_universe": campaigns,
            "start_date": start_date,
            "end_date": end_date,
            "eligible_count": candidate_pack.get("eligible_count", 0),
            "selected_count": 0,
            "cached_count": 0,
            "missing_count": 0,
            "selection_policy": candidate_pack.get("selection_policy"),
            "message": "Tidak ada eligible Online Media/Print article untuk spokesperson enrichment.",
        }

    cache_split = split_cached_and_missing_candidates(candidates)
    missing_candidates = list(cache_split.get("missing_candidates") or [])
    cached_results = list(cache_split.get("cached_results") or [])

    prompt_batches = []
    if include_prompts and missing_candidates:
        for batch_no, batch_candidates in enumerate(_chunk_list(missing_candidates, llm_batch_size), start=1):
            prompt_batches.append(
                {
                    "batch_no": batch_no,
                    "candidate_count": len(batch_candidates),
                    "candidate_ids": [c.get("canonical_post_id") for c in batch_candidates],
                    "prompt": build_spokesperson_extraction_prompt(
                        batch_candidates,
                        campaign_universe=campaigns,
                    ),
                    "candidates": batch_candidates,
                }
            )

    workflow_status = (
        "READY" if not missing_candidates else "NEEDS_AUTO_SPOKESPERSON_ENRICHMENT"
    )

    return {
        "success": True,
        "workflow_status": workflow_status,
        "requires_user_action": False,
        "requires_claude_action": bool(missing_candidates),
        "workflow_version": WORKFLOW_VERSION,
        "campaign_universe": campaigns,
        "start_date": start_date,
        "end_date": end_date,
        "eligible_count": candidate_pack.get("eligible_count", 0),
        "sample_size": candidate_pack.get("sample_size", 0),
        "selected_count": candidate_pack.get("selected_count", len(candidates)),
        "cached_count": cache_split.get("cached_count", 0),
        "missing_count": cache_split.get("missing_count", 0),
        "selection_policy": candidate_pack.get("selection_policy"),
        "topic_relevant_candidate_filter_applied": canonical_filter is not None,
        "cached_summary": cache_split.get("cached_summary", {}),
        "cached_results": cached_results,
        "missing_candidates": missing_candidates,
        "prompt_batch_count": len(prompt_batches),
        "prompt_batches": prompt_batches,
        "message": (
            "Semua selected spokesperson candidates sudah tersedia di cache."
            if not missing_candidates
            else "Spokesperson enrichment membutuhkan LLM extraction untuk candidate yang belum cached."
        ),
    }


def save_spokesperson_enrichment_batch_response(
    response: Any,
    *,
    candidates: Iterable[Mapping[str, Any]] | None = None,
    model_version: str = "claude_spokesperson_extraction_v1",
    overwrite: bool = True,
) -> dict[str, Any]:
    """Validate and save an LLM extraction response into the cache."""

    is_valid, errors, normalized = validate_spokesperson_batch_response(response)
    if not is_valid:
        return {
            "success": False,
            "validation_errors": errors,
            "normalized_response": normalized,
            "workflow_version": WORKFLOW_VERSION,
        }

    normalized, hydrated_candidates = _hydrate_response_hashes(
        normalized,
        candidates,
    )

    saved = save_spokesperson_enrichment_results(
        normalized,
        candidates=hydrated_candidates,
        model_version=model_version,
        overwrite=overwrite,
    )

    return {
        "success": True,
        "validation_errors": [],
        "normalized_response": normalized,
        "save_result": saved,
        "summary": normalized.get("summary") or summarize_spokesperson_results(
            normalized.get("results") or []
        ),
        "workflow_version": WORKFLOW_VERSION,
    }


__all__ = [
    "WORKFLOW_VERSION",
    "prepare_spokesperson_enrichment_batch",
    "save_spokesperson_enrichment_batch_response",
    "fetch_spokesperson_candidate_records",
    "fetch_spokesperson_candidates_by_ids",
    "normalize_campaign_universe",
]


