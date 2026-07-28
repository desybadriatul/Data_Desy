"""Pure EVO sample-target and stratified-selection logic."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
import math
from typing import Any

from reporting.enrichment.evo_attribute_contract import normalize_text


DEFAULT_SAMPLE_RATIO = 0.10
DEFAULT_MIN_PER_BRAND = 30
DEFAULT_INITIAL_MAX_PER_BRAND = 100
MAX_BATCH_SIZE = 100
MAX_TARGET_PER_BRAND = 1000
STRATIFICATION_DIMENSIONS = (
    "brand",
    "channel",
    "sentiment",
    "content_type",
    "source_type",
    "period",
    "engagement_tier",
)


def effective_evo_sample_target(
    total_eligible: int,
    *,
    requested_target: int | None = None,
    ratio: float = DEFAULT_SAMPLE_RATIO,
    minimum: int = DEFAULT_MIN_PER_BRAND,
    initial_maximum: int = DEFAULT_INITIAL_MAX_PER_BRAND,
) -> int:
    total = max(0, int(total_eligible or 0))
    if total == 0:
        return 0
    if requested_target is not None and int(requested_target) > 0:
        return min(total, max(1, min(int(requested_target), MAX_TARGET_PER_BRAND)))
    ratio = max(0.01, min(float(ratio or DEFAULT_SAMPLE_RATIO), 1.0))
    minimum = max(1, int(minimum or DEFAULT_MIN_PER_BRAND))
    initial_maximum = max(minimum, int(initial_maximum or DEFAULT_INITIAL_MAX_PER_BRAND))
    if total <= minimum:
        return total
    return min(total, max(minimum, math.ceil(total * ratio)), initial_maximum)


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


def _with_engagement_tiers(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = _rank(posts)
    total = len(ranked)
    result: list[dict[str, Any]] = []
    for index, post in enumerate(ranked):
        percentile = (index + 1) / total if total else 1
        tier = "high" if percentile <= 0.20 else "medium" if percentile <= 0.50 else "low"
        item = dict(post)
        item["engagement_tier"] = tier
        item["impact_rank"] = index + 1
        item["impact_percentile"] = round(percentile, 4)
        result.append(item)
    return result


def _dimension_value(post: Mapping[str, Any], dimension: str) -> str:
    mapping = {"channel": "channel_norm", "period": "period_bucket"}
    key = mapping.get(dimension, dimension)
    return normalize_text(post.get(key)).casefold() or "unknown"


def _coverage_counts(posts: Iterable[Mapping[str, Any]]) -> dict[str, Counter[str]]:
    result: dict[str, Counter[str]] = {
        dimension: Counter() for dimension in STRATIFICATION_DIMENSIONS[1:]
    }
    for post in posts:
        for dimension in result:
            result[dimension][_dimension_value(post, dimension)] += 1
    return result


def select_stratified_posts(
    *,
    population_posts: list[Mapping[str, Any]],
    candidate_posts: list[Mapping[str, Any]],
    existing_sampled_posts: list[Mapping[str, Any]],
    select_count: int,
) -> list[dict[str, Any]]:
    """Select high-signal posts while repairing representation deficits."""
    select_count = max(0, min(int(select_count or 0), len(candidate_posts)))
    if select_count == 0:
        return []

    population = _with_engagement_tiers([dict(post) for post in population_posts])
    tier_lookup = {
        (post["canonical_key"], post["content_hash"]): post["engagement_tier"]
        for post in population
    }

    def attach_tier(items: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for raw in items:
            item = dict(raw)
            item["engagement_tier"] = tier_lookup.get(
                (item["canonical_key"], item["content_hash"]),
                item.get("engagement_tier") or "low",
            )
            out.append(item)
        return out

    candidates = attach_tier(candidate_posts)
    existing = attach_tier(existing_sampled_posts)
    final_target = len(existing) + select_count
    population_counts = _coverage_counts(population)
    current_counts = _coverage_counts(existing)
    total_population = max(1, len(population))

    target_counts: dict[str, dict[str, int]] = {}
    for dimension, counts in population_counts.items():
        target_counts[dimension] = {}
        for category, count in counts.items():
            target_counts[dimension][category] = max(
                1, int(round(final_target * count / total_population))
            )

    ranked = _rank(candidates)
    rank_index = {
        (post["canonical_key"], post["content_hash"]): index
        for index, post in enumerate(ranked)
    }
    selected: list[dict[str, Any]] = []
    remaining = {
        (post["canonical_key"], post["content_hash"]): post
        for post in candidates
    }

    impact_seed = min(select_count, max(1, math.ceil(select_count * 0.25)))
    for post in ranked[:impact_seed]:
        key = (post["canonical_key"], post["content_hash"])
        if key not in remaining:
            continue
        item = dict(remaining.pop(key))
        item["sample_reasons"] = ["top_impact"]
        selected.append(item)
        for dimension in current_counts:
            current_counts[dimension][_dimension_value(item, dimension)] += 1

    while remaining and len(selected) < select_count:
        best_key: tuple[str, str] | None = None
        best_score = -1.0
        best_reasons: list[str] = []
        for key, post in remaining.items():
            score = 0.0
            reasons: list[str] = []
            for dimension in current_counts:
                category = _dimension_value(post, dimension)
                target = target_counts.get(dimension, {}).get(category, 0)
                current = current_counts[dimension].get(category, 0)
                deficit = max(0, target - current)
                if deficit > 0 and target > 0:
                    score += deficit / target
                    reasons.append(f"coverage:{dimension}={category}")
                    if current == 0:
                        score += 0.30
            impact_position = rank_index.get(key, len(ranked))
            score += (1 - impact_position / max(1, len(ranked))) * 0.25
            if post.get("sentiment") == "negative":
                score += 0.10
                reasons.append("negative_signal")
            score += (
                float(post.get("interactions") or 0) * 1e-9
                + float(post.get("views") or 0) * 1e-12
            )
            if score > best_score:
                best_score = score
                best_key = key
                best_reasons = reasons[:4] or ["ranked_fill"]
        assert best_key is not None
        item = dict(remaining.pop(best_key))
        item["sample_reasons"] = best_reasons
        selected.append(item)
        for dimension in current_counts:
            current_counts[dimension][_dimension_value(item, dimension)] += 1

    return selected[:select_count]


__all__ = [
    "DEFAULT_INITIAL_MAX_PER_BRAND",
    "DEFAULT_MIN_PER_BRAND",
    "DEFAULT_SAMPLE_RATIO",
    "MAX_BATCH_SIZE",
    "MAX_TARGET_PER_BRAND",
    "STRATIFICATION_DIMENSIONS",
    "effective_evo_sample_target",
    "select_stratified_posts",
]
