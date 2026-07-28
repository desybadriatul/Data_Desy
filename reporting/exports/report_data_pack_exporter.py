"""
Report Data Pack exporter for Cogan Task 1 packages.

Purpose:
- Give users an audit trail for a generated report.
- Export all Task 1 qt_*/ql_* views, limitations, evidence log, and optionally
  raw canonical source rows for the exact report scope.
- Prefer Excel multi-sheet output; fall back to CSV ZIP if openpyxl is not
  available in the runtime.

This module is intentionally report-type agnostic. It can export Daily Social,
Mainstream Media, and future report types as long as they follow
`report_input_v1`.
"""

from __future__ import annotations

import base64
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO, StringIO
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping
from zipfile import ZIP_DEFLATED, ZipFile

from reporting.storage.report_input_store import (
    ReportInputStoreError,
    get_report_input,
)


EXPORT_DIR = Path("exports/report_data_packs")
MAX_XLSX_ROWS = 1_000_000
MAX_BASE64_BYTES_DEFAULT = 4_000_000
COGAN_PREFIX = "_cogan_"

SOCIAL_CHANNELS = {
    "facebook",
    "fb",
    "forum",
    "instagram",
    "ig",
    "tiktok",
    "tik tok",
    "twitter",
    "x",
    "youtube",
    "yt",
}
MAINSTREAM_CHANNELS = {
    "online media",
    "online_media",
    "online",
    "news",
    "printmedia",
    "print media",
    "print_media",
    "print",
    "tv",
    "television",
    "radio",
}


class ReportDataPackExportError(RuntimeError):
    """Raised when an export cannot be built safely."""


@dataclass(frozen=True)
class SheetSpec:
    name: str
    columns: list[str]
    rows: list[dict[str, Any]]
    source: str
    truncated: bool = False
    original_row_count: int | None = None


# ---------------------------------------------------------------------------
# Basic normalization helpers
# ---------------------------------------------------------------------------
def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _slug(value: str, max_len: int = 80) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", _text(value)).strip("_")
    return (cleaned or "export")[:max_len]


def _sheet_name(value: str, used: set[str]) -> str:
    cleaned = re.sub(r"[\\/*?:\[\]]", "_", _text(value))
    cleaned = re.sub(r"\s+", " ", cleaned).strip() or "Sheet"
    cleaned = cleaned[:31]

    candidate = cleaned
    index = 2
    while candidate in used:
        suffix = f"_{index}"
        candidate = cleaned[: 31 - len(suffix)] + suffix
        index += 1
    used.add(candidate)
    return candidate


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return str(value)


