from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy
import json
from typing import Any

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from reporting.enrichment.spokesperson_llm_contract import (
    normalize_spokesperson_batch_response,
    summarize_spokesperson_results,
)


SPOKESPERSON_CACHE_TABLE = "spokesperson_enrichment_cache"
STORE_VERSION = "spokesperson_enrichment_store_v1"
DEFAULT_MODEL_VERSION = "manual_or_claude_pending"


class SpokespersonEnrichmentStoreError(RuntimeError):
    """Raised when spokesperson enrichment cache operations fail."""


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _get_pool() -> Any:
    """Load the same PostgreSQL pool used by Cogan.

    Supports both package layouts used in the repo:
    - from database.db import get_pool
    - from database import db; db.get_pool()
    """

    try:
        from database.db import get_pool  # type: ignore

        return get_pool()
    except Exception:
        try:
            from database import db  # type: ignore

            return db.get_pool()
        except Exception as exc:  # noqa: BLE001
            raise SpokespersonEnrichmentStoreError(
                "Database Cogan tidak siap. Periksa DATABASE_URL dan import database."
            ) from exc


def make_spokesperson_cache_key(canonical_post_id: Any, content_hash: Any = None) -> str:
    """Build deterministic cache key for one article.

    content_hash is included when available so stale extraction can be detected
    if article content changes. canonical_post_id is still required.
    """

    canonical = _clean_text(canonical_post_id)
    if not canonical:
        raise SpokespersonEnrichmentStoreError("canonical_post_id wajib tersedia.")

    hash_part = _clean_text(content_hash)
    return f"{canonical}::{hash_part}"


def _candidate_lookup(candidates: Iterable[Mapping[str, Any]] | None) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    if not candidates:
        return lookup

    for candidate in candidates:
        canonical_post_id = candidate.get("canonical_post_id")
        if canonical_post_id in (None, ""):
            continue
        content_hash = candidate.get("content_hash")
        key = make_spokesperson_cache_key(canonical_post_id, content_hash)
        lookup[key] = deepcopy(dict(candidate))

    return lookup


