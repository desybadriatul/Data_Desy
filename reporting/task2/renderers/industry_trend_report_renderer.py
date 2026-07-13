"""
Task 2 renderer: Industry Trend Report — TAHAP 1 (kerangka + data preview).

Mengikuti pola daily_social_media_report_renderer.py milik Fuji:
- Renderer TIDAK membuat file .pptx. Dia menghasilkan "paket siap-PPT"
  (dict berisi slides + ppt_style_brief) yang nanti dirender jadi PPTX
  oleh Claude lewat MCP.
- Sumber kebenaran struktur = registry (lewat build_report_outline_from_id).
- Renderer TIDAK BOLEH mengarang metrik, quote, topic, atau URL. Semua harus
  berasal dari view Task 1. View NOT_AVAILABLE dirender sebagai N/A.

Menyediakan:
  - build_industry_trend_report_data_preview(report_input_id)
  - build_industry_trend_report_package(report_input_id, ...)

Struktur slide mengikuti section_order registry Industry Trend (Action Plan
First): Header -> Executive Summary -> Industry Action Plan -> lapisan evidence.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from reporting.storage.report_input_store import get_report_input
from reporting.task2.report_outline_builder import build_report_outline_from_id

REPORT_TYPE_ID = "industry_trend"
PREVIEW_VERSION = "industry_trend_data_preview_v1"

# Taxonomy action plan Industry Trend — SALIN PERSIS dari registry
# (report_type_registry -> action_taxonomy_by_report_type -> "Industry Trend").
# Jangan diarang; kalau registry berubah, ambil ulang dari sana.
ACTION_TYPES = (
    "Capture Opportunity",
    "Mitigate Industry Risk",
    "Shift Messaging",
    "Channel Focus",
    "Monitor Closely",
)
# Ambang minimum agar sebuah topik boleh memicu aksi berprioritas HIGH.
# Di bawah ini, sinyalnya tetap dilaporkan tapi diturunkan ke Monitor Closely —
# bukti tipis mengubah tingkat kepercayaan, bukan keberadaan sinyal.
MIN_POSTS_FOR_HIGH_PRIORITY = 3
NEGATIVE_RATIO_THRESHOLD = 0.3
NEGATIVE_PCT_THRESHOLD = 25.0
TOPIC_COVERAGE_SAFE_PCT = 60.0


class IndustryTrendRendererError(RuntimeError):
    """Raised when Task 2 cannot safely build an Industry Trend package."""


# ----------------------------------------------------------------------
#  Helper baca view (pola sama seperti renderer Fuji)
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
        return {"view_id": view_id, "status": "MISSING", "rows": 0, "reason": "View tidak ada."}
    meta = _as_mapping(view.get("metadata"))
    status = str(meta.get("status", "READY")).upper()
    rows = view.get("rows")
    count = len(rows) if isinstance(rows, list) else 0
    if status == "READY" and count == 0:
        status = "EMPTY"
    return {
        "view_id": view_id,
        "status": status,
        "rows": count,
        "reason": meta.get("reason"),
    }


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
    """Rapikan teks untuk tabel markdown: buang newline & pipe, potong jika panjang."""
    if value in (None, ""):
        return "N/A"
    text = " ".join(str(value).split()).replace("|", "/")
    if limit and len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


# Kolom yang isinya teks bebas -> perlu dipotong agar tabel tidak pecah.
_TEXT_COLUMNS = {"Content", "Title", "reason"}


def _markdown_table(rows: list[dict], columns: list[str], limit: int = 10,
                    text_limit: int = 120) -> str:
    if not rows:
        return "_Tidak ada data (N/A)._"
    header = "| " + " | ".join(columns) + " |"
    sep = "|" + "|".join("---" for _ in columns) + "|"
    lines = [header, sep]
    for row in rows[:limit]:
        cells = []
        for c in columns:
            value = row.get(c)
            if c in _TEXT_COLUMNS:
                cells.append(_clean_text(value, text_limit))
            else:
                cells.append(_na(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


# ----------------------------------------------------------------------
#  Ringkasan yang dipakai preview (dan nanti slides)
# ----------------------------------------------------------------------
def _kpi(report_input: Mapping[str, Any]) -> dict[str, Any]:
    rows = _rows(report_input, "qt_it_total_metrics_summary")
    row = rows[0] if rows else {}
    return {
        "total_content": int(_num(row.get("Count of Content"))),
        "total_engagement": int(_num(row.get("Engagement"))),
        "potential_reach": row.get("Potential Reach"),
        "ad_value": row.get("Ad Value"),
        "ad_value_note": "Coverage Ad Value rendah; angka bisa understated.",
    }


def _sentiment_summary(report_input: Mapping[str, Any]) -> dict[str, Any]:
    rows = _rows(report_input, "qt_it_sentiment_overall")
    total = sum(_num(r.get("Count of Content")) for r in rows)
    buckets = {str(r.get("Sentiment") or "").casefold(): _num(r.get("Count of Content"))
               for r in rows}
    pos, neg = buckets.get("positive", 0.0), buckets.get("negative", 0.0)
    net = round(100 * (pos - neg) / total, 1) if total else None
    return {
        "rows": rows,
        "total": int(total),
        "positive_pct": round(100 * pos / total, 1) if total else None,
        "negative_pct": round(100 * neg / total, 1) if total else None,
        "net_sentiment": net,
    }


def _topic_coverage(report_input: Mapping[str, Any]) -> dict[str, Any]:
    """Coverage topic diambil dari metadata view, bukan dikarang."""
    view = _view(report_input, "qt_it_topic_volume_engagement")
    meta = _as_mapping(view.get("metadata")) if view else {}
    coverage = meta.get("topic_coverage_pct")
    if coverage is None:
        return {
            "coverage_pct": None,
            "safe_for_topic_conclusion": False,
            "message": "Topic belum tersedia (taxonomy/cache kosong).",
        }
    safe = float(coverage) >= TOPIC_COVERAGE_SAFE_PCT
    return {
        "coverage_pct": coverage,
        "taxonomy_version": meta.get("taxonomy_version"),
        "safe_for_topic_conclusion": safe,
        "message": (
            f"Topic coverage {coverage}%. "
            + ("Aman untuk kesimpulan topic." if safe
               else "Perlakukan sebagai early classified signal, bukan ranking final.")
        ),
    }


ALL_VIEW_IDS = [
    "qt_it_total_metrics_summary",
    "qt_it_brand_sov_soe",
    "qt_it_channel_volume_engagement",
    "qt_it_content_type_distribution",
    "qt_it_topic_volume_engagement",
    "qt_it_sentiment_overall",
    "qt_it_sentiment_trend",
    "qt_it_sentiment_by_topic",
    "qt_it_key_sentiment_drivers",
    "qt_it_channel_role_classification",
    "ql_it_key_events_context",
    "ql_it_topic_examples",
    "ql_it_sentiment_driver_narratives",
    "ql_it_channel_behavior_insight",
    "ql_it_audience_tone_indicators",
    "ql_it_authority_mentions",
    "ql_it_complaint_praise_classification",
]


def _load_report_input(report_input_id: str) -> Mapping[str, Any]:
    if not isinstance(report_input_id, str) or not report_input_id.strip():
        raise IndustryTrendRendererError("report_input_id wajib diisi.")
    report_input = get_report_input(report_input_id.strip())
    if report_input is None:
        raise IndustryTrendRendererError(
            f"report_input_id '{report_input_id}' tidak ditemukan."
        )
    if report_input.get("report_type_id") != REPORT_TYPE_ID:
        raise IndustryTrendRendererError(
            f"Renderer ini hanya untuk {REPORT_TYPE_ID}, "
            f"bukan {report_input.get('report_type_id')}."
        )
    validation = _as_mapping(report_input.get("validation"))
    if validation.get("status") == "FAIL":
        raise IndustryTrendRendererError(
            "report_input validation FAIL; tidak aman untuk dirender."
        )
    return report_input


# ----------------------------------------------------------------------
#  API publik Tahap 1
# ----------------------------------------------------------------------
def build_industry_trend_report_data_preview(
    report_input_id: str,
    *,
    include_evidence_limit: int = 10,
    audience_context: str | None = None,
    audience_pov: str | None = None,
) -> dict[str, Any]:
    """Preview Task 1 untuk Industry Trend sebelum PPT dibuat."""
    report_input = _load_report_input(report_input_id)
    outline = build_report_outline_from_id(report_input_id, allow_partial=True)

    ctx = _as_mapping(report_input.get("context"))
    period = _as_mapping(ctx.get("period"))
    kpi = _kpi(report_input)
    sentiment = _sentiment_summary(report_input)
    coverage = _topic_coverage(report_input)
    statuses = [_view_status(report_input, vid) for vid in ALL_VIEW_IDS]

    ready = sum(1 for s in statuses if s["status"] == "READY")
    readiness = "READY"
    if any(s["status"] != "READY" for s in statuses):
        readiness = "READY_WITH_LIMITATIONS"
    if not coverage["safe_for_topic_conclusion"]:
        readiness = "READY_WITH_TOPIC_CAVEAT"

    brands = _rows(report_input, "qt_it_brand_sov_soe")
    channels = _rows(report_input, "qt_it_channel_volume_engagement")
    topics = _rows(report_input, "qt_it_topic_volume_engagement")
    evidence = _rows(report_input, "ql_it_key_events_context")

    markdown = f"""# Industry Trend Data Preview — {ctx.get('project_name')}

