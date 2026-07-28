"""Task 1 builder for the EVO Perception Intelligence report.

The builder consumes canonical posts joined to the persisted EVO attribute
classification cache.  Attribute-level scores are never inferred from driver
aggregates.  All values consumed by Task 2 are frozen in report_input_v1 views.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from statistics import mean
from typing import Any

from reporting.contracts.report_input_contract_v1 import add_limitation
from reporting.enrichment.evo_attribute_batch_builder import (
    EVOAttributeBatchError,
    get_evo_enriched_scope_posts,
)
from reporting.enrichment.evo_attribute_contract import EVO_DRIVERS
from reporting.task1.base_builder import (
    BaseReportInputBuilder,
    BuildRequest,
    ReportBuildError,
)


REPORT_TYPE_ID = "evo_perception_intelligence"
ATTRIBUTE_SCORE_FORMULA = "count_sentiment_point=(net_sentiment+100)/2"


def _num(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _brand_key(value: Any) -> str:
    return " ".join(str(value or "").split()).casefold()


def _pct(part: float, whole: float) -> float | None:
    return round(part * 100 / whole, 2) if whole else None


def _sentiment_counts(posts: list[Mapping[str, Any]]) -> Counter[str]:
    return Counter(str(post.get("sentiment") or "unclassified").casefold() for post in posts)


def _net_sentiment(posts: list[Mapping[str, Any]]) -> float | None:
    if not posts:
        return None
    counts = _sentiment_counts(posts)
    return round((counts["positive"] - counts["negative"]) * 100 / len(posts), 2)


def _sentiment_point(posts: list[Mapping[str, Any]]) -> float | None:
    net = _net_sentiment(posts)
    return None if net is None else round((net + 100) / 2, 2)


def _index(value: float | None, category_value: float | None) -> float | None:
    if value is None or category_value in (None, 0):
        return None
    return round(value * 100 / category_value, 2)


def _avg_interactions(posts: list[Mapping[str, Any]]) -> float | None:
    if not posts:
        return None
    return round(sum(_num(post.get("interactions")) for post in posts) / len(posts), 2)


def _score_band(score: float | None) -> tuple[str | None, str | None]:
    if score is None:
        return None, None
    if score < 90:
        return "underperform", "Underperform"
    if score <= 110:
        return "on_par", "On Par"
    return "outperform", "Outperform"


def _confidence(sample_size: int) -> str:
    if sample_size < 10:
        return "low_confidence"
    if sample_size < 30:
        return "directional"
    return "adequate_directional"


def _assignment(post: Mapping[str, Any]) -> Mapping[str, Any] | None:
    value = post.get("evo_attribute_assignment")
    if not isinstance(value, Mapping):
        return None
    if str(value.get("classification_status") or "").casefold() != "classified":
        return None
    return value


def _journey_stage(post: Mapping[str, Any]) -> str:
    """Conservative observable-signal journey mapping.

    Owned content is Awareness. Social audience response is Engagement.
    Earned/mainstream content is Perception Impact because the meaning is
    carried beyond the brand's owned voice. This does not claim commercial
    impact.
    """

    source_type = str(post.get("source_type") or "").casefold()
    if source_type == "owned":
        return "Awareness"
    if source_type in {"earned", "mainstream"}:
        return "Perception Impact"
    return "Engagement"


def _move_type(
    *,
    focus_posts: int,
    focus_score: float,
    best_score: float,
    focus_net: float | None,
) -> str:
    if focus_posts == 0 and best_score > 0:
        return "Build"
    if focus_posts < 10:
        return "Test"
    if focus_net is not None and focus_net < 0:
        return "Fix"
    if focus_score >= best_score and focus_score >= 60:
        return "Scale"
    if focus_score >= 60:
        return "Protect"
    if best_score - focus_score >= 15:
        return "Build"
    return "Monitor"


class EVOPerceptionIntelligenceBuilder(BaseReportInputBuilder):
    report_type_id = REPORT_TYPE_ID
    builder_version = "1.0.0"

    def build_views(self, report_input: dict[str, Any], request: BuildRequest) -> None:
        scope = dict(request.scope or {})
        focus_brand = request.client_brand or request.project_name
        competitors = list(request.competitor_brands)

        try:
            enriched = get_evo_enriched_scope_posts(
                focus_brand=focus_brand,
                competitor_brands=competitors,
                map_id=scope.get("evo_attribute_map_id"),
                category=scope.get("evo_category"),
                start_date=request.start_date,
                end_date=request.end_date,
                channels=request.channels or None,
                keywords=scope.get("keywords") or None,
                exclude_keywords=scope.get("exclude_keywords") or None,
                match_mode=scope.get("match_mode") or "any",
            )
        except EVOAttributeBatchError as exc:
            raise ReportBuildError(f"EVO tidak dapat membaca attribute cache: {exc}") from exc

        posts = list(enriched.get("posts") or [])
        attribute_map = dict(enriched.get("attribute_map") or {})
        audit = dict(enriched.get("classification_audit") or {})
        brand_universe = list((enriched.get("scope") or {}).get("brand_universe") or [])
        if not brand_universe:
            brand_universe = [focus_brand, *competitors]

        report_input["scope"]["evo_attribute_map"] = {
            key: attribute_map.get(key)
            for key in ("map_id", "map_version", "map_name", "map_source", "category")
        }
        report_input["scope"]["evo_classification_audit"] = audit
        report_input["scope"]["evo_metric_contract"] = {
            "attribute_score_formula": ATTRIBUTE_SCORE_FORMULA,
            "driver_score_formula": "mean(sentiment_index, virality_index)",
            "evo_score_formula": "mean(total_driver_score across E/V/O)",
            "basis": "canonical unique tagged posts",
        }

        if not posts:
            self._mark_all_remaining_na(
                report_input,
                reason="Tidak ada canonical post pada scope EVO.",
            )
            return

        classified = [post for post in posts if _assignment(post)]
        coverage = audit.get("population_coverage_pct")
        if coverage is not None and float(coverage) < 100:
            add_limitation(
                report_input,
                f"Attribute classification mencakup {coverage}% dari populasi eligible; "
                "hasil atribut bersifat directional.",
            )
        missing_campaigns = list((enriched.get("scope") or {}).get("missing_campaigns") or [])
        if missing_campaigns:
            add_limitation(
                report_input,
                "Benchmark tidak ditemukan pada database: " + ", ".join(missing_campaigns),
            )
        if not classified:
            self._mark_all_remaining_na(
                report_input,
                reason="Belum ada post berstatus classified pada EVO attribute cache.",
            )
            return

        by_brand: dict[str, list[dict[str, Any]]] = defaultdict(list)
        by_brand_driver: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        by_brand_attribute: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        by_driver: dict[str, list[dict[str, Any]]] = defaultdict(list)
        journey: dict[tuple[str, str], int] = Counter()

        for post in classified:
            brand = _brand_key(post.get("project_name") or "(tidak diketahui)")
            assignment = _assignment(post) or {}
            driver = str(assignment.get("primary_driver") or "")
            attribute_id = str(assignment.get("primary_attribute_id") or "")
            by_brand[brand].append(post)
            by_brand_driver[(brand, driver)].append(post)
            by_brand_attribute[(brand, attribute_id)].append(post)
            by_driver[driver].append(post)
            journey[(brand, _journey_stage(post))] += 1

        driver_rows: list[dict[str, Any]] = []
        brand_driver_scores: dict[str, list[float]] = defaultdict(list)
        for brand in brand_universe:
            brand_key = _brand_key(brand)
            brand_total = len(by_brand.get(brand_key, []))
            for driver in EVO_DRIVERS:
                group = by_brand_driver.get((brand_key, driver), [])
                category_group = by_driver.get(driver, [])
                sentiment_index = _index(_sentiment_point(group), _sentiment_point(category_group))
                virality_index = _index(_avg_interactions(group), _avg_interactions(category_group))
                components = [value for value in (sentiment_index, virality_index) if value is not None]
                total_score = round(mean(components), 2) if components else None
                if total_score is not None:
                    brand_driver_scores[brand_key].append(total_score)
                band_code, band_label = _score_band(total_score)
                driver_rows.append(
                    {
                        "Brand": brand,
                        "Driver": driver,
                        "Posts": len(group),
                        "EVO Share %": _pct(len(group), brand_total),
                        "Net Sentiment": _net_sentiment(group),
                        "Sentiment Index": sentiment_index,
                        "Virality Index": virality_index,
                        "Total Driver Score": total_score,
                        "Score Band": band_code,
                        "Score Band Label": band_label,
                        "Confidence": _confidence(len(group)),
                    }
                )

        brand_summary_rows: list[dict[str, Any]] = []
        for brand in brand_universe:
            brand_key = _brand_key(brand)
            scores = brand_driver_scores.get(brand_key, [])
            evo_score = round(mean(scores), 2) if scores else None
            band_code, band_label = _score_band(evo_score)
            brand_summary_rows.append(
                {
                    "Brand": brand,
                    "EVOScore": evo_score,
                    "Score Band": band_code,
                    "Score Band Label": band_label,
                    "Total Tagged Posts": len(by_brand.get(brand_key, [])),
                    "Confidence": _confidence(len(by_brand.get(brand_key, []))),
                }
            )

        attributes = list(attribute_map.get("attributes") or [])
        focus_attribute_rows: dict[str, dict[str, Any]] = {}
        attribute_rows: list[dict[str, Any]] = []
        for attribute in attributes:
            attribute_id = str(attribute.get("attribute_id") or "")
            label = str(attribute.get("attribute") or attribute_id)
            driver = str(attribute.get("driver") or "")
            scores_by_brand: dict[str, float] = {}
            for brand in brand_universe:
                group = by_brand_attribute.get((_brand_key(brand), attribute_id), [])
                scores_by_brand[brand] = _sentiment_point(group) or 0.0

            non_focus = [
                (brand, score)
                for brand, score in scores_by_brand.items()
                if _brand_key(brand) != _brand_key(focus_brand)
                and by_brand_attribute.get((_brand_key(brand), attribute_id))
            ]
            best_brand, best_score = (
                max(non_focus, key=lambda item: item[1])
                if non_focus
                else (None, 0.0)
            )
            focus_score = next(
                (
                    score
                    for brand, score in scores_by_brand.items()
                    if _brand_key(brand) == _brand_key(focus_brand)
                ),
                0.0,
            )
            for brand in brand_universe:
                group = by_brand_attribute.get((_brand_key(brand), attribute_id), [])
                row = {
                    "Brand": brand,
                    "Attribute ID": attribute_id,
                    "Attribute": label,
                    "Driver": driver,
                    "Posts": len(group),
                    "Net Sentiment": _net_sentiment(group),
                    "Attribute Score": scores_by_brand.get(brand, 0.0),
                    "Confidence": _confidence(len(group)),
                    "Best Brand": best_brand if _brand_key(brand) == _brand_key(focus_brand) else None,
                    "Best Brand Score": best_score if _brand_key(brand) == _brand_key(focus_brand) else None,
                    "Attribute Gap": (
                        round(best_score - focus_score, 2)
                        if _brand_key(brand) == _brand_key(focus_brand) and best_brand
                        else None
                    ),
                    "Whitespace": bool(
                        _brand_key(brand) == _brand_key(focus_brand)
                        and best_score > 0
                        and focus_score == 0
                    ),
                }
                attribute_rows.append(row)
                if _brand_key(brand) == _brand_key(focus_brand):
                    focus_attribute_rows[attribute_id] = row

        journey_rows = [
            {
                "Brand": brand,
                "Awareness": int(journey[(_brand_key(brand), "Awareness")]),
                "Engagement": int(journey[(_brand_key(brand), "Engagement")]),
                "Perception Impact": int(journey[(_brand_key(brand), "Perception Impact")]),
                "Basis": "observable source role on tagged canonical posts",
            }
            for brand in brand_universe
        ]

        evidence_rows: list[dict[str, Any]] = []
        ranked = sorted(
            classified,
            key=lambda post: (_num(post.get("interactions")), _num(post.get("views"))),
            reverse=True,
        )
        for post in ranked[:50]:
            assignment = _assignment(post) or {}
            evidence_rows.append(
                {
                    "Brand": post.get("project_name"),
                    "Issue": assignment.get("issue_name"),
                    "Attribute ID": assignment.get("primary_attribute_id"),
                    "Attribute": assignment.get("primary_attribute_label"),
                    "Driver": assignment.get("primary_driver"),
                    "Sentiment": post.get("sentiment"),
                    "Content": post.get("content") or post.get("title"),
                    "Interactions": _num(post.get("interactions")),
                    "Views": _num(post.get("views")),
                    "Source URL": post.get("url"),
                    "Confidence": assignment.get("confidence"),
                }
            )

        recommendation_rows: list[dict[str, Any]] = []
        for attribute in attributes:
            attribute_id = str(attribute.get("attribute_id") or "")
            row = focus_attribute_rows.get(attribute_id) or {}
            focus_posts = int(row.get("Posts") or 0)
            focus_score = _num(row.get("Attribute Score"))
            best_score = _num(row.get("Best Brand Score"))
            gap = _num(row.get("Attribute Gap"))
            move = _move_type(
                focus_posts=focus_posts,
                focus_score=focus_score,
                best_score=best_score,
                focus_net=row.get("Net Sentiment"),
            )
            focus_evidence = by_brand_attribute.get((_brand_key(focus_brand), attribute_id), [])
            recommendation_rows.append(
                {
                    "Brand": focus_brand,
                    "Attribute ID": attribute_id,
                    "Attribute": attribute.get("attribute"),
                    "Driver": attribute.get("driver"),
                    "Move Type": move,
                    "Priority": (
                        "HIGH" if move in {"Fix", "Build"} and (gap >= 15 or focus_posts >= 10)
                        else "MEDIUM" if move in {"Scale", "Protect", "Test"}
                        else "LOW"
                    ),
                    "Rationale": (
                        f"Focus score {round(focus_score, 2)}; benchmark "
                        f"{row.get('Best Brand') or 'N/A'} {round(best_score, 2)}; "
                        f"gap {round(gap, 2)}; sample {focus_posts}."
                    ),
                    "Evidence Status": _confidence(focus_posts),
                    "evidence_id": f"{focus_brand}:{attribute_id}",
                    "source_url": (
                        focus_evidence[0].get("url")
                        if focus_evidence
                        else None
                    ),
                    "Smallest Next Step": (
                        "Validate the attribute with a larger tagged sample."
                        if focus_posts < 30
                        else "Turn the strongest evidence pattern into one measurable intervention."
                    ),
                }
            )

        self._add_qt(report_input, "qt_evo_brand_summary", brand_summary_rows)
        self._add_qt(report_input, "qt_evo_driver_scorecard", driver_rows)
        self._add_qt(report_input, "qt_evo_attribute_scorecard", attribute_rows)
        self._add_qt(report_input, "qt_evo_journey_matrix", journey_rows)
        self._add_ql(
            report_input,
            "ql_evo_evidence_cards",
            evidence_rows,
            "Evidence berasal dari canonical post yang memiliki cached EVO attribute tag.",
        )
        self._add_ql(
            report_input,
            "ql_evo_recommendation_inputs",
            recommendation_rows,
            "Move diturunkan dari score, gap, polarity, dan sample confidence.",
        )

        report_input["evo"] = {
            "classification_audit": audit,
            "metric_manifest": {
                "attribute_score_formula": ATTRIBUTE_SCORE_FORMULA,
                "driver_score_formula": "mean(sentiment_index, virality_index)",
                "evo_score_formula": "mean(total_driver_score across available E/V/O)",
                "basis": "canonical unique tagged posts",
            },
            "component_completeness_audit": {
                "B2_attribute_architecture": "produced",
                "B3_driver_landscape": "produced",
                "B5_focus_brand_scorecard": "produced",
                "B7_attribute_gap": "produced" if competitors else "skipped - no benchmark",
                "D2_comparative_journey": "produced" if competitors else "skipped - no benchmark",
                "C3_evidence": "produced" if evidence_rows else "skipped - no classified evidence",
            },
        }
        self._mark_all_remaining_na(
            report_input,
            reason="View EVO belum memiliki bukti yang cukup pada scope ini.",
        )

    def _add_qt(self, report_input: dict[str, Any], view_id: str, rows: list[dict[str, Any]]) -> None:
        if view_id in self.quantitative_view_ids:
            self.add_quantitative_view(
                report_input,
                view_id=view_id,
                rows=rows,
                metadata={"metric_basis": "canonical unique tagged posts"},
            )

    def _add_ql(
        self,
        report_input: dict[str, Any],
        view_id: str,
        rows: list[dict[str, Any]],
        reason: str,
    ) -> None:
        if view_id in self.qualitative_view_ids:
            self.add_qualitative_view(
                report_input,
                view_id=view_id,
                rows=rows,
                evidence_reason=reason,
            )

    def _mark_all_remaining_na(self, report_input: dict[str, Any], *, reason: str) -> None:
        for view_id in self.quantitative_view_ids:
            if view_id not in report_input["quantitative_views"]:
                self.mark_view_na(
                    report_input,
                    view_id=view_id,
                    view_type="quantitative",
                    reason=reason,
                )
        for view_id in self.qualitative_view_ids:
            if view_id not in report_input["qualitative_views"]:
                self.mark_view_na(
                    report_input,
                    view_id=view_id,
                    view_type="qualitative",
                    reason=reason,
                )


def build_evo_data_preview(
    report_input_id: str,
    *,
    allow_partial: bool = True,
) -> dict[str, Any]:
    from reporting.task2.renderers.evo_perception_intelligence_report_renderer import (
        build_evo_report_data_preview,
    )

    return build_evo_report_data_preview(report_input_id, allow_partial=allow_partial)


def build_evo_report_package(
    *,
    report_input_id: str,
    audience_context: str | None = None,
    audience_pov: str | None = None,
) -> dict[str, Any]:
    from reporting.task2.renderers.evo_perception_intelligence_report_renderer import (
        build_evo_report_package as _build,
    )

    return _build(
        report_input_id,
        audience_context=audience_context,
        audience_pov=audience_pov,
    )


BUILDER_CLASS = EVOPerceptionIntelligenceBuilder

__all__ = [
    "ATTRIBUTE_SCORE_FORMULA",
    "BUILDER_CLASS",
    "EVOPerceptionIntelligenceBuilder",
    "build_evo_data_preview",
    "build_evo_report_package",
]
