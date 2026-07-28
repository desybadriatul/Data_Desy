"""
Registry-aware validation for Cogan Task 1 report-input packages.

This validator answers two separate questions:
1. Does the package follow the shared report_input_v1 contract?
2. Does the package contain the qt_* and ql_* views required by the selected
   report type in the Action-Plan-First registry?

It does not validate business conclusions or Action Plan wording. Those belong
to Task 2 / final report QA.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from reporting.contracts.report_input_contract_v1 import (
    ReportInputContractError,
    VALIDATION_STATUSES,
    set_validation,
    validate_report_input_shape,
)
from reporting.registry.registry_loader import (
    RegistryError,
    get_report_input_requirements,
    get_required_view_ids,
)


VIEW_STATUS_READY = "READY"
VIEW_STATUS_NA = "N_A"
VIEW_STATUS_NOT_AVAILABLE = "NOT_AVAILABLE"
KNOWN_VIEW_STATUSES = frozenset(
    {
        VIEW_STATUS_READY,
        VIEW_STATUS_NA,
        VIEW_STATUS_NOT_AVAILABLE,
    }
)

EVIDENCE_TRACEABILITY_FIELDS = frozenset(
    {
        "source_url",
        "link_url",
        "url",
        "source_row_id",
        "source_id",
        "evidence_id",
        "content",
        "title",
    }
)


class ReportInputValidationError(ValueError):
    """Raised when validation cannot be applied to a malformed package."""


def _add_unique(items: list[str], message: str) -> None:
    """Append a message once while preserving occurrence order."""
    if message not in items:
        items.append(message)


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _view_status(view: Mapping[str, Any]) -> str:
    """
    Read optional view metadata status.

    A Task 1 builder may return an empty view only when it is explicit that the
    source was unavailable. This lets Task 2 render N/A instead of inventing a
    table/chart.
    """
    metadata = _as_mapping(view.get("metadata")) or {}
    raw_status = metadata.get("status", VIEW_STATUS_READY)

    if not isinstance(raw_status, str):
        return "INVALID"

    return raw_status.strip().upper()


def _has_traceable_evidence(row: Mapping[str, Any]) -> bool:
    """
    A qualitative row must contain at least one traceability anchor.

    Content/title is accepted as a fallback because some source systems do not
    supply stable URL/row IDs. Builders should still include source_url or
    source_row_id whenever such data exists.
    """
    for key, value in row.items():
        if key.casefold() not in EVIDENCE_TRACEABILITY_FIELDS:
            continue
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return True
    return False


def _inspect_view(
    *,
    view_id: str,
    expected_type: str,
    view: Any,
) -> dict[str, Any]:
    """Validate one qt_* / ql_* wrapper without interpreting its metrics."""
    errors: list[str] = []
    warnings: list[str] = []
    rows_count = 0
    status = "FAIL"

    if not isinstance(view, Mapping):
        return {
            "view_id": view_id,
            "expected_type": expected_type,
            "status": status,
            "rows_count": rows_count,
            "errors": [f"{view_id}: wrapper view harus berupa dictionary."],
            "warnings": warnings,
        }

    actual_view_id = view.get("view_id")
    if actual_view_id != view_id:
        _add_unique(
            errors,
            f"{view_id}: field view_id harus persis '{view_id}'.",
        )

    actual_type = view.get("view_type")
    if actual_type != expected_type:
        _add_unique(
            errors,
            f"{view_id}: view_type harus '{expected_type}', bukan "
            f"'{actual_type}'.",
        )

    rows = view.get("rows")
    if not isinstance(rows, list):
        _add_unique(errors, f"{view_id}: rows harus berupa list.")
        rows = []
    else:
        rows_count = len(rows)
        for index, row in enumerate(rows):
            if not isinstance(row, Mapping):
                _add_unique(
                    errors,
                    f"{view_id}: rows[{index}] harus berupa dictionary.",
                )

    metadata = view.get("metadata")
    if not isinstance(metadata, Mapping):
        _add_unique(errors, f"{view_id}: metadata harus berupa dictionary.")
        metadata = {}

    declared_status = _view_status(view)
    if declared_status == "INVALID":
        _add_unique(
            errors,
            f"{view_id}: metadata.status harus string bila diisi.",
        )
    elif declared_status not in KNOWN_VIEW_STATUSES:
        _add_unique(
            errors,
            f"{view_id}: metadata.status harus salah satu dari "
            f"{sorted(KNOWN_VIEW_STATUSES)}.",
        )

    if rows_count == 0:
        if declared_status == VIEW_STATUS_READY:
            _add_unique(
                warnings,
                f"{view_id}: tidak memiliki rows. Gunakan metadata.status='N_A' "
                "atau 'NOT_AVAILABLE' bila memang tidak ada data.",
            )
        else:
            _add_unique(
                warnings,
                f"{view_id}: data tidak tersedia ({declared_status}).",
            )

    if expected_type == "qualitative" and rows_count > 0:
        untraceable_rows = [
            index
            for index, row in enumerate(rows)
            if isinstance(row, Mapping) and not _has_traceable_evidence(row)
        ]
        if untraceable_rows:
            preview = ", ".join(str(index) for index in untraceable_rows[:5])
            _add_unique(
                warnings,
                f"{view_id}: {len(untraceable_rows)} qualitative row tidak punya "
                "source/link/ID/content/title yang bisa ditelusuri "
                f"(contoh index: {preview}).",
            )

    if errors:
        status = "FAIL"
    elif warnings:
        status = "WARN"
    else:
        status = "PASS"

    return {
        "view_id": view_id,
        "expected_type": expected_type,
        "status": status,
        "rows_count": rows_count,
        "declared_data_status": declared_status,
        "errors": errors,
        "warnings": warnings,
    }


def validate_report_input(
    report_input: Mapping[str, Any],
    *,
    registry_dir: str | None = None,
) -> dict[str, Any]:
    """
    Validate a Task 1 output package against contract + registry.

    Result statuses:
    - PASS: all required views exist; no structural error; no warnings.
    - PARTIAL_PASS: required views exist, but documented N/A views or warnings
      remain. Task 2 may continue only with limitations/caveats.
    - FAIL: malformed contract, unsupported/missing required view, unknown
      report type, or missing minimum viable view.

    This function is non-mutating. Use `apply_validation_result()` after a
    builder finishes and the result is accepted.
    """
    contract_errors = validate_report_input_shape(report_input)
    result: dict[str, Any] = {
        "status": "FAIL",
        "report_type_id": None,
        "registry_version": None,
        "required_views": {
            "quantitative": [],
            "qualitative": [],
            "minimum_viable": [],
        },
        "present_views": {
            "quantitative": [],
            "qualitative": [],
        },
        "missing_views": [],
        "missing_minimum_viable_views": [],
        "unsupported_views": [],
        "view_checks": {},
        "warnings": [],
        "errors": list(contract_errors),
    }

    if contract_errors:
        return result

    report_type_id = report_input["report_type_id"]
    result["report_type_id"] = report_type_id

    try:
        requirements = get_report_input_requirements(
            report_type_id,
            registry_dir=registry_dir,
        )
        required_quantitative = get_required_view_ids(
            report_type_id,
            view_type="quantitative",
            registry_dir=registry_dir,
        )
        required_qualitative = get_required_view_ids(
            report_type_id,
            view_type="qualitative",
            registry_dir=registry_dir,
        )
    except RegistryError as exc:
        _add_unique(result["errors"], str(exc))
        return result

    result["registry_version"] = requirements["registry_version"]
    result["required_views"] = {
        "quantitative": required_quantitative,
        "qualitative": required_qualitative,
        "minimum_viable": list(requirements["minimum_viable_inputs"]),
    }

    quantitative_views = report_input["quantitative_views"]
    qualitative_views = report_input["qualitative_views"]
    present_quantitative = list(quantitative_views.keys())
    present_qualitative = list(qualitative_views.keys())

    result["present_views"] = {
        "quantitative": present_quantitative,
        "qualitative": present_qualitative,
    }

    allowed_quantitative = set(required_quantitative)
    allowed_qualitative = set(required_qualitative)

    missing_quantitative = [
        view_id
        for view_id in required_quantitative
        if view_id not in quantitative_views
    ]
    missing_qualitative = [
        view_id
        for view_id in required_qualitative
        if view_id not in qualitative_views
    ]
    result["missing_views"] = missing_quantitative + missing_qualitative

    all_present_view_ids = set(present_quantitative) | set(present_qualitative)
    result["missing_minimum_viable_views"] = [
        view_id
        for view_id in requirements["minimum_viable_inputs"]
        if view_id not in all_present_view_ids
    ]

    for view_id in present_quantitative:
        if view_id not in allowed_quantitative:
            result["unsupported_views"].append(view_id)
            _add_unique(
                result["errors"],
                f"{view_id}: quantitative view tidak terdaftar untuk "
                f"{report_type_id}.",
            )
            continue

        check = _inspect_view(
            view_id=view_id,
            expected_type="quantitative",
            view=quantitative_views[view_id],
        )
        result["view_checks"][view_id] = check
        for message in check["errors"]:
            _add_unique(result["errors"], message)
        for message in check["warnings"]:
            _add_unique(result["warnings"], message)

    for view_id in present_qualitative:
        if view_id not in allowed_qualitative:
            result["unsupported_views"].append(view_id)
            _add_unique(
                result["errors"],
                f"{view_id}: qualitative view tidak terdaftar untuk "
                f"{report_type_id}.",
            )
            continue

        check = _inspect_view(
            view_id=view_id,
            expected_type="qualitative",
            view=qualitative_views[view_id],
        )
        result["view_checks"][view_id] = check
        for message in check["errors"]:
            _add_unique(result["errors"], message)
        for message in check["warnings"]:
            _add_unique(result["warnings"], message)

    if result["missing_minimum_viable_views"]:
        _add_unique(
            result["errors"],
            "Minimum viable view belum tersedia: "
            + ", ".join(result["missing_minimum_viable_views"]),
        )

    if result["missing_views"]:
        _add_unique(
            result["warnings"],
            "Required view belum dibangun dan harus tercatat sebagai N/A atau "
            "diisi sebelum final report: "
            + ", ".join(result["missing_views"]),
        )

    if not isinstance(report_input.get("metric_readiness"), Mapping) or not report_input[
        "metric_readiness"
    ]:
        _add_unique(
            result["warnings"],
            "metric_readiness belum diisi. Interactions/views belum boleh "
            "menjadi KPI utama sampai readiness tersedia.",
        )

    if not isinstance(report_input.get("data_health"), Mapping) or not report_input[
        "data_health"
    ]:
        _add_unique(
            result["warnings"],
            "data_health belum diisi. Coverage dan canonical scope belum "
            "terdokumentasi.",
        )

    if result["errors"]:
        result["status"] = "FAIL"
    elif result["warnings"]:
        result["status"] = "PARTIAL_PASS"
    else:
        result["status"] = "PASS"

    return result


def apply_validation_result(
    report_input: dict[str, Any],
    validation_result: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Copy a validator result into the shared package's validation field.

    This must be called only after `validate_report_input()` returns. The
    registry-specific diagnostic remains available separately for debug/test,
    while the package stores the compact universally agreed contract shape.
    """
    if not isinstance(validation_result, Mapping):
        raise ReportInputValidationError(
            "validation_result harus berupa dictionary."
        )

    status = validation_result.get("status")
    if status not in VALIDATION_STATUSES:
        raise ReportInputValidationError(
            "validation_result.status tidak valid."
        )

    set_validation(
        report_input,
        status=status,
        missing_views=validation_result.get("missing_views", []),
        warnings=validation_result.get("warnings", []),
        errors=validation_result.get("errors", []),
    )
    return report_input


def validate_and_apply(
    report_input: dict[str, Any],
    *,
    registry_dir: str | None = None,
) -> dict[str, Any]:
    """Validate a report input and write the compact validation result into it."""
    result = validate_report_input(report_input, registry_dir=registry_dir)
    try:
        apply_validation_result(report_input, result)
    except ReportInputContractError as exc:
        raise ReportInputValidationError(
            "Hasil validation tidak dapat diterapkan ke report input: "
            f"{exc}"
        ) from exc
    return result


def get_missing_required_views(
    report_input: Mapping[str, Any],
    *,
    registry_dir: str | None = None,
) -> list[str]:
    """Convenience helper for builder tests and MCP response summaries."""
    result = validate_report_input(report_input, registry_dir=registry_dir)
    return list(result["missing_views"])


__all__ = [
    "EVIDENCE_TRACEABILITY_FIELDS",
    "KNOWN_VIEW_STATUSES",
    "ReportInputValidationError",
    "VIEW_STATUS_NA",
    "VIEW_STATUS_NOT_AVAILABLE",
    "VIEW_STATUS_READY",
    "apply_validation_result",
    "get_missing_required_views",
    "validate_and_apply",
    "validate_report_input",
]
