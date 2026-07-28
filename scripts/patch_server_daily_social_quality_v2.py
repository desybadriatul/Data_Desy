"""Install/upgrade MCP tool hooks for Daily Social renderer v2.

Run from repository root:
    python scripts/patch_server_daily_social_quality_v2.py
"""

from pathlib import Path

SERVER = Path("server.py")
MARKER = "# ---------------------------------------------------------------------\n# Insight report skill loaders"

BUILD_FUNCTION_NAME = "build_daily_social_report_ppt_package"
PREVIEW_FUNCTION_NAME = "build_daily_social_report_data_preview"

BUILD_BLOCK = (
    "# ---------------------------------------------------------------------\n"
    "# Task 2 Daily Social report renderer\n"
    "# ---------------------------------------------------------------------\n"
    "@mcp.tool()\n"
    "def build_daily_social_report_ppt_package(\n"
    "    report_input_id: str,\n"
    "    allow_partial: bool = True,\n"
    ") -> dict[str, Any]:\n"
    "    \"\"\"Build a PPT-ready Daily Social report package from a stored report_input_id.\"\"\"\n"
    "    try:\n"
    "        from reporting.task2.renderers.daily_social_media_report_renderer import (\n"
    "            build_daily_social_report_package as _build_daily_social_package,\n"
    "        )\n"
    "        return _build_daily_social_package(\n"
    "            report_input_id=report_input_id,\n"
    "            allow_partial=bool(allow_partial),\n"
    "        )\n"
    "    except Exception as exc:\n"
    "        return {\"success\": False, \"error\": str(exc)}\n"
    "\n"
)

PREVIEW_BLOCK = (
    "# ---------------------------------------------------------------------\n"
    "# Task 1 Daily Social data preview\n"
    "# ---------------------------------------------------------------------\n"
    "@mcp.tool()\n"
    "def build_daily_social_report_data_preview(\n"
    "    report_input_id: str,\n"
    "    include_evidence_limit: int = 10,\n"
    ") -> dict[str, Any]:\n"
    "    \"\"\"Build a user-facing Task 1 data preview before PPT creation.\"\"\"\n"
    "    try:\n"
    "        from reporting.task2.renderers.daily_social_media_report_renderer import (\n"
    "            build_daily_social_report_data_preview as _build_preview,\n"
    "        )\n"
    "        return _build_preview(\n"
    "            report_input_id=report_input_id,\n"
    "            include_evidence_limit=int(include_evidence_limit),\n"
    "        )\n"
    "    except Exception as exc:\n"
    "        return {\"success\": False, \"error\": str(exc)}\n"
    "\n"
)


def _insert_block(text: str, function_name: str, block: str) -> tuple[str, bool]:
    if function_name in text:
        return text, False
    if MARKER not in text:
        raise SystemExit("Marker Insight report skill loaders tidak ditemukan; patch manual diperlukan.")
    return text.replace(MARKER, block + MARKER, 1), True


def main() -> None:
    if not SERVER.exists():
        raise SystemExit("server.py tidak ditemukan. Jalankan script dari root repo.")

    text = SERVER.read_text(encoding="utf-8")
    changed = False

    text, did_insert = _insert_block(text, BUILD_FUNCTION_NAME, BUILD_BLOCK)
    changed = changed or did_insert

    text, did_insert = _insert_block(text, PREVIEW_FUNCTION_NAME, PREVIEW_BLOCK)
    changed = changed or did_insert

    if changed:
        SERVER.write_text(text, encoding="utf-8")
        print("Installed/updated Daily Social MCP tool hooks.")
    else:
        print("Daily Social MCP tool hooks already installed; no change.")


if __name__ == "__main__":
    main()
