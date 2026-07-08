"""
Task 1 builder: Industry Trend Report  (VERSI 2 — berbasis data nyata)

Perubahan dari v1, setelah cek data mentah AQUA & Nestle PureLife asli:
- Engagement  -> pakai "Interactions" canonical dari db.fetch_posts_df
                 (BUKAN kolom Engagement mentah, BUKAN Views). Definisi ini
                 dicatat di metadata tiap view agar tidak ketukar.
- Ad Value    -> diambil dari db.metrics_breakdown (kolom ad_value). Coverage
                 di data nyata cuma ~10%, jadi disertai catatan coverage.
- Author      -> view authority_mentions diisi dari db.top_authors().
- SOV/SOE     -> dihitung HANYA jika client_brand + competitor_brands diberikan
                 di request (sesuai aturan: universe brand tidak boleh diambil
                 otomatis dari semua campaign). Kalau tidak ada -> N/A.
- N/A jujur   -> Mood, Sentence Type, Aspect, Topic = 0% terisi di data nyata,
                 jadi tetap N/A. Topic & Aspect menunggu pipeline enrichment.
- Media Type  -> hanya 8-14% terisi; diisi HANYA kalau fetch_posts_df sudah
                 mengekspos kolomnya, dengan catatan coverage. Kalau belum
                 diekspos -> N/A dengan alasan jelas (minta Fuji menambahkannya).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pandas as pd

from database import db
from reporting.task1.base_builder import BaseReportInputBuilder, BuildRequest


def _safe(v):
    """Ubah tipe DB (Decimal/Timestamp/numpy) jadi tipe Python biasa supaya JSON-safe."""
    if isinstance(v, Decimal):
        return int(v) if v == v.to_integral_value() else float(v)
    if hasattr(v, "isoformat"):  # datetime / pandas Timestamp / date
        try:
            return v.isoformat()
        except Exception:
            return str(v)
    if hasattr(v, "item"):  # numpy scalar
        try:
            return v.item()
        except Exception:
            return v
    return v


# "Engagement" (istilah registry) == kolom "Interactions" canonical di db.py
ENGAGEMENT_COLUMN = "Interactions"
ENGAGEMENT_NOTE = (
    "Engagement = Interactions canonical per db.py (bukan Engagement mentah, "
    "bukan Views)."
)


def _num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0)


class IndustryTrendReportBuilder(BaseReportInputBuilder):
    report_type_id = "industry_trend"

    def build_views(
        self,
        report_input: dict[str, Any],
        request: BuildRequest,
    ) -> None:
        df = db.fetch_posts_df(
            campaign_name=request.project_name,
            start_date=request.start_date,
            end_date=request.end_date,
            channels=list(request.channels) or None,
        )

        if df is None or df.empty:
            self._mark_all_remaining_na(
                report_input,
                reason="Tidak ada data pada project/periode ini.",
            )
            return

        df = df.assign(_eng=_num(df.get(ENGAGEMENT_COLUMN, pd.Series(dtype=float))))

        # ---------- VIEW NYATA ----------
        self._view_total_metrics(report_input, df, request)
        self._add_qt(report_input, "qt_it_channel_volume_engagement",
                     self._group(df, "Channel"))
        self._add_qt(report_input, "qt_it_sentiment_overall",
                     self._group(df, "Sentiment"))
        self._add_qt(report_input, "qt_it_sentiment_trend",
                     self._sentiment_trend(df))

        self._add_ql(report_input, "ql_it_key_events_context",
                     self._top_content(df, 5, ["Content", "Date", "Link URL"]),
                     reason="Top konten by engagement.")
        self._add_ql(report_input, "ql_it_channel_behavior_insight",
                     self._top_content(df, 5, ["Channel", "Content", "Link URL"]),
                     reason="Contoh perilaku konten per channel.")

        self._view_authority_mentions(report_input, request)
        self._view_media_type(report_input, df)          # isi kalau ada, else N/A
        self._view_brand_sov_soe(report_input, request)  # isi kalau brand ada

        # ---------- N/A JUJUR (0% terisi / butuh enrichment) ----------
        self._na(report_input, "qt_it_topic_volume_engagement", "quantitative",
                 "Topic Extraction 0% terisi; butuh pipeline topic enrichment.")
        self._na(report_input, "qt_it_sentiment_by_topic", "quantitative",
                 "Topic Extraction 0% terisi; butuh pipeline topic enrichment.")
        self._na(report_input, "qt_it_key_sentiment_drivers", "quantitative",
                 "Aspect Based Sentiment 0% terisi; butuh aspect enrichment.")
        self._na(report_input, "qt_it_channel_role_classification", "quantitative",
                 "Bergantung Media Type yang coverage-nya sangat rendah.")
        self._na(report_input, "ql_it_topic_examples", "qualitative",
                 "Topic Extraction 0% terisi; butuh pipeline topic enrichment.")
        self._na(report_input, "ql_it_sentiment_driver_narratives", "qualitative",
                 "Aspect Based Sentiment 0% terisi; butuh aspect enrichment.")
        self._na(report_input, "ql_it_audience_tone_indicators", "qualitative",
                 "Mood 0% terisi di data.")
        self._na(report_input, "ql_it_complaint_praise_classification", "qualitative",
                 "Sentence Type Classification 0% terisi di data.")

        # jaring pengaman: view registry lain yang belum tersentuh -> N/A
        self._mark_all_remaining_na(
            report_input,
            reason="Belum diimplementasikan di builder ini.",
        )

    # ------------------------------------------------------------------
    #  View yang butuh logika sendiri
    # ------------------------------------------------------------------
    def _view_total_metrics(self, report_input, df, request) -> None:
        ad_value, ad_cov = self._ad_value_total(request)
        self.add_quantitative_view(
            report_input,
            view_id="qt_it_total_metrics_summary",
            rows=[{
                "Count of Content": int(len(df)),
                "Engagement": int(df["_eng"].sum()),
                "Potential Reach": int(_num(df.get("Potential Reach", pd.Series(dtype=float))).sum()),
                "Ad Value": ad_value,
            }],
            metadata={
                "engagement_definition": ENGAGEMENT_NOTE,
                "ad_value_coverage_note": ad_cov,
            },
        )

    def _ad_value_total(self, request):
        """Ad Value total dari metrics_breakdown; coverage rendah -> beri catatan."""
        try:
            rows = db.metrics_breakdown(
                campaign_name=request.project_name,
                start_date=request.start_date,
                end_date=request.end_date,
            ) or []
            total = sum(float(r.get("ad_value") or 0) for r in rows)
            if total <= 0:
                return None, "Ad Value 0/again kosong di periode ini."
            return int(total), "Coverage Ad Value di data historis ~10%; angka ini bisa understated."
        except Exception:
            return None, "Ad Value tidak dapat dihitung."

    def _view_authority_mentions(self, report_input, request) -> None:
        try:
            authors = db.top_authors(
                campaign_name=request.project_name,
                start_date=request.start_date,
                end_date=request.end_date,
                limit=5,
            ) or []
        except Exception:
            authors = []

        if not authors:
            self._na(report_input, "ql_it_authority_mentions", "qualitative",
                     "Tidak ada author dengan engagement pada periode ini.")
            return

        rows = []
        for a in authors:
            top_post = a.get("top_post") or {}
            rows.append({
                "Author": a.get("author"),
                "Engagement": int(a.get("total_interactions") or 0),
                "Channel": a.get("channel"),
                "Content": top_post.get("content"),
                "source_url": top_post.get("url"),
            })
        self._add_ql(report_input, "ql_it_authority_mentions", rows,
                     reason="Top author by interactions.")

    def _view_media_type(self, report_input, df) -> None:
        # Media Type ada di raw tapi coverage rendah; hanya bisa dipakai kalau
        # fetch_posts_df sudah mengeksposnya sebagai kolom.
        if "Media Type" not in df.columns:
            self._na(report_input, "qt_it_content_type_distribution", "quantitative",
                     "Media Type belum diekspos ke fetch_posts_df (ada di raw, "
                     "coverage ~10%). Minta Fuji menambahkan kolomnya.")
            return
        sub = df[df["Media Type"].astype(str).str.strip().replace("nan", "") != ""]
        if sub.empty:
            self._na(report_input, "qt_it_content_type_distribution", "quantitative",
                     "Media Type kosong pada periode ini.")
            return
        coverage = round(100 * len(sub) / len(df))
        self.add_quantitative_view(
            report_input,
            view_id="qt_it_content_type_distribution",
            rows=self._group(sub.assign(_eng=sub["_eng"]), "Media Type"),
            metadata={"coverage_note": f"Hanya {coverage}% konten punya Media Type."},
        )

    def _view_brand_sov_soe(self, report_input, request) -> None:
        brands = []
        if request.client_brand:
            brands.append(request.client_brand)
        brands.extend(list(request.competitor_brands))
        brands = [b for b in brands if b]

        if len(brands) < 2:
            self._na(report_input, "qt_it_brand_sov_soe", "quantitative",
                     "Brand universe belum ditentukan (butuh client_brand + "
                     "minimal 1 competitor di request).")
            return

        rows, total_c, total_e = [], 0, 0
        try:
            for b in brands:
                bdf = db.fetch_posts_df(
                    campaign_name=b,
                    start_date=request.start_date,
                    end_date=request.end_date,
                )
                c = 0 if bdf is None else len(bdf)
                e = 0 if bdf is None else int(_num(bdf.get(ENGAGEMENT_COLUMN, pd.Series(dtype=float))).sum())
                rows.append({"Campaign": b, "Count of Content": c, "Engagement": e})
                total_c += c
                total_e += e
        except Exception:
            self._na(report_input, "qt_it_brand_sov_soe", "quantitative",
                     "Sebagian brand pembanding tidak ada di database.")
            return

        for r in rows:
            r["Share of Voice (%)"] = round(100 * r["Count of Content"] / total_c, 2) if total_c else None
            r["Share of Engagement (%)"] = round(100 * r["Engagement"] / total_e, 2) if total_e else None
        self.add_quantitative_view(
            report_input, view_id="qt_it_brand_sov_soe", rows=rows,
            metadata={"engagement_definition": ENGAGEMENT_NOTE,
                      "brand_universe": brands},
        )

    # ------------------------------------------------------------------
    #  Helper umum
    # ------------------------------------------------------------------
    def _group(self, df: pd.DataFrame, col: str) -> list[dict]:
        if col not in df.columns:
            return []
        out = []
        for key, g in df.groupby(col, dropna=False):
            out.append({
                col: (None if pd.isna(key) else key),
                "Count of Content": int(len(g)),
                "Engagement": int(g["_eng"].sum()),
            })
        return out

    def _sentiment_trend(self, df: pd.DataFrame) -> list[dict]:
        if "Date" not in df.columns or "Sentiment" not in df.columns:
            return []
        d = df.copy()
        d["_day"] = pd.to_datetime(d["Date"], errors="coerce").dt.date.astype("string")
        out = []
        for (day, sent), g in d.groupby(["_day", "Sentiment"], dropna=False):
            out.append({
                "Date": None if pd.isna(day) else str(day),
                "Sentiment": None if pd.isna(sent) else sent,
                "Count of Content": int(len(g)),
            })
        return out

    def _top_content(self, df: pd.DataFrame, n: int, cols: list[str]) -> list[dict]:
        d = df.sort_values("_eng", ascending=False).head(n)
        out = []
        for _, r in d.iterrows():
            row = {"Engagement": int(r["_eng"])}
            for c in cols:
                row[c] = None if (c not in d.columns or pd.isna(r.get(c))) else _safe(r.get(c))
            if row.get("Link URL"):
                row["source_url"] = row["Link URL"]
            out.append(row)
        return out

    # wrappers yang mengecek view memang milik report type
    def _add_qt(self, report_input, view_id, rows, metadata=None):
        if view_id in self.quantitative_view_ids:
            self.add_quantitative_view(report_input, view_id=view_id, rows=rows,
                                       metadata=metadata)

    def _add_ql(self, report_input, view_id, rows, reason=None):
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
