"""Validate Claude EVO attribute batch output before database persistence."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from reporting.enrichment.evo_attribute_contract import (
    EVO_CLASSIFICATION_STATUSES,
    EVOAttributeContractError,
    attribute_index,
    normalize_text,
    validate_attribute_map_payload,
)


class EVOAttributeResultValidationError(ValueError):
    """EVO batch output is incomplete, foreign, or outside the active map."""


def _require_text(value: Any, field: str) -> str:
    clean = normalize_text(value)
    if not clean:
        raise EVOAttributeResultValidationError(f"'{field}' wajib tidak kosong.")
    return clean


def _confidence(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise EVOAttributeResultValidationError(
            "classification_confidence harus angka 0..1."
        ) from exc
    if number < 0 or number > 1:
        raise EVOAttributeResultValidationError(
            "classification_confidence harus berada pada rentang 0..1."
        )
    return round(number, 4)


def validate_evo_attribute_batch_results(
    *,
    batch: Mapping[str, Any],
    attribute_map: Mapping[str, Any],
    results: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if not isinstance(results, list):
        raise EVOAttributeResultValidationError("results harus list.")
    try:
        normalized_map = validate_attribute_map_payload(attribute_map)
        attributes = attribute_index(normalized_map)
    except EVOAttributeContractError as exc:
        raise EVOAttributeResultValidationError(str(exc)) from exc

    post_refs = batch.get("post_refs")
    if not isinstance(post_refs, list) or not post_refs:
        raise EVOAttributeResultValidationError("Batch tidak memiliki post_refs valid.")

    expected: dict[tuple[str, str], dict[str, Any]] = {}
    for index, ref in enumerate(post_refs):
        if not isinstance(ref, Mapping):
            raise EVOAttributeResultValidationError(f"post_refs[{index}] harus object.")
        key = (
            _require_text(ref.get("canonical_key"), "canonical_key"),
            _require_text(ref.get("content_hash"), "content_hash"),
        )
        if key in expected:
            raise EVOAttributeResultValidationError("post_refs batch duplikat.")
        expected[key] = dict(ref)

    if len(results) != len(expected):
        raise EVOAttributeResultValidationError(
            f"Jumlah result {len(results)} harus sama dengan jumlah post batch {len(expected)}."
        )

    seen: set[tuple[str, str]] = set()
    normalized: list[dict[str, Any]] = []
    for index, result in enumerate(results):
        if not isinstance(result, Mapping):
            raise EVOAttributeResultValidationError(f"results[{index}] harus object.")
        canonical_key = _require_text(result.get("canonical_key"), "canonical_key")
        content_hash = _require_text(result.get("content_hash"), "content_hash")
        key = (canonical_key, content_hash)
        if key not in expected:
            raise EVOAttributeResultValidationError(
                f"results[{index}] bukan post dari batch yang diterbitkan."
            )
        if key in seen:
            raise EVOAttributeResultValidationError(
                f"results[{index}] menduplikasi post yang sama."
            )
        seen.add(key)

        status = _require_text(
            result.get("classification_status"), "classification_status"
        ).casefold()
        if status not in EVO_CLASSIFICATION_STATUSES:
            raise EVOAttributeResultValidationError(
                "classification_status harus classified, not_relevant, atau review_needed."
            )

        primary_id = _require_text(
            result.get("primary_attribute_id"), "primary_attribute_id"
        ).upper()
        issue_name = normalize_text(result.get("issue_name"))[:240] or None
        rationale = normalize_text(result.get("classification_rationale"))[:600] or None
        confidence = _confidence(result.get("classification_confidence"))

        if status == "classified":
            if primary_id not in attributes:
                raise EVOAttributeResultValidationError(
                    f"primary_attribute_id '{primary_id}' tidak ada di attribute map."
                )
            if not issue_name:
                raise EVOAttributeResultValidationError(
                    "Status classified wajib memiliki issue_name."
                )
            attribute = attributes[primary_id]
            primary_label = attribute["attribute"]
            primary_driver = attribute["driver"]
        elif status == "review_needed":
            if primary_id != "UNMAPPED":
                raise EVOAttributeResultValidationError(
                    "Status review_needed wajib memakai primary_attribute_id UNMAPPED."
                )
            if not issue_name or not rationale:
                raise EVOAttributeResultValidationError(
                    "review_needed wajib memiliki issue_name dan classification_rationale."
                )
            primary_label = "Unmapped"
            primary_driver = None
        else:
            if primary_id != "NOT_RELEVANT":
                raise EVOAttributeResultValidationError(
                    "Status not_relevant wajib memakai primary_attribute_id NOT_RELEVANT."
                )
            primary_label = "Not Relevant"
            primary_driver = None

        secondary_raw = normalize_text(result.get("secondary_attribute_id")).upper()
        secondary_id = secondary_raw or None
        if secondary_id:
            if secondary_id not in attributes:
                raise EVOAttributeResultValidationError(
                    f"secondary_attribute_id '{secondary_id}' tidak ada di attribute map."
                )
            if secondary_id == primary_id:
                raise EVOAttributeResultValidationError(
                    "secondary_attribute_id tidak boleh sama dengan primary_attribute_id."
                )
            if status != "classified":
                raise EVOAttributeResultValidationError(
                    "secondary_attribute_id hanya boleh diisi untuk status classified."
                )

        ref = expected[key]
        campaign_id = ref.get("campaign_id")
        if campaign_id is None:
            raise EVOAttributeResultValidationError(
                "post_refs batch tidak memiliki campaign_id."
            )
        normalized.append(
            {
                "campaign_id": int(campaign_id),
                "brand": _require_text(ref.get("project_name"), "project_name"),
                "canonical_key": canonical_key,
                "content_hash": content_hash,
                "canonical_post_id": ref.get("canonical_post_id"),
                "issue_name": issue_name,
                "primary_attribute_id": primary_id,
                "primary_attribute_label": primary_label,
                "primary_driver": primary_driver,
                "secondary_attribute_id": secondary_id,
                "classification_status": status,
                "confidence": confidence,
                "classification_rationale": rationale,
                "classification_source": "auto_llm",
                "raw_result": deepcopy(dict(result)),
            }
        )

    if set(expected) != seen:
        raise EVOAttributeResultValidationError(
            "Ada post batch yang belum diberi result."
        )
    return normalized


__all__ = [
    "EVOAttributeResultValidationError",
    "validate_evo_attribute_batch_results",
]
