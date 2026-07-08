# Install server.py tool hook for Daily Social Task 2 renderer.

from pathlib import Path

SERVER = Path("server.py")
MARKER = "# ---------------------------------------------------------------------\n# Insight report skill loaders"
FUNCTION_NAME = "build_daily_social_report_ppt_package"

BLOCK = (
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


def main() -> None:
    if not SERVER.exists():
        raise SystemExit("server.py tidak ditemukan. Jalankan script dari root repo.")
    text = SERVER.read_text(encoding="utf-8")
    if FUNCTION_NAME in text:
        print(f"{FUNCTION_NAME} already installed; no change.")
        return
    if MARKER not in text:
        raise SystemExit("Marker Insight report skill loaders tidak ditemukan; patch manual diperlukan.")
    text = text.replace(MARKER, BLOCK + MARKER, 1)
    SERVER.write_text(text, encoding="utf-8")
    print(f"Installed {FUNCTION_NAME} into server.py")


if __name__ == "__main__":
    main()
