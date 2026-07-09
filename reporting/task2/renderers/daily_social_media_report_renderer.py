"""Daily Social Media Report Task 2 renderer, v2.

This module converts a frozen Task 1 `report_input_v1` package plus the
registry outline into a PPT-ready report package for Claude/LLM rendering.

v2 improves the first smoke-test renderer by:

- surfacing source URLs as required evidence fields;
- strengthening executive/action narratives with situation/risk/implication;
- adding optional deep-dive and appendix slides when risk/evidence warrants it;
- exposing a Task 1 data preview that users can review before PPT creation;
- separating report-ready insight from low-coverage/topic-smoke-test limitations.

It does not fabricate quotes, topics, URLs, or metrics. All examples come from
qt_* and ql_* views created by Task 1.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from reporting.storage.report_input_store import get_report_input
from reporting.task2.report_outline_builder import build_report_outline_from_id


RENDER_PACKAGE_VERSION = "daily_social_report_render_package_v3"
REPORT_TYPE_ID = "daily_social_media_report"
SENTIMENT_ORDER = ("positive", "neutral", "negative")
ACTION_TYPES = (
    "Amplify Strength",
    "Respond to Risk",
    "Monitor Inquiry",
    "Prepare Response",
    "Content Opportunity",
)
CORE_DAILY_STRUCTURE = [
    "Header / Identitas Report",
    "Executive Summary",
    "Daily Action Plan",
    "Thematic Topics",
    "Sentiment Analysis",
    "Top Performing Authors",
    "Top Performing Content",
    "Key Findings",
    "Footer / Disclaimer",
]


class DailySocialRendererError(RuntimeError):
    """Raised when Daily Social Task 2 rendering cannot proceed safely."""


AUDIENCE_ALIASES = {
    "pr": "PR / Corporate Communications",
    "public relations": "PR / Corporate Communications",
    "corcom": "PR / Corporate Communications",
    "corporate communication": "PR / Corporate Communications",
    "corporate communications": "PR / Corporate Communications",
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
    "social care": "Social Care / Customer Care",
    "customer care": "Social Care / Customer Care",
    "cs": "Social Care / Customer Care",
    "marketing": "Marketing / Content Team",
    "content": "Marketing / Content Team",
    "brand": "Brand Team",
    "brand team": "Brand Team",
}

AUDIENCE_GUIDANCE = {
    "PR / Corporate Communications": {
        "primary_question": "Apa risiko reputasi hari ini dan respons komunikasi apa yang paling aman?",
        "narrative_angle": "reputation risk, public statement guardrails, escalation risk, media/account concentration",
        "preferred_outputs": [
            "holding statement direction",
            "response guardrails",
            "risk trigger and escalation threshold",
            "source URLs for sensitive posts",
        ],
        "avoid": "terlalu banyak tabel teknis tanpa interpretasi respons komunikasi",
    },
    "Insight / Analyst Team": {
        "primary_question": "Pola data apa yang berubah, seberapa kuat evidencenya, dan apa caveat metodologinya?",
        "narrative_angle": "data pattern, channel/topic/sentiment relationship, evidence quality, coverage caveats",
        "preferred_outputs": [
            "metric readout",
            "topic/sentiment cross-readout",
            "evidence audit trail",
            "coverage and methodology limitation",
        ],
        "avoid": "rekomendasi komunikasi yang terlalu normatif tanpa data support",
    },
    "Management": {
        "primary_question": "Apa yang perlu diputuskan/diarahkan manajemen dalam 24 jam ke depan?",
        "narrative_angle": "executive risk posture, business implication, priority decision, concise action",
        "preferred_outputs": [
            "posture and implication",
            "top 3 risks/opportunities",
            "decision needed",
            "simple next actions by owner",
        ],
        "avoid": "tabel panjang dan detail teknis yang tidak membantu keputusan",
    },
    "CEO / Board": {
        "primary_question": "Apakah isu ini butuh perhatian eksekutif dan apa implikasi reputasinya?",
        "narrative_angle": "executive brief, strategic implication, external exposure, clear risk level",
        "preferred_outputs": [
            "one-page executive readout",
            "why it matters",
            "risk containment recommendation",
            "high-level evidence only",
        ],
        "avoid": "operasional detail berlebihan atau jargon monitoring",
    },
    "Social Care / Customer Care": {
        "primary_question": "Post/komentar mana yang perlu direspons, dimonitor, atau dieskalasi?",
        "narrative_angle": "response handling, comment monitoring, escalation queue, source URL priority",
        "preferred_outputs": [
            "response priority list",
            "reply/monitor/escalate classification",
            "top URLs to check",
            "FAQ/response guardrails",
        ],
        "avoid": "narasi strategis panjang tanpa daftar tindakan operasional",
    },
    "Marketing / Content Team": {
        "primary_question": "Konten/kanal apa yang bisa diamplifikasi atau perlu dihindari hari ini?",
        "narrative_angle": "content opportunity, channel format, amplification risk, audience engagement",
        "preferred_outputs": [
            "content opportunities",
            "format/channel insight",
            "amplification do/don't",
            "top content URLs",
        ],
        "avoid": "mendorong konten positif yang tone-deaf saat risiko reputasi tinggi",
    },
    "Brand Team": {
        "primary_question": "Bagaimana kondisi brand perception hari ini dan apa pesan utama yang harus dijaga?",
        "narrative_angle": "brand perception, sentiment posture, message consistency, perception risks",
        "preferred_outputs": [
            "brand posture",
            "message risk/opportunity",
            "topic perception",
            "evidence examples",
        ],
        "avoid": "hanya mengejar engagement tanpa menimbang brand safety",
    },
    "General Business User": {
        "primary_question": "Apa yang terjadi, kenapa penting, dan apa tindakan berikutnya?",
        "narrative_angle": "plain-language situation, risk, action, evidence",
        "preferred_outputs": [
            "summary",
            "action plan",
            "top evidence links",
            "limitations",
        ],
        "avoid": "istilah teknis yang tidak dijelaskan",
    },
}


def normalize_audience_context(
    audience_context: str | None = None,
    audience_pov: str | None = None,
) -> dict[str, Any]:
    """Normalize the intended reader/user of the report.

    This is used by the workflow and renderer so Claude can adapt the depth,
    vocabulary, evidence placement, and action framing to the target reader.
    """
    raw = _clean_text(audience_context or audience_pov or "")
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
            f"Report Daily Social{target}{period} ini dibuat untuk siapa? "
            "Pilih salah satu: PR/Corcom, tim Insight, Management, CEO/Board, Social Care/CS, Marketing/Content, atau Brand Team."
        ),
        "why_needed": (
            "Audience menentukan POV analisis, kedalaman narasi, bahasa, action plan, dan jenis evidence yang paling penting."
        ),
        "suggested_audiences": [
            "PR / Corporate Communications",
            "Insight / Analyst Team",
            "Management",
            "CEO / Board",
            "Social Care / Customer Care",
            "Marketing / Content Team",
            "Brand Team",
        ],
        "example_user_reply": "Untuk tim PR/Corcom.",
    }


def _audience_prefix(audience: Mapping[str, Any]) -> str:
    return (
        f"Audience: {audience.get('audience')} | POV: {audience.get('primary_question')} | "
        f"Angle: {audience.get('narrative_angle')}"
    )


def apply_audience_to_package(package: dict[str, Any], audience_context: str | None = None, audience_pov: str | None = None) -> dict[str, Any]:
    """Attach audience-specific guidance to a render package without changing data."""
    audience = normalize_audience_context(audience_context, audience_pov)
    package = dict(package)
    meta = dict(package.get("meta") or {})
    meta["audience_context"] = audience
    package["meta"] = meta

    style = dict(package.get("ppt_style_brief") or {})
    style["audience_context"] = audience
    style["tone"] = audience.get("tone")
    must_follow = list(style.get("must_follow") or [])
    must_follow.extend(
        [
            f"Write for {audience['audience']}; answer: {audience['primary_question']}",
            f"Prioritize: {', '.join(audience['preferred_outputs'])}.",
            f"Avoid: {audience['avoid']}.",
        ]
    )
    # Keep order but remove duplicates.
    seen: set[str] = set()
    style["must_follow"] = [item for item in must_follow if not (item in seen or seen.add(item))]
    package["ppt_style_brief"] = style

    instructions = list(package.get("claude_instructions") or [])
    instructions.insert(0, _audience_prefix(audience))
    instructions.append(
        "Adapt the narrative and action-plan wording to the audience_context, but do not change metrics, snippets, URLs, or evidence."
    )
    package["claude_instructions"] = instructions
    package["audience_context"] = audience
    return package


def _now_id(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}_{stamp}_{uuid4().hex[:8]}"


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
    metadata = _as_mapping(view.get("metadata"))
    rows = view.get("rows")
    return {
        "view_id": view_id,
        "view_type": view_type,
        "status": str(metadata.get("status") or "READY"),
        "reason": metadata.get("reason"),
        "row_count": len(rows) if isinstance(rows, list) else 0,
        "metadata": dict(metadata),
    }


def _num(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _fmt_int(value: Any) -> str:
    return f"{int(round(_num(value))):,}".replace(",", ".")


def _fmt_num(value: Any, digits: int = 1) -> str:
    value = _num(value)
    if abs(value - round(value)) < 0.0001:
        return _fmt_int(value)
    return f"{value:,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _fmt_pct(value: Any) -> str:
    if value is None:
        return "N/A"
    return f"{_num(value):.1f}%".replace(".", ",")


def _clean_text(value: Any, limit: int | None = None) -> str:
    text = " ".join(str(value or "").strip().split())
    if limit and len(text) > limit:
        return text[: max(0, limit - 1)].rstrip() + "…"
    return text


def _top(rows: list[dict[str, Any]], key: str, limit: int = 1) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: _num(row.get(key)), reverse=True)[:limit]


def _url(row: Mapping[str, Any]) -> str | None:
    for key in (
        "source_url",
        "top_post_url",
        "url",
        "link_url",
        "post_url",
        "article_url",
    ):
        value = row.get(key)
        if value:
            return str(value).strip()
    return None


def _source_ref(row: Mapping[str, Any]) -> dict[str, Any]:
    url = _url(row)
    snippet = _clean_text(
        row.get("content_snippet")
        or row.get("top_post_content_snippet")
        or row.get("snippet"),
        320,
    )
    return {
        "author": row.get("author"),
        "channel": row.get("channel"),
        "source_url": url,
        "url": url,
        "url_available": bool(url),
        "canonical_post_id": row.get("canonical_post_id") or row.get("top_post_canonical_post_id"),
        "sentiment": row.get("sentiment"),
        "topic_id": row.get("topic_id"),
        "topic_label": row.get("topic_label"),
        "snippet": snippet,
        "content_snippet": snippet,
        "interactions": row.get("interactions") or row.get("total_interactions") or row.get("topic_interactions"),
        "views": row.get("views") or row.get("total_views") or row.get("topic_views"),
    }


def _source_label(ref: Mapping[str, Any]) -> str:
    author = _clean_text(ref.get("author"), 60) or "Unknown author"
    channel = _clean_text(ref.get("channel"), 30) or "Unknown channel"
    return f"{author} / {channel}"


def _sentiment_distribution(report_input: Mapping[str, Any]) -> dict[str, Any]:
    rows = _rows(report_input, "qt_dsm_sentiment_distribution_overall")
    by = {str(row.get("sentiment") or "").casefold(): row for row in rows}
    positive = _num(by.get("positive", {}).get("share_of_classified_posts_pct"))
    negative = _num(by.get("negative", {}).get("share_of_classified_posts_pct"))
    neutral = _num(by.get("neutral", {}).get("share_of_classified_posts_pct"))
    return {
        "rows": rows,
        "positive_share_pct": positive,
        "neutral_share_pct": neutral,
        "negative_share_pct": negative,
        "net_sentiment_by_count": round(positive - negative, 1),
    }


def _posture(sent: Mapping[str, Any]) -> dict[str, Any]:
    net = _num(sent.get("net_sentiment_by_count"))
    neg = _num(sent.get("negative_share_pct"))
    if neg >= 35 or net <= -20:
        return {
            "label": "RED / HIGH RISK",
            "short_label": "HIGH RISK",
            "rationale": "Porsi negatif tinggi atau net sentiment sudah masuk area risiko.",
            "severity": "red",
        }
    if neg >= 20 or net <= -5:
        return {
            "label": "AMBER / WATCH",
            "short_label": "WATCH",
            "rationale": "Ada tekanan negatif yang perlu dipantau dan diberi respons selektif.",
            "severity": "amber",
        }
    return {
        "label": "GREEN / STABLE",
        "short_label": "STABLE",
        "rationale": "Sentimen tidak menunjukkan tekanan negatif dominan pada scope ini.",
        "severity": "green",
    }


def _kpi(report_input: Mapping[str, Any]) -> dict[str, Any]:
    rows = _rows(report_input, "qt_dsm_kpi_summary")
    row = rows[0] if rows else {}
    return {
        "total_mentions": int(_num(row.get("canonical_post_count"))),
        "total_interactions": _num(row.get("interactions")),
        "total_views": _num(row.get("views")),
        "total_authors": int(_num(row.get("unique_author_count"))),
        "avg_interactions_per_applicable_post": row.get("avg_interactions_per_applicable_post"),
        "interaction_coverage_pct": row.get("interaction_coverage_pct"),
        "views_coverage_pct": row.get("views_coverage_pct"),
        "sentiment_coverage_pct": row.get("sentiment_coverage_pct"),
        "topic_completion_coverage_pct": row.get("topic_completion_coverage_pct"),
        "topic_report_coverage_pct": row.get("topic_report_coverage_pct"),
    }


def _top_channel(report_input: Mapping[str, Any], key: str = "interactions") -> dict[str, Any] | None:
    rows = _rows(report_input, "qt_dsm_sentiment_by_channel_table")
    selected = _top(rows, key, 1)
    return selected[0] if selected else None


def _top_topic_rows(report_input: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _rows(report_input, "qt_dsm_top_topics_ranked")


def _topic_evidence(report_input: Mapping[str, Any], sentiment: str | None = None) -> list[dict[str, Any]]:
    rows = _rows(report_input, "ql_dsm_topic_sentiment")
    if sentiment:
        rows = [row for row in rows if str(row.get("sentiment") or "").casefold() == sentiment]
    return sorted(
        rows,
        key=lambda row: (_num(row.get("topic_interactions")), _num(row.get("interactions"))),
        reverse=True,
    )


def _content_evidence(report_input: Mapping[str, Any], sentiment: str | None = None) -> list[dict[str, Any]]:
    rows = _rows(report_input, "ql_dsm_top_content_positive_negative")
    if sentiment:
        rows = [row for row in rows if str(row.get("sentiment") or "").casefold() == sentiment]
    return sorted(rows, key=lambda row: (_num(row.get("interactions")), _num(row.get("views"))), reverse=True)


def _account_profiles(report_input: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _rows(report_input, "ql_dsm_top_engagement_account_profile")


def _coverage_note(kpi: Mapping[str, Any]) -> dict[str, Any]:
    topic_cov = _num(kpi.get("topic_completion_coverage_pct"))
    if topic_cov <= 0:
        return {
            "level": "missing",
            "message": "Topic enrichment belum tersedia; topic/thematic insight harus dianggap N/A.",
            "safe_for_topic_conclusion": False,
        }
    if topic_cov < 60:
        return {
            "level": "low",
            "message": (
                f"Topic coverage baru {_fmt_pct(topic_cov)}; thematic insight hanya early signal, "
                "belum representatif untuk seluruh percakapan."
            ),
            "safe_for_topic_conclusion": False,
        }
    if topic_cov < 90:
        return {
            "level": "partial",
            "message": (
                f"Topic coverage {_fmt_pct(topic_cov)}; cukup untuk directional readout tetapi tetap cantumkan caveat."
            ),
            "safe_for_topic_conclusion": True,
        }
    return {
        "level": "complete",
        "message": f"Topic coverage {_fmt_pct(topic_cov)}; topic insight aman dipakai sebagai ranking report.",
        "safe_for_topic_conclusion": True,
    }


def _risk_issue_label(report_input: Mapping[str, Any]) -> str:
    neg_topic = (_topic_evidence(report_input, "negative") or [])[:1]
    neg_content = (_content_evidence(report_input, "negative") or [])[:1]
    source = neg_topic[0] if neg_topic else (neg_content[0] if neg_content else {})
    return _clean_text(source.get("topic_label") or "isu negatif utama", 90)


def _build_executive_summary(report_input: Mapping[str, Any]) -> dict[str, Any]:
    kpi = _kpi(report_input)
    sent = _sentiment_distribution(report_input)
    posture = _posture(sent)
    channel = _top_channel(report_input, "interactions")
    account = (_account_profiles(report_input) or [{}])[0]
    top_topics = _top_topic_rows(report_input)
    top_topic = top_topics[0] if top_topics else None
    issue_label = _risk_issue_label(report_input)
    coverage = _coverage_note(kpi)

    situation = (
        f"Percakapan harian mencatat {_fmt_int(kpi['total_mentions'])} post unik, "
        f"{_fmt_num(kpi['total_interactions'])} interactions, dan {_fmt_num(kpi['total_views'])} views."
    )
    risk = (
        f"Posture berada di {posture['label']} karena negatif {_fmt_pct(sent['negative_share_pct'])} "
        f"dan net sentiment {sent['net_sentiment_by_count']:+.1f}."
    )
    implication = (
        f"Perhatian perlu difokuskan pada {issue_label}; isu ini perlu dipantau sebagai potensi eskalasi reputasi, "
        "terutama bila engagement terkonsentrasi pada akun/media eksternal."
    )
    if channel:
        implication += (
            f" Channel prioritas: {channel.get('channel')} "
            f"({_fmt_num(channel.get('interactions'))} interactions dari {_fmt_int(channel.get('post_count'))} post)."
        )
    priority_move = (
        "Prioritas 24 jam: pisahkan respons empati, klarifikasi fakta/proses, dan monitoring komentar berisiko; "
        "hindari membalas spekulasi personal tanpa statement resmi yang jelas."
        if posture["severity"] == "red"
        else "Prioritas 24 jam: pantau top channel, amplifikasi konten positif yang terbukti, dan siapkan response rule bila tekanan negatif naik."
    )

    bullets = [situation, risk]
    if top_topic:
        bullets.append(
            f"Top topic: {_clean_text(top_topic.get('topic_label'), 80)} "
            f"({_fmt_num(top_topic.get('interactions'))} interactions; {_fmt_int(top_topic.get('post_count'))} post)."
        )
    else:
        bullets.append("Top topic belum tersedia karena taxonomy/classification topic belum lengkap.")
    if channel:
        bullets.append(
            f"Channel driver terbesar: {channel.get('channel')} — {_fmt_num(channel.get('interactions'))} interactions; views dilaporkan terpisah."
        )
    if account:
        bullets.append(
            f"Top engagement account: {_clean_text(account.get('author'), 80)} "
            f"({_clean_text(account.get('channel'), 40)}; {_fmt_num(account.get('total_interactions'))} interactions)."
        )

    return {
        "posture": posture,
        "kpi_cards": [
            {"label": "Total Mentions", "value": _fmt_int(kpi["total_mentions"]), "note": "canonical social posts"},
            {"label": "Total Interactions", "value": _fmt_num(kpi["total_interactions"]), "note": "views excluded"},
            {"label": "Total Views", "value": _fmt_num(kpi["total_views"]), "note": "separate from interactions"},
            {"label": "Net Sentiment", "value": f"{sent['net_sentiment_by_count']:+.1f}", "note": "positive % - negative %"},
        ],
        "bullets": bullets[:5],
        "executive_readout": {
            "situation": situation,
            "risk_diagnosis": risk,
            "business_implication": implication,
            "priority_move_next_24h": priority_move,
            "topic_coverage_note": coverage["message"],
        },
        "top_topic": top_topic,
        "top_channel": channel,
        "top_account": account,
        "coverage_note": coverage,
    }


def _make_action(
    *,
    priority: str,
    action_type: str,
    focus_area: str,
    recommended_action: str,
    rationale: str,
    supporting_evidence: str,
    expected_impact: str,
    owner_next_step: str,
    evidence_refs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    refs = evidence_refs or []
    return {
        "priority": priority,
        "action_type": action_type,
        "focus_area": focus_area,
        "recommended_action": recommended_action,
        "rationale": rationale,
        "supporting_evidence": supporting_evidence,
        "expected_impact": expected_impact,
        "owner_next_step": owner_next_step,
        "evidence_refs": refs,
        "evidence_urls": [ref.get("source_url") for ref in refs if ref.get("source_url")],
        "requires_url_in_ppt": True,
    }


def _build_action_plan(report_input: Mapping[str, Any]) -> list[dict[str, Any]]:
    sent = _sentiment_distribution(report_input)
    positive_topic = (_topic_evidence(report_input, "positive") or [])[:1]
    negative_topic = (_topic_evidence(report_input, "negative") or [])[:1]
    neutral_topic = (_topic_evidence(report_input, "neutral") or [])[:1]
    positive_content = (_content_evidence(report_input, "positive") or [])[:1]
    negative_content = (_content_evidence(report_input, "negative") or [])[:1]
    channel = _top_channel(report_input, "interactions") or {}
    account = (_account_profiles(report_input) or [{}])[0]
    top_negative_content = negative_content[0] if negative_content else {}

    actions: list[dict[str, Any]] = []

    pos_focus = positive_topic[0] if positive_topic else (positive_content[0] if positive_content else {})
    if pos_focus:
        label = pos_focus.get("topic_label") or "konten positif dengan engagement tertinggi"
        ref = _source_ref(pos_focus)
        actions.append(
            _make_action(
                priority="MEDIUM",
                action_type="Amplify Strength",
                focus_area=_clean_text(label, 90),
                recommended_action=(
                    "Amplifikasi hanya narasi positif yang relevan dengan konteks isu hari ini; "
                    "utamakan format yang evidence-backed dan tidak menutupi risiko utama."
                ),
                rationale="Ada sinyal positif yang menghasilkan engagement, tetapi perlu dijaga agar tidak terlihat tone-deaf terhadap isu negatif dominan.",
                supporting_evidence=(
                    f"{_source_label(ref)}; {_fmt_num(ref.get('interactions'))} interactions."
                ),
                expected_impact="Membantu menyeimbangkan percakapan tanpa mengabaikan isu risiko utama.",
                owner_next_step="Content/Comms: pilih 1 konten positif untuk amplification terbatas dan review tone sebelum publish.",
                evidence_refs=[ref],
            )
        )
    else:
        actions.append(
            _make_action(
                priority="LOW",
                action_type="Amplify Strength",
                focus_area="N/A",
                recommended_action="Tunda amplification sampai ada evidence positif yang cukup jelas.",
                rationale="Action tidak dibuat tanpa contoh konten/evidence positif.",
                supporting_evidence="Positive qualitative evidence belum tersedia.",
                expected_impact="Menghindari rekomendasi yang tidak berbasis data.",
                owner_next_step="Lengkapi topic/content evidence atau perluas scope periode.",
            )
        )

    neg_focus = negative_topic[0] if negative_topic else (negative_content[0] if negative_content else {})
    if neg_focus:
        neg_priority = "HIGH" if _num(sent.get("negative_share_pct")) >= 20 else "MEDIUM"
        label = neg_focus.get("topic_label") or "konten negatif dengan engagement tertinggi"
        ref = _source_ref(neg_focus)
        actions.append(
            _make_action(
                priority=neg_priority,
                action_type="Respond to Risk",
                focus_area=_clean_text(label, 90),
                recommended_action=(
                    "Siapkan holding statement empathy-first: akui perhatian publik, jelaskan proses tanggung jawab/penanganan, "
                    "dan arahkan pembaruan hanya ke kanal resmi. Jangan masuk debat spekulasi personal."
                ),
                rationale=(
                    "Isu negatif dominan berpotensi melebar dari kejadian utama menjadi pertanyaan akuntabilitas brand/figur terkait."
                ),
                supporting_evidence=(
                    f"Negatif {_fmt_pct(sent.get('negative_share_pct'))}; {_source_label(ref)}; "
                    f"{_fmt_num(ref.get('interactions'))} interactions."
                ),
                expected_impact="Menurunkan risiko misinformasi dan menjaga konsistensi respons lintas kanal.",
                owner_next_step="PR + Social Care: draft 3-part response, tetapkan escalation trigger, dan review legal/comms sebelum reply publik.",
                evidence_refs=[ref],
            )
        )
    else:
        actions.append(
            _make_action(
                priority="LOW",
                action_type="Respond to Risk",
                focus_area="Risk watch",
                recommended_action="Monitor negatif harian; belum ada evidence negatif dominan yang cukup untuk respons publik.",
                rationale="Tidak ada top negative evidence yang cukup kuat pada qualitative view.",
                supporting_evidence=f"Negatif {_fmt_pct(sent.get('negative_share_pct'))}; qualitative negative evidence N/A.",
                expected_impact="Menjaga respons tetap proporsional.",
                owner_next_step="Social care: monitor mention negatif baru dan eskalasi bila volume/engagement naik.",
            )
        )

    if neutral_topic:
        neu = neutral_topic[0]
        ref = _source_ref(neu)
        actions.append(
            _make_action(
                priority="MEDIUM",
                action_type="Monitor Inquiry",
                focus_area=_clean_text(neu.get("topic_label"), 90),
                recommended_action="Pisahkan pertanyaan faktual, komentar simpati, dan spekulasi; siapkan FAQ singkat untuk pertanyaan yang berulang.",
                rationale="Percakapan netral sering menjadi ruang awal klarifikasi sebelum berubah menjadi keluhan atau sentimen negatif.",
                supporting_evidence=(
                    f"{_fmt_num(neu.get('topic_interactions'))} interactions pada topic netral; {_source_label(ref)}."
                ),
                expected_impact="Mengurangi kebingungan publik dan menjaga respons tetap konsisten.",
                owner_next_step="Monitoring team: buat tag untuk pertanyaan berulang dan update FAQ sebelum shift berikutnya.",
                evidence_refs=[ref],
            )
        )
    else:
        actions.append(
            _make_action(
                priority="LOW",
                action_type="Monitor Inquiry",
                focus_area="Top channel monitoring",
                recommended_action="Monitor channel dengan volume/interactions terbesar untuk mendeteksi pertanyaan berulang.",
                rationale="Neutral topic evidence belum tersedia, tetapi channel driver tetap bisa dipakai untuk monitoring harian.",
                supporting_evidence=(
                    f"Top channel: {_clean_text(channel.get('channel'), 40)}; {_fmt_num(channel.get('interactions'))} interactions."
                    if channel
                    else "Channel evidence N/A."
                ),
                expected_impact="Menjaga tim tetap responsif tanpa membuat asumsi topic.",
                owner_next_step="Monitoring team: cek mention di top channel pada batch berikutnya.",
            )
        )

    if neg_focus:
        ref = _source_ref(neg_focus)
        actions.append(
            _make_action(
                priority="HIGH" if _num(sent.get("negative_share_pct")) >= 35 else "MEDIUM",
                action_type="Prepare Response",
                focus_area=_clean_text(neg_focus.get("topic_label") or "risk response", 90),
                recommended_action=(
                    "Siapkan response kit 24 jam: public reply pendek, holding statement, escalation note, dan daftar post prioritas untuk dipantau."
                ),
                rationale="Daily report harus menghasilkan kesiapan operasional, bukan hanya snapshot dashboard.",
                supporting_evidence=_clean_text(ref.get("snippet"), 180) or "Negative evidence tersedia tanpa snippet panjang.",
                expected_impact="Mempercepat respons bila isu yang sama naik lagi pada monitoring berikutnya.",
                owner_next_step="PR + Social care: review template, assign PIC, dan pantau URL evidence prioritas.",
                evidence_refs=[ref],
            )
        )
    else:
        actions.append(
            _make_action(
                priority="LOW",
                action_type="Prepare Response",
                focus_area="Risk response guardrail",
                recommended_action="Siapkan response rule dasar sebagai guardrail, tanpa public statement baru.",
                rationale="Belum ada negative evidence dominan, tetapi guardrail tetap diperlukan untuk monitoring harian.",
                supporting_evidence="Negative evidence N/A.",
                expected_impact="Membuat tim siap tanpa over-response.",
                owner_next_step="PR/Social care: tetapkan threshold eskalasi.",
            )
        )

    if account:
        ref = _source_ref(account)
        actions.append(
            _make_action(
                priority="MEDIUM",
                action_type="Content Opportunity",
                focus_area=_clean_text(channel.get("channel") or account.get("channel") or "top channel/account", 90),
                recommended_action=(
                    "Gunakan format top-performing content sebagai referensi monitoring dan response placement, bukan otomatis ditiru sebagai konten promosi."
                ),
                rationale="Top account/channel menunjukkan lokasi perhatian audiens yang paling efisien untuk dipantau dan dimasuki secara selektif.",
                supporting_evidence=(
                    f"{_source_label(ref)}; {_fmt_num(account.get('total_interactions'))} interactions."
                ),
                expected_impact="Meningkatkan efisiensi monitoring dan menjaga brand hadir di percakapan yang relevan.",
                owner_next_step="Content/Social team: tentukan apakah perlu reply, pin statement, atau monitoring saja pada top URL.",
                evidence_refs=[ref] if ref.get("source_url") or ref.get("snippet") else [],
            )
        )
    else:
        actions.append(
            _make_action(
                priority="LOW",
                action_type="Content Opportunity",
                focus_area="N/A",
                recommended_action="Tunda content opportunity sampai top account/content evidence tersedia.",
                rationale="Top account evidence N/A.",
                supporting_evidence="Top account evidence N/A.",
                expected_impact="Menghindari rekomendasi tanpa evidence.",
                owner_next_step="Lengkapi qualitative evidence.",
            )
        )

    ordered: list[dict[str, Any]] = []
    for action_type in ACTION_TYPES:
        match = next((item for item in actions if item["action_type"] == action_type), None)
        if match:
            ordered.append(match)
    return ordered


def _build_thematic_topics(report_input: Mapping[str, Any]) -> dict[str, Any]:
    status = _view_status(report_input, "qt_dsm_top_topics_ranked")
    kpi = _kpi(report_input)
    coverage = _coverage_note(kpi)
    if status["status"] != "READY" or status["row_count"] == 0:
        return {
            "available": False,
            "reason": status.get("reason") or "Topic taxonomy/classification belum tersedia.",
            "positive": [],
            "neutral": [],
            "negative": [],
            "coverage_note": coverage,
            "narrative": "Thematic Topics belum dapat dirender karena report-topic LLM belum tersedia untuk scope ini.",
        }

    topics = _top_topic_rows(report_input)
    evidence = _topic_evidence(report_input)
    out: dict[str, Any] = {
        "available": True,
        "positive": [],
        "neutral": [],
        "negative": [],
        "coverage_note": coverage,
        "topic_rows": topics,
    }
    for sentiment in SENTIMENT_ORDER:
        rows = [row for row in evidence if str(row.get("sentiment") or "").casefold() == sentiment]
        out[sentiment] = [
            {
                "topic_label": row.get("topic_label"),
                "topic_id": row.get("topic_id"),
                "post_count": row.get("topic_post_count"),
                "interactions": row.get("topic_interactions"),
                "one_liner": _clean_text(row.get("content_snippet"), 180),
                "evidence_ref": _source_ref(row),
                "source_url": _url(row),
                "requires_url_in_ppt": True,
            }
            for row in rows[:3]
        ]
    top = topics[0] if topics else {}
    out["narrative"] = (
        f"Percakapan tematik paling kuat mengarah ke {_clean_text(top.get('topic_label'), 90)} "
        f"dengan {_fmt_num(top.get('interactions'))} interactions dan {_fmt_int(top.get('post_count'))} post. "
        f"{coverage['message']}"
        if top
        else "Topic ranking tersedia tetapi belum memiliki top topic yang cukup kuat."
    )
    return out


def _build_sentiment_section(report_input: Mapping[str, Any]) -> dict[str, Any]:
    sent = _sentiment_distribution(report_input)
    channels = _rows(report_input, "qt_dsm_sentiment_by_channel_table")
    top_negative = sorted(channels, key=lambda row: (_num(row.get("negative_share_pct")), _num(row.get("negative_posts"))), reverse=True)[:1]
    top_interactions = sorted(channels, key=lambda row: _num(row.get("interactions")), reverse=True)[:1]
    readout = []
    if top_negative:
        row = top_negative[0]
        readout.append(f"Channel risiko tertinggi: {row.get('channel')} ({_fmt_pct(row.get('negative_share_pct'))} negatif).")
    if top_interactions:
        row = top_interactions[0]
        readout.append(f"Channel engagement terbesar: {row.get('channel')} ({_fmt_num(row.get('interactions'))} interactions).")
    readout.append("Interpretasi channel harus memisahkan interactions dan views sesuai metric contract.")
    return {
        "distribution": sent,
        "channel_table": channels,
        "readout": " ".join(readout) if readout else "Readout channel sentiment N/A.",
    }


def _build_critical_deep_dive(report_input: Mapping[str, Any], executive: Mapping[str, Any]) -> dict[str, Any] | None:
    sent = _sentiment_distribution(report_input)
    posture = executive.get("posture", {})
    negative_topic = (_topic_evidence(report_input, "negative") or [])[:3]
    negative_content = (_content_evidence(report_input, "negative") or [])[:5]
    if posture.get("severity") != "red" and _num(sent.get("negative_share_pct")) < 35 and not negative_topic:
        return None

    issue_label = _risk_issue_label(report_input)
    primary_refs = [_source_ref(row) for row in (negative_topic or negative_content)[:3]]
    return {
        "available": True,
        "issue_label": issue_label,
        "risk_readout": (
            f"Isu prioritas hari ini adalah {issue_label}. Negatif {_fmt_pct(sent.get('negative_share_pct'))} "
            f"dengan net sentiment {sent.get('net_sentiment_by_count'):+.1f}."
        ),
        "why_it_matters": (
            "Isu dengan engagement tinggi dapat bergeser dari percakapan insiden/keluhan menjadi penilaian akuntabilitas brand. "
            "Karena itu response harus konsisten, empatik, dan berbasis fakta."
        ),
        "response_guardrails": [
            "Acknowledge concern/empathy first; jangan mulai dari promosi atau denial.",
            "Pisahkan fakta yang sudah dapat dikonfirmasi dari proses investigasi/penanganan.",
            "Hindari debat personal/spekulatif; arahkan ke kanal resmi dan update yang terverifikasi.",
            "Prioritaskan monitoring pada URL dengan interactions tertinggi.",
        ],
        "evidence_refs": primary_refs,
        "requires_url_in_ppt": True,
    }


def _build_key_findings(report_input: Mapping[str, Any], executive: Mapping[str, Any], actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    del actions
    sent = _sentiment_distribution(report_input)
    top_positive = _content_evidence(report_input, "positive")[:1]
    top_negative = _content_evidence(report_input, "negative")[:1]
    channel = _top_channel(report_input, "interactions") or {}
    issue_label = _risk_issue_label(report_input)
    return [
        {
            "type": "Risk Trigger",
            "finding": f"Risiko utama bukan sekadar volume negatif, tetapi konsentrasi engagement pada isu {issue_label}.",
            "evidence": _clean_text((top_negative[0].get("content_snippet") if top_negative else "Negative evidence N/A."), 200),
            "evidence_ref": _source_ref(top_negative[0]) if top_negative else None,
        },
        {
            "type": "Strengths",
            "finding": (
                f"Masih ada ruang positif ({_fmt_pct(sent.get('positive_share_pct'))}), tetapi amplification harus sangat selektif agar tidak terlihat mengabaikan isu risiko."
            ),
            "evidence": _clean_text((top_positive[0].get("content_snippet") if top_positive else "Positive evidence N/A."), 200),
            "evidence_ref": _source_ref(top_positive[0]) if top_positive else None,
        },
        {
            "type": "Weaknesses",
            "finding": (
                f"Negatif {_fmt_pct(sent.get('negative_share_pct'))} menunjukkan perlunya response rule yang jelas: kapan monitor, kapan reply, kapan eskalasi."
            ),
            "evidence": _clean_text((top_negative[0].get("content_snippet") if top_negative else "Negative evidence N/A."), 200),
            "evidence_ref": _source_ref(top_negative[0]) if top_negative else None,
        },
        {
            "type": "Opportunities",
            "finding": (
                f"Kanal {_clean_text(channel.get('channel'), 40) or 'N/A'} menjadi titik distribusi prioritas untuk monitoring dan placement response."
            ),
            "evidence": (
                f"{_fmt_num(channel.get('interactions'))} interactions; {_fmt_int(channel.get('post_count'))} post."
                if channel
                else "Channel evidence N/A."
            ),
            "evidence_ref": None,
        },
    ]


def _evidence_appendix(report_input: Mapping[str, Any], limit: int = 12) -> list[dict[str, Any]]:
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    sources = (
        _content_evidence(report_input, "negative")
        + _content_evidence(report_input, "positive")
        + _topic_evidence(report_input)
        + _account_profiles(report_input)
    )
    for row in sources:
        ref = _source_ref(row)
        key = ref.get("source_url") or ref.get("canonical_post_id") or ref.get("snippet")
        if not key or str(key) in seen:
            continue
        seen.add(str(key))
        rows.append(
            {
                "rank": len(rows) + 1,
                "source_label": _source_label(ref),
                "sentiment": ref.get("sentiment"),
                "topic_label": ref.get("topic_label"),
                "interactions": ref.get("interactions"),
                "views": ref.get("views"),
                "source_url": ref.get("source_url"),
                "snippet": _clean_text(ref.get("snippet"), 180),
                "url_available": bool(ref.get("source_url")),
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _slide(slide_id: str, title: str, subtitle: str, components: list[dict[str, Any]], speaker_notes: str = "") -> dict[str, Any]:
    return {
        "slide_id": slide_id,
        "title": title,
        "subtitle": subtitle,
        "components": components,
        "speaker_notes": speaker_notes,
    }


def _build_slides(report_input: Mapping[str, Any], outline: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ctx = _as_mapping(report_input.get("context"))
    period = _as_mapping(ctx.get("period"))
    project = ctx.get("project_name")
    kpi = _kpi(report_input)
    executive = _build_executive_summary(report_input)
    actions = _build_action_plan(report_input)
    thematic = _build_thematic_topics(report_input)
    sentiment = _build_sentiment_section(report_input)
    profiles = _account_profiles(report_input)
    authors = _rows(report_input, "qt_dsm_top_authors_ranked")
    findings = _build_key_findings(report_input, executive, actions)
    deep_dive = _build_critical_deep_dive(report_input, executive)
    appendix = _evidence_appendix(report_input)

    meta = {
        "project_name": project,
        "period": period,
        "posture": executive["posture"],
        "kpi": kpi,
        "validation": report_input.get("validation"),
        "outline_status": outline.get("outline_status"),
        "topic_coverage_note": executive["coverage_note"],
    }

    slides = [
        _slide(
            "dsm_01_header",
            "DAILY SOCIAL MEDIA REPORT",
            f"{project} · {period.get('start_date')} to {period.get('end_date')} · Social Media Monitoring",
            [
                {"type": "hero_statement", "text": executive["executive_readout"]["situation"]},
                {"type": "kpi_cards", "items": executive["kpi_cards"]},
                {"type": "posture_badge", "item": executive["posture"]},
                {"type": "coverage_warning", "item": executive["coverage_note"]},
            ],
            "Opening slide. Keep it executive and action-oriented. Include coverage caveat if topic coverage is low.",
        ),
        _slide(
            "dsm_02_executive_summary",
            "EXECUTIVE SUMMARY",
            "Situation, risk diagnosis, implication, and priority move.",
            [
                {"type": "executive_readout", "item": executive["executive_readout"]},
                {"type": "bullet_summary", "items": executive["bullets"]},
                {"type": "top_topic_card", "item": executive.get("top_topic")},
                {"type": "top_engagement_account", "item": executive.get("top_account")},
            ],
            "This must appear before Action Plan. Narrate so-what and priority move; do not add unsupported recommendations.",
        ),
        _slide(
            "dsm_03_daily_action_plan",
            "DAILY ACTION PLAN",
            "Evidence-backed next actions for the next monitoring cycle.",
            [
                {"type": "action_plan_table", "items": actions},
                {"type": "action_plan_instruction", "text": "Every row must display at least one evidence URL when available."},
            ],
            "Action Plan is mandatory immediately after Executive Summary. Preserve evidence_urls as visible hyperlinks or short URLs.",
        ),
    ]

    if deep_dive:
        slides.append(
            _slide(
                "dsm_04_critical_issue_deep_dive",
                "CRITICAL ISSUE DEEP DIVE",
                "Why the top risk matters and how the team should respond.",
                [
                    {"type": "critical_issue_readout", "item": deep_dive},
                    {"type": "evidence_refs", "items": deep_dive.get("evidence_refs", [])},
                ],
                "Optional high-risk slide. Include source URLs for all evidence refs.",
            )
        )

    slides.extend(
        [
            _slide(
                "dsm_05_thematic_topics" if deep_dive else "dsm_04_thematic_topics",
                "THEMATIC TOPICS",
                "Top positive, neutral, and negative topics as the primary evidence layer.",
                [
                    {"type": "topic_cards_by_sentiment", "item": thematic},
                    {"type": "topic_coverage_warning", "item": thematic.get("coverage_note")},
                ],
                "If thematic.available=false, render an honest N/A slide. If coverage is low, label it as early classified signal.",
            ),
            _slide(
                "dsm_06_sentiment_analysis" if deep_dive else "dsm_05_sentiment_analysis",
                "SENTIMENT ANALYSIS",
                "Overall sentiment and channel-level posture.",
                [
                    {"type": "sentiment_distribution", "item": sentiment["distribution"]},
                    {"type": "sentiment_by_channel_table", "items": sentiment["channel_table"]},
                    {"type": "readout", "text": sentiment["readout"]},
                ],
                "Suggested visual: donut/pie for distribution plus compact channel table.",
            ),
            _slide(
                "dsm_07_top_performing_authors" if deep_dive else "dsm_06_top_performing_authors",
                "TOP PERFORMING AUTHORS",
                "Author ranking by interactions, with representative content and URL when available.",
                [
                    {"type": "author_rank_table", "items": authors[:10]},
                    {"type": "top_account_cards", "items": profiles[:3]},
                ],
                "Use ranked table; include top_post_url/source_url where available; avoid generic influencer commentary.",
            ),
            _slide(
                "dsm_08_top_performing_content" if deep_dive else "dsm_07_top_performing_content",
                "TOP PERFORMING CONTENT",
                "Evidence cards for highest positive and negative content. URL is mandatory when available.",
                [
                    {"type": "positive_content_cards", "items": _content_evidence(report_input, "positive")[:5], "must_show_url": True},
                    {"type": "negative_content_cards", "items": _content_evidence(report_input, "negative")[:5], "must_show_url": True},
                ],
                "Snippets must be copied only from content_snippet; render source_url as visible link/short URL.",
            ),
            _slide(
                "dsm_09_key_findings" if deep_dive else "dsm_08_key_findings",
                "KEY FINDINGS",
                "Risk trigger, strengths, weaknesses, and opportunities after the Action Plan.",
                [
                    {"type": "finding_cards", "items": findings},
                ],
                "Findings support the Action Plan; include evidence URLs when finding has evidence_ref.",
            ),
        ]
    )

    if appendix:
        slides.append(
            _slide(
                "dsm_10_evidence_appendix" if deep_dive else "dsm_09_evidence_appendix",
                "APPENDIX — POST EVIDENCE LINKS",
                "Audit trail for posts used as evidence in the report.",
                [
                    {"type": "evidence_url_table", "items": appendix, "must_show_url": True},
                ],
                "Appendix slide. Every row should show source_url if available. Do not hide URLs.",
            )
        )

    slides.append(
        _slide(
            "dsm_11_footer_disclaimer" if deep_dive and appendix else "dsm_10_footer_disclaimer" if deep_dive or appendix else "dsm_09_footer_disclaimer",
            "SOURCES & NOTES",
            "Data source, metric contract, limitations, and AI-assisted insight note.",
            [
                {"type": "scope", "item": {"project_name": project, "period": period, "channels": ctx.get("channels")}},
                {"type": "metric_contract", "item": _as_mapping(report_input.get("metric_readiness")).get("metric_contract")},
                {"type": "limitations", "items": report_input.get("limitations") or []},
                {"type": "coverage_note", "item": executive["coverage_note"]},
                {"type": "note", "text": "Data internal: Cogan canonical social posts. Interactions exclude views. Raw Topic Extraction is not used as report topic."},
            ],
            "Use this as final source/limitation slide.",
        )
    )
    return slides, meta


def _view_rows_preview(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    return [dict(row) for row in rows[: max(0, limit)]]


def _markdown_table(rows: list[dict[str, Any]], columns: list[str], limit: int = 10) -> str:
    if not rows:
        return "_No rows._"
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows[:limit]:
        cells = []
        for col in columns:
            value = row.get(col)
            if isinstance(value, float):
                value = _fmt_num(value)
            cells.append(_clean_text(value, 90).replace("|", "/"))
        body.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, sep, *body])


def build_daily_social_report_data_preview(
    report_input_id: str,
    *,
    include_evidence_limit: int = 10,
) -> dict[str, Any]:
    """Build a user-facing Task 1 data preview before PPT creation."""
    if not isinstance(report_input_id, str) or not report_input_id.strip():
        raise DailySocialRendererError("report_input_id wajib diisi.")
    report_input_id = report_input_id.strip()
    report_input = get_report_input(report_input_id)
    if report_input is None:
        raise DailySocialRendererError(f"report_input_id '{report_input_id}' tidak ditemukan.")
    if report_input.get("report_type_id") != REPORT_TYPE_ID:
        raise DailySocialRendererError(
            f"Preview ini hanya untuk {REPORT_TYPE_ID}, bukan {report_input.get('report_type_id')}."
        )

    ctx = _as_mapping(report_input.get("context"))
    period = _as_mapping(ctx.get("period"))
    kpi = _kpi(report_input)
    sent = _sentiment_distribution(report_input)
    posture = _posture(sent)
    topic_cov = _coverage_note(kpi)
    view_statuses = _all_view_statuses(report_input)
    top_topics = _top_topic_rows(report_input)
    authors = _rows(report_input, "qt_dsm_top_authors_ranked")
    channels = _rows(report_input, "qt_dsm_sentiment_by_channel_table")
    content = _content_evidence(report_input)
    topic_evidence = _topic_evidence(report_input)
    account_profiles = _account_profiles(report_input)
    appendix = _evidence_appendix(report_input, include_evidence_limit)

    readiness = "READY"
    if any(v["status"] != "READY" for v in view_statuses):
        readiness = "READY_WITH_LIMITATIONS"
    if not topic_cov["safe_for_topic_conclusion"]:
        readiness = "READY_WITH_TOPIC_CAVEAT"

    markdown = f"""# Daily Social Data Preview — {ctx.get('project_name')}

