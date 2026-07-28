"""Task 1 builder for Daily Social Media Report.

The builder never classifies text with an LLM. It reads only cached topic
assignments created through reporting.enrichment and converts canonical posts
into the registry-required qt_dsm_* / ql_dsm_* report-input views.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable

from database import db

from reporting.contracts.report_input_contract_v1 import add_limitation
from reporting.enrichment.global_relevance_filter import (
    apply_global_relevance_filter,
    compact_exclusion_examples,
)
from reporting.enrichment.taxonomy_evolution import (
    extract_taxonomy_evolution_candidates,
)
from reporting.enrichment.topic_batch_builder import (
    TopicBatchError,
    get_enriched_scope_posts,
)
from reporting.task1.base_builder import (
    BaseReportInputBuilder,
    BuildRequest,
    ReportBuildError,
)


SOCIAL_CHANNELS = frozenset(
    {"instagram", "facebook", "youtube", "tiktok", "x", "forum"}
)
INTERACTION_CHANNELS = frozenset(
    {"instagram", "facebook", "youtube", "tiktok", "x"}
)
SENTIMENTS = ("positive", "neutral", "negative")


def _n(value: Any) -> int | float:
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def _pct(part: int | float, base: int | float) -> float | None:
    return round(float(part) * 100 / float(base), 1) if base else None


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _snippet(post: Mapping[str, Any], limit: int = 800) -> str:
    return (_text(post.get("content")) or _text(post.get("title")))[:limit]


def _rank(rows: Iterable[Mapping[str, Any]], *keys: str) -> list[dict[str, Any]]:
    return sorted(
        (dict(row) for row in rows),
        key=lambda row: tuple(_n(row.get(key)) for key in keys),
        reverse=True,
    )


class DailySocialMediaReportBuilder(BaseReportInputBuilder):
    report_type_id = "daily_social_media_report"
    builder_version = "1.0.0"

    def build_views(
        self,
        report_input: dict[str, Any],
        request: BuildRequest,
    ) -> None:
        scope = dict(request.scope or {})

        try:
            enriched = get_enriched_scope_posts(
                project_name=request.project_name,
                taxonomy_version=scope.get("topic_taxonomy_version"),
                start_date=request.start_date,
                end_date=request.end_date,
                channels=request.channels or None,
                keywords=scope.get("keywords") or None,
                exclude_keywords=scope.get("exclude_keywords") or None,
                match_mode=scope.get("match_mode") or "any",
            )
        except TopicBatchError as exc:
            raise ReportBuildError(
                f"Daily Social tidak dapat membaca source/topic cache: {exc}"
            ) from exc

        # Daily Social never includes Online Media, even if the project has it.
        posts = [
            post
            for post in enriched["posts"]
            if post.get("channel_norm") in SOCIAL_CHANNELS
        ]
        if not posts:
            raise ReportBuildError(
                "Tidak ada canonical social-media post pada scope Daily Social."
            )

        relevance_result = apply_global_relevance_filter(
            posts,
            project_name=request.project_name,
            report_type_id=self.report_type_id,
            client_brand=request.client_brand or request.project_name,
            brand_universe=[request.client_brand or request.project_name],
            scope=scope,
            analysis_objective=request.analysis_objective,
            keep_review_rows=True,
        )
        posts = relevance_result["clean_rows"]
        self._attach_relevance_filter_summary(report_input, relevance_result)
        if not posts:
            raise ReportBuildError(
                "Tidak ada clean/review social-media post setelah global relevance/noise filter."
            )

        report_input["scope"]["channel_policy"] = "social_only; online_media excluded"
        report_input["scope"]["raw_topic_extraction_policy"] = "not_used_as_report_topic"
        report_input["scope"]["topic_taxonomy_version"] = (
            enriched["taxonomy"]["taxonomy_version"]
            if enriched.get("taxonomy")
            else None
        )

        report_input["metric_readiness"] = self._metric_readiness(request, posts)
        report_input["data_health"] = self._data_health(request, posts)
        for item in (
            report_input["metric_readiness"]["warnings"]
            + report_input["metric_readiness"]["blockers"]
        ):
            add_limitation(report_input, item)

        self._add_kpi(report_input, posts, enriched)
        self._add_sentiment_overall(report_input, posts)
        self._add_sentiment_by_channel(report_input, posts)
        author_rows = self._add_authors(report_input, posts)
        self._add_top_content(report_input, posts)

        topic_context = self._topic_context(posts, enriched)
        report_input["scope"]["taxonomy_evolution"] = topic_context.get("taxonomy_evolution")
        if (topic_context.get("taxonomy_evolution") or {}).get("candidate_count"):
            add_limitation(
                report_input,
                "Ada emerging topic candidate dari review_needed/Topik Baru; buat taxonomy version baru agar percakapan baru tidak terus masuk bucket Topik Baru.",
            )
        if not topic_context["taxonomy_available"]:
            self._mark_topic_views_not_available(
                report_input,
                "Taxonomy LLM report-topic belum tersedia untuk project ini.",
            )
            return
        if not topic_context["relevant_classified_posts"]:
            self._mark_topic_views_not_available(
                report_input,
                "Belum ada cached LLM report-topic status=classified pada scope ini.",
            )
            return

        if (topic_context["completion_coverage_pct"] or 0) < 100:
            add_limitation(
                report_input,
                "Topic coverage belum 100%; ranking topic hanya memakai post "
                "yang sudah selesai diklasifikasikan LLM.",
            )

        self._add_top_topics(report_input, topic_context)
        self._add_topic_sentiment_evidence(report_input, topic_context)
        self._add_topic_channel_evidence(report_input, topic_context)

    def _attach_relevance_filter_summary(
        self,
        report_input: dict[str, Any],
        relevance_result: Mapping[str, Any],
    ) -> None:
        summary = dict(relevance_result.get("summary") or {})
        summary["examples"] = compact_exclusion_examples(
            relevance_result.get("excluded_rows") or [],
            limit=5,
        )
        report_input["scope"]["global_relevance_filter"] = summary
        excluded = int(summary.get("excluded_count") or 0)
        review = int(summary.get("review_count") or 0)
        if excluded:
            add_limitation(
                report_input,
                f"Global relevance filter mengeluarkan {excluded} row noise sebelum KPI/sentiment/topic Daily Social dihitung.",
            )
        if review:
            add_limitation(
                report_input,
                f"{review} row masuk review relevance ber-confidence rendah; tetap dihitung tetapi ditandai dalam audit scope.",
            )

    def _scope_filters(
        self,
        request: BuildRequest,
        posts: list[Mapping[str, Any]],
    ) -> tuple[list[str], Any, Any, str]:
        scope = dict(request.scope or {})
        channels = sorted({str(post["channel"]) for post in posts})
        return (
            channels,
            scope.get("keywords") or None,
            scope.get("exclude_keywords") or None,
            scope.get("match_mode") or "any",
        )

    def _metric_readiness(
        self,
        request: BuildRequest,
        posts: list[Mapping[str, Any]],
    ) -> dict[str, Any]:
        """
        Use db.metric_readiness() rather than inferring raw-header availability
        from report rows. This keeps Task 1 aligned with Cogan's metric guardrail.
        """
        channels, keywords, excludes, match_mode = self._scope_filters(request, posts)
        try:
            raw = db.metric_readiness(
                request.project_name,
                request.start_date,
                request.end_date,
                channels,
                keywords,
                excludes,
                match_mode,
            )
        except Exception as exc:
            raise ReportBuildError(
                f"Gagal menjalankan db.metric_readiness: {exc}"
            ) from exc

        if raw is None:
            raise ReportBuildError("Project tidak ditemukan saat metric readiness.")

        overview = raw.get("overview") or {}
        warnings: list[str] = []
        blockers: list[str] = []
        channel_rows = raw.get("channels") or []

        if int(overview.get("canonical_posts") or 0) == 0:
            blockers.append("Tidak ada canonical post pada scope Daily Social.")

        for row in channel_rows:
            applicable = int(row.get("interactions_applicable_posts") or 0)
            available = int(row.get("interactions_available_posts") or 0)
            posts_count = int(row.get("posts") or 0)
            views_available = int(row.get("views_available_posts") or 0)
            channel = row.get("channel") or "(tidak diketahui)"
            interaction_coverage = _pct(available, applicable)
            views_coverage = _pct(views_available, posts_count)

            if applicable and available == 0:
                blockers.append(
                    f"{channel}: tidak ada post dengan komponen interactions lengkap."
                )
            elif interaction_coverage is not None and interaction_coverage < 60:
                warnings.append(
                    f"{channel}: coverage interactions {interaction_coverage}% (<60%)."
                )
            if (
                views_coverage is not None
                and 0 < views_available < posts_count
                and views_coverage < 60
            ):
                warnings.append(
                    f"{channel}: coverage views {views_coverage}% (<60%)."
                )

        unknown = raw.get("unknown_channel_rows") or []
        if unknown:
            labels = ", ".join(
                sorted(
                    {
                        str(row.get("channel") or "(tidak diketahui)")
                        for row in unknown
                    }
                )
            )
            warnings.append(
                "Channel tanpa rumus interactions terdeteksi: " + labels
            )

        parse_warnings = raw.get("parse_warnings") or {}
        for field, diagnostic in parse_warnings.items():
            nonstandard = int(diagnostic.get("nonstandard_values_detected") or 0)
            if nonstandard:
                warnings.append(
                    f"{field}: {nonstandard} raw value non-standar perlu audit."
                )

        raw_fields = {}
        for field, info in (raw.get("raw_field_status") or {}).items():
            raw_fields[field] = {
                "available_on_canonical_posts": int(
                    info.get("available_on_canonical_posts") or 0
                ),
                "detected_headers": info.get("detected_headers") or [],
                "configured_aliases": info.get("configured_aliases") or [],
            }

        channels_output = []
        for row in channel_rows:
            applicable = int(row.get("interactions_applicable_posts") or 0)
            available = int(row.get("interactions_available_posts") or 0)
            posts_count = int(row.get("posts") or 0)
            views_available = int(row.get("views_available_posts") or 0)
            channels_output.append(
                {
                    "channel": row.get("channel"),
                    "channel_type": row.get("channel_norm"),
                    "posts": posts_count,
                    "interaction_applicable_posts": applicable,
                    "interaction_available_posts": available,
                    "views_available_posts": views_available,
                    "interaction_coverage_pct": _pct(available, applicable),
                    "views_coverage_pct": _pct(views_available, posts_count),
                }
            )

        return {
            "status": "FAIL" if blockers else ("WARN" if warnings else "PASS"),
            "overview": {
                "canonical_posts": int(overview.get("canonical_posts") or 0),
                "unmapped_channel_posts": int(
                    overview.get("unmapped_channel_posts") or 0
                ),
            },
            "raw_metric_fields": raw_fields,
            "channels": channels_output,
            "unknown_channels": unknown,
            "numeric_format_diagnostics": parse_warnings,
            "warnings": warnings,
            "blockers": blockers,
            "metric_contract": {
                "interactions": (
                    "Instagram/YouTube=Likes+Comments; "
                    "Facebook/TikTok=Likes+Comments+Shares; "
                    "X=Likes+Replies+Retweets."
                ),
                "views": "Views always separate from interactions.",
            },
        }

    def _data_health(
        self,
        request: BuildRequest,
        posts: list[Mapping[str, Any]],
    ) -> dict[str, Any]:
        """Compute data health from already-fetched canonical social posts.

        This avoids relying on db.data_health(), because that diagnostic query can
        fail on some DB revisions due to ambiguous SQL aliases. Task 1 only needs
        health metadata for the exact post set used by this builder.
        """
        del request

        total_posts = len(posts)
        channels: dict[str, dict[str, Any]] = {}
        dates = []
        sentiment_classified = 0
        interaction_applicable = 0
        interaction_available = 0
        views_available = 0

        for post in posts:
            channel = _text(post.get("channel")) or "(unknown)"
            channel_norm = _text(post.get("channel_norm")) or "unknown"
            row = channels.setdefault(
                channel,
                {
                    "channel": channel,
                    "channel_type": channel_norm,
                    "posts": 0,
                    "sentiment_classified_posts": 0,
                    "interaction_applicable_posts": 0,
                    "interaction_available_posts": 0,
                    "views_available_posts": 0,
                },
            )
            row["posts"] += 1

            post_date = post.get("post_date") or post.get("date")
            if post_date:
                dates.append(str(post_date)[:10])

            sentiment = _text(post.get("sentiment")).casefold()
            if sentiment in SENTIMENTS:
                sentiment_classified += 1
                row["sentiment_classified_posts"] += 1

            if channel_norm in INTERACTION_CHANNELS:
                interaction_applicable += 1
                row["interaction_applicable_posts"] += 1
                if post.get("interactions_available"):
                    interaction_available += 1
                    row["interaction_available_posts"] += 1

            if post.get("views_available"):
                views_available += 1
                row["views_available_posts"] += 1

        channel_rows = []
        for row in sorted(
            channels.values(),
            key=lambda item: (-int(item["posts"]), item["channel"]),
        ):
            posts_count = int(row["posts"])
            applicable = int(row["interaction_applicable_posts"])
            available = int(row["interaction_available_posts"])
            channel_views = int(row["views_available_posts"])
            channel_sentiment = int(row["sentiment_classified_posts"])

            channel_rows.append(
                {
                    **row,
                    "coverage_percent": {
                        "sentiment_classified": _pct(channel_sentiment, posts_count),
                        "interactions_available_of_applicable": _pct(
                            available, applicable
                        ),
                        "views_available_of_posts": _pct(channel_views, posts_count),
                    },
                }
            )

        return {
            "n_posts_unique": total_posts,
            "n_rows_raw": total_posts,
            "duplicate_rows_removed": 0,
            "date_range_actual": {
                "from": min(dates) if dates else None,
                "to": max(dates) if dates else None,
            },
            "coverage_percent": {
                "sentiment_classified": _pct(sentiment_classified, total_posts),
                "interactions_available_of_applicable": _pct(
                    interaction_available, interaction_applicable
                ),
                "views_available_of_posts": _pct(views_available, total_posts),
            },
            "coverage_counts": {
                "sentiment_classified_posts": sentiment_classified,
                "interaction_applicable_posts": interaction_applicable,
                "interaction_available_posts": interaction_available,
                "views_available_posts": views_available,
            },
            "channels": channel_rows,
            "source": "computed_from_builder_canonical_posts",
        }


    def _metadata(
        self,
        purpose: str,
        topic_context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        output = {
            "purpose": purpose,
            "canonical_post_policy": "one canonical post per URL/id",
            "metric_contract": "interactions and views are separate",
        }
        if topic_context:
            output["topic_enrichment"] = {
                "taxonomy_version": topic_context.get("taxonomy_version"),
                "completion_coverage_pct": topic_context.get(
                    "completion_coverage_pct"
                ),
                "raw_topic_extraction_policy": "ignored",
            }
        return output

    def _add_kpi(
        self,
        package: dict[str, Any],
        posts: list[Mapping[str, Any]],
        enriched: Mapping[str, Any],
    ) -> None:
        applicable = sum(
            post["channel_norm"] in INTERACTION_CHANNELS for post in posts
        )
        available = sum(
            post["channel_norm"] in INTERACTION_CHANNELS
            and post["interactions_available"]
            for post in posts
        )
        topic_status = enriched.get("topic_status") or {}
        self.add_quantitative_view(
            package,
            view_id="qt_dsm_kpi_summary",
            rows=[
                {
                    "canonical_post_count": len(posts),
                    "unique_author_count": len(
                        {
                            _text(post.get("author")).casefold()
                            for post in posts
                            if _text(post.get("author"))
                        }
                    ),
                    "interactions": round(sum(_n(post["interactions"]) for post in posts), 2),
                    "views": round(sum(_n(post["views"]) for post in posts), 2),
                    "avg_interactions_per_applicable_post": round(
                        sum(_n(post["interactions"]) for post in posts) / applicable,
                        1,
                    )
                    if applicable
                    else None,
                    "interaction_coverage_pct": _pct(available, applicable),
                    "views_coverage_pct": _pct(
                        sum(post["views_available"] for post in posts), len(posts)
                    ),
                    "sentiment_coverage_pct": _pct(
                        sum(post["sentiment"] in SENTIMENTS for post in posts),
                        len(posts),
                    ),
                    "topic_completion_coverage_pct": topic_status.get(
                        "completion_coverage_pct"
                    ),
                    "topic_report_coverage_pct": topic_status.get(
                        "report_topic_coverage_pct"
                    ),
                }
            ],
            metadata=self._metadata("Daily KPI summary"),
        )

    def _add_sentiment_overall(
        self,
        package: dict[str, Any],
        posts: list[Mapping[str, Any]],
    ) -> None:
        classified = [post for post in posts if post["sentiment"] in SENTIMENTS]
        rows = []
        for sentiment in SENTIMENTS:
            items = [post for post in classified if post["sentiment"] == sentiment]
            rows.append(
                {
                    "sentiment": sentiment,
                    "post_count": len(items),
                    "share_of_classified_posts_pct": _pct(len(items), len(classified)),
                    "interactions": round(sum(_n(post["interactions"]) for post in items), 2),
                    "views": round(sum(_n(post["views"]) for post in items), 2),
                }
            )
        self.add_quantitative_view(
            package,
            view_id="qt_dsm_sentiment_distribution_overall",
            rows=rows,
            metadata=self._metadata("Overall sentiment distribution"),
        )

    def _add_sentiment_by_channel(
        self,
        package: dict[str, Any],
        posts: list[Mapping[str, Any]],
    ) -> None:
        groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for post in posts:
            groups[str(post["channel"])].append(post)

        rows = []
        for channel, items in sorted(groups.items()):
            classified = [post for post in items if post["sentiment"] in SENTIMENTS]
            row = {
                "channel": channel,
                "channel_type": items[0]["channel_norm"],
                "post_count": len(items),
                "interactions": round(sum(_n(post["interactions"]) for post in items), 2),
                "views": round(sum(_n(post["views"]) for post in items), 2),
                "sentiment_classified_posts": len(classified),
                "sentiment_coverage_pct": _pct(len(classified), len(items)),
            }
            for sentiment in SENTIMENTS:
                count = sum(post["sentiment"] == sentiment for post in classified)
                row[f"{sentiment}_posts"] = count
                row[f"{sentiment}_share_pct"] = _pct(count, len(classified))
            rows.append(row)

        self.add_quantitative_view(
            package,
            view_id="qt_dsm_sentiment_by_channel_table",
            rows=rows,
            metadata=self._metadata("Channel x sentiment"),
        )

    def _author_rows(self, posts: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
        groups: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
        for post in posts:
            author = _text(post.get("author"))
            if author:
                groups[(author, str(post["channel"]))].append(post)

        rows = []
        for (author, channel), items in groups.items():
            top = _rank(items, "interactions", "views")[0]
            applicable = sum(
                post["channel_norm"] in INTERACTION_CHANNELS for post in items
            )
            rows.append(
                {
                    "author": author,
                    "channel": channel,
                    "verified_account": top.get("verified_account"),
                    "post_count": len(items),
                    "total_interactions": round(sum(_n(post["interactions"]) for post in items), 2),
                    "total_views": round(sum(_n(post["views"]) for post in items), 2),
                    "avg_interactions_per_applicable_post": round(
                        sum(_n(post["interactions"]) for post in items) / applicable,
                        1,
                    )
                    if applicable
                    else None,
                    "positive_posts": sum(post["sentiment"] == "positive" for post in items),
                    "neutral_posts": sum(post["sentiment"] == "neutral" for post in items),
                    "negative_posts": sum(post["sentiment"] == "negative" for post in items),
                    "top_post_canonical_post_id": top["canonical_post_id"],
                    "top_post_url": top.get("url"),
                    "top_post_content_snippet": _snippet(top),
                }
            )
        rows = _rank(rows, "total_interactions", "total_views", "post_count")
        for rank, row in enumerate(rows, 1):
            row["rank"] = rank
        return rows

    def _add_authors(
        self,
        package: dict[str, Any],
        posts: list[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        rows = self._author_rows(posts)
        if not rows:
            self.mark_view_na(
                package,
                view_id="qt_dsm_top_authors_ranked",
                view_type="quantitative",
                reason="Tidak ada Author valid pada scope ini.",
            )
            self.mark_view_na(
                package,
                view_id="ql_dsm_top_engagement_account_profile",
                view_type="qualitative",
                reason="Tidak ada Author valid pada scope ini.",
            )
            return []

        self.add_quantitative_view(
            package,
            view_id="qt_dsm_top_authors_ranked",
            rows=rows[:50],
            metadata=self._metadata("Top authors by interactions"),
        )
        profiles = []
        for row in rows[:3]:
            profiles.append(
                {
                    "evidence_id": (
                        f"ql_dsm_top_engagement_account_profile:"
                        f"{row['author']}:{row['channel']}"
                    ),
                    **row,
                    "content_snippet": row["top_post_content_snippet"],
                    "source_url": row["top_post_url"],
                }
            )
        self.add_qualitative_view(
            package,
            view_id="ql_dsm_top_engagement_account_profile",
            rows=profiles,
            metadata=self._metadata("Top engagement account profiles"),
            evidence_reason="Top author representative content",
        )
        return rows

    def _add_top_content(
        self,
        package: dict[str, Any],
        posts: list[Mapping[str, Any]],
    ) -> None:
        rows = []
        for sentiment in ("positive", "negative"):
            candidates = [post for post in posts if post["sentiment"] == sentiment]
            for rank, post in enumerate(_rank(candidates, "interactions", "views")[:5], 1):
                assignment = post.get("topic_assignment")
                rows.append(
                    {
                        "evidence_id": (
                            f"ql_dsm_top_content_positive_negative:"
                            f"{sentiment}:{post['canonical_post_id']}"
                        ),
                        "rank_within_sentiment": rank,
                        "sentiment": sentiment,
                        "topic_id": assignment.get("primary_topic_id")
                        if isinstance(assignment, Mapping)
                        else None,
                        "topic_label": assignment.get("primary_topic_label")
                        if isinstance(assignment, Mapping)
                        else None,
                        "canonical_post_id": post["canonical_post_id"],
                        "channel": post["channel"],
                        "author": post.get("author"),
                        "verified_account": post.get("verified_account"),
                        "sentence_type_classification": post.get(
                            "sentence_type_classification"
                        ),
                        "content_snippet": _snippet(post),
                        "source_url": post.get("url"),
                        "interactions": _n(post["interactions"]),
                        "views": _n(post["views"]),
                    }
                )

        if not rows:
            self.mark_view_na(
                package,
                view_id="ql_dsm_top_content_positive_negative",
                view_type="qualitative",
                reason="Tidak ada post positive/negative pada scope ini.",
            )
            return

        self.add_qualitative_view(
            package,
            view_id="ql_dsm_top_content_positive_negative",
            rows=rows,
            metadata=self._metadata("Top positive and negative content"),
            evidence_reason="Top content by sentiment and interactions",
        )

    def _topic_context(
        self,
        posts: list[Mapping[str, Any]],
        enriched: Mapping[str, Any],
    ) -> dict[str, Any]:
        relevant = []
        for post in posts:
            assignment = post.get("topic_assignment")
            if (
                isinstance(assignment, Mapping)
                and assignment.get("classification_status") == "classified"
                and assignment.get("primary_topic_id") != "not_relevant"
            ):
                relevant.append(post)
        status = dict(enriched.get("topic_status") or {})
        taxonomy_version = (
            enriched["taxonomy"]["taxonomy_version"]
            if enriched.get("taxonomy")
            else None
        )
        evolution = extract_taxonomy_evolution_candidates(
            posts,
            taxonomy_version=taxonomy_version,
            assignment_field="topic_assignment",
        )
        return {
            "taxonomy_available": bool(enriched.get("taxonomy")),
            "taxonomy_version": taxonomy_version,
            "completion_coverage_pct": status.get("completion_coverage_pct"),
            "relevant_classified_posts": relevant,
            "taxonomy_evolution": evolution,
        }

    def _mark_topic_views_not_available(
        self,
        package: dict[str, Any],
        reason: str,
    ) -> None:
        for view_id, view_type in (
            ("qt_dsm_top_topics_ranked", "quantitative"),
            ("ql_dsm_topic_sentiment", "qualitative"),
            ("ql_dsm_topic_channels", "qualitative"),
        ):
            self.mark_view_not_available(
                package,
                view_id=view_id,
                view_type=view_type,
                reason=reason,
            )

    def _add_top_topics(
        self,
        package: dict[str, Any],
        context: Mapping[str, Any],
    ) -> None:
        groups: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
        for post in context["relevant_classified_posts"]:
            assignment = post["topic_assignment"]
            groups[
                (
                    assignment["primary_topic_id"],
                    assignment["primary_topic_label"],
                )
            ].append(post)

        rows = []
        for (topic_id, label), items in groups.items():
            row = {
                "topic_id": topic_id,
                "topic_label": label,
                "post_count": len(items),
                "interactions": round(sum(_n(post["interactions"]) for post in items), 2),
                "views": round(sum(_n(post["views"]) for post in items), 2),
            }
            for sentiment in SENTIMENTS:
                selected = [post for post in items if post["sentiment"] == sentiment]
                row[f"{sentiment}_posts"] = len(selected)
                row[f"{sentiment}_interactions"] = round(
                    sum(_n(post["interactions"]) for post in selected),
                    2,
                )
            rows.append(row)

        rows = _rank(rows, "interactions", "post_count", "views")
        for rank, row in enumerate(rows, 1):
            row["rank_overall"] = rank
        for sentiment in SENTIMENTS:
            ranked = _rank(rows, f"{sentiment}_interactions", f"{sentiment}_posts")
            for rank, row in enumerate(ranked, 1):
                row[f"rank_{sentiment}"] = rank

        self.add_quantitative_view(
            package,
            view_id="qt_dsm_top_topics_ranked",
            rows=rows,
            metadata=self._metadata("LLM report topics ranked by interactions", context),
        )

    def _add_topic_sentiment_evidence(
        self,
        package: dict[str, Any],
        context: Mapping[str, Any],
    ) -> None:
        grouped: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
        for post in context["relevant_classified_posts"]:
            if post["sentiment"] not in SENTIMENTS:
                continue
            topic = post["topic_assignment"]
            grouped[
                (
                    topic["primary_topic_id"],
                    topic["primary_topic_label"],
                    post["sentiment"],
                )
            ].append(post)

        rows = []
        for sentiment in SENTIMENTS:
            candidates = []
            for (topic_id, label, row_sentiment), items in grouped.items():
                if row_sentiment != sentiment:
                    continue
                top = _rank(items, "interactions", "views")[0]
                candidates.append(
                    {
                        "topic_id": topic_id,
                        "topic_label": label,
                        "sentiment": sentiment,
                        "topic_post_count": len(items),
                        "topic_interactions": round(
                            sum(_n(post["interactions"]) for post in items), 2
                        ),
                        "canonical_post_id": top["canonical_post_id"],
                        "channel": top["channel"],
                        "author": top.get("author"),
                        "verified_account": top.get("verified_account"),
                        "sentence_type_classification": top.get(
                            "sentence_type_classification"
                        ),
                        "content_snippet": _snippet(top),
                        "source_url": top.get("url"),
                        "interactions": _n(top["interactions"]),
                        "views": _n(top["views"]),
                    }
                )
            for rank, row in enumerate(
                _rank(candidates, "topic_interactions", "topic_post_count")[:5], 1
            ):
                row["rank_within_sentiment"] = rank
                row["evidence_id"] = (
                    f"ql_dsm_topic_sentiment:{sentiment}:{row['topic_id']}:"
                    f"{row['canonical_post_id']}"
                )
                rows.append(row)

        if not rows:
            self.mark_view_na(
                package,
                view_id="ql_dsm_topic_sentiment",
                view_type="qualitative",
                reason="Tidak ada evidence topic x sentiment yang valid.",
            )
            return
        self.add_qualitative_view(
            package,
            view_id="ql_dsm_topic_sentiment",
            rows=rows,
            metadata=self._metadata("Topic evidence by sentiment", context),
            evidence_reason="Top topic evidence per sentiment",
        )

    def _add_topic_channel_evidence(
        self,
        package: dict[str, Any],
        context: Mapping[str, Any],
    ) -> None:
        groups: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
        for post in context["relevant_classified_posts"]:
            topic = post["topic_assignment"]
            groups[
                (
                    post["channel"],
                    topic["primary_topic_id"],
                    topic["primary_topic_label"],
                )
            ].append(post)

        by_channel: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for (channel, topic_id, label), items in groups.items():
            top = _rank(items, "interactions", "views")[0]
            by_channel[channel].append(
                {
                    "channel": channel,
                    "topic_id": topic_id,
                    "topic_label": label,
                    "topic_post_count": len(items),
                    "topic_interactions": round(
                        sum(_n(post["interactions"]) for post in items),
                        2,
                    ),
                    "canonical_post_id": top["canonical_post_id"],
                    "author": top.get("author"),
                    "content_snippet": _snippet(top),
                    "source_url": top.get("url"),
                    "interactions": _n(top["interactions"]),
                    "views": _n(top["views"]),
                }
            )

        rows = []
        for channel, candidates in sorted(by_channel.items()):
            for rank, row in enumerate(
                _rank(candidates, "topic_interactions", "topic_post_count")[:2], 1
            ):
                row["rank_within_channel"] = rank
                row["evidence_id"] = (
                    f"ql_dsm_topic_channels:{channel}:{row['topic_id']}:"
                    f"{row['canonical_post_id']}"
                )
                rows.append(row)

        if not rows:
            self.mark_view_na(
                package,
                view_id="ql_dsm_topic_channels",
                view_type="qualitative",
                reason="Tidak ada evidence topic x channel yang valid.",
            )
            return
        self.add_qualitative_view(
            package,
            view_id="ql_dsm_topic_channels",
            rows=rows,
            metadata=self._metadata("Top two report topics per channel", context),
            evidence_reason="Topic x channel grounding",
        )


BUILDER_CLASS = DailySocialMediaReportBuilder

__all__ = ["DailySocialMediaReportBuilder", "BUILDER_CLASS"]