**Period:** {period.get('start_date')} → {period.get('end_date')}
**Readiness:** {readiness}
**View READY:** {ready}/{len(statuses)}
**Topic coverage:** {coverage['message']}

## 1. KPI Summary

| Metric | Value |
|---|---:|
| Total content | {_fmt_int(kpi['total_content'])} |
| Total engagement (interactions) | {_fmt_int(kpi['total_engagement'])} |
| Potential reach | {_fmt_int(kpi['potential_reach']) if kpi['potential_reach'] is not None else 'N/A'} |
| Ad value | {_na(kpi['ad_value'])} |
| Net sentiment | {_na(sentiment['net_sentiment'])} |

## 2. Share of Voice / Engagement

{_markdown_table(brands, ['Campaign', 'Count of Content', 'Engagement', 'Share of Voice (%)', 'Share of Engagement (%)'], include_evidence_limit)}

## 3. Channel Volume & Engagement

{_markdown_table(channels, ['Channel', 'Count of Content', 'Engagement'], include_evidence_limit)}

## 4. Top Topics (LLM report-topic)

{_markdown_table(topics, ['Topic Extraction', 'Count of Content', 'Engagement'], include_evidence_limit)}

## 5. Key Events Evidence

{_markdown_table(evidence, ['Date', 'Content', 'Engagement', 'source_url'], include_evidence_limit)}

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


