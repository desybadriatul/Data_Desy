"""PostgreSQL cache for EVO attribute maps, batches, and assignments."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy
import json
from typing import Any
from uuid import uuid4

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from database import db
from reporting.enrichment.evo_attribute_contract import (
    EVOAttributeContractError,
    EVO_SEED_MAP_ID,
    attribute_map_hash,
    normalize_text,
    seed_attribute_map,
    validate_attribute_map_payload,
)


MAPS_TABLE = "evo_attribute_maps"
BATCHES_TABLE = "evo_attribute_batches"
ASSIGNMENTS_TABLE = "evo_attribute_assignments"
BATCH_EXPIRY_HOURS = 6


class EVOAttributeStoreError(RuntimeError):
    """EVO attribute cache/database operation failed."""


def _project_id(project_name: str) -> int:
    clean = normalize_text(project_name)
    if not clean:
        raise EVOAttributeStoreError("project_name wajib tidak kosong.")
    campaign_id = db.get_campaign_id(clean)
    if campaign_id is None:
        raise EVOAttributeStoreError(f"Project '{clean}' tidak ditemukan.")
    return int(campaign_id)


def _json(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _iso(value: Any) -> Any:
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else value


def ensure_evo_attribute_store() -> None:
    """Create only EVO enrichment tables; raw campaign/post tables are untouched."""
    ddl = [
        f"""
        CREATE TABLE IF NOT EXISTS {MAPS_TABLE} (
            map_id TEXT PRIMARY KEY,
            owner_campaign_id INTEGER REFERENCES campaigns(id) ON DELETE CASCADE,
            map_version TEXT NOT NULL,
            map_name TEXT NOT NULL,
            map_source TEXT NOT NULL CHECK (
                map_source IN ('client_approved', 'category_specific', 'evo_seed')
            ),
            category TEXT NOT NULL,
            map_hash TEXT NOT NULL,
            map_payload JSONB NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        f"""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_{MAPS_TABLE}_one_active
        ON {MAPS_TABLE} ((COALESCE(owner_campaign_id, 0)), lower(category))
        WHERE is_active
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {BATCHES_TABLE} (
            batch_id TEXT PRIMARY KEY,
            owner_campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
            map_id TEXT NOT NULL REFERENCES {MAPS_TABLE}(map_id),
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
        ON {BATCHES_TABLE} (map_id, status, created_at DESC)
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {ASSIGNMENTS_TABLE} (
            id BIGSERIAL PRIMARY KEY,
            campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
            map_id TEXT NOT NULL REFERENCES {MAPS_TABLE}(map_id),
            canonical_key TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            canonical_post_id BIGINT,
            brand TEXT NOT NULL,
            issue_name TEXT,
            primary_attribute_id TEXT NOT NULL,
            primary_attribute_label TEXT,
            primary_driver TEXT,
            secondary_attribute_id TEXT,
            classification_status TEXT NOT NULL CHECK (
                classification_status IN ('classified', 'not_relevant', 'review_needed')
            ),
            confidence NUMERIC(5,4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
            classification_rationale TEXT,
            classification_source TEXT NOT NULL DEFAULT 'auto_llm',
            batch_id TEXT REFERENCES {BATCHES_TABLE}(batch_id),
            raw_result JSONB NOT NULL DEFAULT '{{}}'::jsonb,
            classified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (campaign_id, map_id, canonical_key, content_hash)
        )
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_{ASSIGNMENTS_TABLE}_lookup
        ON {ASSIGNMENTS_TABLE} (campaign_id, map_id, canonical_key, content_hash)
        """,
    ]
    try:
        with db.get_pool().connection() as conn:
            with conn.cursor() as cur:
                for statement in ddl:
                    cur.execute(statement)
            conn.commit()
    except Exception as exc:
        raise EVOAttributeStoreError("Gagal memastikan table EVO attribute cache.") from exc


def _map_from_row(row: Mapping[str, Any]) -> dict[str, Any]:
    payload = _json(row.get("map_payload"))
    if not isinstance(payload, Mapping):
        raise EVOAttributeStoreError("map_payload tidak valid di database.")
    item = deepcopy(dict(payload))
    item.update(
        {
            "owner_project_name": row.get("owner_project_name"),
            "owner_campaign_id": row.get("owner_campaign_id"),
            "map_hash": row.get("map_hash"),
            "is_active": bool(row.get("is_active")),
            "created_at": _iso(row.get("created_at")),
            "updated_at": _iso(row.get("updated_at")),
        }
    )
    return item


