"""
Shared base builder for Cogan Task 1 report-input packages.

Every report type builder inherits this class. The base class owns the workflow
that must stay identical across Daily Social, Mainstream Media, Competitive,
Industry Trend, Brand & Content Effectiveness, and Spokesperson Intelligence:

1. receive a confirmed analysis request;
2. create a standard report_input_v1 package;
3. attach scope, metric readiness, and data health snapshots;
4. allow the report-specific builder to create only registry-approved qt_* / ql_* views;
5. validate against the registry;
6. optionally persist the frozen package for Task 2.

A report-specific builder only implements `build_views()`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from reporting.contracts.report_input_contract_v1 import (
    ReportInputContractError,
    add_evidence,
    add_limitation,
    add_view,
    add_warning,
    create_report_input,
)
from reporting.registry.registry_loader import (
    RegistryError,
    get_report_input_requirements,
)
from reporting.validators.report_input_validator import (
    validate_and_apply,
)


DEFAULT_BUILDER_VERSION = "1.0.0"
VIEW_STATUS_READY = "READY"
VIEW_STATUS_NA = "N_A"
VIEW_STATUS_NOT_AVAILABLE = "NOT_AVAILABLE"


class ReportBuildError(RuntimeError):
    """Raised when a Task 1 builder cannot create a safe report-input package."""


@dataclass(frozen=True)
class BuildRequest:
    """
    Standard Task 1 request passed into every report-specific builder.

    This is deliberately report-agnostic. A builder may read optional context
    values, but must not silently infer missing material scope from raw data.
    """

    project_name: str
    start_date: str
    end_date: str
    confirmed_intent_id: str

    channels: tuple[str, ...] = field(default_factory=tuple)
    data_scope: str = "brand"
    timezone_name: str = "Asia/Jakarta"

    client_brand: str | None = None
    competitor_brands: tuple[str, ...] = field(default_factory=tuple)
    analysis_objective: str | None = None

    # Exact scope/filter information must be preserved for Task 2 and audit.
    scope: Mapping[str, Any] = field(default_factory=dict)

    # Snapshots come from Cogan readiness/data-health tools before aggregation.
    metric_readiness: Mapping[str, Any] = field(default_factory=dict)
    data_health: Mapping[str, Any] = field(default_factory=dict)

    # Useful when a caller wants traceability to project/campaign lookup.
    source_request_id: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.project_name, "project_name")
        _require_text(self.start_date, "start_date")
        _require_text(self.end_date, "end_date")
        _require_text(self.confirmed_intent_id, "confirmed_intent_id")
        _require_text(self.data_scope, "data_scope")
        _require_text(self.timezone_name, "timezone_name")

        if self.start_date > self.end_date:
            raise ReportBuildError(
                "start_date tidak boleh lebih akhir dari end_date."
            )

        if isinstance(self.channels, (str, bytes)):
            raise ReportBuildError(
                "channels harus tuple/list, bukan satu string."
            )
        if isinstance(self.competitor_brands, (str, bytes)):
            raise ReportBuildError(
                "competitor_brands harus tuple/list, bukan satu string."
            )
        if not isinstance(self.scope, Mapping):
            raise ReportBuildError("scope harus berupa dictionary.")
        if not isinstance(self.metric_readiness, Mapping):
            raise ReportBuildError("metric_readiness harus berupa dictionary.")
        if not isinstance(self.data_health, Mapping):
            raise ReportBuildError("data_health harus berupa dictionary.")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "BuildRequest":
        """
        Convenience constructor for future MCP tool payloads.

        `channels` and `competitor_brands` are normalized into tuples so the
        builder request is immutable during a build.
        """
        if not isinstance(payload, Mapping):
            raise ReportBuildError("Build request harus berupa dictionary.")

        return cls(
            project_name=payload.get("project_name", ""),
            start_date=payload.get("start_date", ""),
            end_date=payload.get("end_date", ""),
            confirmed_intent_id=payload.get("confirmed_intent_id", ""),
            channels=_normalize_text_tuple(payload.get("channels", ())),
            data_scope=payload.get("data_scope", "brand"),
            timezone_name=payload.get("timezone_name", "Asia/Jakarta"),
            client_brand=payload.get("client_brand"),
            competitor_brands=_normalize_text_tuple(
                payload.get("competitor_brands", ())
            ),
            analysis_objective=payload.get("analysis_objective"),
            scope=deepcopy(dict(payload.get("scope", {}))),
            metric_readiness=deepcopy(
                dict(payload.get("metric_readiness", {}))
            ),
            data_health=deepcopy(dict(payload.get("data_health", {}))),
            source_request_id=payload.get("source_request_id"),
        )


def _require_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReportBuildError(
            f"'{field_name}' wajib berupa string yang tidak kosong."
        )
    return value.strip()


def _normalize_text_tuple(values: Any) -> tuple[str, ...]:
    """Normalize arbitrary text iterable without accepting a bare string."""
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        raise ReportBuildError("Value harus list/tuple string, bukan satu string.")

    result: list[str] = []
    seen: set[str] = set()
    try:
        iterator = iter(values)
    except TypeError as exc:
        raise ReportBuildError(
            "Value harus berupa list/tuple string."
        ) from exc

    for value in iterator:
        if not isinstance(value, str):
            raise ReportBuildError("Setiap item harus berupa string.")
        cleaned = value.strip()
        if not cleaned:
            continue
        dedupe_key = cleaned.casefold()
        if dedupe_key not in seen:
            result.append(cleaned)
            seen.add(dedupe_key)

    return tuple(result)


class BaseReportInputBuilder(ABC):
    """
    Base class for every Task 1 report builder.

    Subclasses must declare `report_type_id` exactly as listed in the registry
    and implement only `build_views()`. They should use add_quantitative_view(),
    add_qualitative_view(), or mark_view_na(); do not mutate view dictionaries
    manually.
    """

    report_type_id: str = ""
    builder_version: str = DEFAULT_BUILDER_VERSION

    def __init__(
        self,
        *,
        registry_dir: str | Path | None = None,
    ) -> None:
        self.registry_dir = registry_dir
        self._requirements = self._load_requirements()

    def _load_requirements(self) -> dict[str, Any]:
        report_type_id = _require_text(self.report_type_id, "report_type_id")
        try:
            return get_report_input_requirements(
                report_type_id,
                registry_dir=self.registry_dir,
            )
        except RegistryError as exc:
            raise ReportBuildError(
                f"Builder '{report_type_id}' tidak dapat membaca registry: {exc}"
            ) from exc

    @property
    def requirements(self) -> dict[str, Any]:
        """Read-only-copy of current report requirements from registry."""
        return deepcopy(self._requirements)

    @property
    def quantitative_view_ids(self) -> tuple[str, ...]:
        return tuple(
            item["input_id"] for item in self._requirements["quantitative"]
        )

    @property
    def qualitative_view_ids(self) -> tuple[str, ...]:
        return tuple(
            item["input_id"] for item in self._requirements["qualitative"]
        )

    @property
    def required_view_ids(self) -> tuple[str, ...]:
        return self.quantitative_view_ids + self.qualitative_view_ids

    def build(
        self,
        request: BuildRequest | Mapping[str, Any],
        *,
        persist: bool = False,
        allow_fail_to_persist: bool = False,
    ) -> dict[str, Any]:
        """
        Create one report-ready Task 1 package.

        A builder can return PARTIAL_PASS when the registry-approved N/A views
        are explicitly documented. It must not silently return invalid/missing
        views. Failed packages are not persisted unless the caller explicitly
        opts in for debugging.
        """
        build_request = self._coerce_request(request)
        report_input = self._create_base_package(build_request)

        try:
            self.build_views(report_input, build_request)
        except (ReportBuildError, ReportInputContractError):
            raise
        except Exception as exc:
            raise ReportBuildError(
                f"Gagal membangun view untuk '{self.report_type_id}': {exc}"
            ) from exc

        validation_result = validate_and_apply(
            report_input,
            registry_dir=self.registry_dir,
        )
        report_input["builder"] = {
            "report_type_id": self.report_type_id,
            "builder_version": self.builder_version,
            "validation_status": validation_result["status"],
        }

        if persist:
            if (
                validation_result["status"] == "FAIL"
                and not allow_fail_to_persist
            ):
                raise ReportBuildError(
                    "Report input FAIL tidak disimpan. Perbaiki view/contract "
                    "atau gunakan allow_fail_to_persist=True hanya untuk debug."
                )
            self.persist(report_input)

        return report_input

    @abstractmethod
    def build_views(
        self,
        report_input: dict[str, Any],
        request: BuildRequest,
    ) -> None:
        """
        Build all registry-approved qt_* and ql_* views.

        Subclasses should either:
        - add a populated view with metadata.status='READY'; or
        - use mark_view_na() / mark_view_not_available() with a clear reason.

        Never silently omit a required view.
        """

    def _coerce_request(
        self,
        request: BuildRequest | Mapping[str, Any],
    ) -> BuildRequest:
        if isinstance(request, BuildRequest):
            return request
        if isinstance(request, Mapping):
            return BuildRequest.from_mapping(request)
        raise ReportBuildError(
            "request harus BuildRequest atau dictionary."
        )

    def _create_base_package(
        self,
        request: BuildRequest,
    ) -> dict[str, Any]:
        builder_scope = deepcopy(dict(request.scope))
        builder_scope["confirmed_intent_id"] = request.confirmed_intent_id
        builder_scope["source_request_id"] = request.source_request_id
        builder_scope["report_input_builder"] = {
            "report_type_id": self.report_type_id,
            "builder_version": self.builder_version,
            "registry_version": self._requirements["registry_version"],
        }

        report_input = create_report_input(
            report_type_id=self.report_type_id,
            project_name=request.project_name,
            start_date=request.start_date,
            end_date=request.end_date,
            timezone_name=request.timezone_name,
            channels=request.channels,
            data_scope=request.data_scope,
            registry_version=self._requirements["registry_version"],
            client_brand=request.client_brand,
            competitor_brands=request.competitor_brands,
            analysis_objective=request.analysis_objective,
            confirmed_intent_id=request.confirmed_intent_id,
            scope=builder_scope,
        )

        report_input["metric_readiness"] = deepcopy(
            dict(request.metric_readiness)
        )
        report_input["data_health"] = deepcopy(dict(request.data_health))

        if not request.metric_readiness:
            add_warning(
                report_input,
                "metric_readiness belum diteruskan ke builder."
            )
        if not request.data_health:
            add_warning(
                report_input,
                "data_health belum diteruskan ke builder."
            )

        return report_input

    def add_quantitative_view(
        self,
        report_input: dict[str, Any],
        *,
        view_id: str,
        rows: Iterable[Mapping[str, Any]],
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """Add a registry-approved qt_* view."""
        self._assert_allowed_view(view_id, "quantitative")
        add_view(
            report_input,
            view_id=view_id,
            view_type="quantitative",
            rows=rows,
            metadata=self._metadata_with_defaults(
                metadata,
                status=VIEW_STATUS_READY,
            ),
        )

    def add_qualitative_view(
        self,
        report_input: dict[str, Any],
        *,
        view_id: str,
        rows: Iterable[Mapping[str, Any]],
        metadata: Mapping[str, Any] | None = None,
        evidence_reason: str | None = None,
    ) -> None:
        """
        Add a registry-approved ql_* view and log traceable evidence rows.

        The source row itself remains inside the view. The evidence log gives
        Task 2 a compact traceability index without re-reading all raw posts.
        """
        self._assert_allowed_view(view_id, "qualitative")
        normalized_rows = [deepcopy(dict(row)) for row in rows]

        add_view(
            report_input,
            view_id=view_id,
            view_type="qualitative",
            rows=normalized_rows,
            metadata=self._metadata_with_defaults(
                metadata,
                status=VIEW_STATUS_READY,
            ),
        )

        for index, row in enumerate(normalized_rows):
            evidence_id = (
                str(row.get("evidence_id") or "")
                or f"{view_id}:{index + 1}"
            )
            source_url = self._first_text(
                row,
                ("source_url", "link_url", "url", "Link URL"),
            )
            source_row_id = (
                row.get("source_row_id")
                or row.get("source_id")
                or row.get("post_id")
                or row.get("id")
            )

            add_evidence(
                report_input,
                view_id=view_id,
                evidence_id=evidence_id,
                source_url=source_url,
                source_row_id=source_row_id,
                reason=evidence_reason,
                extra={
                    "channel": row.get("channel") or row.get("Channel"),
                    "author": row.get("author") or row.get("Author"),
                    "sentiment": row.get("sentiment") or row.get("Sentiment"),
                },
            )

    def mark_view_na(
        self,
        report_input: dict[str, Any],
        *,
        view_id: str,
        view_type: str,
        reason: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """
        Add an explicit N/A view.

        Use when the registry requires the view but the project/source does not
        contain enough valid data. This is better than omitting the view because
        Task 2 can render N/A and disclose the limitation.
        """
        self._assert_allowed_view(view_id, view_type)
        reason = _require_text(reason, "reason")
        merged_metadata = self._metadata_with_defaults(
            metadata,
            status=VIEW_STATUS_NA,
        )
        merged_metadata["reason"] = reason

        add_view(
            report_input,
            view_id=view_id,
            view_type=view_type,
            rows=[],
            metadata=merged_metadata,
        )
        add_limitation(report_input, f"{view_id}: {reason}")

    def mark_view_not_available(
        self,
        report_input: dict[str, Any],
        *,
        view_id: str,
        view_type: str,
        reason: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """
        Add a view explicitly unavailable because source field/tool is missing.
        """
        self._assert_allowed_view(view_id, view_type)
        reason = _require_text(reason, "reason")
        merged_metadata = self._metadata_with_defaults(
            metadata,
            status=VIEW_STATUS_NOT_AVAILABLE,
        )
        merged_metadata["reason"] = reason

        add_view(
            report_input,
            view_id=view_id,
            view_type=view_type,
            rows=[],
            metadata=merged_metadata,
        )
        add_limitation(report_input, f"{view_id}: {reason}")

    def persist(self, report_input: Mapping[str, Any]) -> dict[str, Any]:
        """
        Persist the package only when the caller explicitly chooses `persist=True`.
        """
        try:
            from reporting.storage.report_input_store import save_report_input
        except ImportError as exc:
            raise ReportBuildError(
                "Storage report input belum tersedia."
            ) from exc

        try:
            storage_result = save_report_input(report_input)
        except Exception as exc:
            raise ReportBuildError(
                f"Gagal menyimpan report input: {exc}"
            ) from exc

        if not isinstance(report_input, dict):
            raise ReportBuildError(
                "report_input harus dictionary agar storage metadata dapat dicatat."
            )

        report_input["storage"] = {
            "saved": True,
            "report_input_id": storage_result["report_input_id"],
            "saved_at": str(storage_result["updated_at"]),
        }
        return storage_result

    def _assert_allowed_view(
        self,
        view_id: str,
        view_type: str,
    ) -> None:
        view_id = _require_text(view_id, "view_id")
        view_type = _require_text(view_type, "view_type").casefold()

        if view_type == "quantitative":
            allowed = self.quantitative_view_ids
            expected_prefix = "qt_"
        elif view_type == "qualitative":
            allowed = self.qualitative_view_ids
            expected_prefix = "ql_"
        else:
            raise ReportBuildError(
                "view_type harus 'quantitative' atau 'qualitative'."
            )

        if not view_id.startswith(expected_prefix):
            raise ReportBuildError(
                f"{view_id}: prefix harus '{expected_prefix}'."
            )
        if view_id not in allowed:
            raise ReportBuildError(
                f"{view_id}: tidak terdaftar untuk report type "
                f"'{self.report_type_id}'."
            )

    def _metadata_with_defaults(
        self,
        metadata: Mapping[str, Any] | None,
        *,
        status: str,
    ) -> dict[str, Any]:
        result = deepcopy(dict(metadata or {}))
        result.setdefault("status", status)
        result.setdefault("builder_version", self.builder_version)
        result.setdefault("registry_version", self._requirements["registry_version"])
        return result

    @staticmethod
    def _first_text(
        row: Mapping[str, Any],
        candidates: Iterable[str],
    ) -> str | None:
        for field_name in candidates:
            value = row.get(field_name)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None


__all__ = [
    "BaseReportInputBuilder",
    "BuildRequest",
    "DEFAULT_BUILDER_VERSION",
    "ReportBuildError",
    "VIEW_STATUS_NA",
    "VIEW_STATUS_NOT_AVAILABLE",
    "VIEW_STATUS_READY",
]
