"""
Task 1 builder: Spokesperson Intelligence (SFIR).

PENTING — keterbatasan data:
Seluruh report ini dibangun dari field Spokesperson, Media Name, dan Ad Value.
Di data brand konsumen (mis. AQUA/Nestle) coverage-nya sangat rendah:
Spokesperson ~2% (bahkan 0%), Media Name ~10%, Ad Value ~10%. Report ini
dirancang untuk dataset bertipe PR/mainstream-media yang MELACAK juru bicara.

Selain itu, field Spokesperson/Media Name/Ad Value TIDAK diekspos oleh
db.fetch_posts_df (mereka ada di kolom raw JSONB). Jadi builder ini:
- memakai kolom Spokesperson/Media Name/Ad Value HANYA jika sudah diekspos ke
  fetch_posts_df (future-proof);
- kalau belum diekspos ATAU kosong -> tandai N/A dengan alasan jelas.
Ini bukan bug: dengan data sekarang, report SFIR memang belum viable.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from database import db
from reporting.task1.base_builder import BaseReportInputBuilder, BuildRequest

SPOKESPERSON_COL = "Spokesperson"
MEDIA_NAME_COL = "Media Name"
AD_VALUE_COL = "Ad Value"


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(0)


def _nonempty(series: pd.Series) -> pd.Series:
    """True untuk nilai yang benar-benar ada (bukan kosong / '-')."""
    s = series.astype(str).str.strip()
    return (s != "") & (s.str.lower() != "nan") & (s != "-")


class SpokespersonIntelligenceBuilder(BaseReportInputBuilder):
    report_type_id = "spokesperson_intelligence"

    def build_views(self, report_input: dict[str, Any], request: BuildRequest) -> None:
        df = db.fetch_posts_df(
            campaign_name=request.project_name,
            start_date=request.start_date,
            end_date=request.end_date,
            channels=list(request.channels) or None,
        )

        # Cek ketersediaan Spokesperson. Kalau tidak ada kolom / semua kosong,
        # seluruh report N/A dengan alasan jujur.
        has_spox = (
            df is not None
            and not df.empty
            and SPOKESPERSON_COL in df.columns
            and _nonempty(df[SPOKESPERSON_COL]).any()
        )
        if not has_spox:
            reason = (
                "Spokesperson tidak tersedia/kosong pada data ini (coverage ~2% "
                "di data brand konsumen; kolom juga belum diekspos ke "
                "fetch_posts_df). Report SFIR butuh dataset PR/media dengan "
                "pelacakan juru bicara."
            )
            self._mark_all_remaining_na(report_input, reason=reason)
            return

        # --- Kalau Spokesperson tersedia, hitung view-nya ---
        d = df[_nonempty(df[SPOKESPERSON_COL])].copy()
        d["_ad"] = _num(d.get(AD_VALUE_COL, pd.Series(dtype=float)))

        # qt_sfir_kpi_overview (total period)
        self._add_qt(report_input, "qt_sfir_kpi_overview", [{
            "Spokesperson": int(d[SPOKESPERSON_COL].nunique()),
            "Ad Value": int(d["_ad"].sum()),
            "Content": int(len(d)),
            "Media Name": int(d[MEDIA_NAME_COL].nunique()) if MEDIA_NAME_COL in d.columns else None,
        }])

        # qt_sfir_top5_spokesperson_rank (Top 5 by Ad Value)
        agg = (d.groupby(SPOKESPERSON_COL)
                 .agg(Content=("_ad", "size"), Ad_Value=("_ad", "sum"))
                 .reset_index()
                 .sort_values("Ad_Value", ascending=False).head(5))
        self._add_qt(report_input, "qt_sfir_top5_spokesperson_rank", [{
            "Spokesperson": r[SPOKESPERSON_COL],
            "Ad Value": int(r["Ad_Value"]),
            "Content": int(r["Content"]),
            "Media Name": None,
        } for _, r in agg.iterrows()])

        # qt_sfir_sentiment_distribution_by_spokesperson
        rows = []
        for (spox, s), g in d.groupby([SPOKESPERSON_COL, "Sentiment"], dropna=False):
            rows.append({"Spokesperson": spox, "Sentiment": (None if pd.isna(s) else s),
                         "Content": int(len(g))})
        self._add_qt(report_input, "qt_sfir_sentiment_distribution_by_spokesperson", rows)

        # qt_sfir_channel_effectiveness_by_spokesperson
        rows = []
        for (spox, ch), g in d.groupby([SPOKESPERSON_COL, "Channel"], dropna=False):
            rows.append({"Spokesperson": spox, "Channel": (None if pd.isna(ch) else ch),
                         "Content": int(len(g))})
        self._add_qt(report_input, "qt_sfir_channel_effectiveness_by_spokesperson", rows)

        # ql_sfir_exposure_quotes_and_analysis (1-3 baris representatif per spokesperson)
        rows = []
        for spox, g in d.groupby(SPOKESPERSON_COL):
            for _, r in g.head(3).iterrows():
                rows.append({
                    "Spokesperson": spox,
                    "Title": r.get("Title"),
                    "Content": r.get("Content"),
                    "Media Name": r.get(MEDIA_NAME_COL),
                    "Sentiment": r.get("Sentiment"),
                    "source_url": r.get("Link URL"),
                })
        self._add_ql(report_input, "ql_sfir_exposure_quotes_and_analysis", rows,
                     reason="Contoh eksposur per juru bicara.")

        # ql_sfir_issue_cards_per_spokesperson -> butuh Topic (0% terisi) -> N/A
        self._na(report_input, "ql_sfir_issue_cards_per_spokesperson", "qualitative",
                 "Butuh Topic Extraction (0% terisi, perlu topic enrichment).")

        self._mark_all_remaining_na(report_input, reason="Belum diimplementasikan di builder ini.")

    # --- helper (identik pola) ---
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


BUILDER_CLASS = SpokespersonIntelligenceBuilder