def ensure_seed_attribute_map() -> dict[str, Any]:
    """Persist the stable seed fallback without overriding a better active map."""
    ensure_evo_attribute_store()
    existing = get_attribute_map(EVO_SEED_MAP_ID)
    if existing:
        return existing

    # A client/category map may already be the active generic fallback. In that
    # case the seed is stored for explicit fallback use, but must not deactivate
    # the existing active map.
    try:
        with db.get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT 1
                    FROM {MAPS_TABLE}
                    WHERE owner_campaign_id IS NULL
                      AND lower(category) = 'generic'
                      AND is_active = TRUE
                    LIMIT 1
                    """
                )
                has_active_generic = cur.fetchone() is not None
    except Exception as exc:
        raise EVOAttributeStoreError(
            "Gagal memeriksa active global EVO attribute map."
        ) from exc

    return save_attribute_map(
        project_name=None,
        attribute_map=seed_attribute_map(),
        activate=not has_active_generic,
    )


def save_attribute_map(
    *,
    project_name: str | None,
    attribute_map: Mapping[str, Any],
    activate: bool = True,
) -> dict[str, Any]:
    try:
        normalized = validate_attribute_map_payload(attribute_map)
    except EVOAttributeContractError as exc:
        raise EVOAttributeStoreError(str(exc)) from exc

    owner_campaign_id = _project_id(project_name) if normalize_text(project_name) else None
    ensure_evo_attribute_store()
    try:
        with db.get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    f"SELECT 1 FROM {MAPS_TABLE} WHERE map_id = %s",
                    (normalized["map_id"],),
                )
                if cur.fetchone():
                    raise EVOAttributeStoreError(
                        "map_id sudah ada. Buat map_id/map_version baru bila map berubah."
                    )

                if activate:
                    if owner_campaign_id is None:
                        cur.execute(
                            f"""
                            UPDATE {MAPS_TABLE}
                            SET is_active = FALSE, updated_at = NOW()
                            WHERE owner_campaign_id IS NULL
                              AND lower(category) = lower(%s)
                              AND is_active
                            """,
                            (normalized["category"],),
                        )
                    else:
                        cur.execute(
                            f"""
                            UPDATE {MAPS_TABLE}
                            SET is_active = FALSE, updated_at = NOW()
                            WHERE owner_campaign_id = %s
                              AND lower(category) = lower(%s)
                              AND is_active
                            """,
                            (owner_campaign_id, normalized["category"]),
                        )

                cur.execute(
                    f"""
                    INSERT INTO {MAPS_TABLE} (
                        map_id, owner_campaign_id, map_version, map_name,
                        map_source, category, map_hash, map_payload, is_active
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING
                        map_id, owner_campaign_id,
                        %s::text AS owner_project_name,
                        map_hash, map_payload, is_active, created_at, updated_at
                    """,
                    (
                        normalized["map_id"],
                        owner_campaign_id,
                        normalized["map_version"],
                        normalized["map_name"],
                        normalized["map_source"],
                        normalized["category"],
                        attribute_map_hash(normalized),
                        Jsonb(normalized),
                        bool(activate),
                        normalize_text(project_name) or None,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
    except EVOAttributeStoreError:
        raise
    except Exception as exc:
        raise EVOAttributeStoreError("Gagal menyimpan EVO attribute map.") from exc
    return _map_from_row(row)


def get_attribute_map(map_id: str) -> dict[str, Any] | None:
    clean = normalize_text(map_id)
    if not clean:
        raise EVOAttributeStoreError("map_id wajib tidak kosong.")
    ensure_evo_attribute_store()
    query = f"""
        SELECT m.map_id, m.owner_campaign_id, c.name AS owner_project_name,
               m.map_hash, m.map_payload, m.is_active, m.created_at, m.updated_at
        FROM {MAPS_TABLE} m
        LEFT JOIN campaigns c ON c.id = m.owner_campaign_id
        WHERE m.map_id = %s
    """
    try:
        with db.get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, (clean,))
                row = cur.fetchone()
    except Exception as exc:
        raise EVOAttributeStoreError("Gagal membaca EVO attribute map.") from exc
    return _map_from_row(row) if row else None


def resolve_attribute_map(
    *,
    project_name: str,
    map_id: str | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    ensure_seed_attribute_map()
    if normalize_text(map_id):
        item = get_attribute_map(normalize_text(map_id))
        if not item:
            raise EVOAttributeStoreError(f"map_id '{map_id}' tidak ditemukan.")
        return item

    campaign_id = _project_id(project_name)
    category_clean = normalize_text(category)
    ensure_evo_attribute_store()
    params: list[Any] = [campaign_id]
    category_clause = ""
    if category_clean:
        category_clause = "AND lower(m.category) = lower(%s)"
        params.append(category_clean)

    query = f"""
        SELECT m.map_id, m.owner_campaign_id, c.name AS owner_project_name,
               m.map_hash, m.map_payload, m.is_active, m.created_at, m.updated_at
        FROM {MAPS_TABLE} m
        LEFT JOIN campaigns c ON c.id = m.owner_campaign_id
        WHERE m.owner_campaign_id = %s AND m.is_active {category_clause}
        ORDER BY m.updated_at DESC
        LIMIT 1
    """
    try:
        with db.get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                if row:
                    return _map_from_row(row)

                if category_clean:
                    cur.execute(
                        f"""
                        SELECT m.map_id, m.owner_campaign_id, NULL::text AS owner_project_name,
                               m.map_hash, m.map_payload, m.is_active,
                               m.created_at, m.updated_at
                        FROM {MAPS_TABLE} m
                        WHERE m.owner_campaign_id IS NULL
                          AND lower(m.category) = lower(%s)
                          AND m.is_active
                        ORDER BY m.updated_at DESC
                        LIMIT 1
                        """,
                        (category_clean,),
                    )
                    row = cur.fetchone()
                    if row:
                        return _map_from_row(row)
    except Exception as exc:
        raise EVOAttributeStoreError("Gagal resolve EVO attribute map.") from exc

    seed = get_attribute_map(EVO_SEED_MAP_ID)
    if not seed:
        raise EVOAttributeStoreError("EVO seed map gagal tersedia.")
    return seed


def list_attribute_maps(project_name: str | None = None) -> list[dict[str, Any]]:
    ensure_seed_attribute_map()
    owner_id = _project_id(project_name) if normalize_text(project_name) else None
    where = "WHERE m.owner_campaign_id = %s OR m.owner_campaign_id IS NULL" if owner_id else ""
    params = (owner_id,) if owner_id else ()
    query = f"""
        SELECT m.map_id, m.owner_campaign_id, c.name AS owner_project_name,
               m.map_hash, m.map_payload, m.is_active, m.created_at, m.updated_at
        FROM {MAPS_TABLE} m
        LEFT JOIN campaigns c ON c.id = m.owner_campaign_id
        {where}
        ORDER BY m.is_active DESC, m.updated_at DESC
    """
    try:
        with db.get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
    except Exception as exc:
        raise EVOAttributeStoreError("Gagal membaca daftar EVO attribute map.") from exc
    return [_map_from_row(row) for row in rows]


def get_assignment_index(
    *,
    project_name: str,
    map_id: str,
    post_refs: Iterable[Mapping[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    refs = list(post_refs)
    if not refs:
        return {}
    campaign_id = _project_id(project_name)
    ensure_evo_attribute_store()
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
        SELECT canonical_key, content_hash, canonical_post_id, brand, issue_name,
               primary_attribute_id, primary_attribute_label, primary_driver,
               secondary_attribute_id, classification_status, confidence,
               classification_rationale, classification_source, batch_id,
               classified_at, updated_at
        FROM {ASSIGNMENTS_TABLE}
        WHERE campaign_id = %s AND map_id = %s AND canonical_key = ANY(%s)
    """
    try:
        with db.get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, (campaign_id, map_id, keys))
                rows = cur.fetchall()
    except Exception as exc:
        raise EVOAttributeStoreError("Gagal membaca cached EVO assignments.") from exc
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        item = dict(row)
        item["confidence"] = float(item.get("confidence") or 0)
        item["classified_at"] = _iso(item.get("classified_at"))
        item["updated_at"] = _iso(item.get("updated_at"))
        result[(item["canonical_key"], item["content_hash"])] = item
    return result


