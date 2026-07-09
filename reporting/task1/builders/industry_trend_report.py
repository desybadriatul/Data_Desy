"""
Task 1 builder: Industry Trend Report (VERSI 3 — topic-enrichment aware).

Perubahan besar dari v2:
- Sumber data pindah dari db.fetch_posts_df ke
  reporting.enrichment.topic_batch_builder.get_enriched_scope_posts, mengikuti
  pola daily_social_media_report.py milik Fuji.
- Konsekuensinya builder ini kini punya:
    * `interactions` canonical (tidak perlu lagi menebak Engagement vs Views),
    * `topic_assignment` dari cache LLM  -> view topic bisa TERISI,
    * `topic_status` (coverage %) -> dilaporkan sebagai limitation yang jujur.
- Builder HANYA MEMBACA cache topic. Tidak memanggil LLM, tidak memakai quota.
  Taxonomy & klasifikasi dibuat terpisah lewat Claude+MCP Cogan.
- Kalau taxonomy belum ada / belum ada post classified -> view topic ditandai
  N/A dengan alasan jelas (pola sama seperti builder Fuji).

Catatan: raw `Topic Extraction` TIDAK dipakai sebagai report topic.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from database import db
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

TOP_TOPIC_LIMIT = 10
TOP_CONTENT_LIMIT = 5


def _num(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _rank_posts(posts: list[dict], limit: int | None = None) -> list[dict]:
    ranked = sorted(posts, key=lambda p: _num(p.get("interactions")), reverse=True)
    return ranked[:limit] if limit else ranked


class IndustryTrendReportBuilder(BaseReportInputBuilder):
    report_type_id = "industry_trend"

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
                f"Industry Trend tidak dapat membaca source/topic cache: {exc}"
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

        # ---------- VIEW NON-TOPIC (selalu bisa dari canonical data) ----------
        self._add_total_metrics(report_input, posts, request)
        self._add_qt("qt_it_channel_volume_engagement", report_input,
                     self._group(posts, "channel"))
        self._add_qt("qt_it_sentiment_overall", report_input,
                     self._group(posts, "sentiment"))
        self._add_qt("qt_it_sentiment_trend", report_input,
                     self._sentiment_trend(posts))
        self._add_brand_sov_soe(report_input, request)

        self._add_ql("ql_it_key_events_context", report_input,
                     self._evidence(posts, ["post_date"]),
                     "Top konten by interactions.")
        self._add_ql("ql_it_channel_behavior_insight", report_input,
                     self._evidence(posts, ["channel"]),
                     "Contoh perilaku konten per channel.")
        self._add_ql("ql_it_authority_mentions", report_input,
                     self._evidence(posts, ["author", "verified_account", "channel"]),
                     "Top author by interactions.")

        # ---------- VIEW TOPIC (dari cache LLM) ----------
        self._add_topic_views(report_input, posts, enriched)

        # ---------- N/A jujur: field yang 0% terisi di data ----------
        self._na(report_input, "qt_it_content_type_distribution", "quantitative",
                 "Media Type tidak tersedia pada canonical post.")
        self._na(report_input, "qt_it_channel_role_classification", "quantitative",
                 "Media Type tidak tersedia pada canonical post.")
        self._na(report_input, "qt_it_key_sentiment_drivers", "quantitative",
                 "Aspect Based Sentiment 0% terisi; butuh aspect enrichment.")
        self._na(report_input, "ql_it_sentiment_driver_narratives", "qualitative",
                 "Aspect Based Sentiment 0% terisi; butuh aspect enrichment.")
        self._na(report_input, "ql_it_audience_tone_indicators", "qualitative",
                 "Mood 0% terisi di data.")
        self._na(report_input, "ql_it_complaint_praise_classification", "qualitative",
                 "Sentence Type Classification 0% terisi di data.")

        self._mark_all_remaining_na(
            report_input, reason="Belum diimplementasikan di builder ini."
        )

    # ------------------------------------------------------------------
    #  Topic views (inti perubahan v3)
    # ------------------------------------------------------------------
    def _add_topic_views(self, report_input, posts, enriched) -> None:
        status = enriched.get("topic_status") or {}

        if not enriched.get("taxonomy"):
            self._na_topics(report_input,
                            "Taxonomy LLM report-topic belum tersedia untuk project ini. "
                            "Buat taxonomy dulu lewat Claude+MCP Cogan.")
            return

        classified = [
            p for p in posts
            if (p.get("topic_assignment") or {}).get("classification_status") == "classified"
        ]
        if not classified:
            self._na_topics(report_input,
                            "Belum ada cached LLM report-topic status=classified pada scope ini.")
            return

        # Coverage jujur: laporkan berapa % post yang benar-benar punya topic.
        coverage = status.get("report_topic_coverage_pct")
        if coverage is not None and coverage < 100:
            add_limitation(
                report_input,
                f"Topic coverage baru {coverage}% dari post topic-eligible. "
                "Analisis topic berbasis sample, bukan seluruh data.",
            )

        # qt_it_topic_volume_engagement (Top 10 by interactions)
        agg: dict[str, dict] = defaultdict(
            lambda: {"Count of Content": 0, "Engagement": 0}
        )
        for p in classified:
            label = p["topic_assignment"]["primary_topic_label"]
            agg[label]["Count of Content"] += 1
            agg[label]["Engagement"] += int(_num(p.get("interactions")))
        rows = [{"Topic Extraction": k, **v} for k, v in agg.items()]
        rows.sort(key=lambda r: r["Engagement"], reverse=True)
        self._add_qt("qt_it_topic_volume_engagement", report_input,
                     rows[:TOP_TOPIC_LIMIT],
                     metadata={"topic_coverage_pct": coverage,
                               "taxonomy_version": enriched["taxonomy"]["taxonomy_version"]})

        # qt_it_sentiment_by_topic (Topic x Sentiment)
        cross: dict[tuple, int] = defaultdict(int)
        for p in classified:
            label = p["topic_assignment"]["primary_topic_label"]
            cross[(label, p.get("sentiment") or "unclassified")] += 1
        self._add_qt("qt_it_sentiment_by_topic", report_input,
                     [{"Topic Extraction": t, "Sentiment": s, "Count of Content": c}
                      for (t, s), c in cross.items()])

        # ql_it_topic_examples (contoh nyata per topic, top by interactions)
        examples = []
        seen: set[str] = set()
        for p in _rank_posts(classified):
            label = p["topic_assignment"]["primary_topic_label"]
            if label in seen:
                continue
            seen.add(label)
            examples.append({
                "Topic Extraction": label,
                "Content": p.get("content"),
                "Author": p.get("author"),
                "Channel": p.get("channel"),
                "Sentiment": p.get("sentiment"),
                "Engagement": int(_num(p.get("interactions"))),
                "source_url": p.get("url"),
            })
            if len(examples) >= TOP_CONTENT_LIMIT:
                break
        self._add_ql("ql_it_topic_examples", report_input, examples,
                     "Contoh konten per report-topic (dari cache LLM).")

    def _na_topics(self, report_input, reason: str) -> None:
        add_limitation(report_input, reason)
        for vid, vtype in (
            ("qt_it_topic_volume_engagement", "quantitative"),
            ("qt_it_sentiment_by_topic", "quantitative"),
            ("ql_it_topic_examples", "qualitative"),
        ):
            self._na(report_input, vid, vtype, reason)

    # ------------------------------------------------------------------
    #  View non-topic
    # ------------------------------------------------------------------
    def _add_total_metrics(self, report_input, posts, request) -> None:
        ad_value = None
        try:
            rows = db.metrics_breakdown(
                campaign_name=request.project_name,
                start_date=request.start_date,
                end_date=request.end_date,
            ) or []
            total = sum(_num(r.get("ad_value")) for r in rows)
            ad_value = int(total) if total > 0 else None
        except Exception:
            pass

        self._add_qt("qt_it_total_metrics_summary", report_input, [{
            "Count of Content": len(posts),
            "Engagement": int(sum(_num(p.get("interactions")) for p in posts)),
            "Potential Reach": None,
            "Ad Value": ad_value,
        }], metadata={"engagement_definition": "Interactions canonical (bukan Views).",
                      "ad_value_note": "Coverage Ad Value rendah; angka bisa understated."})

    def _group(self, posts: list[dict], key: str) -> list[dict]:
        agg: dict[str, dict] = defaultdict(
            lambda: {"Count of Content": 0, "Engagement": 0}
        )
        for p in posts:
            k = p.get(key) or "(tidak diketahui)"
            agg[k]["Count of Content"] += 1
            agg[k]["Engagement"] += int(_num(p.get("interactions")))
        col = "Channel" if key == "channel" else "Sentiment"
        return [{col: k, **v} for k, v in agg.items()]

    def _sentiment_trend(self, posts: list[dict]) -> list[dict]:
        agg: dict[tuple, int] = defaultdict(int)
        for p in posts:
            day = str(p.get("post_date") or "")[:10] or None
            agg[(day, p.get("sentiment") or "unclassified")] += 1
        return [{"Date": d, "Sentiment": s, "Count of Content": c}
                for (d, s), c in agg.items()]

    def _evidence(self, posts: list[dict], extra: list[str]) -> list[dict]:
        rows = []
        for p in _rank_posts(posts, TOP_CONTENT_LIMIT):
            row = {
                "Content": p.get("content"),
                "Engagement": int(_num(p.get("interactions"))),
                "source_url": p.get("url"),
            }
            for f in extra:
                col = {"post_date": "Date", "author": "Author",
                       "channel": "Channel",
                       "verified_account": "Verified Account"}.get(f, f)
                row[col] = p.get(f)
            rows.append(row)
        return rows

    def _add_brand_sov_soe(self, report_input, request) -> None:
        brands = [b for b in ([request.client_brand] + list(request.competitor_brands)) if b]
        if len(brands) < 2:
            self._na(report_input, "qt_it_brand_sov_soe", "quantitative",
                     "Brand universe belum ditentukan (butuh client_brand + minimal 1 competitor).")
            return

        rows, tot_c, tot_e = [], 0, 0
        try:
            for b in brands:
                data = get_enriched_scope_posts(
                    project_name=b,
                    start_date=request.start_date,
                    end_date=request.end_date,
                )
                bp = data["posts"]
                c = len(bp)
                e = int(sum(_num(p.get("interactions")) for p in bp))
                rows.append({"Campaign": b, "Count of Content": c, "Engagement": e})
                tot_c += c
                tot_e += e
        except TopicBatchError:
            self._na(report_input, "qt_it_brand_sov_soe", "quantitative",
                     "Sebagian brand pembanding tidak ada di database.")
            return

        for r in rows:
            r["Share of Voice (%)"] = round(100 * r["Count of Content"] / tot_c, 2) if tot_c else None
            r["Share of Engagement (%)"] = round(100 * r["Engagement"] / tot_e, 2) if tot_e else None
        self._add_qt("qt_it_brand_sov_soe", report_input, rows,
                     metadata={"brand_universe": brands})

    # ------------------------------------------------------------------
    #  Helper wrapper
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


BUILDER_CLASS = IndustryTrendReportBuilder

__all__ = ["IndustryTrendReportBuilder", "BUILDER_CLASS"]
