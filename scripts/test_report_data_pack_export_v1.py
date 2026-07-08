"""Smoke test for report data pack export."""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from reporting.storage.report_input_store import list_report_inputs
from reporting.exports.report_data_pack_exporter import export_report_data_pack


def main() -> None:
    rows = list_report_inputs(limit=1)
    if not rows:
        raise RuntimeError("Belum ada report_input tersimpan. Jalankan prepare_report_input/workflow dulu.")

    report_input_id = rows[0]["report_input_id"]
    print("REPORT_INPUT_ID =", report_input_id)
    print("REPORT_TYPE =", rows[0]["report_type_id"])
    print("PROJECT =", rows[0]["project_name"])

    result = export_report_data_pack(
        report_input_id,
        output_format="xlsx",
        include_raw_data=True,
        raw_row_limit=2000,
        include_task1_views=True,
        include_file_base64=False,
    )

    print("SUCCESS =", result["success"])
    print("FORMAT =", result["file_format"])
    print("FILE =", result["file_path"])
    print("SIZE =", result["file_size_bytes"])
    print("SHEETS =", len(result["sheets"]))
    for sheet in result["sheets"][:20]:
        print("-", sheet["sheet_name"], "| rows:", sheet["row_count"], "| source:", sheet["source"])
    if result.get("limitations"):
        print("LIMITATIONS:")
        for item in result["limitations"]:
            print("-", item)


if __name__ == "__main__":
    main()
