"""Prepare incremental, stratified EVO attribute classification batches."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
import re
import unicodedata
from typing import Any

from database import db
from reporting.enrichment.evo_attribute_contract import (
    canonical_content_hash,
    canonical_key_from_values,
    classification_instruction,
    normalize_text,
)
from reporting.enrichment.evo_attribute_result_validator import (
    EVOAttributeResultValidationError,
    validate_evo_attribute_batch_results,
)
from reporting.enrichment.evo_attribute_sampling import (
    DEFAULT_INITIAL_MAX_PER_BRAND,
    DEFAULT_MIN_PER_BRAND,
    DEFAULT_SAMPLE_RATIO,
    MAX_BATCH_SIZE,
    MAX_TARGET_PER_BRAND,
    STRATIFICATION_DIMENSIONS,
    effective_evo_sample_target,
    select_stratified_posts,
)
from reporting.enrichment.evo_attribute_store import (
    EVOAttributeStoreError,
    create_evo_attribute_batch,
    get_assignment_index,
    get_evo_attribute_batch,
    get_reserved_refs,
    resolve_attribute_map,
    save_validated_batch_results,
)

DONE_STATUSES = frozenset({"classified", "not_relevant", "review_needed"})



class EVOAttributeBatchError(RuntimeError):
    """EVO attribute sampling/classification workflow cannot continue."""


def _safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        value = float(value)
        return int(value) if value.is_integer() else round(value, 4)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _number(value: Any) -> float:
    value = _safe(value)
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _terms(values: str | Iterable[str] | None) -> list[str]:
    if values is None:
        return []
    raw = re.split(r"[,;|]", values) if isinstance(values, str) else list(values)
    result: list[str] = []
    seen: set[str] = set()
    for value in raw:
        clean = normalize_text(value)
        key = clean.casefold()
        if clean and key not in seen:
            result.append(clean)
            seen.add(key)
    return result


def _source_value(record: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        value = record.get(name)
        if value is not None and str(value).strip() != "":
            return value
    return None


def _channel_norm(value: Any) -> str:
    raw = normalize_text(value).casefold()
    aliases = {
        "ig": "instagram",
        "instagram reels": "instagram",
        "fb": "facebook",
        "yt": "youtube",
        "tik tok": "tiktok",
        "twitter": "x",
        "twitter/x": "x",
        "x/twitter": "x",
        "online": "online_media",
        "online media": "online_media",
        "media online": "online_media",
        "news": "online_media",
        "print media": "printmedia",
        "printed media": "printmedia",
    }
    return aliases.get(raw, raw or "unknown")


def _campaign_key(value: Any) -> str:
    text = unicodedata.normalize("NFKD", normalize_text(value))
    ascii_text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return "".join(ch for ch in ascii_text.casefold() if ch.isalnum())


def _resolve_campaign_name(value: str, known: Iterable[str]) -> str:
    clean = normalize_text(value)
    key = _campaign_key(clean)
    for candidate in known:
        if _campaign_key(candidate) == key:
            return candidate
    return clean


def _parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = normalize_text(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def _period_bucket(value: Any, start_date: str | None) -> str:
    item_date = _parse_date(value)
    start = _parse_date(start_date)
    if not item_date or not start:
        return "period_unknown"
    day_offset = max(0, (item_date - start).days)
    return f"week_{day_offset // 7 + 1}"


def _source_type(channel_norm: str, ownership: Any) -> str:
    own = normalize_text(ownership).casefold()
    if "owned" in own:
        return "owned"
    if "earned" in own:
        return "earned"
    if channel_norm in {"online_media", "printmedia", "tv", "radio"}:
        return "mainstream"
    return "social"


def _normalise_post(
    record: Mapping[str, Any],
    *,
    project_name: str,
    campaign_id: int,
    start_date: str | None,
) -> dict[str, Any]:
    canonical_id = _source_value(record, "_cogan_canonical_post_id")
    url = _source_value(record, "_cogan_url", "Link URL", "URL", "Source URL")
    title = normalize_text(_source_value(record, "Title", "Headline"))
    content = normalize_text(_source_value(record, "Content", "Extracted Text"))
    channel = normalize_text(_source_value(record, "Channel", "_cogan_channel")) or "(tidak diketahui)"
    channel_norm = _channel_norm(channel)
    sentiment_raw = normalize_text(_source_value(record, "Sentiment")).casefold()
    sentiment = sentiment_raw if sentiment_raw in {"positive", "neutral", "negative"} else "unclassified"
    post_date = _safe(_source_value(record, "_cogan_post_date", "Date"))
    content_type = normalize_text(
        _source_value(record, "Media Type", "Content Type", "Type")
    ) or channel_norm
    ownership = _source_value(record, "Ownership", "Owned/Earned", "Content Ownership")
    canonical_post_id = None
    try:
        canonical_post_id = int(canonical_id) if canonical_id is not None else None
    except (TypeError, ValueError):
        canonical_post_id = None
    try:
        canonical_key = canonical_key_from_values(
            url=url,
            canonical_post_id=canonical_id,
        )
    except Exception:
        # This fallback is stable only within unchanged content and is used only
        # when the source genuinely lacks both URL and canonical ID.
        canonical_key = "hash:" + canonical_content_hash(title, content)
    return {
        "project_name": project_name,
        "campaign_id": campaign_id,
        "canonical_post_id": canonical_post_id,
        "canonical_key": canonical_key,
        "content_hash": canonical_content_hash(title, content),
        "post_date": post_date,
        "period_bucket": _period_bucket(post_date, start_date),
        "channel": channel,
        "channel_norm": channel_norm,
        "sentiment": sentiment,
        "content_type": content_type,
        "source_type": _source_type(channel_norm, ownership),
        "title": title,
        "content": content,
        "url": normalize_text(url) or None,
        "interactions": _number(_source_value(record, "_cogan_interactions")),
        "views": _number(_source_value(record, "_cogan_views")),
        "eligible": bool(title or content),
    }


def _scope(
    *,
    focus_brand: str,
    competitor_brands: Iterable[str],
    start_date: str | None,
    end_date: str | None,
    channels: str | Iterable[str] | None,
    keywords: str | Iterable[str] | None,
    exclude_keywords: str | Iterable[str] | None,
    match_mode: str,
) -> dict[str, Any]:
    competitors = _terms(competitor_brands)
    return {
        "focus_brand": normalize_text(focus_brand),
        "competitor_brands": competitors,
        "brand_universe": [normalize_text(focus_brand), *competitors],
        "start_date": normalize_text(start_date) or None,
        "end_date": normalize_text(end_date) or None,
        "channels": _terms(channels),
        "keywords": _terms(keywords),
        "exclude_keywords": _terms(exclude_keywords),
        "match_mode": "all" if normalize_text(match_mode).casefold() == "all" else "any",
        "universe": "issue_only" if _terms(keywords) or _terms(exclude_keywords) else "brand",
    }


def fetch_evo_scope_posts(
    *,
    focus_brand: str,
    competitor_brands: str | Iterable[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    channels: str | Iterable[str] | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    focus = normalize_text(focus_brand)
    if not focus:
        raise EVOAttributeBatchError("focus_brand wajib diisi.")
    competitors = _terms(competitor_brands)
    scope = _scope(
        focus_brand=focus,
        competitor_brands=competitors,
        start_date=start_date,
        end_date=end_date,
        channels=channels,
        keywords=keywords,
        exclude_keywords=exclude_keywords,
        match_mode=match_mode,
    )
    try:
        known_campaigns = db.list_campaigns()
    except Exception:
        known_campaigns = []

    posts: list[dict[str, Any]] = []
    missing: list[str] = []
    for requested in scope["brand_universe"]:
        campaign_name = _resolve_campaign_name(requested, known_campaigns)
        campaign_id = db.get_campaign_id(campaign_name)
        if campaign_id is None:
            missing.append(requested)
            continue
        try:
            records = db.fetch_raw_records(
                campaign_name,
                scope["start_date"],
                scope["end_date"],
                None,
                scope["keywords"] or None,
                scope["exclude_keywords"] or None,
                scope["match_mode"],
                scope["channels"] or None,
            )
        except Exception as exc:
            raise EVOAttributeBatchError(
                f"Gagal menarik canonical post '{campaign_name}': {exc}"
            ) from exc
        if records is None:
            missing.append(requested)
            continue
        seen: set[tuple[str, str]] = set()
        for record in records:
            post = _normalise_post(
                record,
                project_name=campaign_name,
                campaign_id=int(campaign_id),
                start_date=scope["start_date"],
            )
            key = (post["canonical_key"], post["content_hash"])
            if key in seen:
                continue
            seen.add(key)
            posts.append(post)
    scope["missing_campaigns"] = missing
    return posts, scope


def _post_ref(post: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "project_name": post["project_name"],
        "campaign_id": post["campaign_id"],
        "canonical_post_id": post.get("canonical_post_id"),
        "canonical_key": post["canonical_key"],
        "content_hash": post["content_hash"],
        "sample_reasons": list(post.get("sample_reasons") or []),
    }


def _llm_post(post: Mapping[str, Any]) -> dict[str, Any]:
    text = "\n".join(
        part for part in (normalize_text(post.get("title")), normalize_text(post.get("content"))) if part
    )
    return {
        "project_name": post["project_name"],
        "canonical_post_id": post.get("canonical_post_id"),
        "canonical_key": post["canonical_key"],
        "content_hash": post["content_hash"],
        "date": post.get("post_date"),
        "channel": post.get("channel"),
        "sentiment": post.get("sentiment"),
        "content_type": post.get("content_type"),
        "source_type": post.get("source_type"),
        "period_bucket": post.get("period_bucket"),
        "engagement_tier": post.get("engagement_tier"),
        "interactions": post.get("interactions"),
        "views": post.get("views"),
        "selection_reasons": list(post.get("sample_reasons") or []),
        "text": text[:5000],
    }


def _brand_posts(posts: list[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for post in posts:
        grouped[str(post["project_name"])].append(dict(post))
    return grouped


def get_evo_attribute_enrichment_status(
    *,
    focus_brand: str,
    competitor_brands: str | Iterable[str] | None = None,
    map_id: str | None = None,
    category: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    channels: str | Iterable[str] | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
    target_per_brand: int | None = None,
) -> dict[str, Any]:
    attribute_map = resolve_attribute_map(
        project_name=focus_brand,
        map_id=map_id,
        category=category,
    )
    posts, scope = fetch_evo_scope_posts(
        focus_brand=focus_brand,
        competitor_brands=competitor_brands,
        start_date=start_date,
        end_date=end_date,
        channels=channels,
        keywords=keywords,
        exclude_keywords=exclude_keywords,
        match_mode=match_mode,
    )
    reserved = get_reserved_refs(map_id=attribute_map["map_id"])
    grouped = _brand_posts(posts)
    per_brand: list[dict[str, Any]] = []
    totals = Counter()
    for brand in scope["brand_universe"]:
        actual_brand = next((name for name in grouped if _campaign_key(name) == _campaign_key(brand)), brand)
        eligible = [post for post in grouped.get(actual_brand, []) if post.get("eligible")]
        refs = [_post_ref(post) for post in eligible]
        try:
            cache = get_assignment_index(
                project_name=actual_brand,
                map_id=attribute_map["map_id"],
                post_refs=refs,
            )
        except EVOAttributeStoreError as exc:
            raise EVOAttributeBatchError(str(exc)) from exc
        counts = Counter()
        for post in eligible:
            key = (post["canonical_key"], post["content_hash"])
            assignment = cache.get(key)
            if assignment:
                counts[assignment["classification_status"]] += 1
            elif (actual_brand.casefold(), key[0], key[1]) in reserved:
                counts["reserved"] += 1
            else:
                counts["unclassified"] += 1
        completed = sum(counts[status] for status in DONE_STATUSES)
        target = effective_evo_sample_target(
            len(eligible),
            requested_target=target_per_brand,
        )
        row = {
            "brand": actual_brand,
            "eligible_posts": len(eligible),
            "default_or_requested_target": target,
            "completed_sample": completed,
            "classified": counts["classified"],
            "not_relevant": counts["not_relevant"],
            "review_needed_unmapped": counts["review_needed"],
            "reserved_in_active_batch": counts["reserved"],
            "unclassified": counts["unclassified"],
            "remaining_to_target": max(0, target - completed - counts["reserved"]),
            "population_coverage_pct": round(completed * 100 / len(eligible), 2) if eligible else None,
            "target_completion_pct": round(completed * 100 / target, 1) if target else None,
            "confidence": (
                "adequate_directional" if completed >= 30 else
                "directional" if completed >= 10 else
                "low_confidence"
            ),
        }
        per_brand.append(row)
        for key, value in row.items():
            if isinstance(value, int):
                totals[key] += value
    return {
        "success": True,
        "focus_brand": focus_brand,
        "scope": scope,
        "attribute_map": {
            "map_id": attribute_map["map_id"],
            "map_version": attribute_map["map_version"],
            "map_name": attribute_map["map_name"],
            "map_source": attribute_map["map_source"],
            "category": attribute_map["category"],
        },
        "sampling_policy": {
            "default_ratio": DEFAULT_SAMPLE_RATIO,
            "minimum_per_brand": DEFAULT_MIN_PER_BRAND,
            "initial_maximum_per_brand": DEFAULT_INITIAL_MAX_PER_BRAND,
            "maximum_per_llm_batch": MAX_BATCH_SIZE,
            "maximum_incremental_target_per_brand": MAX_TARGET_PER_BRAND,
            "stratification": list(STRATIFICATION_DIMENSIONS),
            "incremental_cache_reuse": True,
        },
        "per_brand": per_brand,
        "totals": dict(totals),
    }


def get_unclassified_evo_attribute_batch(
    *,
    focus_brand: str,
    competitor_brands: str | Iterable[str] | None = None,
    map_id: str | None = None,
    category: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    channels: str | Iterable[str] | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
    target_per_brand: int | None = None,
    batch_size: int = 100,
) -> dict[str, Any]:
    clean_batch_size = max(1, min(int(batch_size or MAX_BATCH_SIZE), MAX_BATCH_SIZE))
    attribute_map = resolve_attribute_map(
        project_name=focus_brand,
        map_id=map_id,
        category=category,
    )
    posts, scope = fetch_evo_scope_posts(
        focus_brand=focus_brand,
        competitor_brands=competitor_brands,
        start_date=start_date,
        end_date=end_date,
        channels=channels,
        keywords=keywords,
        exclude_keywords=exclude_keywords,
        match_mode=match_mode,
    )
    reserved = get_reserved_refs(map_id=attribute_map["map_id"])
    grouped = _brand_posts(posts)

    brand_state: list[dict[str, Any]] = []
    for requested_brand in scope["brand_universe"]:
        brand = next((name for name in grouped if _campaign_key(name) == _campaign_key(requested_brand)), requested_brand)
        eligible = [post for post in grouped.get(brand, []) if post.get("eligible")]
        cache = get_assignment_index(
            project_name=brand,
            map_id=attribute_map["map_id"],
            post_refs=[_post_ref(post) for post in eligible],
        )
        existing_posts: list[dict[str, Any]] = []
        candidates: list[dict[str, Any]] = []
        for post in eligible:
            key = (post["canonical_key"], post["content_hash"])
            if cache.get(key):
                existing_posts.append(post)
            elif (brand.casefold(), key[0], key[1]) not in reserved:
                candidates.append(post)
        target = effective_evo_sample_target(
            len(eligible),
            requested_target=target_per_brand,
        )
        needed = max(0, target - len(existing_posts))
        brand_state.append(
            {
                "brand": brand,
                "population": eligible,
                "existing": existing_posts,
                "candidates": candidates,
                "target": target,
                "needed": needed,
            }
        )

    total_needed = sum(item["needed"] for item in brand_state)
    if total_needed <= 0:
        return {
            "success": True,
            "workflow_status": "EVO_ATTRIBUTE_TARGET_REACHED",
            "attribute_map": attribute_map,
            "scope": scope,
            "message": "Target klasifikasi EVO sudah tercapai untuk semua brand.",
            "per_brand": [
                {
                    "brand": item["brand"],
                    "target": item["target"],
                    "completed": len(item["existing"]),
                    "needed": 0,
                }
                for item in brand_state
            ],
        }

    remaining_slots = min(clean_batch_size, total_needed)
    selected_all: list[dict[str, Any]] = []
    allocation: dict[str, int] = {}
    active = [item for item in brand_state if item["needed"] > 0 and item["candidates"]]
    while remaining_slots > 0 and active:
        progressed = False
        for item in sorted(active, key=lambda row: (-row["needed"], row["brand"].casefold())):
            if remaining_slots <= 0:
                break
            allocated = allocation.get(item["brand"], 0)
            if allocated >= item["needed"] or allocated >= len(item["candidates"]):
                continue
            allocation[item["brand"]] = allocated + 1
            remaining_slots -= 1
            progressed = True
        if not progressed:
            break

    for item in brand_state:
        count = allocation.get(item["brand"], 0)
        if count <= 0:
            continue
        selected = select_stratified_posts(
            population_posts=item["population"],
            candidate_posts=item["candidates"],
            existing_sampled_posts=item["existing"],
            select_count=count,
        )
        selected_all.extend(selected)

    if not selected_all:
        raise EVOAttributeBatchError(
            "Tidak ada post baru yang dapat diambil. Cek active batch reservation atau scope."
        )

    batch_scope = {
        **scope,
        "map_id": attribute_map["map_id"],
        "map_version": attribute_map["map_version"],
        "target_per_brand": target_per_brand,
        "sampling_method": "incremental_stratified_deficit_fill",
        "stratification": list(STRATIFICATION_DIMENSIONS),
        "allocation": allocation,
    }
    batch = create_evo_attribute_batch(
        owner_project_name=focus_brand,
        map_id=attribute_map["map_id"],
        scope=batch_scope,
        post_refs=[_post_ref(post) for post in selected_all],
    )
    return {
        "success": True,
        "workflow_status": "NEEDS_AUTO_EVO_ATTRIBUTE_CLASSIFICATION",
        "batch_id": batch["batch_id"],
        "attribute_map": attribute_map,
        "classification_instruction": classification_instruction(attribute_map),
        "posts": [_llm_post(post) for post in selected_all],
        "sampling": {
            "method": "incremental_stratified_deficit_fill",
            "selected_count": len(selected_all),
            "maximum_per_request": MAX_BATCH_SIZE,
            "allocation_by_brand": allocation,
            "stratification": list(STRATIFICATION_DIMENSIONS),
            "note": (
                "Cached posts count toward the target. Additional batches prioritize "
                "under-represented strata and do not resend completed posts."
            ),
        },
        "assistant_next_steps": [
            "Classify every post using classification_instruction and the returned attribute_map.",
            "Return one JSON object per post; do not omit or add posts.",
            "Call save_evo_attribute_batch_results(batch_id, results_json).",
            "Then rerun status or request the next batch until the chosen target is reached.",
        ],
    }


def get_evo_enriched_scope_posts(
    *,
    focus_brand: str,
    competitor_brands: str | Iterable[str] | None = None,
    map_id: str | None = None,
    category: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    channels: str | Iterable[str] | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
) -> dict[str, Any]:
    attribute_map = resolve_attribute_map(
        project_name=focus_brand,
        map_id=map_id,
        category=category,
    )
    posts, scope = fetch_evo_scope_posts(
        focus_brand=focus_brand,
        competitor_brands=competitor_brands,
        start_date=start_date,
        end_date=end_date,
        channels=channels,
        keywords=keywords,
        exclude_keywords=exclude_keywords,
        match_mode=match_mode,
    )
    grouped = _brand_posts(posts)
    counts = Counter()
    joined: list[dict[str, Any]] = []
    for brand, brand_posts in grouped.items():
        cache = get_assignment_index(
            project_name=brand,
            map_id=attribute_map["map_id"],
            post_refs=[_post_ref(post) for post in brand_posts if post.get("eligible")],
        )
        for post in brand_posts:
            item = deepcopy(post)
            assignment = cache.get((post["canonical_key"], post["content_hash"]))
            item["evo_attribute_assignment"] = deepcopy(assignment) if assignment else None
            if not post.get("eligible"):
                counts["ineligible"] += 1
            elif assignment is None:
                counts["unclassified"] += 1
            else:
                counts[assignment["classification_status"]] += 1
            joined.append(item)
    eligible_total = len([post for post in posts if post.get("eligible")])
    sampled_total = sum(counts[status] for status in DONE_STATUSES)
    return {
        "focus_brand": focus_brand,
        "scope": scope,
        "attribute_map": attribute_map,
        "posts": joined,
        "classification_audit": {
            "basis": "canonical_unique_post",
            "population_total": eligible_total,
            "sampled_total": sampled_total,
            "classified_tagged_total": counts["classified"],
            "not_relevant_total": counts["not_relevant"],
            "unmapped_review_total": counts["review_needed"],
            "unclassified_total": counts["unclassified"],
            "reconciliation": (
                sampled_total
                == counts["classified"] + counts["not_relevant"] + counts["review_needed"]
            ),
            "population_coverage_pct": round(sampled_total * 100 / eligible_total, 2) if eligible_total else None,
            "attribute_basis_total": counts["classified"],
        },
    }


def submit_evo_attribute_batch_results(
    *,
    batch_id: str,
    results: list[Mapping[str, Any]],
) -> dict[str, Any]:
    try:
        batch = get_evo_attribute_batch(batch_id)
    except EVOAttributeStoreError as exc:
        raise EVOAttributeBatchError(str(exc)) from exc
    if batch is None:
        raise EVOAttributeBatchError(f"batch_id '{batch_id}' tidak ditemukan.")
    if batch["status"] != "issued":
        raise EVOAttributeBatchError(
            f"Batch '{batch_id}' berstatus {batch['status']}."
        )
    attribute_map = resolve_attribute_map(
        project_name=batch["owner_project_name"],
        map_id=batch["map_id"],
    )
    try:
        assignments = validate_evo_attribute_batch_results(
            batch=batch,
            attribute_map=attribute_map,
            results=results,
        )
        saved = save_validated_batch_results(
            batch_id=batch_id,
            assignments=assignments,
        )
    except (EVOAttributeResultValidationError, EVOAttributeStoreError) as exc:
        raise EVOAttributeBatchError(str(exc)) from exc
    return {
        **saved,
        "map_id": batch["map_id"],
        "next_step": (
            "Cek get_evo_attribute_enrichment_status, lalu ambil batch berikutnya "
            "bila target sampling belum tercapai."
        ),
    }


__all__ = [
    "DEFAULT_INITIAL_MAX_PER_BRAND",
    "DEFAULT_MIN_PER_BRAND",
    "DEFAULT_SAMPLE_RATIO",
    "EVOAttributeBatchError",
    "MAX_BATCH_SIZE",
    "MAX_TARGET_PER_BRAND",
    "STRATIFICATION_DIMENSIONS",
    "effective_evo_sample_target",
    "fetch_evo_scope_posts",
    "get_evo_attribute_enrichment_status",
    "get_evo_enriched_scope_posts",
    "get_unclassified_evo_attribute_batch",
    "select_stratified_posts",
    "submit_evo_attribute_batch_results",
]
