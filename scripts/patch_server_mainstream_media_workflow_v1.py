"""Install Mainstream Media Report one-command workflow hooks.

Run from repository root:
    python scripts/patch_server_mainstream_media_workflow_v1.py

Adds/updates MCP tools:
- create_mainstream_media_report_workflow
- build_mainstream_media_report_data_preview
- build_mainstream_media_report_ppt_package

Guardrail:
- PPT package requires audience and preview_confirmed=True.
- Short user prompts should go through create_mainstream_media_report_workflow first.
"""

from __future__ import annotations

from pathlib import Path

SERVER = Path("server.py")
MARKER = "# ---------------------------------------------------------------------\n# Insight report skill loaders"


def _find_tool_def(text: str, function_name: str) -> tuple[int, int] | None:
    needle = f"def {function_name}("
    def_pos = text.find(needle)
    if def_pos < 0:
        return None
    start = text.rfind("@mcp.tool()", 0, def_pos)
    if start < 0:
        start = def_pos
    comment_start = text.rfind("# ---------------------------------------------------------------------", 0, start)
    if comment_start >= 0:
        gap = text[comment_start:start]
        if "@mcp.tool()" not in gap and len(gap) < 600:
            start = comment_start
    candidates = []
    for marker in ("\n@mcp.tool()", "\n# ---------------------------------------------------------------------\n"):
        pos = text.find(marker, def_pos + len(needle))
        if pos >= 0:
            candidates.append(pos + 1)
    end = min(candidates) if candidates else len(text)
    return start, end


def _upsert_tool(text: str, function_name: str, block: str) -> tuple[str, str]:
    found = _find_tool_def(text, function_name)
    if found:
        start, end = found
        return text[:start] + block + text[end:], "replaced"
    if MARKER not in text:
        raise SystemExit("Marker Insight report skill loaders tidak ditemukan; patch manual diperlukan.")
    return text.replace(MARKER, block + MARKER, 1), "inserted"


WORKFLOW_BLOCK = '''# ---------------------------------------------------------------------
# One-command Mainstream Media Report workflow with smart auto-issue planning
# ---------------------------------------------------------------------
@mcp.tool()
def create_mainstream_media_report_workflow(
    project_name: str,
    start_date: str,
    end_date: str = "",
    audience: str = "",
    report_pov: str = "",
    client_brand: str = "",
    topic_taxonomy_version: str = "",
    issue_taxonomy_version: str = "",
    confirmed_intent_id: str = "",
    analysis_objective: str = "",
    channels: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
    output_mode: str = "preview_only",
    include_evidence_limit: int = 10,
    allow_partial: bool = True,
    require_audience: bool = True,
    ask_before_pptx: bool = True,
    auto_issue_mode: str = "smart_sample",
    auto_issue_enabled: bool = True,
    issue_sample_ratio: float = 0.10,
    issue_min_articles: int = 20,
    issue_max_articles: int = 100,
    taxonomy_sample_size: int = 30,
    force_skip_auto_issue: bool = False,
) -> dict[str, Any]:
    """Preferred tool for natural Mainstream Media Report requests.

    Use this FIRST when the user asks naturally, e.g. "buatkan mainstream
    media report Gojek tanggal 2026-05-08". If audience/reader is omitted,
    this returns NEEDS_AUDIENCE so the assistant must ask who the report is for.

    After audience is known, the workflow uses full canonical mainstream data
    for KPI, sentiment, media contributors, and article evidence. For issue
    analysis, it uses existing cache/taxonomy or auto-plans a lightweight smart
    sample by default: 10% of issue-eligible articles, minimum 20, maximum 100.
    The user should not be asked to manage taxonomy/enrichment/batches.

    Default output_mode is preview_only: show Task 1 data preview first, then
    wait for user confirmation before creating PPTX.
    """
    try:
        from reporting.task2.workflows.mainstream_media_report_workflow import (
            create_mainstream_media_report_workflow as _workflow,
        )
        return _workflow(
            project_name=project_name,
            start_date=start_date,
            end_date=end_date or None,
            audience=audience or None,
            report_pov=report_pov or None,
            client_brand=client_brand or None,
            topic_taxonomy_version=topic_taxonomy_version or None,
            issue_taxonomy_version=issue_taxonomy_version or None,
            confirmed_intent_id=confirmed_intent_id or None,
            analysis_objective=analysis_objective or None,
            channels=channels or None,
            keywords=keywords or None,
            exclude_keywords=exclude_keywords or None,
            match_mode=match_mode,
            output_mode=output_mode or "preview_only",
            include_evidence_limit=int(include_evidence_limit),
            allow_partial=bool(allow_partial),
            require_audience=bool(require_audience),
            ask_before_pptx=bool(ask_before_pptx),
            auto_issue_mode=auto_issue_mode or "smart_sample",
            auto_issue_enabled=bool(auto_issue_enabled),
            issue_sample_ratio=float(issue_sample_ratio),
            issue_min_articles=int(issue_min_articles),
            issue_max_articles=int(issue_max_articles),
            taxonomy_sample_size=int(taxonomy_sample_size),
            force_skip_auto_issue=bool(force_skip_auto_issue),
        )
    except Exception as exc:
        return {"success": False, "workflow_status": "ERROR", "error": str(exc)}

'''

