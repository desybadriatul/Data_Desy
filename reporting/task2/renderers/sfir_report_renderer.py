"""
Task 2 renderer: Spokesperson Intelligence Report (SFIR).

Pola sama dengan industry_trend & bce renderer:
- Renderer TIDAK membuat .pptx. Dia menghasilkan paket siap-PPT.
- Struktur = section_order registry (9 section, Action Plan First).
- Tidak mengarang metrik, nama, kutipan, atau URL.
- View NOT_AVAILABLE dirender sebagai N/A, bukan disembunyikan.

CATATAN KHUSUS SFIR
-------------------
Report ini menyebut NAMA ORANG SUNGGUHAN. Karena itu:
- Hanya juru bicara yang `represented_campaign`-nya cocok dengan brand yang
  boleh disebut juru bicara brand. Builder Task 1 sudah menyaringnya.
- Setiap kutipan wajib membawa source_url. Tanpa itu, jangan dikutip.
- Kalau bukti tipis (1-2 artikel), prioritas aksi diturunkan ke Monitor Exposure.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

from reporting.storage.report_input_store import get_report_input
from reporting.task2.report_outline_builder import build_report_outline_from_id

REPORT_TYPE_ID = "spokesperson_intelligence"
PREVIEW_VERSION = "sfir_data_preview_v1"
PACKAGE_VERSION = "sfir_ppt_package_v1"

# SALIN PERSIS dari registry -> action_taxonomy_by_report_type.
ACTION_TYPES = (
    "Amplify",
    "Contain Risk",
    "Clarify Message",
    "Prioritize Media Channel",
    "Monitor Exposure",
)

# Ambang keputusan. Bukti tipis menurunkan prioritas, bukan menghapus sinyal.
MIN_ARTICLES_FOR_HIGH_PRIORITY = 3
NEGATIVE_RATIO_THRESHOLD = 0.3
SINGLE_VOICE_RISK_RATIO = 0.8   # >80% eksposur dari satu orang = risiko konsentrasi


class SFIRRendererError(RuntimeError):
    """Raised when Task 2 cannot safely build an SFIR package."""


# ----------------------------------------------------------------------
#  Helper
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
                 "Rationale", "Supporting Evidence", "Expected Impact", "Role"}


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
    "qt_sfir_kpi_overview",
    "qt_sfir_top5_spokesperson_rank",
    "qt_sfir_sentiment_distribution_by_spokesperson",
    "qt_sfir_channel_effectiveness_by_spokesperson",
    "ql_sfir_exposure_quotes_and_analysis",
    "ql_sfir_issue_cards_per_spokesperson",
]


def _kpi(report_input: Mapping[str, Any]) -> dict[str, Any]:
    rows = _rows(report_input, "qt_sfir_kpi_overview")
    row = rows[0] if rows else {}
    return {
        "spokesperson_count": int(_num(row.get("Spokesperson"))),
        "ad_value": row.get("Ad Value"),
        "article_count": int(_num(row.get("Content"))),
        "media_count": row.get("Media Name"),
    }


def _sentiment_summary(report_input: Mapping[str, Any]) -> dict[str, Any]:
    rows = _rows(report_input, "qt_sfir_sentiment_distribution_by_spokesperson")
    counter: Counter[str] = Counter()
    for row in rows:
        counter[str(row.get("Sentiment") or "unclassified").casefold()] += int(
            _num(row.get("Content")))
    total = sum(counter.values())
    if not total:
        return {"rows": rows, "total": 0, "positive_pct": None,
                "negative_pct": None, "net_sentiment": None}
    pos = counter.get("positive", 0)
    neg = counter.get("negative", 0)
    return {
        "rows": rows,
        "total": total,
        "positive_pct": round(100 * pos / total, 1),
        "negative_pct": round(100 * neg / total, 1),
        "net_sentiment": round(100 * (pos - neg) / total, 1),
    }


def _spokesperson_risk(report_input: Mapping[str, Any]) -> dict[str, Any]:
    """Deteksi konsentrasi suara: apakah satu orang mendominasi eksposur?"""
    rows = _rows(report_input, "qt_sfir_top5_spokesperson_rank")
    if not rows:
        return {"dominant": None, "share": None, "concentrated": False}
    total = sum(_num(r.get("Content")) for r in rows)
    if not total:
        return {"dominant": None, "share": None, "concentrated": False}
    top = max(rows, key=lambda r: _num(r.get("Content")))
    share = _num(top.get("Content")) / total
    return {
        "dominant": top.get("Spokesperson"),
        "role": top.get("Role"),
        "share": round(100 * share, 1),
        "concentrated": share >= SINGLE_VOICE_RISK_RATIO and len(rows) > 1,
    }


def _load_report_input(report_input_id: str) -> Mapping[str, Any]:
    if not isinstance(report_input_id, str) or not report_input_id.strip():
        raise SFIRRendererError("report_input_id wajib diisi.")
    report_input = get_report_input(report_input_id.strip())
    if report_input is None:
        raise SFIRRendererError(f"report_input_id '{report_input_id}' tidak ditemukan.")
    if report_input.get("report_type_id") != REPORT_TYPE_ID:
        raise SFIRRendererError(
            f"Renderer ini hanya untuk {REPORT_TYPE_ID}, "
            f"bukan {report_input.get('report_type_id')}."
        )
    if _as_mapping(report_input.get("validation")).get("status") == "FAIL":
        raise SFIRRendererError("report_input validation FAIL; tidak aman dirender.")
    return report_input


# ======================================================================
#  AUDIENCE CONTEXT — SFIR pembacanya PR / Corcom / Manajemen
#  Audience mengubah CARA BERCERITA, bukan angkanya.
# ======================================================================

AUDIENCE_ALIASES = {
    "management": "Management",
    "manajemen": "Management",
    "executive": "Management",
    "direksi": "CEO / Board",
    "ceo": "CEO / Board",
    "board": "CEO / Board",
    "pr": "PR / Corporate Communications",
    "corcom": "PR / Corporate Communications",
    "humas": "PR / Corporate Communications",
    "public relations": "PR / Corporate Communications",
    "corporate communications": "PR / Corporate Communications",
    "media relations": "Media Relations Team",
    "media": "Media Relations Team",
    "spokesperson": "Spokesperson / Juru Bicara",
    "juru bicara": "Spokesperson / Juru Bicara",
    "insight": "Insight / Analyst Team",
    "analyst": "Insight / Analyst Team",
    "legal": "Legal / Risk Team",
    "risk": "Legal / Risk Team",
}

AUDIENCE_GUIDANCE = {
    "Management": {
        "primary_question": "Apakah suara brand kita terwakili dengan baik di media?",
        "narrative_angle": "kekuatan suara brand, risiko reputasi, keputusan komunikasi",
        "preferred_outputs": [
            "siapa yang paling sering bicara untuk brand",
            "risiko konsentrasi suara",
            "action plan komunikasi",
        ],
        "avoid": "detail teknis metrik media",
    },
    "CEO / Board": {
        "primary_question": "Apakah posisi brand kita di ruang publik aman?",
        "narrative_angle": "risiko reputasi strategis, otoritas juru bicara",
        "preferred_outputs": [
            "satu kalimat posture reputasi",
            "risiko utama",
            "keputusan tingkat direksi",
        ],
        "avoid": "tabel mentah dan detail outlet",
    },
    "PR / Corporate Communications": {
        "primary_question": "Siapa yang bicara untuk kita, dan apa yang perlu diperbaiki?",
        "narrative_angle": "efektivitas juru bicara, pesan yang tersampaikan, isu yang muncul",
        "preferred_outputs": [
            "ranking juru bicara beserta eksposurnya",
            "kutipan lengkap dengan source_url",
            "isu bersentimen negatif",
            "action plan Amplify/Contain Risk/Clarify Message",
        ],
        "avoid": "analisis finansial",
    },
    "Media Relations Team": {
        "primary_question": "Outlet mana yang paling efektif mengangkat suara kita?",
        "narrative_angle": "efektivitas outlet, distribusi eksposur, peluang placement",
        "preferred_outputs": [
            "outlet dengan Ad Value tertinggi",
            "juru bicara per outlet",
            "rekomendasi prioritas channel",
        ],
        "avoid": "narasi strategi korporat",
    },
    "Spokesperson / Juru Bicara": {
        "primary_question": "Bagaimana pesan saya diterima media?",
        "narrative_angle": "kutipan yang terpakai, sentimen, konsistensi pesan",
        "preferred_outputs": [
            "kutipan yang dimuat beserta konteksnya",
            "sentimen artikel tempat kutipan muncul",
            "saran penyesuaian pesan",
        ],
        "avoid": "perbandingan antar juru bicara yang menghakimi",
    },
    "Insight / Analyst Team": {
        "primary_question": "Seberapa kuat evidence di balik kesimpulan ini?",
        "narrative_angle": "coverage enrichment, kualitas atribusi, caveat metodologi",
        "preferred_outputs": [
            "status tiap view dan alasannya",
            "coverage cache enrichment",
            "audit trail source_url",
        ],
        "avoid": "rekomendasi normatif tanpa dukungan data",
    },
    "Legal / Risk Team": {
        "primary_question": "Apakah ada pernyataan yang berisiko secara hukum atau reputasi?",
        "narrative_angle": "pernyataan sensitif, isu negatif, potensi eskalasi",
        "preferred_outputs": [
            "kutipan bersentimen negatif",
            "isu yang berpotensi eskalasi",
            "source_url untuk verifikasi",
        ],
        "avoid": "metrik marketing",
    },
    "General Business User": {
        "primary_question": "Siapa juru bicara brand kita dan bagaimana kinerjanya?",
        "narrative_angle": "ringkasan juru bicara, eksposur, sentimen, aksi",
        "preferred_outputs": [
            "ranking juru bicara",
            "kutipan dengan source_url",
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
        "tone": ("executive, direct, evidence-backed"
                 if label in {"Management", "CEO / Board"}
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
            f"Spokesperson Intelligence Report{target}{period} ini dibuat untuk "
            "siapa? Pilih salah satu: Management, CEO/Board, PR/Corcom, "
            "Media Relations, Juru Bicara, tim Insight, atau Legal/Risk."
        ),
        "why_needed": (
            "Audience menentukan POV analisis, kedalaman narasi, framing action "
            "plan, dan jenis evidence yang paling penting."
        ),
        "suggested_audiences": [
            "Management", "CEO / Board", "PR / Corporate Communications",
            "Media Relations Team", "Spokesperson / Juru Bicara",
            "Insight / Analyst Team", "Legal / Risk Team",
        ],
        "example_user_reply": "Untuk tim PR/Corcom.",
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
#  ACTION PLAN — taxonomy SFIR (5 tipe dari registry)
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


def _build_action_plan(report_input: Mapping[str, Any]) -> tuple[list[dict], list[str]]:
    actions: list[dict] = []
    caveats: list[str] = []

    kpi = _kpi(report_input)
    top = _rows(report_input, "qt_sfir_top5_spokesperson_rank")
    sentiment = _sentiment_summary(report_input)
    by_sp = _rows(report_input, "qt_sfir_sentiment_distribution_by_spokesperson")
    channels = _rows(report_input, "qt_sfir_channel_effectiveness_by_spokesperson")
    risk = _spokesperson_risk(report_input)

    # 1) AMPLIFY — juru bicara dengan eksposur tertinggi.
    if top:
        best = top[0]
        name = best.get("Spokesperson")
        articles = int(_num(best.get("Content")))
        thin = articles < MIN_ARTICLES_FOR_HIGH_PRIORITY
        if thin:
            caveats.append(
                f"{name} baru muncul di {articles} artikel "
                f"(< {MIN_ARTICLES_FOR_HIGH_PRIORITY}); belum konklusif."
            )
        actions.append(_action_row(
            "MEDIUM" if thin else "HIGH",
            "Monitor Exposure" if thin else "Amplify",
            f"Spokesperson: {name}",
            (f"Pantau eksposur {name} sebelum menambah penugasan media."
             if thin else
             f"Perbanyak kesempatan bicara untuk {name} di isu prioritas."),
            f"Eksposur tertinggi: {articles} artikel, Ad Value "
            f"{_na(best.get('Ad Value'))}.",
            f"qt_sfir_top5_spokesperson_rank: {name} = {articles} artikel.",
            "Penguatan suara brand melalui juru bicara yang sudah terbukti dimuat.",
        ))

    # 2) CONTAIN RISK — konsentrasi suara pada satu orang.
    if risk["concentrated"]:
        actions.append(_action_row(
            "HIGH", "Contain Risk", "Distribusi juru bicara",
            "Siapkan juru bicara cadangan untuk mengurangi ketergantungan.",
            f"{risk['share']}% eksposur berasal dari {risk['dominant']} saja.",
            f"qt_sfir_top5_spokesperson_rank: {risk['dominant']} = "
            f"{risk['share']}% dari total artikel.",
            "Mengurangi risiko reputasi bila satu juru bicara tidak tersedia.",
        ))

    # 3) CONTAIN RISK — juru bicara dengan sentimen negatif dominan.
    neg: dict[str, int] = {}
    tot: dict[str, int] = {}
    for row in by_sp:
        name = str(row.get("Spokesperson") or "")
        count = int(_num(row.get("Content")))
        tot[name] = tot.get(name, 0) + count
        if str(row.get("Sentiment") or "").casefold() == "negative":
            neg[name] = neg.get(name, 0) + count
    risky = [(n, neg[n] / tot[n], tot[n]) for n in neg if tot.get(n)]
    risky.sort(key=lambda item: (item[1], item[2]), reverse=True)
    if risky and risky[0][1] >= NEGATIVE_RATIO_THRESHOLD:
        name, ratio, volume = risky[0]
        pct = round(ratio * 100)
        thin = volume < MIN_ARTICLES_FOR_HIGH_PRIORITY
        if thin:
            caveats.append(
                f"Sentimen negatif pada {name} berasal dari {volume} artikel saja; "
                "diperlakukan sebagai sinyal awal."
            )
        actions.append(_action_row(
            "MEDIUM" if thin else "HIGH",
            "Monitor Exposure" if thin else "Clarify Message",
            f"Spokesperson: {name}",
            (f"Pantau pemberitaan yang mengutip {name}."
             if thin else
             f"Tinjau dan perjelas pesan yang disampaikan {name}."),
            f"{pct}% artikel yang mengutip {name} bersentimen negatif "
            f"({volume} artikel).",
            f"qt_sfir_sentiment_distribution_by_spokesperson: {name} "
            f"negative {pct}%.",
            "Perbaikan penerimaan pesan pada periode berikutnya.",
        ))

    # 4) PRIORITIZE MEDIA CHANNEL — outlet dengan eksposur terbanyak.
    outlet_count: Counter[str] = Counter()
    for row in channels:
        outlet = str(row.get("Media Name") or "").strip()
        if outlet and outlet != "(tidak diketahui)":
            outlet_count[outlet] += int(_num(row.get("Content")))
    if outlet_count:
        outlet, count = outlet_count.most_common(1)[0]
        actions.append(_action_row(
            "MEDIUM", "Prioritize Media Channel", f"Outlet: {outlet}",
            f"Prioritaskan {outlet} untuk penempatan pesan berikutnya.",
            f"{outlet} memuat {count} kutipan juru bicara brand.",
            f"qt_sfir_channel_effectiveness_by_spokesperson: {outlet} = "
            f"{count} kutipan.",
            "Eksposur lebih efisien lewat outlet yang sudah responsif.",
        ))

    # 5) Fallback — tidak cukup bukti.
    if not actions:
        actions.append(_action_row(
            "LOW", "Monitor Exposure", "Data readiness",
            "Lanjutkan monitoring; perkuat coverage enrichment sebelum aksi.",
            "View pendukung belum cukup untuk menurunkan aksi yang bertanggung jawab.",
            "Lihat tabel View Readiness pada data preview.",
            "Menghindari keputusan berbasis bukti tipis.",
        ))

    if kpi["spokesperson_count"] == 1:
        caveats.append(
            "Hanya satu juru bicara terdeteksi mewakili brand pada periode ini. "
            "Kesimpulan perbandingan antar juru bicara tidak tersedia."
        )
    return actions, caveats


# ======================================================================
#  DATA PREVIEW
# ======================================================================
def build_sfir_report_data_preview(
    report_input_id: str,
    *,
    include_evidence_limit: int = 10,
    audience_context: str | None = None,
    audience_pov: str | None = None,
) -> dict[str, Any]:
    report_input = _load_report_input(report_input_id)
    outline = build_report_outline_from_id(report_input_id, allow_partial=True)

    ctx = _as_mapping(report_input.get("context"))
    period = _as_mapping(ctx.get("period"))
    scope = _as_mapping(report_input.get("scope"))
    kpi = _kpi(report_input)
    sentiment = _sentiment_summary(report_input)
    risk = _spokesperson_risk(report_input)
    statuses = [_view_status(report_input, vid) for vid in ALL_VIEW_IDS]
    ready = sum(1 for s in statuses if s["status"] == "READY")

    readiness = "READY"
    if any(s["status"] != "READY" for s in statuses):
        readiness = "READY_WITH_LIMITATIONS"
    if kpi["spokesperson_count"] <= 1:
        readiness = "READY_WITH_THIN_EVIDENCE"
    if ready == 0:
        readiness = "NOT_RENDERABLE"

    top = _rows(report_input, "qt_sfir_top5_spokesperson_rank")
    quotes = _rows(report_input, "ql_sfir_exposure_quotes_and_analysis")
    channels = _rows(report_input, "qt_sfir_channel_effectiveness_by_spokesperson")

    markdown = f"""# Spokesperson Intelligence Preview — {ctx.get('project_name')}

