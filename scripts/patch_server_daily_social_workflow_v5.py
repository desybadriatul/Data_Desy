"""Install Daily Social one-command workflow hooks v5.

Run from repository root:
    python scripts/patch_server_daily_social_workflow_v5.py

What this changes:
- create_daily_social_report_workflow becomes the preferred natural-language
  path for short Daily Social requests.
- It asks audience when omitted.
- It can auto-plan lightweight topic taxonomy/classification using smart sample
  defaults, so users do not need to understand enrichment/batch terms.
- It still shows Task 1 data preview before PPTX.
- build_daily_social_report_ppt_package remains guarded: audience + preview
  confirmation are required.
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
# One-command Daily Social report workflow with smart auto-topic planning
# ---------------------------------------------------------------------
@mcp.tool()
def create_daily_social_report_workflow(
    project_name: str,
    start_date: str,
    end_date: str = "",
    audience: str = "",
    report_pov: str = "",
    client_brand: str = "",
    topic_taxonomy_version: str = "",
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
    auto_topic_mode: str = "smart_sample",
    auto_topic_enabled: bool = True,
    topic_sample_ratio: float = 0.10,
    topic_min_posts: int = 20,
    topic_max_posts: int = 100,
    taxonomy_sample_size: int = 30,
    force_skip_auto_topic: bool = False,
) -> dict[str, Any]:
    """Preferred tool for natural Daily Social report requests.

    Use this FIRST when the user asks naturally, e.g. "buatkan daily report
    Gojek tanggal 2026-05-08". If audience/reader is omitted, this returns
    NEEDS_AUDIENCE so the assistant must ask who the report is for.

    After audience is known, this workflow uses full canonical data for KPI,
    sentiment, author, and content views. For thematic topics, it uses existing
    cache/taxonomy or auto-plans a lightweight smart sample by default:
    10% of topic-eligible posts, minimum 20, maximum 100. The user should not
    be asked to manage taxonomy/enrichment/batches.

    Default output_mode is preview_only: show Task 1 data preview first, then
    wait for user confirmation before creating PPTX.
    """
    try:
        from reporting.task2.workflows.daily_social_report_workflow import (
            create_daily_social_report_workflow as _workflow,
        )
        return _workflow(
            project_name=project_name,
            start_date=start_date,
            end_date=end_date or None,
            audience=audience or None,
            report_pov=report_pov or None,
            client_brand=client_brand or None,
            topic_taxonomy_version=topic_taxonomy_version or None,
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
            auto_topic_mode=auto_topic_mode or "smart_sample",
            auto_topic_enabled=bool(auto_topic_enabled),
            topic_sample_ratio=float(topic_sample_ratio),
            topic_min_posts=int(topic_min_posts),
            topic_max_posts=int(topic_max_posts),
            taxonomy_sample_size=int(taxonomy_sample_size),
            force_skip_auto_topic=bool(force_skip_auto_topic),
        )
    except Exception as exc:
        return {"success": False, "workflow_status": "ERROR", "error": str(exc)}

'''

PREVIEW_BLOCK = '''# ---------------------------------------------------------------------
# Task 1 Daily Social data preview
# ---------------------------------------------------------------------
@mcp.tool()
def build_daily_social_report_data_preview(
    report_input_id: str,
    include_evidence_limit: int = 10,
) -> dict[str, Any]:
    """Build a user-facing Task 1 data preview before PPT creation.

    Use this to show KPI, sentiment/channel data, topic status, top authors,
    qualitative evidence, and source URLs before creating PPTX.
    """
    try:
        from reporting.task2.renderers.daily_social_media_report_renderer import (
            build_daily_social_report_data_preview as _build_preview,
        )
        return _build_preview(
            report_input_id=report_input_id,
            include_evidence_limit=int(include_evidence_limit),
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}

'''

BUILD_BLOCK = '''# ---------------------------------------------------------------------
# Guarded Task 2 Daily Social report renderer
# ---------------------------------------------------------------------
@mcp.tool()
def build_daily_social_report_ppt_package(
    report_input_id: str,
    allow_partial: bool = True,
    audience: str = "",
    report_pov: str = "",
    preview_confirmed: bool = False,
) -> dict[str, Any]:
    """Build a PPT-ready Daily Social package only after audience + preview confirmation.

    Guardrail for user experience: for Daily Social reports, the assistant must
    know the target reader/POV and must show the Task 1 data preview first. If
    either is missing, this tool returns an actionable status instead of a PPT
    package, preventing accidental direct PPT creation from a short prompt.
    """
    clean_audience = " ".join(str(audience or "").split())
    clean_pov = " ".join(str(report_pov or "").split())
    if not clean_audience and not clean_pov:
        return {
            "success": False,
            "workflow_status": "NEEDS_AUDIENCE",
            "clarification_question": (
                "Report Daily Social ini dibuat untuk siapa? Pilih salah satu: "
                "PR/Corcom, Insight, Management, CEO/Board, Social Care, Marketing, atau Brand Team."
            ),
            "instruction_to_assistant": (
                "Ask the user who the report is for. Do not build PPTX yet. "
                "After audience is provided, call create_daily_social_report_workflow first to show data preview."
            ),
        }
    if not bool(preview_confirmed):
        return {
            "success": False,
            "workflow_status": "NEEDS_PREVIEW_CONFIRMATION",
            "report_input_id": report_input_id,
            "instruction_to_assistant": (
                "Show Task 1 data preview first using create_daily_social_report_workflow(output_mode='preview_only'). "
                "If the workflow returns NEEDS_AUTO_TOPIC_TAXONOMY or NEEDS_AUTO_TOPIC_CLASSIFICATION, continue those automated steps first. "
                "Then ask the user whether to continue to PPTX. Call this tool again with preview_confirmed=True only after the user confirms."
            ),
        }
    try:
        from reporting.task2.renderers.daily_social_media_report_renderer import (
            build_daily_social_report_package as _build_daily_social_package,
        )
        return _build_daily_social_package(
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
        ("create_daily_social_report_workflow", WORKFLOW_BLOCK),
        ("build_daily_social_report_data_preview", PREVIEW_BLOCK),
        ("build_daily_social_report_ppt_package", BUILD_BLOCK),
    ):
        text, action = _upsert_tool(text, name, block)
        print(f"{action}: {name}")

    SERVER.write_text(text, encoding="utf-8")
    print("Installed Daily Social workflow MCP hooks v5.")


if __name__ == "__main__":
    main()
