"""Prepare taxonomy samples and non-overlapping Claude classification batches."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from database import db
from reporting.enrichment.topic_contract import (
    canonical_content_hash,
    canonical_key_from_values,
    classification_instruction,
    normalize_text,
    taxonomy_instruction,
    topic_text_for_llm,
)
from reporting.enrichment.topic_result_validator import (
    TopicResultValidationError,
    validate_topic_batch_results,
)
from reporting.enrichment.topic_store import (
    TopicStoreError,
    create_topic_batch,
    get_active_taxonomy,
    get_assignment_index,
    get_reserved_refs,
    get_taxonomy,
    get_topic_batch,
    save_validated_batch_results,
)


DEFAULT_BATCH_SIZE = 50
MAX_BATCH_SIZE = 100
DEFAULT_SAMPLE_SIZE = 80
DONE_STATUSES = frozenset({"classified", "not_relevant"})


class TopicBatchError(RuntimeError):
    """Topic batch/sample workflow cannot continue."""


def _safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        value = float(value)
        return int(value) if value.is_integer() else round(value, 4)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _number(value: Any) -> int | float:
    value = _safe(value)
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def _terms(values: str | Iterable[str] | None) -> list[str]:
    if values is None:
        return []
    raw = values.split(",") if isinstance(values, str) else list(values)
    result, seen = [], set()
    for value in raw:
        clean = normalize_text(value)
        if clean and clean.casefold() not in seen:
            result.append(clean)
            seen.add(clean.casefold())
    return result


def _channel_norm(channel: Any) -> str:
    value = normalize_text(channel).casefold()
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
    }
    return aliases.get(value, value or "unknown")


def _source_value(record: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        value = record.get(name)
        if value is not None and str(value).strip() != "":
            return value
    return None


def _scope(
    *,
    project_name: str,
    start_date: str | None,
    end_date: str | None,
    channels: str | Iterable[str] | None,
    keywords: str | Iterable[str] | None,
    exclude_keywords: str | Iterable[str] | None,
    match_mode: str,
) -> dict[str, Any]:
    channels_clean = _terms(channels)
    keywords_clean = _terms(keywords)
    excludes_clean = _terms(exclude_keywords)
    return {
        "project_name": normalize_text(project_name),
        "start_date": normalize_text(start_date) or None,
        "end_date": normalize_text(end_date) or None,
        "channels": channels_clean,
        "keywords": keywords_clean,
        "exclude_keywords": excludes_clean,
        "match_mode": "all" if normalize_text(match_mode).casefold() == "all" else "any",
        "universe": "issue_only" if keywords_clean or excludes_clean else "brand",
        "raw_topic_extraction_policy": "ignored_for_report_topic",
    }


def _normalise_post(record: Mapping[str, Any]) -> dict[str, Any]:
    canonical_id = _source_value(record, "_cogan_canonical_post_id")
    url = _source_value(record, "_cogan_url", "Link URL", "URL")
    title = normalize_text(_source_value(record, "Title"))
    content = normalize_text(_source_value(record, "Content"))
    return {
        "canonical_post_id": int(canonical_id) if canonical_id is not None else None,
        "canonical_key": canonical_key_from_values(
            url=url,
            canonical_post_id=canonical_id,
        ),
        "content_hash": canonical_content_hash(title, content),
        "post_date": _safe(_source_value(record, "_cogan_post_date", "Date")),
        "channel": normalize_text(
            _source_value(record, "Channel", "_cogan_channel")
        )
        or "(tidak diketahui)",
        "channel_norm": _channel_norm(
            _source_value(record, "Channel", "_cogan_channel")
        ),
        "author": normalize_text(_source_value(record, "Author")) or None,
        "verified_account": _source_value(record, "Verified Account"),
        "sentiment": (
            normalize_text(_source_value(record, "Sentiment")).casefold()
            if normalize_text(_source_value(record, "Sentiment")).casefold()
            in {"positive", "neutral", "negative"}
            else "unclassified"
        ),
        "title": title,
        "content": content,
        "url": normalize_text(url) or None,
        "interactions": _number(_source_value(record, "_cogan_interactions")),
        "views": _number(_source_value(record, "_cogan_views")),
        "potential_reach": _number(
            _source_value(
                record,
                "Potential Reach",
                "potential_reach",
                "potential reach",
                "potentialReach",
            )
        ),
        "original_reach": _number(
            _source_value(
                record,
                "Original Reach",
                "original_reach",
                "original reach",
                "originalReach",
            )
        ),
        "viral_reach": _number(
            _source_value(
                record,
                "Viral Reach",
                "viral_reach",
                "viral reach",
                "viralReach",
            )
        ),
        "interactions_available": bool(
            _source_value(record, "_cogan_interactions_available")
        ),
        "views_available": bool(_source_value(record, "_cogan_views_available")),
        "sentence_type_classification": normalize_text(
            _source_value(record, "Sentence Type Classification")
        )
        or None,
        # Retained for diagnostics only. Never used to classify or aggregate topic.
        "raw_topic_extraction": normalize_text(
            _source_value(record, "Topic Extraction")
        )
        or None,
        "media_name": _safe(
            _source_value(record, "Media Name", "media_name")
        ),
        "spokesperson_raw": _safe(
            _source_value(record, "Spokesperson", "spokesperson")
        ),
        "ad_value": _number(
            _source_value(record, "Ad Value", "ad_value")
        ),
        "pr_value": _number(
            _source_value(record, "PR Value", "pr_value")
        ),
        "readership": _number(
            _source_value(record, "Readership", "readership")
        ),
        "media_type": _safe(
            _source_value(record, "Media Type", "media_type")
        ),
        "topic_eligible": bool(title or content),
        "campaigns": _safe(
            _source_value(record, "Campaigns", "Campaign", "campaigns", "campaign")
        ),
        "tags": _safe(
            _source_value(record, "Tags", "Tag", "tags", "tag")
        ),
        "dashboard_name": _safe(
            _source_value(record, "Dashboard Name", "dashboard_name")
        ),
        "widget_name": _safe(
            _source_value(record, "Widget Name", "widget_name")
        ),
    }


def fetch_scope_posts(
    *,
    project_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    channels: str | Iterable[str] | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Read canonical records through db.py; never use raw Topic Extraction."""
    scope = _scope(
        project_name=project_name,
        start_date=start_date,
        end_date=end_date,
        channels=channels,
        keywords=keywords,
        exclude_keywords=exclude_keywords,
        match_mode=match_mode,
    )
    try:
        records = db.fetch_raw_records(
            project_name,
            scope["start_date"],
            scope["end_date"],
            None,
            scope["keywords"] or None,
            scope["exclude_keywords"] or None,
            scope["match_mode"],
            scope["channels"] or None,
        )
    except Exception as exc:
        raise TopicBatchError(f"Gagal menarik canonical post: {exc}") from exc

    if records is None:
        raise TopicBatchError(f"Project '{project_name}' tidak ditemukan.")
    return [_normalise_post(record) for record in records], scope


