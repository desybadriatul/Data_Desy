"""One-command Daily Social report workflow.

This workflow is the user-friendly orchestrator for Claude/Cogan:

- asks for audience/reader when omitted;
- prepares Task 1 report_input;
- shows Task 1 data preview before PPT;
- builds Task 2 outline and PPT-ready package;
- adapts narrative guidance to the target audience/POV;
- does not perform LLM topic enrichment or batch classification, so it does not
  spend Claude usage on topic classification by itself.

Claude still creates the final PPTX from the returned slides array.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from reporting.task1.report_input_dispatcher import prepare_report_input
from reporting.task2.report_outline_builder import build_report_outline_from_id
from reporting.task2.renderers.daily_social_media_report_renderer import (
    audience_clarification_payload,
    build_daily_social_report_data_preview,
    build_daily_social_report_package,
    normalize_audience_context,
)

REPORT_TYPE_ID = "daily_social_media_report"
DEFAULT_ANALYSIS_OBJECTIVE = "Daily Social Media Report Action-Plan-First"


class DailySocialWorkflowError(RuntimeError):
    """Raised when the workflow cannot run safely."""


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _csv_list(value: str | Iterable[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(item).strip() for item in value if str(item).strip()]


def _active_taxonomy_version(project_name: str) -> str | None:
    """Return active taxonomy version if topic enrichment store is available."""
    try:
        from reporting.enrichment.topic_store import get_active_taxonomy

        taxonomy = get_active_taxonomy(project_name)
        if taxonomy:
            return str(taxonomy.get("taxonomy_version") or "").strip() or None
    except Exception:
        return None
    return None


def _topic_status(
    *,
    project_name: str,
    taxonomy_version: str | None,
    start_date: str,
    end_date: str,
    channels: list[str],
    keywords: list[str],
    exclude_keywords: list[str],
    match_mode: str,
) -> dict[str, Any] | None:
    try:
        from reporting.enrichment.topic_batch_builder import get_topic_enrichment_status

        return get_topic_enrichment_status(
            project_name=project_name,
            taxonomy_version=taxonomy_version,
            start_date=start_date,
            end_date=end_date,
            channels=channels,
            keywords=keywords,
            exclude_keywords=exclude_keywords,
            match_mode=match_mode,
        )
    except Exception as exc:
        return {
            "status": "UNKNOWN",
            "error": str(exc),
            "note": "Topic enrichment status tidak dapat dibaca; workflow tetap lanjut dengan limitation dari Task 1.",
        }


def _needs_ppt_confirmation(preview: dict[str, Any], ask_before_pptx: bool) -> bool:
    if ask_before_pptx:
        return True
    readiness = str(preview.get("readiness") or "")
    return readiness in {"READY_WITH_TOPIC_CAVEAT", "READY_WITH_LIMITATIONS"}


def _period_label(start_date: str, end_date: str) -> str:
    return start_date if start_date == end_date else f"{start_date} s/d {end_date}"


def create_daily_social_report_workflow(
    *,
    project_name: str,
    start_date: str,
    end_date: str | None = None,
    audience: str | None = None,
    report_pov: str | None = None,
    client_brand: str | None = None,
    topic_taxonomy_version: str | None = None,
    confirmed_intent_id: str | None = None,
    analysis_objective: str | None = None,
    channels: str | Iterable[str] | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
    output_mode: str = "preview_and_package",
    include_evidence_limit: int = 10,
    allow_partial: bool = True,
    require_audience: bool = True,
    ask_before_pptx: bool = True,
) -> dict[str, Any]:
    """Run the Daily Social report workflow from a short user request.

    Parameters are intentionally compact so Claude can call this after parsing a
    sentence like: "Buatkan daily report Gojek tanggal 8 Mei 2026".

    This function never calls get_unclassified_topic_batch and never performs LLM
    classification. It reuses an active/provided taxonomy if available and returns
    a clear recommendation when topic enrichment is still needed.
    """
    project_name = _clean(project_name)
    start_date = _clean(start_date)
    end_date = _clean(end_date) or start_date
    if not project_name:
        raise DailySocialWorkflowError("project_name wajib diisi.")
    if not start_date:
        raise DailySocialWorkflowError("start_date wajib diisi dalam format YYYY-MM-DD.")

    if require_audience and not _clean(audience) and not _clean(report_pov):
        return audience_clarification_payload(project_name, _period_label(start_date, end_date))

    audience_context = normalize_audience_context(audience, report_pov)
    channel_list = _csv_list(channels)
    keyword_list = _csv_list(keywords)
    exclude_keyword_list = _csv_list(exclude_keywords)

    taxonomy_source = "provided"
    selected_taxonomy_version = _clean(topic_taxonomy_version) or None
    if not selected_taxonomy_version:
        selected_taxonomy_version = _active_taxonomy_version(project_name)
        taxonomy_source = "active_taxonomy" if selected_taxonomy_version else "none"

    topic_status_before = _topic_status(
        project_name=project_name,
        taxonomy_version=selected_taxonomy_version,
        start_date=start_date,
        end_date=end_date,
        channels=channel_list,
        keywords=keyword_list,
        exclude_keywords=exclude_keyword_list,
        match_mode=match_mode,
    )

    intent_id = _clean(confirmed_intent_id) or (
        "workflow_daily_social_"
        + project_name.lower().replace(" ", "_")
        + "_"
        + start_date.replace("-", "")
        + "_"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )

    request = {
        "project_name": project_name,
        "start_date": start_date,
        "end_date": end_date,
        "confirmed_intent_id": intent_id,
        "channels": tuple(channel_list),
        "data_scope": "brand",
        "client_brand": _clean(client_brand) or project_name,
        "competitor_brands": (),
        "analysis_objective": _clean(analysis_objective) or DEFAULT_ANALYSIS_OBJECTIVE,
        "audience_context": audience_context,
        "scope": {
            "channels": channel_list,
            "universe": "brand",
            "topic_taxonomy_version": selected_taxonomy_version,
            "keywords": keyword_list,
            "exclude_keywords": exclude_keyword_list,
            "match_mode": match_mode,
        },
        "metric_readiness": {},
        "data_health": {},
    }

    report_input = prepare_report_input(
        report_type_id=REPORT_TYPE_ID,
        request=request,
        persist=True,
    )
    report_input_id = report_input["report_input_id"]

    preview = build_daily_social_report_data_preview(
        report_input_id,
        include_evidence_limit=int(include_evidence_limit),
    )
    preview["audience_context"] = audience_context
    preview["markdown"] = (
        f"**Target reader / POV:** {audience_context['audience']} — {audience_context['primary_question']}\n\n"
        + preview.get("markdown", "")
    )

    outline = build_report_outline_from_id(report_input_id, allow_partial=allow_partial)
    package = None
    if output_mode in {"preview_and_package", "package", "ppt_package"}:
        package = build_daily_social_report_package(
            report_input_id,
            allow_partial=allow_partial,
            audience_context=audience_context["audience"],
            audience_pov=audience_context["primary_question"],
        )

    needs_confirmation = _needs_ppt_confirmation(preview, bool(ask_before_pptx))
    topic_note = preview.get("topic_coverage_note") or {}

    return {
        "success": True,
        "workflow_version": "daily_social_report_workflow_v1",
        "workflow_status": "READY_FOR_PREVIEW_AND_PPT_PACKAGE" if package else "READY_FOR_PREVIEW",
        "report_type_id": REPORT_TYPE_ID,
        "project_name": project_name,
        "period": {"start_date": start_date, "end_date": end_date},
        "audience_context": audience_context,
        "taxonomy_strategy": {
            "selected_taxonomy_version": selected_taxonomy_version,
            "source": taxonomy_source,
            "does_not_spend_claude_usage": True,
            "note": (
                "Workflow ini tidak melakukan batch topic enrichment otomatis. "
                "Ia hanya memakai taxonomy/cache yang sudah ada agar aman untuk usage Claude."
            ),
        },
        "topic_enrichment_status_before_prepare": topic_status_before,
        "report_input_id": report_input_id,
        "validation_status": (report_input.get("validation") or {}).get("status"),
        "outline_id": outline.get("outline_id"),
        "outline_status": outline.get("outline_status"),
        "data_preview": preview,
        "render_package": package,
        "pptx_policy": {
            "needs_user_confirmation_before_pptx": needs_confirmation,
            "reason": (
                "Preview harus ditampilkan dulu sebelum PPTX, terutama untuk memastikan audience/POV, URL evidence, dan caveat topic coverage sudah diterima user."
                if needs_confirmation
                else "Data readiness cukup; Claude dapat lanjut membuat PPTX dari render_package bila user memang meminta output PPTX."
            ),
        },
        "user_facing_summary": {
            "readiness": preview.get("readiness"),
            "posture": (preview.get("posture") or {}).get("label"),
            "topic_coverage_message": topic_note.get("message"),
            "suggested_next_message_to_user": (
                "Saya sudah siapkan preview data Task 1. Cek dulu ringkasan data, URL evidence, dan caveat coverage. "
                "Kalau sudah oke, saya lanjut buat PPTX."
            ),
        },
        "claude_instructions": [
            "If workflow_status is NEEDS_AUDIENCE, ask the clarification_question and do not create the report yet.",
            "Show data_preview.markdown to the user before creating PPTX unless the user explicitly asks to skip preview.",
            "When creating PPTX, use render_package.slides and render_package.ppt_style_brief exactly; do not invent metrics, URLs, snippets, or topics.",
            "Adapt narrative to audience_context. Keep Action Plan slide immediately after Executive Summary.",
            "If topic coverage is low, label topic insights as early classified topic signal and keep the limitation visible.",
        ],
    }


__all__ = ["create_daily_social_report_workflow", "DailySocialWorkflowError"]
