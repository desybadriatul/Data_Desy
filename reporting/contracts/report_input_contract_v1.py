"""
Shared report-ready package contract for Cogan Task 1.

Every Task 1 builder must return the same outer package. The report-specific
difference lives only in quantitative_views and qualitative_views.

This module intentionally uses only Python standard library so all builders
can import it without adding a dependency.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy
from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4


SCHEMA_VERSION = "report_input_v1"
DEFAULT_TIMEZONE = "Asia/Jakarta"
DEFAULT_REGISTRY_VERSION = "mvp.v2.2_action_plan_first"

VALIDATION_STATUSES = frozenset({"PASS", "PARTIAL_PASS", "FAIL"})
VIEW_TYPES = frozenset({"quantitative", "qualitative"})

REQUIRED_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "report_input_id",
        "report_type_id",
        "registry_version",
        "created_at",
        "context",
        "scope",
        "metric_readiness",
        "data_health",
        "validation",
        "quantitative_views",
        "qualitative_views",
        "limitations",
        "evidence_log",
    }
)

REQUIRED_CONTEXT_KEYS = frozenset(
    {
        "project_name",
        "period",
        "timezone",
        "channels",
        "data_scope",
    }
)


class ReportInputContractError(ValueError):
    """Raised when a report input package violates the shared contract."""


def _require_text(value: str, field_name: str) -> str:
    """Return a stripped non-empty string or raise a clear contract error."""
    if not isinstance(value, str) or not value.strip():
        raise ReportInputContractError(
            f"'{field_name}' wajib berupa string yang tidak kosong."
        )
    return value.strip()


def _validate_iso_date(value: str, field_name: str) -> str:
    """Validate YYYY-MM-DD date text used by report context."""
    value = _require_text(value, field_name)
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ReportInputContractError(
            f"'{field_name}' harus memakai format YYYY-MM-DD, bukan '{value}'."
        ) from exc
    return value


def _normalize_channels(channels: Iterable[str] | None) -> list[str]:
    """
    Remove blank/duplicate channel names while preserving user-provided order.

    Empty list means the report uses all channels available in the confirmed
    scope. It does not mean the builder may silently change the scope.
    """
    if channels is None:
        return []

    if isinstance(channels, (str, bytes)):
        raise ReportInputContractError(
            "'channels' harus berupa list channel, bukan satu string."
        )

    normalized: list[str] = []
    seen: set[str] = set()

    for channel in channels:
        if not isinstance(channel, str):
            raise ReportInputContractError(
                "Setiap value pada 'channels' harus berupa string."
            )

        cleaned = channel.strip()
        if not cleaned:
            continue

        dedupe_key = cleaned.casefold()
        if dedupe_key not in seen:
            normalized.append(cleaned)
            seen.add(dedupe_key)

    return normalized


def _ensure_json_like(value: Any, field_name: str) -> None:
    """
    Validate that output is composed of JSON-safe primitives, mappings, and lists.

    We keep this explicit because every report input will eventually be saved,
    returned by MCP, and consumed by Task 2.
    """
    primitive_types = (str, int, float, bool, type(None))

    if isinstance(value, primitive_types):
        return

    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ReportInputContractError(
                    f"{field_name} memiliki key non-string: {key!r}."
                )
            _ensure_json_like(item, f"{field_name}.{key}")
        return

    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _ensure_json_like(item, f"{field_name}[{index}]")
        return

    raise ReportInputContractError(
        f"{field_name} berisi tipe yang tidak JSON-safe: {type(value).__name__}."
    )


def create_report_input_id(report_type_id: str) -> str:
    """
    Create a readable, collision-resistant ID.

    Example:
    ri_daily_social_media_report_20260707T143001Z_1a2b3c4d
    """
    safe_report_type = _require_text(report_type_id, "report_type_id").replace(
        " ", "_"
    )
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"ri_{safe_report_type}_{timestamp}_{uuid4().hex[:8]}"


def create_report_input(
    *,
    report_type_id: str,
    project_name: str,
    start_date: str,
    end_date: str,
    timezone_name: str = DEFAULT_TIMEZONE,
    channels: Iterable[str] | None = None,
    data_scope: str = "brand",
    registry_version: str = DEFAULT_REGISTRY_VERSION,
    client_brand: str | None = None,
    competitor_brands: Iterable[str] | None = None,
    analysis_objective: str | None = None,
    confirmed_intent_id: str | None = None,
    scope: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create an empty, valid shared package for Task 1 builders.

    A builder must add report-specific qt_* and ql_* views later through
    `add_view()`. The initial validation status is PARTIAL_PASS because no
    report-specific required views have been built yet.
    """
    report_type_id = _require_text(report_type_id, "report_type_id")
    project_name = _require_text(project_name, "project_name")
    start_date = _validate_iso_date(start_date, "start_date")
    end_date = _validate_iso_date(end_date, "end_date")

    if start_date > end_date:
        raise ReportInputContractError(
            "'start_date' tidak boleh lebih akhir dari 'end_date'."
        )

    timezone_name = _require_text(timezone_name, "timezone_name")
    data_scope = _require_text(data_scope, "data_scope")
    registry_version = _require_text(registry_version, "registry_version")

    normalized_competitors = _normalize_channels(competitor_brands)
    normalized_scope = deepcopy(dict(scope or {}))
    _ensure_json_like(normalized_scope, "scope")

    context: dict[str, Any] = {
        "project_name": project_name,
        "period": {
            "start_date": start_date,
            "end_date": end_date,
        },
        "timezone": timezone_name,
        "channels": _normalize_channels(channels),
        "data_scope": data_scope,
        "client_brand": client_brand.strip() if isinstance(client_brand, str) else None,
        "competitor_brands": normalized_competitors,
        "analysis_objective": (
            analysis_objective.strip()
            if isinstance(analysis_objective, str) and analysis_objective.strip()
            else None
        ),
        "confirmed_intent_id": (
            confirmed_intent_id.strip()
            if isinstance(confirmed_intent_id, str) and confirmed_intent_id.strip()
            else None
        ),
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "report_input_id": create_report_input_id(report_type_id),
        "report_type_id": report_type_id,
        "registry_version": registry_version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "context": context,
        "scope": normalized_scope,
        "metric_readiness": {},
        "data_health": {},
        "validation": {
            "status": "PARTIAL_PASS",
            "missing_views": [],
            "warnings": [],
            "errors": [],
        },
        "quantitative_views": {},
        "qualitative_views": {},
        "limitations": [],
        "evidence_log": [],
    }


