"""One-command Mainstream Media Report workflow with smart auto-issue planning.

User-facing goal:
- User can ask: "Buatkan Mainstream Media Report Gojek tanggal 2026-05-08".
- Claude asks only the missing audience/reader.
- After audience is known, workflow prepares all non-LLM data from full canonical
  Online Media + Printmedia records.
- If media issue taxonomy/cache is missing or low, workflow returns continuation
  states so Claude can run a lightweight smart issue sample automatically.
- Workflow always returns a Task 1 data preview before PPT.
- PPT package is built only after preview confirmation.

Issue enrichment intentionally mirrors Daily Social topic enrichment:
Title + Content -> LLM issue taxonomy -> cached assignment -> reusable by future
reports/users. Raw Topic Extraction is never used as final issue source.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any, Mapping

from reporting.task1.report_input_dispatcher import prepare_report_input
from reporting.task2.report_outline_builder import build_report_outline_from_id
from reporting.task2.renderers.mainstream_media_report_renderer import (
    audience_clarification_payload,
    build_mainstream_media_report_data_preview,
    build_mainstream_media_report_package,
    normalize_audience_context,
)

REPORT_TYPE_ID = "mainstream_media_report"
DEFAULT_ANALYSIS_OBJECTIVE = "Mainstream Media Report Action-Plan-First"
DEFAULT_MAINSTREAM_CHANNELS = ["Online Media", "Printmedia"]
DEFAULT_ISSUE_RATIO = 0.10
DEFAULT_ISSUE_MIN_ARTICLES = 50
DEFAULT_ISSUE_MAX_ARTICLES = 100
DEFAULT_TAXONOMY_SAMPLE_SIZE = 40
MAX_ISSUE_BATCH_SIZE = 100


class MainstreamMediaWorkflowError(RuntimeError):
    """Raised when workflow cannot run safely."""


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


def _effective_issue_target(total_eligible: int, ratio: float, min_articles: int, max_articles: int) -> int:
    total_eligible = max(0, int(total_eligible or 0))
    if total_eligible <= 0:
        return 0
    ratio = max(0.01, min(float(ratio or DEFAULT_ISSUE_RATIO), 1.0))
    min_articles = max(1, int(min_articles or DEFAULT_ISSUE_MIN_ARTICLES))
    max_articles = max(min_articles, int(max_articles or DEFAULT_ISSUE_MAX_ARTICLES))
    if total_eligible <= min_articles:
        return total_eligible
    return min(total_eligible, max(min_articles, math.ceil(total_eligible * ratio)), max_articles)


def _active_taxonomy_version(project_name: str) -> str | None:
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
            "note": "Issue enrichment status tidak dapat dibaca; workflow tetap bisa lanjut dengan limitation dari Task 1.",
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
    issue_policy: Mapping[str, Any],
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
            "workflow_version": "mainstream_media_report_workflow_v3",
            "workflow_status": "AUTO_ISSUE_TAXONOMY_SAMPLE_ERROR",
            "requires_user_action": False,
            "requires_claude_action": False,
            "project_name": project_name,
            "period": {"start_date": start_date, "end_date": end_date},
            "audience_context": dict(audience_context),
            "error": str(exc),
            "fallback_instruction": "Lanjutkan prepare report tanpa issue taxonomy bila user butuh cepat; issue sections akan muncul sebagai limitation.",
        }

    return {
        "success": False,
        "workflow_version": "mainstream_media_report_workflow_v3",
        "workflow_status": "NEEDS_AUTO_ISSUE_TAXONOMY",
        "requires_user_action": False,
        "requires_claude_action": True,
        "project_name": project_name,
        "period": {"start_date": start_date, "end_date": end_date},
        "audience_context": dict(audience_context),
        "auto_issue_policy": dict(issue_policy),
        "suggested_taxonomy_version": suggested_taxonomy_version,
        "taxonomy_sample": sample,
        "assistant_next_steps": [
            "Do not ask the user to understand taxonomy/enrichment. Continue automatically.",
            "Create a compact mainstream-media issue taxonomy JSON from taxonomy_sample.sample_posts using Title + Content/Headline only. Use 6-10 substantive issues by default; maximum 12 if the sample is genuinely diverse, plus mandatory other_emerging_topic and not_relevant.",
            "Do not use raw Topic Extraction as the final issue source.",
            f"Use taxonomy_version '{suggested_taxonomy_version}' unless save_topic_taxonomy reports it already exists.",
            "Include mandatory topics: other_emerging_topic and not_relevant. Avoid over-fragmenting similar issues; this is a report issue taxonomy, not a raw entity taxonomy.",
            "Call save_topic_taxonomy(project_name, taxonomy_json, activate=True).",
            "Then call create_mainstream_media_report_workflow again with the saved taxonomy_version and same audience.",
            "Do not create PPTX yet; the workflow must show data preview first.",
        ],
        "user_visible_progress_message": "Saya akan membuat issue taxonomy ringan otomatis dari sample artikel berdampak, lalu menampilkan preview data sebelum PPT.",
    }


def _issue_batch_payload(
    *,
    project_name: str,
    taxonomy_version: str,
    start_date: str,
    end_date: str,
    channels: list[str],
    keywords: list[str],
    exclude_keywords: list[str],
    match_mode: str,
    target_articles: int,
    already_processed: int,
    audience_context: Mapping[str, Any],
    topic_status: Mapping[str, Any],
    issue_policy: Mapping[str, Any],
) -> dict[str, Any]:
    remaining_target = max(0, int(target_articles) - int(already_processed))
    batch_size = min(MAX_ISSUE_BATCH_SIZE, max(1, remaining_target))
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
            "workflow_version": "mainstream_media_report_workflow_v3",
            "workflow_status": "AUTO_ISSUE_BATCH_ERROR",
            "requires_user_action": False,
            "requires_claude_action": False,
            "project_name": project_name,
            "period": {"start_date": start_date, "end_date": end_date},
            "audience_context": dict(audience_context),
            "taxonomy_version": taxonomy_version,
            "topic_status": dict(topic_status),
            "error": str(exc),
            "fallback_instruction": "Lanjutkan prepare report dengan issue cache yang tersedia; jelaskan limitation bila coverage rendah.",
        }

    if batch.get("status") == "COMPLETE" or not batch.get("posts"):
        return {
            "success": False,
            "workflow_version": "mainstream_media_report_workflow_v3",
            "workflow_status": "AUTO_ISSUE_NO_BATCH_AVAILABLE",
            "requires_user_action": False,
            "requires_claude_action": False,
            "project_name": project_name,
            "period": {"start_date": start_date, "end_date": end_date},
            "audience_context": dict(audience_context),
            "taxonomy_version": taxonomy_version,
            "topic_status": dict(topic_status),
            "auto_issue_policy": dict(issue_policy),
            "note": "Tidak ada batch issue tersedia. Workflow dapat dilanjutkan dengan cache yang ada.",
        }

    return {
        "success": False,
        "workflow_version": "mainstream_media_report_workflow_v3",
        "workflow_status": "NEEDS_AUTO_ISSUE_CLASSIFICATION",
        "requires_user_action": False,
        "requires_claude_action": True,
        "project_name": project_name,
        "period": {"start_date": start_date, "end_date": end_date},
        "audience_context": dict(audience_context),
        "taxonomy_version": taxonomy_version,
        "topic_status_before_batch": dict(topic_status),
        "auto_issue_policy": dict(issue_policy),
        "target_issue_processed_articles": target_articles,
        "already_processed_articles": already_processed,
        "batch": batch,
        "assistant_next_steps": [
            "Do not ask the user to choose batch size or understand enrichment. Continue automatically.",
            "Classify every item in batch.posts into exactly one mainstream-media issue using batch.classification_instruction.",
            "Use Title + Content/Headline only. Do not use raw Topic Extraction as final issue.",
            "Return results in the required_result_shape exactly; preserve canonical_key. content_hash is server-managed and may be omitted.",
            "If classification_status is review_needed, primary_topic_id must be other_emerging_topic.",
            "Call save_topic_batch_results(batch_id, results_json).",
            "Then call create_mainstream_media_report_workflow again with same project, period, audience, and taxonomy_version.",
            "Do not fetch a second batch unless the workflow again returns NEEDS_AUTO_ISSUE_CLASSIFICATION.",
            "Do not create PPTX yet; show data preview first after workflow reaches READY_FOR_PREVIEW_AWAITING_USER_CONFIRMATION.",
        ],
        "user_visible_progress_message": f"Saya akan mengklasifikasikan smart sample issue otomatis sebanyak {len(batch.get('posts') or [])} artikel berdampak untuk melengkapi preview report tanpa memproses seluruh data.",
    }



def _classified_spokesperson_candidate_ids(
    *,
    project_name: str,
    taxonomy_version: str | None,
    start_date: str,
    end_date: str,
    channels: list[str],
    keywords: list[str],
    exclude_keywords: list[str],
    match_mode: str,
) -> list[int] | None:
    """Use only topic-classified relevant articles for spokesperson sampling."""

    if not taxonomy_version:
        return None
    try:
        from reporting.enrichment.topic_batch_builder import get_enriched_scope_posts

        enriched = get_enriched_scope_posts(
            project_name=project_name,
            taxonomy_version=taxonomy_version,
            start_date=start_date,
            end_date=end_date,
            channels=channels,
            keywords=keywords,
            exclude_keywords=exclude_keywords,
            match_mode=match_mode,
        )
    except Exception:
        return None

    ids: list[int] = []
    for post in enriched.get("posts") or []:
        assignment = post.get("topic_assignment") or {}
        if assignment.get("classification_status") != "classified":
            continue
        canonical_post_id = post.get("canonical_post_id")
        try:
            if canonical_post_id is not None:
                ids.append(int(canonical_post_id))
        except (TypeError, ValueError):
            continue
    return sorted(set(ids))

def _needs_ppt_confirmation(preview: dict[str, Any], ask_before_pptx: bool) -> bool:
    if ask_before_pptx:
        return True
    return str(preview.get("readiness") or "") in {"READY_WITH_ISSUE_CAVEAT", "READY_WITH_LIMITATIONS"}


def create_mainstream_media_report_workflow(
    *,
    project_name: str,
    start_date: str,
    end_date: str | None = None,
    audience: str | None = None,
    report_pov: str | None = None,
    client_brand: str | None = None,
    topic_taxonomy_version: str | None = None,
    issue_taxonomy_version: str | None = None,
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
    auto_issue_mode: str = "smart_sample",
    auto_issue_enabled: bool = True,
    issue_sample_ratio: float = DEFAULT_ISSUE_RATIO,
    issue_min_articles: int = DEFAULT_ISSUE_MIN_ARTICLES,
    issue_max_articles: int = DEFAULT_ISSUE_MAX_ARTICLES,
    taxonomy_sample_size: int = DEFAULT_TAXONOMY_SAMPLE_SIZE,
    force_skip_auto_issue: bool = False,
    auto_spokesperson_enabled: bool = True,
    spokesperson_llm_batch_size: int = 20,
    force_skip_auto_spokesperson: bool = False,
) -> dict[str, Any]:
    project_name = _clean(project_name)
    start_date = _clean(start_date)
    end_date = _clean(end_date) or start_date
    if not project_name:
        raise MainstreamMediaWorkflowError("project_name wajib diisi.")
    if not start_date:
        raise MainstreamMediaWorkflowError("start_date wajib diisi dalam format YYYY-MM-DD.")

    if require_audience and not _clean(audience) and not _clean(report_pov):
        payload = audience_clarification_payload(project_name, _period_label(start_date, end_date))
        payload["workflow_version"] = "mainstream_media_report_workflow_v3"
        payload["requires_user_action"] = True
        payload["requires_claude_action"] = False
        payload["note"] = "Audience/reader wajib karena narasi, action plan, dan level detail MMR akan disesuaikan."
        return payload

    audience_context = normalize_audience_context(audience, report_pov)
    channel_list = _csv_list(channels) or list(DEFAULT_MAINSTREAM_CHANNELS)
    keyword_list = _csv_list(keywords)
    exclude_keyword_list = _csv_list(exclude_keywords)
    auto_issue_mode = _clean(auto_issue_mode).casefold() or "smart_sample"
    auto_issue_enabled = bool(auto_issue_enabled) and not bool(force_skip_auto_issue) and auto_issue_mode not in {"off", "none", "cache_only"}

    taxonomy_source = "provided"
    selected_taxonomy_version = _clean(issue_taxonomy_version) or _clean(topic_taxonomy_version) or None
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

    issue_eligible = int(topic_status_before.get("topic_eligible_posts") or 0)
    target_articles = _effective_issue_target(
        issue_eligible,
        ratio=float(issue_sample_ratio or DEFAULT_ISSUE_RATIO),
        min_articles=int(issue_min_articles or DEFAULT_ISSUE_MIN_ARTICLES),
        max_articles=int(issue_max_articles or DEFAULT_ISSUE_MAX_ARTICLES),
    )
    classified = int(topic_status_before.get("classified") or 0)
    not_relevant = int(topic_status_before.get("not_relevant") or 0)
    processed = classified + not_relevant
    unclassified = int(topic_status_before.get("unclassified") or 0)

    issue_policy = {
        "mode": auto_issue_mode,
        "enabled": auto_issue_enabled,
        "full_data_used_for_kpi_sentiment_media_articles": True,
        "issue_sample_ratio": float(issue_sample_ratio or DEFAULT_ISSUE_RATIO),
        "issue_min_articles": int(issue_min_articles or DEFAULT_ISSUE_MIN_ARTICLES),
        "issue_max_articles": int(issue_max_articles or DEFAULT_ISSUE_MAX_ARTICLES),
        "taxonomy_sample_size": int(taxonomy_sample_size or DEFAULT_TAXONOMY_SAMPLE_SIZE),
        "issue_eligible_articles": issue_eligible,
        "target_issue_processed_articles": target_articles,
        "current_processed_articles": processed,
        "current_classified_articles": classified,
        "current_unclassified_articles": unclassified,
        "channels": channel_list,
        "raw_topic_extraction_policy": "not_used_as_final_report_issue",
        "usage_guardrail": "Default MMR request uses a fixed smart issue sample only, not full classification. Full canonical data is still used for KPI, sentiment, media contributors, and article evidence.",
        "allow_auto_expand": False,
        "hard_stop_at_target": True,
    }

    if auto_issue_enabled and issue_eligible > 0:
        if not selected_taxonomy_version or topic_status_before.get("status") == "NEEDS_TAXONOMY":
            suggested_version = f"{_slug(project_name)}_mmr_issue_auto_v1"
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
                issue_policy=issue_policy,
            )
        if processed < target_articles and unclassified > 0:
            return _issue_batch_payload(
                project_name=project_name,
                taxonomy_version=selected_taxonomy_version,
                start_date=start_date,
                end_date=end_date,
                channels=channel_list,
                keywords=keyword_list,
                exclude_keywords=exclude_keyword_list,
                match_mode=match_mode,
                target_articles=target_articles,
                already_processed=processed,
                audience_context=audience_context,
                topic_status=topic_status_before,
                issue_policy=issue_policy,
            )

    spokesperson_policy = {
        "enabled": bool(auto_spokesperson_enabled) and not bool(force_skip_auto_spokesperson),
        "runs_after_topic": True,
        "candidate_scope": "topic_classified_relevant_articles",
        "llm_batch_size": max(1, int(spokesperson_llm_batch_size or 20)),
    }
    if spokesperson_policy["enabled"]:
        try:
            from reporting.enrichment.spokesperson_enrichment_workflow import (
                prepare_spokesperson_enrichment_batch,
            )

            relevant_ids = _classified_spokesperson_candidate_ids(
                project_name=project_name,
                taxonomy_version=selected_taxonomy_version,
                start_date=start_date,
                end_date=end_date,
                channels=channel_list,
                keywords=keyword_list,
                exclude_keywords=exclude_keyword_list,
                match_mode=match_mode,
            )
            spokesperson_policy["topic_classified_candidate_count"] = (
                len(relevant_ids) if relevant_ids is not None else None
            )
            spk = prepare_spokesperson_enrichment_batch(
                client_brand=_clean(client_brand) or project_name,
                competitors=[],
                start_date=start_date,
                end_date=end_date,
                llm_batch_size=spokesperson_policy["llm_batch_size"],
                include_prompts=True,
                canonical_post_ids=relevant_ids,
            )
            if spk.get("workflow_status") == "NEEDS_AUTO_SPOKESPERSON_ENRICHMENT":
                spk.update(
                    {
                        "report_workflow": REPORT_TYPE_ID,
                        "workflow_version": "mainstream_media_report_workflow_v3",
                        "audience_context": audience_context,
                        "auto_issue_policy": issue_policy,
                        "spokesperson_policy": spokesperson_policy,
                        "locked_scope": {
                            "project_name": project_name,
                            "start_date": start_date,
                            "end_date": end_date,
                            "channels": channel_list,
                            "keywords": keyword_list,
                            "exclude_keywords": exclude_keyword_list,
                            "match_mode": match_mode,
                            "audience": audience_context.get("audience"),
                        },
                        "instruction_to_assistant": (
                            "Process only the returned prompt_batches, call "
                            "save_spokesperson_enrichment_response once per batch, then rerun "
                            "create_mainstream_media_report_workflow with the same locked scope. "
                            "Do not expand the issue sample and do not fetch social-media batches."
                        ),
                    }
                )
                return spk
            spokesperson_policy["status"] = spk.get("workflow_status")
            spokesperson_policy["cached_count"] = spk.get("cached_count", 0)
            spokesperson_policy["selected_count"] = spk.get("selected_count", 0)
        except Exception as exc:
            return {
                "success": False,
                "workflow_version": "mainstream_media_report_workflow_v3",
                "workflow_status": "SPOKESPERSON_ENRICHMENT_ERROR",
                "requires_user_action": False,
                "requires_claude_action": False,
                "error": str(exc),
                "locked_scope": {
                    "project_name": project_name,
                    "start_date": start_date,
                    "end_date": end_date,
                    "channels": channel_list,
                },
            }

    intent_id = _clean(confirmed_intent_id) or (
        "workflow_mmr_" + _slug(project_name) + "_" + start_date.replace("-", "") + "_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
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
            "issue_taxonomy_version": selected_taxonomy_version,
            "topic_taxonomy_version": selected_taxonomy_version,
            "keywords": keyword_list,
            "exclude_keywords": exclude_keyword_list,
            "match_mode": match_mode,
        },
        "metric_readiness": {},
        "data_health": {},
    }

    report_input = prepare_report_input(report_type_id=REPORT_TYPE_ID, request=request, persist=True)
    report_input_id = report_input["report_input_id"]
    preview = build_mainstream_media_report_data_preview(report_input_id, include_evidence_limit=int(include_evidence_limit))
    preview["audience_context"] = audience_context
    preview["auto_issue_policy"] = issue_policy
    preview["spokesperson_policy"] = spokesperson_policy
    preview["markdown"] = (
        f"**Target reader / POV:** {audience_context['audience']} — {audience_context['primary_question']}\n\n"
        + f"**Issue handling:** KPI/sentiment/media/article evidence memakai full canonical data; issue analysis memakai smart sample target {target_articles} artikel bila coverage belum full. Raw Topic Extraction tidak dipakai sebagai final issue.\n\n"
        + preview.get("markdown", "")
    )
    outline = build_report_outline_from_id(report_input_id, allow_partial=allow_partial)
    package = None
    if output_mode in {"preview_and_package", "package", "ppt_package"}:
        package = build_mainstream_media_report_package(report_input_id, allow_partial=allow_partial, audience_context=audience_context["audience"], audience_pov=audience_context["primary_question"])

    needs_confirmation = _needs_ppt_confirmation(preview, bool(ask_before_pptx))
    issue_note = preview.get("issue_coverage_note") or {}
    return {
        "success": True,
        "workflow_version": "mainstream_media_report_workflow_v3",
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
            "auto_issue_policy": issue_policy,
            "note": "Workflow memakai full canonical data untuk KPI/sentiment/media/article evidence. Issue analysis memakai cached taxonomy dan smart sample otomatis; Legal/Crisis/PR audiences get stronger brand-facing risk overlay and fact-vs-allegation guardrail.",
        },
        "issue_enrichment_status_before_prepare": topic_status_before,
        "spokesperson_policy": spokesperson_policy,
        "report_input_id": report_input_id,
        "validation_status": (report_input.get("validation") or {}).get("status"),
        "outline_id": outline.get("outline_id"),
        "outline_status": outline.get("outline_status"),
        "data_preview": preview,
        "render_package": package,
        "pptx_policy": {
            "needs_user_confirmation_before_pptx": needs_confirmation,
            "reason": "Preview harus ditampilkan dulu sebelum PPTX, terutama untuk memastikan audience/POV, URL evidence, dan caveat issue coverage sudah diterima user." if needs_confirmation else "Data readiness cukup; Claude dapat lanjut membuat PPTX dari render_package bila user memang meminta output PPTX.",
        },
        "user_facing_summary": {
            "readiness": preview.get("readiness"),
            "posture": (preview.get("posture") or {}).get("label"),
            "issue_coverage_message": issue_note.get("message"),
            "suggested_next_message_to_user": "Saya sudah siapkan preview data Task 1. KPI, sentiment, media, dan article evidence memakai full data. Issue memakai smart sample/cache untuk hemat usage. Cek dulu URL evidence dan caveat coverage; kalau sudah oke, saya lanjut buat PPTX.",
        },
        "claude_instructions": [
            "If workflow_status is NEEDS_AUDIENCE, ask clarification_question and do not create the report yet.",
            "If workflow_status is NEEDS_AUTO_ISSUE_TAXONOMY, create taxonomy JSON from taxonomy_sample and call save_topic_taxonomy automatically; do not ask the user about taxonomy.",
            "If workflow_status is NEEDS_AUTO_ISSUE_CLASSIFICATION, classify batch.posts and call save_topic_batch_results automatically; do not ask the user about batch/enrichment.",
            "For short MMR requests, follow only the returned continuation state. Never expand issue classification beyond auto_issue_policy.target_issue_processed_articles.",
            "Spokesperson enrichment runs only after topic readiness and only on topic-classified relevant articles.",
            "Show data_preview.markdown to the user before building any PPTX.",
            "Do not create PPTX until the user has seen the preview and explicitly confirms to continue.",
            "When creating PPTX, call build_mainstream_media_report_ppt_package with audience/report_pov and preview_confirmed=True.",
            "Use render_package.slides and render_package.ppt_style_brief exactly; do not invent metrics, URLs, headlines, snippets, or issues.",
        ],
    }


__all__ = ["create_mainstream_media_report_workflow", "MainstreamMediaWorkflowError"]

