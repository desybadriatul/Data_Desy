"""One-command Daily Social report workflow with smart auto-topic planning.

User-facing goal:
- User can ask: "Buatkan daily report Gojek tanggal 2026-05-08".
- Claude asks only the missing audience/reader.
- After audience is known, workflow prepares all non-LLM data from full canonical posts.
- If topic taxonomy/cache is missing or too low, workflow guides Claude to run a
  small smart topic sample automatically without asking the user to understand
  taxonomy/enrichment/batch jargon.
- Workflow always returns a Task 1 data preview before PPT.
- PPT package is built only after preview confirmation.

Important: Python cannot call Claude internally. Therefore taxonomy creation and
batch classification are returned as explicit continuation states for Claude to
execute with existing Cogan MCP tools. The user should not need to manage those
steps.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any, Mapping

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
DEFAULT_TOPIC_RATIO = 0.10
DEFAULT_TOPIC_MIN_POSTS = 20
DEFAULT_TOPIC_MAX_POSTS = 100
DEFAULT_TAXONOMY_SAMPLE_SIZE = 30
MAX_TOPIC_BATCH_SIZE = 100


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


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_")
    return slug or "project"


def _period_label(start_date: str, end_date: str) -> str:
    return start_date if start_date == end_date else f"{start_date} s/d {end_date}"


def _effective_topic_target(total_eligible: int, ratio: float, min_posts: int, max_posts: int) -> int:
    total_eligible = max(0, int(total_eligible or 0))
    if total_eligible <= 0:
        return 0
    ratio = max(0.01, min(float(ratio or DEFAULT_TOPIC_RATIO), 1.0))
    min_posts = max(1, int(min_posts or DEFAULT_TOPIC_MIN_POSTS))
    max_posts = max(min_posts, int(max_posts or DEFAULT_TOPIC_MAX_POSTS))
    if total_eligible <= min_posts:
        return total_eligible
    return min(total_eligible, max(min_posts, math.ceil(total_eligible * ratio)), max_posts)


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
            "note": "Topic enrichment status tidak dapat dibaca; workflow tetap bisa lanjut dengan limitation dari Task 1.",
        }


def _taxonomy_seed_payload(
    *,
    project_name: str,
    start_date: str,
    end_date: str,
    channels: list[str],
    keywords: list[str],
    exclude_keywords: list[str],
    match_mode: str,
    taxonomy_sample_size: int,
    suggested_taxonomy_version: str,
    audience_context: Mapping[str, Any],
    topic_policy: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        from reporting.enrichment.topic_batch_builder import get_topic_taxonomy_sample

        sample = get_topic_taxonomy_sample(
            project_name=project_name,
            start_date=start_date,
            end_date=end_date,
            channels=channels,
            keywords=keywords,
            exclude_keywords=exclude_keywords,
            match_mode=match_mode,
            sample_size=int(taxonomy_sample_size),
        )
    except Exception as exc:
        return {
            "success": False,
            "workflow_version": "daily_social_report_workflow_v5",
            "workflow_status": "AUTO_TOPIC_TAXONOMY_SAMPLE_ERROR",
            "requires_user_action": False,
            "requires_claude_action": False,
            "project_name": project_name,
            "period": {"start_date": start_date, "end_date": end_date},
            "audience_context": dict(audience_context),
            "error": str(exc),
            "fallback_instruction": (
                "Lanjutkan prepare report tanpa taxonomy bila user butuh cepat; "
                "Thematic Topics akan muncul sebagai limitation."
            ),
        }

    return {
        "success": False,
        "workflow_version": "daily_social_report_workflow_v5",
        "workflow_status": "NEEDS_AUTO_TOPIC_TAXONOMY",
        "requires_user_action": False,
        "requires_claude_action": True,
        "project_name": project_name,
        "period": {"start_date": start_date, "end_date": end_date},
        "audience_context": dict(audience_context),
        "auto_topic_policy": dict(topic_policy),
        "suggested_taxonomy_version": suggested_taxonomy_version,
        "taxonomy_sample": sample,
        "assistant_next_steps": [
            "Do not ask the user to understand taxonomy/enrichment. Continue automatically.",
            "Create a compact business-report taxonomy JSON from taxonomy_sample.sample_posts using Title + Content only.",
            f"Use taxonomy_version '{suggested_taxonomy_version}' unless save_topic_taxonomy reports it already exists.",
            "Include mandatory topics: other_emerging_topic and not_relevant.",
            "Call save_topic_taxonomy(project_name, taxonomy_json, activate=True).",
            "Then call create_daily_social_report_workflow again with the saved taxonomy_version and the same audience.",
            "Do not create PPTX yet; the workflow must show data preview first.",
        ],
        "user_visible_progress_message": (
            "Saya akan membuat topic taxonomy ringan otomatis dari sample post berdampak, "
            "lalu menampilkan preview data sebelum PPT."
        ),
    }


def _topic_batch_payload(
    *,
    project_name: str,
    taxonomy_version: str,
    start_date: str,
    end_date: str,
    channels: list[str],
    keywords: list[str],
    exclude_keywords: list[str],
    match_mode: str,
    target_posts: int,
    already_processed: int,
    audience_context: Mapping[str, Any],
    topic_status: Mapping[str, Any],
    topic_policy: Mapping[str, Any],
) -> dict[str, Any]:
    remaining_target = max(0, int(target_posts) - int(already_processed))
    batch_size = min(MAX_TOPIC_BATCH_SIZE, max(1, remaining_target))
    try:
        from reporting.enrichment.topic_batch_builder import get_unclassified_topic_batch

        batch = get_unclassified_topic_batch(
            project_name=project_name,
            taxonomy_version=taxonomy_version,
            start_date=start_date,
            end_date=end_date,
            channels=channels,
            keywords=keywords,
            exclude_keywords=exclude_keywords,
            match_mode=match_mode,
            batch_size=batch_size,
        )
    except Exception as exc:
        return {
            "success": False,
            "workflow_version": "daily_social_report_workflow_v5",
            "workflow_status": "AUTO_TOPIC_BATCH_ERROR",
            "requires_user_action": False,
            "requires_claude_action": False,
            "project_name": project_name,
            "period": {"start_date": start_date, "end_date": end_date},
            "audience_context": dict(audience_context),
            "taxonomy_version": taxonomy_version,
            "topic_status": dict(topic_status),
            "error": str(exc),
            "fallback_instruction": (
                "Lanjutkan prepare report dengan topic cache yang tersedia; "
                "jelaskan limitation bila coverage rendah."
            ),
        }

    if batch.get("status") == "COMPLETE" or not batch.get("posts"):
        return {
            "success": False,
            "workflow_version": "daily_social_report_workflow_v5",
            "workflow_status": "AUTO_TOPIC_NO_BATCH_AVAILABLE",
            "requires_user_action": False,
            "requires_claude_action": False,
            "project_name": project_name,
            "period": {"start_date": start_date, "end_date": end_date},
            "audience_context": dict(audience_context),
            "taxonomy_version": taxonomy_version,
            "topic_status": dict(topic_status),
            "auto_topic_policy": dict(topic_policy),
            "note": "Tidak ada batch topic tersedia. Workflow dapat dilanjutkan dengan cache yang ada.",
        }

    return {
        "success": False,
        "workflow_version": "daily_social_report_workflow_v5",
        "workflow_status": "NEEDS_AUTO_TOPIC_CLASSIFICATION",
        "requires_user_action": False,
        "requires_claude_action": True,
        "project_name": project_name,
        "period": {"start_date": start_date, "end_date": end_date},
        "audience_context": dict(audience_context),
        "taxonomy_version": taxonomy_version,
        "topic_status_before_batch": dict(topic_status),
        "auto_topic_policy": dict(topic_policy),
        "target_topic_processed_posts": target_posts,
        "already_processed_posts": already_processed,
        "batch": batch,
        "assistant_next_steps": [
            "Do not ask the user to choose batch size or understand enrichment. Continue automatically.",
            "Classify every post in batch.posts into exactly one taxonomy topic using batch.classification_instruction.",
            "Return results in the required_result_shape exactly; preserve canonical_key and content_hash.",
            "If classification_status is review_needed, primary_topic_id must be other_emerging_topic.",
            "Call save_topic_batch_results(batch_id, results_json).",
            "Then call create_daily_social_report_workflow again with the same project, period, audience, and taxonomy_version.",
            "Do not fetch a second batch unless the workflow again returns NEEDS_AUTO_TOPIC_CLASSIFICATION.",
            "Do not create PPTX yet; show data preview first after workflow reaches READY_FOR_PREVIEW_AWAITING_USER_CONFIRMATION.",
        ],
        "user_visible_progress_message": (
            f"Saya akan mengklasifikasikan smart sample topic otomatis sebanyak {len(batch.get('posts') or [])} post berdampak "
            "untuk melengkapi preview report tanpa memproses seluruh data."
        ),
    }


def _needs_ppt_confirmation(preview: dict[str, Any], ask_before_pptx: bool) -> bool:
    if ask_before_pptx:
        return True
    readiness = str(preview.get("readiness") or "")
    return readiness in {"READY_WITH_TOPIC_CAVEAT", "READY_WITH_LIMITATIONS"}


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
    output_mode: str = "preview_only",
    include_evidence_limit: int = 10,
    allow_partial: bool = True,
    require_audience: bool = True,
    ask_before_pptx: bool = True,
    auto_topic_mode: str = "smart_sample",
    auto_topic_enabled: bool = True,
    topic_sample_ratio: float = DEFAULT_TOPIC_RATIO,
    topic_min_posts: int = DEFAULT_TOPIC_MIN_POSTS,
    topic_max_posts: int = DEFAULT_TOPIC_MAX_POSTS,
    taxonomy_sample_size: int = DEFAULT_TAXONOMY_SAMPLE_SIZE,
    force_skip_auto_topic: bool = False,
) -> dict[str, Any]:
    """Run Daily Social workflow from a short natural request.

    Default behavior for normal users:
    - Ask audience if omitted.
    - Use full canonical data for KPI/sentiment/author/content.
    - Auto-plan a small smart topic sample when taxonomy/cache is missing.
    - Show Task 1 preview before PPT.
    - Do not build PPTX/package until user confirms after preview.

    This function does not itself spend Claude tokens on classification. When
    topic work is needed, it returns machine-readable continuation states so
    Claude can create taxonomy/classifications automatically via existing MCP
    tools without asking the user about implementation details.
    """
    project_name = _clean(project_name)
    start_date = _clean(start_date)
    end_date = _clean(end_date) or start_date
    if not project_name:
        raise DailySocialWorkflowError("project_name wajib diisi.")
    if not start_date:
        raise DailySocialWorkflowError("start_date wajib diisi dalam format YYYY-MM-DD.")

    if require_audience and not _clean(audience) and not _clean(report_pov):
        payload = audience_clarification_payload(project_name, _period_label(start_date, end_date))
        payload["workflow_version"] = "daily_social_report_workflow_v5"
        payload["requires_user_action"] = True
        payload["requires_claude_action"] = False
        payload["note"] = "Audience/reader wajib karena narasi, action plan, dan level detail report akan disesuaikan."
        return payload

    audience_context = normalize_audience_context(audience, report_pov)
    channel_list = _csv_list(channels)
    keyword_list = _csv_list(keywords)
    exclude_keyword_list = _csv_list(exclude_keywords)

    auto_topic_mode = _clean(auto_topic_mode).casefold() or "smart_sample"
    auto_topic_enabled = bool(auto_topic_enabled) and not bool(force_skip_auto_topic) and auto_topic_mode not in {"off", "none", "cache_only"}

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
    ) or {}

    topic_eligible = int(topic_status_before.get("topic_eligible_posts") or 0)
    target_posts = _effective_topic_target(
        topic_eligible,
        ratio=float(topic_sample_ratio or DEFAULT_TOPIC_RATIO),
        min_posts=int(topic_min_posts or DEFAULT_TOPIC_MIN_POSTS),
        max_posts=int(topic_max_posts or DEFAULT_TOPIC_MAX_POSTS),
    )
    classified = int(topic_status_before.get("classified") or 0)
    not_relevant = int(topic_status_before.get("not_relevant") or 0)
    processed = classified + not_relevant
    unclassified = int(topic_status_before.get("unclassified") or 0)

    topic_policy = {
        "mode": auto_topic_mode,
        "enabled": auto_topic_enabled,
        "full_data_used_for_kpi_sentiment_authors_content": True,
        "topic_sample_ratio": float(topic_sample_ratio or DEFAULT_TOPIC_RATIO),
        "topic_min_posts": int(topic_min_posts or DEFAULT_TOPIC_MIN_POSTS),
        "topic_max_posts": int(topic_max_posts or DEFAULT_TOPIC_MAX_POSTS),
        "taxonomy_sample_size": int(taxonomy_sample_size or DEFAULT_TAXONOMY_SAMPLE_SIZE),
        "topic_eligible_posts": topic_eligible,
        "target_topic_processed_posts": target_posts,
        "current_processed_posts": processed,
        "current_classified_posts": classified,
        "current_unclassified_posts": unclassified,
        "usage_guardrail": (
            "Default report request uses smart topic sample only, not full classification. "
            "Full canonical data is still used for KPI, sentiment, author, and content views."
        ),
    }

    if auto_topic_enabled and topic_eligible > 0:
        if not selected_taxonomy_version or topic_status_before.get("status") == "NEEDS_TAXONOMY":
            suggested_version = f"{_slug(project_name)}_daily_social_auto_v1"
            return _taxonomy_seed_payload(
                project_name=project_name,
                start_date=start_date,
                end_date=end_date,
                channels=channel_list,
                keywords=keyword_list,
                exclude_keywords=exclude_keyword_list,
                match_mode=match_mode,
                taxonomy_sample_size=int(taxonomy_sample_size or DEFAULT_TAXONOMY_SAMPLE_SIZE),
                suggested_taxonomy_version=suggested_version,
                audience_context=audience_context,
                topic_policy=topic_policy,
            )

        if processed < target_posts and unclassified > 0:
            return _topic_batch_payload(
                project_name=project_name,
                taxonomy_version=selected_taxonomy_version,
                start_date=start_date,
                end_date=end_date,
                channels=channel_list,
                keywords=keyword_list,
                exclude_keywords=exclude_keyword_list,
                match_mode=match_mode,
                target_posts=target_posts,
                already_processed=processed,
                audience_context=audience_context,
                topic_status=topic_status_before,
                topic_policy=topic_policy,
            )

    intent_id = _clean(confirmed_intent_id) or (
        "workflow_daily_social_"
        + _slug(project_name)
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
    preview["auto_topic_policy"] = topic_policy
    preview["markdown"] = (
        f"**Target reader / POV:** {audience_context['audience']} — {audience_context['primary_question']}\n\n"
        + f"**Topic handling:** KPI/sentiment/author/content memakai full canonical data; thematic topic memakai smart sample target {target_posts} post bila coverage belum full.\n\n"
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
        "workflow_version": "daily_social_report_workflow_v5",
        "workflow_status": "READY_FOR_PREVIEW_AND_PPT_PACKAGE" if package else "READY_FOR_PREVIEW_AWAITING_USER_CONFIRMATION",
        "requires_user_action": True,
        "requires_claude_action": False,
        "report_type_id": REPORT_TYPE_ID,
        "project_name": project_name,
        "period": {"start_date": start_date, "end_date": end_date},
        "audience_context": audience_context,
        "taxonomy_strategy": {
            "selected_taxonomy_version": selected_taxonomy_version,
            "source": taxonomy_source,
            "auto_topic_policy": topic_policy,
            "note": (
                "Workflow memakai full canonical data untuk KPI/sentiment/author/content. "
                "Topic analysis memakai cached taxonomy dan smart sample otomatis agar hemat Claude usage."
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
                "Saya sudah siapkan preview data Task 1. KPI, sentiment, author, dan content memakai full data. "
                "Topic memakai smart sample/cache untuk hemat usage. Cek dulu URL evidence dan caveat coverage; kalau sudah oke, saya lanjut buat PPTX."
            ),
        },
        "claude_instructions": [
            "If workflow_status is NEEDS_AUDIENCE, ask clarification_question and do not create the report yet.",
            "If workflow_status is NEEDS_AUTO_TOPIC_TAXONOMY, create the taxonomy JSON from taxonomy_sample and call save_topic_taxonomy automatically; do not ask the user about taxonomy.",
            "If workflow_status is NEEDS_AUTO_TOPIC_CLASSIFICATION, classify batch.posts and call save_topic_batch_results automatically; do not ask the user about batch/enrichment.",
            "For short user requests, keep calling create_daily_social_report_workflow until it returns READY_FOR_PREVIEW_AWAITING_USER_CONFIRMATION.",
            "Show data_preview.markdown to the user before building any PPTX.",
            "Do not create PPTX until the user has seen the preview and explicitly confirms to continue.",
            "When creating PPTX, call build_daily_social_report_ppt_package with audience/report_pov and preview_confirmed=True.",
            "Use render_package.slides and render_package.ppt_style_brief exactly; do not invent metrics, URLs, snippets, or topics.",
            "Adapt narrative to audience_context. Keep Action Plan slide immediately after Executive Summary.",
            "If topic coverage is low, label topic insights as early classified topic signal and keep the limitation visible.",
        ],
    }


__all__ = ["create_daily_social_report_workflow", "DailySocialWorkflowError"]
