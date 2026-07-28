"""Install one-command Daily Social workflow MCP hook.

Run from repository root:
    python scripts/patch_server_daily_social_workflow_v3.py
"""

from pathlib import Path

SERVER = Path("server.py")
MARKER = "# ---------------------------------------------------------------------\n# Insight report skill loaders"
FUNCTION_NAME = "create_daily_social_report_workflow"

WORKFLOW_BLOCK = (
    "# ---------------------------------------------------------------------\n"
    "# One-command Daily Social report workflow\n"
    "# ---------------------------------------------------------------------\n"
    "@mcp.tool()\n"
    "def create_daily_social_report_workflow(\n"
    "    project_name: str,\n"
    "    start_date: str,\n"
    "    end_date: str = \"\",\n"
    "    audience: str = \"\",\n"
    "    report_pov: str = \"\",\n"
    "    client_brand: str = \"\",\n"
    "    topic_taxonomy_version: str = \"\",\n"
    "    confirmed_intent_id: str = \"\",\n"
    "    analysis_objective: str = \"\",\n"
    "    channels: str = \"\",\n"
    "    keywords: str = \"\",\n"
    "    exclude_keywords: str = \"\",\n"
    "    match_mode: str = \"any\",\n"
    "    output_mode: str = \"preview_and_package\",\n"
    "    include_evidence_limit: int = 10,\n"
    "    allow_partial: bool = True,\n"
    "    require_audience: bool = True,\n"
    "    ask_before_pptx: bool = True,\n"
    ") -> dict[str, Any]:\n"
    "    \"\"\"Run Daily Social report workflow from a short user request.\n\n"
    "    Use this when the user asks naturally, e.g. 'buatkan daily report\n"
    "    Gojek tanggal 2026-05-08'. If audience is omitted, the tool returns\n"
    "    NEEDS_AUDIENCE so Claude can ask who the report is for before creating\n"
    "    the report. This workflow prepares Task 1 data, builds data preview,\n"
    "    builds outline/package, and adapts narrative guidance to the target\n"
    "    audience. It does not run topic batch enrichment automatically, so it\n"
    "    does not spend Claude usage on classification.\n"
    "    \"\"\"\n"
    "    try:\n"
    "        from reporting.task2.workflows.daily_social_report_workflow import (\n"
    "            create_daily_social_report_workflow as _workflow,\n"
    "        )\n"
    "        return _workflow(\n"
    "            project_name=project_name,\n"
    "            start_date=start_date,\n"
    "            end_date=end_date or None,\n"
    "            audience=audience or None,\n"
    "            report_pov=report_pov or None,\n"
    "            client_brand=client_brand or None,\n"
    "            topic_taxonomy_version=topic_taxonomy_version or None,\n"
    "            confirmed_intent_id=confirmed_intent_id or None,\n"
    "            analysis_objective=analysis_objective or None,\n"
    "            channels=channels or None,\n"
    "            keywords=keywords or None,\n"
    "            exclude_keywords=exclude_keywords or None,\n"
    "            match_mode=match_mode,\n"
    "            output_mode=output_mode,\n"
    "            include_evidence_limit=int(include_evidence_limit),\n"
    "            allow_partial=bool(allow_partial),\n"
    "            require_audience=bool(require_audience),\n"
    "            ask_before_pptx=bool(ask_before_pptx),\n"
    "        )\n"
    "    except Exception as exc:\n"
    "        return {\"success\": False, \"workflow_status\": \"ERROR\", \"error\": str(exc)}\n"
    "\n"
)


def main() -> None:
    if not SERVER.exists():
        raise SystemExit("server.py tidak ditemukan. Jalankan script dari root repo.")

    text = SERVER.read_text(encoding="utf-8")
    if FUNCTION_NAME in text:
        print("Daily Social one-command workflow MCP hook already installed; no change.")
        return
    if MARKER not in text:
        raise SystemExit("Marker Insight report skill loaders tidak ditemukan; patch manual diperlukan.")

    text = text.replace(MARKER, WORKFLOW_BLOCK + MARKER, 1)
    SERVER.write_text(text, encoding="utf-8")
    print("Installed Daily Social one-command workflow MCP hook.")


if __name__ == "__main__":
    main()
