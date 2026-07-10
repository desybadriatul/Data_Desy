"""Task 1 builder: Spokesperson Intelligence (SFIR) — VERSI 3.

Perubahan besar dari v2: sumber spokesperson bukan lagi kolom mentah Sonar,
melainkan **cache hasil spokesperson enrichment** (LLM), lewat foundation Fuji:

    get_enriched_scope_posts        -> post canonical Online Media
    build_spokesperson_enrichment_candidates -> kandidat (Ad Value, url, konteks)
    load_cached_spokesperson_results         -> hasil enrichment tersimpan
    build_spokesperson_report_views          -> baris mention siap pakai

SCOPE (dikonfirmasi Isung): SFIR hanya untuk Online Media / Print.

DUA HAL PENTING
---------------
1. `spokesperson_raw` TIDAK dipakai sebagai kebenaran final. Kontrak Fuji
   (docs/SPOKESPERSON_ENRICHMENT_CONTRACT.md §9) menyatakan nilai mentah Sonar
   bisa tergabung nama+jabatan, berisi organisasi, atau salah.

2. Builder ini TIDAK memakai build_spokesperson_report_views(). Adapter tersebut
   menimpa `represented_campaign` bernilai None dengan nama campaign artikel,
   sehingga siapa pun yang dikutip pada artikel ber-tag "Aqua" dianggap juru
   bicara Aqua. Contoh nyata dari data Aqua:

       cache  : Brian Yuliarto -> represented_campaign = None   (benar)
       adapter: Brian Yuliarto -> represented_campaign = "Aqua" (salah)

   Beliau Menteri Pendidikan Tinggi yang berbicara tentang hilirisasi mineral.
   Karena itu builder membaca cache LANGSUNG, lalu menyaring
   `represented_campaign == client_brand` sebelum menghitung apa pun.

Cache kosong -> seluruh view N/A dengan alasan yang menjelaskan langkah berikutnya.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal
from typing import Any

from reporting.contracts.report_input_contract_v1 import add_limitation
from reporting.task1.base_builder import BaseReportInputBuilder, BuildRequest

SFIR_CHANNEL = "Online Media"
TOP_SPOKESPERSON_LIMIT = 5
QUOTES_LIMIT = 10


def _safe(value: Any) -> Any:
    """Ubah tipe DB (Decimal/date/numpy) jadi tipe Python biasa (JSON-safe)."""
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


def _num(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


class SpokespersonIntelligenceBuilder(BaseReportInputBuilder):
    report_type_id = "spokesperson_intelligence"

    def build_views(self, report_input: dict[str, Any], request: BuildRequest) -> None:
        brand = _text(getattr(request, "client_brand", "") or request.project_name)

        requested = list(request.channels or [])
        if requested and requested != [SFIR_CHANNEL]:
            add_limitation(
                report_input,
                f"Channel yang diminta ({', '.join(requested)}) diabaikan. "
                f"SFIR hanya berlaku untuk {SFIR_CHANNEL}.",
            )
        report_input["scope"]["enforced_channel"] = SFIR_CHANNEL
        report_input["scope"]["spokesperson_brand_filter"] = brand

        posts = self._fetch_posts(report_input, request)
        if posts is None:
            return

        candidates = self._build_candidates(report_input, posts, request, brand)
        if candidates is None:
            return

        mentions = self._load_mentions(report_input, candidates, brand)
        if mentions is None:
            return

        # --- Saring: hanya yang benar-benar mewakili brand ---
        own = [m for m in mentions
               if _text(m.get("represented_campaign")).casefold() == brand.casefold()]
        others = [m for m in mentions if m not in own]

        if not own:
            reason = (
                f"Dari {len(candidates)} artikel {SFIR_CHANNEL} ber-tag '{brand}', "
                f"ditemukan {len(mentions)} sebutan juru bicara, namun tidak satu pun "
                f"berbicara mewakili {brand}. SFIR tidak dapat dibuat untuk scope ini."
            )
            add_limitation(report_input, reason)
            self._mark_all_remaining_na(
                report_input, reason=f"Tidak ada juru bicara yang mewakili {brand}.")
            return

        if others:
            names = sorted({_text(m.get("spokesperson_name")) for m in others})
            add_limitation(
                report_input,
                f"{len(names)} nama lain muncul pada artikel ber-tag '{brand}' "
                f"tetapi tidak berbicara mewakili {brand} (mis. "
                f"{', '.join(names[:3])}). Mereka tidak dihitung sebagai juru bicara "
                f"{brand}. Perlu ditinjau apakah campaign tagging sudah tepat."
            )

        self._add_kpi_overview(report_input, own, candidates)
        self._add_top_rank(report_input, own)
        self._add_sentiment(report_input, own, posts)
        self._add_channel(report_input, own)
        self._add_quotes(report_input, own)

        self._na(report_input, "ql_sfir_issue_cards_per_spokesperson", "qualitative",
                 f"Butuh report-topic per artikel; topic enrichment untuk "
                 f"{SFIR_CHANNEL} belum tersedia.")
        self._mark_all_remaining_na(
            report_input, reason="Belum diimplementasikan di builder ini.")

    # ------------------------------------------------------------------
    #  Tahapan pengambilan data. Tiap tahap punya alasan N/A sendiri.
    # ------------------------------------------------------------------
    def _fetch_posts(self, report_input, request) -> list[dict] | None:
        from reporting.enrichment.topic_batch_builder import get_enriched_scope_posts

        data = get_enriched_scope_posts(
            project_name=request.project_name,
            start_date=request.start_date,
            end_date=request.end_date,
            channels=[SFIR_CHANNEL],
        )
        posts = data.get("posts") or []
        if not posts:
            add_limitation(report_input, (
                f"Campaign '{request.project_name}' tidak memiliki artikel "
                f"{SFIR_CHANNEL} pada periode ini. SFIR membutuhkan data "
                "pemberitaan media yang melacak juru bicara."
            ))
            self._mark_all_remaining_na(
                report_input, reason=f"Tidak ada artikel {SFIR_CHANNEL}.")
            return None
        report_input["scope"]["online_media_articles"] = len(posts)
        return posts

    def _build_candidates(self, report_input, posts, request, brand) -> list[dict] | None:
        from reporting.enrichment.spokesperson_enrichment import (
            build_spokesperson_enrichment_candidates,
        )

        universe = [brand]
        for extra in (getattr(request, "competitor_brands", None) or []):
            if _text(extra) and _text(extra) not in universe:
                universe.append(_text(extra))

        result = build_spokesperson_enrichment_candidates(posts, campaign_universe=universe)
        candidates = result.get("candidates") or []
        report_input["scope"]["spokesperson_sampling"] = {
            "eligible_count": result.get("eligible_count"),
            "sample_size": result.get("sample_size"),
            "selected_count": result.get("selected_count"),
            "policy": result.get("selection_policy"),
        }
        if not candidates:
            add_limitation(report_input, (
                f"Tidak ada artikel {SFIR_CHANNEL} yang memenuhi syarat kandidat "
                "spokesperson enrichment pada periode ini."
            ))
            self._mark_all_remaining_na(
                report_input, reason="Tidak ada kandidat spokesperson.")
            return None
        return candidates

    def _load_mentions(self, report_input, candidates, brand) -> list[dict] | None:
        """Baca cache enrichment LANGSUNG, tanpa lewat build_spokesperson_report_views.

        Alasan: adapter menimpa `represented_campaign` yang bernilai None dengan
        nama campaign artikel. Akibatnya siapa pun yang dikutip pada artikel
        ber-tag 'Aqua' dianggap juru bicara Aqua — termasuk pejabat yang sedang
        membicarakan topik lain. Cache menyimpan nilai yang benar (None), jadi
        builder membaca dari sana dan menggabungkan metadata dari kandidat.
        """
        from reporting.enrichment.spokesperson_enrichment_store import (
            load_cached_spokesperson_results,
        )

        cached = load_cached_spokesperson_results(candidates)
        rows = list(cached.values()) if isinstance(cached, dict) else list(cached or [])

        if not rows:
            add_limitation(report_input, (
                f"Ditemukan {len(candidates)} artikel kandidat, tetapi cache "
                "spokesperson enrichment masih kosong. Jalankan spokesperson "
                "enrichment terlebih dahulu (lihat "
                "docs/SPOKESPERSON_ENRICHMENT_CONTRACT.md)."
            ))
            self._mark_all_remaining_na(
                report_input, reason="Cache spokesperson enrichment kosong.")
            return None

        meta_by_id = {str(c.get("canonical_post_id")): c for c in candidates}
        statuses: Counter[str] = Counter()
        mentions: list[dict[str, Any]] = []

        for row in rows:
            pid = str(row.get("canonical_post_id") or "")
            statuses[_text(row.get("status")) or "unknown"] += 1
            meta = meta_by_id.get(pid, {})
            for speaker in row.get("spokespersons") or []:
                if not isinstance(speaker, dict):
                    continue
                mentions.append({
                    "canonical_post_id": pid,
                    "spokesperson_name": speaker.get("spokesperson_name"),
                    "spokesperson_role": speaker.get("spokesperson_role"),
                    "organization": speaker.get("organization"),
                    "spokesperson_type": speaker.get("spokesperson_type"),
                    # Nilai apa adanya dari cache. Tidak diisi ulang.
                    "represented_campaign": speaker.get("represented_campaign"),
                    "evidence_sentence": speaker.get("evidence_sentence"),
                    "confidence": speaker.get("confidence"),
                    "media_name": meta.get("media_name"),
                    "ad_value": meta.get("ad_value"),
                    "title": meta.get("title"),
                    "url": meta.get("source_url"),
                })

        missing = len(candidates) - len(rows)
        report_input.setdefault("metric_readiness", {})["spokesperson_enrichment"] = {
            "source": "spokesperson_enrichment_cache (dibaca langsung)",
            "candidate_count": len(candidates),
            "cached_article_count": len(rows),
            "missing_candidate_count": max(0, missing),
            "status_counts": dict(statuses),
            "mention_count": len(mentions),
        }
        if missing > 0:
            add_limitation(
                report_input,
                f"{missing} dari {len(candidates)} artikel kandidat belum "
                "ter-enrich. Analisis memakai artikel yang sudah ada di cache.",
            )
        return mentions

    # ------------------------------------------------------------------
    #  View
    # ------------------------------------------------------------------
    def _add_kpi_overview(self, report_input, own, candidates) -> None:
        articles = {m.get("canonical_post_id") for m in own}
        ad_by_article: dict[Any, float] = {}
        media: set[str] = set()
        for m in own:
            pid = m.get("canonical_post_id")
            if pid not in ad_by_article:
                ad_by_article[pid] = _num(m.get("ad_value"))
            if _text(m.get("media_name")):
                media.add(_text(m.get("media_name")))

        total_ad = sum(ad_by_article.values())
        self._add_qt(report_input, "qt_sfir_kpi_overview", [{
            "Spokesperson": len({_text(m.get("spokesperson_name")) for m in own}),
            "Ad Value": int(total_ad) if total_ad else None,
            "Content": len(articles),
            "Media Name": len(media) or None,
        }], metadata={
            "channel": SFIR_CHANNEL,
            "articles_screened": len(candidates),
            "note": "Hanya juru bicara yang mewakili brand yang dihitung.",
        })

    def _add_top_rank(self, report_input, own) -> None:
        agg: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"articles": set(), "ad": 0.0, "media": set(), "role": None})
        for m in own:
            name = _text(m.get("spokesperson_name"))
            if not name:
                continue
            entry = agg[name]
            pid = m.get("canonical_post_id")
            if pid not in entry["articles"]:
                entry["articles"].add(pid)
                entry["ad"] += _num(m.get("ad_value"))
            if _text(m.get("media_name")):
                entry["media"].add(_text(m.get("media_name")))
            entry["role"] = entry["role"] or _text(m.get("spokesperson_role")) or None

        ranked = sorted(agg.items(),
                        key=lambda kv: (kv[1]["ad"], len(kv[1]["articles"])),
                        reverse=True)[:TOP_SPOKESPERSON_LIMIT]

        rows = [{
            "Spokesperson": name,
            "Role": entry["role"],
            "Ad Value": int(entry["ad"]) if entry["ad"] else None,
            "Content": len(entry["articles"]),
            "Media Name": ", ".join(sorted(entry["media"])[:3]) or None,
        } for name, entry in ranked]
        self._add_qt(report_input, "qt_sfir_top5_spokesperson_rank", rows)

    def _add_sentiment(self, report_input, own, posts) -> None:
        sentiment_by_id = {str(p.get("canonical_post_id")): p.get("sentiment")
                           for p in posts}
        counter: Counter[tuple[str, str]] = Counter()
        for m in own:
            name = _text(m.get("spokesperson_name"))
            sentiment = sentiment_by_id.get(str(m.get("canonical_post_id")))
            if name:
                counter[(name, _text(sentiment) or "unclassified")] += 1

        rows = [{"Spokesperson": name, "Sentiment": sentiment, "Content": count}
                for (name, sentiment), count in sorted(counter.items())]
        self._add_qt(report_input, "qt_sfir_sentiment_distribution_by_spokesperson", rows)

    def _add_channel(self, report_input, own) -> None:
        # Channel selalu Online Media, jadi yang bermakna adalah outlet media.
        counter: Counter[tuple[str, str]] = Counter()
        for m in own:
            name = _text(m.get("spokesperson_name"))
            outlet = _text(m.get("media_name")) or "(tidak diketahui)"
            if name:
                counter[(name, outlet)] += 1

        rows = [{"Spokesperson": name, "Channel": SFIR_CHANNEL,
                 "Media Name": outlet, "Content": count}
                for (name, outlet), count in sorted(counter.items())]
        self._add_qt(report_input, "qt_sfir_channel_effectiveness_by_spokesperson", rows,
                     metadata={"note": f"Seluruh artikel berasal dari {SFIR_CHANNEL}; "
                                       "breakdown ditampilkan per outlet media."})

    def _add_quotes(self, report_input, own) -> None:
        ranked = sorted(own, key=lambda m: _num(m.get("ad_value")), reverse=True)
        rows = []
        for m in ranked[:QUOTES_LIMIT]:
            rows.append({
                "Spokesperson": _text(m.get("spokesperson_name")),
                "Role": _text(m.get("spokesperson_role")) or None,
                "Organization": _text(m.get("organization")) or None,
                "Title": _safe(m.get("title")),
                "Content": _safe(m.get("evidence_sentence")),
                "Media Name": _safe(m.get("media_name")),
                "Confidence": _safe(m.get("confidence")),
                "source_url": _safe(m.get("url")),
            })
        self._add_ql(report_input, "ql_sfir_exposure_quotes_and_analysis", rows,
                     reason=f"Kutipan juru bicara {SFIR_CHANNEL} hasil enrichment LLM.")

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
        key = ("quantitative_views" if view_type == "quantitative"
               else "qualitative_views")
        if view_id in allowed and view_id not in report_input[key]:
            self.mark_view_na(report_input, view_id=view_id,
                              view_type=view_type, reason=reason)

    def _mark_all_remaining_na(self, report_input, *, reason):
        for view_id in self.quantitative_view_ids:
            self._na(report_input, view_id, "quantitative", reason)
        for view_id in self.qualitative_view_ids:
            self._na(report_input, view_id, "qualitative", reason)


BUILDER_CLASS = SpokespersonIntelligenceBuilder

__all__ = ["SpokespersonIntelligenceBuilder", "BUILDER_CLASS", "SFIR_CHANNEL"]
