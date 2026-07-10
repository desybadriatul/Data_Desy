from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Any, Iterable, Mapping


SPOKESPERSON_ATTRIBUTION_SIGNALS = [
    "mengatakan",
    "menyampaikan",
    "menjelaskan",
    "menyatakan",
    "menuturkan",
    "menegaskan",
    "menyebut",
    "menyebutkan",
    "mengungkapkan",
    "menerangkan",
    "memaparkan",
    "berpendapat",
    "menilai",
    "mengonfirmasi",
    "mengkonfirmasi",
    "membantah",
    "menyanggah",
    "mengakui",
    "menambahkan",
    "mengimbau",
    "mendesak",
    "mengusulkan",
    "menyarankan",
    "kata",
    "ujar",
    "ucap",
    "tutur",
    "ungkap",
    "papar",
    "jelas",
    "tegas",
    "tandas",
    "pungkas",
    "imbuh",
    "lanjut",
    "tambah",
    "terang",
    "sebut",
    "sanggah",
    "bantah",
    "menurut",
    "dalam keterangannya",
    "dalam keterangan resminya",
    "dalam sambutannya",
]


ONLINE_MEDIA_CHANNELS = {
    "online media",
    "online",
    "print",
    "print media",
    "printmedia",
}


def _norm(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _lower(value: Any) -> str:
    return _norm(value).casefold()


def split_campaigns(value: Any) -> list[str]:
    text = _norm(value)
    if not text:
        return []

    parts = re.split(r"[,;|/\n]+", text)
    return [p.strip() for p in parts if p.strip()]


def campaign_matches(record_campaigns: Any, campaign_universe: Iterable[str]) -> list[str]:
    campaigns = split_campaigns(record_campaigns)
    if not campaigns:
        return []

    wanted = [_lower(c) for c in campaign_universe if _norm(c)]
    matched = []

    for campaign in campaigns:
        campaign_l = _lower(campaign)
        for want_l, want_raw in zip(wanted, campaign_universe):
            if campaign_l == want_l:
                matched.append(str(want_raw))
                break

    return matched


def is_online_media_record(record: Mapping[str, Any]) -> bool:
    channel = _lower(record.get("channel") or record.get("Channel"))
    media_type = _lower(record.get("media_type") or record.get("Media Type"))

    return channel in ONLINE_MEDIA_CHANNELS or media_type in ONLINE_MEDIA_CHANNELS


def quote_signal_score(record: Mapping[str, Any]) -> int:
    text = " ".join(
        [
            _lower(record.get("title") or record.get("Title")),
            _lower(record.get("content") or record.get("Content")),
            _lower(record.get("spokesperson_raw") or record.get("Spokesperson")),
        ]
    )

    if not text.strip():
        return 0

    score = 0
    for signal in SPOKESPERSON_ATTRIBUTION_SIGNALS:
        if signal in text:
            score += 1

    if _norm(record.get("spokesperson_raw") or record.get("Spokesperson")):
        score += 3

    return score


def trim_spokesperson_context(
    title: Any,
    content: Any,
    raw_spokesperson: Any = None,
    max_chars: int = 1800,
) -> str:
    title_text = _norm(title)
    content_text = _norm(content)
    raw_spk = _norm(raw_spokesperson)

    if not content_text:
        return title_text[:max_chars]

    sentences = re.split(r"(?<=[.!?。])\s+", content_text)
    selected: list[str] = []

    if title_text:
        selected.append(f"TITLE: {title_text}")

    # Always include lead.
    selected.extend(sentences[:2])

    lower_sentences = [s.casefold() for s in sentences]
    signals = [s.casefold() for s in SPOKESPERSON_ATTRIBUTION_SIGNALS]

    for i, sent_l in enumerate(lower_sentences):
        has_signal = any(sig in sent_l for sig in signals)
        has_raw_spk = raw_spk and raw_spk.casefold() in sent_l

        if has_signal or has_raw_spk:
            start = max(0, i - 1)
            end = min(len(sentences), i + 2)
            selected.extend(sentences[start:end])

    # Deduplicate while preserving order.
    deduped = []
    seen = set()
    for s in selected:
        clean = _norm(s)
        if clean and clean not in seen:
            deduped.append(clean)
            seen.add(clean)

    result = "\n".join(deduped)
    return result[:max_chars]


def compute_spokesperson_sample_size(
    eligible_count: int,
    sample_pct: float = 0.10,
    min_articles: int = 50,
    max_articles: int = 100,
) -> int:
    if eligible_count <= 0:
        return 0
    if eligible_count <= min_articles:
        return eligible_count

    target = math.ceil(eligible_count * sample_pct)
    return min(max(target, min_articles), max_articles)


def build_spokesperson_enrichment_candidates(
    records: Iterable[Mapping[str, Any]],
    campaign_universe: Iterable[str],
    sample_pct: float = 0.10,
    min_articles: int = 50,
    max_articles: int = 100,
) -> dict[str, Any]:
    campaign_universe = [str(c) for c in campaign_universe if _norm(c)]
    unique_by_key: dict[str, dict[str, Any]] = {}

    for record in records:
        if not is_online_media_record(record):
            continue

        matched_campaigns = campaign_matches(record.get("campaigns") or record.get("Campaigns"), campaign_universe)
        if not matched_campaigns:
            continue

        title = record.get("title") or record.get("Title")
        content = record.get("content") or record.get("Content")
        if not _norm(title) and not _norm(content):
            continue

        canonical_id = record.get("canonical_post_id") or record.get("_cogan_canonical_post_id") or record.get("id")
        content_hash = record.get("content_hash")
        key = str(canonical_id or content_hash or record.get("url") or record.get("Link URL"))

        if not key or key == "None":
            continue

        row = dict(record)
        row["_matched_campaigns"] = matched_campaigns
        row["_quote_signal_score"] = quote_signal_score(record)
        row["_spokesperson_context"] = trim_spokesperson_context(
            title=title,
            content=content,
            raw_spokesperson=record.get("spokesperson_raw") or record.get("Spokesperson"),
        )

        unique_by_key[key] = row

    eligible = list(unique_by_key.values())
    sample_size = compute_spokesperson_sample_size(
        eligible_count=len(eligible),
        sample_pct=sample_pct,
        min_articles=min_articles,
        max_articles=max_articles,
    )

    by_campaign: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        for campaign in row["_matched_campaigns"]:
            by_campaign[campaign].append(row)

    def sort_key(row: Mapping[str, Any]) -> tuple:
        return (
            float(row.get("ad_value") or row.get("Ad Value") or 0),
            float(row.get("pr_value") or row.get("PR Value") or 0),
            float(row.get("readership") or row.get("Readership") or 0),
            int(row.get("_quote_signal_score") or 0),
            str(row.get("post_date") or row.get("_cogan_post_date") or ""),
        )

    for campaign in by_campaign:
        by_campaign[campaign].sort(key=sort_key, reverse=True)

    selected: dict[str, dict[str, Any]] = {}
    if sample_size > 0 and campaign_universe:
        per_campaign_quota = max(1, math.ceil(sample_size / len(campaign_universe)))

        for campaign in campaign_universe:
            for row in by_campaign.get(campaign, [])[:per_campaign_quota]:
                key = str(row.get("canonical_post_id") or row.get("_cogan_canonical_post_id") or row.get("content_hash") or row.get("url"))
                selected[key] = row
                if len(selected) >= sample_size:
                    break

        if len(selected) < sample_size:
            remaining = [r for r in eligible if str(r.get("canonical_post_id") or r.get("_cogan_canonical_post_id") or r.get("content_hash") or r.get("url")) not in selected]
            remaining.sort(key=sort_key, reverse=True)
            for row in remaining:
                key = str(row.get("canonical_post_id") or row.get("_cogan_canonical_post_id") or row.get("content_hash") or row.get("url"))
                selected[key] = row
                if len(selected) >= sample_size:
                    break

    candidates = []
    for row in selected.values():
        candidates.append(
            {
                "canonical_post_id": row.get("canonical_post_id") or row.get("_cogan_canonical_post_id") or row.get("id"),
                "content_hash": row.get("content_hash"),
                "campaigns": row.get("campaigns") or row.get("Campaigns"),
                "matched_campaigns": row.get("_matched_campaigns", []),
                "channel": row.get("channel") or row.get("Channel"),
                "media_name": row.get("media_name") or row.get("Media Name"),
                "title": row.get("title") or row.get("Title"),
                "spokesperson_raw": row.get("spokesperson_raw") or row.get("Spokesperson"),
                "ad_value": row.get("ad_value") or row.get("Ad Value") or 0,
                "pr_value": row.get("pr_value") or row.get("PR Value") or 0,
                "readership": row.get("readership") or row.get("Readership") or 0,
                "quote_signal_score": row.get("_quote_signal_score", 0),
                "llm_context": row.get("_spokesperson_context", ""),
                "source_url": row.get("url") or row.get("Link URL"),
            }
        )

    return {
        "eligible_count": len(eligible),
        "sample_size": sample_size,
        "selected_count": len(candidates),
        "campaign_universe": campaign_universe,
        "candidates": candidates,
        "selection_policy": {
            "channel": "Online Media / Print only",
            "sample_pct": sample_pct,
            "min_articles": min_articles,
            "max_articles": max_articles,
            "priority": [
                "ad_value DESC",
                "pr_value DESC",
                "readership DESC",
                "quote_signal_score DESC",
                "post_date DESC",
            ],
        },
    }


SPOKESPERSON_EXTRACTION_CONTRACT = {
    "definition": "Spokesperson is a named person who is quoted or attributed as making a statement in an article.",
    "must_extract": [
        "Named people who speak, explain, state, say, argue, confirm, deny, or are quoted.",
    ],
    "must_not_extract": [
        "Companies or institutions without named people.",
        "Associations or government bodies without named people.",
        "Journalist narration.",
        "Anonymous public or netizens.",
        "People mentioned but not speaking.",
    ],
    "output_shape": {
        "canonical_post_id": "number/string",
        "status": "relevant | not_relevant | review_needed",
        "source": "llm_enriched | llm_checked | sonar_raw_normalized | llm_corrected_sonar",
        "confidence": "high | medium | low",
        "spokespersons": [
            {
                "spokesperson_name": "clean person name",
                "spokesperson_role": "role/title",
                "organization": "organization represented",
                "spokesperson_type": "company_representative | government_official | external_expert | public_source | other",
                "represented_campaign": "campaign/brand if inferable",
                "evidence_sentence": "short sentence proving attribution",
                "confidence": "high | medium | low",
            }
        ],
    },
}