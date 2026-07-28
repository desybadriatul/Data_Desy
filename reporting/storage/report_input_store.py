"""
Persistent storage for Cogan Task 1 report-ready packages.

This module stores Task 1 output packages in PostgreSQL so Task 2 can retrieve
the exact frozen package by `report_input_id`. It creates only the `report_inputs`
output table; it never modifies Cogan raw/source tables such as `posts`.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import json
from typing import Any

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from reporting.contracts.report_input_contract_v1 import (
    validate_report_input_shape,
)


REPORT_INPUTS_TABLE = "report_inputs"
MAX_LIST_LIMIT = 100
VALIDATION_STATUSES = {"PASS", "PARTIAL_PASS", "FAIL"}


class ReportInputStoreError(RuntimeError):
    """Raised when report input storage cannot complete safely."""


def _require_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReportInputStoreError(
            f"'{field_name}' wajib berupa string yang tidak kosong."
        )
    return value.strip()


def _get_pool() -> Any:
    """
    Load the same PostgreSQL pool used by Cogan's raw-data layer.

    Imported lazily so this module can still be compiled/tested before
    DATABASE_URL is configured.
    """
    try:
        from database.db import get_pool
    except ImportError as exc:
        raise ReportInputStoreError(
            "Tidak dapat mengimpor database.db.get_pool. Pastikan package "
            "database Cogan tersedia."
        ) from exc

    try:
        return get_pool()
    except Exception as exc:
        raise ReportInputStoreError(
            "Database Cogan tidak siap. Periksa DATABASE_URL dan koneksi Railway."
        ) from exc


def _index_fields(report_input: Mapping[str, Any]) -> dict[str, str]:
    """
    Extract indexable metadata from a valid shared report input package.
    """
    contract_errors = validate_report_input_shape(report_input)
    if contract_errors:
        raise ReportInputStoreError(
            "Report input tidak sesuai contract: " + " | ".join(contract_errors)
        )

    context = report_input["context"]
    period = context.get("period")
    if not isinstance(period, Mapping):
        raise ReportInputStoreError("context.period harus berupa dictionary.")

    start_date = _require_text(
        period.get("start_date"),
        "context.period.start_date",
    )
    end_date = _require_text(
        period.get("end_date"),
        "context.period.end_date",
    )
    if start_date > end_date:
        raise ReportInputStoreError(
            "context.period.start_date tidak boleh lebih akhir dari end_date."
        )

    validation = report_input.get("validation")
    if not isinstance(validation, Mapping):
        raise ReportInputStoreError("validation harus berupa dictionary.")

    validation_status = _require_text(
        validation.get("status"),
        "validation.status",
    ).upper()
    if validation_status not in VALIDATION_STATUSES:
        raise ReportInputStoreError(
            "validation.status harus PASS, PARTIAL_PASS, atau FAIL."
        )

    return {
        "report_input_id": _require_text(
            report_input.get("report_input_id"),
            "report_input_id",
        ),
        "report_type_id": _require_text(
            report_input.get("report_type_id"),
            "report_type_id",
        ),
        "project_name": _require_text(
            context.get("project_name"),
            "context.project_name",
        ),
        "period_start": start_date,
        "period_end": end_date,
        "validation_status": validation_status,
    }


def _normalize_payload(payload: Any) -> dict[str, Any]:
    """Normalize a JSONB payload returned by PostgreSQL/psycopg."""
    if isinstance(payload, Mapping):
        return deepcopy(dict(payload))

    if isinstance(payload, str):
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ReportInputStoreError(
                "Payload JSON report input rusak di database."
            ) from exc

        if isinstance(decoded, Mapping):
            return deepcopy(dict(decoded))

    raise ReportInputStoreError(
        "Payload report input di database bukan object JSON."
    )


def ensure_report_input_store() -> None:
    """
    Create report-input output storage and lookup indexes if absent.

    This is safe to call repeatedly. It does not alter the raw data schema.
    """
    create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {REPORT_INPUTS_TABLE} (
            report_input_id TEXT PRIMARY KEY,
            report_type_id TEXT NOT NULL,
            project_name TEXT NOT NULL,
            period_start DATE NOT NULL,
            period_end DATE NOT NULL,
            validation_status TEXT NOT NULL CHECK (
                validation_status IN ('PASS', 'PARTIAL_PASS', 'FAIL')
            ),
            payload JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """

    index_queries = [
        f"""
        CREATE INDEX IF NOT EXISTS idx_{REPORT_INPUTS_TABLE}_project_period
        ON {REPORT_INPUTS_TABLE} (project_name, period_start, period_end)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_{REPORT_INPUTS_TABLE}_type_updated
        ON {REPORT_INPUTS_TABLE} (report_type_id, updated_at DESC)
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
    except Exception as exc:
        raise ReportInputStoreError(
            "Gagal membuat/mengecek table report_inputs. "
            "Periksa permission database Railway."
        ) from exc


def save_report_input(
    report_input: Mapping[str, Any],
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """
    Save a frozen Task 1 package.

    Default `overwrite=False` prevents accidental changes to a package that
    Task 2 may already be using. Use overwrite only for an explicit rebuild
    of exactly the same report_input_id.
    """
    fields = _index_fields(report_input)
    payload = deepcopy(dict(report_input))
    ensure_report_input_store()

    insert_sql = f"""
        INSERT INTO {REPORT_INPUTS_TABLE} (
            report_input_id, report_type_id, project_name,
            period_start, period_end, validation_status, payload
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING
            report_input_id,
            report_type_id,
            project_name,
            period_start::TEXT AS period_start,
            period_end::TEXT AS period_end,
            validation_status,
            created_at,
            updated_at
    """

    upsert_sql = f"""
        INSERT INTO {REPORT_INPUTS_TABLE} (
            report_input_id, report_type_id, project_name,
            period_start, period_end, validation_status, payload
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (report_input_id) DO UPDATE SET
            report_type_id = EXCLUDED.report_type_id,
            project_name = EXCLUDED.project_name,
            period_start = EXCLUDED.period_start,
            period_end = EXCLUDED.period_end,
            validation_status = EXCLUDED.validation_status,
            payload = EXCLUDED.payload,
            updated_at = NOW()
        RETURNING
            report_input_id,
            report_type_id,
            project_name,
            period_start::TEXT AS period_start,
            period_end::TEXT AS period_end,
            validation_status,
            created_at,
            updated_at
    """

    params = (
        fields["report_input_id"],
        fields["report_type_id"],
        fields["project_name"],
        fields["period_start"],
        fields["period_end"],
        fields["validation_status"],
        Jsonb(payload),
    )

    pool = _get_pool()
    try:
        with pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(upsert_sql if overwrite else insert_sql, params)
                row = cursor.fetchone()
            conn.commit()
    except Exception as exc:
        error_name = type(exc).__name__.lower()
        if not overwrite and (
            "unique" in error_name or "duplicate key" in str(exc).lower()
        ):
            raise ReportInputStoreError(
                f"report_input_id '{fields['report_input_id']}' sudah ada. "
                "Gunakan ID baru atau overwrite=True bila memang rebuild."
            ) from exc
        raise ReportInputStoreError(
            "Gagal menyimpan report input ke database."
        ) from exc

    if not row:
        raise ReportInputStoreError(
            "Database tidak mengembalikan metadata setelah save report input."
        )

    return dict(row)


def get_report_input(report_input_id: str) -> dict[str, Any] | None:
    """
    Return a full frozen package for Task 2, or None when it does not exist.
    """
    report_input_id = _require_text(report_input_id, "report_input_id")
    ensure_report_input_store()

    query = f"""
        SELECT payload
        FROM {REPORT_INPUTS_TABLE}
        WHERE report_input_id = %s
    """

    pool = _get_pool()
    try:
        with pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(query, (report_input_id,))
                row = cursor.fetchone()
    except Exception as exc:
        raise ReportInputStoreError(
            "Gagal membaca report input dari database."
        ) from exc

    return None if row is None else _normalize_payload(row["payload"])


def get_report_input_summary(report_input_id: str) -> dict[str, Any] | None:
    """Return package metadata only; useful for Task 2 routing and MCP lists."""
    report_input_id = _require_text(report_input_id, "report_input_id")
    ensure_report_input_store()

    query = f"""
        SELECT
            report_input_id,
            report_type_id,
            project_name,
            period_start::TEXT AS period_start,
            period_end::TEXT AS period_end,
            validation_status,
            created_at,
            updated_at
        FROM {REPORT_INPUTS_TABLE}
        WHERE report_input_id = %s
    """

    pool = _get_pool()
    try:
        with pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(query, (report_input_id,))
                row = cursor.fetchone()
    except Exception as exc:
        raise ReportInputStoreError(
            "Gagal membaca summary report input."
        ) from exc

    return dict(row) if row else None


def list_report_inputs(
    *,
    project_name: str | None = None,
    report_type_id: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    List recent stored packages without returning heavy qt_*/ql_* payloads.
    """
    if not isinstance(limit, int) or isinstance(limit, bool):
        raise ReportInputStoreError("'limit' harus integer.")
    limit = max(1, min(limit, MAX_LIST_LIMIT))

    filters: list[str] = []
    params: list[Any] = []

    if project_name is not None:
        filters.append("project_name = %s")
        params.append(_require_text(project_name, "project_name"))

    if report_type_id is not None:
        filters.append("report_type_id = %s")
        params.append(_require_text(report_type_id, "report_type_id"))

    where_clause = "WHERE " + " AND ".join(filters) if filters else ""
    params.append(limit)
    ensure_report_input_store()

    query = f"""
        SELECT
            report_input_id,
            report_type_id,
            project_name,
            period_start::TEXT AS period_start,
            period_end::TEXT AS period_end,
            validation_status,
            created_at,
            updated_at
        FROM {REPORT_INPUTS_TABLE}
        {where_clause}
        ORDER BY updated_at DESC, report_input_id DESC
        LIMIT %s
    """

    pool = _get_pool()
    try:
        with pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()
    except Exception as exc:
        raise ReportInputStoreError(
            "Gagal menampilkan daftar report input."
        ) from exc

    return [dict(row) for row in rows]


def delete_report_input(report_input_id: str) -> bool:
    """
    Explicit cleanup for invalid/test packages. Normal flow does not delete.
    """
    report_input_id = _require_text(report_input_id, "report_input_id")
    ensure_report_input_store()

    query = f"""
        DELETE FROM {REPORT_INPUTS_TABLE}
        WHERE report_input_id = %s
        RETURNING report_input_id
    """

    pool = _get_pool()
    try:
        with pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(query, (report_input_id,))
                row = cursor.fetchone()
            conn.commit()
    except Exception as exc:
        raise ReportInputStoreError(
            "Gagal menghapus report input."
        ) from exc

    return row is not None


__all__ = [
    "MAX_LIST_LIMIT",
    "REPORT_INPUTS_TABLE",
    "ReportInputStoreError",
    "delete_report_input",
    "ensure_report_input_store",
    "get_report_input",
    "get_report_input_summary",
    "list_report_inputs",
    "save_report_input",
]
