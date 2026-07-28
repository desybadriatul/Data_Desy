"""
Generic Task 1 dispatcher for Cogan report-input builders.

This is the single routing point behind the future MCP feature:
    prepare_report_input(report_type_id=..., request=...)

It does not contain aggregation logic. Each report-specific module owns only its
own builder under `reporting.task1.builders/`, while this dispatcher chooses the
correct builder from the shared registry-supported route map.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import importlib
from pathlib import Path
from typing import Any

from reporting.registry.registry_loader import (
    RegistryError,
    get_report_type_definition,
    list_report_types,
)
from reporting.task1.base_builder import (
    BaseReportInputBuilder,
    BuildRequest,
    ReportBuildError,
)


# This map is created once in shared foundation. It is intentionally complete:
# report owners replace only the corresponding builder file; they do not edit
# this dispatcher or server.py.
BUILDER_MODULES: dict[str, str] = {
    "competitive_analysis": (
        "reporting.task1.builders.competitive_analysis"
    ),
    "industry_trend": (
        "reporting.task1.builders.industry_trend_report"
    ),
    "daily_social_media_report": (
        "reporting.task1.builders.daily_social_media_report"
    ),
    "brand_content_effectiveness": (
        "reporting.task1.builders.brand_content_effectiveness_report"
    ),
    "spokesperson_intelligence": (
        "reporting.task1.builders.spokesperson_intelligence_report"
    ),
    "mainstream_media_report": (
        "reporting.task1.builders.mainstream_media_report"
    ),
    "evo_perception_intelligence": (
        "reporting.task1.builders.evo_perception_intelligence"
    ),
}

BUILDER_CLASS_EXPORT = "BUILDER_CLASS"


class ReportInputDispatcherError(RuntimeError):
    """Raised when Cogan cannot safely route a Task 1 report request."""


def _require_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReportInputDispatcherError(
            f"'{field_name}' wajib berupa string yang tidak kosong."
        )
    return value.strip()


def _validate_report_type(
    report_type_id: str,
    *,
    registry_dir: str | Path | None = None,
) -> str:
    """Confirm report_type_id exists in the registry before module import."""
    report_type_id = _require_text(report_type_id, "report_type_id")

    try:
        get_report_type_definition(report_type_id, registry_dir=registry_dir)
    except RegistryError as exc:
        raise ReportInputDispatcherError(str(exc)) from exc

    if report_type_id not in BUILDER_MODULES:
        raise ReportInputDispatcherError(
            f"Belum ada route builder untuk '{report_type_id}'. "
            "Tambahkan route hanya pada shared foundation dispatcher."
        )

    return report_type_id


def get_builder(
    report_type_id: str,
    *,
    registry_dir: str | Path | None = None,
) -> BaseReportInputBuilder:
    """
    Return an instantiated builder for a registry-supported report type.

    Every concrete builder module must expose exactly one class using:
        BUILDER_CLASS = DailySocialMediaReportBuilder

    The class must inherit BaseReportInputBuilder and declare a matching
    `report_type_id`.
    """
    report_type_id = _validate_report_type(
        report_type_id,
        registry_dir=registry_dir,
    )
    module_path = BUILDER_MODULES[report_type_id]

    try:
        module = importlib.import_module(module_path)
    except Exception as exc:
        raise ReportInputDispatcherError(
            f"Gagal memuat module builder '{module_path}' untuk "
            f"'{report_type_id}': {exc}"
        ) from exc

    builder_class = getattr(module, BUILDER_CLASS_EXPORT, None)
    if builder_class is None:
        raise ReportInputDispatcherError(
            f"Builder '{report_type_id}' belum diimplementasikan. "
            f"Tambahkan `{BUILDER_CLASS_EXPORT} = NamaBuilder` pada "
            f"{module_path}."
        )

    if not isinstance(builder_class, type):
        raise ReportInputDispatcherError(
            f"{module_path}.{BUILDER_CLASS_EXPORT} harus berupa class."
        )

    if not issubclass(builder_class, BaseReportInputBuilder):
        raise ReportInputDispatcherError(
            f"{module_path}.{BUILDER_CLASS_EXPORT} harus mewarisi "
            "BaseReportInputBuilder."
        )

    declared_type = getattr(builder_class, "report_type_id", None)
    if declared_type != report_type_id:
        raise ReportInputDispatcherError(
            f"Builder di {module_path} menyatakan report_type_id "
            f"'{declared_type}', seharusnya '{report_type_id}'."
        )

    try:
        return builder_class(registry_dir=registry_dir)
    except (ReportBuildError, RegistryError) as exc:
        raise ReportInputDispatcherError(
            f"Builder '{report_type_id}' gagal diinisialisasi: {exc}"
        ) from exc
    except Exception as exc:
        raise ReportInputDispatcherError(
            f"Terjadi error saat inisialisasi builder '{report_type_id}': {exc}"
        ) from exc


def prepare_report_input(
    *,
    report_type_id: str,
    request: BuildRequest | Mapping[str, Any],
    registry_dir: str | Path | None = None,
    persist: bool = False,
    allow_fail_to_persist: bool = False,
) -> dict[str, Any]:
    """
    Build a Task 1 report-ready package through one common interface.

    This is the function that future MCP `prepare_report_input` should call.
    `request` must contain confirmed_intent_id; Task 1 does not ask users
    follow-up questions or decide report recommendations.
    """
    builder = get_builder(report_type_id, registry_dir=registry_dir)

    try:
        return builder.build(
            request,
            persist=persist,
            allow_fail_to_persist=allow_fail_to_persist,
        )
    except ReportBuildError:
        raise
    except Exception as exc:
        raise ReportInputDispatcherError(
            f"Gagal menyiapkan report input '{report_type_id}': {exc}"
        ) from exc


def builder_availability(
    *,
    registry_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    """
    Show readiness of all registry report types without executing aggregation.

    Useful for MCP health checks and team integration. A builder is READY only
    after its module exports a valid `BUILDER_CLASS`.
    """
    report_types = list_report_types(registry_dir)
    result: list[dict[str, Any]] = []

    for item in report_types:
        report_type_id = item["report_type_id"]
        module_path = BUILDER_MODULES.get(report_type_id)

        entry: dict[str, Any] = {
            "report_type_id": report_type_id,
            "display_name": item["display_name"],
            "module_path": module_path,
            "status": "NOT_IMPLEMENTED",
            "reason": None,
        }

        if not module_path:
            entry["status"] = "ROUTE_MISSING"
            entry["reason"] = "Route tidak ditemukan di shared dispatcher."
            result.append(entry)
            continue

        try:
            get_builder(report_type_id, registry_dir=registry_dir)
        except ReportInputDispatcherError as exc:
            entry["reason"] = str(exc)
        else:
            entry["status"] = "READY"

        result.append(entry)

    return result


def get_dispatcher_contract() -> dict[str, Any]:
    """
    Return a small serializable description for future MCP tool documentation.
    """
    return {
        "feature_name": "prepare_report_input",
        "required_arguments": [
            "report_type_id",
            "request.project_name",
            "request.start_date",
            "request.end_date",
            "request.confirmed_intent_id",
        ],
        "optional_arguments": [
            "request.channels",
            "request.data_scope",
            "request.client_brand",
            "request.competitor_brands",
            "request.scope",
            "request.metric_readiness",
            "request.data_health",
            "persist",
        ],
        "supported_report_type_ids": list(BUILDER_MODULES.keys()),
        "builder_module_export": BUILDER_CLASS_EXPORT,
    }


__all__ = [
    "BUILDER_CLASS_EXPORT",
    "BUILDER_MODULES",
    "ReportInputDispatcherError",
    "builder_availability",
    "get_builder",
    "get_dispatcher_contract",
    "prepare_report_input",
]
