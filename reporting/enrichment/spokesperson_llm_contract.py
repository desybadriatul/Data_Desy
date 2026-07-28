from __future__ import annotations

import json
from typing import Any, Iterable, Mapping


ALLOWED_STATUSES = {"relevant", "not_relevant", "review_needed"}
ALLOWED_SOURCES = {
    "llm_enriched",
    "llm_checked",
    "sonar_raw_normalized",
    "llm_corrected_sonar",
}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}
ALLOWED_SPOKESPERSON_TYPES = {
    "company_representative",
    "government_official",
    "external_expert",
    "labor_union_representative",
    "community_representative",
    "public_source",
    "other",
    "unclear",
}


SPOKESPERSON_DEFINITION = (
    "A spokesperson is a named person who is quoted or attributed as making a "
    "statement in an Online Media or Print article. A company, institution, "
    "association, media outlet, or anonymous public group is not a spokesperson "
    "unless a named person is present."
)


SYSTEM_INSTRUCTIONS = f"""
You are an information extraction engine for media-intelligence reporting.

Definition:
{SPOKESPERSON_DEFINITION}

Extract spokespersons only when there is a named person who speaks, is quoted,
or is attributed as making a statement in the article context.

Do extract:
- named people who say, explain, state, argue, confirm, deny, suggest, or are quoted
- multiple named speakers when one article contains more than one speaker
- role/title and organization when available

Do not extract:
- companies or institutions without named people
- associations or government bodies without named people
- media outlet names
- journalist narration
- anonymous public / netizens / commenters
- people who are mentioned but do not speak

Important normalization rules:
- Split name, role, and organization into separate fields.
- Do not merge role and name into one string.
- Skip organization-only entities from spokespersons.
- If there is only an organization statement and no named person, use status "review_needed".
- If there is no speaking person, use status "not_relevant".
- Use evidence_sentence to quote/paraphrase the exact sentence that proves attribution.

Return JSON only. No markdown. No commentary.
""".strip()


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _clean_or_none(value: Any) -> str | None:
    text = _clean_text(value)
    return text or None


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _normalize_allowed(value: Any, allowed: set[str], default: str) -> str:
    text = _clean_text(value).casefold().replace(" ", "_").replace("-", "_")
    return text if text in allowed else default


def build_spokesperson_extraction_prompt(
    candidates: Iterable[Mapping[str, Any]],
    campaign_universe: Iterable[str],
) -> str:
    """Build a deterministic JSON-only prompt for spokesperson extraction.

    The caller should pass candidates produced by
    `build_spokesperson_enrichment_candidates`. This function does not call any
    LLM; it only prepares the prompt body.
    """

    campaign_universe = [str(c) for c in campaign_universe if _clean_text(c)]
    payload_items: list[dict[str, Any]] = []

    for candidate in candidates:
        payload_items.append(
            {
                "canonical_post_id": candidate.get("canonical_post_id"),
                "content_hash": candidate.get("content_hash"),
                "campaigns": candidate.get("campaigns"),
                "matched_campaigns": candidate.get("matched_campaigns") or [],
                "media_name": candidate.get("media_name"),
                "title": candidate.get("title"),
                "spokesperson_raw": candidate.get("spokesperson_raw"),
                "llm_context": candidate.get("llm_context"),
                "source_url": candidate.get("source_url"),
            }
        )

    contract = {
        "task": "extract_spokespersons_from_media_articles",
        "campaign_universe": campaign_universe,
        "definition": SPOKESPERSON_DEFINITION,
        "output_schema": {
            "results": [
                {
                    "canonical_post_id": "same as input",
                    "status": "relevant | not_relevant | review_needed",
                    "source": "llm_enriched | llm_checked | sonar_raw_normalized | llm_corrected_sonar",
                    "confidence": "high | medium | low",
                    "reason": "brief reason",
                    "spokespersons": [
                        {
                            "spokesperson_name": "clean named person",
                            "spokesperson_role": "role/title, nullable",
                            "organization": "organization represented, nullable",
                            "spokesperson_type": "company_representative | government_official | external_expert | labor_union_representative | community_representative | public_source | other | unclear",
                            "represented_campaign": "one of campaign_universe if inferable, nullable",
                            "evidence_sentence": "sentence proving the person spoke or was quoted",
                            "confidence": "high | medium | low",
                        }
                    ],
                }
            ]
        },
        "articles": payload_items,
    }

    return SYSTEM_INSTRUCTIONS + "\n\nINPUT_JSON:\n" + json.dumps(
        contract,
        ensure_ascii=False,
        indent=2,
        default=str,
    )