__all__ = [
    "build_industry_trend_report_data_preview",
    "IndustryTrendRendererError",
    "REPORT_TYPE_ID",
    "ACTION_TYPES",
]


# ======================================================================
#  AUDIENCE CONTEXT
#  Mengikuti pola daily_social_media_report_renderer.py milik Fuji.
#  Audience mengubah CARA BERCERITA, bukan angkanya. Data tetap sama.
# ======================================================================

AUDIENCE_ALIASES = {
    "management": "Management",
    "manajemen": "Management",
    "executive": "Management",
    "ceo": "CEO / Board",
    "direksi": "CEO / Board",
    "board": "CEO / Board",
    "insight": "Insight / Analyst Team",
    "insights": "Insight / Analyst Team",
    "analyst": "Insight / Analyst Team",
    "tim insight": "Insight / Analyst Team",
    "marketing": "Marketing / Content Team",
    "content": "Marketing / Content Team",
    "brand": "Brand / Strategy Team",
    "brand team": "Brand / Strategy Team",
    "strategy": "Brand / Strategy Team",
    "strategi": "Brand / Strategy Team",
    "pr": "PR / Corporate Communications",
    "corcom": "PR / Corporate Communications",
    "public relations": "PR / Corporate Communications",
    "corporate communications": "PR / Corporate Communications",
}

