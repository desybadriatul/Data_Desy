"""
Task 2 renderer: Brand & Content Effectiveness (BCE).

Pola sama dengan industry_trend_report_renderer.py:
- Renderer TIDAK membuat file .pptx. Dia menghasilkan "paket siap-PPT"
  (dict berisi slides + ppt_style_brief) yang dirender jadi PPTX oleh Claude.
- Sumber kebenaran struktur = registry (9 section, Action Plan First).
- Renderer TIDAK BOLEH mengarang metrik, quote, topic, atau URL.
  View NOT_AVAILABLE dirender sebagai N/A, bukan disembunyikan.

Action taxonomy BCE hanya tiga: Scale / Fix / Test.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from reporting.storage.report_input_store import get_report_input
from reporting.task2.report_outline_builder import build_report_outline_from_id

REPORT_TYPE_ID = "brand_content_effectiveness"
PREVIEW_VERSION = "bce_data_preview_v1"
PACKAGE_VERSION = "bce_ppt_package_v1"

# SALIN PERSIS dari registry -> action_taxonomy_by_report_type ->
# "Brand & Content Effectiveness". Jangan diarang.
ACTION_TYPES = ("Scale", "Fix", "Test")

# Ambang keputusan. Bukti tipis menurunkan prioritas, bukan menghapus sinyal.
MIN_POSTS_FOR_HIGH_PRIORITY = 3
NEGATIVE_PCT_THRESHOLD = 25.0
LOW_ENGAGEMENT_RATIO = 0.5   # channel < 50% rata-rata dianggap underperform
TOPIC_COVERAGE_SAFE_PCT = 60.0


class BCERendererError(RuntimeError):
    """Raised when Task 2 cannot safely build a BCE package."""


# ----------------------------------------------------------------------
#  Helper baca view
# ----------------------------------------------------------------------
def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _view(report_input: Mapping[str, Any], view_id: str) -> Mapping[str, Any] | None:
    for group in ("quantitative_views", "qualitative_views"):
        views = _as_mapping(report_input.get(group))
        if view_id in views:
            return _as_mapping(views[view_id])
    return None


def _rows(report_input: Mapping[str, Any], view_id: str) -> list[dict[str, Any]]:
    view = _view(report_input, view_id)
    rows = view.get("rows") if view else None
    return list(rows) if isinstance(rows, list) else []


def _view_status(report_input: Mapping[str, Any], view_id: str) -> dict[str, Any]:
    view = _view(report_input, view_id)
    if view is None:
        return {"view_id": view_id, "status": "MISSING", "rows": 0,
                "reason": "View tidak ada."}
    meta = _as_mapping(view.get("metadata"))
    status = str(meta.get("status", "READY")).upper()
    rows = view.get("rows")
    count = len(rows) if isinstance(rows, list) else 0
    if status == "READY" and count == 0:
        status = "EMPTY"
    return {"view_id": view_id, "status": status, "rows": count,
            "reason": meta.get("reason")}


def _num(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _fmt_int(value: Any) -> str:
    return f"{int(_num(value)):,}"


def _na(value: Any) -> str:
    return "N/A" if value in (None, "") else str(value)


def _clean_text(value: Any, limit: int | None = None) -> str:
    if value in (None, ""):
        return "N/A"
    text = " ".join(str(value).split()).replace("|", "/")
    if limit and len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


_TEXT_COLUMNS = {"Content", "Title", "reason", "Recommended Action",
                 "Rationale", "Supporting Evidence", "Expected Impact"}


def _markdown_table(rows: list[dict], columns: list[str], limit: int = 10,
                    text_limit: int = 120) -> str:
    if not rows:
        return "_Tidak ada data (N/A)._"
    lines = ["| " + " | ".join(columns) + " |",
             "|" + "|".join("---" for _ in columns) + "|"]
    for row in rows[:limit]:
        cells = [
            _clean_text(row.get(c), text_limit) if c in _TEXT_COLUMNS
            else _na(row.get(c))
            for c in columns
        ]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


ALL_VIEW_IDS = [
    "qt_bce_exec_kpi_summary",
    "qt_bce_sentiment_distribution",
    "qt_bce_channel_effectiveness",
    "qt_bce_format_theme_effectiveness",
    "qt_bce_top_performing_content",
    "ql_bce_brand_content_summary",
    "ql_bce_top_content_patterns",
    "ql_bce_recommendation_inputs",
    "ql_bce_top_content_by_media_type",
    "ql_bce_top_content_sentiment",
    "ql_bce_top_content_channel",
]


# ----------------------------------------------------------------------
#  Ringkasan
# ----------------------------------------------------------------------
def _kpi(report_input: Mapping[str, Any]) -> dict[str, Any]:
    rows = _rows(report_input, "qt_bce_exec_kpi_summary")
    row = rows[0] if rows else {}
    return {
        "campaign": row.get("Campaign"),
        "total_mentions": int(_num(row.get("Total Mentions"))),
        "total_engagement": int(_num(row.get("Total Engagement"))),
        "avg_engagement": row.get("Avg Engagement per Post"),
        "positive_pct": row.get("Positive Sentiment %"),
        "negative_pct": row.get("Negative Sentiment %"),
        "potential_reach": row.get("Potential Reach"),
    }


def _topic_coverage(report_input: Mapping[str, Any]) -> dict[str, Any]:
    """Coverage topic diambil dari metadata view/limitations, bukan dikarang."""
    for limitation in report_input.get("limitations") or []:
        text = str(limitation)
        if "Topic coverage" in text:
            try:
                pct = float(text.split("Topic coverage baru")[1].split("%")[0])
            except (IndexError, ValueError):
                continue
            return {
                "coverage_pct": pct,
                "safe_for_topic_conclusion": pct >= TOPIC_COVERAGE_SAFE_PCT,
                "message": (
                    f"Topic coverage {pct}%. "
                    + ("Aman untuk kesimpulan topic."
                       if pct >= TOPIC_COVERAGE_SAFE_PCT
                       else "Perlakukan sebagai early signal, bukan ranking final.")
                ),
            }
    has_topic = any(
        row.get("Topic Extraction")
        for row in _rows(report_input, "qt_bce_top_performing_content")
    )
    return {
        "coverage_pct": None,
        "safe_for_topic_conclusion": False,
        "message": ("Topic tersedia sebagian tanpa metrik coverage."
                    if has_topic
                    else "Topic belum tersedia (taxonomy/cache kosong)."),
    }


def _channel_stats(report_input: Mapping[str, Any]) -> dict[str, Any]:
    rows = _rows(report_input, "qt_bce_channel_effectiveness")
    valid = [r for r in rows if _num(r.get("Content Count")) > 0]
    if not valid:
        return {"rows": rows, "best": None, "worst": None, "avg_efficiency": None}
    for row in valid:
        row["_eff"] = _num(row.get("Total Engagement")) / _num(row.get("Content Count"))
    avg = sum(r["_eff"] for r in valid) / len(valid)
    ranked = sorted(valid, key=lambda r: r["_eff"], reverse=True)
    return {"rows": rows, "best": ranked[0], "worst": ranked[-1], "avg_efficiency": avg}


def _load_report_input(report_input_id: str) -> Mapping[str, Any]:
    if not isinstance(report_input_id, str) or not report_input_id.strip():
        raise BCERendererError("report_input_id wajib diisi.")
    report_input = get_report_input(report_input_id.strip())
    if report_input is None:
        raise BCERendererError(f"report_input_id '{report_input_id}' tidak ditemukan.")
    if report_input.get("report_type_id") != REPORT_TYPE_ID:
        raise BCERendererError(
            f"Renderer ini hanya untuk {REPORT_TYPE_ID}, "
            f"bukan {report_input.get('report_type_id')}."
        )
    if _as_mapping(report_input.get("validation")).get("status") == "FAIL":
        raise BCERendererError("report_input validation FAIL; tidak aman dirender.")
    return report_input


# ======================================================================
#  AUDIENCE CONTEXT
#  Audience mengubah CARA BERCERITA, bukan angkanya. Data tetap sama.
#  BCE lebih operasional: pembacanya tim konten, brand, dan marketing.
# ======================================================================

AUDIENCE_ALIASES = {
    "management": "Management",
    "manajemen": "Management",
    "executive": "Management",
    "marketing": "Marketing / Content Team",
    "content": "Marketing / Content Team",
    "tim konten": "Marketing / Content Team",
    "social media": "Social Media Team",
    "socmed": "Social Media Team",
    "brand": "Brand Team",
    "brand team": "Brand Team",
    "creative": "Creative Team",
    "kreatif": "Creative Team",
    "insight": "Insight / Analyst Team",
    "analyst": "Insight / Analyst Team",
    "tim insight": "Insight / Analyst Team",
    "agency": "Agency / Partner",
    "client": "Client / Stakeholder",
    "klien": "Client / Stakeholder",
}

AUDIENCE_GUIDANCE = {
    "Management": {
        "primary_question": "Apakah investasi konten kita membuahkan hasil, dan apa yang perlu diubah?",
        "narrative_angle": "ROI konten, efektivitas channel, keputusan alokasi",
        "preferred_outputs": [
            "KPI ringkas dan artinya",
            "channel mana yang layak ditambah/dikurangi",
            "action plan Scale/Fix/Test",
        ],
        "avoid": "detail caption dan tabel konten mentah",
    },
    "Marketing / Content Team": {
        "primary_question": "Konten seperti apa yang berhasil, dan apa yang harus kami produksi berikutnya?",
        "narrative_angle": "pola konten pemenang, tema resonan, format & channel efektif",
        "preferred_outputs": [
            "top performing content beserta tautan sumber",
            "pola yang bisa direplikasi",
            "channel paling efisien",
            "action plan operasional",
        ],
        "avoid": "analisis korporat dan metrik finansial",
    },
    "Social Media Team": {
        "primary_question": "Channel dan waktu mana yang paling efektif untuk konten kita?",
        "narrative_angle": "efektivitas per channel, engagement rate, contoh konten nyata",
        "preferred_outputs": [
            "engagement per konten tiap channel",
            "porsi akun terverifikasi",
            "contoh konten teratas per channel",
        ],
        "avoid": "narasi strategi jangka panjang",
    },
    "Brand Team": {
        "primary_question": "Bagaimana persepsi brand terbentuk dari konten yang beredar?",
        "narrative_angle": "sentimen, tema yang melekat pada brand, konsistensi pesan",
        "preferred_outputs": [
            "distribusi sentimen dan pergeserannya",
            "tema yang paling diasosiasikan dengan brand",
            "konten negatif yang perlu direspons",
        ],
        "avoid": "detail teknis metrik channel",
    },
    "Creative Team": {
        "primary_question": "Ide dan format konten apa yang terbukti resonan?",
        "narrative_angle": "pola kreatif, hook, format, contoh konkret",
        "preferred_outputs": [
            "contoh konten teratas lengkap dengan tautan sumber",
            "pola yang berulang pada konten pemenang",
            "rekomendasi Test untuk ide baru",
        ],
        "avoid": "tabel metrik tanpa contoh konten",
    },
    "Insight / Analyst Team": {
        "primary_question": "Seberapa kuat evidence di balik kesimpulan efektivitas konten ini?",
        "narrative_angle": "kualitas data, coverage, relasi metrik, caveat metodologi",
        "preferred_outputs": [
            "metric readout lengkap",
            "status tiap view (READY/N/A) dan alasannya",
            "audit trail evidence dan tautan sumber",
        ],
        "avoid": "rekomendasi normatif tanpa dukungan data",
    },
    "Agency / Partner": {
        "primary_question": "Apa yang harus kami eksekusi periode berikutnya?",
        "narrative_angle": "brief eksekusi, prioritas konten, channel fokus",
        "preferred_outputs": [
            "action plan Scale/Fix/Test yang jelas",
            "contoh konten acuan",
            "channel prioritas",
        ],
        "avoid": "diskusi internal dan data sensitif",
    },
    "Client / Stakeholder": {
        "primary_question": "Apakah kampanye ini berhasil, dan apa langkah berikutnya?",
        "narrative_angle": "hasil, bukti, rekomendasi",
        "preferred_outputs": [
            "KPI utama",
            "bukti konten berkinerja terbaik",
            "rekomendasi ringkas",
        ],
        "avoid": "jargon teknis dan detail metodologi",
    },
    "General Business User": {
        "primary_question": "Konten apa yang berhasil dan apa yang perlu diperbaiki?",
        "narrative_angle": "ringkasan performa, pola pemenang, aksi yang disarankan",
        "preferred_outputs": [
            "KPI utama",
            "top performing content",
            "action plan yang jelas",
        ],
        "avoid": "jargon teknis tanpa penjelasan",
    },
}


def normalize_audience_context(
    audience_context: str | None = None,
    audience_pov: str | None = None,
) -> dict[str, Any]:
    raw = _clean_text(audience_context or audience_pov or "")
    if raw == "N/A":
        raw = ""
    if not raw:
        label = "General Business User"
    else:
        key = raw.casefold()
        label = AUDIENCE_ALIASES.get(key)
        if not label:
            for alias, mapped in AUDIENCE_ALIASES.items():
                if alias in key:
                    label = mapped
                    break
        label = label or raw
    guidance = AUDIENCE_GUIDANCE.get(label, AUDIENCE_GUIDANCE["General Business User"])
    return {
        "audience": label,
        "raw_audience_input": raw or None,
        "primary_question": guidance["primary_question"],
        "narrative_angle": guidance["narrative_angle"],
        "preferred_outputs": list(guidance["preferred_outputs"]),
        "avoid": guidance["avoid"],
        "tone": ("executive, direct, evidence-backed" if label == "Management"
                 else "clear, action-oriented, evidence-backed"),
    }


def audience_clarification_payload(
    project_name: str | None = None,
    period_label: str | None = None,
) -> dict[str, Any]:
    target = f" untuk {project_name}" if project_name else ""
    period = f" periode {period_label}" if period_label else ""
    return {
        "success": False,
        "workflow_status": "NEEDS_AUDIENCE",
        "needs_clarification": True,
        "clarification_question": (
            f"Brand & Content Effectiveness Report{target}{period} ini dibuat "
            "untuk siapa? Pilih salah satu: Management, Marketing/Content, "
            "Social Media, Brand Team, Creative, tim Insight, Agency, "
            "atau Client/Stakeholder."
        ),
        "why_needed": (
            "Audience menentukan POV analisis, kedalaman narasi, bahasa, "
            "framing action plan, dan jenis evidence yang paling penting."
        ),
        "suggested_audiences": [
            "Management", "Marketing / Content Team", "Social Media Team",
            "Brand Team", "Creative Team", "Insight / Analyst Team",
            "Agency / Partner", "Client / Stakeholder",
        ],
        "example_user_reply": "Untuk tim Marketing/Content.",
    }


def apply_audience_to_package(
    package: dict[str, Any],
    audience_context: str | None = None,
    audience_pov: str | None = None,
) -> dict[str, Any]:
    """Tempelkan panduan audience TANPA mengubah data."""
    audience = normalize_audience_context(audience_context, audience_pov)
    package = dict(package)

    meta = dict(package.get("meta") or {})
    meta["audience_context"] = audience
    package["meta"] = meta

    style = dict(package.get("ppt_style_brief") or {})
    style["audience_context"] = audience
    style["tone"] = audience.get("tone")
    must_follow = list(style.get("must_follow") or [])
    must_follow.extend([
        f"Tulis untuk {audience['audience']}; jawab: {audience['primary_question']}",
        f"Prioritaskan: {', '.join(audience['preferred_outputs'])}.",
        f"Hindari: {audience['avoid']}.",
    ])
    seen: set[str] = set()
    style["must_follow"] = [m for m in must_follow if not (m in seen or seen.add(m))]
    package["ppt_style_brief"] = style

    instructions = list(package.get("claude_instructions") or [])
    instructions.insert(0, (
        f"Audience: {audience['audience']} | POV: {audience['primary_question']} "
        f"| Angle: {audience['narrative_angle']}"
    ))
    package["claude_instructions"] = instructions
    return package


# ======================================================================
#  ACTION PLAN — taxonomy BCE: Scale / Fix / Test
#  Diturunkan dari view yang READY. Bukti tipis -> prioritas turun.
# ======================================================================

ACTION_COLUMNS = [
    "Priority", "Action Type", "Focus Area", "Recommended Action",
    "Rationale", "Supporting Evidence", "Expected Impact",
]


def _action_row(priority: str, action_type: str, focus: str, action: str,
                rationale: str, evidence: str, impact: str) -> dict[str, str]:
    """8 field sesuai standard_action_plan_framework registry."""
    return {
        "Priority": priority,
        "Action Type": action_type,
        "Focus Area": focus,
        "Recommended Action": action,
        "Rationale": rationale,
        "Supporting Evidence": evidence,
        "Expected Impact": impact,
        "Owner/Next Step": "",
    }


def _build_action_plan(report_input: Mapping[str, Any],
                       coverage: Mapping[str, Any]) -> tuple[list[dict], list[str]]:
    actions: list[dict] = []
    caveats: list[str] = []

    kpi = _kpi(report_input)
    channels = _channel_stats(report_input)
    top_content = _rows(report_input, "qt_bce_top_performing_content")
    patterns = _rows(report_input, "ql_bce_top_content_patterns")

    # 1) SCALE — channel paling efisien.
    best = channels.get("best")
    if best:
        eff = round(best["_eff"], 1)
        volume = int(_num(best.get("Content Count")))
        thin = volume < MIN_POSTS_FOR_HIGH_PRIORITY
        if thin:
            caveats.append(
                f"Channel {best.get('Channel')} hanya punya {volume} konten "
                f"(< {MIN_POSTS_FOR_HIGH_PRIORITY}); efisiensinya belum konklusif."
            )
        actions.append(_action_row(
            "MEDIUM" if thin else "HIGH",
            "Test" if thin else "Scale",
            f"Channel: {best.get('Channel')}",
            (f"Uji tambah volume konten di {best.get('Channel')} sebelum scale penuh."
             if thin else
             f"Perbanyak produksi konten di {best.get('Channel')}."),
            f"Engagement per konten tertinggi ({eff}) dari {volume} konten.",
            f"qt_bce_channel_effectiveness: {best.get('Channel')} = {eff} "
            f"engagement/konten ({volume} konten).",
            "Efisiensi engagement lebih tinggi pada volume produksi yang sama.",
        ))

    # 2) FIX — channel yang membuang paling banyak effort.
    #    Bukan sekadar efisiensi terendah: channel dengan 4 konten buruk kurang
    #    merugikan dibanding channel dengan 84 konten buruk. Prioritaskan
    #    berdasarkan volume konten yang terbuang (volume x kekurangan efisiensi).
    avg = channels.get("avg_efficiency")
    underperformers = [
        row for row in channels["rows"]
        if row.get("_eff") is not None
        and avg
        and row["_eff"] < avg * LOW_ENGAGEMENT_RATIO
        and row is not best
    ]
    if underperformers:
        for row in underperformers:
            row["_waste"] = _num(row.get("Content Count")) * (avg - row["_eff"])
        worst = max(underperformers, key=lambda r: r["_waste"])
        volume = int(_num(worst.get("Content Count")))
        eff = round(worst["_eff"], 2)
        thin = volume < MIN_POSTS_FOR_HIGH_PRIORITY
        if thin:
            caveats.append(
                f"Channel {worst.get('Channel')} hanya punya {volume} konten "
                f"(< {MIN_POSTS_FOR_HIGH_PRIORITY}); temuan belum konklusif."
            )
        actions.append(_action_row(
            "MEDIUM" if thin else "HIGH",
            "Fix",
            f"Channel: {worst.get('Channel')}",
            f"Perbaiki format/pesan konten di {worst.get('Channel')}, "
            "atau kurangi alokasinya.",
            f"{volume} konten hanya menghasilkan {eff} engagement/konten, "
            f"jauh di bawah rata-rata {round(avg, 1)}.",
            f"qt_bce_channel_effectiveness: {worst.get('Channel')} = {eff} "
            f"vs rata-rata {round(avg, 1)} ({volume} konten).",
            "Menghentikan pemborosan produksi pada channel berkinerja rendah.",
        ))

    # 3) FIX — sentimen negatif tinggi.
    neg = _num(kpi.get("negative_pct"))
    if kpi.get("negative_pct") is not None and neg >= NEGATIVE_PCT_THRESHOLD:
        actions.append(_action_row(
            "HIGH", "Fix", "Brand sentiment",
            "Tinjau pesan konten dan siapkan respons untuk konten negatif.",
            f"Sentimen negatif mencapai {neg}% dari total konten.",
            f"qt_bce_exec_kpi_summary: Negative Sentiment % = {neg}.",
            "Penurunan porsi sentimen negatif pada periode berikutnya.",
        ))

    # 4) SCALE / TEST — pola konten pemenang.
    if patterns:
        top = patterns[0]
        label = top.get("Topic Extraction")
        safe = bool(coverage.get("safe_for_topic_conclusion"))
        if label:
            if not safe:
                caveats.append(
                    f"Pola konten berbasis topic dipakai sebagai sinyal awal "
                    f"({coverage.get('message')})."
                )
            actions.append(_action_row(
                "HIGH" if safe else "MEDIUM",
                "Scale" if safe else "Test",
                f"Tema: {label}",
                (f"Replikasi pola konten pada tema '{label}'." if safe else
                 f"Uji ulang tema '{label}' pada volume lebih besar."),
                f"Tema ini muncul pada konten dengan engagement tertinggi.",
                f"ql_bce_top_content_patterns: {label}.",
                "Replikasi pola yang sudah terbukti resonan.",
            ))
    elif top_content:
        actions.append(_action_row(
            "MEDIUM", "Test", "Pola konten",
            "Analisis manual konten teratas untuk menemukan pola yang bisa diulang.",
            "Topic enrichment belum tersedia sehingga pola belum bisa dihitung.",
            "qt_bce_top_performing_content (lihat kolom Content).",
            "Menemukan hook/format yang bisa direplikasi.",
        ))

    if not actions:
        actions.append(_action_row(
            "LOW", "Test", "Data readiness",
            "Lengkapi data sebelum mengambil keputusan konten.",
            "View pendukung belum cukup untuk menurunkan aksi yang bertanggung jawab.",
            "Lihat tabel View Readiness pada data preview.",
            "Menghindari keputusan berbasis bukti tipis.",
        ))
    return actions, caveats


# ======================================================================
#  DATA PREVIEW
# ======================================================================
def build_bce_report_data_preview(
    report_input_id: str,
    *,
    include_evidence_limit: int = 10,
    audience_context: str | None = None,
    audience_pov: str | None = None,
) -> dict[str, Any]:
    """Preview Task 1 untuk BCE sebelum PPT dibuat."""
    report_input = _load_report_input(report_input_id)
    outline = build_report_outline_from_id(report_input_id, allow_partial=True)

    ctx = _as_mapping(report_input.get("context"))
    period = _as_mapping(ctx.get("period"))
    kpi = _kpi(report_input)
    coverage = _topic_coverage(report_input)
    statuses = [_view_status(report_input, vid) for vid in ALL_VIEW_IDS]
    ready = sum(1 for s in statuses if s["status"] == "READY")

    readiness = "READY"
    if any(s["status"] != "READY" for s in statuses):
        readiness = "READY_WITH_LIMITATIONS"
    if not coverage["safe_for_topic_conclusion"]:
        readiness = "READY_WITH_TOPIC_CAVEAT"

    sentiment = _rows(report_input, "qt_bce_sentiment_distribution")
    channels = _rows(report_input, "qt_bce_channel_effectiveness")
    top_content = _rows(report_input, "qt_bce_top_performing_content")
    evidence = _rows(report_input, "ql_bce_brand_content_summary")

    markdown = f"""# Brand & Content Effectiveness Preview — {ctx.get('project_name')}