def normalize_spokesperson_item(item: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize one spokesperson object returned by the LLM."""

    return {
        "spokesperson_name": _clean_or_none(item.get("spokesperson_name")),
        "spokesperson_role": _clean_or_none(item.get("spokesperson_role")),
        "organization": _clean_or_none(item.get("organization")),
        "spokesperson_type": _normalize_allowed(
            item.get("spokesperson_type"),
            ALLOWED_SPOKESPERSON_TYPES,
            "unclear",
        ),
        "represented_campaign": _clean_or_none(item.get("represented_campaign")),
        "evidence_sentence": _clean_or_none(item.get("evidence_sentence")),
        "confidence": _normalize_allowed(item.get("confidence"), ALLOWED_CONFIDENCE, "low"),
    }


def normalize_article_result(result: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize one article-level LLM extraction result.

    This is intentionally conservative:
    - relevant requires at least one spokesperson with a name
    - no named spokesperson downgrades to not_relevant/review_needed
    """

    status = _normalize_allowed(result.get("status"), ALLOWED_STATUSES, "review_needed")
    source = _normalize_allowed(result.get("source"), ALLOWED_SOURCES, "llm_checked")
    confidence = _normalize_allowed(result.get("confidence"), ALLOWED_CONFIDENCE, "low")

    spokespersons = [
        sp
        for sp in (
            normalize_spokesperson_item(item)
            for item in _as_list(result.get("spokespersons"))
            if isinstance(item, Mapping)
        )
        if sp.get("spokesperson_name")
    ]

    if spokespersons:
        status = "relevant"
        if source == "llm_checked":
            source = "llm_enriched"
    elif status == "relevant":
        status = "review_needed"

    return {
        "canonical_post_id": result.get("canonical_post_id"),
        "content_hash": result.get("content_hash"),
        "status": status,
        "source": source,
        "confidence": confidence,
        "reason": _clean_or_none(result.get("reason")),
        "spokespersons": spokespersons,
    }


def normalize_spokesperson_batch_response(response: Any) -> dict[str, Any]:
    """Normalize a batch response from the LLM.

    Accepts either:
    - dict with key `results`
    - raw list of article result objects
    """

    if isinstance(response, str):
        response = json.loads(response)

    if isinstance(response, Mapping):
        raw_results = response.get("results")
    else:
        raw_results = response

    results = [
        normalize_article_result(item)
        for item in _as_list(raw_results)
        if isinstance(item, Mapping)
    ]

    return {
        "results": results,
        "summary": summarize_spokesperson_results(results),
    }


def summarize_spokesperson_results(results: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    results = list(results)
    relevant = [r for r in results if r.get("status") == "relevant"]
    not_relevant = [r for r in results if r.get("status") == "not_relevant"]
    review_needed = [r for r in results if r.get("status") == "review_needed"]
    spokesperson_count = sum(len(_as_list(r.get("spokespersons"))) for r in relevant)

    unique_names = {
        _clean_text(sp.get("spokesperson_name")).casefold()
        for r in relevant
        for sp in _as_list(r.get("spokespersons"))
        if isinstance(sp, Mapping) and _clean_text(sp.get("spokesperson_name"))
    }

    return {
        "article_count": len(results),
        "relevant_articles": len(relevant),
        "not_relevant_articles": len(not_relevant),
        "review_needed_articles": len(review_needed),
        "spokesperson_mentions": spokesperson_count,
        "unique_spokesperson_names": len(unique_names),
    }


def validate_spokesperson_batch_response(response: Any) -> tuple[bool, list[str], dict[str, Any]]:
    """Validate and normalize a spokesperson extraction response.

    Returns:
        (is_valid, errors, normalized_response)
    """

    errors: list[str] = []

    try:
        normalized = normalize_spokesperson_batch_response(response)
    except Exception as exc:  # noqa: BLE001 - validation should never crash caller
        return False, [f"Invalid JSON/response shape: {exc}"], {"results": [], "summary": {}}

    for idx, result in enumerate(normalized.get("results", [])):
        if result.get("canonical_post_id") in (None, ""):
            errors.append(f"results[{idx}].canonical_post_id is required")

        if result.get("status") not in ALLOWED_STATUSES:
            errors.append(f"results[{idx}].status is invalid")

        if result.get("source") not in ALLOWED_SOURCES:
            errors.append(f"results[{idx}].source is invalid")

        if result.get("confidence") not in ALLOWED_CONFIDENCE:
            errors.append(f"results[{idx}].confidence is invalid")

        for sp_idx, sp in enumerate(_as_list(result.get("spokespersons"))):
            if not isinstance(sp, Mapping):
                errors.append(f"results[{idx}].spokespersons[{sp_idx}] is not an object")
                continue
            if not _clean_text(sp.get("spokesperson_name")):
                errors.append(
                    f"results[{idx}].spokespersons[{sp_idx}].spokesperson_name is required"
                )
            if sp.get("spokesperson_type") not in ALLOWED_SPOKESPERSON_TYPES:
                errors.append(
                    f"results[{idx}].spokespersons[{sp_idx}].spokesperson_type is invalid"
                )
            if sp.get("confidence") not in ALLOWED_CONFIDENCE:
                errors.append(
                    f"results[{idx}].spokespersons[{sp_idx}].confidence is invalid"
                )

    return not errors, errors, normalized