def _cell_value(value: Any) -> Any:
    value = _json_safe(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def _rows_from_mapping(mapping: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [{"field": key, "value": _json_safe(value)} for key, value in mapping.items()]


def _row_columns(rows: Iterable[Mapping[str, Any]]) -> list[str]:
    columns: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            key_text = str(key)
            if key_text not in seen:
                seen.add(key_text)
                columns.append(key_text)
    return columns


def _normalize_rows(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows or []:
        if isinstance(row, Mapping):
            output.append({str(key): _json_safe(value) for key, value in row.items()})
    return output


def _truncate_rows(rows: list[dict[str, Any]], limit: int | None) -> tuple[list[dict[str, Any]], bool, int]:
    original_count = len(rows)
    if limit is None or limit <= 0 or original_count <= limit:
        return rows, False, original_count
    return rows[:limit], True, original_count


# ---------------------------------------------------------------------------
# Report/input extraction
# ---------------------------------------------------------------------------
def _load_report_input(report_input_id: str) -> dict[str, Any]:
    report_input_id = _text(report_input_id)
    if not report_input_id:
        raise ReportDataPackExportError("report_input_id wajib diisi.")

    try:
        report_input = get_report_input(report_input_id)
    except ReportInputStoreError as exc:
        raise ReportDataPackExportError(str(exc)) from exc

    if not report_input:
        raise ReportDataPackExportError(f"report_input_id tidak ditemukan: {report_input_id}")
    return report_input


def _report_scope(report_input: Mapping[str, Any]) -> dict[str, Any]:
    context = report_input.get("context") or {}
    period = context.get("period") or {}
    scope = report_input.get("scope") or {}

    return {
        "report_input_id": report_input.get("report_input_id"),
        "report_type_id": report_input.get("report_type_id"),
        "project_name": context.get("project_name"),
        "period_start": period.get("start_date"),
        "period_end": period.get("end_date"),
        "timezone": context.get("timezone"),
        "channels": context.get("channels") or scope.get("channels") or [],
        "client_brand": context.get("client_brand"),
        "competitor_brands": context.get("competitor_brands") or [],
        "analysis_objective": context.get("analysis_objective"),
        "confirmed_intent_id": context.get("confirmed_intent_id"),
        "data_scope": context.get("data_scope"),
        "scope": scope,
        "validation_status": (report_input.get("validation") or {}).get("status"),
        "created_at": report_input.get("created_at"),
    }


def _view_sheets(report_input: Mapping[str, Any], *, used_names: set[str]) -> list[SheetSpec]:
    sheets: list[SheetSpec] = []

    for group_key, prefix in (("quantitative_views", "QT"), ("qualitative_views", "QL")):
        views = report_input.get(group_key) or {}
        if not isinstance(views, Mapping):
            continue

        for view_id, view in views.items():
            if not isinstance(view, Mapping):
                continue
            rows = _normalize_rows(view.get("rows") or [])
            columns = _row_columns(rows) or ["note"]
            if not rows:
                rows = [{"note": "EMPTY_OR_NOT_AVAILABLE"}]
            name = _sheet_name(f"{prefix}_{view_id}", used_names)
            sheets.append(
                SheetSpec(
                    name=name,
                    columns=columns,
                    rows=rows,
                    source=str(view_id),
                    truncated=False,
                    original_row_count=len(rows),
                )
            )

            metadata = view.get("metadata") or {}
            if isinstance(metadata, Mapping) and metadata:
                meta_rows = _rows_from_mapping(metadata)
                sheets.append(
                    SheetSpec(
                        name=_sheet_name(f"META_{view_id}", used_names),
                        columns=["field", "value"],
                        rows=meta_rows,
                        source=f"{view_id}.metadata",
                    )
                )

    return sheets


def _channel_filter_for_report(report_input: Mapping[str, Any]) -> list[str] | None:
    report_type = _text(report_input.get("report_type_id")).casefold()
    context = report_input.get("context") or {}
    scope = report_input.get("scope") or {}

    explicit = context.get("channels") or scope.get("channels") or []
    if isinstance(explicit, str):
        explicit = [explicit]
    if explicit:
        return [str(item) for item in explicit if str(item).strip()]

    if report_type == "daily_social_media_report":
        return [
            "Facebook",
            "Forum",
            "Instagram",
            "Tiktok",
            "TikTok",
            "Twitter",
            "X",
            "Youtube",
            "YouTube",
        ]
    if report_type == "mainstream_media_report":
        return ["Online Media", "Printmedia", "Print Media", "TV", "Radio"]
    return None


def _filter_raw_by_report_type(records: list[dict[str, Any]], report_type_id: str) -> list[dict[str, Any]]:
    report_type = _text(report_type_id).casefold()
    if report_type not in {"daily_social_media_report", "mainstream_media_report"}:
        return records

    allowed = SOCIAL_CHANNELS if report_type == "daily_social_media_report" else MAINSTREAM_CHANNELS
    output = []
    for record in records:
        channel = _text(record.get("_cogan_channel") or record.get("Channel") or record.get("channel")).casefold()
        if channel in allowed:
            output.append(record)
    return output


def _raw_columns(records: list[dict[str, Any]]) -> list[str]:
    raw_cols: list[str] = []
    cogan_cols: list[str] = []
    raw_seen: set[str] = set()
    cogan_seen: set[str] = set()

    for record in records:
        for key in record.keys():
            key_text = str(key)
            if key_text.startswith(COGAN_PREFIX):
                if key_text not in cogan_seen:
                    cogan_seen.add(key_text)
                    cogan_cols.append(key_text)
            elif key_text not in raw_seen:
                raw_seen.add(key_text)
                raw_cols.append(key_text)
    return raw_cols + cogan_cols


def _fetch_raw_rows_for_report(
    report_input: Mapping[str, Any],
    *,
    raw_row_limit: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    context = report_input.get("context") or {}
    scope = report_input.get("scope") or {}
    period = context.get("period") or {}
    project_name = _text(context.get("project_name"))
    start_date = _text(period.get("start_date")) or None
    end_date = _text(period.get("end_date")) or None

    if not project_name:
        return [], ["Raw data tidak diekspor karena context.project_name kosong."]

    try:
        from database import db
    except Exception as exc:
        return [], [f"Raw data tidak diekspor karena database.db tidak dapat diimport: {exc}"]

    channels = _channel_filter_for_report(report_input)
    keywords = scope.get("keywords") or None
    exclude_keywords = scope.get("exclude_keywords") or None
    match_mode = scope.get("match_mode") or "any"

    # Fetch slightly above row limit before post-filtering by report type, but do
    # not allow unbounded raw export from MCP by default.
    fetch_limit = max(1, int(raw_row_limit or 1))
    try:
        records = db.fetch_raw_records(
            project_name,
            start_date,
            end_date,
            limit=fetch_limit,
            keywords=keywords,
            exclude_keywords=exclude_keywords,
            match_mode=match_mode,
            channels=channels,
        ) or []
    except Exception as exc:
        return [], [f"Raw data tidak berhasil diekspor: {type(exc).__name__}: {exc}"]

    records = _filter_raw_by_report_type([dict(item) for item in records], _text(report_input.get("report_type_id")))
    return records, []


# ---------------------------------------------------------------------------
# Sheet construction
# ---------------------------------------------------------------------------
def _build_report_sheets(
    report_input: Mapping[str, Any],
    *,
    include_task1_views: bool,
    include_raw_data: bool,
    raw_row_limit: int,
) -> tuple[list[SheetSpec], list[str]]:
    used: set[str] = set()
    limitations: list[str] = []
    scope = _report_scope(report_input)

    readme_rows = [
        {
            "item": "Purpose",
            "value": "Audit data pack for report numbers, Task 1 views, evidence, and optional raw canonical data.",
        },
        {
            "item": "Report Input ID",
            "value": report_input.get("report_input_id"),
        },
        {
            "item": "Metric Note",
            "value": "Views are reported separately from interactions. Raw Engagement is not automatically the final report metric.",
        },
        {
            "item": "Generated At UTC",
            "value": datetime.now(timezone.utc).isoformat(),
        },
    ]

    sheets: list[SheetSpec] = [
        SheetSpec(
            name=_sheet_name("00_README", used),
            columns=["item", "value"],
            rows=readme_rows,
            source="exporter",
        ),
        SheetSpec(
            name=_sheet_name("01_SCOPE", used),
            columns=["field", "value"],
            rows=_rows_from_mapping(scope),
            source="report_input.context_scope",
        ),
        SheetSpec(
            name=_sheet_name("02_VALIDATION", used),
            columns=["field", "value"],
            rows=_rows_from_mapping(report_input.get("validation") or {}),
            source="report_input.validation",
        ),
    ]

    report_limitations = report_input.get("limitations") or []
    if isinstance(report_limitations, list):
        limitation_rows = [
            {"no": idx + 1, "limitation": _json_safe(item)}
            for idx, item in enumerate(report_limitations)
        ] or [{"no": "", "limitation": "No limitations recorded."}]
        sheets.append(
            SheetSpec(
                name=_sheet_name("03_LIMITATIONS", used),
                columns=["no", "limitation"],
                rows=limitation_rows,
                source="report_input.limitations",
            )
        )

    evidence_log = report_input.get("evidence_log") or []
    if isinstance(evidence_log, list):
        evidence_rows = _normalize_rows(evidence_log)
        sheets.append(
            SheetSpec(
                name=_sheet_name("04_EVIDENCE_LOG", used),
                columns=_row_columns(evidence_rows) or ["note"],
                rows=evidence_rows or [{"note": "No explicit evidence_log records."}],
                source="report_input.evidence_log",
            )
        )

    if include_task1_views:
        sheets.extend(_view_sheets(report_input, used_names=used))

    if include_raw_data:
        raw_limit = max(1, min(int(raw_row_limit or 1), MAX_XLSX_ROWS))
        raw_rows, raw_warnings = _fetch_raw_rows_for_report(report_input, raw_row_limit=raw_limit)
        limitations.extend(raw_warnings)
        if raw_rows:
            rows, truncated, original_count = _truncate_rows(raw_rows, raw_limit)
            columns = _raw_columns(rows)
            sheets.append(
                SheetSpec(
                    name=_sheet_name("RAW_CANONICAL_DATA", used),
                    columns=columns,
                    rows=rows,
                    source="database.db.fetch_raw_records",
                    truncated=truncated,
                    original_row_count=original_count,
                )
            )
        else:
            sheets.append(
                SheetSpec(
                    name=_sheet_name("RAW_CANONICAL_DATA", used),
                    columns=["note"],
                    rows=[{"note": "No raw rows exported for this scope or raw export failed. Check limitations."}],
                    source="database.db.fetch_raw_records",
                )
            )

    return sheets, limitations


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------
def _write_csv_to_string(columns: list[str], rows: list[Mapping[str, Any]]) -> str:
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({col: _cell_value(row.get(col)) for col in columns})
    return buffer.getvalue()


def _write_csv_zip(sheets: list[SheetSpec], output_path: Path) -> None:
    with ZipFile(output_path, "w", ZIP_DEFLATED) as zf:
        manifest = []
        for sheet in sheets:
            filename = f"{_slug(sheet.name, 90)}.csv"
            csv_text = _write_csv_to_string(sheet.columns, sheet.rows)
            zf.writestr(filename, csv_text.encode("utf-8-sig"))
            manifest.append(
                {
                    "sheet_name": sheet.name,
                    "file_name": filename,
                    "row_count": len(sheet.rows),
                    "source": sheet.source,
                    "truncated": sheet.truncated,
                    "original_row_count": sheet.original_row_count,
                }
            )
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))


def _write_xlsx(sheets: list[SheetSpec], output_path: Path) -> None:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter
    except Exception as exc:
        raise ReportDataPackExportError(
            "openpyxl tidak tersedia di runtime; gunakan output_format='csv_zip'."
        ) from exc

    workbook = Workbook()
    default_sheet = workbook.active
    workbook.remove(default_sheet)

    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(color="FFFFFF", bold=True)
    title_font = Font(bold=True, size=12)

    for sheet in sheets:
        ws = workbook.create_sheet(title=sheet.name)
        ws.append(sheet.columns)
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for row in sheet.rows:
            ws.append([_cell_value(row.get(col)) for col in sheet.columns])

        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions

        for col_idx, column in enumerate(sheet.columns, 1):
            max_width = len(str(column)) + 2
            sample_limit = min(ws.max_row, 200)
            for row_idx in range(2, sample_limit + 1):
                value = ws.cell(row=row_idx, column=col_idx).value
                if value is not None:
                    max_width = max(max_width, min(len(str(value)) + 2, 60))
            ws.column_dimensions[get_column_letter(col_idx)].width = max(10, min(max_width, 42))

        if sheet.name.startswith("00_"):
            for cell in ws[1]:
                cell.font = title_font

        for row in ws.iter_rows():
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)

    workbook.save(output_path)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def export_report_data_pack(
    report_input_id: str,
    *,
    output_format: str = "xlsx",
    include_raw_data: bool = True,
    raw_row_limit: int = 50_000,
    include_task1_views: bool = True,
    include_file_base64: bool = False,
    max_base64_bytes: int = MAX_BASE64_BYTES_DEFAULT,
    output_dir: str | Path = EXPORT_DIR,
) -> dict[str, Any]:
    """Export an audit data pack for a stored `report_input_id`."""
    report_input = _load_report_input(report_input_id)
    return _export_from_report_input(
        report_input,
        output_format=output_format,
        include_raw_data=include_raw_data,
        raw_row_limit=raw_row_limit,
        include_task1_views=include_task1_views,
        include_file_base64=include_file_base64,
        max_base64_bytes=max_base64_bytes,
        output_dir=output_dir,
    )


def export_raw_scope_data(
    *,
    project_name: str,
    start_date: str,
    end_date: str,
    report_type_id: str = "",
    channels: Iterable[str] | str | None = None,
    output_format: str = "xlsx",
    row_limit: int = 50_000,
    include_file_base64: bool = False,
    max_base64_bytes: int = MAX_BASE64_BYTES_DEFAULT,
    output_dir: str | Path = EXPORT_DIR,
) -> dict[str, Any]:
    """Export raw canonical records for an ad-hoc scope, without report views."""
    project_name = _text(project_name)
    if not project_name:
        raise ReportDataPackExportError("project_name wajib diisi.")

    report_type = _text(report_type_id) or "raw_scope_export"
    channel_list: list[str] = []
    if isinstance(channels, str):
        channel_list = [item.strip() for item in channels.split(",") if item.strip()]
    elif channels:
        channel_list = [str(item).strip() for item in channels if str(item).strip()]

    pseudo_report_input = {
        "report_input_id": f"raw_{_slug(project_name)}_{_slug(start_date)}_{_slug(end_date)}",
        "report_type_id": report_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "context": {
            "project_name": project_name,
            "period": {"start_date": start_date, "end_date": end_date},
            "timezone": "Asia/Jakarta",
            "channels": channel_list,
            "data_scope": "raw_scope",
            "client_brand": project_name,
            "competitor_brands": [],
            "analysis_objective": "Raw canonical scope export",
            "confirmed_intent_id": None,
        },
        "scope": {"channels": channel_list, "keywords": [], "exclude_keywords": [], "match_mode": "any"},
        "metric_readiness": {},
        "data_health": {},
        "validation": {"status": "PASS", "missing_views": [], "warnings": [], "errors": []},
        "quantitative_views": {},
        "qualitative_views": {},
        "limitations": [],
        "evidence_log": [],
    }
    return _export_from_report_input(
        pseudo_report_input,
        output_format=output_format,
        include_raw_data=True,
        raw_row_limit=row_limit,
        include_task1_views=False,
        include_file_base64=include_file_base64,
        max_base64_bytes=max_base64_bytes,
        output_dir=output_dir,
    )


def _export_from_report_input(
    report_input: Mapping[str, Any],
    *,
    output_format: str,
    include_raw_data: bool,
    raw_row_limit: int,
    include_task1_views: bool,
    include_file_base64: bool,
    max_base64_bytes: int,
    output_dir: str | Path,
) -> dict[str, Any]:
    output_format = _text(output_format).casefold() or "xlsx"
    if output_format not in {"xlsx", "csv_zip"}:
        raise ReportDataPackExportError("output_format harus 'xlsx' atau 'csv_zip'.")

    sheets, export_limitations = _build_report_sheets(
        report_input,
        include_task1_views=include_task1_views,
        include_raw_data=include_raw_data,
        raw_row_limit=max(1, int(raw_row_limit or 1)),
    )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    scope = _report_scope(report_input)
    base_name = "_".join(
        [
            _slug(str(scope.get("project_name") or "project"), 35),
            _slug(str(scope.get("report_type_id") or "report"), 35),
            _slug(str(scope.get("period_start") or "start"), 12),
            _slug(str(scope.get("period_end") or "end"), 12),
            "Data_Pack",
        ]
    )

    actual_format = output_format
    output_path = output_dir / f"{base_name}.xlsx"
    try:
        if output_format == "xlsx":
            _write_xlsx(sheets, output_path)
        else:
            output_path = output_dir / f"{base_name}.zip"
            _write_csv_zip(sheets, output_path)
    except ReportDataPackExportError as exc:
        if output_format != "xlsx":
            raise
        export_limitations.append(str(exc))
        actual_format = "csv_zip"
        output_path = output_dir / f"{base_name}.zip"
        _write_csv_zip(sheets, output_path)

    file_bytes = output_path.read_bytes()
    base64_payload = None
    if include_file_base64:
        if len(file_bytes) <= max(1, int(max_base64_bytes or 1)):
            base64_payload = base64.b64encode(file_bytes).decode("ascii")
        else:
            export_limitations.append(
                f"Base64 payload tidak disertakan karena ukuran file {len(file_bytes)} bytes melebihi batas."
            )

    sheet_manifest = [
        {
            "sheet_name": sheet.name,
            "source": sheet.source,
            "row_count": len(sheet.rows),
            "column_count": len(sheet.columns),
            "truncated": sheet.truncated,
            "original_row_count": sheet.original_row_count,
        }
        for sheet in sheets
    ]

    return {
        "success": True,
        "export_version": "report_data_pack_export_v1",
        "report_input_id": report_input.get("report_input_id"),
        "report_type_id": report_input.get("report_type_id"),
        "project_name": scope.get("project_name"),
        "period": {"start_date": scope.get("period_start"), "end_date": scope.get("period_end")},
        "file_name": output_path.name,
        "file_path": str(output_path.resolve()),
        "file_format": actual_format,
        "file_size_bytes": len(file_bytes),
        "mime_type": (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if actual_format == "xlsx"
            else "application/zip"
        ),
        "sheets": sheet_manifest,
        "limitations": export_limitations,
        "file_base64": base64_payload,
        "assistant_instruction": (
            "Jika user meminta file download di chat, gunakan file_base64 bila tersedia untuk membuat attachment. "
            "Jika file_base64 kosong, baca file_path dari runtime MCP hanya bila connector mendukung file retrieval; "
            "kalau tidak, jalankan ulang dengan include_file_base64=True dan batas ukuran yang sesuai."
        ),
    }


__all__ = [
    "ReportDataPackExportError",
    "export_report_data_pack",
    "export_raw_scope_data",
]
