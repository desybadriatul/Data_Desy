"""
Task 1 builder: Brand & Content Effectiveness (BCE) — VERSI 2.

Perubahan dari v1 (sejalan dengan industry_trend_report.py v3):
- Sumber data pindah dari db.fetch_posts_df ke get_enriched_scope_posts.
  Konsekuensinya builder ini kini punya:
    * `interactions` canonical (bukan Engagement mentah, bukan Views),
    * `verified_account` -> "Verified Account Content %" akhirnya bisa dihitung,
    * `topic_assignment` dari cache LLM -> 7 view yang butuh Topic bisa lengkap,
    * `sentence_type_classification` (dipakai kalau terisi).
- Builder HANYA MEMBACA cache topic. Tidak memanggil LLM, tidak pakai quota.
  Taxonomy & klasifikasi dibuat terpisah lewat Claude+MCP Cogan.
- Kalau taxonomy/cache belum ada -> kolom Topic diisi None + view yang benar-
  benar bergantung pada Topic ditandai N/A dengan alasan jelas.
- Aspect Based Sentiment / Entity / Mood tetap N/A (0% terisi; tim sepakat
  tidak dibangun enrichment-nya untuk MVP).

Raw `Topic Extraction` TIDAK dipakai sebagai report topic.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from reporting.contracts.report_input_contract_v1 import add_limitation
from reporting.enrichment.topic_batch_builder import (
    TopicBatchError,
    get_enriched_scope_posts,
)
from reporting.task1.base_builder import (
    BaseReportInputBuilder,
    BuildRequest,
    ReportBuildError,
)

TOP_CONTENT_LIMIT = 5
TOP_PER_SENTIMENT = 3


def _num(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _pct(part: int, whole: int) -> float | None:
    return round(100 * part / whole, 2) if whole else None


def _rank(posts: list[dict], limit: int | None = None) -> list[dict]:
    ranked = sorted(posts, key=lambda p: _num(p.get("interactions")), reverse=True)
    return ranked[:limit] if limit else ranked


def _is_verified(post: dict) -> bool:
    v = post.get("verified_account")
    if isinstance(v, bool):
        return v
    return str(v or "").strip().casefold() in {"true", "yes", "1", "verified"}


def _topic_label(post: dict) -> str | None:
    """Label report-topic dari cache LLM; None kalau belum terklasifikasi."""
    assignment = post.get("topic_assignment") or {}
    if assignment.get("classification_status") == "classified":
        return assignment.get("primary_topic_label")
    return None


class BrandContentEffectivenessBuilder(BaseReportInputBuilder):
    report_type_id = "brand_content_effectiveness"

    def build_views(self, report_input: dict[str, Any], request: BuildRequest) -> None:
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
                f"BCE tidak dapat membaca source/topic cache: {exc}"
            ) from exc

        posts: list[dict] = enriched["posts"]
        if not posts:
            self._mark_all_remaining_na(
                report_input, reason="Tidak ada canonical post pada scope ini."
            )
            return

        report_input["scope"]["raw_topic_extraction_policy"] = "not_used_as_report_topic"
        report_input["scope"]["topic_taxonomy_version"] = (
            enriched["taxonomy"]["taxonomy_version"] if enriched.get("taxonomy") else None
        )

        has_topic = bool(enriched.get("taxonomy")) and any(_topic_label(p) for p in posts)
        status = enriched.get("topic_status") or {}
        coverage = status.get("report_topic_coverage_pct")
        if has_topic and coverage is not None and coverage < 100:
            add_limitation(
                report_input,
                f"Topic coverage baru {coverage}% dari post topic-eligible. "
                "View berbasis topic bersifat sample, bukan seluruh data.",
            )

        total_c = len(posts)
        total_e = int(sum(_num(p.get("interactions")) for p in posts))

        self._add_exec_kpi(report_input, posts, request, total_c, total_e)
        self._add_sentiment_distribution(report_input, posts, total_c, total_e)
        self._add_channel_effectiveness(report_input, posts)
        self._add_top_performing_content(report_input, posts)
        self._add_evidence_views(report_input, posts, has_topic)
        self._add_topic_dependent_views(report_input, posts, has_topic)

        self._mark_all_remaining_na(
            report_input, reason="Belum diimplementasikan di builder ini."
        )

    # ------------------------------------------------------------------
    def _add_exec_kpi(self, report_input, posts, request, total_c, total_e) -> None:
        pos = sum(1 for p in posts if p.get("sentiment") == "positive")
        neg = sum(1 for p in posts if p.get("sentiment") == "negative")
        self._add_qt("qt_bce_exec_kpi_summary", report_input, [{
            "Campaign": request.project_name,
            "Total Mentions": total_c,
            "Total Engagement": total_e,
            "Avg Engagement per Post": round(total_e / total_c, 2) if total_c else None,
            "Positive Sentiment %": _pct(pos, total_c),
            "Negative Sentiment %": _pct(neg, total_c),
            "Potential Reach": None,
        }], metadata={"engagement_definition": "Interactions canonical (bukan Views)."})

    def _add_sentiment_distribution(self, report_input, posts, total_c, total_e) -> None:
        agg: dict[str, dict] = defaultdict(lambda: {"c": 0, "e": 0})
        for p in posts:
            s = p.get("sentiment") or "unclassified"
            agg[s]["c"] += 1
            agg[s]["e"] += int(_num(p.get("interactions")))
        self._add_qt("qt_bce_sentiment_distribution", report_input, [{
            "Sentiment": s,
            "Content Count": v["c"],
            "Content Share %": _pct(v["c"], total_c),
            "Total Engagement": v["e"],
            "Engagement Share %": _pct(v["e"], total_e),
        } for s, v in agg.items()])

    def _add_channel_effectiveness(self, report_input, posts) -> None:
        agg: dict[str, list] = defaultdict(list)
        for p in posts:
            agg[p.get("channel") or "(tidak diketahui)"].append(p)

        rows = []
        for ch, group in agg.items():
            c = len(group)
            e = int(sum(_num(p.get("interactions")) for p in group))
            rows.append({
                "Channel": ch,
                "Content Count": c,
                "Total Engagement": e,
                "Avg Engagement per Content": round(e / c, 2) if c else None,
                "Positive Sentiment %": _pct(
                    sum(1 for p in group if p.get("sentiment") == "positive"), c),
                "Negative Sentiment %": _pct(
                    sum(1 for p in group if p.get("sentiment") == "negative"), c),
                # Sekarang bisa dihitung: verified_account tersedia di canonical post.
                "Verified Account Content %": _pct(
                    sum(1 for p in group if _is_verified(p)), c),
            })
        self._add_qt("qt_bce_channel_effectiveness", report_input, rows)

    def _add_top_performing_content(self, report_input, posts) -> None:
        rows = []
        for p in _rank(posts, TOP_CONTENT_LIMIT):
            rows.append({
                "Author": p.get("author"),
                "Verified Account": p.get("verified_account"),
                "Channel": p.get("channel"),
                "Media Type": None,  # tidak tersedia pada canonical post
                "Title": p.get("title") or None,
                "Content": p.get("content"),
                "Topic Extraction": _topic_label(p),  # label LLM, bukan raw Sonar
                "Sentiment": p.get("sentiment"),
                "Engagement": int(_num(p.get("interactions"))),
                "Views": int(_num(p.get("views"))),
                "source_url": p.get("url"),
            })
        self._add_qt("qt_bce_top_performing_content", report_input, rows,
                     metadata={"note": "Topic Extraction = label report-topic LLM, "
                                       "bukan raw Sonar Topic Extraction."})

    def _add_evidence_views(self, report_input, posts, has_topic) -> None:
        # ql_bce_brand_content_summary (MINIMUM VIABLE) — selalu diisi.
        self._add_ql("ql_bce_brand_content_summary", report_input, [{
            "Title": p.get("title") or None,
            "Content": p.get("content"),
            "Sentiment": p.get("sentiment"),
            "Topic Extraction": _topic_label(p),
            "Sentence Type Classification": p.get("sentence_type_classification"),
            "Engagement": int(_num(p.get("interactions"))),
            "source_url": p.get("url"),
        } for p in _rank(posts, TOP_CONTENT_LIMIT)],
            "Contoh konten brand. Mood/Aspect/Entity tidak tersedia di data.")

        # ql_bce_top_content_sentiment (Top 3 per sentiment) — Aspect tetap N/A.
        by_sent: dict[str, list] = defaultdict(list)
        for p in posts:
            by_sent[p.get("sentiment") or "unclassified"].append(p)
        rows = []
        for sent, group in by_sent.items():
            for p in _rank(group, TOP_PER_SENTIMENT):
                rows.append({
                    "Sentiment": sent,
                    "Content": p.get("content"),
                    "Engagement": int(_num(p.get("interactions"))),
                    "Aspect Based Sentiment": None,  # 0% terisi; tidak dibangun
                    "source_url": p.get("url"),
                })
        self._add_ql("ql_bce_top_content_sentiment", report_input, rows,
                     "Top konten per sentimen. Aspect tidak tersedia di data.")

        # ql_bce_top_content_channel (Top 1 per channel) — kini lengkap dengan Topic.
        by_ch: dict[str, list] = defaultdict(list)
        for p in posts:
            by_ch[p.get("channel") or "(tidak diketahui)"].append(p)
        rows = []
        for ch, group in by_ch.items():
            top = _rank(group, 1)
            for p in top:
                rows.append({
                    "Channel": ch,
                    "Content": p.get("content"),
                    "Engagement": int(_num(p.get("interactions"))),
                    "Topic Extraction": _topic_label(p),
                    "source_url": p.get("url"),
                })
        self._add_ql("ql_bce_top_content_channel", report_input, rows,
                     "Top konten per channel.")

    def _add_topic_dependent_views(self, report_input, posts, has_topic) -> None:
        if not has_topic:
            reason = (
                "Belum ada cached LLM report-topic (status=classified) pada scope ini. "
                "Buat taxonomy & klasifikasi dulu lewat Claude+MCP Cogan."
            )
            add_limitation(report_input, reason)
            self._na(report_input, "ql_bce_top_content_patterns", "qualitative", reason)
        else:
            # ql_bce_top_content_patterns: pola konten teratas per topic.
            classified = [p for p in posts if _topic_label(p)]
            rows = []
            seen: set[str] = set()
            for p in _rank(classified):
                label = _topic_label(p)
                if label in seen:
                    continue
                seen.add(label)
                rows.append({
                    "Title": p.get("title") or None,
                    "Content": p.get("content"),
                    "Topic Extraction": label,
                    "Sentence Type Classification": p.get("sentence_type_classification"),
                    "Media Type": None,
                    "Author": p.get("author"),
                    "Channel": p.get("channel"),
                    "Engagement": int(_num(p.get("interactions"))),
                    "source_url": p.get("url"),
                })
                if len(rows) >= TOP_CONTENT_LIMIT:
                    break
            self._add_ql("ql_bce_top_content_patterns", report_input, rows,
                         "Pola konten teratas per report-topic. Entity/Noun tidak tersedia.")

        # View yang bergantung Media Type / Aspect / Entity -> tetap N/A.
        self._na(report_input, "qt_bce_format_theme_effectiveness", "quantitative",
                 "Media Type tidak tersedia pada canonical post.")
        self._na(report_input, "ql_bce_top_content_by_media_type", "qualitative",
                 "Media Type tidak tersedia pada canonical post.")
        self._na(report_input, "ql_bce_recommendation_inputs", "qualitative",
                 "Butuh Aspect/Mood/Generic Sentiment/Entity yang 0% terisi di data.")

    # ------------------------------------------------------------------
    def _add_qt(self, view_id, report_input, rows, metadata=None):
        if view_id in self.quantitative_view_ids:
            self.add_quantitative_view(report_input, view_id=view_id, rows=rows,
                                       metadata=metadata)

    def _add_ql(self, view_id, report_input, rows, reason=None):
        if view_id in self.qualitative_view_ids:
            self.add_qualitative_view(report_input, view_id=view_id, rows=rows,
                                      evidence_reason=reason)

    def _na(self, report_input, view_id, view_type, reason):
        allowed = (self.quantitative_view_ids if view_type == "quantitative"
                   else self.qualitative_view_ids)
        present = report_input[
            "quantitative_views" if view_type == "quantitative" else "qualitative_views"
        ]
        if view_id in allowed and view_id not in present:
            self.mark_view_na(report_input, view_id=view_id,
                              view_type=view_type, reason=reason)

    def _mark_all_remaining_na(self, report_input, *, reason):
        for v in self.quantitative_view_ids:
            self._na(report_input, v, "quantitative", reason)
        for v in self.qualitative_view_ids:
            self._na(report_input, v, "qualitative", reason)


BUILDER_CLASS = BrandContentEffectivenessBuilder

__all__ = ["BrandContentEffectivenessBuilder", "BUILDER_CLASS"]