**Period:** {period.get('start_date')} → {period.get('end_date')}  
**Readiness:** {readiness}  
**Posture:** {posture['label']}  
**Topic coverage:** {topic_cov['message']}

## 1. KPI Summary

| Metric | Value |
|---|---:|
| Total mentions | {_fmt_int(kpi['total_mentions'])} |
| Total interactions | {_fmt_num(kpi['total_interactions'])} |
| Total views | {_fmt_num(kpi['total_views'])} |
| Total authors | {_fmt_int(kpi['total_authors'])} |
| Net sentiment | {sent['net_sentiment_by_count']:+.1f} |

## 2. Sentiment by Channel

{_markdown_table(channels, ['channel', 'post_count', 'positive_share_pct', 'neutral_share_pct', 'negative_share_pct', 'interactions', 'views'], include_evidence_limit)}

## 3. Top Topics

{_markdown_table(top_topics, ['rank', 'topic_label', 'post_count', 'interactions', 'views', 'dominant_sentiment'], include_evidence_limit)}

## 4. Top Authors

{_markdown_table(authors, ['rank', 'author', 'channel', 'post_count', 'total_interactions', 'total_views', 'top_post_url'], include_evidence_limit)}

## 5. Qualitative Evidence — Top Content

{_markdown_table(content, ['sentiment', 'topic_label', 'author', 'channel', 'interactions', 'views', 'source_url'], include_evidence_limit)}