def expire_stale_batches(*, map_id: str, max_age_hours: int = BATCH_EXPIRY_HOURS) -> int:
    ensure_evo_attribute_store()
    if not isinstance(max_age_hours, int) or max_age_hours < 1:
        raise EVOAttributeStoreError("max_age_hours harus integer minimal 1.")
    try:
        with db.get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE {BATCHES_TABLE}
                    SET status = 'expired', completed_at = NOW()
                    WHERE map_id = %s AND status = 'issued'
                      AND created_at < NOW() - (%s * INTERVAL '1 hour')
                    """,
                    (map_id, max_age_hours),
                )
                count = cur.rowcount
            conn.commit()
    except Exception as exc:
        raise EVOAttributeStoreError("Gagal expire EVO batch lama.") from exc
    return int(count or 0)


def get_reserved_refs(*, map_id: str) -> set[tuple[str, str, str]]:
    expire_stale_batches(map_id=map_id)
    ensure_evo_attribute_store()
    try:
        with db.get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    f"SELECT post_refs FROM {BATCHES_TABLE} WHERE map_id = %s AND status = 'issued'",
                    (map_id,),
                )
                rows = cur.fetchall()
    except Exception as exc:
        raise EVOAttributeStoreError("Gagal membaca EVO batch reservation.") from exc
    refs: set[tuple[str, str, str]] = set()
    for row in rows:
        for ref in _json(row.get("post_refs")) or []:
            if isinstance(ref, Mapping):
                brand = normalize_text(ref.get("project_name"))
                key = normalize_text(ref.get("canonical_key"))
                content_hash = normalize_text(ref.get("content_hash"))
                if brand and key and content_hash:
                    refs.add((brand.casefold(), key, content_hash))
    return refs


def _batch_from_row(row: Mapping[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["scope"] = _json(item.get("scope")) or {}
    item["post_refs"] = _json(item.get("post_refs")) or []
    item["created_at"] = _iso(item.get("created_at"))
    item["completed_at"] = _iso(item.get("completed_at"))
    return item


def create_evo_attribute_batch(
    *,
    owner_project_name: str,
    map_id: str,
    scope: Mapping[str, Any],
    post_refs: list[Mapping[str, Any]],
) -> dict[str, Any]:
    if not post_refs:
        raise EVOAttributeStoreError("Tidak dapat membuat EVO batch tanpa post.")
    owner_campaign_id = _project_id(owner_project_name)
    ensure_evo_attribute_store()
    batch_id = f"evo_attr_batch_{uuid4().hex}"
    try:
        with db.get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    f"""
                    INSERT INTO {BATCHES_TABLE} (
                        batch_id, owner_campaign_id, map_id, scope,
                        post_refs, total_posts, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, 'issued')
                    RETURNING batch_id, %s::text AS owner_project_name,
                              owner_campaign_id, map_id, scope, post_refs,
                              total_posts, status, created_at, completed_at
                    """,
                    (
                        batch_id,
                        owner_campaign_id,
                        map_id,
                        Jsonb(deepcopy(dict(scope))),
                        Jsonb([deepcopy(dict(ref)) for ref in post_refs]),
                        len(post_refs),
                        owner_project_name,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
    except Exception as exc:
        raise EVOAttributeStoreError("Gagal membuat EVO attribute batch.") from exc
    return _batch_from_row(row)


def get_evo_attribute_batch(batch_id: str) -> dict[str, Any] | None:
    clean = normalize_text(batch_id)
    if not clean:
        raise EVOAttributeStoreError("batch_id wajib tidak kosong.")
    ensure_evo_attribute_store()
    query = f"""
        SELECT b.batch_id, c.name AS owner_project_name, b.owner_campaign_id,
               b.map_id, b.scope, b.post_refs, b.total_posts, b.status,
               b.created_at, b.completed_at
        FROM {BATCHES_TABLE} b
        JOIN campaigns c ON c.id = b.owner_campaign_id
        WHERE b.batch_id = %s
    """
    try:
        with db.get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, (clean,))
                row = cur.fetchone()
    except Exception as exc:
        raise EVOAttributeStoreError("Gagal membaca EVO attribute batch.") from exc
    return _batch_from_row(row) if row else None


def save_validated_batch_results(
    *,
    batch_id: str,
    assignments: list[Mapping[str, Any]],
) -> dict[str, Any]:
    ensure_evo_attribute_store()
    if not assignments:
        raise EVOAttributeStoreError("Assignment EVO batch kosong.")
    try:
        with db.get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    f"SELECT status, total_posts, map_id FROM {BATCHES_TABLE} WHERE batch_id = %s FOR UPDATE",
                    (batch_id,),
                )
                batch = cur.fetchone()
                if batch is None:
                    raise EVOAttributeStoreError(f"Batch '{batch_id}' tidak ditemukan.")
                if batch["status"] != "issued":
                    raise EVOAttributeStoreError(
                        f"Batch '{batch_id}' berstatus {batch['status']}."
                    )
                if int(batch["total_posts"]) != len(assignments):
                    raise EVOAttributeStoreError(
                        "Jumlah assignment tidak sama dengan jumlah post batch."
                    )

                for item in assignments:
                    cur.execute(
                        f"""
                        INSERT INTO {ASSIGNMENTS_TABLE} (
                            campaign_id, map_id, canonical_key, content_hash,
                            canonical_post_id, brand, issue_name,
                            primary_attribute_id, primary_attribute_label,
                            primary_driver, secondary_attribute_id,
                            classification_status, confidence,
                            classification_rationale, classification_source,
                            batch_id, raw_result
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (campaign_id, map_id, canonical_key, content_hash)
                        DO UPDATE SET
                            canonical_post_id = EXCLUDED.canonical_post_id,
                            brand = EXCLUDED.brand,
                            issue_name = EXCLUDED.issue_name,
                            primary_attribute_id = EXCLUDED.primary_attribute_id,
                            primary_attribute_label = EXCLUDED.primary_attribute_label,
                            primary_driver = EXCLUDED.primary_driver,
                            secondary_attribute_id = EXCLUDED.secondary_attribute_id,
                            classification_status = EXCLUDED.classification_status,
                            confidence = EXCLUDED.confidence,
                            classification_rationale = EXCLUDED.classification_rationale,
                            classification_source = EXCLUDED.classification_source,
                            batch_id = EXCLUDED.batch_id,
                            raw_result = EXCLUDED.raw_result,
                            updated_at = NOW()
                        """,
                        (
                            item["campaign_id"],
                            batch["map_id"],
                            item["canonical_key"],
                            item["content_hash"],
                            item.get("canonical_post_id"),
                            item["brand"],
                            item.get("issue_name"),
                            item["primary_attribute_id"],
                            item.get("primary_attribute_label"),
                            item.get("primary_driver"),
                            item.get("secondary_attribute_id"),
                            item["classification_status"],
                            item["confidence"],
                            item.get("classification_rationale"),
                            item.get("classification_source") or "auto_llm",
                            batch_id,
                            Jsonb(deepcopy(dict(item.get("raw_result") or {}))),
                        ),
                    )

                cur.execute(
                    f"UPDATE {BATCHES_TABLE} SET status = 'completed', completed_at = NOW() WHERE batch_id = %s",
                    (batch_id,),
                )
            conn.commit()
    except EVOAttributeStoreError:
        raise
    except Exception as exc:
        raise EVOAttributeStoreError("Gagal menyimpan EVO batch results.") from exc
    return {
        "success": True,
        "batch_id": batch_id,
        "saved_assignments": len(assignments),
        "status": "completed",
    }


__all__ = [
    "ASSIGNMENTS_TABLE",
    "BATCHES_TABLE",
    "EVOAttributeStoreError",
    "MAPS_TABLE",
    "create_evo_attribute_batch",
    "ensure_evo_attribute_store",
    "ensure_seed_attribute_map",
    "expire_stale_batches",
    "get_assignment_index",
    "get_attribute_map",
    "get_evo_attribute_batch",
    "get_reserved_refs",
    "list_attribute_maps",
    "resolve_attribute_map",
    "save_attribute_map",
    "save_validated_batch_results",
]