AUDIENCE_GUIDANCE = {
    "Management": {
        "primary_question": "Ke mana arah industri bergerak, dan keputusan apa yang perlu diambil periode ini?",
        "narrative_angle": "arah pasar, posisi kompetitif, implikasi bisnis, keputusan prioritas",
        "preferred_outputs": [
            "posture industri dan implikasinya",
            "top 3 peluang/risiko",
            "keputusan yang dibutuhkan",
            "action plan ringkas",
        ],
        "avoid": "tabel panjang dan detail metodologi yang tidak membantu keputusan",
    },
    "CEO / Board": {
        "primary_question": "Apakah posisi kita di industri menguat atau melemah, dan apa taruhannya?",
        "narrative_angle": "posisi kompetitif, tren struktural, risiko strategis jangka menengah",
        "preferred_outputs": [
            "satu kalimat posture industri",
            "share of voice / engagement vs kompetitor",
            "risiko strategis utama",
            "keputusan tingkat direksi",
        ],
        "avoid": "detail channel, tabel mentah, jargon teknis",
    },
    "Insight / Analyst Team": {
        "primary_question": "Pola apa yang berubah di industri, seberapa kuat evidencenya, dan apa caveat metodologinya?",
        "narrative_angle": "pola data, relasi topic-sentiment-channel, kualitas evidence, coverage caveat",
        "preferred_outputs": [
            "metric readout lengkap",
            "cross-readout topic x sentiment",
            "audit trail evidence dan source_url",
            "limitasi coverage dan metodologi",
        ],
        "avoid": "rekomendasi normatif tanpa dukungan data",
    },
    "Marketing / Content Team": {
        "primary_question": "Tema dan channel apa yang harus kami garap periode berikutnya?",
        "narrative_angle": "tema resonan, efisiensi channel, format konten, contoh nyata",
        "preferred_outputs": [
            "topic dengan engagement tertinggi",
            "channel paling efisien",
            "contoh konten beserta source_url",
            "action plan konten yang operasional",
        ],
        "avoid": "analisis korporat dan metrik finansial",
    },
    "Brand / Strategy Team": {
        "primary_question": "Bagaimana persepsi brand kita relatif terhadap industri, dan celah apa yang bisa diambil?",
        "narrative_angle": "positioning, share of voice/engagement, celah tema, pergeseran persepsi",
        "preferred_outputs": [
            "SOV/SOE vs kompetitor",
            "tema yang belum digarap kompetitor",
            "pergeseran sentimen per tema",
            "rekomendasi positioning",
        ],
        "avoid": "detail operasional harian",
    },
    "PR / Corporate Communications": {
        "primary_question": "Isu industri apa yang berisiko bagi reputasi kita, dan bagaimana merespons?",
        "narrative_angle": "risiko reputasi, isu negatif per tema, eskalasi, guardrail komunikasi",
        "preferred_outputs": [
            "tema dengan sentimen negatif tertinggi",
            "ambang eskalasi",
            "source_url untuk konten sensitif",
            "arah pernyataan",
        ],
        "avoid": "tabel teknis tanpa interpretasi respons komunikasi",
    },
    "General Business User": {
        "primary_question": "Apa yang sedang terjadi di industri ini dan apa artinya bagi kita?",
        "narrative_angle": "ringkasan tren, tema utama, sentimen, aksi yang disarankan",
        "preferred_outputs": [
            "ringkasan tren industri",
            "tema dan channel utama",
            "action plan yang jelas",
            "evidence dengan source_url",
        ],
        "avoid": "jargon teknis tanpa penjelasan",
    },
}


def normalize_audience_context(
    audience_context: str | None = None,
    audience_pov: str | None = None,
) -> dict[str, Any]:
    """Normalisasi pembaca report. Dipakai workflow & renderer agar kedalaman,
    kosakata, penempatan evidence, dan framing aksi menyesuaikan pembaca."""
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
    """Payload saat audience belum ditentukan. Workflow berhenti di sini."""
    target = f" untuk {project_name}" if project_name else ""
    period = f" periode {period_label}" if period_label else ""
    return {
        "success": False,
        "workflow_status": "NEEDS_AUDIENCE",
        "needs_clarification": True,
        "clarification_question": (
            f"Industry Trend Report{target}{period} ini dibuat untuk siapa? "
            "Pilih salah satu: Management, CEO/Board, tim Insight, "
            "Marketing/Content, Brand/Strategy, atau PR/Corcom."
        ),
        "why_needed": (
            "Audience menentukan POV analisis, kedalaman narasi, bahasa, "
            "framing action plan, dan jenis evidence yang paling penting."
        ),
        "suggested_audiences": [
            "Management",
            "CEO / Board",
            "Insight / Analyst Team",
            "Marketing / Content Team",
            "Brand / Strategy Team",
            "PR / Corporate Communications",
        ],
        "example_user_reply": "Untuk tim Brand/Strategy.",
    }


def _audience_prefix(audience: Mapping[str, Any]) -> str:
    return (
        f"Audience: {audience.get('audience')} | "
        f"POV: {audience.get('primary_question')} | "
        f"Angle: {audience.get('narrative_angle')}"
    )


def apply_audience_to_package(
    package: dict[str, Any],
    audience_context: str | None = None,
    audience_pov: str | None = None,
) -> dict[str, Any]:
    """Tempelkan panduan audience ke paket render TANPA mengubah data."""
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
    instructions.insert(0, _audience_prefix(audience))
    package["claude_instructions"] = instructions
    return package


# ======================================================================
#  TAHAP 2 — SLIDES
#  Struktur mengikuti section_order registry Industry Trend.
#  Renderer TIDAK mengarang angka/quote. Semua dari view Task 1.
# ======================================================================

PACKAGE_VERSION = "industry_trend_ppt_package_v1"