**Period:** {period.get('start_date')} → {period.get('end_date')}
**Channel:** {scope.get('enforced_channel', 'Online Media')}
**Readiness:** {readiness}
**View READY:** {ready}/{len(statuses)}

## 1. KPI Overview

| Metric | Value |
|---|---:|
| Juru bicara brand | {_fmt_int(kpi['spokesperson_count'])} |
| Artikel | {_fmt_int(kpi['article_count'])} |
| Outlet media | {_na(kpi['media_count'])} |
| Ad Value | {_na(kpi['ad_value'])} |
| Net sentiment | {_na(sentiment['net_sentiment'])} |

## 2. Top Spokesperson

{_markdown_table(top, ['Spokesperson', 'Role', 'Content', 'Ad Value', 'Media Name'], include_evidence_limit)}

## 3. Sentiment per Spokesperson

{_markdown_table(sentiment['rows'], ['Spokesperson', 'Sentiment', 'Content'], 15)}

## 4. Outlet Media

{_markdown_table(channels, ['Spokesperson', 'Media Name', 'Content'], 15)}

## 5. Kutipan (evidence)

{_markdown_table(quotes, ['Spokesperson', 'Role', 'Content', 'Media Name', 'source_url'], include_evidence_limit)}

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
        "sentiment": sentiment,
        "concentration_risk": risk,
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
    ("sfir_header_identitas_report", "Header / Identitas Report", "header"),
    ("sfir_executive_summary", "Executive Summary", "executive_summary"),
    ("sfir_spokesperson_action_plan", "Spokesperson Action Plan", "action_plan"),
    ("sfir_top_spokesperson_landscape", "Top Spokesperson Landscape", "supporting_evidence"),
    ("sfir_sentiment_and_issue_association", "Sentiment & Issue Association", "supporting_evidence"),
    ("sfir_channel_effectiveness", "Channel Effectiveness", "supporting_evidence"),
    ("sfir_exposure_analysis", "Exposure Analysis", "supporting_evidence"),
    ("sfir_key_findings", "Key Findings", "supporting_evidence"),
    ("sfir_footer", "Footer", "supporting_evidence"),
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