## 6. Qualitative Evidence — Topic x Sentiment

{_markdown_table(topic_evidence, ['sentiment', 'topic_label', 'topic_post_count', 'topic_interactions', 'author', 'channel', 'source_url'], include_evidence_limit)}

## 7. Evidence URLs for Audit

{_markdown_table(appendix, ['rank', 'source_label', 'sentiment', 'topic_label', 'interactions', 'views', 'source_url'], include_evidence_limit)}

## 8. PPT Recommendation

- {'Aman membuat PPT dengan caveat topic coverage.' if readiness != 'READY' else 'Aman membuat PPT.'}
- Jika topic coverage rendah, tulis label **early classified topic signal** pada slide topic.
- URL evidence wajib ditampilkan di Top Content, Action Plan evidence, dan Appendix.
"""

    return {
        "success": True,
        "preview_version": "daily_social_report_data_preview_v1",
        "preview_id": _now_id("dsm_data_preview"),
        "report_input_id": report_input_id,
        "report_type_id": REPORT_TYPE_ID,
        "project_name": ctx.get("project_name"),
        "period": dict(period),
        "readiness": readiness,
        "posture": posture,
        "kpi": kpi,
        "sentiment": sent,
        "topic_coverage_note": topic_cov,
        "view_statuses": view_statuses,
        "quantitative_preview": {
            "qt_dsm_kpi_summary": _view_rows_preview(_rows(report_input, "qt_dsm_kpi_summary"), include_evidence_limit),
            "qt_dsm_sentiment_distribution_overall": _view_rows_preview(_rows(report_input, "qt_dsm_sentiment_distribution_overall"), include_evidence_limit),
            "qt_dsm_sentiment_by_channel_table": _view_rows_preview(channels, include_evidence_limit),
            "qt_dsm_top_topics_ranked": _view_rows_preview(top_topics, include_evidence_limit),
            "qt_dsm_top_authors_ranked": _view_rows_preview(authors, include_evidence_limit),
        },
        "qualitative_preview": {
            "ql_dsm_topic_sentiment": _view_rows_preview(topic_evidence, include_evidence_limit),
            "ql_dsm_top_content_positive_negative": _view_rows_preview(content, include_evidence_limit),
            "ql_dsm_top_engagement_account_profile": _view_rows_preview(account_profiles, include_evidence_limit),
            "ql_dsm_topic_channels": _view_rows_preview(_rows(report_input, "ql_dsm_topic_channels"), include_evidence_limit),
        },
        "evidence_url_audit": appendix,
        "markdown": markdown,
        "claude_instructions": [
            "Show this preview to the user before creating PPTX when user asks to review Task 1 data.",
            "Do not hide evidence URLs. Display source_url or top_post_url for content examples when available.",
            "Explain whether topic coverage is complete, partial, or low before recommending PPT generation.",
        ],
    }


def _all_view_statuses(report_input: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        _view_status(report_input, view_id)
        for view_id in (
            "qt_dsm_kpi_summary",
            "qt_dsm_sentiment_distribution_overall",
            "qt_dsm_sentiment_by_channel_table",
            "qt_dsm_top_topics_ranked",
            "qt_dsm_top_authors_ranked",
            "ql_dsm_topic_sentiment",
            "ql_dsm_top_content_positive_negative",
            "ql_dsm_top_engagement_account_profile",
            "ql_dsm_topic_channels",
        )
    ]


def build_daily_social_report_package(
    report_input_id: str,
    *,
    allow_partial: bool = True,
    audience_context: str | None = None,
    audience_pov: str | None = None,
) -> dict[str, Any]:
    """Build a Daily Social PPT-ready package from a stored report_input_id."""
    if not isinstance(report_input_id, str) or not report_input_id.strip():
        raise DailySocialRendererError("report_input_id wajib diisi.")
    report_input_id = report_input_id.strip()

    report_input = get_report_input(report_input_id)
    if report_input is None:
        raise DailySocialRendererError(f"report_input_id '{report_input_id}' tidak ditemukan.")
    if report_input.get("report_type_id") != REPORT_TYPE_ID:
        raise DailySocialRendererError(
            f"Renderer ini hanya untuk {REPORT_TYPE_ID}, bukan {report_input.get('report_type_id')}."
        )

    validation = _as_mapping(report_input.get("validation"))
    if validation.get("status") == "FAIL":
        raise DailySocialRendererError("report_input validation FAIL; tidak aman untuk dirender.")
    if validation.get("status") == "PARTIAL_PASS" and not allow_partial:
        raise DailySocialRendererError("report_input PARTIAL_PASS; set allow_partial=True untuk render dengan limitation.")

    outline = build_report_outline_from_id(report_input_id, allow_partial=allow_partial)
    slides, meta = _build_slides(report_input, outline)
    data_preview = build_daily_social_report_data_preview(report_input_id, include_evidence_limit=10)

    package = {
        "success": True,
        "render_package_version": RENDER_PACKAGE_VERSION,
        "render_package_id": _now_id("dsm_render_package"),
        "report_input_id": report_input_id,
        "report_type_id": REPORT_TYPE_ID,
        "outline_id": outline.get("outline_id"),
        "outline_status": outline.get("outline_status"),
        "meta": meta,
        "report_structure_source": {
            "document": "Dokumen Standar Struktur Report Baru Action Plan First Framework",
            "daily_social_core_order": CORE_DAILY_STRUCTURE,
            "optional_slides_policy": (
                "Core Daily Social structure is 9 slides. Renderer may add Critical Issue Deep Dive and Evidence Appendix "
                "when risk/evidence warrants it."
            ),
            "action_taxonomy": list(ACTION_TYPES),
        },
        "ppt_style_brief": {
            "format": "client-facing PPTX",
            "tone": "executive, direct, action-first, evidence-backed",
            "slide_count": len(slides),
            "visual_style": "card-based executive report; large KPI cards; compact tables; evidence cards with visible source URL",
            "must_follow": [
                "Action Plan must be slide 3, immediately after Executive Summary.",
                "Do not invent topics, quotes, source URLs, or metrics.",
                "Every content/example/action evidence must display source_url/top_post_url when available.",
                "Use N/A or limitation copy when a required view is NOT_AVAILABLE.",
                "If topic coverage is low, label topic insight as early classified signal, not final ranking.",
                "Interactions and views must remain separate.",
                "Raw Topic Extraction is not a report topic source.",
            ],
        },
        "slides": slides,
        "view_statuses": _all_view_statuses(report_input),
        "limitations": report_input.get("limitations") or [],
        "pre_ppt_data_preview": {
            "preview_id": data_preview["preview_id"],
            "readiness": data_preview["readiness"],
            "markdown": data_preview["markdown"],
            "evidence_url_audit": data_preview["evidence_url_audit"],
        },
        "claude_instructions": [
            "Create a PPTX from the slides array. Keep the slide order exactly as provided.",
            "Use the PPT style brief and Action Plan First structure.",
            "Render source_url/top_post_url as visible hyperlinks or short URLs in Top Content, Action Plan evidence, Deep Dive, and Appendix.",
            "For each action row, preserve priority, action type, recommended action, rationale, supporting evidence, expected impact, owner/next step, and evidence_urls.",
            "For content examples, use content_snippet/source_url only; do not create new quotes.",
            "When thematic topics are unavailable, render slide 4 as an explicit limitation/N/A slide rather than omitting it.",
            "When topic coverage is low, state the coverage caveat on the topic slide and footer.",
        ],
    }
    if audience_context or audience_pov:
        package = apply_audience_to_package(package, audience_context, audience_pov)
    return package


__all__ = [
    "build_daily_social_report_package",
    "build_daily_social_report_data_preview",
    "normalize_audience_context",
    "audience_clarification_payload",
    "apply_audience_to_package",
    "DailySocialRendererError",
]


# ---------------------------------------------------------------------------
# v4 polish overlay: executive evidence IDs + restrained URL display policy.
# URLs remain fully available in appendix/data pack, but main slides use Evidence
# IDs so the PPT does not look like a debug/audit export.
# ---------------------------------------------------------------------------

_BUILD_DSM_SLIDES_BEFORE_URL_POLISH = _build_slides
_BUILD_DSM_PACKAGE_BEFORE_URL_POLISH = build_daily_social_report_package
RENDER_PACKAGE_VERSION = "daily_social_report_render_package_v4"

URL_DISPLAY_POLICY = {
    "main_slides": "Use Evidence ID only (S01, S02, ...); do not print raw URLs.",
    "action_plan": "No raw URL. Show Evidence ID + source label only.",
    "deep_dive": "Max 3 evidence IDs; URL lives in appendix/data pack.",
    "top_content": "Show Evidence ID and source label; avoid raw URL unless user explicitly asks.",
    "appendix": "Full URL audit trail is allowed and expected.",
    "data_pack": "All URLs must remain available for audit.",
}

_URL_KEYS_TO_HIDE = {"source_url", "top_post_url", "url", "link_url", "post_url", "article_url", "evidence_urls"}


def _evidence_key_from_ref(ref: Mapping[str, Any]) -> str:
    return str(ref.get("source_url") or ref.get("top_post_url") or ref.get("url") or ref.get("canonical_post_id") or ref.get("snippet") or ref.get("content_snippet") or "").strip()


def _build_social_evidence_index(report_input: Mapping[str, Any], limit: int = 30) -> list[dict[str, Any]]:
    rows = _evidence_appendix(report_input, limit=limit)
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(rows, start=1):
        item = dict(row)
        item["evidence_id"] = f"S{idx:02d}"
        item["full_url"] = item.get("source_url")
        item["url_display_policy"] = "full_url_only_in_appendix_or_data_pack"
        out.append(item)
    return out


def _evidence_lookup(report_input: Mapping[str, Any]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for item in _build_social_evidence_index(report_input, limit=50):
        for key in (item.get("source_url"), item.get("source_label"), item.get("snippet")):
            if key:
                lookup[str(key).strip()] = item["evidence_id"]
    return lookup


def _find_evidence_id(ref: Mapping[str, Any], lookup: Mapping[str, str]) -> str | None:
    for key in (
        ref.get("source_url"), ref.get("top_post_url"), ref.get("url"),
        ref.get("source_label"), ref.get("snippet"), ref.get("content_snippet"),
    ):
        if key and str(key).strip() in lookup:
            return lookup[str(key).strip()]
    return None


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


def _compact_social_ref(ref: Mapping[str, Any], lookup: Mapping[str, str]) -> dict[str, Any]:
    item = _strip_visible_urls(dict(ref))
    evidence_id = _find_evidence_id(ref, lookup)
    if evidence_id:
        item["evidence_id"] = evidence_id
    item["source_label"] = _source_label(ref)
    item["url_display_policy"] = "no_raw_url_on_main_slide; see appendix/data pack"
    item["link_text"] = f"{evidence_id or 'Evidence'} — see appendix"
    return item


def _content_context(row: Mapping[str, Any]) -> str:
    blob = " ".join(_clean_text(row.get(k), 80) for k in ("topic_label", "content_snippet", "author", "channel")).casefold()
    if any(token in blob for token in ("jual", "penjualan", "mobil", "eks-armada", "heritage", "warisan", "wisata", "layanan")):
        return "business-as-usual / non-crisis positive"
    if any(token in blob for token in ("kecelakaan", "korban", "meninggal", "tanggung jawab", "klarifikasi", "respons")):
        return "crisis-relevant evidence"
    return "general evidence"


def _compact_content_cards(rows: list[dict[str, Any]], lookup: Mapping[str, str]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for row in rows:
        ref = _source_ref(row)
        card = _compact_social_ref(ref, lookup)
        card.update({
            "author": row.get("author"),
            "channel": row.get("channel"),
            "sentiment": row.get("sentiment"),
            "topic_label": row.get("topic_label"),
            "interactions": row.get("interactions"),
            "views": row.get("views"),
            "content_snippet": _clean_text(row.get("content_snippet") or row.get("snippet"), 260),
            "content_context": _content_context(row),
        })
        cards.append(card)
    return cards


def _polish_social_actions(actions: list[dict[str, Any]], lookup: Mapping[str, str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for action in actions:
        item = dict(action)
        refs = action.get("evidence_refs") or []
        compact_refs = [_compact_social_ref(ref, lookup) for ref in refs[:1] if isinstance(ref, Mapping)]
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


def _build_slides(report_input: Mapping[str, Any], outline: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:  # override v3
    slides, meta = _BUILD_DSM_SLIDES_BEFORE_URL_POLISH(report_input, outline)
    lookup = _evidence_lookup(report_input)
    evidence_index = _build_social_evidence_index(report_input, limit=30)

    for slide in slides:
        slide["url_display_policy"] = URL_DISPLAY_POLICY
        sid = slide.get("slide_id") or ""
        comps = slide.get("components") or []
        new_components: list[dict[str, Any]] = []
        for comp in comps:
            c = dict(comp)
            ctype = c.get("type")
            if ctype == "action_plan_table":
                c["type"] = "action_plan_cards"
                c["items"] = _polish_social_actions(c.get("items") or [], lookup)
                c["layout_hint"] = "Render as 3-5 compact action cards, not a dense table. Evidence uses ID only."
                c["must_show_url"] = False
            elif ctype == "action_plan_instruction":
                c["text"] = "Use Evidence ID only (S01/S02). Do not print raw URLs in Action Plan."
            elif ctype == "evidence_refs":
                c["items"] = [_compact_social_ref(ref, lookup) for ref in (c.get("items") or [])[:3] if isinstance(ref, Mapping)]
                c["must_show_url"] = False
            elif ctype in {"positive_content_cards", "negative_content_cards"}:
                c["items"] = _compact_content_cards(c.get("items") or [], lookup)
                c["must_show_url"] = False
                c["layout_hint"] = "Show Evidence ID + source label; no raw URL. Full URL lives in appendix."
            elif ctype == "finding_cards":
                c["items"] = _strip_visible_urls(c.get("items") or [])
                for item in c["items"]:
                    if isinstance(item, dict) and item.get("evidence_ref"):
                        item["evidence_ref"] = _compact_social_ref(item["evidence_ref"], lookup)
            elif ctype in {"author_rank_table", "top_account_cards"} and "top_performing_authors" in sid:
                c = _strip_visible_urls(c)
            new_components.append(c)
        slide["components"] = new_components
        if "action_plan" in sid:
            slide["subtitle"] = "Priority actions with owner/next step. Evidence shown as ID; full URLs stay in appendix."
            slide["speaker_notes"] = "Do not show raw URLs here. Use S01/S02 evidence IDs and keep the slide executive."
        if "critical_issue" in sid:
            slide["speaker_notes"] = "Use max 3 evidence IDs. Do not print raw URLs; full URL audit trail is in appendix."
        if "top_performing_content" in sid:
            slide["speaker_notes"] = "Label non-crisis positives as business-as-usual/non-crisis so amplification does not look tone-deaf."
        if "evidence_appendix" in sid:
            slide["title"] = "APPENDIX — EVIDENCE ID & FULL URL"
            slide["speaker_notes"] = "This is the only slide where full URLs are expected."

    meta["evidence_link_policy"] = URL_DISPLAY_POLICY
    meta["evidence_index_count"] = len(evidence_index)
    return slides, meta


def build_daily_social_report_package(
    report_input_id: str,
    *,
    allow_partial: bool = True,
    audience_context: str | None = None,
    audience_pov: str | None = None,
) -> dict[str, Any]:  # override v3
    package = _BUILD_DSM_PACKAGE_BEFORE_URL_POLISH(
        report_input_id,
        allow_partial=allow_partial,
        audience_context=audience_context,
        audience_pov=audience_pov,
    )
    report_input = get_report_input(report_input_id)
    evidence_index = _build_social_evidence_index(report_input or {}, limit=30)
    package["render_package_version"] = RENDER_PACKAGE_VERSION
    package["quality_upgrade"] = "v4_url_policy_and_executive_polish"
    package["evidence_link_policy"] = URL_DISPLAY_POLICY
    package["evidence_index"] = evidence_index
    package["ppt_style_brief"]["visual_style"] = "executive card-based deck; fewer tables; Evidence IDs on main slides; full URLs only in appendix/data pack"
    package["ppt_style_brief"]["must_follow"] = [
        rule for rule in package["ppt_style_brief"].get("must_follow", [])
        if "Every content/example/action evidence must display" not in rule
    ] + [
        "Use Evidence IDs on main slides; do not print raw URLs in Action Plan, Timeline, Key Findings, or main evidence cards.",
        "Full URLs belong only in Appendix/Evidence URL slide and data pack unless the user explicitly asks otherwise.",
        "For positive content unrelated to the crisis, label it as business-as-usual / non-crisis positive.",
    ]
    package["claude_instructions"] = [
        instr for instr in package.get("claude_instructions", [])
        if "Render source_url" not in instr and "evidence_urls" not in instr
    ] + [
        "Render Evidence IDs on main slides and keep raw/full URLs only in Appendix/Data Pack.",
        "Do not place raw URLs in Action Plan. Use S01/S02 evidence IDs instead.",
        "Use card layout for Action Plan when possible: Respond / Hold / Monitor / Amplify Carefully.",
    ]
    return package
