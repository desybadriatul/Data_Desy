"""
Task 2 workflow: Brand & Content Effectiveness Report.

Orkestrator satu-perintah, mengikuti pola daily_social_report_workflow.py Fuji.

Alur (state machine lintas panggilan — Claude memanggil ulang tiap tahap):
  1. Audience belum ada        -> NEEDS_AUDIENCE          (tanya user)
  2. Taxonomy belum ada        -> NEEDS_AUTO_TOPIC_TAXONOMY (Claude bikin taxonomy)
  3. Sample topic belum cukup  -> NEEDS_AUTO_TOPIC_BATCH    (Claude klasifikasi)
  4. Data siap                 -> DATA_PREVIEW_READY        (tunggu konfirmasi user)
  5. User konfirmasi           -> PACKAGE_READY             (paket siap-PPT)

Prinsip:
- KPI / sentiment / channel / content SELALU memakai full canonical data.
- Hanya analisis TOPIC yang memakai smart sample (default 10%, min 20, max 100).
- Workflow TIDAK memanggil LLM sendiri. Dia mengembalikan instruksi untuk Claude.
- Tidak pernah membuat PPTX sebelum user melihat data preview.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Mapping
from typing import Any

from reporting.task1.report_input_dispatcher import prepare_report_input
from reporting.task2.renderers.bce_report_renderer import (
    audience_clarification_payload,
    build_bce_report_data_preview,
    build_bce_report_package,
    normalize_audience_context,
)

WORKFLOW_VERSION = "bce_report_workflow_v1"
REPORT_TYPE_ID = "brand_content_effectiveness"

# Smart topic sampling — samakan dengan aturan tim (Daily Social v5).
DEFAULT_TOPIC_RATIO = 0.10
DEFAULT_TOPIC_MIN_POSTS = 20
DEFAULT_TOPIC_MAX_POSTS = 100
DEFAULT_TAXONOMY_SAMPLE_SIZE = 40
MAX_TOPIC_BATCH_SIZE = 100


class BCEWorkflowError(RuntimeError):
    """Raised when the BCE workflow cannot proceed safely."""


# ----------------------------------------------------------------------
#  Helper
# ----------------------------------------------------------------------
def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _csv_list(value: str | Iterable[str] | None) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(item).strip() for item in value if str(item).strip()]


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _clean(value).casefold()).strip("_") or "project"


def _period_label(start_date: str, end_date: str) -> str:
    return f"{start_date} → {end_date}" if start_date != end_date else start_date


def _effective_topic_target(
    total_eligible: int, ratio: float, min_posts: int, max_posts: int
) -> int:
    """Smart sample: <= min -> semua; selain itu min(total, max(min, ceil(total*ratio)), max)."""
    total_eligible = max(0, int(total_eligible or 0))
    if total_eligible <= 0:
        return 0
    ratio = max(0.01, min(float(ratio or DEFAULT_TOPIC_RATIO), 1.0))
    min_posts = max(1, int(min_posts or DEFAULT_TOPIC_MIN_POSTS))
    max_posts = max(min_posts, int(max_posts or DEFAULT_TOPIC_MAX_POSTS))
    if total_eligible <= min_posts:
        return total_eligible
    return min(total_eligible,
               max(min_posts, math.ceil(total_eligible * ratio)),
               max_posts)


def _active_taxonomy_version(project_name: str) -> str | None:
    try:
        from reporting.enrichment.topic_store import get_active_taxonomy

        taxonomy = get_active_taxonomy(project_name)
        if taxonomy:
            return str(taxonomy.get("taxonomy_version") or "").strip() or None
    except Exception:
        return None
    return None


def _topic_status(**kwargs: Any) -> dict[str, Any]:
    try:
        from reporting.enrichment.topic_batch_builder import get_topic_enrichment_status

        return get_topic_enrichment_status(**kwargs) or {}
    except Exception as exc:
        return {
            "status": "UNKNOWN",
            "error": str(exc),
            "note": ("Topic enrichment status tidak terbaca; workflow tetap "
                     "bisa lanjut dengan limitation dari Task 1."),
        }


def _base_payload(status: str, project_name: str, start_date: str,
                  end_date: str, audience: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "success": False,
        "workflow_version": WORKFLOW_VERSION,
        "workflow_status": status,
        "report_type_id": REPORT_TYPE_ID,
        "project_name": project_name,
        "period": {"start_date": start_date, "end_date": end_date},
        "audience_context": dict(audience),
    }


# ----------------------------------------------------------------------
#  Payload: minta Claude membuat taxonomy
# ----------------------------------------------------------------------
def _taxonomy_seed_payload(
    *, project_name: str, start_date: str, end_date: str,
    channels: list[str], keywords: list[str], exclude_keywords: list[str],
    match_mode: str, taxonomy_sample_size: int, suggested_taxonomy_version: str,
    audience: Mapping[str, Any], topic_policy: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        from reporting.enrichment.topic_batch_builder import get_topic_taxonomy_sample

        sample = get_topic_taxonomy_sample(
            project_name=project_name, start_date=start_date, end_date=end_date,
            channels=channels, keywords=keywords, exclude_keywords=exclude_keywords,
            match_mode=match_mode, sample_size=int(taxonomy_sample_size),
        )
    except Exception as exc:
        payload = _base_payload("AUTO_TOPIC_TAXONOMY_SAMPLE_ERROR",
                                project_name, start_date, end_date, audience)
        payload.update({
            "requires_user_action": False,
            "requires_claude_action": False,
            "error": str(exc),
            "fallback_instruction": (
                "Lanjutkan prepare report tanpa taxonomy bila user butuh cepat; "
                "Content Format & Theme Effectiveness akan muncul sebagai limitation."
            ),
        })
        return payload

    payload = _base_payload("NEEDS_AUTO_TOPIC_TAXONOMY",
                            project_name, start_date, end_date, audience)
    payload.update({
        "requires_user_action": False,
        "requires_claude_action": True,
        "auto_topic_policy": dict(topic_policy),
        "suggested_taxonomy_version": suggested_taxonomy_version,
        "taxonomy_sample": sample,
        "assistant_next_steps": [
            "Jangan minta user memahami taxonomy/enrichment. Lanjutkan otomatis.",
            "Susun taxonomy JSON ringkas dari taxonomy_sample.sample_posts "
            "memakai Title + Content saja.",
            "Topic harus report-level (tema konten/brand), bukan entity "
            "(Person/Location/Company).",
            f"Pakai taxonomy_version '{suggested_taxonomy_version}' kecuali "
            "save_topic_taxonomy melaporkan versi itu sudah ada.",
            "Wajib sertakan topic: other_emerging_topic dan not_relevant.",
            "Panggil save_topic_taxonomy(project_name, taxonomy_json, activate=True).",
            "Lalu panggil create_bce_report_workflow lagi dengan "
            "taxonomy_version tersimpan dan audience yang sama.",
            "Jangan buat PPTX dulu; workflow harus menampilkan data preview.",
        ],
        "user_visible_progress_message": (
            "Saya akan membuat topic taxonomy konten otomatis dari sample "
            "post berdampak, lalu menampilkan preview data sebelum PPT."
        ),
    })
    return payload


# ----------------------------------------------------------------------
#  Payload: minta Claude mengklasifikasi batch
# ----------------------------------------------------------------------
def _topic_batch_payload(
    *, project_name: str, taxonomy_version: str, start_date: str, end_date: str,
    channels: list[str], keywords: list[str], exclude_keywords: list[str],
    match_mode: str, batch_size: int, audience: Mapping[str, Any],
    topic_policy: Mapping[str, Any], topic_status: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        from reporting.enrichment.topic_batch_builder import get_unclassified_topic_batch

        batch = get_unclassified_topic_batch(
            project_name=project_name, taxonomy_version=taxonomy_version,
            start_date=start_date, end_date=end_date, channels=channels,
            keywords=keywords, exclude_keywords=exclude_keywords,
            match_mode=match_mode, batch_size=int(batch_size),
        )
    except Exception as exc:
        payload = _base_payload("AUTO_TOPIC_BATCH_ERROR",
                                project_name, start_date, end_date, audience)
        payload.update({
            "requires_user_action": False, "requires_claude_action": False,
            "taxonomy_version": taxonomy_version,
            "topic_status": dict(topic_status), "error": str(exc),
            "fallback_instruction": (
                "Lanjutkan prepare report dengan topic cache yang tersedia; "
                "jelaskan limitation bila coverage rendah."
            ),
        })
        return payload

    if batch.get("status") == "COMPLETE" or not batch.get("posts"):
        payload = _base_payload("AUTO_TOPIC_NO_BATCH_AVAILABLE",
                                project_name, start_date, end_date, audience)
        payload.update({
            "requires_user_action": False, "requires_claude_action": False,
            "taxonomy_version": taxonomy_version,
            "topic_status": dict(topic_status),
            "auto_topic_policy": dict(topic_policy),
            "note": ("Tidak ada batch topic tersedia. Workflow dapat "
                     "dilanjutkan dengan cache yang ada."),
        })
        return payload

    payload = _base_payload("NEEDS_AUTO_TOPIC_BATCH",
                            project_name, start_date, end_date, audience)
    payload.update({
        "requires_user_action": False,
        "requires_claude_action": True,
        "taxonomy_version": taxonomy_version,
        "topic_status": dict(topic_status),
        "auto_topic_policy": dict(topic_policy),
        "topic_batch": batch,
        "assistant_next_steps": [
            "Klasifikasi SETIAP post di topic_batch.posts ke TEPAT SATU "
            "primary_topic_id dari taxonomy. Jangan bikin topic_id baru.",
            "Baca Title + Content saja. Jangan pakai raw Topic Extraction.",
            "Pakai not_relevant untuk post di luar scope brand/konten.",
            "review_needed wajib memakai other_emerging_topic + "
            "emerging_topic_detail.",
            "Panggil save_topic_batch_results(batch_id, results_json).",
            "Lalu panggil create_bce_report_workflow lagi dengan "
            "taxonomy_version dan audience yang sama.",
            "Jangan buat PPTX dulu; workflow harus menampilkan data preview.",
        ],
        "user_visible_progress_message": (
            "Saya sedang mengklasifikasi sample post berdampak ke topic "
            "konten, lalu menampilkan preview data sebelum PPT."
        ),
    })
    return payload


def _needs_ppt_confirmation(preview: Mapping[str, Any], ask_before_pptx: bool) -> bool:
    """Report dengan caveat WAJIB dikonfirmasi user sebelum dibuat PPTX."""
    if ask_before_pptx:
        return True
    readiness = str(preview.get("readiness") or "")
    return readiness in {"READY_WITH_TOPIC_CAVEAT", "READY_WITH_LIMITATIONS"}


# ----------------------------------------------------------------------
#  API publik
# ----------------------------------------------------------------------
def create_bce_report_workflow(
    *,
    project_name: str,
    start_date: str,
    end_date: str | None = None,
    audience: str | None = None,
    report_pov: str | None = None,
    client_brand: str | None = None,
    channels: str | Iterable[str] | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
    topic_taxonomy_version: str | None = None,
    auto_topic_enabled: bool = True,
    auto_topic_mode: str = "smart_sample",
    force_skip_auto_topic: bool = False,
    topic_sample_ratio: float = DEFAULT_TOPIC_RATIO,
    topic_min_posts: int = DEFAULT_TOPIC_MIN_POSTS,
    topic_max_posts: int = DEFAULT_TOPIC_MAX_POSTS,
    taxonomy_sample_size: int = DEFAULT_TAXONOMY_SAMPLE_SIZE,
    confirm_pptx: bool = False,
    ask_before_pptx: bool = True,
    persist: bool = True,
) -> dict[str, Any]:
    """Satu perintah untuk membuat Brand & Content Effectiveness Report end-to-end."""
    project_name = _clean(project_name)
    start_date = _clean(start_date)
    end_date = _clean(end_date) or start_date
    if not project_name or not start_date:
        raise BCEWorkflowError("project_name dan start_date wajib diisi.")

    period_label = _period_label(start_date, end_date)

    # --- TAHAP 1: audience wajib ---
    if not _clean(audience) and not _clean(report_pov):
        payload = audience_clarification_payload(project_name, period_label)
        payload["workflow_version"] = WORKFLOW_VERSION
        payload["report_type_id"] = REPORT_TYPE_ID
        payload["requires_user_action"] = True
        payload["requires_claude_action"] = False
        payload["note"] = (
            "Audience wajib karena narasi, action plan, dan level detail "
            "report akan disesuaikan."
        )
        return payload

    audience_ctx = normalize_audience_context(audience, report_pov)
    channel_list = _csv_list(channels)
    keyword_list = _csv_list(keywords)
    exclude_list = _csv_list(exclude_keywords)

    mode = _clean(auto_topic_mode).casefold() or "smart_sample"
    topic_enabled = (bool(auto_topic_enabled) and not bool(force_skip_auto_topic)
                     and mode not in {"off", "none", "cache_only"})

    taxonomy_version = _clean(topic_taxonomy_version) or None
    taxonomy_source = "provided"
    if not taxonomy_version:
        taxonomy_version = _active_taxonomy_version(project_name)
        taxonomy_source = "active_taxonomy" if taxonomy_version else "none"

    status_before = _topic_status(
        project_name=project_name, taxonomy_version=taxonomy_version,
        start_date=start_date, end_date=end_date, channels=channel_list,
        keywords=keyword_list, exclude_keywords=exclude_list, match_mode=match_mode,
    )

    eligible = int(status_before.get("topic_eligible_posts") or 0)
    target = _effective_topic_target(eligible, topic_sample_ratio,
                                     topic_min_posts, topic_max_posts)
    classified = int(status_before.get("classified") or 0)
    not_relevant = int(status_before.get("not_relevant") or 0)
    processed = classified + not_relevant

    topic_policy = {
        "mode": mode,
        "enabled": topic_enabled,
        "full_data_used_for_kpi_sentiment_channel_content": True,
        "topic_sample_ratio": float(topic_sample_ratio),
        "topic_min_posts": int(topic_min_posts),
        "topic_max_posts": int(topic_max_posts),
        "topic_eligible_posts": eligible,
        "target_topic_processed_posts": target,
        "current_processed_posts": processed,
        "current_classified_posts": classified,
        "taxonomy_source": taxonomy_source,
        "usage_guardrail": (
            "Default report memakai smart topic sample, bukan klasifikasi penuh. "
            "Full canonical data tetap dipakai untuk KPI, sentiment, channel, "
            "dan content views."
        ),
    }

    # --- TAHAP 2 & 3: auto topic enrichment ---
    if topic_enabled and eligible > 0:
        if not taxonomy_version or status_before.get("status") == "NEEDS_TAXONOMY":
            return _taxonomy_seed_payload(
                project_name=project_name, start_date=start_date, end_date=end_date,
                channels=channel_list, keywords=keyword_list,
                exclude_keywords=exclude_list, match_mode=match_mode,
                taxonomy_sample_size=taxonomy_sample_size,
                suggested_taxonomy_version=f"{_slug(project_name)}_content_topic_v1",
                audience=audience_ctx, topic_policy=topic_policy,
            )

        if processed < target:
            batch_size = min(MAX_TOPIC_BATCH_SIZE, max(1, target - processed))
            return _topic_batch_payload(
                project_name=project_name, taxonomy_version=taxonomy_version,
                start_date=start_date, end_date=end_date, channels=channel_list,
                keywords=keyword_list, exclude_keywords=exclude_list,
                match_mode=match_mode, batch_size=batch_size,
                audience=audience_ctx, topic_policy=topic_policy,
                topic_status=status_before,
            )

    # --- TAHAP 4: jalankan Task 1 & tampilkan preview ---
    request: dict[str, Any] = {
        "project_name": project_name,
        "start_date": start_date,
        "end_date": end_date,
        "confirmed_intent_id": f"{WORKFLOW_VERSION}:{_slug(project_name)}",
    }
    if client_brand:
        request["client_brand"] = _clean(client_brand)
    if channel_list:
        request["channels"] = channel_list
    scope: dict[str, Any] = {}
    if taxonomy_version:
        scope["topic_taxonomy_version"] = taxonomy_version
    if keyword_list:
        scope["keywords"] = keyword_list
    if exclude_list:
        scope["exclude_keywords"] = exclude_list
    if match_mode:
        scope["match_mode"] = match_mode
    if scope:
        request["scope"] = scope

    try:
        report_input = prepare_report_input(
            report_type_id=REPORT_TYPE_ID, request=request, persist=persist,
        )
    except Exception as exc:
        payload = _base_payload("TASK1_FAILED", project_name, start_date,
                                end_date, audience_ctx)
        payload["error"] = str(exc)
        payload["requires_user_action"] = True
        payload["requires_claude_action"] = False
        return payload

    report_input_id = report_input.get("report_input_id")
    if not report_input_id:
        raise BCEWorkflowError(
            "Task 1 tidak mengembalikan report_input_id; tidak bisa lanjut."
        )

    preview = build_bce_report_data_preview(
        report_input_id, audience_context=audience, audience_pov=report_pov,
    )

    if not confirm_pptx and _needs_ppt_confirmation(preview, ask_before_pptx):
        payload = _base_payload("DATA_PREVIEW_READY", project_name,
                                start_date, end_date, audience_ctx)
        payload.update({
            "requires_user_action": True,
            "requires_claude_action": False,
            "report_input_id": report_input_id,
            "auto_topic_policy": topic_policy,
            "data_preview": preview,
            "confirmation_question": (
                f"Data preview BCE {project_name} ({period_label}) "
                "sudah siap. Lanjut buat PPTX?"
            ),
            "assistant_next_steps": [
                "Tampilkan data_preview.markdown ke user.",
                "Sampaikan readiness & topic coverage apa adanya.",
                "Jangan buat PPTX sebelum user setuju.",
                "Setelah user setuju, panggil workflow ini lagi dengan "
                "confirm_pptx=True dan report_input_id yang sama.",
            ],
        })
        return payload

    # --- TAHAP 5: paket siap-PPT ---
    package = build_bce_report_package(
        report_input_id, audience_context=audience, audience_pov=report_pov,
    )
    return {
        "success": True,
        "workflow_version": WORKFLOW_VERSION,
        "workflow_status": "PACKAGE_READY",
        "report_type_id": REPORT_TYPE_ID,
        "project_name": project_name,
        "period": {"start_date": start_date, "end_date": end_date},
        "audience_context": dict(audience_ctx),
        "report_input_id": report_input_id,
        "auto_topic_policy": topic_policy,
        "data_preview": preview,
        "ppt_package": package,
        "assistant_next_steps": [
            "Render PPTX dari ppt_package.slides sesuai ppt_style_brief.",
            "Jangan mengarang metrik, quote, topic, atau URL.",
            "Komponen berstatus N/A tetap ditampilkan sebagai N/A.",
            "Sertakan source_url pada setiap evidence.",
        ],
    }


__all__ = [
    "create_bce_report_workflow",
    "BCEWorkflowError",
    "WORKFLOW_VERSION",
]
