"""
Task 1 builder: Brand & Content Effectiveness (BCE).

Pola sama persis dengan industry_trend_report.py. Engagement = Interactions
canonical (bukan Engagement mentah, bukan Views). View yang butuh field
enrichment kosong (Topic, Aspect, Mood, Sentence Type, Entity, Noun, Generic
Sentiment) ditandai N/A. Media Type coverage rendah -> N/A kecuali diekspos.
Verified Account ada di data (~100%) tapi belum diekspos ke fetch_posts_df,
jadi sub-metrik "Verified %" diisi None + catatan.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from database import db
from reporting.task1.base_builder import BaseReportInputBuilder, BuildRequest

ENGAGEMENT_COLUMN = "Interactions"
ENGAGEMENT_NOTE = (
    "Engagement = Interactions canonical per db.py (bukan Engagement mentah, "
    "bukan Views)."
)


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(0)


def _pct(part: int, whole: int) -> float | None:
    return round(100 * part / whole, 2) if whole else None


class BrandContentEffectivenessBuilder(BaseReportInputBuilder):
    report_type_id = "brand_content_effectiveness"

    def build_views(self, report_input: dict[str, Any], request: BuildRequest) -> None:
        df = db.fetch_posts_df(
            campaign_name=request.project_name,
            start_date=request.start_date,
            end_date=request.end_date,
            channels=list(request.channels) or None,
        )
        if df is None or df.empty:
            self._mark_all_remaining_na(report_input, reason="Tidak ada data pada project/periode ini.")
            return

        df = df.assign(_eng=_num(df.get(ENGAGEMENT_COLUMN, pd.Series(dtype=float))))
        total_c = len(df)
        total_e = int(df["_eng"].sum())
        sent = df.get("Sentiment", pd.Series(dtype=object)).astype(str).str.lower()

        # qt_bce_exec_kpi_summary (grain: Campaign) -> 1 baris untuk project ini
        self._add_qt(report_input, "qt_bce_exec_kpi_summary", [{
            "Campaign": request.project_name,
            "Total Mentions": total_c,
            "Total Engagement": total_e,
            "Avg Engagement per Post": round(total_e / total_c, 2) if total_c else None,
            "Positive Sentiment %": _pct(int((sent == "positive").sum()), total_c),
            "Negative Sentiment %": _pct(int((sent == "negative").sum()), total_c),
            "Potential Reach": int(_num(df.get("Potential Reach", pd.Series(dtype=float))).sum()),
        }], metadata={"engagement_definition": ENGAGEMENT_NOTE})

        # qt_bce_sentiment_distribution (grain: Sentiment)
        rows = []
        for key, g in df.groupby("Sentiment", dropna=False):
            c = len(g); e = int(g["_eng"].sum())
            rows.append({
                "Sentiment": None if pd.isna(key) else key,
                "Content Count": c,
                "Content Share %": _pct(c, total_c),
                "Total Engagement": e,
                "Engagement Share %": _pct(e, total_e),
            })
        self._add_qt(report_input, "qt_bce_sentiment_distribution", rows)

        # qt_bce_channel_effectiveness (grain: Channel) - Verified % belum tersedia
        rows = []
        for key, g in df.groupby("Channel", dropna=False):
            c = len(g); e = int(g["_eng"].sum())
            gs = g.get("Sentiment", pd.Series(dtype=object)).astype(str).str.lower()
            rows.append({
                "Channel": None if pd.isna(key) else key,
                "Content Count": c,
                "Total Engagement": e,
                "Avg Engagement per Content": round(e / c, 2) if c else None,
                "Positive Sentiment %": _pct(int((gs == "positive").sum()), c),
                "Negative Sentiment %": _pct(int((gs == "negative").sum()), c),
                "Verified Account Content %": None,  # butuh Verified Account diekspos ke fetch_posts_df
            })
        self._add_qt(report_input, "qt_bce_channel_effectiveness", rows,
                     metadata={"note": "Verified Account % belum tersedia (kolom belum diekspos ke fetch_posts_df)."})

        # qt_bce_top_performing_content (Top 5 by engagement) - field enrichment yang ada saja
        self._add_qt(report_input, "qt_bce_top_performing_content",
                     self._top_rows(df, 5, ["Channel", "Title", "Content", "Sentiment",
                                            "Likes", "Comments", "Shares", "Retweets",
                                            "Views", "Link URL"]))

        # ql_bce_brand_content_summary (MIN VIABLE) - pakai Title/Content/Sentiment nyata
        self._add_ql(report_input, "ql_bce_brand_content_summary",
                     self._top_rows(df, 5, ["Title", "Content", "Sentiment", "Link URL"]),
                     reason="Contoh konten brand (enrichment signals belum tersedia).")

        # ql_bce_top_content_sentiment (Top 3 per sentiment) - Aspect kosong -> diabaikan
        rows = []
        for key, g in df.groupby("Sentiment", dropna=False):
            for _, r in g.sort_values("_eng", ascending=False).head(3).iterrows():
                rows.append({
                    "Sentiment": None if pd.isna(key) else key,
                    "Content": r.get("Content"),
                    "Engagement": int(r["_eng"]),
                    "source_url": r.get("Link URL"),
                })
        self._add_ql(report_input, "ql_bce_top_content_sentiment", rows,
                     reason="Top konten per sentimen.")

        # ql_bce_top_content_channel (Top 1 per channel) - Topic kosong -> diabaikan
        rows = []
        for key, g in df.groupby("Channel", dropna=False):
            top = g.sort_values("_eng", ascending=False).head(1)
            for _, r in top.iterrows():
                rows.append({
                    "Channel": None if pd.isna(key) else key,
                    "Content": r.get("Content"),
                    "Engagement": int(r["_eng"]),
                    "source_url": r.get("Link URL"),
                })
        self._add_ql(report_input, "ql_bce_top_content_channel", rows,
                     reason="Top konten per channel.")

        # ---- N/A jujur (butuh enrichment / field kosong) ----
        self._na(report_input, "qt_bce_format_theme_effectiveness", "quantitative",
                 "Butuh Media Type (coverage ~10%) x Topic (0% terisi, perlu enrichment).")
        self._na(report_input, "ql_bce_top_content_patterns", "qualitative",
                 "Butuh Topic/Entity/Noun/Sentence Type yang 0% terisi.")
        self._na(report_input, "ql_bce_recommendation_inputs", "qualitative",
                 "Butuh Aspect/Topic/Mood/Generic Sentiment yang 0% terisi.")
        self._na(report_input, "ql_bce_top_content_by_media_type", "qualitative",
                 "Media Type coverage sangat rendah (~10%).")

        self._mark_all_remaining_na(report_input, reason="Belum diimplementasikan di builder ini.")

    # --- helper (identik dengan Industry Trend) ---
    def _top_rows(self, df: pd.DataFrame, n: int, cols: list[str]) -> list[dict]:
        d = df.sort_values("_eng", ascending=False).head(n)
        out = []
        for _, r in d.iterrows():
            row = {"Engagement": int(r["_eng"])}
            for c in cols:
                row[c] = None if (c not in d.columns or pd.isna(r.get(c))) else r.get(c)
            if row.get("Link URL"):
                row["source_url"] = row["Link URL"]
            out.append(row)
        return out

    def _add_qt(self, report_input, view_id, rows, metadata=None):
        if view_id in self.quantitative_view_ids:
            self.add_quantitative_view(report_input, view_id=view_id, rows=rows, metadata=metadata)

    def _add_ql(self, report_input, view_id, rows, reason=None):
        if view_id in self.qualitative_view_ids:
            self.add_qualitative_view(report_input, view_id=view_id, rows=rows, evidence_reason=reason)

    def _na(self, report_input, view_id, view_type, reason):
        allowed = self.quantitative_view_ids if view_type == "quantitative" else self.qualitative_view_ids
        present = report_input["quantitative_views" if view_type == "quantitative" else "qualitative_views"]
        if view_id in allowed and view_id not in present:
            self.mark_view_na(report_input, view_id=view_id, view_type=view_type, reason=reason)

    def _mark_all_remaining_na(self, report_input, *, reason):
        for v in self.quantitative_view_ids:
            self._na(report_input, v, "quantitative", reason)
        for v in self.qualitative_view_ids:
            self._na(report_input, v, "qualitative", reason)


BUILDER_CLASS = BrandContentEffectivenessBuilder
