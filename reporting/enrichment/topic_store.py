"""PostgreSQL storage for topic taxonomies, issued batches, and assignments."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy
import json
from typing import Any
from uuid import uuid4

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from database import db
from reporting.enrichment.topic_contract import (
    TopicContractError,
    normalize_text,
    validate_taxonomy_payload,
)


TAXONOMIES_TABLE = "topic_taxonomies"
BATCHES_TABLE = "topic_enrichment_batches"
ASSIGNMENTS_TABLE = "topic_assignments"
BATCH_EXPIRY_HOURS = 6


class TopicStoreError(RuntimeError):
    """Topic enrichment cache/database operation failed."""


def _project_id(project_name: str) -> int:
    clean = normalize_text(project_name)
    if not clean:
        raise TopicStoreError("project_name wajib tidak kosong.")
    campaign_id = db.get_campaign_id(clean)
    if campaign_id is None:
        raise TopicStoreError(f"Project '{clean}' tidak ditemukan.")
    return campaign_id


def _json(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _iso(value: Any) -> Any:
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else value


def ensure_topic_store() -> None:
    """Create only report-topic cache tables; raw post tables are untouched."""
    ddl = [
        f"""
        CREATE TABLE IF NOT EXISTS {TAXONOMIES_TABLE} (
            id BIGSERIAL PRIMARY KEY,
            campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
            taxonomy_version TEXT NOT NULL,
            taxonomy_name TEXT NOT NULL,
            taxonomy_payload JSONB NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (campaign_id, taxonomy_version)
        )
        """,
        f"""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_{TAXONOMIES_TABLE}_one_active
        ON {TAXONOMIES_TABLE} (campaign_id) WHERE is_active
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {BATCHES_TABLE} (
            batch_id TEXT PRIMARY KEY,
            campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
            taxonomy_version TEXT NOT NULL,
            scope JSONB NOT NULL,
            post_refs JSONB NOT NULL,
            total_posts INTEGER NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN ('issued', 'completed', 'expired', 'cancelled')
            ),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            completed_at TIMESTAMPTZ
        )
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_{BATCHES_TABLE}_lookup
        ON {BATCHES_TABLE} (campaign_id, taxonomy_version, status, created_at DESC)
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {ASSIGNMENTS_TABLE} (
            id BIGSERIAL PRIMARY KEY,
            campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
            taxonomy_version TEXT NOT NULL,
            canonical_key TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            canonical_post_id BIGINT,
            primary_topic_id TEXT NOT NULL,
            primary_topic_label TEXT NOT NULL,
            classification_status TEXT NOT NULL CHECK (
                classification_status IN ('classified', 'not_relevant', 'review_needed')
            ),
            confidence TEXT NOT NULL CHECK (
                confidence IN ('high', 'medium', 'low')
            ),
            classification_reason TEXT,
            emerging_topic_detail TEXT,
            batch_id TEXT REFERENCES topic_enrichment_batches(batch_id),
            raw_result JSONB NOT NULL DEFAULT '{{}}'::jsonb,
            classified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (campaign_id, taxonomy_version, canonical_key, content_hash)
        )
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_{ASSIGNMENTS_TABLE}_lookup
        ON {ASSIGNMENTS_TABLE} (
            campaign_id, taxonomy_version, canonical_key, content_hash
        )
        """,
    ]
    try:
        with db.get_pool().connection() as conn:
            with conn.cursor() as cur:
                for statement in ddl:
                    cur.execute(statement)
            conn.commit()
    except Exception as exc:
        raise TopicStoreError("Gagal memastikan table topic cache.") from exc


def _taxonomy_from_row(row: Mapping[str, Any]) -> dict[str, Any]:
    payload = _json(row.get("taxonomy_payload"))
    if not isinstance(payload, Mapping):
        raise TopicStoreError("taxonomy_payload tidak valid di database.")
    item = deepcopy(dict(payload))
    item.update(
        {
            "project_name": row.get("project_name"),
            "campaign_id": row.get("campaign_id"),
            "is_active": bool(row.get("is_active")),
            "created_at": _iso(row.get("created_at")),
            "updated_at": _iso(row.get("updated_at")),
        }
    )
    return item


def save_taxonomy(
    *,
    project_name: str,
    taxonomy: Mapping[str, Any],
    activate: bool = True,
) -> dict[str, Any]:
    """Save a new immutable taxonomy version and optionally make it active."""
    try:
        taxonomy = validate_taxonomy_payload(taxonomy)
    except TopicContractError as exc:
        raise TopicStoreError(str(exc)) from exc

    campaign_id = _project_id(project_name)
    ensure_topic_store()

    try:
        with db.get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    f"""
                    SELECT 1 FROM {TAXONOMIES_TABLE}
                    WHERE campaign_id = %s AND taxonomy_version = %s
                    """,
                    (campaign_id, taxonomy["taxonomy_version"]),
                )
                if cur.fetchone():
                    raise TopicStoreError(
                        "taxonomy_version sudah ada. Buat versi baru bila "
                        "taxonomy diubah."
                    )

                if activate:
                    cur.execute(
                        f"""
                        UPDATE {TAXONOMIES_TABLE}
                        SET is_active = FALSE, updated_at = NOW()
                        WHERE campaign_id = %s AND is_active
                        """,
                        (campaign_id,),
                    )

                cur.execute(
                    f"""
                    INSERT INTO {TAXONOMIES_TABLE} (
                        campaign_id, taxonomy_version, taxonomy_name,
                        taxonomy_payload, is_active
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING
                        %s::text AS project_name,
                        campaign_id, taxonomy_payload, is_active,
                        created_at, updated_at
                    """,
                    (
                        campaign_id,
                        taxonomy["taxonomy_version"],
                        taxonomy["taxonomy_name"],
                        Jsonb(taxonomy),
                        bool(activate),
                        project_name,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
    except TopicStoreError:
        raise
    except Exception as exc:
        raise TopicStoreError("Gagal menyimpan taxonomy.") from exc

    return _taxonomy_from_row(row)


def _get_taxonomy_row(
    project_name: str,
    taxonomy_version: str | None,
    *,
    active_only: bool,
) -> dict[str, Any] | None:
    campaign_id = _project_id(project_name)
    ensure_topic_store()

    where = "t.is_active = TRUE" if active_only else "t.taxonomy_version = %s"
    params = [campaign_id] if active_only else [campaign_id, taxonomy_version]

    query = f"""
        SELECT
            c.name AS project_name, t.campaign_id, t.taxonomy_payload,
            t.is_active, t.created_at, t.updated_at
        FROM {TAXONOMIES_TABLE} t
        JOIN campaigns c ON c.id = t.campaign_id
        WHERE t.campaign_id = %s AND {where}
        ORDER BY t.updated_at DESC
        LIMIT 1
    """
    try:
        with db.get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, params)
                row = cur.fetchone()
    except Exception as exc:
        raise TopicStoreError("Gagal membaca taxonomy.") from exc
    return _taxonomy_from_row(row) if row else None


def get_active_taxonomy(project_name: str) -> dict[str, Any] | None:
    return _get_taxonomy_row(project_name, None, active_only=True)


def get_taxonomy(
    *,
    project_name: str,
    taxonomy_version: str,
) -> dict[str, Any] | None:
    return _get_taxonomy_row(
        project_name,
        normalize_text(taxonomy_version),
        active_only=False,
    )


def list_taxonomies(project_name: str) -> list[dict[str, Any]]:
    campaign_id = _project_id(project_name)
    ensure_topic_store()
    query = f"""
        SELECT
            c.name AS project_name, t.campaign_id, t.taxonomy_payload,
            t.is_active, t.created_at, t.updated_at
        FROM {TAXONOMIES_TABLE} t
        JOIN campaigns c ON c.id = t.campaign_id
        WHERE t.campaign_id = %s
        ORDER BY t.is_active DESC, t.updated_at DESC
    """
    try:
        with db.get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, (campaign_id,))
                rows = cur.fetchall()
    except Exception as exc:
        raise TopicStoreError("Gagal membaca daftar taxonomy.") from exc
    return [_taxonomy_from_row(row) for row in rows]


def expire_stale_batches(
    *,
    project_name: str,
    taxonomy_version: str,
    max_age_hours: int = BATCH_EXPIRY_HOURS,
) -> int:
    campaign_id = _project_id(project_name)
    ensure_topic_store()
    if not isinstance(max_age_hours, int) or max_age_hours < 1:
        raise TopicStoreError("max_age_hours harus integer minimal 1.")

    try:
        with db.get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE {BATCHES_TABLE}
                    SET status = 'expired'
                    WHERE campaign_id = %s
                      AND taxonomy_version = %s
                      AND status = 'issued'
                      AND created_at < NOW() - %s::interval
                    """,
                    (campaign_id, taxonomy_version, f"{max_age_hours} hours"),
                )
                count = cur.rowcount
            conn.commit()
    except Exception as exc:
        raise TopicStoreError("Gagal meng-expire batch lama.") from exc
    return int(count or 0)