**Period:** {period.get('start_date')} → {period.get('end_date')}
**Readiness:** {readiness}
**View READY:** {ready}/{len(statuses)}
**Topic coverage:** {coverage['message']}

## 1. KPI Summary

| Metric | Value |
|---|---:|
| Total mentions | {_fmt_int(kpi['total_mentions'])} |
| Total engagement (interactions) | {_fmt_int(kpi['total_engagement'])} |
| Avg engagement per post | {_na(kpi['avg_engagement'])} |
| Positive sentiment | {_na(kpi['positive_pct'])}% |
| Negative sentiment | {_na(kpi['negative_pct'])}% |
| Potential reach | {_na(kpi['potential_reach'])} |

## 2. Sentiment Distribution

{_markdown_table(sentiment, ['Sentiment', 'Content Count', 'Content Share %', 'Total Engagement', 'Engagement Share %'], include_evidence_limit)}

## 3. Channel Effectiveness

{_markdown_table(channels, ['Channel', 'Content Count', 'Total Engagement', 'Avg Engagement per Content', 'Positive Sentiment %', 'Verified Account Content %'], include_evidence_limit)}

## 4. Top Performing Content

{_markdown_table(top_content, ['Channel', 'Content', 'Topic Extraction', 'Sentiment', 'Engagement', 'source_url'], include_evidence_limit)}