def add_view(
    report_input: dict[str, Any],
    *,
    view_id: str,
    view_type: str,
    rows: Iterable[Mapping[str, Any]],
    metadata: Mapping[str, Any] | None = None,
    replace_existing: bool = False,
) -> None:
    """
    Add one logical view to a report input package.

    All views use the same wrapper:

    {
      "view_id": "qt_dsm_kpi_summary",
      "view_type": "quantitative",
      "rows": [{...}],
      "metadata": {...}
    }

    `rows` is always a list of dictionaries, even for a one-row KPI summary.
    """
    validate_report_input_shape(report_input, raise_on_error=True)

    view_id = _require_text(view_id, "view_id")
    view_type = _require_text(view_type, "view_type").casefold()

    if view_type not in VIEW_TYPES:
        raise ReportInputContractError(
            f"'view_type' harus salah satu dari {sorted(VIEW_TYPES)}."
        )

    expected_prefix = "qt_" if view_type == "quantitative" else "ql_"
    if not view_id.startswith(expected_prefix):
        raise ReportInputContractError(
            f"View '{view_id}' harus memakai prefix '{expected_prefix}'."
        )

    if isinstance(rows, (str, bytes, Mapping)):
        raise ReportInputContractError(
            "'rows' harus berupa iterable berisi dictionary, bukan satu object/string."
        )

    normalized_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ReportInputContractError(
                f"Row ke-{index} pada '{view_id}' harus berupa dictionary."
            )
        normalized_row = deepcopy(dict(row))
        _ensure_json_like(normalized_row, f"{view_id}.rows[{index}]")
        normalized_rows.append(normalized_row)

    normalized_metadata = deepcopy(dict(metadata or {}))
    _ensure_json_like(normalized_metadata, f"{view_id}.metadata")

    destination_key = (
        "quantitative_views"
        if view_type == "quantitative"
        else "qualitative_views"
    )
    destination = report_input[destination_key]

    if view_id in destination and not replace_existing:
        raise ReportInputContractError(
            f"View '{view_id}' sudah ada. Gunakan replace_existing=True bila "
            "memang ingin membangun ulang view tersebut."
        )

    destination[view_id] = {
        "view_id": view_id,
        "view_type": view_type,
        "rows": normalized_rows,
        "metadata": normalized_metadata,
    }


def add_warning(report_input: dict[str, Any], message: str) -> None:
    """Append one non-empty warning without silently duplicating it."""
    validate_report_input_shape(report_input, raise_on_error=True)
    message = _require_text(message, "warning")

    warnings = report_input["validation"]["warnings"]
    if message not in warnings:
        warnings.append(message)


def add_error(report_input: dict[str, Any], message: str) -> None:
    """Append one validation error and force validation status to FAIL."""
    validate_report_input_shape(report_input, raise_on_error=True)
    message = _require_text(message, "error")

    errors = report_input["validation"]["errors"]
    if message not in errors:
        errors.append(message)
    report_input["validation"]["status"] = "FAIL"


def add_limitation(report_input: dict[str, Any], message: str) -> None:
    """Record a data limitation that Task 2 may disclose in the report."""
    validate_report_input_shape(report_input, raise_on_error=True)
    message = _require_text(message, "limitation")

    limitations = report_input["limitations"]
    if message not in limitations:
        limitations.append(message)


