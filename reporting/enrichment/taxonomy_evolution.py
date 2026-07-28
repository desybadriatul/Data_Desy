"""Helpers for turning `review_needed` topic assignments into taxonomy candidates.

The active taxonomy remains explicit and versioned. This module does not mutate
an active taxonomy automatically; it extracts saved `review_needed`/legacy
`other_emerging_topic` assignments into stable candidate clusters so Claude can
create and save a new taxonomy version with the existing save_topic_taxonomy tool.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from typing import Any


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _slug(value: Any, *, fallback: str = "candidate_topic") -> str:
    text = _text(value).casefold()
    slug = re.sub(r"[^a-z0-9]+", "_", text).strip("_")[:60]
    return slug or fallback


def _snippet(row: Mapping[str, Any], limit: int = 220) -> str:
    return _text(
        row.get("content")
        or row.get("Content")
        or row.get("caption")
        or row.get("Caption")
        or row.get("title")
        or row.get("Title")
    )[:limit]


def _assignment_from_row(row: Mapping[str, Any], assignment_field: str | None = None) -> Mapping[str, Any] | None:
    if assignment_field:
        value = row.get(assignment_field)
        if isinstance(value, Mapping):
            return value
    for key in ("topic_assignment", "issue_assignment", "assignment"):
        value = row.get(key)
        if isinstance(value, Mapping):
            return value
    # Competitive rows flatten assignment fields onto the row.
    if row.get("classification_status") or row.get("primary_topic_id"):
        return row
    return None


def extract_taxonomy_evolution_candidates(
    rows: Iterable[Mapping[str, Any]],
    *,
    taxonomy_version: str | None = None,
    assignment_field: str | None = None,
    min_evidence_count: int = 1,
    max_candidates: int = 12,
    examples_per_candidate: int = 3,
) -> dict[str, Any]:
    """Build candidate topic clusters from saved emerging-topic assignments."""
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    status_counts = Counter()
    total_rows = 0

    for row in rows:
        total_rows += 1
        assignment = _assignment_from_row(row, assignment_field)
        if not assignment:
            continue
        status = _text(assignment.get("classification_status")).casefold()
        topic_id = _text(assignment.get("primary_topic_id") or assignment.get("topic_id")).casefold()
        label = _text(assignment.get("primary_topic_label") or assignment.get("topic_label") or assignment.get("topic"))
        status_counts[status or "unknown"] += 1
        is_emerging = (
            status == "review_needed"
            or topic_id == "other_emerging_topic"
            or label.casefold() in {"topik baru", "topik baru / perlu review", "other emerging topic"}
        )
        if not is_emerging:
            continue
        detail = (
            _text(assignment.get("emerging_topic_detail"))
            or _text(assignment.get("classification_reason"))
            or label
            or "Topik Baru"
        )
        key = _slug(detail)
        groups[key].append(row)

    candidates: list[dict[str, Any]] = []
    for key, items in groups.items():
        if len(items) < int(min_evidence_count or 1):
            continue
        labels = Counter()
        reasons = Counter()
        examples = []
        for row in items:
            assignment = _assignment_from_row(row, assignment_field) or {}
            detail = (
                _text(assignment.get("emerging_topic_detail"))
                or _text(assignment.get("classification_reason"))
                or _text(assignment.get("primary_topic_label"))
                or "Topik Baru"
            )
            labels[detail] += 1
            if assignment.get("classification_reason"):
                reasons[_text(assignment.get("classification_reason"))] += 1
            if len(examples) < examples_per_candidate:
                examples.append(
                    {
                        "title": _text(row.get("title") or row.get("Title") or row.get("headline") or row.get("Headline"))[:160],
                        "snippet": _snippet(row),
                        "source_url": row.get("source_url") or row.get("url") or row.get("URL") or row.get("Link URL"),
                        "sentiment": row.get("sentiment") or row.get("Sentiment"),
                        "interactions": row.get("interactions") or row.get("Interactions") or row.get("engagement"),
                    }
                )
        top_label = labels.most_common(1)[0][0]
        candidates.append(
            {
                "candidate_topic_id": _slug(top_label),
                "candidate_label": top_label[:80],
                "status": "candidate",
                "evidence_count": len(items),
                "definition_hint": (reasons.most_common(1)[0][0] if reasons else f"Emerging conversation cluster: {top_label}")[:260],
                "example_rows": examples,
            }
        )

    candidates.sort(key=lambda item: item["evidence_count"], reverse=True)
    candidates = candidates[:max_candidates]
    return {
        "status": "HAS_CANDIDATES" if candidates else "NO_CANDIDATES",
        "taxonomy_version": taxonomy_version,
        "policy": "review_needed and legacy other_emerging_topic assignments become candidate topics for the next taxonomy revision; they are not silently counted as stable topics.",
        "total_rows_scanned": total_rows,
        "assignment_status_counts": dict(status_counts),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "next_action": (
            "Create a new taxonomy JSON version that keeps existing active topics, adds approved candidates as normal topics, preserves other_emerging_topic and not_relevant, then call save_topic_taxonomy."
            if candidates else None
        ),
    }


def taxonomy_expansion_instruction(project_name: str, taxonomy_version: str | None, candidates: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    candidate_list = [dict(item) for item in candidates]
    return {
        "project_name": project_name,
        "current_taxonomy_version": taxonomy_version,
        "candidate_count": len(candidate_list),
        "candidates": candidate_list,
        "assistant_next_steps": [
            "Do not force emerging conversations into Topik Baru as classified topics.",
            "Create a new taxonomy JSON version by retaining current stable topics and adding useful candidate topics with stable lowercase snake_case topic_id values.",
            "Keep mandatory system topics other_emerging_topic and not_relevant.",
            "Call save_topic_taxonomy(project_name, taxonomy_json, activate=True for single-brand Daily/MMR or activate=False for Competitive Analysis if taxonomy is campaign-specific).",
            "Rerun the workflow with the new taxonomy_version so new conversations are classified into real topics.",
        ],
    }


__all__ = ["extract_taxonomy_evolution_candidates", "taxonomy_expansion_instruction"]
