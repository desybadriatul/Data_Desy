"""
Task 1 builder: Spokesperson Intelligence (SFIR) — VERSI 2.

SCOPE (dikonfirmasi Isung, perancang report):
SFIR hanya berlaku untuk **Online Media**. Bukan untuk channel sosial.
Spokesperson tidak pernah terisi di Twitter/TikTok/Instagram/Facebook/YouTube.
Bukti dari data Aqua (2.600 post):

    Online Media : 273 artikel -> 51 spokesperson terisi (18,7%)
    Twitter      : 1.390 post  -> 0
    TikTok       :   716 post  -> 0
    Instagram    :   182 post  -> 0
    Facebook / YouTube / Forum -> 0

Karena itu builder ini MEMAKSA scope ke Online Media, apa pun channel yang
diminta pemanggil. Kalau campaign tidak punya artikel Online Media, atau punya
artikel tapi tanpa spokesperson, seluruh view ditandai N/A dengan alasan yang
menjelaskan APA yang kurang dan APA yang perlu dilakukan.

Isung: "ada kemungkinan kalau ga ada spokesperson di datanya reportnya ga bisa
di-generate." Jadi 0 view READY pada campaign konsumen adalah hasil yang BENAR,
bukan kegagalan builder.

CATATAN TEKNIS:
Field Spokesperson / Media Name / Ad Value belum diekspos oleh db.fetch_posts_df
(mereka masih di kolom raw JSONB). Builder ini sudah future-proof: begitu kolom
tersebut tersedia, view langsung terisi tanpa perubahan kode.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pandas as pd

from database import db
from reporting.contracts.report_input_contract_v1 import add_limitation
from reporting.task1.base_builder import BaseReportInputBuilder, BuildRequest

SPOKESPERSON_COL = "Spokesperson"
MEDIA_NAME_COL = "Media Name"
AD_VALUE_COL = "Ad Value"

# SFIR hanya berlaku pada channel ini.
SFIR_CHANNEL = "Online Media"

TOP_SPOKESPERSON_LIMIT = 5
QUOTES_PER_SPOKESPERSON = 3


def _safe(value: Any) -> Any:
    """Ubah tipe DB (Decimal/Timestamp/numpy) jadi tipe Python biasa (JSON-safe)."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return value
    return value


def _num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0)


def _nonempty(series: pd.Series) -> pd.Series:
    """True untuk nilai yang benar-benar ada (bukan NaN / kosong / '-')."""
    filled = series.notna()
    text = series.astype(str).str.strip()
    return filled & (text != "") & (text.str.lower() != "nan") & (text != "-")


