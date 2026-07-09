"""Mainstream Media Report Task 2 renderer and data preview.

This renderer converts a frozen Task 1 `report_input_v1` package into a
PPT-ready package. It mirrors the Daily Social v5 UX:
- audience/reader-aware narrative guidance;
- Task 1 data preview before PPT;
- source URL surfaced on every evidence/article section when available;
- issue insights treated as smart-sample/cached LLM output, not raw Topic Extraction;
- no metric, quote, URL, headline, or issue fabrication.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from reporting.storage.report_input_store import get_report_input
from reporting.task2.report_outline_builder import build_report_outline_from_id

REPORT_TYPE_ID = "mainstream_media_report"
RENDER_PACKAGE_VERSION = "mainstream_media_report_render_package_v2"
SENTIMENTS = ("positive", "neutral", "negative")

CORE_STRUCTURE = [
    "Header / Identitas Report",
    "Executive Summary",
    "Media Response Action Plan",
    "Media Overview",
    "Top Issues & Topics",
    "Sensitive Issues",
    "Sentiment Analysis",
    "Spokesperson Overview",
    "Media Contributors",
    "Supporting Article Evidence",
    "Footer / Sources & Notes",
]


class MainstreamMediaRendererError(RuntimeError):
    """Raised when MMR Task 2 rendering cannot proceed safely."""


AUDIENCE_ALIASES = {
    "pr": "PR / Corporate Communications",
    "corcom": "PR / Corporate Communications",
    "corporate communication": "PR / Corporate Communications",
    "corporate communications": "PR / Corporate Communications",
    "media relations": "Media Relations",
    "media relation": "Media Relations",
    "media": "Media Relations",
    "insight": "Insight / Analyst Team",
    "insights": "Insight / Analyst Team",
    "analyst": "Insight / Analyst Team",
    "management": "Management",
    "manajemen": "Management",
    "ceo": "CEO / Board",
    "board": "CEO / Board",
    "direksi": "CEO / Board",
    "legal": "Legal / Crisis Team",
    "crisis": "Legal / Crisis Team",
    "crisis team": "Legal / Crisis Team",
    "marketing": "Marketing / Brand Team",
    "brand": "Marketing / Brand Team",
    "brand team": "Marketing / Brand Team",
}

AUDIENCE_GUIDANCE = {
    "PR / Corporate Communications": {
        "primary_question": "Apa risiko reputasi di media dan respons komunikasi apa yang paling aman?",
        "narrative_angle": "reputation risk, holding statement, clarification angle, media response priority",
        "preferred_outputs": ["response line", "risk framing", "article URLs", "media follow-up priority"],
        "avoid": "tabel panjang tanpa interpretasi komunikasi dan tanpa URL artikel sumber",
    },
    "Media Relations": {
        "primary_question": "Media mana yang perlu diprioritaskan untuk follow-up dan angle apa yang perlu diluruskan?",
        "narrative_angle": "publisher priority, article angle, media follow-up, journalist/editorial handling",
        "preferred_outputs": ["top media priority", "article links", "follow-up angle", "media watchlist"],
        "avoid": "rekomendasi terlalu umum tanpa pemetaan media dan artikel rujukan",
    },
    "Insight / Analyst Team": {
        "primary_question": "Pola exposure, issue, sentiment, dan caveat data apa yang perlu dicatat?",
        "narrative_angle": "data pattern, issue/sentiment relationship, PR value distribution, methodology caveat",
        "preferred_outputs": ["metric readout", "issue coverage", "evidence audit", "method caveat"],
        "avoid": "action komunikasi yang terlalu normatif tanpa bukti data",
    },
    "Management": {
        "primary_question": "Apa implikasi bisnis/reputasi dan keputusan apa yang perlu diarahkan?",
        "narrative_angle": "executive risk posture, business implication, priority decision, next 24/48h action",
        "preferred_outputs": ["executive posture", "decision needed", "top risks", "recommended owner action"],
        "avoid": "detail teknis yang terlalu granular untuk keputusan manajemen",
    },
    "CEO / Board": {
        "primary_question": "Apakah exposure media ini butuh perhatian eksekutif dan apa implikasi strategisnya?",
        "narrative_angle": "board-level risk, high-level media exposure, strategic implication, concise next decision",
        "preferred_outputs": ["one-page brief", "risk level", "why it matters", "high-impact evidence"],
        "avoid": "operasional media monitoring yang terlalu detail",
    },
    "Legal / Crisis Team": {
        "primary_question": "Artikel/isu mana yang berisiko secara krisis/legal dan perlu guardrail respons?",
        "narrative_angle": "sensitive claim, allegation framing, crisis escalation, safe response guardrails",
        "preferred_outputs": ["sensitive article URLs", "risky wording", "holding line", "escalation trigger"],
        "avoid": "mengubah fakta artikel atau memberi klaim legal tanpa bukti",
    },
    "Marketing / Brand Team": {
        "primary_question": "Bagaimana exposure media memengaruhi persepsi brand dan narasi positif apa yang aman diamplifikasi?",
        "narrative_angle": "brand perception, positive narrative, content opportunity, brand safety",
        "preferred_outputs": ["brand perception", "amplification opportunity", "message risk", "article evidence"],
        "avoid": "amplifikasi positif yang tone-deaf saat issue negatif dominan",
    },
    "General Business User": {
        "primary_question": "Apa yang terjadi di media, kenapa penting, dan apa tindakan berikutnya?",
        "narrative_angle": "plain-language media summary, risk, action, evidence",
        "preferred_outputs": ["summary", "action plan", "top articles", "limitations"],
        "avoid": "jargon teknis yang tidak dijelaskan",
    },
}


def _clean(value: Any, limit: int | None = None) -> str:
    text = " ".join(str(value or "").strip().split())
    if limit and len(text) > limit:
        return text[: max(0, limit - 1)].rstrip() + "…"
    return text


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
    return {
        "audience": label,
        "raw_audience_input": raw or None,
        "primary_question": guidance["primary_question"],
        "narrative_angle": guidance["narrative_angle"],
        "preferred_outputs": list(guidance["preferred_outputs"]),
        "avoid": guidance["avoid"],
        "tone": "executive, direct, evidence-backed" if label in {"Management", "CEO / Board"} else "clear, action-oriented, evidence-backed",
    }


def audience_clarification_payload(project_name: str | None = None, period_label: str | None = None) -> dict[str, Any]:
    target = f" untuk {project_name}" if project_name else ""
    period = f" periode {period_label}" if period_label else ""
    return {
        "success": False,
        "workflow_status": "NEEDS_AUDIENCE",
        "needs_clarification": True,
        "clarification_question": (
            f"Mainstream Media Report{target}{period} ini dibuat untuk siapa? "
            "Pilih salah satu: PR/Corcom, Media Relations, tim Insight, Management, CEO/Board, Legal/Crisis Team, atau Marketing/Brand."
        ),
        "why_needed": "Audience menentukan POV analisis, depth narasi, action plan, dan tipe evidence yang ditonjolkan.",
        "suggested_audiences": [
            "PR / Corporate Communications",
            "Media Relations",
            "Insight / Analyst Team",
            "Management",
            "CEO / Board",
            "Legal / Crisis Team",
            "Marketing / Brand Team",
        ],
        "example_user_reply": "Untuk tim PR/Corcom.",
    }


def _now_id(prefix: str) -> str:
    return f"{prefix}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid4().hex[:8]}"


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _rows(report_input: Mapping[str, Any], view_id: str) -> list[dict[str, Any]]:
    views = _as_mapping(report_input.get("quantitative_views"))
    if view_id not in views:
        views = _as_mapping(report_input.get("qualitative_views"))
    view = _as_mapping(views.get(view_id))
    rows = view.get("rows")
    return [dict(row) for row in rows] if isinstance(rows, list) else []


def _view_status(report_input: Mapping[str, Any], view_id: str) -> dict[str, Any]:
    views = _as_mapping(report_input.get("quantitative_views"))
    view_type = "quantitative"
    if view_id not in views:
        views = _as_mapping(report_input.get("qualitative_views"))
        view_type = "qualitative"
    view = _as_mapping(views.get(view_id))
    meta = _as_mapping(view.get("metadata"))
    rows = view.get("rows")
    return {
        "view_id": view_id,
        "view_type": view_type,
        "status": str(meta.get("status") or "READY"),
        "reason": meta.get("reason"),
        "row_count": len(rows) if isinstance(rows, list) else 0,
        "metadata": dict(meta),
    }


def _num(value: Any) -> float:
    try:
        if value is None or value == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        text = str(value).replace("Rp", "").replace("IDR", "").replace(".", "").replace(",", ".")
        try:
            return float(text)
        except Exception:
            return 0.0


def _fmt_int(value: Any) -> str:
    return f"{int(round(_num(value))):,}".replace(",", ".")


def _fmt_num(value: Any, digits: int = 1) -> str:
    value = _num(value)
    if abs(value - round(value)) < 0.0001:
        return _fmt_int(value)
    return f"{value:,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _fmt_money(value: Any) -> str:
    value = _num(value)
    if not value:
        return "N/A"
    return "Rp" + _fmt_int(value)


def _fmt_pct(value: Any) -> str:
    if value is None:
        return "N/A"
    return f"{_num(value):.1f}%".replace(".", ",")


def _url(row: Mapping[str, Any]) -> str | None:
    for key in ("source_url", "top_article_url", "article_url", "url", "link_url"):
        value = row.get(key)
        if value:
            return str(value).strip()
    return None


def _source_ref(row: Mapping[str, Any]) -> dict[str, Any]:
    url = _url(row)
    return {
        "title": _clean(row.get("title") or row.get("top_article_title"), 180),
        "media_name": row.get("media_name") or row.get("top_article_media"),
        "channel": row.get("channel"),
        "source_url": url,
        "url": url,
        "url_available": bool(url),
        "sentiment": row.get("sentiment") or row.get("dominant_sentiment"),
        "issue_label": row.get("issue_label") or row.get("topic") or row.get("top_issue"),
        "content_snippet": _clean(row.get("content_snippet") or row.get("snippet"), 360),
        "ad_value": row.get("ad_value") or row.get("total_ad_value"),
        "pr_value": row.get("pr_value") or row.get("total_pr_value"),
    }


def _source_label(ref: Mapping[str, Any]) -> str:
    media = _clean(ref.get("media_name"), 70) or "Unknown media"
    title = _clean(ref.get("title"), 90) or "Untitled article"
    return f"{media} — {title}"


def _top(rows: list[dict[str, Any]], key: str, limit: int = 1) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: _num(row.get(key)), reverse=True)[:limit]


def _kpi(report_input: Mapping[str, Any]) -> dict[str, Any]:
    row = (_rows(report_input, "qt_mm_kpi_tiles") or [{}])[0]
    return {
        "total_articles": int(_num(row.get("total_articles") or row.get("total_news"))),
        "total_media": int(_num(row.get("total_media"))),
        "total_ad_value": _num(row.get("total_ad_value")),
        "total_pr_value": _num(row.get("total_pr_value")),
        "total_readership": _num(row.get("total_readership")),
        "total_circulation": _num(row.get("total_circulation")),
        "dominant_sentiment": row.get("dominant_sentiment"),
        "media_posture": row.get("media_posture") or "UNKNOWN",
        "net_sentiment": row.get("net_sentiment"),
        "issue_taxonomy_version": row.get("issue_taxonomy_version"),
        "issue_coverage_pct": row.get("issue_coverage_pct"),
    }


def _sentiment(report_input: Mapping[str, Any]) -> dict[str, Any]:
    rows = _rows(report_input, "qt_mm_sentiment_distribution")
    by = {str(row.get("sentiment") or "").casefold(): row for row in rows}
    return {
        "rows": rows,
        "positive_pct": by.get("positive", {}).get("share_pct"),
        "neutral_pct": by.get("neutral", {}).get("share_pct"),
        "negative_pct": by.get("negative", {}).get("share_pct"),
        "positive_count": by.get("positive", {}).get("article_count"),
        "neutral_count": by.get("neutral", {}).get("article_count"),
        "negative_count": by.get("negative", {}).get("article_count"),
    }


def _posture(kpi: Mapping[str, Any], sent: Mapping[str, Any]) -> dict[str, Any]:
    label = str(kpi.get("media_posture") or "").strip() or "UNKNOWN"
    neg = _num(sent.get("negative_pct"))
    net = _num(kpi.get("net_sentiment"))
    if "RED" in label.upper() or neg >= 40 or net <= -20:
        return {"label": "RED / HIGH RISK", "short_label": "HIGH RISK", "severity": "red", "rationale": "Porsi artikel negatif tinggi atau net sentiment negatif signifikan."}
    if "AMBER" in label.upper() or neg >= 25 or net < 0:
        return {"label": "AMBER / WATCH", "short_label": "WATCH", "severity": "amber", "rationale": "Ada tekanan media negatif yang perlu dipantau."}
    return {"label": "GREEN / STABLE", "short_label": "STABLE", "severity": "green", "rationale": "Tone media relatif stabil pada scope ini."}


def _issue_coverage_note(kpi: Mapping[str, Any]) -> dict[str, Any]:
    cov = _num(kpi.get("issue_coverage_pct"))
    if cov <= 0:
        return {"level": "missing", "message": "Issue enrichment belum tersedia; issue-based analysis akan N/A sampai smart sample dijalankan.", "safe_for_issue_conclusion": False}
    if cov < 60:
        return {"level": "low", "message": f"Issue coverage baru {_fmt_pct(cov)}; issue insight hanya early classified signal, belum representatif penuh.", "safe_for_issue_conclusion": False}
    if cov < 90:
        return {"level": "partial", "message": f"Issue coverage {_fmt_pct(cov)}; cukup untuk directional readout dengan caveat.", "safe_for_issue_conclusion": True}
    return {"level": "complete", "message": f"Issue coverage {_fmt_pct(cov)}; issue ranking aman dipakai sebagai report readout.", "safe_for_issue_conclusion": True}


def _table_markdown(rows: list[Mapping[str, Any]], columns: list[str], limit: int = 10) -> str:
    selected = rows[:limit]
    if not selected:
        return "N/A\n"
    out = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in selected:
        vals = [_clean(row.get(col), 160) for col in columns]
        out.append("| " + " | ".join(vals) + " |")
    return "\n".join(out) + "\n"


def build_mainstream_media_report_data_preview(report_input_id: str, include_evidence_limit: int = 10) -> dict[str, Any]:
    report_input = get_report_input(report_input_id)
    if not report_input:
        raise MainstreamMediaRendererError(f"report_input_id tidak ditemukan: {report_input_id}")
    if report_input.get("report_type_id") != REPORT_TYPE_ID:
        raise MainstreamMediaRendererError(f"report_input_id bukan mainstream_media_report: {report_input.get('report_type_id')}")

    kpi = _kpi(report_input)
    sent = _sentiment(report_input)
    posture = _posture(kpi, sent)
    coverage = _issue_coverage_note(kpi)
    limitations = list(report_input.get("limitations") or [])
    readiness = "READY"
    if coverage["level"] in {"missing", "low"}:
        readiness = "READY_WITH_ISSUE_CAVEAT"
    elif limitations:
        readiness = "READY_WITH_LIMITATIONS"

    channel_rows = _rows(report_input, "qt_mm_channel_distribution")
    sentiment_matrix = _rows(report_input, "qt_mm_sentiment_matrix_by_channel")
    issue_rows = _rows(report_input, "qt_mm_main_topics_top3")
    media_rows = _rows(report_input, "qt_mm_media_contributors_table")
    spokesperson_rows = _rows(report_input, "qt_mm_spokesperson_overview")
    enriched = _rows(report_input, "ql_mm_article_enriched")
    sensitive = _rows(report_input, "ql_mm_headlines_summary")
    top_issue_cards = _rows(report_input, "ql_mm_top_issues_cards")
    sentiment_issue_cards = _rows(report_input, "ql_mm_sentiment_issue_cards")

    scope = _as_mapping(report_input.get("scope"))
    md: list[str] = []
    md.append(f"# Mainstream Media Data Preview — {report_input.get('project_name')}\n")
    md.append(f"**Period:** {report_input.get('start_date')} → {report_input.get('end_date')}  ")
    md.append(f"**Readiness:** {readiness}  ")
    md.append(f"**Posture:** {posture['label']}  ")
    md.append(f"**Issue handling:** {coverage['message']}  ")
    md.append(f"**Issue taxonomy:** {scope.get('issue_taxonomy_version') or scope.get('topic_taxonomy_version') or 'N/A'}\n")

    md.append("## 1. KPI Summary\n")
    md.append("| Metric | Value |\n|---|---:|\n")
    md.append(f"| Total articles | {_fmt_int(kpi['total_articles'])} |\n")
    md.append(f"| Total media | {_fmt_int(kpi['total_media'])} |\n")
    md.append(f"| Total PR Value | {_fmt_money(kpi['total_pr_value'])} |\n")
    md.append(f"| Total Ad Value | {_fmt_money(kpi['total_ad_value'])} |\n")
    md.append(f"| Net sentiment | {_fmt_num(kpi.get('net_sentiment'))} |\n")

    md.append("\n## 2. Channel / Media Type Distribution\n")
    md.append(_table_markdown(channel_rows, ["channel", "article_count", "share_pct", "pr_value", "ad_value"], 10))

    md.append("\n## 3. Sentiment Distribution\n")
    md.append(_table_markdown(_rows(report_input, "qt_mm_sentiment_distribution"), ["sentiment", "article_count", "share_pct", "pr_value", "ad_value"], 10))

    md.append("\n## 4. Top Issues / Topics\n")
    if issue_rows:
        md.append(_table_markdown(issue_rows, ["rank", "issue_label", "article_count", "share_pct", "dominant_sentiment", "pr_value", "top_article_url"], 10))
    else:
        md.append("N/A — issue taxonomy/cache belum tersedia atau smart sample belum cukup.\n")

    md.append("\n## 5. Top Media Contributors\n")
    md.append(_table_markdown(media_rows, ["rank", "media_name", "channel", "article_count", "pr_value", "dominant_sentiment", "top_issue", "top_article_url"], 10))

    md.append("\n## 6. Spokesperson Overview\n")
    if spokesperson_rows:
        md.append(_table_markdown(spokesperson_rows, ["rank", "spokesperson", "article_count", "dominant_sentiment", "top_media", "top_article_url"], 10))
    else:
        status = _view_status(report_input, "qt_mm_spokesperson_overview")
        md.append(f"N/A — {status.get('reason') or 'field spokesperson tidak tersedia.'}\n")

    md.append("\n## 7. High-impact / Sensitive Headlines + URL\n")
    if sensitive:
        for row in sensitive[: int(include_evidence_limit)]:
            md.append(
                f"- **{_clean(row.get('title'), 150)}** — {_clean(row.get('media_name'), 80)}; "
                f"sentiment: {row.get('sentiment')}; PR Value: {_fmt_money(row.get('pr_value'))}; "
                f"URL: {_url(row) or 'N/A'}; reason: {_clean(row.get('why_sensitive'), 140)}\n"
            )
    else:
        md.append("N/A\n")

    md.append("\n## 8. Article Evidence Table + URL\n")
    if enriched:
        for row in enriched[: int(include_evidence_limit)]:
            md.append(
                f"- **{_clean(row.get('title'), 140)}** — {_clean(row.get('media_name'), 80)}; "
                f"{row.get('sentiment')}; PR Value: {_fmt_money(row.get('pr_value'))}; URL: {_url(row) or 'N/A'}\n"
            )
    else:
        md.append("N/A\n")

    md.append("\n## 9. Readiness Recommendation\n")
    if coverage["level"] in {"missing", "low"}:
        md.append("Data KPI/sentiment/media/article evidence siap. Issue-based insight perlu dibaca sebagai early signal sampai smart issue sample selesai.\n")
    else:
        md.append("Data cukup untuk dibuat PPT dengan caveat metodologi yang tetap ditampilkan.\n")
    if limitations:
        md.append("\n## 10. Limitations\n")
        for item in limitations:
            md.append(f"- {_clean(item, 260)}\n")

    return {
        "success": True,
        "preview_id": _now_id("mmr_data_preview"),
        "report_input_id": report_input_id,
        "report_type_id": REPORT_TYPE_ID,
        "readiness": readiness,
        "posture": posture,
        "kpi": kpi,
        "sentiment": sent,
        "issue_coverage_note": coverage,
        "view_status": [_view_status(report_input, vid) for vid in (
            "qt_mm_kpi_tiles", "qt_mm_channel_distribution", "qt_mm_sentiment_distribution",
            "qt_mm_main_topics_top3", "qt_mm_sentiment_matrix_by_channel", "qt_mm_spokesperson_overview",
            "qt_mm_media_contributors_table", "ql_mm_article_enriched", "ql_mm_top_issues_cards",
            "ql_mm_sentiment_issue_cards", "ql_mm_headlines_summary",
        )],
        "top_issues": issue_rows,
        "top_media": media_rows,
        "high_impact_articles": sensitive[: int(include_evidence_limit)],
        "article_evidence": enriched[: int(include_evidence_limit)],
        "issue_cards": top_issue_cards,
        "sentiment_issue_cards": sentiment_issue_cards,
        "limitations": limitations,
        "markdown": "".join(md),
    }


def _build_executive_summary(report_input: Mapping[str, Any]) -> dict[str, Any]:
    kpi = _kpi(report_input)
    sent = _sentiment(report_input)
    posture = _posture(kpi, sent)
    coverage = _issue_coverage_note(kpi)
    top_media = (_rows(report_input, "qt_mm_media_contributors_table") or [{}])[0]
    top_issue = (_rows(report_input, "qt_mm_main_topics_top3") or [{}])[0]
    sensitive = (_rows(report_input, "ql_mm_headlines_summary") or [{}])[0]

    situation = f"Media mainstream mencatat {_fmt_int(kpi['total_articles'])} artikel dari {_fmt_int(kpi['total_media'])} media pada periode ini."
    value = f"Total PR Value tercatat {_fmt_money(kpi['total_pr_value'])}; Ad Value {_fmt_money(kpi['total_ad_value'])}."
    risk = f"Posture media berada di {posture['label']} dengan net sentiment {_fmt_num(kpi.get('net_sentiment'))}."
    if top_issue:
        issue = f"Issue utama: {_clean(top_issue.get('issue_label'), 90)} ({_fmt_int(top_issue.get('article_count'))} artikel classified; PR Value {_fmt_money(top_issue.get('pr_value'))})."
    else:
        issue = "Issue utama belum tersedia karena issue taxonomy/cache belum lengkap."
    if top_media:
        media = f"Media contributor terbesar: {_clean(top_media.get('media_name'), 80)} ({_fmt_int(top_media.get('article_count'))} artikel; PR Value {_fmt_money(top_media.get('pr_value'))})."
    else:
        media = "Media contributor utama belum tersedia."
    implication = "Prioritas 24/48 jam: cek artikel berisiko, siapkan response line, dan tentukan media follow-up berdasarkan evidence URL."

    return {
        "posture": posture,
        "kpi_cards": [
            {"label": "Total Articles", "value": _fmt_int(kpi["total_articles"]), "note": "canonical mainstream articles"},
            {"label": "Total Media", "value": _fmt_int(kpi["total_media"]), "note": "unique publishers"},
            {"label": "Total PR Value", "value": _fmt_money(kpi["total_pr_value"]), "note": "if available"},
            {"label": "Net Sentiment", "value": _fmt_num(kpi.get("net_sentiment")), "note": "positive % - negative %"},
        ],
        "bullets": [situation, value, risk, issue, media],
        "executive_readout": {
            "situation": situation,
            "exposure_value": value,
            "risk_diagnosis": risk,
            "issue_readout": issue,
            "business_implication": implication,
            "issue_coverage_note": coverage["message"],
        },
        "top_issue": top_issue,
        "top_media": top_media,
        "top_sensitive_article": sensitive,
        "coverage_note": coverage,
    }


def _make_action(priority: str, action_type: str, focus_area: str, recommended_action: str, rationale: str, evidence: Mapping[str, Any], expected_impact: str, owner_next_step: str) -> dict[str, Any]:
    ref = _source_ref(evidence)
    return {
        "priority": priority,
        "action_type": action_type,
        "focus_area": focus_area,
        "recommended_action": recommended_action,
        "rationale": rationale,
        "supporting_evidence": _source_label(ref),
        "expected_impact": expected_impact,
        "owner_next_step": owner_next_step,
        "evidence_refs": [ref] if ref else [],
        "evidence_urls": [ref.get("source_url")] if ref.get("source_url") else [],
        "requires_url_in_ppt": True,
    }


def _build_action_plan(report_input: Mapping[str, Any]) -> list[dict[str, Any]]:
    sensitive = _rows(report_input, "ql_mm_headlines_summary")
    issues = _rows(report_input, "qt_mm_main_topics_top3")
    media = _rows(report_input, "qt_mm_media_contributors_table")
    articles = _rows(report_input, "ql_mm_article_enriched")
    neg_articles = [row for row in articles if str(row.get("sentiment") or "").casefold() == "negative"]
    pos_articles = [row for row in articles if str(row.get("sentiment") or "").casefold() == "positive"]

    evidence_risk = (neg_articles or sensitive or articles or [{}])[0]
    evidence_issue = (issues or sensitive or articles or [{}])[0]
    evidence_media = (media or articles or [{}])[0]
    evidence_pos = (pos_articles or articles or [{}])[0]

    return [
        _make_action(
            "HIGH",
            "Prioritize Issue Response",
            _clean(evidence_issue.get("issue_label") or evidence_issue.get("topic") or "Issue utama", 90),
            "Siapkan response line berbasis fakta artikel: apa yang terjadi, posisi perusahaan, proses tindak lanjut, dan kanal update resmi.",
            "Issue/media exposure perlu ditangani dengan narasi konsisten agar tidak berkembang menjadi interpretasi liar.",
            evidence_risk,
            "Mengurangi risiko framing negatif berulang di media dan kanal turunan.",
            "PR/Corcom: review 3 artikel paling sensitif dan finalisasi holding line hari ini.",
        ),
        _make_action(
            "HIGH" if neg_articles else "MEDIUM",
            "Prepare Holding Statement",
            "Sensitive / high-impact headlines",
            "Buat holding statement pendek yang aman: empati, fakta yang sudah terkonfirmasi, proses investigasi/penanganan, dan contact point resmi.",
            "Artikel sensitif perlu respons yang tidak over-claim dan tidak menambah risiko legal/reputasi.",
            evidence_risk,
            "Menjaga konsistensi jawaban bila media meminta klarifikasi lanjutan.",
            "PR + Legal/Crisis: setujui red line dan FAQ respons sebelum distribusi.",
        ),
        _make_action(
            "MEDIUM",
            "Target Media Contributors",
            _clean(evidence_media.get("media_name") or "Top media contributors", 90),
            "Prioritaskan monitoring/follow-up pada media dengan artikel/value tertinggi dan cek apakah angle pemberitaan sudah akurat.",
            "Media contributor utama menentukan persebaran narasi mainstream dan rujukan media lain.",
            evidence_media,
            "Membantu menentukan media mana yang perlu diluruskan, diupdate, atau diamplifikasi.",
            "Media Relations: buat daftar top media + URL artikel untuk follow-up selektif.",
        ),
        _make_action(
            "MEDIUM",
            "Strengthen Positive Narrative",
            "Positive / constructive coverage",
            "Amplifikasi coverage positif hanya bila tidak tone-deaf terhadap issue utama; gunakan angle yang faktual dan relevan.",
            "Positive coverage bisa menyeimbangkan exposure, tapi harus tetap aman secara reputasi.",
            evidence_pos,
            "Memperkuat pesan positif tanpa mengabaikan risiko utama.",
            "Brand/Comms: pilih 1–2 artikel positif untuk amplification internal/owned channel setelah risk review.",
        ),
        _make_action(
            "MEDIUM",
            "Monitor Follow-up",
            "Next 24/48h media watch",
            "Pantau artikel lanjutan dengan keyword issue utama, media prioritas, dan perubahan tone negatif/positif.",
            "Mainstream issue sering berkembang melalui follow-up article dan syndicated pickup.",
            evidence_risk,
            "Memberi early warning sebelum framing negatif menguat.",
            "Insight/Monitoring: set watchlist issue + media + URL evidence dan update jika ada headline baru.",
        ),
    ]


def _build_slides(report_input: Mapping[str, Any], outline: Mapping[str, Any], audience: Mapping[str, Any]) -> list[dict[str, Any]]:
    kpi = _kpi(report_input)
    sent = _sentiment(report_input)
    summary = _build_executive_summary(report_input)
    actions = _build_action_plan(report_input)
    issue_rows = _rows(report_input, "qt_mm_main_topics_top3")
    channel_rows = _rows(report_input, "qt_mm_channel_distribution")
    sentiment_rows = _rows(report_input, "qt_mm_sentiment_distribution")
    matrix_rows = _rows(report_input, "qt_mm_sentiment_matrix_by_channel")
    media_rows = _rows(report_input, "qt_mm_media_contributors_table")
    spokesperson_rows = _rows(report_input, "qt_mm_spokesperson_overview")
    sensitive = _rows(report_input, "ql_mm_headlines_summary")
    articles = _rows(report_input, "ql_mm_article_enriched")
    issue_cards = _rows(report_input, "ql_mm_top_issues_cards")
    sentiment_issue = _rows(report_input, "ql_mm_sentiment_issue_cards")
    limitations = list(report_input.get("limitations") or [])
    coverage = _issue_coverage_note(kpi)

    slides: list[dict[str, Any]] = [
        {
            "slide_id": "mmr_00_header",
            "section": CORE_STRUCTURE[0],
            "title": "MAINSTREAM MEDIA REPORT",
            "subtitle": f"{report_input.get('project_name')} · {report_input.get('start_date')} to {report_input.get('end_date')}",
            "audience_context": audience,
            "kpi_cards": summary["kpi_cards"],
            "posture": summary["posture"],
            "speaker_note": "Opening slide. Keep it executive and media-response oriented.",
        },
        {
            "slide_id": "mmr_01_executive_summary",
            "section": CORE_STRUCTURE[1],
            "title": "EXECUTIVE SUMMARY",
            "subtitle": "What happened in media, why it matters, and what needs attention.",
            "audience_context": audience,
            "posture": summary["posture"],
            "bullets": summary["bullets"],
            "executive_readout": summary["executive_readout"],
            "top_issue": summary.get("top_issue"),
            "top_media": summary.get("top_media"),
        },
        {
            "slide_id": "mmr_02_media_response_action_plan",
            "section": CORE_STRUCTURE[2],
            "title": "MEDIA RESPONSE ACTION PLAN",
            "subtitle": "Prioritized actions based on mainstream exposure and evidence articles.",
            "audience_context": audience,
            "actions": actions,
            "must_show_evidence_url": True,
        },
        {
            "slide_id": "mmr_03_media_overview",
            "section": CORE_STRUCTURE[3],
            "title": "MEDIA OVERVIEW",
            "subtitle": "Article volume, media type distribution, and exposure value.",
            "kpi": kpi,
            "channel_distribution": channel_rows,
            "sentiment_distribution": sentiment_rows,
        },
        {
            "slide_id": "mmr_04_top_issues_topics",
            "section": CORE_STRUCTURE[4],
            "title": "TOP ISSUES & TOPICS",
            "subtitle": "LLM issue taxonomy from Title + Content; raw Topic Extraction is not used as final issue.",
            "available": bool(issue_rows),
            "coverage_note": coverage,
            "issue_rows": issue_rows,
            "issue_cards": issue_cards,
            "render_guidance": "If coverage is low, label as early classified issue signal.",
        },
        {
            "slide_id": "mmr_05_sensitive_issues",
            "section": CORE_STRUCTURE[5],
            "title": "SENSITIVE ISSUES",
            "subtitle": "High-impact or risk-sensitive headlines requiring communication attention.",
            "sensitive_articles": sensitive[:8],
            "must_show_url": True,
        },
        {
            "slide_id": "mmr_06_sentiment_analysis",
            "section": CORE_STRUCTURE[6],
            "title": "SENTIMENT ANALYSIS",
            "subtitle": "Overall tone and sentiment matrix by media type/channel.",
            "sentiment_distribution": sentiment_rows,
            "sentiment_matrix_by_channel": matrix_rows,
            "sentiment_issue_cards": sentiment_issue,
            "readout": f"Dominant sentiment: {kpi.get('dominant_sentiment')}; net sentiment: {_fmt_num(kpi.get('net_sentiment'))}.",
        },
        {
            "slide_id": "mmr_07_spokesperson_overview",
            "section": CORE_STRUCTURE[7],
            "title": "SPOKESPERSON OVERVIEW",
            "subtitle": "Named spokesperson/narasumber coverage when field is available.",
            "available": bool(spokesperson_rows),
            "rows": spokesperson_rows,
            "view_status": _view_status(report_input, "qt_mm_spokesperson_overview"),
        },
        {
            "slide_id": "mmr_08_media_contributors",
            "section": CORE_STRUCTURE[8],
            "title": "MEDIA CONTRIBUTORS",
            "subtitle": "Top publishers/media by article count and exposure value.",
            "rows": media_rows,
            "must_show_url": True,
        },
        {
            "slide_id": "mmr_09_supporting_article_evidence",
            "section": CORE_STRUCTURE[9],
            "title": "SUPPORTING ARTICLE EVIDENCE",
            "subtitle": "Article evidence with source URLs for audit and follow-up.",
            "articles": articles[:10],
            "sensitive_articles": sensitive[:5],
            "must_show_url": True,
        },
    ]

    if summary["posture"].get("severity") == "red" and sensitive:
        slides.append(
            {
                "slide_id": "mmr_10_critical_issue_deep_dive",
                "section": "Optional Deep Dive",
                "title": "CRITICAL ISSUE DEEP DIVE",
                "subtitle": "Why the highest-risk article/issue matters and what to monitor next.",
                "lead_article": sensitive[0],
                "related_articles": sensitive[1:6],
                "risk_questions": [
                    "Is the headline framing factual, speculative, or accusatory?",
                    "Does the article require clarification, follow-up, or monitoring only?",
                    "Which official response line should be used if media asks for comment?",
                ],
                "must_show_url": True,
            }
        )

    slides.append(
        {
            "slide_id": "mmr_11_article_url_appendix",
            "section": "Appendix",
            "title": "APPENDIX — ARTICLE EVIDENCE LINKS",
            "subtitle": "Top article URLs used as supporting evidence.",
            "article_links": [{"title": row.get("title"), "media_name": row.get("media_name"), "sentiment": row.get("sentiment"), "source_url": _url(row)} for row in articles[:15]],
        }
    )

    slides.append(
        {
            "slide_id": "mmr_12_footer_sources_notes",
            "section": CORE_STRUCTURE[10],
            "title": "SOURCES & NOTES",
            "subtitle": "Data source, metric contract, limitations, and AI-assisted note.",
            "scope": {
                "project": report_input.get("project_name"),
                "period": f"{report_input.get('start_date')} → {report_input.get('end_date')}",
                "source": "Cogan canonical mainstream media articles",
                "issue_taxonomy": kpi.get("issue_taxonomy_version") or "N/A",
            },
            "metric_contract": [
                "Primary volume metric: article count / news count.",
                "Exposure metrics: PR Value, Ad Value, readership, circulation if available.",
                "Raw Topic Extraction is diagnostic only; final report issue uses LLM issue taxonomy from Title + Content.",
                "Article URL must be displayed for evidence where available.",
            ],
            "limitations": limitations + [coverage["message"]],
        }
    )
    return slides


def build_mainstream_media_report_package(
    report_input_id: str,
    allow_partial: bool = True,
    audience_context: str | None = None,
    audience_pov: str | None = None,
) -> dict[str, Any]:
    report_input = get_report_input(report_input_id)
    if not report_input:
        raise MainstreamMediaRendererError(f"report_input_id tidak ditemukan: {report_input_id}")
    if report_input.get("report_type_id") != REPORT_TYPE_ID:
        raise MainstreamMediaRendererError(f"report_input_id bukan mainstream_media_report: {report_input.get('report_type_id')}")

    outline = build_report_outline_from_id(report_input_id, allow_partial=allow_partial)
    audience = normalize_audience_context(audience_context, audience_pov)
    preview = build_mainstream_media_report_data_preview(report_input_id)
    slides = _build_slides(report_input, outline, audience)

    return {
        "success": True,
        "render_package_id": _now_id("mmr_render_package"),
        "render_package_version": RENDER_PACKAGE_VERSION,
        "report_type_id": REPORT_TYPE_ID,
        "report_input_id": report_input_id,
        "outline_id": outline.get("outline_id"),
        "outline_status": outline.get("outline_status"),
        "audience_context": audience,
        "pre_ppt_data_preview": preview,
        "core_structure": CORE_STRUCTURE,
        "slides": slides,
        "limitations": preview.get("limitations") or [],
        "ppt_style_brief": {
            "language": "Indonesian, with English section headers allowed",
            "tone": audience.get("tone"),
            "structure_rule": "Action Plan must appear immediately after Executive Summary.",
            "must_follow": [
                f"Write for {audience['audience']}; answer: {audience['primary_question']}",
                "Use article_count/news count as primary volume metric, not interactions.",
                "Show source_url/article URL on evidence, action plan, high-impact articles, and appendix slides.",
                "Do not use raw Topic Extraction as final issue/topic; use issue taxonomy/cache only.",
                "If issue coverage is low, label issue insight as early classified issue signal.",
                "Do not fabricate headlines, quotes, PR Value, URLs, media names, issues, or spokespersons.",
            ],
        },
        "claude_instructions": [
            "Show data preview before PPTX unless user has already confirmed it.",
            "Use slides array as the source of truth for PPT content and order.",
            "Adapt narrative to audience_context but do not change metrics/evidence.",
            "Every evidence/article card should include URL when source_url is available.",
            "Keep Media Response Action Plan directly after Executive Summary.",
        ],
    }


__all__ = [
    "MainstreamMediaRendererError",
    "audience_clarification_payload",
    "normalize_audience_context",
    "build_mainstream_media_report_data_preview",
    "build_mainstream_media_report_package",
]


# ---------------------------------------------------------------------------
# v2 quality overlay: crisis/legal readout, noise guard, richer action plan.
# These definitions intentionally override selected v1 functions above while
# keeping the public API stable for the existing server hooks.
# ---------------------------------------------------------------------------

_BUILD_MMR_PREVIEW_V1 = build_mainstream_media_report_data_preview

RENDER_PACKAGE_VERSION = "mainstream_media_report_render_package_v2"

RISK_KEYWORDS = (
    "audit", "bpkn", "ylki", "dpr", "cabut izin", "izin", "regulator",
    "investigasi", "dugaan", "diduga", "bohong", "menipu", "pembohongan",
    "menyesatkan", "klaim", "label", "sumur bor", "air tanah", "lingkungan",
    "tuntut", "desak", "krisis", "klarifikasi", "gugatan", "pelanggaran",
)

NOISE_KEYWORDS = (
    "kkb", "sandra dewi", "harvey", "biji kakao", "alat kelamin", "janda",
    "lampung", "aksi kamisan", "amnesty", "ktt iklim", "prabowo", "papua",
    "korupsi anggaran penelitian", "saldo dana", "macet bandung",
)

ALLEGATION_KEYWORDS = (
    "dugaan", "diduga", "menipu", "bohong", "pembohongan", "menyesatkan",
    "klaim", "audit", "cabut izin", "sumur bor", "air tanah", "penyesatan",
)

OFFICIAL_RESPONSE_KEYWORDS = (
    "klarifikasi", "buka suara", "respons", "tanggapan", "menjelaskan",
    "danone jelaskan", "manajemen", "esdm", "pemerintah", "resmi",
)


def _text_blob(row: Mapping[str, Any]) -> str:
    return " ".join(
        _clean(row.get(key))
        for key in (
            "title", "top_article_title", "content_snippet", "snippet", "why_sensitive",
            "issue_label", "topic", "media_name", "source_url", "url",
        )
    ).casefold()


def _is_noise_article(row: Mapping[str, Any]) -> bool:
    blob = _text_blob(row)
    issue = _clean(row.get("issue_label") or row.get("topic") or row.get("dominant_issue")).casefold()
    status = _clean(row.get("classification_status") or row.get("status")).casefold()
    reason = _clean(row.get("why_sensitive") or row.get("reason") or row.get("notes")).casefold()
    if issue in {"not_relevant", "tidak relevan", "noise", "off topic", "off-topic"}:
        return True
    if status in {"not_relevant", "not relevant"}:
        return True
    if any(token in reason for token in ("noise", "off-topic", "tidak relevan", "entity sama")):
        return True
    return any(token in blob for token in NOISE_KEYWORDS)


def _risk_keyword_hits(row: Mapping[str, Any]) -> list[str]:
    blob = _text_blob(row)
    return [kw for kw in RISK_KEYWORDS if kw in blob]


def _dedupe_articles(rows: list[Mapping[str, Any]], limit: int | None = None) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        key = _url(row) or _clean(row.get("title") or row.get("top_article_title"), 200).casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        item = dict(row)
        item["source_url"] = _url(row)
        item["url_display_label"] = "Open article ↗" if _url(row) else "URL unavailable"
        item["is_noise"] = _is_noise_article(row)
        item["risk_keyword_hits"] = _risk_keyword_hits(row)
        out.append(item)
        if limit and len(out) >= limit:
            break
    return out


def _main_evidence_rows(report_input: Mapping[str, Any], limit: int = 20) -> list[dict[str, Any]]:
    sensitive = _rows(report_input, "ql_mm_headlines_summary")
    articles = _rows(report_input, "ql_mm_article_enriched")
    merged = sorted(sensitive + articles, key=lambda r: (_num(r.get("pr_value")), len(_risk_keyword_hits(r))), reverse=True)
    clean_rows = [row for row in merged if not _is_noise_article(row)]
    return _dedupe_articles(clean_rows, limit=limit)


def _noise_rows(report_input: Mapping[str, Any], limit: int = 20) -> list[dict[str, Any]]:
    rows = _rows(report_input, "ql_mm_headlines_summary") + _rows(report_input, "ql_mm_article_enriched")
    return _dedupe_articles([row for row in rows if _is_noise_article(row)], limit=limit)


def _brand_facing_risk_posture(report_input: Mapping[str, Any], audience: Mapping[str, Any] | None = None) -> dict[str, Any]:
    kpi = _kpi(report_input)
    sent = _sentiment(report_input)
    sentiment_posture = _posture(kpi, sent)
    evidence = _main_evidence_rows(report_input, limit=30)
    issue_rows = _rows(report_input, "qt_mm_main_topics_top3")
    neg_pct = _num(sent.get("negative_pct"))
    risk_articles = [row for row in evidence if _risk_keyword_hits(row)]
    risk_terms = sorted({kw for row in risk_articles for kw in row.get("risk_keyword_hits", [])})
    issue_blob = " ".join(_clean(row.get("issue_label")) for row in issue_rows).casefold()
    issue_has_crisis = any(kw in issue_blob for kw in RISK_KEYWORDS)
    audience_label = _clean((audience or {}).get("audience")).casefold()
    legal_or_crisis = any(token in audience_label for token in ("legal", "crisis", "pr", "corporate"))

    score = 0
    if risk_articles:
        score += min(3, len(risk_articles))
    if issue_has_crisis:
        score += 2
    if neg_pct >= 10:
        score += 2
    elif neg_pct >= 3:
        score += 1
    if legal_or_crisis and (risk_articles or issue_has_crisis):
        score += 2

    if score >= 6:
        label = "RED / ACTIVE CRISIS WATCH"
        severity = "red"
        decision = "Treat as crisis/legal response room input; verify facts and align response guardrails before external amplification."
    elif score >= 3:
        label = "AMBER / BRAND-FACING HIGH WATCH"
        severity = "amber"
        decision = "Do not read green sentiment as safe; use monitored, evidence-backed response and watch follow-up media."
    else:
        label = "GREEN / LOW BRAND-FACING RISK"
        severity = "green"
        decision = "Continue monitoring; maintain evidence URL trail and respond only if new trigger appears."

    return {
        "label": label,
        "short_label": label.split("/")[-1].strip(),
        "severity": severity,
        "sentiment_posture": sentiment_posture,
        "sentiment_posture_label": sentiment_posture.get("label"),
        "rationale": "Risk overlay uses sensitive keywords, regulator/legal mentions, negative share, and high-impact evidence — not raw sentiment only.",
        "risk_terms": risk_terms[:12],
        "risk_article_count": len(risk_articles),
        "decision_implication": decision,
    }


def _fact_vs_allegation(report_input: Mapping[str, Any]) -> dict[str, Any]:
    evidence = _main_evidence_rows(report_input, limit=30)
    verified: list[dict[str, Any]] = []
    allegations: list[dict[str, Any]] = []
    official_response: list[dict[str, Any]] = []
    for row in evidence:
        blob = _text_blob(row)
        item = _source_ref(row)
        item["risk_keyword_hits"] = _risk_keyword_hits(row)
        item["url_display_label"] = "Open article ↗" if item.get("source_url") else "URL unavailable"
        if any(kw in blob for kw in OFFICIAL_RESPONSE_KEYWORDS):
            official_response.append(item)
        if any(kw in blob for kw in ALLEGATION_KEYWORDS):
            allegations.append(item)
        else:
            verified.append(item)
    return {
        "verified_or_reported_events": _dedupe_articles(verified, limit=6),
        "allegations_or_claims_need_verification": _dedupe_articles(allegations, limit=6),
        "official_response_or_clarification": _dedupe_articles(official_response, limit=6),
        "render_guidance": "Do not convert media allegations into verified facts. Attribute claims to the media/source and show URLs.",
    }


def _date_key(row: Mapping[str, Any]) -> str:
    for key in ("published_date", "date", "post_date", "article_date", "created_at"):
        value = row.get(key)
        if value:
            return str(value)[:10]
    return "N/A"


def _timeline_events(report_input: Mapping[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    rows = _main_evidence_rows(report_input, limit=40)
    rows = sorted(rows, key=lambda r: (_date_key(r), -_num(r.get("pr_value"))))
    events = []
    for row in rows:
        events.append({
            "date": _date_key(row),
            "headline": _clean(row.get("title") or row.get("top_article_title"), 130),
            "media_name": row.get("media_name"),
            "sentiment": row.get("sentiment"),
            "risk_terms": row.get("risk_keyword_hits") or _risk_keyword_hits(row),
            "source_url": _url(row),
            "url_display_label": "Open article ↗" if _url(row) else "URL unavailable",
        })
        if len(events) >= limit:
            break
    return events


def _issue_risk_map(report_input: Mapping[str, Any]) -> list[dict[str, Any]]:
    issue_rows = _rows(report_input, "qt_mm_main_topics_top3")
    out = []
    for row in issue_rows[:10]:
        label = _clean(row.get("issue_label"), 120)
        blob = label.casefold()
        severity = "high" if any(kw in blob for kw in RISK_KEYWORDS) else "medium"
        exposure = "high" if _num(row.get("pr_value")) >= 100_000_000 or _num(row.get("article_count")) >= 10 else "medium"
        action = "Fact-check and prepare response guardrail" if severity == "high" else "Monitor and use as context for narrative"
        out.append({
            "issue_label": label,
            "article_count": row.get("article_count"),
            "pr_value": row.get("pr_value"),
            "dominant_sentiment": row.get("dominant_sentiment"),
            "severity": severity,
            "exposure": exposure,
            "priority": "HIGH" if severity == "high" and exposure == "high" else "MEDIUM",
            "recommended_handling": action,
            "top_article_url": row.get("top_article_url"),
        })
    return out


def _normalize_spokesperson_name(value: Any) -> tuple[str, str]:
    raw = _clean(value, 100)
    key = raw.casefold()
    if key in {"dedi", "kdm", "dedi mulyadi", "kang dedi", "gubernur jawa barat"}:
        return "Dedi Mulyadi / Gubernur Jawa Barat", "normalized"
    if "bpkn" in key or "mufti" in key:
        return "Mufti Mubarok / BPKN", "normalized"
    if key in {"dr aqua", "aqua", "danone"} or key.startswith("dr aqua"):
        return raw or "Unknown", "review_required"
    return raw or "Unknown", "raw"


def _normalized_spokesperson_rows(report_input: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = _rows(report_input, "qt_mm_spokesperson_overview")
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        name, status = _normalize_spokesperson_name(row.get("spokesperson"))
        item = grouped.setdefault(name, {
            "spokesperson": name,
            "normalization_status": status,
            "article_count": 0,
            "top_media": row.get("top_media"),
            "dominant_sentiment": row.get("dominant_sentiment"),
            "top_article_url": row.get("top_article_url") or _url(row),
            "related_topics": [],
        })
        item["article_count"] += int(_num(row.get("article_count")))
        topic = _clean(row.get("top_topics") or row.get("top_issue") or row.get("issue_label"), 120)
        if topic and topic not in item["related_topics"]:
            item["related_topics"].append(topic)
        if status == "review_required":
            item["normalization_status"] = "review_required"
    return sorted(grouped.values(), key=lambda r: _num(r.get("article_count")), reverse=True)


def _make_action_v2(priority: str, action_type: str, focus_area: str, owner: str, trigger: str, do_action: str, do_not: str, evidence: Mapping[str, Any], deadline: str) -> dict[str, Any]:
    ref = _source_ref(evidence)
    ref["url_display_label"] = "Open article ↗" if ref.get("source_url") else "URL unavailable"
    return {
        "priority": priority,
        "action_type": action_type,
        "focus_area": focus_area,
        "owner": owner,
        "trigger": trigger,
        "do": do_action,
        "do_not": do_not,
        "deadline": deadline,
        "supporting_evidence": _source_label(ref),
        "evidence_refs": [ref] if ref else [],
        "evidence_urls": [ref.get("source_url")] if ref.get("source_url") else [],
        "requires_url_in_ppt": True,
    }


def _build_action_plan(report_input: Mapping[str, Any]) -> list[dict[str, Any]]:  # override v1
    evidence = _main_evidence_rows(report_input, limit=10)
    issue_map = _issue_risk_map(report_input)
    media = _rows(report_input, "qt_mm_media_contributors_table")
    risk = (evidence or [{}])[0]
    top_issue = (issue_map or [{}])[0]
    top_media = (media or [{}])[0]
    return [
        _make_action_v2(
            "HIGH",
            "VERIFY & FRAME",
            _clean(top_issue.get("issue_label") or "Top legal/reputation issue", 90),
            "Legal + PR/Corcom",
            "Media repeats allegation/regulator keyword or high-impact article appears.",
            "Separate verified facts, media allegations, and official response line before any amplification.",
            "Do not repeat alleged claims as confirmed facts; do not use positive sentiment as proof that brand risk is low.",
            risk,
            "Today / before external statement",
        ),
        _make_action_v2(
            "HIGH",
            "HOLDING STATEMENT",
            "Sensitive / high-impact headline",
            "PR/Corcom + Legal/Crisis",
            "Tier-1 media, regulator, YLKI/BPKN/DPR, or 'misleading/bohong/menipu' frame appears.",
            "Prepare a short, attributable holding line: factual position, process, contact point, and what is being verified.",
            "Do not over-explain technical details before Legal validates wording and supporting proof.",
            risk,
            "Today",
        ),
        _make_action_v2(
            "MEDIUM",
            "MEDIA PRIORITY",
            _clean(top_media.get("media_name") or "Top media contributors", 90),
            "Media Relations",
            "Top media drives article count/PR Value or syndicates the sensitive angle.",
            "Create a priority follow-up list with headline, angle, article URL, and whether correction/update is needed.",
            "Do not contact all media equally; prioritize high-exposure and high-risk articles first.",
            top_media or risk,
            "Next 24 hours",
        ),
        _make_action_v2(
            "MEDIUM",
            "WATCHLIST",
            "Next 24/48h escalation triggers",
            "Insight/Monitoring",
            "New articles mention regulator action, audit, legal claim, label/advertising, permit, or consumer harm.",
            "Track trigger keywords and update issue map; alert PR/Legal when trigger appears in tier-1 media.",
            "Do not rely only on net sentiment count; track brand-facing and legal-risk wording.",
            risk,
            "Every monitoring cycle",
        ),
        _make_action_v2(
            "MEDIUM",
            "SAFE AMPLIFICATION",
            "Constructive/positive coverage",
            "Brand/Comms",
            "Positive or neutral clarification articles are available and crisis claim has been addressed.",
            "Amplify only factual clarification or constructive context after risk review.",
            "Do not amplify celebratory/green sentiment framing while sensitive allegations remain active.",
            (evidence[-1] if evidence else risk),
            "After Legal/PR approval",
        ),
    ]


def _build_executive_summary(report_input: Mapping[str, Any]) -> dict[str, Any]:  # override v1
    kpi = _kpi(report_input)
    sent = _sentiment(report_input)
    sentiment_posture = _posture(kpi, sent)
    risk = _brand_facing_risk_posture(report_input)
    coverage = _issue_coverage_note(kpi)
    top_media = (_rows(report_input, "qt_mm_media_contributors_table") or [{}])[0]
    top_issue = (_rows(report_input, "qt_mm_main_topics_top3") or [{}])[0]
    evidence = (_main_evidence_rows(report_input, limit=1) or [{}])[0]

    situation = f"Media mainstream mencatat {_fmt_int(kpi['total_articles'])} artikel dari {_fmt_int(kpi['total_media'])} media pada periode ini."
    value = f"Total PR Value tercatat {_fmt_money(kpi['total_pr_value'])}; Ad Value {_fmt_money(kpi['total_ad_value'])}."
    risk_line = f"Sentiment posture {sentiment_posture['label']}, tetapi brand-facing risk overlay membaca {risk['label']}."
    if top_issue:
        issue = f"Issue prioritas: {_clean(top_issue.get('issue_label'), 90)} ({_fmt_int(top_issue.get('article_count'))} artikel classified; PR Value {_fmt_money(top_issue.get('pr_value'))})."
    else:
        issue = "Issue prioritas belum tersedia karena issue taxonomy/cache belum lengkap."
    media = f"Media contributor terbesar: {_clean(top_media.get('media_name'), 80)} ({_fmt_int(top_media.get('article_count'))} artikel; PR Value {_fmt_money(top_media.get('pr_value'))})." if top_media else "Media contributor utama belum tersedia."

    return {
        "posture": risk,
        "sentiment_posture": sentiment_posture,
        "kpi_cards": [
            {"label": "Total Articles", "value": _fmt_int(kpi["total_articles"]), "note": "canonical mainstream articles"},
            {"label": "Total Media", "value": _fmt_int(kpi["total_media"]), "note": "unique publishers"},
            {"label": "Total PR Value", "value": _fmt_money(kpi["total_pr_value"]), "note": "exposure estimate"},
            {"label": "Brand Risk", "value": risk["short_label"], "note": "risk overlay, not sentiment only"},
        ],
        "bullets": [situation, value, risk_line, issue, media],
        "executive_readout": {
            "situation": situation,
            "exposure_value": value,
            "risk_diagnosis": risk_line,
            "decision_implication": risk["decision_implication"],
            "issue_readout": issue,
            "evidence_to_check_first": _source_ref(evidence),
            "issue_coverage_note": coverage["message"],
        },
        "top_issue": top_issue,
        "top_media": top_media,
        "top_sensitive_article": evidence,
        "coverage_note": coverage,
    }


def build_mainstream_media_report_data_preview(report_input_id: str, include_evidence_limit: int = 10) -> dict[str, Any]:  # override v1
    preview = _BUILD_MMR_PREVIEW_V1(report_input_id, include_evidence_limit=include_evidence_limit)
    report_input = get_report_input(report_input_id)
    risk = _brand_facing_risk_posture(report_input)
    facts = _fact_vs_allegation(report_input)
    issue_map = _issue_risk_map(report_input)
    noise = _noise_rows(report_input, limit=10)
    clean_evidence = _main_evidence_rows(report_input, limit=include_evidence_limit)
    preview["render_package_version_hint"] = RENDER_PACKAGE_VERSION
    preview["brand_facing_risk_posture"] = risk
    preview["posture"] = risk
    preview["fact_vs_allegation"] = facts
    preview["issue_risk_map"] = issue_map
    preview["noise_excluded_from_main_slides"] = noise
    preview["clean_article_evidence"] = clean_evidence
    # Prepend higher-value executive preview; keep v1 markdown below for tables.
    head = []
    head.append(f"# Mainstream Media Data Preview v2 — {report_input.get('project_name')}\n")
    head.append(f"**Brand-facing risk posture:** {risk['label']}  ")
    head.append(f"**Sentiment posture:** {risk.get('sentiment_posture_label')}  ")
    head.append(f"**Decision implication:** {risk['decision_implication']}  ")
    if risk.get("risk_terms"):
        head.append(f"**Risk terms detected:** {', '.join(risk['risk_terms'][:8])}  ")
    if noise:
        head.append(f"**Noise guard:** {len(noise)} off-topic/noise evidence candidate(s) excluded from main callouts; keep them only in audit/data pack.  ")
    head.append("\n## Executive Evidence to Check First\n")
    for row in clean_evidence[:5]:
        head.append(f"- **{_clean(row.get('title'), 150)}** — {_clean(row.get('media_name'), 80)}; {row.get('sentiment')}; URL: {_url(row) or 'N/A'}\n")
    head.append("\n## Fact vs Allegation Guardrail\n")
    head.append("- Verified/reported event, media claim/allegation, and official response must be separated in PPT narrative.\n")
    head.append("- Do not treat media allegations as verified facts without attribution and URL.\n\n")
    preview["markdown"] = "".join(head) + "\n---\n\n" + preview.get("markdown", "")
    return preview


def _build_slides(report_input: Mapping[str, Any], outline: Mapping[str, Any], audience: Mapping[str, Any]) -> list[dict[str, Any]]:  # override v1
    kpi = _kpi(report_input)
    summary = _build_executive_summary(report_input)
    actions = _build_action_plan(report_input)
    issue_rows = _rows(report_input, "qt_mm_main_topics_top3")
    channel_rows = _rows(report_input, "qt_mm_channel_distribution")
    sentiment_rows = _rows(report_input, "qt_mm_sentiment_distribution")
    matrix_rows = _rows(report_input, "qt_mm_sentiment_matrix_by_channel")
    media_rows = _rows(report_input, "qt_mm_media_contributors_table")
    spokesperson_rows = _normalized_spokesperson_rows(report_input)
    articles = _main_evidence_rows(report_input, limit=30)
    sensitive = articles[:10]
    noise = _noise_rows(report_input, limit=10)
    coverage = _issue_coverage_note(kpi)
    facts = _fact_vs_allegation(report_input)
    risk = _brand_facing_risk_posture(report_input, audience)
    issue_map = _issue_risk_map(report_input)
    timeline = _timeline_events(report_input, limit=8)
    limitations = list(report_input.get("limitations") or [])

    slides: list[dict[str, Any]] = [
        {
            "slide_id": "mmr_00_header",
            "section": "Cover / Crisis Snapshot",
            "title": "MAINSTREAM MEDIA REPORT",
            "subtitle": f"{report_input.get('project_name')} · {report_input.get('start_date')} to {report_input.get('end_date')}",
            "audience_context": audience,
            "kpi_cards": summary["kpi_cards"],
            "brand_facing_risk_posture": risk,
            "sentiment_posture": risk.get("sentiment_posture"),
            "speaker_note": "Open with decision posture, not raw sentiment only.",
        },
        {
            "slide_id": "mmr_01_executive_decision_brief",
            "section": "Executive Decision Brief",
            "title": "EXECUTIVE DECISION BRIEF",
            "subtitle": "What happened, why raw sentiment can mislead, and what decision is needed.",
            "audience_context": audience,
            "brand_facing_risk_posture": risk,
            "sentiment_posture": risk.get("sentiment_posture"),
            "bullets": summary["bullets"],
            "executive_readout": summary["executive_readout"],
            "top_issue": summary.get("top_issue"),
            "top_media": summary.get("top_media"),
        },
        {
            "slide_id": "mmr_02_fact_vs_allegation",
            "section": "Fact vs Allegation",
            "title": "FACT VS ALLEGATION",
            "subtitle": "Separate reported facts, media allegations, and official clarification before responding.",
            "fact_vs_allegation": facts,
            "must_show_url": True,
            "legal_guardrail": "Attribute claims to media/source; do not restate allegations as verified facts.",
        },
        {
            "slide_id": "mmr_03_media_response_action_plan",
            "section": "Media Response Action Plan",
            "title": "MEDIA RESPONSE ACTION PLAN",
            "subtitle": "Owner, trigger, do / do-not, deadline, and evidence URL.",
            "audience_context": audience,
            "actions": actions,
            "must_show_evidence_url": True,
        },
        {
            "slide_id": "mmr_04_timeline_escalation_pattern",
            "section": "Timeline / Escalation Pattern",
            "title": "TIMELINE / ESCALATION PATTERN",
            "subtitle": "Article sequence and escalation triggers to monitor.",
            "events": timeline,
            "must_show_url": True,
        },
        {
            "slide_id": "mmr_05_issue_risk_map",
            "section": "Issue Risk Map",
            "title": "ISSUE RISK MAP",
            "subtitle": "Severity × exposure view; issue taxonomy uses Title + Content, not raw Topic Extraction.",
            "available": bool(issue_map),
            "coverage_note": coverage,
            "issue_risk_map": issue_map,
            "issue_rows": issue_rows,
        },
        {
            "slide_id": "mmr_06_sentiment_brand_risk",
            "section": "Sentiment & Brand-Facing Risk",
            "title": "SENTIMENT & BRAND-FACING RISK",
            "subtitle": "Why green sentiment may not mean brand safety.",
            "brand_facing_risk_posture": risk,
            "sentiment_distribution": sentiment_rows,
            "sentiment_matrix_by_channel": matrix_rows,
            "channel_distribution": channel_rows,
            "readout": risk.get("decision_implication"),
        },
        {
            "slide_id": "mmr_07_media_contributors_priority",
            "section": "Media Contributors & Priority Follow-up",
            "title": "MEDIA CONTRIBUTORS & PRIORITY FOLLOW-UP",
            "subtitle": "Top publishers/media by volume, exposure value, and follow-up priority.",
            "rows": media_rows,
            "must_show_url": True,
        },
        {
            "slide_id": "mmr_08_sensitive_article_watchlist",
            "section": "Sensitive Articles / Legal Watchlist",
            "title": "SENSITIVE ARTICLE WATCHLIST",
            "subtitle": "Cleaned high-risk article evidence; off-topic/noise removed from main callouts.",
            "sensitive_articles": sensitive[:10],
            "noise_excluded_count": len(noise),
            "must_show_url": True,
        },
        {
            "slide_id": "mmr_09_spokesperson_regulator_mentions",
            "section": "Spokesperson & Regulator Mentions",
            "title": "SPOKESPERSON & REGULATOR MENTIONS",
            "subtitle": "Normalized names; low-confidence extracted entities require review.",
            "available": bool(spokesperson_rows),
            "rows": spokesperson_rows,
            "view_status": _view_status(report_input, "qt_mm_spokesperson_overview"),
        },
        {
            "slide_id": "mmr_10_supporting_article_evidence",
            "section": "Supporting Article Evidence",
            "title": "SUPPORTING ARTICLE EVIDENCE",
            "subtitle": "Audit-ready article evidence with clickable source URL.",
            "articles": articles[:12],
            "must_show_url": True,
        },
        {
            "slide_id": "mmr_11_article_url_appendix",
            "section": "Appendix",
            "title": "APPENDIX — ARTICLE EVIDENCE LINKS",
            "subtitle": "Full URL audit trail; noise candidates are not used in main narrative.",
            "article_links": [{"title": row.get("title"), "media_name": row.get("media_name"), "sentiment": row.get("sentiment"), "source_url": _url(row), "url_display_label": "Open article ↗" if _url(row) else "URL unavailable"} for row in articles[:20]],
            "noise_candidates": noise,
        },
        {
            "slide_id": "mmr_12_footer_sources_notes",
            "section": "Sources & Notes",
            "title": "SOURCES & NOTES",
            "subtitle": "Data source, metric contract, limitations, and AI-assisted note.",
            "scope": {
                "project": report_input.get("project_name"),
                "period": f"{report_input.get('start_date')} → {report_input.get('end_date')}",
                "source": "Cogan canonical mainstream media articles",
                "issue_taxonomy": kpi.get("issue_taxonomy_version") or "N/A",
            },
            "metric_contract": [
                "Primary volume metric: article count / news count.",
                "Exposure metrics: PR Value, Ad Value, readership, circulation if available.",
                "Raw Topic Extraction is diagnostic only; final report issue uses LLM issue taxonomy from Title + Content.",
                "Article URL must be displayed for evidence where available.",
                "Brand-facing risk posture is a response overlay; it is not equal to raw net sentiment.",
            ],
            "limitations": limitations + [coverage["message"]] + ([f"{len(noise)} off-topic/noise evidence candidate(s) excluded from main callouts; kept for audit only."] if noise else []),
        },
    ]
    return slides


def build_mainstream_media_report_package(
    report_input_id: str,
    allow_partial: bool = True,
    audience_context: str | None = None,
    audience_pov: str | None = None,
) -> dict[str, Any]:  # override v1
    report_input = get_report_input(report_input_id)
    if not report_input:
        raise MainstreamMediaRendererError(f"report_input_id tidak ditemukan: {report_input_id}")
    if report_input.get("report_type_id") != REPORT_TYPE_ID:
        raise MainstreamMediaRendererError(f"report_input_id bukan mainstream_media_report: {report_input.get('report_type_id')}")

    outline = build_report_outline_from_id(report_input_id, allow_partial=allow_partial)
    audience = normalize_audience_context(audience_context, audience_pov)
    preview = build_mainstream_media_report_data_preview(report_input_id)
    slides = _build_slides(report_input, outline, audience)
    risk = _brand_facing_risk_posture(report_input, audience)

    return {
        "success": True,
        "render_package_id": _now_id("mmr_render_package"),
        "render_package_version": RENDER_PACKAGE_VERSION,
        "quality_upgrade": "v2_crisis_decision_overlay",
        "report_type_id": REPORT_TYPE_ID,
        "report_input_id": report_input_id,
        "outline_id": outline.get("outline_id"),
        "outline_status": outline.get("outline_status"),
        "audience_context": audience,
        "brand_facing_risk_posture": risk,
        "pre_ppt_data_preview": preview,
        "core_structure": [slide["section"] for slide in slides],
        "slides": slides,
        "limitations": preview.get("limitations") or [],
        "ppt_style_brief": {
            "language": "Indonesian, with English section headers allowed",
            "tone": audience.get("tone"),
            "structure_rule": "Fact vs Allegation and Action Plan must appear before supporting evidence for Legal/Crisis/PR audiences.",
            "visual_style": "consulting deck, stronger hierarchy, fewer raw URLs on main slides; use clickable label 'Open article ↗' and full URL in appendix",
            "must_follow": [
                f"Write for {audience['audience']}; answer: {audience['primary_question']}",
                "Use brand-facing risk posture, not raw sentiment posture, as the executive decision label.",
                "Separate verified/reported facts, media allegations, and official responses; never present allegations as confirmed facts.",
                "Exclude noise/off-topic articles from main callouts; they may appear only as audit notes/data pack.",
                "Use article_count/news count as primary volume metric, not interactions.",
                "Show evidence URL through clickable text on main slides and full URL in appendix.",
                "If issue coverage is low, label issue insight as early classified issue signal.",
                "Do not fabricate headlines, quotes, PR Value, URLs, media names, issues, or spokespersons.",
            ],
        },
        "claude_instructions": [
            "Show data preview before PPTX unless user has already confirmed it.",
            "Use slides array as the source of truth for PPT content and order.",
            "Use v2 decision framing: sentiment posture is not enough; use brand_facing_risk_posture.",
            "Render Fact vs Allegation before Action Plan for legal/crisis-sensitive coverage.",
            "Do not include articles marked noise/off-topic in the main narrative, sensitive issue callouts, or action plan.",
            "Every evidence/article card should include URL when source_url is available.",
        ],
    }


# ---------------------------------------------------------------------------
# v3 polish overlay: stricter noise exclusion, crisis-aware severity, evidence
# IDs, and restrained URL display policy.
# ---------------------------------------------------------------------------

_BUILD_MMR_SLIDES_BEFORE_V3_POLISH = _build_slides
_BUILD_MMR_PACKAGE_BEFORE_V3_POLISH = build_mainstream_media_report_package
_BUILD_MMR_PREVIEW_BEFORE_V3_POLISH = build_mainstream_media_report_data_preview
RENDER_PACKAGE_VERSION = "mainstream_media_report_render_package_v3"

URL_DISPLAY_POLICY = {
    "main_slides": "Use Evidence ID only (E01, E02, ...); do not print raw URLs.",
    "action_plan": "No raw URL. Show Evidence ID + media/headline only.",
    "fact_vs_allegation": "Use Evidence IDs. Full URLs stay in appendix/data pack.",
    "timeline": "No URL. Date + media + headline + Evidence ID only.",
    "watchlist": "Evidence ID only unless the user explicitly asks for clickable links.",
    "appendix": "Full URL audit trail is allowed and expected.",
    "data_pack": "All source URLs must remain available.",
}

# Extend v2 noise keywords with the actual off-topic patterns seen in BlueBird MMR.
NOISE_KEYWORDS = tuple(dict.fromkeys(tuple(NOISE_KEYWORDS) + (
    "ihsg", "chatib basri", "bursa", "saham", "market", "stock", "asts",
    "satelit", "space", "bluebird bio", "bluebird asts", "forwat", "technocamp",
    "festival", "job fair", "esports", "unipin", "sriwijaya esports", "tabloid pulsa",
    "forum wartawan teknologi", "mobitekno", "canggih", "review1st",
)))

IMPACT_HIGH_KEYWORDS = (
    "tewas", "meninggal", "korban jiwa", "kecelakaan maut", "fatal", "anak yatim",
    "yatim piatu", "duka", "keluarga korban", "tuntut", "tuntutan", "desak",
    "audit", "bpkn", "ylki", "dpr", "regulator", "izin", "cabut izin", "gugatan",
    "investigasi", "dugaan", "diduga", "menipu", "bohong", "pembohongan", "menyesatkan",
)

_URL_KEYS_TO_HIDE = {"source_url", "top_article_url", "article_url", "url", "link_url", "evidence_urls"}


def _is_noise_article(row: Mapping[str, Any]) -> bool:  # override v2
    blob = _text_blob(row)
    issue = _clean(row.get("issue_label") or row.get("topic") or row.get("dominant_issue") or row.get("top_issue")).casefold()
    status = _clean(row.get("classification_status") or row.get("status")).casefold()
    reason = _clean(row.get("why_sensitive") or row.get("reason") or row.get("notes") or row.get("relevance") or row.get("relevansi_brand")).casefold()
    if issue in {"not_relevant", "tidak relevan", "noise", "off topic", "off-topic"}:
        return True
    if "off-topic" in issue or "noise" in issue:
        return True
    if status in {"not_relevant", "not relevant"}:
        return True
    if any(token in reason for token in ("noise", "off-topic", "tidak relevan", "entity sama")):
        return True
    return any(token in blob for token in NOISE_KEYWORDS)


def _issue_coverage_note(kpi: Mapping[str, Any]) -> dict[str, Any]:  # override v1/v2
    cov = _num(kpi.get("issue_coverage_pct"))
    total = int(_num(kpi.get("total_articles") or kpi.get("total_news")))
    if cov <= 0:
        return {"level": "missing", "message": "Issue enrichment belum tersedia; issue-based analysis akan N/A sampai classification dijalankan.", "safe_for_issue_conclusion": False}
    if total and total <= 50 and cov < 95:
        return {
            "level": "small_scope_incomplete",
            "message": f"Issue coverage {_fmt_pct(cov)} pada scope kecil ({total} artikel). Untuk final MMR, scope <=50 artikel sebaiknya diklasifikasi 100%; perlakukan issue map sebagai preliminary.",
            "safe_for_issue_conclusion": False,
            "recommended_action": "Run issue classification for all eligible articles before final PPT.",
        }
    if cov < 60:
        return {"level": "low", "message": f"Issue coverage baru {_fmt_pct(cov)}; issue insight hanya early classified signal, belum representatif penuh.", "safe_for_issue_conclusion": False}
    if cov < 90:
        return {"level": "partial", "message": f"Issue coverage {_fmt_pct(cov)}; cukup untuk directional readout dengan caveat.", "safe_for_issue_conclusion": True}
    return {"level": "complete", "message": f"Issue coverage {_fmt_pct(cov)}; issue ranking aman dipakai sebagai report readout.", "safe_for_issue_conclusion": True}


def _strip_visible_urls(value: Any) -> Any:
    if isinstance(value, list):
        return [_strip_visible_urls(item) for item in value]
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if k in _URL_KEYS_TO_HIDE:
                continue
            if k in {"requires_url_in_ppt", "must_show_url", "must_show_evidence_url"}:
                out[k] = False
            else:
                out[k] = _strip_visible_urls(v)
        return out
    return value


def _build_article_evidence_index(report_input: Mapping[str, Any], limit: int = 40) -> list[dict[str, Any]]:
    clean_articles = _main_evidence_rows(report_input, limit=limit)
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(clean_articles, start=1):
        ref = _source_ref(row)
        out.append({
            "evidence_id": f"E{idx:02d}",
            "media_name": ref.get("media_name"),
            "title": ref.get("title"),
            "sentiment": ref.get("sentiment"),
            "issue_label": ref.get("issue_label"),
            "pr_value": ref.get("pr_value"),
            "source_url": ref.get("source_url"),
            "full_url": ref.get("source_url"),
            "url_display_policy": "full_url_only_in_appendix_or_data_pack",
        })
    return out


def _article_lookup(report_input: Mapping[str, Any]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for item in _build_article_evidence_index(report_input, limit=60):
        for key in (item.get("source_url"), item.get("title")):
            if key:
                lookup[str(key).strip()] = item["evidence_id"]
    return lookup


def _find_article_evidence_id(ref: Mapping[str, Any], lookup: Mapping[str, str]) -> str | None:
    for key in (ref.get("source_url"), ref.get("url"), ref.get("top_article_url"), ref.get("title"), ref.get("top_article_title")):
        if key and str(key).strip() in lookup:
            return lookup[str(key).strip()]
    return None


def _compact_article_ref(ref_or_row: Mapping[str, Any], lookup: Mapping[str, str]) -> dict[str, Any]:
    ref = _source_ref(ref_or_row) if ("title" not in ref_or_row and "top_article_title" in ref_or_row) else dict(ref_or_row)
    if "media_name" not in ref or "title" not in ref:
        ref = _source_ref(ref_or_row)
    item = _strip_visible_urls(dict(ref))
    evidence_id = _find_article_evidence_id(ref, lookup)
    if evidence_id:
        item["evidence_id"] = evidence_id
    item["source_label"] = _source_label(ref)
    item["url_display_policy"] = "no_raw_url_on_main_slide; see appendix/data pack"
    item["link_text"] = f"{evidence_id or 'Evidence'} — see appendix"
    return item


def _fact_vs_allegation(report_input: Mapping[str, Any]) -> dict[str, Any]:  # override v2
    evidence = _main_evidence_rows(report_input, limit=30)
    lookup = _article_lookup(report_input)
    verified: list[dict[str, Any]] = []
    allegations: list[dict[str, Any]] = []
    official_response: list[dict[str, Any]] = []
    for row in evidence:
        blob = _text_blob(row)
        item = _compact_article_ref(_source_ref(row), lookup)
        item["risk_keyword_hits"] = _risk_keyword_hits(row)
        is_official = any(kw in blob for kw in OFFICIAL_RESPONSE_KEYWORDS) and any(
            token in blob for token in ("bluebird", "blue bird", "danone", "aqua", "manajemen", "resmi", "klarifikasi", "buka suara", "tanggapan")
        )
        if is_official:
            official_response.append(item)
        if any(kw in blob for kw in ALLEGATION_KEYWORDS):
            allegations.append(item)
        elif not is_official:
            verified.append(item)
    return {
        "verified_or_reported_events": verified[:5],
        "allegations_or_claims_need_verification": allegations[:5],
        "official_response_or_clarification": official_response[:4],
        "official_response_empty_message": "Belum ditemukan respons resmi/klarifikasi brand dalam mainstream media scope periode ini." if not official_response else None,
        "render_guidance": "Use Evidence IDs only on this slide. Do not convert media allegations into verified facts. If official response list is empty, show the empty-message rather than forcing a media article into this bucket.",
    }


def _issue_severity(label: str, extra_text: str = "") -> str:
    blob = f"{label} {extra_text}".casefold()
    if any(token in blob for token in IMPACT_HIGH_KEYWORDS):
        return "high"
    if any(token in blob for token in ("nikita", "indra", "viral", "serbu", "netizen", "blame", "pemilik")):
        return "medium-high"
    return "medium"


def _issue_risk_map(report_input: Mapping[str, Any]) -> list[dict[str, Any]]:  # override v2
    issue_rows = _rows(report_input, "qt_mm_main_topics_top3")
    out = []
    for row in issue_rows[:10]:
        label = _clean(row.get("issue_label"), 120)
        extra = _clean(row.get("top_article_title"), 180)
        severity = _issue_severity(label, extra)
        exposure = "high" if _num(row.get("pr_value")) >= 100_000_000 or _num(row.get("article_count")) >= 8 else "medium"
        if severity == "high":
            action = "Verify facts, align Legal/PR guardrail, and prepare holding line."
        elif severity == "medium-high":
            action = "Monitor escalation and prevent blame narrative from spreading."
        else:
            action = "Monitor and use as context for narrative."
        out.append({
            "issue_label": label,
            "article_count": row.get("article_count"),
            "pr_value": row.get("pr_value"),
            "dominant_sentiment": row.get("dominant_sentiment"),
            "severity": severity,
            "exposure": exposure,
            "priority": "HIGH" if severity == "high" else "MEDIUM-HIGH" if severity == "medium-high" and exposure == "high" else "MEDIUM",
            "recommended_handling": action,
            "top_article_evidence_id": None,
            "url_display_policy": "no_raw_url_on_issue_map",
        })
    return out


def _timeline_events(report_input: Mapping[str, Any], limit: int = 6) -> list[dict[str, Any]]:  # override v2
    rows = _main_evidence_rows(report_input, limit=40)
    lookup = _article_lookup(report_input)
    rows = sorted(rows, key=lambda r: (_date_key(r), -_num(r.get("pr_value"))))
    events = []
    for row in rows:
        ref = _compact_article_ref(_source_ref(row), lookup)
        events.append({
            "date": _date_key(row),
            "headline": _clean(row.get("title") or row.get("top_article_title"), 130),
            "media_name": row.get("media_name"),
            "sentiment": row.get("sentiment"),
            "risk_terms": row.get("risk_keyword_hits") or _risk_keyword_hits(row),
            "evidence_id": ref.get("evidence_id"),
            "url_display_policy": "no_url_on_timeline; see appendix",
        })
        if len(events) >= limit:
            break
    return events


def _polish_mmr_actions(actions: list[dict[str, Any]], lookup: Mapping[str, str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for action in actions:
        item = dict(action)
        refs = action.get("evidence_refs") or []
        compact_refs = [_compact_article_ref(ref, lookup) for ref in refs[:1] if isinstance(ref, Mapping)]
        evidence_id = compact_refs[0].get("evidence_id") if compact_refs else None
        if evidence_id:
            item["evidence_id"] = evidence_id
            item["supporting_evidence"] = f"{evidence_id} — {compact_refs[0].get('source_label')}"
        item["evidence_refs"] = compact_refs
        item["evidence_urls"] = []
        item["requires_url_in_ppt"] = False
        item["url_display_policy"] = "show_evidence_id_only; no_raw_url_in_action_plan"
        out.append(item)
    return out


def _filter_media_rows_for_main(rows: list[dict[str, Any]], noise: list[dict[str, Any]]) -> list[dict[str, Any]]:
    noise_media = {_clean(row.get("media_name")).casefold() for row in noise if row.get("media_name")}
    out = []
    for row in rows:
        blob = _text_blob(row)
        media = _clean(row.get("media_name")).casefold()
        if media in noise_media or any(token in blob for token in NOISE_KEYWORDS) or "off-topic" in blob or "noise" in blob:
            continue
        out.append(row)
    return out


def _build_slides(report_input: Mapping[str, Any], outline: Mapping[str, Any], audience: Mapping[str, Any]) -> list[dict[str, Any]]:  # override v2
    slides = _BUILD_MMR_SLIDES_BEFORE_V3_POLISH(report_input, outline, audience)
    lookup = _article_lookup(report_input)
    evidence_index = _build_article_evidence_index(report_input, limit=40)
    noise = _noise_rows(report_input, limit=50)

    for slide in slides:
        slide["url_display_policy"] = URL_DISPLAY_POLICY
        sid = slide.get("slide_id") or ""
        if sid == "mmr_02_fact_vs_allegation":
            slide["must_show_url"] = False
            slide["subtitle"] = "Separate reported facts, media allegations, and official response. Evidence uses IDs; full URLs are in appendix."
        elif sid == "mmr_03_media_response_action_plan":
            slide["actions"] = _polish_mmr_actions(slide.get("actions") or [], lookup)
            slide["must_show_evidence_url"] = False
            slide["subtitle"] = "Owner · trigger · do / do-not · deadline. Evidence shown as ID; full URLs stay in appendix."
        elif sid == "mmr_04_timeline_escalation_pattern":
            slide["events"] = _timeline_events(report_input, limit=6)
            slide["must_show_url"] = False
            slide["subtitle"] = "Brand-relevant article sequence only; off-topic/noise excluded. Evidence uses IDs."
        elif sid == "mmr_07_media_contributors_priority":
            slide["rows"] = _filter_media_rows_for_main(slide.get("rows") or [], noise)[:10]
            slide["must_show_url"] = False
            slide["noise_excluded_count"] = len(noise)
        elif sid == "mmr_08_sensitive_article_watchlist":
            clean_items = []
            for row in (slide.get("sensitive_articles") or [])[:8]:
                if not _is_noise_article(row):
                    clean_items.append(_compact_article_ref(row, lookup))
            slide["sensitive_articles"] = clean_items[:6]
            slide["must_show_url"] = False
            slide["subtitle"] = "Brand-relevant high-risk evidence only. Evidence ID shown; full URL in appendix."
        elif sid == "mmr_10_supporting_article_evidence":
            # Dedicated evidence slide still avoids raw URL; appendix/data pack hold full URLs.
            slide["articles"] = [_compact_article_ref(row, lookup) for row in _main_evidence_rows(report_input, limit=12)]
            slide["must_show_url"] = False
            slide["subtitle"] = "Audit-ready evidence IDs. Use appendix for full URLs."
        elif sid == "mmr_11_article_url_appendix":
            slide["title"] = "APPENDIX — EVIDENCE ID & FULL URL"
            slide["article_links"] = evidence_index[:25]
            slide["noise_candidates"] = _noise_rows(report_input, limit=20)
            slide["subtitle"] = "Full URL audit trail; main slides use Evidence IDs."
        elif sid == "mmr_12_footer_sources_notes":
            slide["metric_contract"] = [
                text for text in slide.get("metric_contract", [])
                if "Article URL must be displayed" not in str(text)
            ] + ["Main slides use Evidence IDs; full URLs are available in appendix and data pack."]
        elif sid in {"mmr_00_header", "mmr_01_executive_decision_brief", "mmr_05_issue_risk_map", "mmr_06_sentiment_brand_risk", "mmr_09_spokesperson_regulator_mentions"}:
            # Remove stray URLs from main decision/risk slides.
            for key, value in list(slide.items()):
                if key not in {"slide_id", "section", "title", "subtitle", "url_display_policy"}:
                    slide[key] = _strip_visible_urls(value)

    return slides


def build_mainstream_media_report_data_preview(report_input_id: str, include_evidence_limit: int = 10) -> dict[str, Any]:  # override v2
    preview = _BUILD_MMR_PREVIEW_BEFORE_V3_POLISH(report_input_id, include_evidence_limit=include_evidence_limit)
    preview["preview_version"] = "mainstream_media_report_data_preview_v3"
    preview["url_display_policy"] = URL_DISPLAY_POLICY
    preview["claude_instructions"] = [
        instr for instr in preview.get("claude_instructions", [])
        if "URL" not in instr and "source_url" not in instr
    ] + [
        "Show URLs in preview/evidence audit only. In PPT main slides, use Evidence IDs and keep full URLs in appendix/data pack.",
    ]
    return preview


def build_mainstream_media_report_package(
    report_input_id: str,
    allow_partial: bool = True,
    audience_context: str | None = None,
    audience_pov: str | None = None,
) -> dict[str, Any]:  # override v2
    package = _BUILD_MMR_PACKAGE_BEFORE_V3_POLISH(
        report_input_id,
        allow_partial=allow_partial,
        audience_context=audience_context,
        audience_pov=audience_pov,
    )
    report_input = get_report_input(report_input_id)
    evidence_index = _build_article_evidence_index(report_input or {}, limit=40)
    package["render_package_version"] = RENDER_PACKAGE_VERSION
    package["quality_upgrade"] = "v3_noise_coverage_severity_url_policy"
    package["evidence_link_policy"] = URL_DISPLAY_POLICY
    package["evidence_index"] = evidence_index
    if package.get("ppt_style_brief"):
        package["ppt_style_brief"]["visual_style"] = "consulting deck; executive hierarchy; Evidence IDs on main slides; full URLs only in appendix/data pack"
        package["ppt_style_brief"]["must_follow"] = [
            rule for rule in package["ppt_style_brief"].get("must_follow", [])
            if "Show evidence URL" not in rule and "Every evidence" not in rule
        ] + [
            "Use Evidence IDs on main slides. Do not print raw URLs in Action Plan, Fact vs Allegation, Timeline, Issue Map, Sentiment, or Media Contributors.",
            "Full URLs belong only in Appendix/Evidence URL slide and data pack unless the user explicitly asks otherwise.",
            "Exclude noise/off-topic articles from all main slides; keep them only in appendix audit note/data pack.",
            "If official response is not found, show the empty official-response message; do not force media allegation articles into official response bucket.",
            "Use crisis-aware severity: fatality/children/family/regulator/legal keywords are high severity even with low article count.",
        ]
    package["claude_instructions"] = [
        instr for instr in package.get("claude_instructions", [])
        if "Every evidence" not in instr and "source_url" not in instr
    ] + [
        "Render Evidence IDs on main slides and keep raw/full URLs only in Appendix/Data Pack.",
        "Do not place raw URLs in Action Plan or Timeline.",
        "Do not include noise/off-topic articles in main narrative, media contributors, watchlist, timeline, or action plan.",
    ]
    return package
