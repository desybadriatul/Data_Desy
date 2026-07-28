"""Install Competitive Analysis one-command workflow hooks v2.

Run from repository root:
    python scripts/patch_server_competitive_analysis_workflow_v2.py

Adds/updates MCP tools:
- create_competitive_analysis_report_workflow
- build_competitive_analysis_report_data_preview
- build_competitive_analysis_report_ppt_package

Guardrails:
- Audience is required.
- Competitor list is required by default.
- Competitive topic/narrative taxonomy/classification is required before final preview.
- Data preview must be shown before PPT package.
- Main slides should use Evidence IDs; full URLs live in Appendix/Data Pack.
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
        if "@mcp.tool()" not in gap and len(gap) < 900:
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
# One-command Competitive Analysis workflow v2
# ---------------------------------------------------------------------
@mcp.tool()
def create_competitive_analysis_report_workflow(
    project_name: str,
    start_date: str,
    end_date: str = "",
    audience: str = "",
    report_pov: str = "",
    client_brand: str = "",
    competitors: str = "",
    competitor_brands: str = "",
    confirmed_intent_id: str = "",
    analysis_objective: str = "",
    channels: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
    industry: str = "",
    market: str = "",
    topic_taxonomy_version: str = "",
    output_mode: str = "preview_only",
    include_evidence_limit: int = 10,
    allow_partial: bool = True,
    require_audience: bool = True,
    require_competitors: bool = True,
    ask_before_pptx: bool = True,
) -> dict[str, Any]:
    """Preferred tool for natural Competitive Analysis requests.

    Use this FIRST when user asks for Competitive Analysis. If audience or
    competitor list is missing, this returns NEEDS_AUDIENCE or NEEDS_COMPETITORS.
    If competitive topic/narrative taxonomy/classification is missing, this
    returns NEEDS_AUTO_COMPETITIVE_TAXONOMY or NEEDS_AUTO_COMPETITIVE_TOPIC_CLASSIFICATION.

    Topic policy: final CA topic/narrative metrics use cached LLM assignments
    from Title + Content. Raw Topic Extraction, legacy Aspect, and Entity
    Extraction are diagnostic only, not core source of truth.

    Main slide URL policy: use Evidence IDs only. Full URLs belong in Appendix
    and export_report_data_pack.
    """
    try:
        from reporting.task2.workflows.competitive_analysis_report_workflow import (
            create_competitive_analysis_report_workflow as _workflow,
        )
        return _workflow(
            project_name=project_name,
            start_date=start_date,
            end_date=end_date or None,
            audience=audience or None,
            report_pov=report_pov or None,
            client_brand=client_brand or None,
            competitors=competitors or None,
            competitor_brands=competitor_brands or None,
            confirmed_intent_id=confirmed_intent_id or None,
            analysis_objective=analysis_objective or None,
            channels=channels or None,
            keywords=keywords or None,
            exclude_keywords=exclude_keywords or None,
            match_mode=match_mode or "any",
            industry=industry or None,
            market=market or None,
            topic_taxonomy_version=topic_taxonomy_version or None,
            output_mode=output_mode or "preview_only",
            include_evidence_limit=int(include_evidence_limit),
            allow_partial=bool(allow_partial),
            require_audience=bool(require_audience),
            require_competitors=bool(require_competitors),
            ask_before_pptx=bool(ask_before_pptx),
        )
    except Exception as exc:
        return {"success": False, "workflow_status": "ERROR", "error": str(exc)}

'''

PREVIEW_BLOCK = '''# ---------------------------------------------------------------------
# Task 1 Competitive Analysis data preview
# ---------------------------------------------------------------------
@mcp.tool()
def build_competitive_analysis_report_data_preview(
    report_input_id: str,
    include_evidence_limit: int = 10,
) -> dict[str, Any]:
    """Build user-facing Task 1 preview before Competitive Analysis PPT creation.

    Shows brand universe, SOV/SOE, sentiment, channel/content benchmark,
    LLM topic/narrative coverage, limitations, and evidence IDs. Full URLs are
    kept for Appendix/Data Pack.
    """
    try:
        from reporting.task2.renderers.competitive_analysis_report_renderer import (
            build_competitive_analysis_report_data_preview as _build_preview,
        )
        return _build_preview(
            report_input_id=report_input_id,
            include_evidence_limit=int(include_evidence_limit),
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}

'''

BUILD_BLOCK = '''# ---------------------------------------------------------------------
# Guarded Task 2 Competitive Analysis renderer
# ---------------------------------------------------------------------
@mcp.tool()
def build_competitive_analysis_report_ppt_package(
    report_input_id: str,
    allow_partial: bool = True,
    audience: str = "",
    report_pov: str = "",
    preview_confirmed: bool = False,
) -> dict[str, Any]:
    """Build a PPT-ready Competitive Analysis package after preview confirmation.

    Guardrail: assistant must know target reader/POV and must show Task 1 data
    preview first. If missing, this returns an actionable status instead of a
    PPT package.
    """
    clean_audience = " ".join(str(audience or "").split())
    clean_pov = " ".join(str(report_pov or "").split())
    if not clean_audience and not clean_pov:
        return {
            "success": False,
            "workflow_status": "NEEDS_AUDIENCE",
            "clarification_question": (
                "Competitive Analysis ini dibuat untuk siapa? Pilih salah satu: "
                "Management, CEO/Board, Marketing/Brand, Marketing/Content, PR/Corcom, atau Insight Team."
            ),
            "instruction_to_assistant": (
                "Ask the user who the report is for. Do not build PPTX yet. "
                "After audience is provided, call create_competitive_analysis_report_workflow first to show data preview."
            ),
        }
    if not bool(preview_confirmed):
        return {
            "success": False,
            "workflow_status": "NEEDS_PREVIEW_CONFIRMATION",
            "report_input_id": report_input_id,
            "instruction_to_assistant": (
                "Show Task 1 data preview first using create_competitive_analysis_report_workflow(output_mode='preview_only'). "
                "Then ask the user whether to continue to PPTX. Call this tool again with preview_confirmed=True only after the user confirms."
            ),
        }
    try:
        from reporting.task2.renderers.competitive_analysis_report_renderer import (
            build_competitive_analysis_report_package as _build_package,
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
        ("create_competitive_analysis_report_workflow", WORKFLOW_BLOCK),
        ("build_competitive_analysis_report_data_preview", PREVIEW_BLOCK),
        ("build_competitive_analysis_report_ppt_package", BUILD_BLOCK),
    ):
        text, action = _upsert_tool(text, name, block)
        print(f"{action}: {name}")
    SERVER.write_text(text, encoding="utf-8")
    print("Installed Competitive Analysis workflow MCP hooks v2.")


if __name__ == "__main__":
    main()