# section_order dari registry (report_type_registry -> industry_trend).
CORE_STRUCTURE = [
    ("it_header", "Header / Report Identity", "header"),
    ("it_executive_summary", "Executive Summary", "executive_summary"),
    ("it_industry_action_plan", "Industry Action Plan", "action_plan"),
    ("it_industry_overview_scope", "Industry Overview & Scope", "supporting_evidence"),
    ("it_conversation_engagement_trend", "Industry Conversation & Engagement Trend", "supporting_evidence"),
    ("it_brand_category_landscape", "Brand & Category Landscape", "supporting_evidence"),
    ("it_channel_content_behavior", "Channel & Content Behavior", "supporting_evidence"),
    ("it_thematic_topic_trends", "Thematic & Topic Trends", "supporting_evidence"),
    ("it_sentiment_perception_shifts", "Sentiment & Perception Shifts", "supporting_evidence"),
    ("it_strategic_insights", "Strategic Insights", "supporting_evidence"),
]


def _slide(slide_id: str, title: str, subtitle: str,
           components: list[dict[str, Any]], speaker_notes: str = "") -> dict[str, Any]:
    return {
        "slide_id": slide_id,
        "title": title,
        "subtitle": subtitle,
        "components": components,
        "speaker_notes": speaker_notes,
    }