## 5. Supporting Evidence

{_markdown_table(evidence, ['Content', 'Sentiment', 'Topic Extraction', 'Engagement', 'source_url'], include_evidence_limit)}

## 6. View Readiness

{_markdown_table([{'view_id': s['view_id'], 'status': s['status'], 'rows': s['rows'], 'reason': s['reason']} for s in statuses], ['view_id', 'status', 'rows', 'reason'], len(statuses))}
"""

    return {
        "success": True,
        "preview_version": PREVIEW_VERSION,
        "report_input_id": report_input_id,
        "report_type_id": REPORT_TYPE_ID,
        "outline_id": outline.get("outline_id"),
        "outline_status": outline.get("outline_status"),
        "readiness": readiness,
        "context": dict(ctx),
        "kpi": kpi,
        "topic_coverage": coverage,
        "view_statuses": statuses,
        "limitations": list(report_input.get("limitations") or []),
        "action_taxonomy": list(ACTION_TYPES),
        "audience_context": (
            normalize_audience_context(audience_context, audience_pov)
            if (audience_context or audience_pov) else None
        ),
        "markdown": markdown,
    }


# ======================================================================
#  SLIDES — 9 section sesuai registry (Action Plan First)
# ======================================================================
CORE_STRUCTURE = [
    ("bce_header_report_identity", "Header / Report Identity", "header"),
    ("bce_executive_summary", "Executive Summary", "executive_summary"),
    ("bce_strategic_recommendations_and_action_plan",
     "Strategic Recommendations & Action Plan", "action_plan"),
    ("bce_brand_performance_snapshot", "Brand Performance Snapshot", "supporting_evidence"),
    ("bce_channel_effectiveness", "Channel Effectiveness", "supporting_evidence"),
    ("bce_content_format_and_theme_effectiveness",
     "Content Format & Theme Effectiveness", "supporting_evidence"),
    ("bce_top_performing_content_what_works",
     "Top Performing Content: What Works", "supporting_evidence"),
    ("bce_supporting_qualitative_evidence",
     "Supporting Qualitative Evidence", "supporting_evidence"),
    ("bce_footer_catatan_penutup", "Footer / Catatan Penutup", "supporting_evidence"),
]


def _slide(slide_id: str, title: str, subtitle: str,
           components: list[dict[str, Any]], speaker_notes: str = "") -> dict[str, Any]:
    return {"slide_id": slide_id, "title": title, "subtitle": subtitle,
            "components": components, "speaker_notes": speaker_notes}


def _kpi_cards(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    return {"type": "kpi_cards",
            "items": [{"label": label, "value": _na(value)} for label, value in pairs]}


def _table(title: str, rows: list[dict], columns: list[str],
           limit: int = 10, text_limit: int = 160) -> dict[str, Any]:
    if not rows:
        return {"type": "table", "title": title, "columns": columns, "rows": [],
                "status": "N/A", "note": "Data tidak tersedia pada report input."}
    clean = [
        {c: (_clean_text(row.get(c), text_limit) if c in _TEXT_COLUMNS
             else _na(row.get(c))) for c in columns}
        for row in rows[:limit]
    ]
    return {"type": "table", "title": title, "columns": columns,
            "rows": clean, "status": "READY"}


def _bullets(title: str, items: list[str]) -> dict[str, Any]:
    kept = [i for i in items if i]
    return {"type": "bullets", "title": title,
            "items": kept or ["N/A — data pendukung tidak tersedia."],
            "status": "READY" if kept else "N/A"}


def _evidence_list(rows: list[dict]) -> dict[str, Any]:
    """Evidence WAJIB membawa tautan sumber; tanpa itu jangan dipakai sebagai quote.

    URL di balik CTA natural (evidence_link_helper), bukan field source_url mentah,
    supaya lolos render_quality_gate.
    """
    try:
        from reporting.task2.renderers.evidence_link_helper import evidence_link
    except Exception:
        evidence_link = None

    items = []
    for row in rows:
        text = _clean_text(row.get("Content"), 180)
        if text == "N/A":
            continue
        item = {
            "text": text,
            "engagement": _na(row.get("Engagement")),
            "sentiment": _na(row.get("Sentiment")),
        }
        url = row.get("source_url")
        if url:
            link = None
            if evidence_link is not None:
                link = evidence_link(dict(row))
            item["evidence_link"] = link or {"label": "Buka link ↗", "url": str(url)}
        items.append(item)
    return {"type": "evidence_list", "items": items,
            "status": "READY" if items else "N/A"}


def _build_slides(report_input: Mapping[str, Any],
                  outline: Mapping[str, Any]) -> tuple[list[dict], dict[str, Any]]:
    ctx = _as_mapping(report_input.get("context"))
    period = _as_mapping(ctx.get("period"))
    kpi = _kpi(report_input)
    coverage = _topic_coverage(report_input)
    channels = _channel_stats(report_input)
    actions, caveats = _build_action_plan(report_input, coverage)

    project = ctx.get("project_name") or "N/A"
    period_label = f"{period.get('start_date')} → {period.get('end_date')}"

    sentiment = _rows(report_input, "qt_bce_sentiment_distribution")
    top_content = _rows(report_input, "qt_bce_top_performing_content")
    patterns = _rows(report_input, "ql_bce_top_content_patterns")
    by_sentiment = _rows(report_input, "ql_bce_top_content_sentiment")
    by_channel = _rows(report_input, "ql_bce_top_content_channel")
    summary = _rows(report_input, "ql_bce_brand_content_summary")

    best = channels.get("best")
    limitations = list(report_input.get("limitations") or [])

    slides = [
        _slide("bce_header_report_identity", "Brand & Content Effectiveness Report",
               f"{project} · {period_label}",
               [_kpi_cards([
                   ("Project", project),
                   ("Period", period_label),
                   ("Total Mentions", _fmt_int(kpi["total_mentions"])),
               ])],
               "Slide identitas. Semua angka berasal dari report input Task 1."),

        _slide("bce_executive_summary", "Executive Summary",
               "Performa konten, pola pemenang, dan yang perlu diperbaiki",
               [
                   _kpi_cards([
                       ("Total Mentions", _fmt_int(kpi["total_mentions"])),
                       ("Total Engagement", _fmt_int(kpi["total_engagement"])),
                       ("Avg Engagement/Post", kpi["avg_engagement"]),
                       ("Negative Sentiment", f"{_na(kpi['negative_pct'])}%"),
                   ]),
                   _bullets("Key Findings", [
                       (f"Channel paling efisien: {best.get('Channel')} "
                        f"({round(best['_eff'], 1)} engagement/konten).") if best else "",
                       (f"Sentimen positif {_na(kpi['positive_pct'])}%, "
                        f"negatif {_na(kpi['negative_pct'])}%."),
                       coverage["message"],
                   ]),
                   _evidence_list(summary),
               ],
               "Ringkasan eksekutif; jangan masuk detail tabel."),

        _slide("bce_strategic_recommendations_and_action_plan",
               "Strategic Recommendations & Action Plan",
               "Aksi Scale / Fix / Test berbasis evidence",
               [
                   _table("Action Plan", actions, ACTION_COLUMNS, limit=8, text_limit=200),
                   _bullets("Caveats", caveats or ["Tidak ada caveat tambahan."]),
               ],
               "Action Plan First: muncul tepat setelah Executive Summary. "
               "Setiap aksi wajib punya Supporting Evidence dari view Task 1. "
               f"Action Type hanya: {', '.join(ACTION_TYPES)}."),

        _slide("bce_brand_performance_snapshot", "Brand Performance Snapshot",
               "KPI dan distribusi sentimen",
               [
                   _kpi_cards([
                       ("Total Mentions", _fmt_int(kpi["total_mentions"])),
                       ("Total Engagement", _fmt_int(kpi["total_engagement"])),
                       ("Potential Reach", kpi["potential_reach"]),
                       ("Avg Engagement/Post", kpi["avg_engagement"]),
                   ]),
                   _table("Sentiment Distribution", sentiment,
                          ["Sentiment", "Content Count", "Content Share %",
                           "Total Engagement", "Engagement Share %"]),
               ],
               "Suggested visual: KPI cards besar untuk 4 metrik, plus donut/pie "
               "distribusi sentimen memakai Content Count. Render sebagai chart "
               "bila baris tersedia; jangan text-only. Snapshot performa brand "
               "pada periode ini."),

        _slide("bce_channel_effectiveness", "Channel Effectiveness",
               "Efisiensi engagement per channel",
               [
                   _table("Channel Effectiveness", channels["rows"],
                          ["Channel", "Content Count", "Total Engagement",
                           "Avg Engagement per Content", "Positive Sentiment %",
                           "Negative Sentiment %", "Verified Account Content %"]),
                   _bullets("Reading Guide", [
                       "Avg Engagement per Content = efisiensi channel.",
                       "Volume tinggi + efisiensi rendah = kandidat Fix.",
                   ]),
               ],
               "Suggested visual: horizontal bar chart Avg Engagement per "
               "Content per channel (efisiensi), urut menurun; tampilkan Content "
               "Count sebagai konteks volume. Render sebagai chart bila baris "
               "tersedia; jangan text-only. Bandingkan efisiensi, bukan hanya "
               "volume."),

        _slide("bce_content_format_and_theme_effectiveness",
               "Content Format & Theme Effectiveness",
               "Tema yang resonan (format N/A: Media Type tidak tersedia)",
               [
                   _table("Top Content Patterns", patterns,
                          ["Topic Extraction", "Content", "Channel", "Engagement"]),
                   _bullets("Topic Coverage", [coverage["message"]]),
                   _bullets("Catatan", [
                       "Format/Media Type tidak tersedia pada canonical post, "
                       "sehingga efektivitas per format ditandai N/A.",
                   ]),
               ],
               "Suggested visual: horizontal bar chart tema/topic berdasarkan "
               "Engagement, urut menurun. Render sebagai chart bila baris "
               "tersedia; jangan text-only. Topic berasal dari taxonomy LLM "
               "yang sudah terkurasi."),

        _slide("bce_top_performing_content_what_works",
               "Top Performing Content: What Works",
               "Konten dengan engagement tertinggi",
               [
                   _table("Top Performing Content", top_content,
                          ["Channel", "Content", "Topic Extraction", "Sentiment",
                           "Engagement", "Views"]),
                   _evidence_list(by_channel),
               ],
               "Suggested visual: horizontal bar chart Top Performing Content "
               "berdasarkan Engagement, urut menurun. Render sebagai chart bila "
               "baris tersedia. Setiap konten wajib menyertakan tautan sumber "
               "di balik CTA natural."),

        _slide("bce_supporting_qualitative_evidence",
               "Supporting Qualitative Evidence",
               "Contoh konten per sentimen dan channel",
               [
                   _evidence_list(by_sentiment),
                   _table("Top Content per Channel", by_channel,
                          ["Channel", "Content", "Engagement"]),
               ],
               "Evidence tanpa tautan sumber tidak boleh dijadikan quote."),

        _slide("bce_footer_catatan_penutup", "Footer / Catatan Penutup",
               "Scope, keterbatasan, dan metodologi",
               [
                   _bullets("Scope", [
                       f"Project: {project}.",
                       f"Periode: {period_label}.",
                       f"Channels: {', '.join(ctx.get('channels') or []) or 'semua channel'}.",
                   ]),
                   _bullets("Limitations", limitations or ["Tidak ada limitation tercatat."]),
                   _bullets("Metodologi", [
                       "Engagement = Interactions canonical (bukan Views).",
                       "Topic berasal dari klasifikasi LLM atas Title + Content.",
                       "Komponen berstatus N/A ditampilkan apa adanya, tidak dikarang.",
                   ]),
               ],
               "Penutup: transparansi scope & keterbatasan."),
    ]

    meta = {
        "project_name": project,
        "period": dict(period),
        "kpi": kpi,
        "topic_coverage": coverage,
        "best_channel": best.get("Channel") if best else None,
        "action_count": len(actions),
        "caveats": caveats,
        "outline_id": outline.get("outline_id"),
        "outline_status": outline.get("outline_status"),
    }
    return slides, meta


def build_bce_report_package(
    report_input_id: str,
    *,
    audience_context: str | None = None,
    audience_pov: str | None = None,
) -> dict[str, Any]:
    """Paket siap-PPT untuk BCE. TIDAK membuat file .pptx."""
    report_input = _load_report_input(report_input_id)
    outline = build_report_outline_from_id(report_input_id, allow_partial=True)
    slides, meta = _build_slides(report_input, outline)

    package = {
        "success": True,
        "package_version": PACKAGE_VERSION,
        "report_input_id": report_input_id,
        "report_type_id": REPORT_TYPE_ID,
        "slides": slides,
        "meta": meta,
        "limitations": list(report_input.get("limitations") or []),
        "action_taxonomy": list(ACTION_TYPES),
        "ppt_style_brief": {
            "format": "client-facing PPTX",
            "tone": "executive, evidence-first",
            "visual_direction": (
                "executive card-based deck; large KPI cards; render charts when "
                "numeric rows exist (donut untuk sentimen, horizontal bar untuk "
                "channel efficiency / topic / top content); natural clickable "
                "evidence CTAs; no raw URL/audit code clutter"
            ),
            "structure": "Action Plan First (Header → Exec Summary → Action Plan → Evidence)",
            "must_follow": [
                "Jangan mengarang metrik, quote, topic, atau URL.",
                "Komponen berstatus N/A tetap ditampilkan sebagai N/A.",
                "Setiap quote wajib menyertakan tautan sumber di balik CTA natural.",
                "Ikuti speaker_notes 'Suggested visual'; render chart bila baris "
                "numerik tersedia, jangan text-only.",
                "Action Plan memakai 8 kolom standard_action_plan_framework.",
                f"Action Type hanya dari taxonomy: {', '.join(ACTION_TYPES)}.",
            ],
        },
    }

    if audience_context or audience_pov:
        package = apply_audience_to_package(package, audience_context, audience_pov)

    try:
        from reporting.task2.renderers.render_quality_gate import (
            apply_render_package_quality_gate,
        )
        package = apply_render_package_quality_gate(package, report_type=REPORT_TYPE_ID)
    except Exception:
        pass
    return package


__all__ = [
    "build_bce_report_data_preview",
    "build_bce_report_package",
    "normalize_audience_context",
    "audience_clarification_payload",
    "apply_audience_to_package",
    "BCERendererError",
    "REPORT_TYPE_ID",
    "ACTION_TYPES",
    "PREVIEW_VERSION",
    "PACKAGE_VERSION",
    "CORE_STRUCTURE",
    "AUDIENCE_GUIDANCE",
]