def ensure_spokesperson_enrichment_store() -> None:
    """Create spokesperson enrichment cache table and indexes if absent.

    Safe to call repeatedly. This creates only an enrichment output cache and
    never modifies raw/source tables such as `posts`.
    """

    create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {SPOKESPERSON_CACHE_TABLE} (
            cache_key TEXT PRIMARY KEY,
            canonical_post_id TEXT NOT NULL,
            content_hash TEXT,
            status TEXT NOT NULL CHECK (
                status IN ('relevant', 'not_relevant', 'review_needed')
            ),
            source TEXT NOT NULL,
            confidence TEXT NOT NULL CHECK (
                confidence IN ('high', 'medium', 'low')
            ),
            spokesperson_count INTEGER NOT NULL DEFAULT 0,
            spokespersons JSONB NOT NULL DEFAULT '[]'::jsonb,
            payload JSONB NOT NULL,
            candidate_metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
            model_version TEXT NOT NULL DEFAULT '{DEFAULT_MODEL_VERSION}',
            store_version TEXT NOT NULL DEFAULT '{STORE_VERSION}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """

    index_queries = [
        f"""
        CREATE INDEX IF NOT EXISTS idx_{SPOKESPERSON_CACHE_TABLE}_canonical
        ON {SPOKESPERSON_CACHE_TABLE} (canonical_post_id)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_{SPOKESPERSON_CACHE_TABLE}_status_updated
        ON {SPOKESPERSON_CACHE_TABLE} (status, updated_at DESC)
        """,
    ]

    pool = _get_pool()
    try:
        with pool.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(create_table_sql)
                for query in index_queries:
                    cursor.execute(query)
            conn.commit()
    except Exception as exc:  # noqa: BLE001
        raise SpokespersonEnrichmentStoreError(
            "Gagal membuat/mengecek table spokesperson enrichment cache."
        ) from exc


def save_spokesperson_enrichment_results(
    response: Any,
    *,
    candidates: Iterable[Mapping[str, Any]] | None = None,
    model_version: str = DEFAULT_MODEL_VERSION,
    overwrite: bool = True,
) -> dict[str, Any]:
    """Normalize and save LLM/manual spokesperson extraction results.

    Args:
        response: dict/list/string accepted by normalize_spokesperson_batch_response.
        candidates: optional original candidates for metadata lookup.
        model_version: model or process version used for extraction.
        overwrite: update existing cache rows when True.

    Returns summary with saved/skipped counts.
    """

    normalized = normalize_spokesperson_batch_response(response)
    results = normalized.get("results", [])
    candidate_by_key = _candidate_lookup(candidates)

    ensure_spokesperson_enrichment_store()

    saved = 0
    skipped = 0
    rows_for_return: list[dict[str, Any]] = []

    insert_sql = f"""
        INSERT INTO {SPOKESPERSON_CACHE_TABLE} (
            cache_key,
            canonical_post_id,
            content_hash,
            status,
            source,
            confidence,
            spokesperson_count,
            spokespersons,
            payload,
            candidate_metadata,
            model_version,
            store_version,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (cache_key) DO UPDATE SET
            status = EXCLUDED.status,
            source = EXCLUDED.source,
            confidence = EXCLUDED.confidence,
            spokesperson_count = EXCLUDED.spokesperson_count,
            spokespersons = EXCLUDED.spokespersons,
            payload = EXCLUDED.payload,
            candidate_metadata = EXCLUDED.candidate_metadata,
            model_version = EXCLUDED.model_version,
            store_version = EXCLUDED.store_version,
            updated_at = NOW()
    """

    insert_no_overwrite_sql = f"""
        INSERT INTO {SPOKESPERSON_CACHE_TABLE} (
            cache_key,
            canonical_post_id,
            content_hash,
            status,
            source,
            confidence,
            spokesperson_count,
            spokespersons,
            payload,
            candidate_metadata,
            model_version,
            store_version,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (cache_key) DO NOTHING
    """

    pool = _get_pool()
    try:
        with pool.connection() as conn:
            with conn.cursor() as cursor:
                for result in results:
                    canonical_post_id = result.get("canonical_post_id")
                    if canonical_post_id in (None, ""):
                        skipped += 1
                        continue

                    content_hash = result.get("content_hash")
                    cache_key = make_spokesperson_cache_key(canonical_post_id, content_hash)
                    candidate_metadata = candidate_by_key.get(cache_key, {})
                    spokespersons = list(result.get("spokespersons") or [])

                    params = (
                        cache_key,
                        str(canonical_post_id),
                        _clean_text(content_hash) or None,
                        result.get("status"),
                        result.get("source"),
                        result.get("confidence"),
                        len(spokespersons),
                        Jsonb(spokespersons),
                        Jsonb(result),
                        Jsonb(candidate_metadata),
                        model_version,
                        STORE_VERSION,
                    )

                    cursor.execute(insert_sql if overwrite else insert_no_overwrite_sql, params)
                    if overwrite or cursor.rowcount:
                        saved += 1
                        rows_for_return.append(deepcopy(dict(result)))
                    else:
                        skipped += 1
            conn.commit()
    except Exception as exc:  # noqa: BLE001
        raise SpokespersonEnrichmentStoreError(
            "Gagal menyimpan hasil spokesperson enrichment cache."
        ) from exc

    return {
        "saved": saved,
        "skipped": skipped,
        "model_version": model_version,
        "store_version": STORE_VERSION,
        "summary": summarize_spokesperson_results(rows_for_return),
    }


def load_cached_spokesperson_results(
    candidates: Iterable[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Load cached extraction results for candidates by cache key."""

    keys = []
    for candidate in candidates:
        canonical_post_id = candidate.get("canonical_post_id")
        if canonical_post_id in (None, ""):
            continue
        keys.append(make_spokesperson_cache_key(canonical_post_id, candidate.get("content_hash")))

    if not keys:
        return {}

    ensure_spokesperson_enrichment_store()

    sql = f"""
        SELECT cache_key, payload, candidate_metadata, model_version, updated_at::TEXT AS updated_at
        FROM {SPOKESPERSON_CACHE_TABLE}
        WHERE cache_key = ANY(%s)
    """

    pool = _get_pool()
    try:
        with pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(sql, (keys,))
                rows = cursor.fetchall()
    except Exception as exc:  # noqa: BLE001
        raise SpokespersonEnrichmentStoreError(
            "Gagal membaca spokesperson enrichment cache."
        ) from exc

    cached: dict[str, dict[str, Any]] = {}
    for row in rows:
        payload = row.get("payload")
        if isinstance(payload, str):
            payload = json.loads(payload)
        if not isinstance(payload, Mapping):
            continue

        result = deepcopy(dict(payload))
        result["cache_key"] = row.get("cache_key")
        result["candidate_metadata"] = row.get("candidate_metadata") or {}
        result["model_version"] = row.get("model_version")
        result["cached_at"] = row.get("updated_at")
        cached[str(row.get("cache_key"))] = result

    return cached


def split_cached_and_missing_candidates(
    candidates: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Return cached results and missing candidates for an enrichment batch."""

    candidate_list = [dict(c) for c in candidates]
    cached = load_cached_spokesperson_results(candidate_list)

    missing = []
    cached_results = []

    for candidate in candidate_list:
        canonical_post_id = candidate.get("canonical_post_id")
        if canonical_post_id in (None, ""):
            missing.append(candidate)
            continue

        key = make_spokesperson_cache_key(canonical_post_id, candidate.get("content_hash"))
        if key in cached:
            cached_results.append(cached[key])
        else:
            missing.append(candidate)

    return {
        "cached_count": len(cached_results),
        "missing_count": len(missing),
        "cached_results": cached_results,
        "missing_candidates": missing,
        "cached_summary": summarize_spokesperson_results(cached_results),
    }


def load_spokesperson_results_by_ids(
    canonical_post_ids: Iterable[Any],
) -> dict[str, list[dict[str, Any]]]:
    """Load latest cached results grouped by canonical_post_id.

    This is useful for report builders that already have canonical post IDs but
    do not know content_hash.
    """

    ids = [_clean_text(value) for value in canonical_post_ids if _clean_text(value)]
    if not ids:
        return {}

    ensure_spokesperson_enrichment_store()

    sql = f"""
        SELECT DISTINCT ON (canonical_post_id)
            canonical_post_id,
            payload,
            candidate_metadata,
            model_version,
            updated_at::TEXT AS updated_at
        FROM {SPOKESPERSON_CACHE_TABLE}
        WHERE canonical_post_id = ANY(%s)
        ORDER BY canonical_post_id, updated_at DESC
    """

    pool = _get_pool()
    try:
        with pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(sql, (ids,))
                rows = cursor.fetchall()
    except Exception as exc:  # noqa: BLE001
        raise SpokespersonEnrichmentStoreError(
            "Gagal membaca spokesperson enrichment cache by canonical_post_id."
        ) from exc

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        payload = row.get("payload")
        if isinstance(payload, str):
            payload = json.loads(payload)
        if not isinstance(payload, Mapping):
            continue

        result = deepcopy(dict(payload))
        result["candidate_metadata"] = row.get("candidate_metadata") or {}
        result["model_version"] = row.get("model_version")
        result["cached_at"] = row.get("updated_at")
        grouped.setdefault(str(row.get("canonical_post_id")), []).append(result)

    return grouped