def _kpi_cards(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    return {
        "type": "kpi_cards",
        "items": [{"label": label, "value": _na(value)} for label, value in pairs],
    }


def _table(title: str, rows: list[dict], columns: list[str],
           limit: int = 10, text_limit: int = 160) -> dict[str, Any]:
    """Tabel untuk slide. Kalau rows kosong -> ditandai N/A, bukan dihapus."""
    if not rows:
        return {"type": "table", "title": title, "columns": columns,
                "rows": [], "status": "N/A",
                "note": "Data tidak tersedia pada report input."}
    clean = []
    for row in rows[:limit]:
        item = {}
        for c in columns:
            value = row.get(c)
            item[c] = (_clean_text(value, text_limit)
                       if c in _TEXT_COLUMNS else _na(value))
        clean.append(item)
    return {"type": "table", "title": title, "columns": columns,
            "rows": clean, "status": "READY"}


def _bullets(title: str, items: list[str]) -> dict[str, Any]:
    kept = [i for i in items if i]
    return {"type": "bullets", "title": title,
            "items": kept or ["N/A — data pendukung tidak tersedia."],
            "status": "READY" if kept else "N/A"}


def _evidence_list(rows: list[dict], text_field: str = "Content") -> dict[str, Any]:
    """Evidence WAJIB membawa source_url; tanpa itu jangan dipakai sebagai quote."""
    items = []
    for row in rows:
        text = _clean_text(row.get(text_field), 180)
        if text == "N/A":
            continue
        items.append({
            "text": text,
            "engagement": _na(row.get("Engagement")),
            "source_url": _na(row.get("source_url")),
        })
    return {"type": "evidence_list", "items": items,
            "status": "READY" if items else "N/A"}


# ----------------------------------------------------------------------
#  Action Plan — diturunkan dari data, bukan dikarang.
# ----------------------------------------------------------------------
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
    """Turunkan action plan dari view yang READY. Kalau bukti tipis -> Monitor Closely."""
    actions: list[dict] = []
    caveats: list[str] = []

    topics = _rows(report_input, "qt_it_topic_volume_engagement")
    channels = _rows(report_input, "qt_it_channel_volume_engagement")
    by_topic = _rows(report_input, "qt_it_sentiment_by_topic")
    sentiment = _sentiment_summary(report_input)

    topic_safe = bool(coverage.get("safe_for_topic_conclusion"))
    if topics and not topic_safe:
        caveats.append(
            f"Topic coverage {coverage.get('coverage_pct')}% — aksi berbasis topic "
            "diberi prioritas Monitor Closely, bukan keputusan final."
        )

    # 1) Topic dengan engagement tertinggi -> Capture Opportunity.
    #    Butuh DUA syarat untuk HIGH: coverage topic memadai DAN volume cukup.
    if topics:
        top = topics[0]
        label = top.get("Topic Extraction")
        eng = _fmt_int(top.get("Engagement"))
        volume = int(_num(top.get("Count of Content")))
        cnt = _fmt_int(volume)
        thin = volume < MIN_POSTS_FOR_HIGH_PRIORITY
        confident = topic_safe and not thin
        if thin:
            caveats.append(
                f"Topic teratas '{label}' hanya {volume} konten "
                f"(< {MIN_POSTS_FOR_HIGH_PRIORITY}); belum cukup untuk aksi HIGH."
            )
        actions.append(_action_row(
            "HIGH" if confident else "MEDIUM",
            "Capture Opportunity" if confident else "Monitor Closely",
            f"Topic: {label}",
            (f"Perbanyak konten pada tema '{label}' di channel dengan "
             "engagement tertinggi." if confident else
             f"Pantau tema '{label}' sampai bukti cukup untuk scale-up."),
            f"Topic ini memimpin engagement ({eng}) dari {cnt} konten.",
            f"qt_it_topic_volume_engagement: {label} = {eng} engagement "
            f"({cnt} konten).",
            "Peningkatan engagement efficiency pada tema yang sudah terbukti resonan.",
        ))

    # 2) Topic dengan sentimen negatif dominan -> Mitigate Industry Risk.
    #    Topik bervolume kecil (< MIN_POSTS_FOR_HIGH_PRIORITY) tetap dilaporkan,
    #    tapi diturunkan ke Monitor Closely agar 1-2 post tidak mendominasi plan.
    neg: dict[str, int] = {}
    tot: dict[str, int] = {}
    for row in by_topic:
        label = str(row.get("Topic Extraction") or "")
        count = int(_num(row.get("Count of Content")))
        tot[label] = tot.get(label, 0) + count
        if str(row.get("Sentiment") or "").casefold() == "negative":
            neg[label] = neg.get(label, 0) + count

    risky = [
        (label, neg[label] / tot[label], tot[label])
        for label in neg if tot.get(label)
    ]
    risky.sort(key=lambda item: (item[1], item[2]), reverse=True)

    if risky and risky[0][1] >= NEGATIVE_RATIO_THRESHOLD:
        label, ratio, volume = risky[0]
        pct = round(ratio * 100)
        thin = volume < MIN_POSTS_FOR_HIGH_PRIORITY
        if thin:
            caveats.append(
                f"Topic '{label}' bersentimen negatif {pct}% tetapi hanya "
                f"{volume} konten (< {MIN_POSTS_FOR_HIGH_PRIORITY}). "
                "Dilaporkan sebagai sinyal awal, bukan prioritas HIGH."
            )
        actions.append(_action_row(
            "MEDIUM" if thin else "HIGH",
            "Monitor Closely" if thin else "Mitigate Industry Risk",
            f"Topic: {label}",
            (f"Pantau perkembangan isu '{label}' sebelum mengambil aksi."
             if thin else
             f"Siapkan respons/klarifikasi untuk isu '{label}'."),
            (f"{pct}% konten pada topic ini negatif, namun volumenya baru "
             f"{volume} konten sehingga belum konklusif."
             if thin else
             f"{pct}% konten pada topic ini bersentimen negatif "
             f"dari {volume} konten."),
            f"qt_it_sentiment_by_topic: {label} negative {pct}% ({volume} konten).",
            ("Deteksi dini eskalasi tanpa over-reaksi pada volume kecil."
             if thin else
             "Mitigasi eskalasi sentimen negatif pada tema berisiko."),
        ))

    # 3) Channel paling efisien -> Channel Focus.
    ranked = [c for c in channels if _num(c.get("Count of Content")) > 0]
    ranked.sort(key=lambda c: _num(c.get("Engagement")) / _num(c.get("Count of Content")),
                reverse=True)
    if ranked:
        best = ranked[0]
        ch = best.get("Channel")
        eff = round(_num(best.get("Engagement")) / _num(best.get("Count of Content")), 1)
        actions.append(_action_row(
            "MEDIUM", "Channel Focus", f"Channel: {ch}",
            f"Alokasikan lebih banyak produksi konten ke {ch}.",
            f"{ch} punya engagement per konten tertinggi ({eff}).",
            f"qt_it_channel_volume_engagement: {ch} = {eff} engagement/konten.",
            "Efisiensi engagement lebih tinggi dengan volume konten yang sama.",
        ))

    # 4) Sentimen negatif tinggi secara keseluruhan -> Shift Messaging.
    if (sentiment["negative_pct"] is not None
            and sentiment["negative_pct"] >= NEGATIVE_PCT_THRESHOLD):
        actions.append(_action_row(
            "HIGH", "Shift Messaging", "Overall sentiment",
            "Sesuaikan pesan utama untuk menurunkan porsi sentimen negatif.",
            f"Sentimen negatif mencapai {sentiment['negative_pct']}% dari total konten.",
            f"qt_it_sentiment_overall: negative {sentiment['negative_pct']}%.",
            "Perbaikan net sentiment pada periode berikutnya.",
        ))

    if not actions:
        actions.append(_action_row(
            "LOW", "Monitor Closely", "Data readiness",
            "Lanjutkan monitoring; perkuat kelengkapan data sebelum mengambil aksi.",
            "View pendukung belum cukup untuk menurunkan aksi yang bertanggung jawab.",
            "Lihat tabel View Readiness pada data preview.",
            "Menghindari keputusan berbasis bukti tipis.",
        ))
    return actions, caveats


ACTION_COLUMNS = [
    "Priority", "Action Type", "Focus Area", "Recommended Action",
    "Rationale", "Supporting Evidence", "Expected Impact",
]



# ----------------------------------------------------------------------
#  Slides
# ----------------------------------------------------------------------
def _build_slides(report_input: Mapping[str, Any],
                  outline: Mapping[str, Any]) -> tuple[list[dict], dict[str, Any]]:
    ctx = _as_mapping(report_input.get("context"))
    period = _as_mapping(ctx.get("period"))
    kpi = _kpi(report_input)
    sentiment = _sentiment_summary(report_input)
    coverage = _topic_coverage(report_input)
    actions, caveats = _build_action_plan(report_input, coverage)

    project = ctx.get("project_name") or "N/A"
    period_label = f"{period.get('start_date')} → {period.get('end_date')}"

    topics = _rows(report_input, "qt_it_topic_volume_engagement")
    channels = _rows(report_input, "qt_it_channel_volume_engagement")
    brands = _rows(report_input, "qt_it_brand_sov_soe")
    trend = _rows(report_input, "qt_it_sentiment_trend")
    by_topic = _rows(report_input, "qt_it_sentiment_by_topic")
    events = _rows(report_input, "ql_it_key_events_context")
    topic_ex = _rows(report_input, "ql_it_topic_examples")
    channel_beh = _rows(report_input, "ql_it_channel_behavior_insight")
    authority = _rows(report_input, "ql_it_authority_mentions")

    top_topic = topics[0].get("Topic Extraction") if topics else None

    slides = [
        _slide("it_header", "Industry Trend Report", f"{project} · {period_label}",
               [_kpi_cards([
                   ("Project", project),
                   ("Period", period_label),
                   ("Total Content", _fmt_int(kpi["total_content"])),
               ])],
               "Slide identitas. Semua angka berasal dari report input Task 1."),

        _slide("it_executive_summary", "Executive Summary",
               "Kondisi industri, driver utama, risiko & peluang",
               [
                   _kpi_cards([
                       ("Total Content", _fmt_int(kpi["total_content"])),
                       ("Total Engagement", _fmt_int(kpi["total_engagement"])),
                       ("Net Sentiment", sentiment["net_sentiment"]),
                       ("Potential Reach", kpi["potential_reach"]),
                   ]),
                   _bullets("Key Findings", [
                       f"Topic dominan: {top_topic}." if top_topic else "",
                       (f"Sentimen positif {sentiment['positive_pct']}%, "
                        f"negatif {sentiment['negative_pct']}%.")
                       if sentiment["total"] else "",
                       coverage["message"],
                   ]),
                   _evidence_list(events),
               ],
               "Ringkasan tingkat eksekutif; jangan masuk detail tabel."),

        _slide("it_industry_action_plan", "Industry Action Plan",
               "Aksi prioritas berbasis evidence",
               [
                   _table("Action Plan", actions, ACTION_COLUMNS, limit=8, text_limit=200),
                   _bullets("Caveats", caveats or ["Tidak ada caveat tambahan."]),
               ],
               "Action Plan First: muncul tepat setelah Executive Summary. "
               "Setiap aksi wajib punya Supporting Evidence dari view Task 1."),

        _slide("it_industry_overview_scope", "Industry Overview & Scope",
               "Definisi industri, total metrics, periode & sumber",
               [
                   _kpi_cards([
                       ("Total Content", _fmt_int(kpi["total_content"])),
                       ("Total Engagement", _fmt_int(kpi["total_engagement"])),
                       ("Potential Reach", kpi["potential_reach"]),
                       ("Ad Value", kpi["ad_value"]),
                   ]),
                   _bullets("Scope Notes", [
                       f"Periode: {period_label}.",
                       f"Channels: {', '.join(ctx.get('channels') or []) or 'semua channel'}.",
                       kpi.get("ad_value_note") or "",
                   ]),
               ],
               "Overview scope. Metrik N/A ditampilkan apa adanya."),

        _slide("it_conversation_engagement_trend",
               "Industry Conversation & Engagement Trend",
               "Pergerakan volume & sentimen sepanjang periode",
               [
                   _table("Sentiment Trend (Date × Sentiment)", trend,
                          ["Date", "Sentiment", "Count of Content"], limit=20),
                   _evidence_list(events),
               ],
               "Narasi early / peak / stabilization diambil dari tren ini."),

        _slide("it_brand_category_landscape", "Brand & Category Landscape",
               "Share of Voice & Share of Engagement antar brand",
               [
                   _table("SOV / SOE", brands,
                          ["Campaign", "Count of Content", "Engagement",
                           "Share of Voice (%)", "Share of Engagement (%)"]),
                   _bullets("Reading Guide", [
                       "SOV = share volume konten. SOE = share engagement.",
                       "SOE jauh di atas SOV berarti efisiensi engagement tinggi.",
                   ]),
               ],
               "Brand universe berasal dari client_brand + competitor_brands."),

        _slide("it_channel_content_behavior", "Channel & Content Behavior",
               "Perilaku konten per channel",
               [
                   _table("Channel Volume & Engagement", channels,
                          ["Channel", "Count of Content", "Engagement"]),
                   _evidence_list(channel_beh),
               ],
               "Content type distribution N/A: Media Type tidak tersedia."),

        _slide("it_thematic_topic_trends", "Thematic & Topic Trends",
               "Tema dominan berdasarkan report-topic LLM",
               [
                   _table("Top Topics", topics,
                          ["Topic Extraction", "Count of Content", "Engagement"]),
                   _evidence_list(topic_ex),
                   _bullets("Topic Coverage", [coverage["message"]]),
               ],
               "Topic berasal dari cached LLM taxonomy, bukan raw Topic Extraction."),

        _slide("it_sentiment_perception_shifts", "Sentiment & Perception Shifts",
               "Distribusi sentimen dan pergeserannya",
               [
                   _table("Sentiment Overall", sentiment["rows"],
                          ["Sentiment", "Count of Content", "Engagement"]),
                   _table("Sentiment by Topic", by_topic,
                          ["Topic Extraction", "Sentiment", "Count of Content"], limit=15),
                   _bullets("Notes", [
                       "Key sentiment drivers N/A: Aspect Based Sentiment tidak tersedia.",
                   ]),
               ],
               "Sentiment driver narratives N/A karena Aspect kosong."),

        _slide("it_strategic_insights", "Strategic Insights",
               "Implikasi strategis dari evidence",
               [
                   _bullets("Implications", [
                       f"Tema '{top_topic}' layak jadi fokus konten." if top_topic else "",
                       (f"Sentimen negatif {sentiment['negative_pct']}% "
                        "perlu diawasi.") if sentiment["negative_pct"] else "",
                       "Prioritaskan channel dengan engagement per konten tertinggi.",
                   ]),
                   _evidence_list(authority),
               ],
               "Insight harus merujuk balik ke Action Plan."),
    ]

    meta = {
        "project_name": project,
        "period": dict(period),
        "kpi": kpi,
        "sentiment": sentiment,
        "topic_coverage": coverage,
        "action_count": len(actions),
        "caveats": caveats,
        "outline_id": outline.get("outline_id"),
        "outline_status": outline.get("outline_status"),
    }
    return slides, meta


def build_industry_trend_report_package(
    report_input_id: str,
    *,
    audience_context: str | None = None,
    audience_pov: str | None = None,
) -> dict[str, Any]:
    """Paket siap-PPT untuk Industry Trend. TIDAK membuat file .pptx.

    Kalau audience diberikan, panduan audience ditempelkan ke ppt_style_brief
    dan claude_instructions — tanpa mengubah satu pun angka/evidence.
    """
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
                "Jangan mengarang metrik, quote, topic, atau URL.",
                "Komponen berstatus N/A tetap ditampilkan sebagai N/A.",
                "Setiap quote wajib menyertakan source_url.",
                "Action Plan memakai 8 kolom standard_action_plan_framework.",
                f"Action Type hanya dari taxonomy: {', '.join(ACTION_TYPES)}.",
            ],
        },
    }

    if audience_context or audience_pov:
        package = apply_audience_to_package(package, audience_context, audience_pov)
    return package


__all__ += [
    "build_industry_trend_report_package",
    "normalize_audience_context",
    "audience_clarification_payload",
    "apply_audience_to_package",
    "PACKAGE_VERSION",
    "CORE_STRUCTURE",
    "AUDIENCE_GUIDANCE",
]
