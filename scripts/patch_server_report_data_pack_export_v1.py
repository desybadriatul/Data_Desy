"""Patch server.py with report data pack export MCP tools."""

from __future__ import annotations

from pathlib import Path

SERVER = Path("server.py")
START = "# --- REPORT DATA PACK EXPORT TOOLS V1 START ---"
END = "# --- REPORT DATA PACK EXPORT TOOLS V1 END ---"

BLOCK = f'''
{START}
@mcp.tool()
def export_report_data_pack(
    report_input_id: str,
    output_format: str = "xlsx",
    include_raw_data: bool = True,
    raw_row_limit: int = 50000,
    include_task1_views: bool = True,
    include_file_base64: bool = False,
    max_base64_bytes: int = 4000000,
) -> dict[str, Any]:
    """
    Export audit data pack for a stored Task 1 report_input_id.

    Use this after prepare_report_input / workflow preview when the user asks
    for raw data, Excel, CSV, evidence pack, audit pack, or proof that report
    numbers are not invented.

    Output:
    - xlsx multi-sheet by default, fallback to csv_zip if xlsx writer is not available.
    - Task 1 quantitative and qualitative views.
    - limitations and evidence log.
    - optional raw canonical data for the exact report scope.
    - optional file_base64 for assistants that need to create a downloadable file.
    """
    try:
        from reporting.exports.report_data_pack_exporter import (
            export_report_data_pack as _export_report_data_pack,
        )

        return _export_report_data_pack(
            report_input_id=report_input_id,
            output_format=output_format,
            include_raw_data=include_raw_data,
            raw_row_limit=max(1, int(raw_row_limit or 1)),
            include_task1_views=include_task1_views,
            include_file_base64=bool(include_file_base64),
            max_base64_bytes=max(1, int(max_base64_bytes or 1)),
        )
    except Exception as exc:
        return {{
            "success": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "report_input_id": report_input_id,
            "instruction": "Periksa report_input_id, DATABASE_URL, dan dependency xlsx writer. Coba output_format='csv_zip' jika xlsx gagal.",
        }}


@mcp.tool()
def export_raw_scope_data(
    project_name: str,
    start_date: str,
    end_date: str,
    report_type_id: str = "",
    channels: str = "",
    output_format: str = "xlsx",
    row_limit: int = 50000,
    include_file_base64: bool = False,
    max_base64_bytes: int = 4000000,
) -> dict[str, Any]:
    """
    Export raw canonical data for an ad-hoc project/date/channel scope.

    Prefer export_report_data_pack(report_input_id) for report audit, because it
    exports the exact Task 1 package used for PPT. Use this tool only when user
    explicitly asks for raw scope data without a report_input_id.
    """
    try:
        from reporting.exports.report_data_pack_exporter import (
            export_raw_scope_data as _export_raw_scope_data,
        )

        channel_list = [item.strip() for item in (channels or "").split(",") if item.strip()]
        return _export_raw_scope_data(
            project_name=project_name,
            start_date=start_date,
            end_date=end_date,
            report_type_id=report_type_id,
            channels=channel_list,
            output_format=output_format,
            row_limit=max(1, int(row_limit or 1)),
            include_file_base64=bool(include_file_base64),
            max_base64_bytes=max(1, int(max_base64_bytes or 1)),
        )
    except Exception as exc:
        return {{
            "success": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "project_name": project_name,
            "period": {{"start_date": start_date, "end_date": end_date}},
            "instruction": "Periksa project_name/periode/channel dan DATABASE_URL. Untuk audit report, pakai export_report_data_pack bila ada report_input_id.",
        }}
{END}
'''


def install() -> None:
    text = SERVER.read_text(encoding="utf-8")

    if START in text and END in text:
        before, rest = text.split(START, 1)
        _, after = rest.split(END, 1)
        text = before.rstrip() + "\n\n" + BLOCK.strip() + "\n" + after
        action = "replaced"
    else:
        marker = "# ---------------------------------------------------------------------\n# Cross-project anomaly scan"
        if marker in text:
            text = text.replace(marker, BLOCK.strip() + "\n\n" + marker, 1)
        else:
            text = text.rstrip() + "\n\n" + BLOCK.strip() + "\n"
        action = "inserted"

    SERVER.write_text(text, encoding="utf-8")
    print(f"{action}: report data pack export MCP tools")
    print("Installed Report Data Pack export tools v1.")


if __name__ == "__main__":
    install()