PREVIEW_BLOCK = '''# ---------------------------------------------------------------------
# Task 1 Mainstream Media data preview
# ---------------------------------------------------------------------
@mcp.tool()
def build_mainstream_media_report_data_preview(
    report_input_id: str,
    include_evidence_limit: int = 10,
) -> dict[str, Any]:
    """Build a user-facing Task 1 data preview before MMR PPT creation.

    Shows KPI, channel/media distribution, sentiment, top issues, top media,
    article evidence URLs, sensitive headlines, limitations, and readiness.
    """
    try:
        from reporting.task2.renderers.mainstream_media_report_renderer import (
            build_mainstream_media_report_data_preview as _build_preview,
        )
        return _build_preview(
            report_input_id=report_input_id,
            include_evidence_limit=int(include_evidence_limit),
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}

'''

BUILD_BLOCK = '''# ---------------------------------------------------------------------
# Guarded Task 2 Mainstream Media Report renderer
# ---------------------------------------------------------------------
@mcp.tool()
def build_mainstream_media_report_ppt_package(
    report_input_id: str,
    allow_partial: bool = True,
    audience: str = "",
    report_pov: str = "",
    preview_confirmed: bool = False,
) -> dict[str, Any]:
    """Build a PPT-ready Mainstream Media package only after audience + preview confirmation.

    Guardrail: assistant must know the target reader/POV and must show Task 1
    data preview first. If either is missing, this tool returns an actionable
    status instead of a PPT package.
    """
    clean_audience = " ".join(str(audience or "").split())
    clean_pov = " ".join(str(report_pov or "").split())
    if not clean_audience and not clean_pov:
        return {
            "success": False,
            "workflow_status": "NEEDS_AUDIENCE",
            "clarification_question": (
                "Mainstream Media Report ini dibuat untuk siapa? Pilih salah satu: "
                "PR/Corcom, Media Relations, Insight, Management, CEO/Board, Legal/Crisis Team, atau Marketing/Brand."
            ),
            "instruction_to_assistant": (
                "Ask the user who the report is for. Do not build PPTX yet. "
                "After audience is provided, call create_mainstream_media_report_workflow first to show data preview."
            ),
        }
    if not bool(preview_confirmed):
        return {
            "success": False,
            "workflow_status": "NEEDS_PREVIEW_CONFIRMATION",
            "report_input_id": report_input_id,
            "instruction_to_assistant": (
                "Show Task 1 data preview first using create_mainstream_media_report_workflow(output_mode='preview_only'). "
                "If the workflow returns NEEDS_AUTO_ISSUE_TAXONOMY or NEEDS_AUTO_ISSUE_CLASSIFICATION, continue those automated steps first. "
                "Then ask the user whether to continue to PPTX. Call this tool again with preview_confirmed=True only after the user confirms."
            ),
        }
    try:
        from reporting.task2.renderers.mainstream_media_report_renderer import (
            build_mainstream_media_report_package as _build_package,
        )
        return _build_package(
            report_input_id=report_input_id,
            allow_partial=bool(allow_partial),
            audience_context=clean_audience,
            audience_pov=clean_pov,
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}

'''


def main() -> None:
    if not SERVER.exists():
        raise SystemExit("server.py tidak ditemukan. Jalankan script dari root repo.")
    text = SERVER.read_text(encoding="utf-8")
    for name, block in (
        ("create_mainstream_media_report_workflow", WORKFLOW_BLOCK),
        ("build_mainstream_media_report_data_preview", PREVIEW_BLOCK),
        ("build_mainstream_media_report_ppt_package", BUILD_BLOCK),
    ):
        text, action = _upsert_tool(text, name, block)
        print(f"{action}: {name}")
    SERVER.write_text(text, encoding="utf-8")
    print("Installed Mainstream Media workflow MCP hooks v1.")


if __name__ == "__main__":
    main()
