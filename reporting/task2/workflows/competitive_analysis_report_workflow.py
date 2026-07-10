"""One-command Competitive Analysis workflow v3.

User-facing goal:
- User can ask: "Buatkan Competitive Analysis Bluebird vs Gojek Grab 9-10 Juni".
- Claude asks only missing audience/brand universe.
- Workflow auto-gates LLM competitive topic/narrative enrichment before final preview.
- Task 1 preview is shown first; PPT package is built only after preview confirmation.

Topic policy v2:
- Raw Topic Extraction, legacy Aspect, and Entity Extraction are not core CA inputs.
- Competitive topics/narratives are created from Title + Content / Content via cached LLM taxonomy.
- Topic-level numbers are aggregated from classified canonical rows, so they are audit-able.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import Any

from database import db

from reporting.enrichment.topic_contract import (
    canonical_content_hash,
    canonical_key_from_values,
    topic_text_for_llm,
)
from reporting.enrichment.topic_store import (
    create_topic_batch,
    get_assignment_index,
    get_reserved_refs,
    get_taxonomy,
    list_taxonomies,
)
from reporting.task1.report_input_dispatcher import prepare_report_input
from reporting.task2.report_outline_builder import build_report_outline_from_id
from reporting.task2.renderers.competitive_analysis_report_renderer import (
    audience_clarification_payload,
    build_competitive_analysis_report_data_preview,
    build_competitive_analysis_report_package,
    competitors_clarification_payload,
    normalize_audience_context,
)


REPORT_TYPE_ID = "competitive_analysis"
WORKFLOW_VERSION = "competitive_analysis_report_workflow_v3"
DEFAULT_ANALYSIS_OBJECTIVE = "Competitive Analysis Action-Plan-First"
DEFAULT_CA_CHANNELS: list[str] = []


class CompetitiveAnalysisWorkflowError(RuntimeError):
    """Raised when workflow cannot run safely."""


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _csv_list(value: str | Iterable[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in re.split(r"[,;|]", value) if item.strip()]
    return [str(item).strip() for item in value if str(item).strip()]


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_")
    return slug or "project"


def _period_label(start_date: str, end_date: str) -> str:
    return start_date if start_date == end_date else f"{start_date} s/d {end_date}"


def _needs_ppt_confirmation(preview: dict[str, Any], ask_before_pptx: bool) -> bool:
    if ask_before_pptx:
        return True
    return str(preview.get("readiness") or "") in {"PARTIAL_PASS", "READY_WITH_LIMITATIONS", "READY_WITH_CAVEAT"}


def _flatten_lookup(record: Mapping[str, Any]) -> dict[str, Any]:
    lookup: dict[str, Any] = {}

    def add_map(item: Mapping[str, Any]) -> None:
        for key, value in item.items():
            if isinstance(key, str):
                norm = "".join(ch for ch in key.casefold() if ch.isalnum())
                lookup.setdefault(norm, value)

    add_map(record)
    for nested_key in ("raw", "raw_data", "payload", "data", "json", "metadata"):
        nested = record.get(nested_key)
        if isinstance(nested, Mapping):
            add_map(nested)
    return lookup


def _source_value(record: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        value = record.get(name)
        if value is not None and str(value).strip() != "":
            return value
    lookup = _flatten_lookup(record)
    for name in names:
        norm = "".join(ch for ch in name.casefold() if ch.isalnum())
        value = lookup.get(norm)
        if value is not None and str(value).strip() != "":
            return value
    return None


def _brand_key(value: str) -> str:
    return "".join(ch for ch in str(value or "").casefold() if ch.isalnum())


def _campaign_key(value: str) -> str:
    # More aggressive than _brand_key: removes accents and punctuation so
    # "Nestlé Pure Life", "Nestle PureLife", and "Nestle Pure Life" can resolve
    # to the same campaign when DB campaign names differ only by styling.
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return "".join(ch for ch in ascii_text.casefold() if ch.isalnum())


CAMPAIGN_ALIAS_KEYS: dict[str, str] = {
    # Known Sonar/Cogan AMDK naming variants. Keep this small and defensive;
    # exact DB campaign name still wins first.
    "aquaviva": "aquviva",
    "nestlepurelife": "nestlepurelife",
}


def _resolve_campaign_name(input_name: str, known_campaigns: Iterable[str] | None = None) -> str:
    clean = _clean(input_name)
    if not clean:
        return clean

    key = CAMPAIGN_ALIAS_KEYS.get(_campaign_key(clean), _campaign_key(clean))
    for campaign in known_campaigns or []:
        candidate = _clean(campaign)
        if not candidate:
            continue
        candidate_key = CAMPAIGN_ALIAS_KEYS.get(_campaign_key(candidate), _campaign_key(candidate))
        if candidate.casefold() == clean.casefold() or candidate_key == key:
            return candidate
    return clean


def _brand_match(text: str, candidates: Iterable[str]) -> str | None:
    haystack = _brand_key(text)
    if not haystack:
        return None
    for brand in candidates:
        key = _brand_key(brand)
        if key and (haystack == key or key in haystack or haystack in key):
            return brand
    return None


def _brand_universe(project_name: str, client_brand: str, competitors: list[str]) -> list[str]:
    raw = [client_brand or project_name, *competitors]
    result: list[str] = []
    seen: set[str] = set()
    for item in raw:
        clean = _clean(item)
        key = clean.casefold()
        if clean and key not in seen:
            result.append(clean)
            seen.add(key)
    return result


def _fetch_records(
    *,
    project_name: str,
    start_date: str,
    end_date: str,
    channels: list[str],
    keywords: list[str],
    exclude_keywords: list[str],
    match_mode: str,
    brand_universe: list[str] | None = None,
) -> list[Mapping[str, Any]]:
    """Fetch Competitive Analysis records campaign-first.

    CA must compare the client campaign plus each competitor campaign. The old
    workflow fetched only project_name, then tried to infer competitor content
    inside that single project; that fails when each brand is a separate Cogan
    campaign.
    """
    requested_campaigns = brand_universe or [project_name]
    fetched: list[Mapping[str, Any]] = []
    missing_campaigns: list[str] = []

    try:
        known_campaigns = db.list_campaigns()
    except Exception:
        known_campaigns = []

    for raw_campaign in requested_campaigns:
        requested_name = _clean(raw_campaign)
        if not requested_name:
            continue

        campaign_name = _resolve_campaign_name(requested_name, known_campaigns)
        raw_records = db.fetch_raw_records(
            campaign_name,
            start_date,
            end_date,
            None,
            keywords or None,
            exclude_keywords or None,
            match_mode or "any",
            channels or None,
        )
        if raw_records is None:
            missing_campaigns.append(requested_name)
            continue

        seen_within_campaign: set[str] = set()
        count = 0
        for record in raw_records:
            item = dict(record or {})
            canonical_id = _source_value(item, "_cogan_canonical_post_id", "ID", "id", "Post ID")
            url = _source_value(item, "_cogan_url", "Link URL", "URL", "Url", "Source URL")
            dedupe_key = str(canonical_id or url or count)
            if dedupe_key in seen_within_campaign:
                continue
            seen_within_campaign.add(dedupe_key)
            item["_cogan_campaign_scope"] = campaign_name
            item["_cogan_requested_campaign"] = requested_name
            fetched.append(item)
            count += 1

        if count == 0:
            missing_campaigns.append(requested_name)

    # Very defensive fallback for legacy/single-project installs only.
    if not fetched and project_name:
        raw_records = db.fetch_raw_records(
            project_name,
            start_date,
            end_date,
            None,
            keywords or None,
            exclude_keywords or None,
            match_mode or "any",
            channels or None,
        )
        if raw_records is None:
            raise CompetitiveAnalysisWorkflowError(
                "Tidak ada campaign yang ditemukan untuk Competitive Analysis: "
                + ", ".join(requested_campaigns)
            )
        for record in raw_records:
            item = dict(record or {})
            item["_cogan_campaign_scope"] = project_name
            item["_cogan_requested_campaign"] = project_name
            fetched.append(item)

    return fetched


def _candidate_refs(records: list[Mapping[str, Any]], brand_universe: list[str]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for record in records:
        title = _clean(_source_value(record, "Title", "Headline", "Judul"))
        content = _clean(_source_value(record, "Content", "Caption", "Text", "Article", "Body", "Isi"))
        campaign_scope = _clean(_source_value(record, "_cogan_campaign_scope", "_cogan_requested_campaign"))
        campaign = _clean(_source_value(record, "Campaigns", "Campaign", "Brand", "Tag", "Client", "Company", "Project", "_cogan_campaign"))
        author = _clean(_source_value(record, "Author", "Username", "Account", "Author Name", "Media Name", "Publisher"))
        channel = _clean(_source_value(record, "Channel", "Source", "Platform", "Media Type", "_cogan_channel"))
        url = _clean(_source_value(record, "Link URL", "URL", "Url", "Source URL", "_cogan_url"))
        canonical_id = _source_value(record, "_cogan_canonical_post_id", "ID", "id", "Post ID")
        brand = _brand_match(campaign_scope, brand_universe)
        if not brand:
            brand = _brand_match(campaign, brand_universe)
        if not brand:
            brand = _brand_match(" ".join([title, content, author]), brand_universe)
        if not brand and len(brand_universe) == 1:
            brand = brand_universe[0]
        if not brand:
            continue
        try:
            canonical_key = canonical_key_from_values(url=url, canonical_post_id=canonical_id)
            content_hash = canonical_content_hash(title, content)
        except Exception:
            continue
        key = (canonical_key, content_hash)
        if key in seen:
            continue
        seen.add(key)
        text_for_llm = topic_text_for_llm(title, content)
        refs.append(
            {
                "canonical_key": canonical_key,
                "content_hash": content_hash,
                "canonical_post_id": canonical_id,
                "brand": brand,
                "campaign_scope": campaign_scope or campaign,
                "title": title[:160],
                "content_excerpt": content[:700],
                "topic_text": text_for_llm,
                "channel": channel,
                "author": author,
                "source_url": url,
            }
        )
    return refs


def _balanced_select(refs: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    by_brand: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ref in refs:
        by_brand[_clean(ref.get("brand")) or "(unknown)"].append(ref)
    selected: list[dict[str, Any]] = []
    brands = sorted(by_brand, key=lambda brand: (-len(by_brand[brand]), brand.casefold()))
    while len(selected) < limit and any(by_brand.values()):
        for brand in brands:
            if by_brand[brand] and len(selected) < limit:
                selected.append(by_brand[brand].pop(0))
    return selected


def _taxonomy_version_suggestion(project_name: str, start_date: str) -> str:
    return f"{_slug(project_name)}_competitive_topic_{start_date.replace('-', '')}_v1"[:80]


def _find_competitive_taxonomy(project_name: str, taxonomy_version: str | None) -> dict[str, Any] | None:
    if taxonomy_version:
        return get_taxonomy(project_name=project_name, taxonomy_version=taxonomy_version)
    taxonomies = list_taxonomies(project_name)
    candidates = []
    for item in taxonomies or []:
        version = _clean(item.get("taxonomy_version"))
        name = _clean(item.get("taxonomy_name"))
        blob = f"{version} {name}".casefold()
        if "competitive" in blob or "competitor" in blob or "ca_topic" in blob:
            candidates.append(item)
    if not candidates:
        return None
    candidates.sort(key=lambda item: _clean(item.get("updated_at") or item.get("created_at")), reverse=True)
    return candidates[0]


def _classification_target(total_eligible: int) -> int:
    if total_eligible <= 0:
        return 0
    if total_eligible <= 150:
        return total_eligible
    return min(max(math.ceil(total_eligible * 0.10), 100), 150)


def _topic_enrichment_gate(
    *,
    project_name: str,
    start_date: str,
    end_date: str,
    brand_universe: list[str],
    records: list[Mapping[str, Any]],
    topic_taxonomy_version: str | None,
) -> dict[str, Any] | None:
    refs = _candidate_refs(records, brand_universe)
    if not refs:
        return {
            "success": False,
            "workflow_version": WORKFLOW_VERSION,
            "workflow_status": "NEEDS_COMPETITIVE_SCOPE_DATA",
            "requires_user_action": True,
            "requires_claude_action": False,
            "message": "Tidak ada canonical content yang bisa dipetakan ke brand universe untuk competitive topic enrichment.",
            "brand_universe": brand_universe,
        }

    taxonomy = _find_competitive_taxonomy(project_name, topic_taxonomy_version)
    if not taxonomy:
        sample = _balanced_select(refs, min(len(refs), 60))
        return {
            "success": False,
            "workflow_version": WORKFLOW_VERSION,
            "workflow_status": "NEEDS_AUTO_COMPETITIVE_TAXONOMY",
            "requires_user_action": False,
            "requires_claude_action": True,
            "project_name": project_name,
            "period": {"start_date": start_date, "end_date": end_date},
            "brand_universe": brand_universe,
            "eligible_content_count": len(refs),
            "suggested_taxonomy_version": _taxonomy_version_suggestion(project_name, start_date),
            "taxonomy_sample": sample,
            "taxonomy_instruction": (
                "Claude must create a cross-brand Competitive Topic/Narrative taxonomy from taxonomy_sample only. "
                "Do not use raw Topic Extraction. Taxonomy must be fair across all brands, not client-only. "
                "Use 6-10 substantive topics plus other_emerging_topic and not_relevant. "
                "Topics should be auditable: every topic metric will be computed by assigning canonical rows to one topic. "
                "After creating taxonomy, call save_topic_taxonomy(project_name, taxonomy_json, activate=False), then rerun this workflow with topic_taxonomy_version."
            ),
            "required_taxonomy_json_shape": {
                "taxonomy_version": "lowercase_version_id",
                "taxonomy_name": "Competitive Topic/Narrative Taxonomy",
                "description": "Cross-brand topic/narrative taxonomy for Competitive Analysis.",
                "topics": [
                    {"topic_id": "service_quality", "label": "Service Quality", "description": "..."},
                    {"topic_id": "other_emerging_topic", "label": "Topik Baru / Perlu Review", "description": "..."},
                    {"topic_id": "not_relevant", "label": "Tidak Relevan", "description": "..."},
                ],
            },
        }

    taxonomy_version = _clean(taxonomy.get("taxonomy_version"))
    assignments = get_assignment_index(project_name=project_name, taxonomy_version=taxonomy_version, post_refs=refs)
    processed_keys = set(assignments)
    processed_count = len(processed_keys)
    classified_count = sum(1 for item in assignments.values() if _clean(item.get("classification_status")).casefold() == "classified")
    target = _classification_target(len(refs))
    if processed_count < target:
        reserved = get_reserved_refs(project_name=project_name, taxonomy_version=taxonomy_version)
        unprocessed = [
            ref for ref in refs
            if (ref["canonical_key"], ref["content_hash"]) not in processed_keys
            and (ref["canonical_key"], ref["content_hash"]) not in reserved
        ]
        batch_size = min(target - processed_count, len(unprocessed), 75)
        if batch_size <= 0:
            return {
                "success": False,
                "workflow_version": WORKFLOW_VERSION,
                "workflow_status": "WAITING_FOR_COMPETITIVE_TOPIC_BATCH_RESULTS",
                "requires_user_action": False,
                "requires_claude_action": True,
                "message": "Ada batch topic classification yang sedang issued/reserved. Simpan hasil batch tersebut atau tunggu expire sebelum membuat batch baru.",
                "taxonomy_version": taxonomy_version,
                "eligible_content_count": len(refs),
                "processed_count": processed_count,
                "target_classification_count": target,
            }
        selected = _balanced_select(unprocessed, batch_size)
        batch = create_topic_batch(
            project_name=project_name,
            taxonomy_version=taxonomy_version,
            scope={
                "workflow": WORKFLOW_VERSION,
                "report_type_id": REPORT_TYPE_ID,
                "period": {"start_date": start_date, "end_date": end_date},
                "brand_universe": brand_universe,
                "sampling_policy": "balanced_per_brand; classify all when <=150 eligible, otherwise 10% min100 max150",
            },
            post_refs=selected,
        )
        return {
            "success": False,
            "workflow_version": WORKFLOW_VERSION,
            "workflow_status": "NEEDS_AUTO_COMPETITIVE_TOPIC_CLASSIFICATION",
            "requires_user_action": False,
            "requires_claude_action": True,
            "project_name": project_name,
            "taxonomy": taxonomy,
            "taxonomy_version": taxonomy_version,
            "eligible_content_count": len(refs),
            "processed_count": processed_count,
            "classified_count": classified_count,
            "target_classification_count": target,
            "batch": batch,
            "classification_instruction": (
                "Claude must classify every post_ref in batch.post_refs using taxonomy.topics. "
                "Return exactly one result per post_ref, using canonical_key and content_hash unchanged. "
                "Do not create new topic_id. If content is outside all brands/report scope use not_relevant. "
                "After classification call save_topic_batch_results(batch_id, results_json), then rerun create_competitive_analysis_report_workflow with the same topic_taxonomy_version."
            ),
            "required_result_shape": {
                "canonical_key": "same as post_ref",
                "content_hash": "same as post_ref",
                "primary_topic_id": "one taxonomy topic_id",
                "classification_status": "classified | not_relevant | review_needed",
                "confidence": "high | medium | low",
                "classification_reason": "short evidence-based reason",
            },
        }
    return {
        "taxonomy_version": taxonomy_version,
        "eligible_content_count": len(refs),
        "processed_count": processed_count,
        "classified_count": classified_count,
        "target_classification_count": target,
        "coverage_pct": round(processed_count * 100 / len(refs), 1) if refs else 0,
    }


def create_competitive_analysis_report_workflow(
    *,
    project_name: str,
    start_date: str,
    end_date: str | None = None,
    audience: str | None = None,
    report_pov: str | None = None,
    client_brand: str | None = None,
    competitors: str | Iterable[str] | None = None,
    competitor_brands: str | Iterable[str] | None = None,
    confirmed_intent_id: str | None = None,
    analysis_objective: str | None = None,
    channels: str | Iterable[str] | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
    industry: str | None = None,
    market: str | None = None,
    topic_taxonomy_version: str | None = None,
    output_mode: str = "preview_only",
    include_evidence_limit: int = 10,
    allow_partial: bool = True,
    require_audience: bool = True,
    require_competitors: bool = True,
    ask_before_pptx: bool = True,
) -> dict[str, Any]:
    project_name = _clean(project_name)
    start_date = _clean(start_date)
    end_date = _clean(end_date) or start_date
    if not project_name:
        raise CompetitiveAnalysisWorkflowError("project_name wajib diisi.")
    if not start_date:
        raise CompetitiveAnalysisWorkflowError("start_date wajib diisi dalam format YYYY-MM-DD.")

    if require_audience and not _clean(audience) and not _clean(report_pov):
        payload = audience_clarification_payload(project_name, _period_label(start_date, end_date))
        payload["workflow_version"] = WORKFLOW_VERSION
        payload["requires_user_action"] = True
        payload["requires_claude_action"] = False
        return payload

    competitor_list = _csv_list(competitors) or _csv_list(competitor_brands)
    if require_competitors and not competitor_list:
        payload = competitors_clarification_payload(project_name)
        payload["workflow_version"] = WORKFLOW_VERSION
        payload["requires_user_action"] = True
        payload["requires_claude_action"] = False
        payload["known_client_brand"] = _clean(client_brand) or project_name
        return payload

    audience_context = normalize_audience_context(audience, report_pov)
    channel_list = _csv_list(channels) or list(DEFAULT_CA_CHANNELS)
    keyword_list = _csv_list(keywords)
    exclude_keyword_list = _csv_list(exclude_keywords)
    client = _clean(client_brand) or project_name
    brand_universe = _brand_universe(project_name, client, competitor_list)

    records = _fetch_records(
        project_name=project_name,
        start_date=start_date,
        end_date=end_date,
        channels=channel_list,
        keywords=keyword_list,
        exclude_keywords=exclude_keyword_list,
        match_mode=match_mode,
        brand_universe=brand_universe,
    )
    topic_gate = _topic_enrichment_gate(
        project_name=project_name,
        start_date=start_date,
        end_date=end_date,
        brand_universe=brand_universe,
        records=records,
        topic_taxonomy_version=_clean(topic_taxonomy_version) or None,
    )
    if topic_gate and topic_gate.get("workflow_status"):
        return topic_gate
    topic_meta = topic_gate if isinstance(topic_gate, Mapping) else {}
    taxonomy_version = _clean(topic_meta.get("taxonomy_version") or topic_taxonomy_version)

    intent_id = _clean(confirmed_intent_id) or (
        "workflow_ca_" + _slug(project_name) + "_" + start_date.replace("-", "") + "_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )

    request = {
        "project_name": project_name,
        "start_date": start_date,
        "end_date": end_date,
        "confirmed_intent_id": intent_id,
        "channels": tuple(channel_list),
        "data_scope": "competitive",
        "client_brand": client,
        "competitor_brands": tuple(competitor_list),
        "competitors": tuple(competitor_list),
        "analysis_objective": _clean(analysis_objective) or DEFAULT_ANALYSIS_OBJECTIVE,
        "audience_context": audience_context,
        "scope": {
            "channels": channel_list,
            "universe": "competitive",
            "client_brand": client,
            "competitor_brands": competitor_list,
            "brand_universe": brand_universe,
            "industry": _clean(industry) or None,
            "market": _clean(market) or None,
            "keywords": keyword_list,
            "exclude_keywords": exclude_keyword_list,
            "match_mode": match_mode,
            "topic_taxonomy_version": taxonomy_version,
            "competitive_topic_enrichment_target": dict(topic_meta),
            "topic_policy": "LLM Competitive Topic/Narrative taxonomy from Title + Content; raw Topic Extraction diagnostic only.",
            "entity_policy": "Entity Extraction not core; brand universe comes from request.",
            "aspect_policy": "Legacy aspect not core; use LLM topic/narrative drivers.",
            "url_policy": "main slides use Evidence ID; full URLs only in appendix/data pack",
        },
        "metric_readiness": {},
        "data_health": {},
    }

    report_input = prepare_report_input(report_type_id=REPORT_TYPE_ID, request=request, persist=True)
    report_input_id = report_input["report_input_id"]
    preview = build_competitive_analysis_report_data_preview(report_input_id, include_evidence_limit=int(include_evidence_limit))
    preview["audience_context"] = audience_context
    preview["markdown"] = (
        f"**Target reader / POV:** {audience_context['audience']} — {audience_context['primary_question']}\n\n"
        + f"**Competitive topic taxonomy:** `{taxonomy_version}` · processed {topic_meta.get('processed_count')}/{topic_meta.get('eligible_content_count')} canonical rows.\n\n"
        + "**Evidence handling:** main report pakai Evidence ID; full URL hanya di Appendix/Data Pack.\n\n"
        + preview.get("markdown", "")
    )
    outline = build_report_outline_from_id(report_input_id, allow_partial=allow_partial)
    package = None
    if output_mode in {"preview_and_package", "package", "ppt_package"}:
        package = build_competitive_analysis_report_package(
            report_input_id,
            allow_partial=allow_partial,
            audience_context=audience_context["audience"],
            audience_pov=audience_context["primary_question"],
        )

    needs_confirmation = _needs_ppt_confirmation(preview, bool(ask_before_pptx))
    return {
        "success": True,
        "workflow_version": WORKFLOW_VERSION,
        "workflow_status": "READY_FOR_PREVIEW_AND_PPT_PACKAGE" if package else "READY_FOR_PREVIEW_AWAITING_USER_CONFIRMATION",
        "requires_user_action": True,
        "requires_claude_action": False,
        "report_type_id": REPORT_TYPE_ID,
        "project_name": project_name,
        "period": {"start_date": start_date, "end_date": end_date},
        "audience_context": audience_context,
        "brand_universe": {"client_brand": client, "competitor_brands": competitor_list},
        "topic_taxonomy_version": taxonomy_version,
        "topic_enrichment_summary": dict(topic_meta),
        "report_input_id": report_input_id,
        "validation_status": (report_input.get("validation") or {}).get("status"),
        "outline_id": outline.get("outline_id"),
        "outline_status": outline.get("outline_status"),
        "data_preview": preview,
        "render_package": package,
        "pptx_policy": {
            "needs_user_confirmation_before_pptx": needs_confirmation,
            "reason": "Preview harus ditampilkan dulu sebelum PPTX, terutama untuk memastikan brand universe, SOV/SOE, LLM topic coverage, caveat, dan evidence ID sudah diterima user." if needs_confirmation else "Data readiness cukup; Claude dapat lanjut membuat PPTX dari render_package bila user memang meminta output PPTX.",
        },
        "user_facing_summary": {
            "readiness": preview.get("readiness"),
            "client_brand": client,
            "competitors": competitor_list,
            "suggested_next_message_to_user": "Saya sudah siapkan preview data Competitive Analysis. Cek dulu brand universe, SOV/SOE, topic/narrative coverage, evidence ID, dan caveat. Kalau sudah oke, saya lanjut buat PPTX.",
        },
        "claude_instructions": [
            "If workflow_status is NEEDS_AUDIENCE, ask the clarification_question and do not create report yet.",
            "If workflow_status is NEEDS_COMPETITORS, ask for client brand and competitor list; do not infer competitor universe silently.",
            "If workflow_status is NEEDS_AUTO_COMPETITIVE_TAXONOMY, create taxonomy JSON from taxonomy_sample and call save_topic_taxonomy with activate=False; then rerun this workflow.",
            "If workflow_status is NEEDS_AUTO_COMPETITIVE_TOPIC_CLASSIFICATION, classify the batch and call save_topic_batch_results; then rerun this workflow.",
            "Show data_preview.markdown to the user before building any PPTX.",
            "Do not create PPTX until the user has seen the preview and explicitly confirms to continue.",
            "When creating PPTX, call build_competitive_analysis_report_ppt_package with preview_confirmed=True.",
            "Use render_package.slides and ppt_style_brief exactly; do not invent metrics, URLs, brand names, competitor claims, or topic numbers.",
            "Do not place raw URLs in main slides; use Evidence IDs and Appendix URL index.",
        ],
    }


__all__ = ["create_competitive_analysis_report_workflow", "CompetitiveAnalysisWorkflowError"]