def _rank(posts: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        (dict(post) for post in posts),
        key=lambda post: (
            float(post.get("interactions") or 0),
            float(post.get("views") or 0),
            str(post.get("post_date") or ""),
            str(post.get("canonical_key") or ""),
        ),
        reverse=True,
    )


def _post_ref(post: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "canonical_post_id": post.get("canonical_post_id"),
        "canonical_key": post["canonical_key"],
        "content_hash": post["content_hash"],
    }


def _llm_post(post: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "canonical_post_id": post.get("canonical_post_id"),
        "canonical_key": post["canonical_key"],
        "content_hash": post["content_hash"],
        "date": post.get("post_date"),
        "channel": post.get("channel"),
        "text": topic_text_for_llm(post.get("title"), post.get("content")),
    }


def get_topic_taxonomy_sample(
    *,
    project_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    channels: str | Iterable[str] | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
    sample_size: int = DEFAULT_SAMPLE_SIZE,
) -> dict[str, Any]:
    """Create deterministic high-signal sample for first taxonomy creation."""
    sample_size = max(10, min(int(sample_size), 200))
    posts, scope = fetch_scope_posts(
        project_name=project_name,
        start_date=start_date,
        end_date=end_date,
        channels=channels,
        keywords=keywords,
        exclude_keywords=exclude_keywords,
        match_mode=match_mode,
    )
    ranked = _rank(post for post in posts if post["topic_eligible"])

    selected, seen = [], set()

    def add(post: Mapping[str, Any], reason: str) -> None:
        if len(selected) >= sample_size:
            return
        key = (post["canonical_key"], post["content_hash"])
        if key in seen:
            return
        item = _llm_post(post)
        item["sample_reason"] = reason
        selected.append(item)
        seen.add(key)

    for post in ranked[: max(5, sample_size // 2)]:
        add(post, "top_interactions_or_views")

    by_sentiment, by_channel = defaultdict(list), defaultdict(list)
    for post in ranked:
        by_sentiment[post["sentiment"]].append(post)
        by_channel[post["channel"]].append(post)

    for sentiment in ("positive", "negative", "neutral", "unclassified"):
        for post in by_sentiment[sentiment][:5]:
            add(post, f"sentiment_coverage:{sentiment}")

    for channel in sorted(by_channel):
        for post in by_channel[channel][:3]:
            add(post, f"channel_coverage:{channel}")

    for post in ranked:
        add(post, "ranked_fill")

    return {
        "project_name": project_name,
        "scope": scope,
        "canonical_posts_in_scope": len(posts),
        "topic_eligible_posts": len(ranked),
        "taxonomy_instruction": taxonomy_instruction(),
        "required_taxonomy_shape": {
            "taxonomy_version": "project_social_topic_v1",
            "taxonomy_name": "Nama taxonomy project",
            "description": "Batas penggunaan taxonomy",
            "topics": [
                {
                    "topic_id": "example_topic",
                    "label": "Nama Topic",
                    "description": "Kapan post masuk ke topic ini",
                },
                {
                    "topic_id": "other_emerging_topic",
                    "label": "Topik Baru / Perlu Review",
                    "description": "Relevan tetapi tidak cocok taxonomy.",
                },
                {
                    "topic_id": "not_relevant",
                    "label": "Tidak Relevan",
                    "description": "Tidak relevan terhadap report scope.",
                },
            ],
        },
        "sample_posts": selected,
        "note": (
            "Taxonomy harus dibuat dari Title + Content. Raw Sonar Topic "
            "Extraction sengaja tidak dipakai."
        ),
    }


def _resolve_taxonomy(
    project_name: str,
    taxonomy_version: str | None,
) -> dict[str, Any]:
    try:
        taxonomy = (
            get_taxonomy(
                project_name=project_name,
                taxonomy_version=taxonomy_version,
            )
            if taxonomy_version
            else get_active_taxonomy(project_name)
        )
    except TopicStoreError as exc:
        raise TopicBatchError(str(exc)) from exc
    if taxonomy is None:
        raise TopicBatchError(
            "Taxonomy belum tersedia. Gunakan get_topic_taxonomy_sample lalu "
            "save_topic_taxonomy terlebih dahulu."
        )
    return taxonomy


def get_unclassified_topic_batch(
    *,
    project_name: str,
    taxonomy_version: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    channels: str | Iterable[str] | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    """Issue only posts not already classified and not reserved by another user."""
    batch_size = max(1, min(int(batch_size), MAX_BATCH_SIZE))
    taxonomy = _resolve_taxonomy(project_name, taxonomy_version)
    posts, scope = fetch_scope_posts(
        project_name=project_name,
        start_date=start_date,
        end_date=end_date,
        channels=channels,
        keywords=keywords,
        exclude_keywords=exclude_keywords,
        match_mode=match_mode,
    )
    eligible = [post for post in posts if post["topic_eligible"]]
    refs = [_post_ref(post) for post in eligible]

    try:
        cache = get_assignment_index(
            project_name=project_name,
            taxonomy_version=taxonomy["taxonomy_version"],
            post_refs=refs,
        )
        reserved = get_reserved_refs(
            project_name=project_name,
            taxonomy_version=taxonomy["taxonomy_version"],
        )
    except TopicStoreError as exc:
        raise TopicBatchError(str(exc)) from exc

    candidates, done, review = [], 0, 0
    for post in eligible:
        key = (post["canonical_key"], post["content_hash"])
        assignment = cache.get(key)
        if assignment and assignment["classification_status"] in DONE_STATUSES:
            done += 1
            continue
        if assignment and assignment["classification_status"] == "review_needed":
            review += 1
        if key in reserved:
            continue
        candidates.append(post)

    selected = _rank(candidates)[:batch_size]
    if not selected:
        return {
            "status": "COMPLETE",
            "project_name": project_name,
            "taxonomy_version": taxonomy["taxonomy_version"],
            "scope": scope,
            "canonical_posts_in_scope": len(posts),
            "topic_eligible_posts": len(eligible),
            "classified_or_not_relevant": done,
            "review_needed": review,
            "unclassified_available": 0,
            "batch_id": None,
            "posts": [],
        }

    try:
        batch = create_topic_batch(
            project_name=project_name,
            taxonomy_version=taxonomy["taxonomy_version"],
            scope=scope,
            post_refs=[_post_ref(post) for post in selected],
        )
    except TopicStoreError as exc:
        raise TopicBatchError(str(exc)) from exc

    return {
        "status": "READY",
        "batch_id": batch["batch_id"],
        "project_name": project_name,
        "taxonomy": {
            "taxonomy_version": taxonomy["taxonomy_version"],
            "taxonomy_name": taxonomy["taxonomy_name"],
            "topics": deepcopy(taxonomy["topics"]),
        },
        "scope": scope,
        "canonical_posts_in_scope": len(posts),
        "topic_eligible_posts": len(eligible),
        "classified_or_not_relevant": done,
        "review_needed": review,
        "unclassified_available_before_issue": len(candidates),
        "batch_size": len(selected),
        "classification_instruction": classification_instruction(taxonomy),
        "required_result_shape": {
            "canonical_key": "copy exact input",
            "content_hash": "copy exact input",
            "primary_topic_id": "one allowed topic_id",
            "classification_status": "classified | not_relevant | review_needed",
            "confidence": "high | medium | low",
            "classification_reason": "optional concise reason",
            "emerging_topic_detail": "required only for review_needed",
        },
        "posts": [_llm_post(post) for post in selected],
        "note": (
            "Post yang sudah cached atau sedang ada di batch user lain tidak "
            "dikirim ulang ke Claude."
        ),
    }


def get_topic_enrichment_status(
    *,
    project_name: str,
    taxonomy_version: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    channels: str | Iterable[str] | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
) -> dict[str, Any]:
    """Count classified, pending, review, and reserved posts for a scope."""
    posts, scope = fetch_scope_posts(
        project_name=project_name,
        start_date=start_date,
        end_date=end_date,
        channels=channels,
        keywords=keywords,
        exclude_keywords=exclude_keywords,
        match_mode=match_mode,
    )
    eligible = [post for post in posts if post["topic_eligible"]]
    try:
        taxonomy = (
            get_taxonomy(
                project_name=project_name,
                taxonomy_version=taxonomy_version,
            )
            if taxonomy_version
            else get_active_taxonomy(project_name)
        )
    except TopicStoreError as exc:
        raise TopicBatchError(str(exc)) from exc

    if taxonomy is None:
        return {
            "status": "NEEDS_TAXONOMY",
            "project_name": project_name,
            "scope": scope,
            "canonical_posts_in_scope": len(posts),
            "topic_eligible_posts": len(eligible),
            "next_step": "Buat dan simpan taxonomy project terlebih dahulu.",
        }

    refs = [_post_ref(post) for post in eligible]
    cache = get_assignment_index(
        project_name=project_name,
        taxonomy_version=taxonomy["taxonomy_version"],
        post_refs=refs,
    )
    reserved = get_reserved_refs(
        project_name=project_name,
        taxonomy_version=taxonomy["taxonomy_version"],
    )

    counts = defaultdict(int)
    for post in eligible:
        key = (post["canonical_key"], post["content_hash"])
        assignment = cache.get(key)
        if assignment:
            counts[assignment["classification_status"]] += 1
        elif key in reserved:
            counts["reserved"] += 1
        else:
            counts["unclassified"] += 1

    completed = counts["classified"] + counts["not_relevant"]
    total = len(eligible)
    return {
        "status": "COMPLETE" if completed == total else "IN_PROGRESS",
        "project_name": project_name,
        "taxonomy": {
            "taxonomy_version": taxonomy["taxonomy_version"],
            "taxonomy_name": taxonomy["taxonomy_name"],
        },
        "scope": scope,
        "canonical_posts_in_scope": len(posts),
        "topic_eligible_posts": total,
        "topic_ineligible_posts": len(posts) - total,
        "classified": counts["classified"],
        "not_relevant": counts["not_relevant"],
        "review_needed": counts["review_needed"],
        "reserved_in_active_batch": counts["reserved"],
        "unclassified": counts["unclassified"],
        "completion_coverage_pct": round(completed * 100 / total, 1) if total else None,
        "report_topic_coverage_pct": round(counts["classified"] * 100 / total, 1) if total else None,
    }


def get_enriched_scope_posts(
    *,
    project_name: str,
    taxonomy_version: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    channels: str | Iterable[str] | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
) -> dict[str, Any]:
    """Read cache only; no LLM call and no Claude quota is spent here."""
    posts, scope = fetch_scope_posts(
        project_name=project_name,
        start_date=start_date,
        end_date=end_date,
        channels=channels,
        keywords=keywords,
        exclude_keywords=exclude_keywords,
        match_mode=match_mode,
    )
    try:
        taxonomy = (
            get_taxonomy(
                project_name=project_name,
                taxonomy_version=taxonomy_version,
            )
            if taxonomy_version
            else get_active_taxonomy(project_name)
        )
    except TopicStoreError as exc:
        raise TopicBatchError(str(exc)) from exc

    if taxonomy is None:
        return {
            "project_name": project_name,
            "scope": scope,
            "taxonomy": None,
            "posts": posts,
            "topic_status": {
                "topic_eligible_posts": sum(post["topic_eligible"] for post in posts),
                "classified": 0,
                "not_relevant": 0,
                "review_needed": 0,
                "unclassified": sum(post["topic_eligible"] for post in posts),
                "completion_coverage_pct": 0.0,
                "report_topic_coverage_pct": 0.0,
            },
        }

    eligible = [post for post in posts if post["topic_eligible"]]
    cache = get_assignment_index(
        project_name=project_name,
        taxonomy_version=taxonomy["taxonomy_version"],
        post_refs=[_post_ref(post) for post in eligible],
    )

    counts = defaultdict(int)
    joined = []
    for post in posts:
        item = deepcopy(post)
        assignment = cache.get((post["canonical_key"], post["content_hash"]))
        item["topic_assignment"] = deepcopy(assignment) if assignment else None
        if not post["topic_eligible"]:
            counts["ineligible"] += 1
        elif assignment is None:
            counts["unclassified"] += 1
        else:
            counts[assignment["classification_status"]] += 1
        joined.append(item)

    total = len(eligible)
    completed = counts["classified"] + counts["not_relevant"]
    return {
        "project_name": project_name,
        "scope": scope,
        "taxonomy": {
            "taxonomy_version": taxonomy["taxonomy_version"],
            "taxonomy_name": taxonomy["taxonomy_name"],
            "topics": deepcopy(taxonomy["topics"]),
        },
        "posts": joined,
        "topic_status": {
            "topic_eligible_posts": total,
            "topic_ineligible_posts": counts["ineligible"],
            "classified": counts["classified"],
            "not_relevant": counts["not_relevant"],
            "review_needed": counts["review_needed"],
            "unclassified": counts["unclassified"],
            "completion_coverage_pct": round(completed * 100 / total, 1) if total else None,
            "report_topic_coverage_pct": round(counts["classified"] * 100 / total, 1) if total else None,
        },
    }


def submit_topic_batch_results(
    *,
    batch_id: str,
    results: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate complete Claude output, persist it, then close the batch."""
    try:
        batch = get_topic_batch(batch_id)
    except TopicStoreError as exc:
        raise TopicBatchError(str(exc)) from exc
    if batch is None:
        raise TopicBatchError(f"batch_id '{batch_id}' tidak ditemukan.")
    if batch["status"] != "issued":
        raise TopicBatchError(
            f"Batch '{batch_id}' berstatus {batch['status']}."
        )

    taxonomy = _resolve_taxonomy(batch["project_name"], batch["taxonomy_version"])
    try:
        assignments = validate_topic_batch_results(
            batch=batch,
            taxonomy=taxonomy,
            results=results,
        )
        saved = save_validated_batch_results(
            batch_id=batch_id,
            assignments=assignments,
        )
    except (TopicResultValidationError, TopicStoreError) as exc:
        raise TopicBatchError(str(exc)) from exc

    return {
        **saved,
        "project_name": batch["project_name"],
        "taxonomy_version": batch["taxonomy_version"],
        "next_step": "Cek status, lalu ambil batch berikutnya bila masih ada post pending.",
    }


__all__ = [
    "TopicBatchError",
    "fetch_scope_posts",
    "get_enriched_scope_posts",
    "get_topic_enrichment_status",
    "get_topic_taxonomy_sample",
    "get_unclassified_topic_batch",
    "submit_topic_batch_results",
]
