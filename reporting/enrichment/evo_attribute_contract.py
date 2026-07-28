"""Contracts and seed map for EVO per-post attribute classification."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json
import re
from typing import Any


EVO_DRIVERS = ("Experience", "Values", "Offer")
EVO_CLASSIFICATION_STATUSES = frozenset(
    {"classified", "not_relevant", "review_needed"}
)
EVO_PROMPT_VERSION = "evo-attribute-classify-v1"
EVO_SEED_MAP_ID = "evo_seed_v1"


class EVOAttributeContractError(ValueError):
    """Raised when an EVO map or classification contract is malformed."""


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def canonical_content_hash(title: Any, content: Any) -> str:
    text = "\n".join((normalize_text(title), normalize_text(content))).casefold()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_key_from_values(*, url: Any, canonical_post_id: Any) -> str:
    clean_url = normalize_text(url)
    if clean_url:
        return "url:" + clean_url
    clean_id = normalize_text(canonical_post_id)
    if clean_id:
        return "post:" + clean_id
    raise EVOAttributeContractError(
        "Post tidak memiliki URL maupun canonical_post_id."
    )


def _slug(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", normalize_text(value).casefold()).strip("_")


def _text_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise EVOAttributeContractError(f"'{field}' harus berupa list.")
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        clean = normalize_text(item)
        key = clean.casefold()
        if clean and key not in seen:
            result.append(clean)
            seen.add(key)
    return result


# The pack provides stable IDs, labels, drivers, and short working definitions.
# It does not provide complete cue lists for all 18 entries. Cue fields therefore
# remain explicit empty lists until a category/client map supplies them.
_SEED_ATTRIBUTES = [
    ("ATTR_EXP_RELIABILITY", "Reliability / Performance", "Experience", "The core product/service works as promised, consistently."),
    ("ATTR_EXP_RESPONSIVENESS", "Responsiveness / Care", "Experience", "The brand answers and resolves when the customer needs it."),
    ("ATTR_EXP_EASE", "Ease / Usability", "Experience", "Interactions are simple, fast, and low-friction."),
    ("ATTR_EXP_ENTERTAINMENT", "Entertainment / Delight", "Experience", "Engaging with the brand is enjoyable, playful, and culturally alive."),
    ("ATTR_EXP_PARTICIPATION", "Participation / Co-creation", "Experience", "Audiences do something with the brand, not only watch it."),
    ("ATTR_EXP_INNOVATION", "Innovation / Modernity", "Experience", "The brand feels current, inventive, and ahead."),
    ("ATTR_VAL_ACCOUNTABILITY", "Accountability / Honesty", "Values", "The brand owns problems, is transparent, and keeps its word."),
    ("ATTR_VAL_LOCALPRIDE", "Local Pride / Cultural Legitimacy", "Values", "The brand belongs to and champions its audience's identity."),
    ("ATTR_VAL_SUSTAINABILITY", "Sustainability / Responsibility", "Values", "The brand acts credibly on environmental and social responsibility."),
    ("ATTR_VAL_EMPOWERMENT", "Empowerment / Inclusion", "Values", "The brand lifts, includes, and gives agency to its audience."),
    ("ATTR_VAL_COLLABORATION", "Collaboration / Partnership", "Values", "The brand allies with people or brands the audience trusts."),
    ("ATTR_VAL_SAFETY", "Safety / Security / Trust", "Values", "The brand can be trusted with money, data, and wellbeing."),
    ("ATTR_OFF_AFFORDABILITY", "Affordability / Value-for-money", "Offer", "The price and benefit trade-off reads as fair or generous."),
    ("ATTR_OFF_INCENTIVE", "Incentive / Reward", "Offer", "Giveaways, loyalty, and perks add tangible value."),
    ("ATTR_OFF_ACCESS", "Access / Availability", "Offer", "The offer is easy to reach, obtain, and use where needed."),
    ("ATTR_OFF_PACKAGE", "Package / Product Design", "Offer", "The way the offer is bundled fits how people actually buy."),
    ("ATTR_OFF_CLARITY", "Offer Clarity", "Offer", "Terms, pricing, and value are understandable, not hidden."),
    ("ATTR_OFF_CHOICE", "Choice / Flexibility", "Offer", "The audience can pick what fits them; the offer is not one-size-fits-all."),
]


def seed_attribute_map() -> dict[str, Any]:
    return {
        "map_id": EVO_SEED_MAP_ID,
        "map_version": "1.0",
        "map_name": "EVO Generic Seed Attribute Map",
        "map_source": "evo_seed",
        "category": "generic",
        "description": (
            "Category-neutral fallback map from the EVO skill pack. "
            "Cue lists are intentionally empty until category/client definitions are approved."
        ),
        "attributes": [
            {
                "attribute_id": attribute_id,
                "attribute": label,
                "driver": driver,
                "working_definition": definition,
                "positive_cues": [],
                "negative_cues": [],
                "exclusion_cues": [],
            }
            for attribute_id, label, driver, definition in _SEED_ATTRIBUTES
        ],
    }


def validate_attribute_map_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise EVOAttributeContractError("Attribute map harus berupa object.")

    map_version = normalize_text(payload.get("map_version"))
    map_name = normalize_text(payload.get("map_name"))
    map_source = normalize_text(payload.get("map_source")).casefold()
    category = normalize_text(payload.get("category")) or "generic"
    if not map_version:
        raise EVOAttributeContractError("'map_version' wajib diisi.")
    if not map_name:
        raise EVOAttributeContractError("'map_name' wajib diisi.")
    if map_source not in {"client_approved", "category_specific", "evo_seed"}:
        raise EVOAttributeContractError(
            "map_source harus client_approved, category_specific, atau evo_seed."
        )

    raw_attributes = payload.get("attributes")
    if not isinstance(raw_attributes, list) or not raw_attributes:
        raise EVOAttributeContractError("'attributes' harus list yang tidak kosong.")

    attributes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_attributes):
        if not isinstance(raw, Mapping):
            raise EVOAttributeContractError(f"attributes[{index}] harus object.")
        attribute_id = normalize_text(raw.get("attribute_id")).upper()
        label = normalize_text(raw.get("attribute"))
        driver = normalize_text(raw.get("driver")).title()
        definition = normalize_text(raw.get("working_definition"))
        if not attribute_id or not re.fullmatch(r"ATTR_(EXP|VAL|OFF)_[A-Z0-9_]+", attribute_id):
            raise EVOAttributeContractError(
                f"attributes[{index}].attribute_id tidak valid: '{attribute_id}'."
            )
        if attribute_id in seen:
            raise EVOAttributeContractError(f"Duplicate attribute_id '{attribute_id}'.")
        if not label or not definition:
            raise EVOAttributeContractError(
                f"attributes[{index}] wajib memiliki attribute dan working_definition."
            )
        if driver not in EVO_DRIVERS:
            raise EVOAttributeContractError(
                f"attributes[{index}].driver harus Experience, Values, atau Offer."
            )
        seen.add(attribute_id)
        attributes.append(
            {
                "attribute_id": attribute_id,
                "attribute": label,
                "driver": driver,
                "working_definition": definition,
                "positive_cues": _text_list(raw.get("positive_cues"), "positive_cues"),
                "negative_cues": _text_list(raw.get("negative_cues"), "negative_cues"),
                "exclusion_cues": _text_list(raw.get("exclusion_cues"), "exclusion_cues"),
            }
        )

    map_id = normalize_text(payload.get("map_id"))
    if not map_id:
        map_id = "evo_map_" + "_".join(
            filter(None, (_slug(map_source), _slug(category), _slug(map_version)))
        )

    return {
        "map_id": map_id,
        "map_version": map_version,
        "map_name": map_name,
        "map_source": map_source,
        "category": category,
        "description": normalize_text(payload.get("description")) or None,
        "attributes": attributes,
    }


def attribute_index(attribute_map: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    normalized = validate_attribute_map_payload(attribute_map)
    return {
        item["attribute_id"]: deepcopy(item)
        for item in normalized["attributes"]
    }


def classification_instruction(attribute_map: Mapping[str, Any]) -> dict[str, Any]:
    normalized = validate_attribute_map_payload(attribute_map)
    return {
        "prompt_version": EVO_PROMPT_VERSION,
        "system_instruction": (
            "Classify each supplied post into the fixed EVO attribute map. "
            "Return a JSON array only, exactly one object per post. Choose one "
            "primary_attribute_id from the registered map. Use UNMAPPED with "
            "classification_status=review_needed when no attribute fits. Use "
            "NOT_RELEVANT with classification_status=not_relevant when the post "
            "does not form a material brand perception. Do not invent quotes."
        ),
        "result_schema": {
            "canonical_key": "string",
            "content_hash": "string",
            "issue_name": "short material issue grounded in the post",
            "primary_attribute_id": "registered ATTR_* id | UNMAPPED | NOT_RELEVANT",
            "secondary_attribute_id": "registered ATTR_* id or null",
            "classification_status": "classified | not_relevant | review_needed",
            "classification_confidence": "number 0..1",
            "classification_rationale": "one sentence grounded in post wording",
        },
        "attribute_map": normalized,
    }


def attribute_map_hash(attribute_map: Mapping[str, Any]) -> str:
    normalized = validate_attribute_map_payload(attribute_map)
    raw = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "EVOAttributeContractError",
    "EVO_CLASSIFICATION_STATUSES",
    "EVO_DRIVERS",
    "EVO_PROMPT_VERSION",
    "EVO_SEED_MAP_ID",
    "attribute_index",
    "attribute_map_hash",
    "canonical_content_hash",
    "canonical_key_from_values",
    "classification_instruction",
    "normalize_text",
    "seed_attribute_map",
    "validate_attribute_map_payload",
]