def _quote_list(rows: list[dict]) -> dict[str, Any]:
    """Kutipan WAJIB membawa source_url. Tanpa itu, jangan ditampilkan."""
    items = []
    for row in rows:
        text = _clean_text(row.get("Content"), 200)
        url = row.get("source_url")
        if text == "N/A" or not url:
            continue
        items.append({
            "spokesperson": _na(row.get("Spokesperson")),
            "role": _na(row.get("Role")),
            "organization": _na(row.get("Organization")),
            "text": text,
            "media_name": _na(row.get("Media Name")),
            "confidence": _na(row.get("Confidence")),
            "source_url": str(url),
        })
    return {"type": "quote_list", "items": items,
            "status": "READY" if items else "N/A",
            "note": None if items else "Kutipan tanpa source_url tidak ditampilkan."}


def _build_slides(report_input: Mapping[str, Any],
                  outline: Mapping[str, Any]) -> tuple[list[dict], dict[str, Any]]:
    ctx = _as_mapping(report_input.get("context"))
    period = _as_mapping(ctx.get("period"))
    scope = _as_mapping(report_input.get("scope"))
    kpi = _kpi(report_input)
    sentiment = _sentiment_summary(report_input)
    risk = _spokesperson_risk(report_input)
    actions, caveats = _build_action_plan(report_input)

    project = ctx.get("project_name") or "N/A"
    brand = scope.get("spokesperson_brand_filter") or project
    period_label = f"{period.get('start_date')} → {period.get('end_date')}"
    channel = scope.get("enforced_channel", "Online Media")

    top = _rows(report_input, "qt_sfir_top5_spokesperson_rank")
    quotes = _rows(report_input, "ql_sfir_exposure_quotes_and_analysis")
    channels = _rows(report_input, "qt_sfir_channel_effectiveness_by_spokesperson")
    limitations = list(report_input.get("limitations") or [])
    sampling = _as_mapping(scope.get("spokesperson_sampling"))

    lead = top[0].get("Spokesperson") if top else None

    slides = [
        _slide("sfir_header_identitas_report", "Spokesperson Intelligence Report",
               f"{project} · {period_label}",
               [_kpi_cards([
                   ("Project", project),
                   ("Period", period_label),
                   ("Channel", channel),
                   ("Juru bicara brand", _fmt_int(kpi["spokesperson_count"])),
               ])],
               "Slide identitas. Semua nama & kutipan berasal dari cache "
               "spokesperson enrichment, bukan dikarang."),

        _slide("sfir_executive_summary", "Executive Summary",
               "Siapa yang bicara untuk brand, dan bagaimana diterimanya",
               [
                   _kpi_cards([
                       ("Juru bicara brand", _fmt_int(kpi["spokesperson_count"])),
                       ("Artikel", _fmt_int(kpi["article_count"])),
                       ("Outlet media", kpi["media_count"]),
                       ("Net sentiment", sentiment["net_sentiment"]),
                   ]),
                   _bullets("Key Findings", [
                       f"Juru bicara paling terekspos: {lead}." if lead else "",
                       (f"{risk['share']}% eksposur terkonsentrasi pada "
                        f"{risk['dominant']}.") if risk["concentrated"] else "",
                       (f"Sentimen positif {sentiment['positive_pct']}%, "
                        f"negatif {sentiment['negative_pct']}%.")
                       if sentiment["total"] else "",
                   ]),
                   _quote_list(quotes[:3]),
               ],
               "Ringkasan eksekutif; jangan masuk detail tabel."),

        _slide("sfir_spokesperson_action_plan", "Spokesperson Action Plan",
               "Aksi prioritas berbasis evidence",
               [
                   _table("Action Plan", actions, ACTION_COLUMNS, limit=8, text_limit=200),
                   _bullets("Caveats", caveats or ["Tidak ada caveat tambahan."]),
               ],
               "Action Plan First: muncul tepat setelah Executive Summary. "
               f"Action Type hanya dari taxonomy: {', '.join(ACTION_TYPES)}."),

        _slide("sfir_top_spokesperson_landscape", "Top Spokesperson Landscape",
               f"Juru bicara yang mewakili {brand}",
               [
                   _table("Top Spokesperson", top,
                          ["Spokesperson", "Role", "Content", "Ad Value", "Media Name"]),
                   _bullets("Reading Guide", [
                       "Hanya juru bicara yang berbicara MEWAKILI brand yang "
                       "dihitung di sini.",
                       "Nama lain yang muncul di artikel ber-tag brand tercatat "
                       "pada Limitations, bukan di tabel ini.",
                   ]),
               ],
               "Jangan menambahkan nama yang tidak ada di tabel."),

        _slide("sfir_sentiment_and_issue_association",
               "Sentiment & Issue Association",
               "Sentimen artikel tempat juru bicara dikutip",
               [
                   _table("Sentiment per Spokesperson", sentiment["rows"],
                          ["Spokesperson", "Sentiment", "Content"], limit=15),
                   _bullets("Catatan", [
                       "Issue cards per spokesperson N/A: topic enrichment untuk "
                       f"{channel} belum tersedia.",
                   ]),
               ],
               "Sentimen berasal dari artikel, bukan penilaian atas pribadi."),

        _slide("sfir_channel_effectiveness", "Channel Effectiveness",
               "Outlet media yang memuat juru bicara",
               [
                   _table("Spokesperson per Outlet", channels,
                          ["Spokesperson", "Channel", "Media Name", "Content"], limit=15),
                   _bullets("Reading Guide", [
                       f"Seluruh artikel berasal dari {channel}; perbandingan "
                       "bermakna adalah antar outlet media.",
                   ]),
               ],
               "Channel selalu Online Media; yang dibandingkan outlet."),

        _slide("sfir_exposure_analysis", "Exposure Analysis",
               "Kutipan yang dimuat beserta sumbernya",
               [
                   _quote_list(quotes),
                   _bullets("Sampling", [
                       (f"Artikel eligible: {sampling.get('eligible_count')}, "
                        f"di-enrich: {sampling.get('selected_count')}.")
                       if sampling else "",
                   ]),
               ],
               "Setiap kutipan wajib menyertakan source_url."),

        _slide("sfir_key_findings", "Key Findings",
               "Implikasi bagi strategi komunikasi",
               [
                   _bullets("Findings", [
                       f"{lead} adalah suara utama brand di media." if lead else "",
                       (f"Ketergantungan tinggi pada satu juru bicara "
                        f"({risk['share']}%).") if risk["concentrated"] else "",
                       (f"Sentimen negatif {sentiment['negative_pct']}% perlu "
                        "diawasi.") if sentiment["negative_pct"] else "",
                       f"Eksposur tersebar di {_na(kpi['media_count'])} outlet media.",
                   ]),
                   _quote_list(quotes[:2]),
               ],
               "Findings harus merujuk balik ke Action Plan."),

        _slide("sfir_footer", "Footer", "Scope, keterbatasan, dan metodologi",
               [
                   _bullets("Scope", [
                       f"Project: {project}.",
                       f"Brand filter: {brand}.",
                       f"Periode: {period_label}.",
                       f"Channel: {channel} (SFIR tidak berlaku untuk media sosial).",
                   ]),
                   _bullets("Limitations", limitations or ["Tidak ada limitation tercatat."]),
                   _bullets("Metodologi", [
                       "Juru bicara diekstraksi LLM dari artikel Online Media.",
                       "Hanya orang bernama yang dikutip; perusahaan & lembaga "
                       "tidak dihitung sebagai juru bicara.",
                       "Hanya yang berbicara mewakili brand yang masuk ranking.",
                       "Komponen berstatus N/A ditampilkan apa adanya.",
                   ]),
               ],
               "Penutup: transparansi scope & keterbatasan."),
    ]

    meta = {
        "project_name": project,
        "brand_filter": brand,
        "period": dict(period),
        "channel": channel,
        "kpi": kpi,
        "sentiment": sentiment,
        "concentration_risk": risk,
        "action_count": len(actions),
        "caveats": caveats,
        "outline_id": outline.get("outline_id"),
        "outline_status": outline.get("outline_status"),
    }
    return slides, meta


