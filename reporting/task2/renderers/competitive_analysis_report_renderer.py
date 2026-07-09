"""Competitive Analysis Task 2 renderer and data preview.

Converts a frozen Task 1 `competitive_analysis` report_input package into a
PPT-ready package for Claude rendering.

Evidence URL policy v1:
- Main slides use Evidence IDs (E01/P01/etc.) and source labels.
- Full URLs are only provided in Appendix / evidence_url_index / data pack.
- Claude must not spread raw URLs across every slide.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from reporting.storage.report_input_store import get_report_input
from reporting.task2.report_outline_builder import build_report_outline_from_id


REPORT_TYPE_ID = "competitive_analysis"
RENDER_PACKAGE_VERSION = "competitive_analysis_report_render_package_v2"


class CompetitiveAnalysisRendererError(RuntimeError):
    """Raised when Competitive Analysis rendering cannot proceed safely."""


AUDIENCE_ALIASES = {
    "management": "Management",
    "manajemen": "Management",
    "ceo": "CEO / Board",
    "board": "CEO / Board",
    "direksi": "CEO / Board",
    "marketing": "Marketing / Brand Team",
    "brand": "Marketing / Brand Team",
    "brand team": "Marketing / Brand Team",
    "content": "Marketing / Content Team",
    "pr": "PR / Corporate Communications",
    "corcom": "PR / Corporate Communications",
    "insight": "Insight / Analyst Team",
    "analyst": "Insight / Analyst Team",
}

AUDIENCE_GUIDANCE = {
    "Management": {
        "primary_question": "Brand mana yang unggul, gap apa yang perlu ditutup, dan keputusan apa yang perlu diarahkan?",
        "narrative_angle": "executive competitive position, SOV/SOE gap, risk/opportunity, next decision",
        "tone": "executive, concise, decision-first",
    },
    "CEO / Board": {
        "primary_question": "Apakah posisi kompetitif brand cukup kuat dan di area mana perlu intervensi strategis?",
        "narrative_angle": "board-level competitive posture, strategic risk, opportunity whitespace",
        "tone": "board-level, crisp, no operational clutter",
    },
    "Marketing / Brand Team": {
        "primary_question": "Narasi, channel, dan konten apa yang perlu dipertahankan, ditiru, atau dibedakan dari kompetitor?",
        "narrative_angle": "brand positioning, channel/content strategy, differentiation, playbook",
        "tone": "strategic-marketing, practical, evidence-backed",
    },
    "Marketing / Content Team": {
        "primary_question": "Format, channel, dan contoh konten kompetitor mana yang bisa jadi benchmark?",
        "narrative_angle": "content format benchmark, best practice, channel efficiency",
        "tone": "practical, content-led, benchmark-oriented",
    },
    "PR / Corporate Communications": {
        "primary_question": "Isu/sentimen kompetitif mana yang berisiko terhadap reputasi brand dan perlu respons komunikasi?",
        "narrative_angle": "reputation comparison, risk narrative, response positioning",
        "tone": "risk-aware, communication-focused, evidence-backed",
    },
    "Insight / Analyst Team": {
        "primary_question": "Apa pola data kompetitif, caveat, dan confidence level yang perlu dicatat?",
        "narrative_angle": "metric patterns, caveats, evidence traceability, methodology",
        "tone": "analytical, transparent, caveat-aware",
    },
    "General Business User": {
        "primary_question": "Apa posisi brand dibanding kompetitor dan tindakan apa yang paling masuk akal?",
        "narrative_angle": "plain-language competitive snapshot, action, evidence",
        "tone": "clear, practical, evidence-backed",
    },
}


def _clean(value: Any, limit: int | None = None) -> str:
    text = " ".join(str(value or "").strip().split())
    if limit and len(text) > limit:
        return text[: max(0, limit - 1)].rstrip() + "…"
    return text


def _num(value: Any) -> int | float:
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return value
    try:
        return float(str(value).replace(",", ""))
    except Exception:
        return 0


def _fmt_int(value: Any) -> str:
    try:
        return f"{int(round(float(value or 0))):,}".replace(",", ".")
    except Exception:
        return "0"


def _fmt_pct(value: Any) -> str:
    return "N/A" if value is None else f"{float(value):.1f}%".replace(".", ",")


def _fmt_metric(value: Any) -> str:
    value = _num(value)
    if value >= 1_000_000_000:
        return f"{value/1_000_000_000:.1f}B".replace(".", ",")
    if value >= 1_000_000:
        return f"{value/1_000_000:.1f}M".replace(".", ",")
    if value >= 1_000:
        return f"{value/1_000:.1f}K".replace(".", ",")
    return _fmt_int(value)


def _now_id(prefix: str) -> str:
    return f"{prefix}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid4().hex[:8]}"


def normalize_audience_context(audience_context: str | None = None, audience_pov: str | None = None) -> dict[str, Any]:
    raw = _clean(audience_context or audience_pov or "")
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
    return {"audience": label, "raw_audience_input": raw or None, **guidance}


def audience_clarification_payload(project_name: str | None = None, period_label: str | None = None) -> dict[str, Any]:
    target = f" untuk {project_name}" if project_name else ""
    period = f" periode {period_label}" if period_label else ""
    return {
        "success": False,
        "workflow_status": "NEEDS_AUDIENCE",
        "needs_clarification": True,
        "clarification_question": (
            f"Competitive Analysis{target}{period} ini dibuat untuk siapa? "
            "Pilih salah satu: Management, CEO/Board, Marketing/Brand, Marketing/Content, PR/Corcom, atau Insight Team."
        ),
        "why_needed": "Audience menentukan angle benchmark, action plan, dan depth narasi kompetitif.",
        "suggested_audiences": [
            "Management",
            "CEO / Board",
            "Marketing / Brand Team",
            "Marketing / Content Team",
            "PR / Corporate Communications",
            "Insight / Analyst Team",
        ],
        "example_user_reply": "Untuk Marketing/Brand Team.",
    }


def competitors_clarification_payload(project_name: str | None = None) -> dict[str, Any]:
    target = f" untuk {project_name}" if project_name else ""
    return {
        "success": False,
        "workflow_status": "NEEDS_COMPETITORS",
        "needs_clarification": True,
        "clarification_question": (
            f"Competitive Analysis{target} mau dibandingkan dengan kompetitor apa saja? "
            "Sebutkan client brand dan daftar kompetitor, misalnya: client Aqua; kompetitor Le Minerale, Vit."
        ),
        "why_needed": "Competitive Analysis butuh brand universe agar SOV/SOE, sentiment, channel, dan evidence tidak tercampur.",
        "example_user_reply": "Client brand Bluebird, kompetitor Grab dan Gojek.",
    }


def _view(report_input: Mapping[str, Any], view_id: str) -> dict[str, Any]:
    bucket = "quantitative_views" if view_id.startswith("qt_") else "qualitative_views"
    view = (report_input.get(bucket) or {}).get(view_id) or {}
    return view if isinstance(view, dict) else {}


def _rows(report_input: Mapping[str, Any], view_id: str) -> list[dict[str, Any]]:
    return [dict(row) for row in (_view(report_input, view_id).get("rows") or []) if isinstance(row, Mapping)]


def _metadata(report_input: Mapping[str, Any], view_id: str) -> dict[str, Any]:
    return dict(_view(report_input, view_id).get("metadata") or {})


def _load_report_input(report_input_id: str) -> dict[str, Any]:
    item = get_report_input(report_input_id)
    if not item:
        raise CompetitiveAnalysisRendererError(f"report_input_id '{report_input_id}' tidak ditemukan.")
    report_input = item.get("report_input") if isinstance(item, Mapping) and "report_input" in item else item
    if not isinstance(report_input, dict):
        raise CompetitiveAnalysisRendererError("Stored report input tidak valid.")
    if report_input.get("report_type_id") != REPORT_TYPE_ID:
        raise CompetitiveAnalysisRendererError(
            f"report_input_id '{report_input_id}' bukan competitive_analysis."
        )
    return report_input


def _brand_status(report_input: Mapping[str, Any]) -> tuple[str | None, list[str], list[str]]:
    status_rows = _rows(report_input, "qt_ca_brand_status")
    client = None
    competitors: list[str] = []
    brands: list[str] = []
    for row in status_rows:
        brand = _clean(row.get("brand") or row.get("campaign"))
        if not brand:
            continue
        brands.append(brand)
        tag = _clean(row.get("tag")).casefold()
        if tag == "client" and not client:
            client = brand
        elif tag == "competitor":
            competitors.append(brand)
    if not client and brands:
        client = brands[0]
        competitors = [brand for brand in brands[1:] if brand not in competitors] + competitors
    return client, competitors, brands


def _leader(rows: list[Mapping[str, Any]], field: str) -> Mapping[str, Any] | None:
    if not rows:
        return None
    return max(rows, key=lambda row: _num(row.get(field)))


def _brand_row_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for row in rows:
        brand = _clean(row.get("brand") or row.get("campaign"))
        if brand:
            result[brand] = row
    return result


def _evidence_index(report_input: Mapping[str, Any], limit: int = 30) -> list[dict[str, Any]]:
    views = [
        "ql_ca_positive_negative_highlights",
        "ql_ca_top_social_posts_by_brand",
        "ql_ca_top_authors_by_brand",
        "ql_ca_topic_sentiment_by_brand",
    ]
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for view_id in views:
        for row in _rows(report_input, view_id):
            url = _clean(row.get("source_url") or row.get("url") or row.get("link_url"))
            content = _clean(row.get("content") or row.get("title"), 150)
            if not (url or content):
                continue
            evidence_id = _clean(row.get("evidence_id")) or f"CA{len(result)+1:02d}"
            key = url or content.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append({
                "evidence_id": evidence_id,
                "brand": _clean(row.get("brand") or row.get("campaign")),
                "source": _clean(row.get("author") or row.get("channel")),
                "channel": _clean(row.get("channel")),
                "sentiment": _clean(row.get("sentiment")),
                "metric": _num(row.get("engagement") or row.get("interactions")),
                "content": content,
                "url": url,
                "view_id": view_id,
            })
            if len(result) >= limit:
                return result
    return result


def _top_topics(report_input: Mapping[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    rows = _rows(report_input, "ql_ca_topic_sentiment_by_brand") or _rows(report_input, "qt_ca_issue_sentiment_by_brand")
    return sorted(rows, key=lambda row: (_num(row.get("engagement")), _num(row.get("count_content"))), reverse=True)[:limit]


def _action_plan(report_input: Mapping[str, Any], audience: Mapping[str, Any]) -> list[dict[str, Any]]:
    kpis = _brand_row_map(_rows(report_input, "qt_ca_kpi_summary_by_brand"))
    vol_rows = _rows(report_input, "qt_ca_brand_volume_engagement")
    sentiment_rows = _rows(report_input, "qt_ca_sentiment_by_brand")
    evidence = _evidence_index(report_input, limit=10)
    client, competitors, _ = _brand_status(report_input)
    client_row = kpis.get(client or "") if client else None
    sov_leader = _leader(vol_rows, "sov_pct")
    soe_leader = _leader(vol_rows, "soe_pct")

    client_sov = _num((client_row or {}).get("sov_pct")) if client_row else None
    client_soe = _num((client_row or {}).get("soe_pct")) if client_row else None
    top_negative = None
    for row in sentiment_rows:
        if row.get("sentiment") == "negative":
            if top_negative is None or _num(row.get("engagement")) > _num(top_negative.get("engagement")):
                top_negative = row

    ev = evidence[0] if evidence else {}
    ev_ref = ev.get("evidence_id", "Appendix")
    actions = [
        {
            "priority": "HIGH",
            "action_type": "DEFEND POSITION" if client and sov_leader and sov_leader.get("brand") == client else "CLOSE VISIBILITY GAP",
            "focus_area": "Share of Voice / Share of Engagement",
            "recommended_action": "Prioritaskan pesan dan channel yang menaikkan visibility brand pada area kompetitor unggul; jangan membaca SOV tinggi sebagai kemenangan bila SOE rendah.",
            "rationale": f"Leader SOV: {_clean((sov_leader or {}).get('brand')) or 'N/A'} ({_fmt_pct((sov_leader or {}).get('sov_pct'))}); leader SOE: {_clean((soe_leader or {}).get('brand')) or 'N/A'} ({_fmt_pct((soe_leader or {}).get('soe_pct'))}).",
            "evidence_ref": ev_ref,
            "expected_impact": "Gap visibility/engagement lebih jelas untuk prioritas campaign berikutnya.",
            "owner_next_step": "Brand/Marketing: pilih 1-2 channel prioritas berdasarkan gap SOV/SOE.",
        },
        {
            "priority": "HIGH" if top_negative else "MEDIUM",
            "action_type": "MITIGATE RISK",
            "focus_area": "Sentiment & issue risk",
            "recommended_action": "Pantau brand dengan engagement negatif tertinggi dan siapkan response/positioning jika isu mulai masuk channel/media utama.",
            "rationale": f"Negatif terbesar terdeteksi pada {_clean((top_negative or {}).get('brand') or (top_negative or {}).get('campaign')) or 'N/A'} dengan engagement {_fmt_metric((top_negative or {}).get('engagement'))}.",
            "evidence_ref": ev_ref,
            "expected_impact": "Risiko reputasi kompetitif lebih cepat terdeteksi dan tidak terlambat ditangani.",
            "owner_next_step": "PR/Insight: review evidence negatif teratas di Appendix.",
        },
        {
            "priority": "MEDIUM",
            "action_type": "DIFFERENTIATE",
            "focus_area": "Narrative / content whitespace",
            "recommended_action": "Cari topik/format yang engagement-nya tinggi di kompetitor tapi belum kuat di client; gunakan sebagai whitespace atau differentiation angle.",
            "rationale": "Topic, author, dan content benchmark tersedia sebagai evidence ID; full URL tidak ditampilkan di main slide agar deck tetap executive.",
            "evidence_ref": ev_ref,
            "expected_impact": "Content plan lebih berbasis benchmark, bukan asumsi kreatif semata.",
            "owner_next_step": "Content/Brand: shortlist 3 evidence ID untuk ide konten atau message testing.",
        },
    ]
    return actions


def build_competitive_analysis_report_data_preview(report_input_id: str, include_evidence_limit: int = 10) -> dict[str, Any]:
    report_input = _load_report_input(report_input_id)
    context = dict(report_input.get("context") or {})
    client, competitors, brands = _brand_status(report_input)
    kpis = _rows(report_input, "qt_ca_kpi_summary_by_brand")
    vol_rows = _rows(report_input, "qt_ca_brand_volume_engagement")
    evidence = _evidence_index(report_input, limit=include_evidence_limit)
    limitations = list(report_input.get("limitations") or [])
    validation = dict(report_input.get("validation") or {})
    metric = dict(report_input.get("metric_readiness") or {})

    total_content = sum(_num(row.get("count_content")) for row in kpis)
    total_interactions = sum(_num(row.get("sum_engagement") or row.get("sum_interactions")) for row in kpis)
    sov_leader = _leader(vol_rows, "sov_pct")
    soe_leader = _leader(vol_rows, "soe_pct")

    lines = [
        f"**Competitive Analysis Preview — {context.get('project_name')}**",
        f"Periode: {(context.get('period') or {}).get('start_date')} s/d {(context.get('period') or {}).get('end_date')}",
        f"Client brand: {client or 'N/A'} | Competitors: {', '.join(competitors) if competitors else 'N/A'}",
        f"Total content: {_fmt_int(total_content)} | Total interactions: {_fmt_int(total_interactions)}",
        f"SOV leader: {_clean((sov_leader or {}).get('brand')) or 'N/A'} ({_fmt_pct((sov_leader or {}).get('sov_pct'))})",
        f"SOE leader: {_clean((soe_leader or {}).get('brand')) or 'N/A'} ({_fmt_pct((soe_leader or {}).get('soe_pct'))})",
        "",
        "**Evidence policy:** main report pakai Evidence ID; full URL hanya di Appendix/Data Pack.",
    ]
    if limitations:
        lines.append("\n**Limitations:**")
        lines.extend(f"- {item}" for item in limitations[:5])

    return {
        "success": True,
        "report_type_id": REPORT_TYPE_ID,
        "report_input_id": report_input_id,
        "readiness": validation.get("status") or "UNKNOWN",
        "context": context,
        "client_brand": client,
        "competitor_brands": competitors,
        "brand_universe": brands,
        "kpi_summary_by_brand": kpis,
        "brand_volume_engagement": vol_rows,
        "sentiment_by_brand": _rows(report_input, "qt_ca_sentiment_by_brand"),
        "top_topics": _top_topics(report_input, limit=8),
        "evidence_index_preview": evidence,
        "limitations": limitations,
        "metric_readiness": metric,
        "markdown": "\n".join(lines),
    }


def build_competitive_analysis_report_package(
    report_input_id: str,
    *,
    allow_partial: bool = True,
    audience_context: str | None = None,
    audience_pov: str | None = None,
) -> dict[str, Any]:
    report_input = _load_report_input(report_input_id)
    validation = dict(report_input.get("validation") or {})
    if validation.get("status") == "FAIL" and not allow_partial:
        raise CompetitiveAnalysisRendererError("Report input FAIL; gunakan allow_partial=True hanya jika ingin render dengan limitation.")

    context = dict(report_input.get("context") or {})
    period = dict(context.get("period") or {})
    audience = normalize_audience_context(audience_context, audience_pov)
    client, competitors, brands = _brand_status(report_input)
    kpis = _rows(report_input, "qt_ca_kpi_summary_by_brand")
    vol_rows = _rows(report_input, "qt_ca_brand_volume_engagement")
    sentiment_rows = _rows(report_input, "qt_ca_sentiment_by_brand")
    channel_rows = _rows(report_input, "qt_ca_channel_mix_by_brand")
    content_rows = _rows(report_input, "qt_ca_content_type_by_brand")
    top_posts = _rows(report_input, "ql_ca_top_social_posts_by_brand")
    highlights = _rows(report_input, "ql_ca_positive_negative_highlights")
    top_authors = _rows(report_input, "ql_ca_top_authors_by_brand")
    topics = _top_topics(report_input, limit=12)
    evidence = _evidence_index(report_input, limit=40)
    action_plan = _action_plan(report_input, audience)
    limitations = list(report_input.get("limitations") or [])
    metric = dict(report_input.get("metric_readiness") or {})
    data_health = dict(report_input.get("data_health") or {})

    total_content = sum(_num(row.get("count_content")) for row in kpis)
    total_interactions = sum(_num(row.get("sum_engagement") or row.get("sum_interactions")) for row in kpis)
    sov_leader = _leader(vol_rows, "sov_pct")
    soe_leader = _leader(vol_rows, "soe_pct")
    efficiency_leader = _leader(kpis, "engagement_per_content")

    slides = [
        {
            "slide_no": 1,
            "title": "COMPETITIVE ANALYSIS",
            "subtitle": f"{client or context.get('project_name')} vs {', '.join(competitors) if competitors else 'benchmark universe'} · {period.get('start_date')}–{period.get('end_date')}",
            "layout": "cover_competitive_snapshot",
            "audience": audience,
            "kpi_tiles": [
                {"label": "BRANDS", "value": len(brands), "note": ", ".join(brands[:4])},
                {"label": "TOTAL CONTENT", "value": _fmt_int(total_content), "note": "canonical mapped rows"},
                {"label": "TOTAL INTERACTIONS", "value": _fmt_int(total_interactions), "note": "views excluded"},
                {"label": "SOV LEADER", "value": _clean((sov_leader or {}).get("brand")) or "N/A", "note": _fmt_pct((sov_leader or {}).get("sov_pct"))},
                {"label": "SOE LEADER", "value": _clean((soe_leader or {}).get("brand")) or "N/A", "note": _fmt_pct((soe_leader or {}).get("soe_pct"))},
            ],
            "decision_implication": "Baca SOV dan SOE bersamaan: volume tinggi belum tentu efektif bila engagement share tertinggal.",
        },
        {
            "slide_no": 2,
            "title": "EXECUTIVE DECISION BRIEF",
            "subtitle": "Posisi kompetitif, gap utama, dan keputusan yang perlu diarahkan",
            "layout": "executive_decision_cards",
            "cards": [
                {"label": "SITUASI", "text": f"Scope memuat {_fmt_int(total_content)} konten dari {len(brands)} brand dalam competitive universe."},
                {"label": "LEADER BY SOV", "text": f"{_clean((sov_leader or {}).get('brand')) or 'N/A'} memimpin share of voice ({_fmt_pct((sov_leader or {}).get('sov_pct'))})."},
                {"label": "LEADER BY SOE", "text": f"{_clean((soe_leader or {}).get('brand')) or 'N/A'} memimpin share of engagement ({_fmt_pct((soe_leader or {}).get('soe_pct'))})."},
                {"label": "EFFICIENCY SIGNAL", "text": f"{_clean((efficiency_leader or {}).get('brand')) or 'N/A'} memiliki engagement per content tertinggi ({_fmt_metric((efficiency_leader or {}).get('engagement_per_content'))})."},
                {"label": "KEPUTUSAN 24/48H", "text": "Tentukan apakah prioritasnya defend visibility, close engagement gap, atau differentiate lewat whitespace topic/channel."},
            ],
            "evidence_policy": "Main deck memakai Evidence ID; buka Appendix/Data Pack untuk URL lengkap.",
        },
        {
            "slide_no": 3,
            "title": "COMPETITIVE ACTION PLAN",
            "subtitle": "Priority · focus · action · evidence ID",
            "layout": "action_cards_no_raw_url",
            "cards": action_plan,
            "url_policy": "No raw URLs on action plan. Use evidence_ref and Appendix URL index.",
        },
        {
            "slide_no": 4,
            "title": "COMPETITIVE LANDSCAPE",
            "subtitle": "SOV, SOE, dan engagement efficiency by brand",
            "layout": "benchmark_table_and_bars",
            "table": vol_rows,
            "interpretation": "Brand dengan SOV tinggi tapi SOE rendah butuh optimasi creative/channel, bukan sekadar tambah volume.",
        },
        {
            "slide_no": 5,
            "title": "SENTIMENT & COMPETITIVE TOPIC LANDSCAPE",
            "subtitle": "Risk/opportunity by brand — topic signal is LLM-classified",
            "layout": "sentiment_issue_matrix",
            "sentiment_table": sentiment_rows,
            "topic_table": topics,
            "caveat": "Topic/issue memakai cached LLM Competitive Topic/Narrative taxonomy dari Title + Content. Raw Topic Extraction tidak dipakai sebagai final topic.",
        },
        {
            "slide_no": 6,
            "title": "CHANNEL STRATEGY COMPARISON",
            "subtitle": "Channel mix by brand and engagement contribution",
            "layout": "channel_mix_cards",
            "table": channel_rows,
            "interpretation": "Gunakan channel dengan gap SOE terbesar sebagai prioritas optimasi, bukan semua channel sekaligus.",
        },
        {
            "slide_no": 7,
            "title": "CONTENT FORMAT BENCHMARK",
            "subtitle": "Content type / media type distribution by brand",
            "layout": "content_format_benchmark",
            "table": content_rows,
            "interpretation": "Format dengan engagement tinggi di kompetitor bisa menjadi benchmark, tapi tetap perlu brand-fit check.",
        },
        {
            "slide_no": 8,
            "title": "BEST PRACTICES & COMPETITIVE PLAYBOOK",
            "subtitle": "Apa yang bisa dipelajari dari top posts/authors tanpa menyalin mentah",
            "layout": "playbook_cards",
            "top_posts": [{k: row.get(k) for k in ("evidence_id", "brand", "author", "channel", "sentiment", "engagement", "content")} for row in top_posts[:10]],
            "top_authors": [{k: row.get(k) for k in ("evidence_id", "brand", "author", "channel", "sentiment", "engagement", "content")} for row in top_authors[:10]],
            "rule": "Use as benchmark inspiration; do not copy competitor creative/message without brand/legal review.",
        },
        {
            "slide_no": 9,
            "title": "SUPPORTING EVIDENCE INDEX",
            "subtitle": "Evidence ID untuk audit — main slides tidak menampilkan URL mentah",
            "layout": "evidence_id_index",
            "table": [{k: row.get(k) for k in ("evidence_id", "brand", "source", "channel", "sentiment", "metric", "content")} for row in evidence[:15]],
            "note": "Full URL berada di Appendix dan export_report_data_pack.",
        },
        {
            "slide_no": 10,
            "title": "APPENDIX — EVIDENCE URL INDEX",
            "subtitle": "Full URL hanya di appendix/data pack",
            "layout": "appendix_url_table",
            "table": evidence[:30],
        },
        {
            "slide_no": 11,
            "title": "SOURCES & NOTES",
            "subtitle": "Metric contract, limitations, and audit trail",
            "layout": "sources_notes",
            "scope": {
                "project": context.get("project_name"),
                "period": period,
                "client_brand": client,
                "competitors": competitors,
                "channels": context.get("channels"),
            },
            "metric_contract": metric.get("metric_contract"),
            "data_health": data_health,
            "topic_enrichment": dict((report_input.get("scope") or {}).get("competitive_topic_enrichment") or (report_input.get("scope") or {}).get("competitive_topic_enrichment_target") or {}),
            "limitations": limitations,
            "audit_tool": "Gunakan export_report_data_pack(report_input_id) untuk membuktikan angka/evidence tidak halu.",
        },
    ]

    outline = build_report_outline_from_id(report_input_id, allow_partial=allow_partial)
    return {
        "success": True,
        "report_type_id": REPORT_TYPE_ID,
        "render_package_version": RENDER_PACKAGE_VERSION,
        "package_id": _now_id("pkg_ca"),
        "report_input_id": report_input_id,
        "outline_id": outline.get("outline_id"),
        "outline_status": outline.get("outline_status"),
        "audience_context": audience,
        "context": context,
        "client_brand": client,
        "competitor_brands": competitors,
        "slides": slides,
        "evidence_url_policy": {
            "main_slides": "Use Evidence ID only; do not display raw URLs in action plan/executive/channel/issue slides.",
            "appendix": "Full URLs allowed.",
            "data_pack": "Full URLs required.",
        },
        "ppt_style_brief": {
            "tone": audience.get("tone"),
            "visual_direction": "executive consulting deck, card-based, benchmark matrix, LLM topic/narrative map, minimal raw URL display",
            "avoid": ["raw URL spam on main slides", "long tables without interpretation", "invented benchmarks", "using raw Topic Extraction/aspect/entity as final report source"],
            "preferred_components": ["decision cards", "SOV/SOE bars", "brand comparison matrix", "evidence ID badges", "appendix URL table"],
        },
        "claude_guardrails": [
            "Use only numbers and evidence from slides/report_input views.",
            "Do not invent competitor brands, metrics, URLs, quotes, or claims.",
            "Do not place raw URLs in Action Plan or Executive Summary; use Evidence IDs and Appendix URL index.",
            "Mention limitations when competitor universe or LLM topic/narrative coverage is incomplete.",
        ],
    }


__all__ = [
    "RENDER_PACKAGE_VERSION",
    "REPORT_TYPE_ID",
    "audience_clarification_payload",
    "competitors_clarification_payload",
    "normalize_audience_context",
    "build_competitive_analysis_report_data_preview",
    "build_competitive_analysis_report_package",
]