def get_assignment_index(
    *,
    project_name: str,
    taxonomy_version: str,
    post_refs: Iterable[Mapping[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    refs = list(post_refs)
    if not refs:
        return {}

    campaign_id = _project_id(project_name)
    ensure_topic_store()
    keys = sorted(
        {
            normalize_text(ref.get("canonical_key"))
            for ref in refs
            if isinstance(ref, Mapping) and normalize_text(ref.get("canonical_key"))
        }
    )
    if not keys:
        return {}

    query = f"""
        SELECT
            canonical_key, content_hash, canonical_post_id,
            primary_topic_id, primary_topic_label, classification_status,
            confidence, classification_reason, emerging_topic_detail,
            batch_id, classified_at, updated_at
        FROM {ASSIGNMENTS_TABLE}
        WHERE campaign_id = %s
          AND taxonomy_version = %s
          AND canonical_key = ANY(%s)
    """
    try:
        with db.get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, (campaign_id, taxonomy_version, keys))
                rows = cur.fetchall()
    except Exception as exc:
        raise TopicStoreError("Gagal membaca cached assignments.") from exc

    result = {}
    for row in rows:
        item = dict(row)
        item["classified_at"] = _iso(item.get("classified_at"))
        item["updated_at"] = _iso(item.get("updated_at"))
        result[(item["canonical_key"], item["content_hash"])] = item
    return result


def _batch_from_row(row: Mapping[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["scope"] = _json(item.get("scope")) or {}
    item["post_refs"] = _json(item.get("post_refs")) or []
    item["created_at"] = _iso(item.get("created_at"))
    item["completed_at"] = _iso(item.get("completed_at"))
    return item


def get_reserved_refs(
    *,
    project_name: str,
    taxonomy_version: str,
) -> set[tuple[str, str]]:
    """Prevent concurrent users from receiving the same issued batch posts."""
    expire_stale_batches(
        project_name=project_name,
        taxonomy_version=taxonomy_version,
    )
    campaign_id = _project_id(project_name)
    ensure_topic_store()
    try:
        with db.get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    f"""
                    SELECT post_refs
                    FROM {BATCHES_TABLE}
                    WHERE campaign_id = %s
                      AND taxonomy_version = %s
                      AND status = 'issued'
                    """,
                    (campaign_id, taxonomy_version),
                )
                rows = cur.fetchall()
    except Exception as exc:
        raise TopicStoreError("Gagal membaca batch yang sedang direserve.") from exc

    refs: set[tuple[str, str]] = set()
    for row in rows:
        for ref in _json(row.get("post_refs")) or []:
            if isinstance(ref, Mapping):
                key = normalize_text(ref.get("canonical_key"))
                content_hash = normalize_text(ref.get("content_hash"))
                if key and content_hash:
                    refs.add((key, content_hash))
    return refs


def create_topic_batch(
    *,
    project_name: str,
    taxonomy_version: str,
    scope: Mapping[str, Any],
    post_refs: list[Mapping[str, Any]],
) -> dict[str, Any]:
    if not post_refs:
        raise TopicStoreError("Tidak dapat membuat batch tanpa post.")
    campaign_id = _project_id(project_name)
    ensure_topic_store()
    batch_id = f"topic_batch_{uuid4().hex}"

    try:
        with db.get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    f"""
                    INSERT INTO {BATCHES_TABLE} (
                        batch_id, campaign_id, taxonomy_version,
                        scope, post_refs, total_posts, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, 'issued')
                    RETURNING
                        batch_id, %s::text AS project_name, campaign_id,
                        taxonomy_version, scope, post_refs, total_posts,
                        status, created_at, completed_at
                    """,
                    (
                        batch_id,
                        campaign_id,
                        taxonomy_version,
                        Jsonb(deepcopy(dict(scope))),
                        Jsonb([deepcopy(dict(ref)) for ref in post_refs]),
                        len(post_refs),
                        project_name,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
    except Exception as exc:
        raise TopicStoreError("Gagal membuat topic batch.") from exc
    return _batch_from_row(row)


def get_topic_batch(batch_id: str) -> dict[str, Any] | None:
    batch_id = normalize_text(batch_id)
    if not batch_id:
        raise TopicStoreError("batch_id wajib tidak kosong.")
    ensure_topic_store()
    query = f"""
        SELECT
            b.batch_id, c.name AS project_name, b.campaign_id,
            b.taxonomy_version, b.scope, b.post_refs, b.total_posts,
            b.status, b.created_at, b.completed_at
        FROM {BATCHES_TABLE} b
        JOIN campaigns c ON c.id = b.campaign_id
        WHERE b.batch_id = %s
    """
    try:
        with db.get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, (batch_id,))
                row = cur.fetchone()
    except Exception as exc:
        raise TopicStoreError("Gagal membaca topic batch.") from exc
    return _batch_from_row(row) if row else None


def save_validated_batch_results(
    *,
    batch_id: str,
    assignments: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Upsert validated assignments and atomically close the issued batch."""
    ensure_topic_store()
    if not assignments:
        raise TopicStoreError("Assignment batch kosong.")

    try:
        with db.get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    f"""
                    SELECT campaign_id, taxonomy_version, status, total_posts
                    FROM {BATCHES_TABLE}
                    WHERE batch_id = %s
                    FOR UPDATE
                    """,
                    (batch_id,),
                )
                batch = cur.fetchone()
                if batch is None:
                    raise TopicStoreError(f"Batch '{batch_id}' tidak ditemukan.")
                if batch["status"] != "issued":
                    raise TopicStoreError(
                        f"Batch '{batch_id}' berstatus {batch['status']}."
                    )
                if int(batch["total_posts"]) != len(assignments):
                    raise TopicStoreError(
                        "Jumlah assignment tidak sama dengan jumlah post batch."
                    )

                for item in assignments:
                    cur.execute(
                        f"""
                        INSERT INTO {ASSIGNMENTS_TABLE} (
                            campaign_id, taxonomy_version, canonical_key,
                            content_hash, canonical_post_id, primary_topic_id,
                            primary_topic_label, classification_status,
                            confidence, classification_reason,
                            emerging_topic_detail, batch_id, raw_result
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s
                        )
                        ON CONFLICT (
                            campaign_id, taxonomy_version, canonical_key, content_hash
                        )
                        DO UPDATE SET
                            canonical_post_id = EXCLUDED.canonical_post_id,
                            primary_topic_id = EXCLUDED.primary_topic_id,
                            primary_topic_label = EXCLUDED.primary_topic_label,
                            classification_status = EXCLUDED.classification_status,
                            confidence = EXCLUDED.confidence,
                            classification_reason = EXCLUDED.classification_reason,
                            emerging_topic_detail = EXCLUDED.emerging_topic_detail,
                            batch_id = EXCLUDED.batch_id,
                            raw_result = EXCLUDED.raw_result,
                            updated_at = NOW()
                        """,
                        (
                            batch["campaign_id"],
                            batch["taxonomy_version"],
                            item["canonical_key"],
                            item["content_hash"],
                            item.get("canonical_post_id"),
                            item["primary_topic_id"],
                            item["primary_topic_label"],
                            item["classification_status"],
                            item["confidence"],
                            item.get("classification_reason"),
                            item.get("emerging_topic_detail"),
                            batch_id,
                            Jsonb(dict(item.get("raw_result", {}))),
                        ),
                    )

                cur.execute(
                    f"""
                    UPDATE {BATCHES_TABLE}
                    SET status = 'completed', completed_at = NOW()
                    WHERE batch_id = %s
                    """,
                    (batch_id,),
                )
            conn.commit()
    except TopicStoreError:
        raise
    except Exception as exc:
        raise TopicStoreError("Gagal menyimpan results batch.") from exc

    return {
        "saved": True,
        "batch_id": batch_id,
        "assignment_count": len(assignments),
        "status": "completed",
    }


__all__ = [
    "ASSIGNMENTS_TABLE",
    "BATCHES_TABLE",
    "TAXONOMIES_TABLE",
    "TopicStoreError",
    "create_topic_batch",
    "ensure_topic_store",
    "expire_stale_batches",
    "get_active_taxonomy",
    "get_assignment_index",
    "get_reserved_refs",
    "get_taxonomy",
    "get_topic_batch",
    "list_taxonomies",
    "save_taxonomy",
    "save_validated_batch_results",
]