def add_evidence(
    report_input: dict[str, Any],
    *,
    view_id: str,
    evidence_id: str,
    source_url: str | None = None,
    source_row_id: str | int | None = None,
    reason: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> None:
    """
    Register traceable source evidence.

    This log is not a replacement for ql_* views. It makes traceability explicit
    when Task 2 turns a source row into an action-plan rationale or slide proof.
    """
    validate_report_input_shape(report_input, raise_on_error=True)

    view_id = _require_text(view_id, "view_id")
    evidence_id = _require_text(evidence_id, "evidence_id")

    record: dict[str, Any] = {
        "evidence_id": evidence_id,
        "view_id": view_id,
        "source_url": source_url.strip() if isinstance(source_url, str) else None,
        "source_row_id": source_row_id,
        "reason": reason.strip() if isinstance(reason, str) else None,
        "extra": deepcopy(dict(extra or {})),
    }
    _ensure_json_like(record, "evidence_log item")

    existing_ids = {
        item.get("evidence_id")
        for item in report_input["evidence_log"]
        if isinstance(item, Mapping)
    }
    if evidence_id in existing_ids:
        raise ReportInputContractError(
            f"evidence_id '{evidence_id}' sudah dipakai."
        )

    report_input["evidence_log"].append(record)


def set_validation(
    report_input: dict[str, Any],
    *,
    status: str,
    missing_views: Iterable[str] | None = None,
    warnings: Iterable[str] | None = None,
    errors: Iterable[str] | None = None,
) -> None:
    """Set validation output after a report-specific builder has completed."""
    validate_report_input_shape(report_input, raise_on_error=True)

    status = _require_text(status, "status").upper()
    if status not in VALIDATION_STATUSES:
        raise ReportInputContractError(
            f"'status' harus salah satu dari {sorted(VALIDATION_STATUSES)}."
        )

    normalized_missing = _normalize_view_ids(missing_views or [])
    normalized_warnings = _normalize_messages(warnings or [], "warning")
    normalized_errors = _normalize_messages(errors or [], "error")

    if normalized_errors and status != "FAIL":
        raise ReportInputContractError(
            "Status validation harus FAIL bila terdapat error."
        )

    report_input["validation"] = {
        "status": status,
        "missing_views": normalized_missing,
        "warnings": normalized_warnings,
        "errors": normalized_errors,
    }


def _normalize_view_ids(view_ids: Iterable[str]) -> list[str]:
    if isinstance(view_ids, (str, bytes)):
        raise ReportInputContractError(
            "missing_views harus berupa iterable, bukan satu string."
        )

    normalized: list[str] = []
    for view_id in view_ids:
        cleaned = _require_text(view_id, "missing_view")
        if cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


def _normalize_messages(messages: Iterable[str], label: str) -> list[str]:
    if isinstance(messages, (str, bytes)):
        raise ReportInputContractError(
            f"{label} harus berupa iterable, bukan satu string."
        )

    normalized: list[str] = []
    for message in messages:
        cleaned = _require_text(message, label)
        if cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


def validate_report_input_shape(
    report_input: Mapping[str, Any],
    *,
    raise_on_error: bool = False,
) -> list[str]:
    """
    Validate shared package shape only.

    It does not validate report-specific required qt_*/ql_* views. That belongs
    in the registry-aware validator added later.
    """
    errors: list[str] = []

    if not isinstance(report_input, Mapping):
        errors.append("Report input harus berupa dictionary.")
    else:
        missing_keys = REQUIRED_TOP_LEVEL_KEYS - set(report_input.keys())
        if missing_keys:
            errors.append(
                "Top-level key wajib tidak ditemukan: "
                + ", ".join(sorted(missing_keys))
            )

        if report_input.get("schema_version") != SCHEMA_VERSION:
            errors.append(
                f"schema_version harus '{SCHEMA_VERSION}'."
            )

        if not isinstance(report_input.get("context"), Mapping):
            errors.append("'context' harus berupa dictionary.")
        else:
            missing_context = REQUIRED_CONTEXT_KEYS - set(
                report_input["context"].keys()
            )
            if missing_context:
                errors.append(
                    "Context key wajib tidak ditemukan: "
                    + ", ".join(sorted(missing_context))
                )

        validation = report_input.get("validation")
        if not isinstance(validation, Mapping):
            errors.append("'validation' harus berupa dictionary.")
        elif validation.get("status") not in VALIDATION_STATUSES:
            errors.append(
                "validation.status harus PASS, PARTIAL_PASS, atau FAIL."
            )

        for key in ("quantitative_views", "qualitative_views"):
            if not isinstance(report_input.get(key), Mapping):
                errors.append(f"'{key}' harus berupa dictionary.")

        for key in ("limitations", "evidence_log"):
            if not isinstance(report_input.get(key), list):
                errors.append(f"'{key}' harus berupa list.")

    if errors and raise_on_error:
        raise ReportInputContractError(" | ".join(errors))

    return errors


__all__ = [
    "DEFAULT_REGISTRY_VERSION",
    "DEFAULT_TIMEZONE",
    "REQUIRED_CONTEXT_KEYS",
    "REQUIRED_TOP_LEVEL_KEYS",
    "ReportInputContractError",
    "SCHEMA_VERSION",
    "VALIDATION_STATUSES",
    "VIEW_TYPES",
    "add_evidence",
    "add_error",
    "add_limitation",
    "add_view",
    "add_warning",
    "create_report_input",
    "create_report_input_id",
    "set_validation",
    "validate_report_input_shape",
]