def build_sfir_report_package(
    report_input_id: str,
    *,
    audience_context: str | None = None,
    audience_pov: str | None = None,
) -> dict[str, Any]:
    """Paket siap-PPT untuk SFIR. TIDAK membuat file .pptx."""
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
            "structure": "Action Plan First (Header → Exec Summary → Action Plan → Evidence)",
            "must_follow": [
                "Jangan mengarang metrik, nama, jabatan, kutipan, atau URL.",
                "Jangan menyebut nama yang tidak ada di qt_sfir_top5_spokesperson_rank "
                "sebagai juru bicara brand.",
                "Setiap kutipan wajib menyertakan source_url.",
                "Komponen berstatus N/A tetap ditampilkan sebagai N/A.",
                "Action Plan memakai 8 kolom standard_action_plan_framework.",
                f"Action Type hanya dari taxonomy: {', '.join(ACTION_TYPES)}.",
            ],
        },
    }

    if audience_context or audience_pov:
        package = apply_audience_to_package(package, audience_context, audience_pov)
    return package


__all__ = [
    "build_sfir_report_data_preview",
    "build_sfir_report_package",
    "normalize_audience_context",
    "audience_clarification_payload",
    "apply_audience_to_package",
    "SFIRRendererError",
    "REPORT_TYPE_ID",
    "ACTION_TYPES",
    "PREVIEW_VERSION",
    "PACKAGE_VERSION",
    "CORE_STRUCTURE",
    "AUDIENCE_GUIDANCE",
]
