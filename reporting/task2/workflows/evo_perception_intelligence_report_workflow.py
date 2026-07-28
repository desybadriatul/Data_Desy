"""Jalur 1 workflow for EVO Perception Intelligence."""

from __future__ import annotations

from collections.abc import Iterable
import json
from typing import Any

from database import db
from reporting.enrichment.evo_attribute_batch_builder import (
    get_evo_attribute_enrichment_status,
    get_unclassified_evo_attribute_batch,
)
from reporting.task1.report_input_dispatcher import prepare_report_input
from reporting.task2.renderers.evo_perception_intelligence_report_renderer import (
    build_evo_report_data_preview,
)


REPORT_TYPE_ID = "evo_perception_intelligence"
WORKFLOW_VERSION = "evo_perception_intelligence_workflow_v1"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _list(value: str | Iterable[str] | None) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        values = value.split(",")
    else:
        values = list(value)
    result: list[str] = []
    seen: set[str] = set()
    for item in values:
        clean = _clean(item)
        if clean and clean.casefold() not in seen:
            result.append(clean)
            seen.add(clean.casefold())
    return result


def _metric_health_snapshots(
    *,
    brands: list[str],
    start_date: str,
    end_date: str,
    channels: list[str],
    keywords: list[str],
    exclude_keywords: list[str],
    match_mode: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Freeze metric readiness and data health for every compared brand."""

    readiness: dict[str, Any] = {"status": "PASS", "by_brand": {}}
    health: dict[str, Any] = {"status": "PASS", "by_brand": {}}
    for brand in brands:
        try:
            readiness_row = db.metric_readiness(
                brand,
                start_date,
                end_date,
                channels or None,
                keywords or None,
                exclude_keywords or None,
                match_mode,
            )
            health_row = db.data_health(
                brand,
                start_date,
                end_date,
                channels or None,
                keywords or None,
                exclude_keywords or None,
                match_mode,
            )
        except Exception as exc:
            readiness["status"] = "WARN"
            health["status"] = "WARN"
            readiness["by_brand"][brand] = {"error": str(exc)}
            health["by_brand"][brand] = {"error": str(exc)}
            continue
        readiness["by_brand"][brand] = readiness_row or {"status": "NOT_FOUND"}
        health["by_brand"][brand] = health_row or {"status": "NOT_FOUND"}
        if readiness_row is None:
            readiness["status"] = "WARN"
        if health_row is None:
            health["status"] = "WARN"

    # Decimal/date values from psycopg must be frozen as JSON-safe values.
    return (
        json.loads(json.dumps(readiness, default=str)),
        json.loads(json.dumps(health, default=str)),
    )


def create_evo_perception_intelligence_report_workflow(
    *,
    project_name: str,
    start_date: str,
    end_date: str | None = None,
    focus_brand: str | None = None,
    competitor_brands: str | Iterable[str] | None = None,
    primary_reader: str | None = None,
    desired_perception: str | None = None,
    attribute_map_source: str = "auto",
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    channels: str | Iterable[str] | None = None,
    match_mode: str = "any",
    analysis_objective: str | None = None,
    confirmed_intent_id: str | None = None,
    confirm_single_brand_fallback: bool = False,
    persist: bool = True,
) -> dict[str, Any]:
    focus = _clean(focus_brand) or _clean(project_name)
    reader = _clean(primary_reader)
    competitors = _list(competitor_brands)
    end = _clean(end_date) or _clean(start_date)
    channel_list = _list(channels)
    keyword_list = _list(keywords)
    exclude_list = _list(exclude_keywords)

    if not reader:
        return {
            "success": False,
            "workflow_status": "NEEDS_AUDIENCE",
            "report_type_id": REPORT_TYPE_ID,
            "clarification_question": "Report EVO ini dibuat untuk pembaca siapa?",
        }
    if not competitors and not confirm_single_brand_fallback:
        return {
            "success": False,
            "workflow_status": "NEEDS_BENCHMARK",
            "report_type_id": REPORT_TYPE_ID,
            "clarification_question": (
                "Sebutkan minimal satu competitor/benchmark, atau konfirmasi "
                "diagnosis single-brand tanpa Best Brand dan Attribute Gap."
            ),
        }

    status = get_evo_attribute_enrichment_status(
        focus_brand=focus,
        competitor_brands=competitors,
        start_date=start_date,
        end_date=end,
        channels=channel_list,
        keywords=keyword_list,
        exclude_keywords=exclude_list,
        match_mode=match_mode,
    )
    if not status.get("success"):
        return {
            "success": False,
            "workflow_status": "ATTRIBUTE_STATUS_ERROR",
            "report_type_id": REPORT_TYPE_ID,
            "error": status.get("error") or "Status attribute enrichment tidak tersedia.",
        }

    remaining = sum(
        int(row.get("remaining_to_target") or 0)
        for row in status.get("per_brand") or []
    )
    if remaining > 0:
        batch = get_unclassified_evo_attribute_batch(
            focus_brand=focus,
            competitor_brands=competitors,
            map_id=(status.get("attribute_map") or {}).get("map_id"),
            start_date=start_date,
            end_date=end,
            channels=channel_list,
            keywords=keyword_list,
            exclude_keywords=exclude_list,
            match_mode=match_mode,
            batch_size=min(100, remaining),
        )
        return {
            "success": False,
            "workflow_status": batch.get(
                "workflow_status",
                "NEEDS_AUTO_EVO_ATTRIBUTE_CLASSIFICATION",
            ),
            "report_type_id": REPORT_TYPE_ID,
            "requires_user_action": False,
            "requires_claude_action": True,
            "attribute_status": status,
            "attribute_batch": batch,
            "assistant_next_steps": [
                "Classify every returned post using classification_instruction.",
                "Call save_evo_attribute_batch_results(batch_id, results_json).",
                "Rerun this workflow until the sampling target is reached.",
                "Do not build a PPT before the Task 1 preview is confirmed.",
            ],
        }

    scope = {
        "focus_brand": focus,
        "primary_reader": reader,
        "desired_perception": _clean(desired_perception) or None,
        "attribute_map_source": _clean(attribute_map_source) or "auto",
        "evo_attribute_map_id": (status.get("attribute_map") or {}).get("map_id"),
        "keywords": keyword_list,
        "exclude_keywords": exclude_list,
        "match_mode": "all" if str(match_mode).casefold() == "all" else "any",
        "analysis_objective": _clean(analysis_objective) or None,
        "competitive_analysis": "available" if competitors else "unavailable",
    }
    metric_readiness, data_health = _metric_health_snapshots(
        brands=[focus, *competitors],
        start_date=start_date,
        end_date=end,
        channels=channel_list,
        keywords=keyword_list,
        exclude_keywords=exclude_list,
        match_mode=scope["match_mode"],
    )
    request = {
        "project_name": project_name,
        "start_date": start_date,
        "end_date": end,
        "confirmed_intent_id": (
            _clean(confirmed_intent_id)
            or f"{WORKFLOW_VERSION}:{focus.casefold().replace(' ', '_')}"
        ),
        "client_brand": focus,
        "competitor_brands": competitors,
        "channels": channel_list,
        "analysis_objective": _clean(analysis_objective) or None,
        "scope": scope,
        "metric_readiness": metric_readiness,
        "data_health": data_health,
    }
    try:
        report_input = prepare_report_input(
            report_type_id=REPORT_TYPE_ID,
            request=request,
            persist=persist,
        )
    except Exception as exc:
        return {
            "success": False,
            "workflow_status": "TASK1_FAILED",
            "report_type_id": REPORT_TYPE_ID,
            "error": str(exc),
        }

    report_input_id = report_input.get("report_input_id")
    if not report_input_id:
        return {
            "success": False,
            "workflow_status": "TASK1_FAILED",
            "report_type_id": REPORT_TYPE_ID,
            "error": "Task 1 tidak mengembalikan report_input_id.",
        }
    preview = build_evo_report_data_preview(report_input_id, allow_partial=True)
    return {
        "success": True,
        "workflow_version": WORKFLOW_VERSION,
        "workflow_status": "DATA_PREVIEW_READY",
        "report_type_id": REPORT_TYPE_ID,
        "project_name": project_name,
        "focus_brand": focus,
        "competitor_brands": competitors,
        "primary_reader": reader,
        "report_input_id": report_input_id,
        "attribute_status": status,
        "data_preview": preview,
        "requires_user_action": True,
        "requires_claude_action": False,
        "confirmation_question": "Data preview EVO sudah siap. Lanjut buat paket PPTX?",
        "assistant_next_steps": [
            "Show data_preview.markdown to the user.",
            "State classification coverage and limitations.",
            "After explicit confirmation, call "
            "build_evo_perception_intelligence_report_ppt_package with "
            "preview_confirmed=True.",
        ],
    }


__all__ = [
    "REPORT_TYPE_ID",
    "WORKFLOW_VERSION",
    "create_evo_perception_intelligence_report_workflow",
]