class SpokespersonIntelligenceBuilder(BaseReportInputBuilder):
    report_type_id = "spokesperson_intelligence"

    def build_views(self, report_input: dict[str, Any], request: BuildRequest) -> None:
        # SFIR selalu Online Media, apa pun yang diminta pemanggil.
        requested = list(request.channels or [])
        if requested and requested != [SFIR_CHANNEL]:
            add_limitation(
                report_input,
                f"Channel yang diminta ({', '.join(requested)}) diabaikan. "
                f"SFIR hanya berlaku untuk {SFIR_CHANNEL}.",
            )
        report_input["scope"]["enforced_channel"] = SFIR_CHANNEL

        df = db.fetch_posts_df(
            campaign_name=request.project_name,
            start_date=request.start_date,
            end_date=request.end_date,
            channels=[SFIR_CHANNEL],
        )

        # --- Kasus 1: campaign tidak punya artikel Online Media sama sekali ---
        if df is None or df.empty:
            # Pesan panjang: untuk dibaca manusia, menjelaskan langkah berikutnya.
            add_limitation(report_input, (
                f"Campaign '{request.project_name}' tidak memiliki artikel "
                f"{SFIR_CHANNEL} pada periode ini. SFIR membutuhkan data "
                "pemberitaan media yang melacak juru bicara. Jalankan SFIR pada "
                "campaign dengan liputan media, atau perluas periode."
            ))
            # Pesan pendek: menandai tiap view, muncul berulang.
            self._mark_all_remaining_na(
                report_input, reason=f"Tidak ada artikel {SFIR_CHANNEL}.")
            return

        article_count = len(df)
        report_input["scope"]["online_media_articles"] = article_count

        # --- Kasus 2: kolom Spokesperson belum diekspos ke fetch_posts_df ---
        if SPOKESPERSON_COL not in df.columns:
            add_limitation(report_input, (
                f"Ditemukan {article_count} artikel {SFIR_CHANNEL}, tetapi kolom "
                f"'{SPOKESPERSON_COL}' belum diekspos ke canonical post (masih "
                "tersimpan di raw JSONB) sehingga builder tidak dapat membacanya. "
                "Perlu penambahan Spokesperson/Media Name/Ad Value ke canonical "
                "layer sebelum SFIR bisa dibuat."
            ))
            self._mark_all_remaining_na(
                report_input,
                reason=f"Kolom '{SPOKESPERSON_COL}' belum ada di canonical post.")
            return

        # --- Kasus 3: kolom ada tapi tidak satu pun artikel punya spokesperson ---
        has_spox = _nonempty(df[SPOKESPERSON_COL])
        spox_count = int(has_spox.sum())
        if spox_count == 0:
            add_limitation(report_input, (
                f"Ditemukan {article_count} artikel {SFIR_CHANNEL}, namun tidak "
                "satu pun memiliki data juru bicara. SFIR tidak dapat dibuat untuk "
                "scope ini. Pertimbangkan spokesperson enrichment, atau pilih "
                "campaign dengan liputan yang mengutip juru bicara."
            ))
            self._mark_all_remaining_na(
                report_input,
                reason=f"Tidak ada juru bicara pada {article_count} artikel.")
            return

        # --- Data cukup: bangun view ---
        coverage_pct = round(100 * spox_count / article_count, 1)
        if coverage_pct < 100:
            add_limitation(
                report_input,
                f"Spokesperson tersedia pada {spox_count} dari {article_count} "
                f"artikel {SFIR_CHANNEL} ({coverage_pct}%). Analisis berbasis "
                "artikel yang memiliki juru bicara saja.",
            )

        d = df[has_spox].copy()
        d["_ad"] = _num(d.get(AD_VALUE_COL, pd.Series(dtype=float)))
        has_media = MEDIA_NAME_COL in d.columns
        has_ad = AD_VALUE_COL in d.columns

        if not has_ad:
            add_limitation(
                report_input,
                f"Kolom '{AD_VALUE_COL}' belum diekspos ke canonical post; "
                "metrik Ad Value ditampilkan sebagai 0/N/A.",
            )

        self._add_kpi_overview(report_input, d, has_media, has_ad, coverage_pct)
        self._add_top_rank(report_input, d, has_media, has_ad)
        self._add_sentiment_by_spokesperson(report_input, d)
        self._add_channel_by_spokesperson(report_input, d)
        self._add_quotes(report_input, d, has_media)

        # Butuh Topic yang belum tersedia untuk artikel Online Media.
        self._na(report_input, "ql_sfir_issue_cards_per_spokesperson", "qualitative",
                 "Butuh report-topic per artikel; topic enrichment untuk "
                 f"{SFIR_CHANNEL} belum tersedia.")

        self._mark_all_remaining_na(
            report_input, reason="Belum diimplementasikan di builder ini.")

    # ------------------------------------------------------------------
    def _add_kpi_overview(self, report_input, d, has_media, has_ad, coverage) -> None:
        self._add_qt(report_input, "qt_sfir_kpi_overview", [{
            "Spokesperson": int(d[SPOKESPERSON_COL].nunique()),
            "Ad Value": int(d["_ad"].sum()) if has_ad else None,
            "Content": int(len(d)),
            "Media Name": int(d[MEDIA_NAME_COL].nunique()) if has_media else None,
        }], metadata={"channel": SFIR_CHANNEL,
                      "spokesperson_coverage_pct": coverage})

    def _add_top_rank(self, report_input, d, has_media, has_ad) -> None:
        grouped = d.groupby(SPOKESPERSON_COL)
        agg = grouped.agg(Content=("_ad", "size"), Ad_Value=("_ad", "sum"))
        agg = agg.reset_index().sort_values(
            ["Ad_Value", "Content"], ascending=False
        ).head(TOP_SPOKESPERSON_LIMIT)

        rows = []
        for _, r in agg.iterrows():
            spox = r[SPOKESPERSON_COL]
            media = None
            if has_media:
                names = d.loc[d[SPOKESPERSON_COL] == spox, MEDIA_NAME_COL].dropna()
                media = ", ".join(sorted(set(names.astype(str)))[:3]) or None
            rows.append({
                "Spokesperson": _safe(spox),
                "Ad Value": int(r["Ad_Value"]) if has_ad else None,
                "Content": int(r["Content"]),
                "Media Name": media,
            })
        self._add_qt(report_input, "qt_sfir_top5_spokesperson_rank", rows)

    def _add_sentiment_by_spokesperson(self, report_input, d) -> None:
        rows = []
        for (spox, sentiment), group in d.groupby(
            [SPOKESPERSON_COL, "Sentiment"], dropna=False
        ):
            rows.append({
                "Spokesperson": _safe(spox),
                "Sentiment": None if pd.isna(sentiment) else _safe(sentiment),
                "Content": int(len(group)),
            })
        self._add_qt(report_input, "qt_sfir_sentiment_distribution_by_spokesperson", rows)

    def _add_channel_by_spokesperson(self, report_input, d) -> None:
        # Channel selalu Online Media; view ini jadi breakdown per media outlet
        # bila Media Name tersedia, kalau tidak cukup satu baris per spokesperson.
        rows = []
        for (spox, channel), group in d.groupby(
            [SPOKESPERSON_COL, "Channel"], dropna=False
        ):
            rows.append({
                "Spokesperson": _safe(spox),
                "Channel": None if pd.isna(channel) else _safe(channel),
                "Content": int(len(group)),
            })
        self._add_qt(report_input, "qt_sfir_channel_effectiveness_by_spokesperson", rows,
                     metadata={"note": f"Seluruh artikel berasal dari {SFIR_CHANNEL}."})

    def _add_quotes(self, report_input, d, has_media) -> None:
        rows = []
        for spox, group in d.groupby(SPOKESPERSON_COL):
            top = group.head(QUOTES_PER_SPOKESPERSON)
            for _, r in top.iterrows():
                rows.append({
                    "Spokesperson": _safe(spox),
                    "Title": _safe(r.get("Title")),
                    "Content": _safe(r.get("Content")),
                    "Media Name": _safe(r.get(MEDIA_NAME_COL)) if has_media else None,
                    "Sentiment": _safe(r.get("Sentiment")),
                    "source_url": _safe(r.get("Link URL")),
                })
        self._add_ql(report_input, "ql_sfir_exposure_quotes_and_analysis", rows,
                     reason="Contoh eksposur per juru bicara di Online Media.")

    # ------------------------------------------------------------------
    def _add_qt(self, report_input, view_id, rows, metadata=None):
        if view_id in self.quantitative_view_ids:
            self.add_quantitative_view(report_input, view_id=view_id,
                                       rows=rows, metadata=metadata)

    def _add_ql(self, report_input, view_id, rows, reason=None):
        if view_id in self.qualitative_view_ids:
            self.add_qualitative_view(report_input, view_id=view_id,
                                      rows=rows, evidence_reason=reason)

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
        for view_id in self.quantitative_view_ids:
            self._na(report_input, view_id, "quantitative", reason)
        for view_id in self.qualitative_view_ids:
            self._na(report_input, view_id, "qualitative", reason)


BUILDER_CLASS = SpokespersonIntelligenceBuilder

__all__ = ["SpokespersonIntelligenceBuilder", "BUILDER_CLASS", "SFIR_CHANNEL"]
