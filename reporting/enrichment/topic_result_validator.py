"""Validate Claude's batch output before it is saved to Cogan."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from reporting.enrichment.topic_contract import (
    CLASSIFICATION_STATUSES,
    CONFIDENCE_LEVELS,
    TopicContractError,
    normalize_text,
    validate_taxonomy_payload,
)


class TopicResultValidationError(ValueError):
    """Batch output is incomplete, invalid, or outside the active taxonomy."""


def _require_text(value: Any, field: str) -> str:
    clean = normalize_text(value)
    if not clean:
        raise TopicResultValidationError(f"'{field}' wajib tidak kosong.")
    return clean


def validate_topic_batch_results(
    *,
    batch: Mapping[str, Any],
    taxonomy: Mapping[str, Any],
    results: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Strictly require exactly one valid result for every issued batch post."""
    if not isinstance(results, list):
        raise TopicResultValidationError("results harus list.")

    try:
        taxonomy = validate_taxonomy_payload(taxonomy)
    except TopicContractError as exc:
        raise TopicResultValidationError(str(exc)) from exc

    post_refs = batch.get("post_refs")
    if not isinstance(post_refs, list) or not post_refs:
        raise TopicResultValidationError("Batch tidak memiliki post_refs valid.")

    expected: dict[tuple[str, str], dict[str, Any]] = {}
    for idx, ref in enumerate(post_refs):
        if not isinstance(ref, Mapping):
            raise TopicResultValidationError(f"post_refs[{idx}] harus object.")
        key = (
            _require_text(ref.get("canonical_key"), "canonical_key"),
            _require_text(ref.get("content_hash"), "content_hash"),
        )
        if key in expected:
            raise TopicResultValidationError("post_refs batch duplikat.")
        expected[key] = dict(ref)

    if len(results) != len(expected):
        raise TopicResultValidationError(
            f"Jumlah result {len(results)} harus sama dengan jumlah post batch "
            f"{len(expected)}."
        )

    topic_labels = {
        topic["topic_id"]: topic["label"]
        for topic in taxonomy["topics"]
    }
    seen: set[tuple[str, str]] = set()
    normalized: list[dict[str, Any]] = []

    for idx, result in enumerate(results):
        if not isinstance(result, Mapping):
            raise TopicResultValidationError(f"results[{idx}] harus object.")

        canonical_key = _require_text(result.get("canonical_key"), "canonical_key")
        content_hash = _require_text(result.get("content_hash"), "content_hash")
        key = (canonical_key, content_hash)
        if key not in expected:
            raise TopicResultValidationError(
                f"results[{idx}] bukan post dari batch yang diterbitkan."
            )
        if key in seen:
            raise TopicResultValidationError(
                f"results[{idx}] menduplikasi post yang sama."
            )
        seen.add(key)

        status = _require_text(
            result.get("classification_status"),
            "classification_status",
        ).casefold()
        if status not in CLASSIFICATION_STATUSES:
            raise TopicResultValidationError(
                "classification_status harus classified, not_relevant, atau "
                "review_needed."
            )

        confidence = _require_text(result.get("confidence"), "confidence").casefold()
        if confidence not in CONFIDENCE_LEVELS:
            raise TopicResultValidationError(
                "confidence harus high, medium, atau low."
            )

        topic_id = _require_text(
            result.get("primary_topic_id"),
            "primary_topic_id",
        ).casefold()
        if topic_id not in topic_labels:
            raise TopicResultValidationError(
                f"primary_topic_id '{topic_id}' tidak ada di taxonomy."
            )
        if status == "not_relevant" and topic_id != "not_relevant":
            raise TopicResultValidationError(
                "status not_relevant wajib memakai topic_id not_relevant."
            )
        if status == "review_needed" and topic_id != "other_emerging_topic":
            raise TopicResultValidationError(
                "status review_needed wajib memakai topic_id "
                "other_emerging_topic."
            )
        if status == "classified" and topic_id == "not_relevant":
            raise TopicResultValidationError(
                "status classified tidak boleh memakai topic_id not_relevant."
            )

        emerging_detail = normalize_text(result.get("emerging_topic_detail"))[:200] or None
        if status == "review_needed" and not emerging_detail:
            raise TopicResultValidationError(
                "review_needed wajib punya emerging_topic_detail."
            )

        normalized.append(
            {
                "canonical_key": canonical_key,
                "content_hash": content_hash,
                "canonical_post_id": expected[key].get("canonical_post_id"),
                "primary_topic_id": topic_id,
                "primary_topic_label": topic_labels[topic_id],
                "classification_status": status,
                "confidence": confidence,
                "classification_reason": normalize_text(
                    result.get("classification_reason")
                )[:500]
                or None,
                "emerging_topic_detail": emerging_detail,
                "raw_result": deepcopy(dict(result)),
            }
        )

    if set(expected) != seen:
        raise TopicResultValidationError("Ada post batch yang belum diberi result.")

    return normalized


__all__ = ["TopicResultValidationError", "validate_topic_batch_results"]
