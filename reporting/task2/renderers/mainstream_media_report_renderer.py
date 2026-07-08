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
RENDER_PACKAGE_VERSION = "mainstream_media_report_render_package_v1"
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
