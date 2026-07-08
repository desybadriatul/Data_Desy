"""Daily Social Media Report Task 2 renderer.

This module converts a frozen Task 1 `report_input_v1` package plus the
registry outline into a PPT-ready report package for Claude/LLM rendering.

It intentionally does not fabricate quotes, topics, or examples. All examples
come from ql_* views created by Task 1. When a required view is unavailable, the
package keeps the relevant section but marks it as N/A or limited so Claude can
render it transparently.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from reporting.storage.report_input_store import get_report_input
from reporting.task2.report_outline_builder import build_report_outline_from_id


RENDER_PACKAGE_VERSION = "daily_social_report_render_package_v1"
REPORT_TYPE_ID = "daily_social_media_report"
SENTIMENT_ORDER = ("positive", "neutral", "negative")
ACTION_TYPES = (
    "Amplify Strength",
    "Respond to Risk",
    "Monitor Inquiry",
    "Prepare Response",
    "Content Opportunity",
)


class DailySocialRendererError(RuntimeError):
    """Raised when Daily Social Task 2 rendering cannot proceed safely."""


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
        }
    if neg >= 20 or net <= -5:
        return {
            "label": "AMBER / WATCH",
            "short_label": "WATCH",
            "rationale": "Ada tekanan negatif yang perlu dipantau dan diberi respons selektif.",
        }
    return {
        "label": "GREEN / STABLE",
        "short_label": "STABLE",
        "rationale": "Sentimen tidak menunjukkan tekanan negatif dominan pada scope ini.",
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


def _source_ref(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "author": row.get("author"),
        "channel": row.get("channel"),
        "url": row.get("source_url") or row.get("top_post_url"),
        "snippet": _clean_text(row.get("content_snippet") or row.get("top_post_content_snippet"), 280),
        "interactions": row.get("interactions") or row.get("total_interactions") or row.get("topic_interactions"),
        "views": row.get("views") or row.get("total_views"),
    }


def _build_executive_summary(report_input: Mapping[str, Any]) -> dict[str, Any]:
    kpi = _kpi(report_input)
    sent = _sentiment_distribution(report_input)
    posture = _posture(sent)
    channel = _top_channel(report_input, "interactions")
    account = (_account_profiles(report_input) or [{}])[0]
    top_topics = _top_topic_rows(report_input)
    top_topic = top_topics[0] if top_topics else None

    bullets = [
        (
            f"Percakapan mencatat {_fmt_int(kpi['total_mentions'])} post unik "
            f"dengan {_fmt_num(kpi['total_interactions'])} interactions pada periode ini."
        ),
        (
            f"Posture sentimen: {posture['short_label']} "
            f"(net {sent['net_sentiment_by_count']:+.1f}; negatif {_fmt_pct(sent['negative_share_pct'])})."
        ),
    ]
    if top_topic:
        bullets.append(
            f"Top topic: {_clean_text(top_topic.get('topic_label'), 80)} "
            f"({_fmt_num(top_topic.get('interactions'))} interactions; {_fmt_int(top_topic.get('post_count'))} post)."
        )
    else:
        bullets.append("Top topic belum tersedia karena taxonomy/classification topic belum lengkap.")

    if channel:
        bullets.append(
            f"Channel driver terbesar: {channel.get('channel')} "
            f"dengan {_fmt_num(channel.get('interactions'))} interactions dari {_fmt_int(channel.get('post_count'))} post."
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
            {"label": "Total Authors", "value": _fmt_int(kpi["total_authors"]), "note": "unique author"},
            {"label": "Net Sentiment", "value": f"{sent['net_sentiment_by_count']:+.1f}", "note": "positive % - negative %"},
        ],
        "bullets": bullets[:5],
        "top_topic": top_topic,
        "top_channel": channel,
        "top_account": account,
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
    return {
        "priority": priority,
        "action_type": action_type,
        "focus_area": focus_area,
        "recommended_action": recommended_action,
        "rationale": rationale,
        "supporting_evidence": supporting_evidence,
        "expected_impact": expected_impact,
        "owner_next_step": owner_next_step,
        "evidence_refs": evidence_refs or [],
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

    actions: list[dict[str, Any]] = []

    pos_focus = positive_topic[0] if positive_topic else (positive_content[0] if positive_content else {})
    if pos_focus:
        label = pos_focus.get("topic_label") or "konten positif dengan engagement tertinggi"
        actions.append(
            _make_action(
                priority="MEDIUM",
                action_type="Amplify Strength",
                focus_area=_clean_text(label, 90),
                recommended_action=(
                    "Perbesar narasi positif yang sudah terbukti mendapat respons, "
                    "terutama melalui kanal/author dengan engagement tertinggi."
                ),
                rationale="Ada sinyal positif yang sudah menghasilkan engagement dan bisa diperluas menjadi konten lanjutan.",
                supporting_evidence=(
                    f"{_clean_text(pos_focus.get('author'), 60)} / {_clean_text(pos_focus.get('channel'), 30)}; "
                    f"{_fmt_num(pos_focus.get('interactions') or pos_focus.get('topic_interactions'))} interactions."
                ),
                expected_impact="Memperkuat share percakapan positif dan menjaga momentum harian.",
                owner_next_step="Social/Content team: siapkan repost, derivative content, atau reply amplification hari berikutnya.",
                evidence_refs=[_source_ref(pos_focus)],
            )
        )
    else:
        actions.append(
            _make_action(
                priority="LOW",
                action_type="Amplify Strength",
                focus_area="N/A",
                recommended_action="N/A — belum ada evidence positif yang cukup pada qualitative view.",
                rationale="Action tidak dibuat tanpa contoh konten/evidence positif.",
                supporting_evidence="ql_dsm_topic_sentiment / ql_dsm_top_content_positive_negative belum menyediakan evidence positif.",
                expected_impact="Menghindari rekomendasi yang tidak berbasis data.",
                owner_next_step="Lengkapi topic/content evidence atau perluas scope periode.",
            )
        )

    neg_focus = negative_topic[0] if negative_topic else (negative_content[0] if negative_content else {})
    if neg_focus:
        neg_priority = "HIGH" if _num(sent.get("negative_share_pct")) >= 20 else "MEDIUM"
        label = neg_focus.get("topic_label") or "konten negatif dengan engagement tertinggi"
        actions.append(
            _make_action(
                priority=neg_priority,
                action_type="Respond to Risk",
                focus_area=_clean_text(label, 90),
                recommended_action=(
                    "Siapkan respons ringkas untuk isu negatif utama; prioritaskan klarifikasi di kanal yang menjadi sumber engagement terbesar."
                ),
                rationale="Isu negatif memiliki contoh konten yang dapat memicu eskalasi bila tidak dipantau atau dijawab selektif.",
                supporting_evidence=(
                    f"Negatif {_fmt_pct(sent.get('negative_share_pct'))}; evidence: "
                    f"{_clean_text(neg_focus.get('author'), 60)} / {_clean_text(neg_focus.get('channel'), 30)} "
                    f"({_fmt_num(neg_focus.get('interactions') or neg_focus.get('topic_interactions'))} interactions)."
                ),
                expected_impact="Mengurangi risiko penyebaran keluhan dan menjaga akurasi narasi publik.",
                owner_next_step="PR/Social care: draft holding response + decision rule kapan perlu reply publik.",
                evidence_refs=[_source_ref(neg_focus)],
            )
        )
    else:
        actions.append(
            _make_action(
                priority="LOW",
                action_type="Respond to Risk",
                focus_area="N/A",
                recommended_action="Pantau negatif harian; belum ada evidence negatif dominan yang cukup untuk respons publik.",
                rationale="Tidak ada top negative evidence yang cukup kuat pada qualitative view.",
                supporting_evidence=f"Negatif {_fmt_pct(sent.get('negative_share_pct'))}; qualitative negative evidence N/A.",
                expected_impact="Menjaga respons tetap proporsional.",
                owner_next_step="Social care: monitor mention negatif baru dan eskalasi bila volume/engagement naik.",
            )
        )

    if neutral_topic:
        neu = neutral_topic[0]
        actions.append(
            _make_action(
                priority="MEDIUM",
                action_type="Monitor Inquiry",
                focus_area=_clean_text(neu.get("topic_label"), 90),
                recommended_action="Pantau pertanyaan/topik netral yang berulang dan siapkan jawaban informatif bila frekuensi naik.",
                rationale="Topik netral sering menjadi indikasi kebutuhan informasi sebelum berubah menjadi keluhan atau peluang edukasi.",
                supporting_evidence=(
                    f"{_fmt_num(neu.get('topic_interactions'))} interactions pada topic netral; "
                    f"contoh dari {_clean_text(neu.get('author'), 60)}."
                ),
                expected_impact="Mengurangi potensi kebingungan publik dan membuka ruang edukasi brand.",
                owner_next_step="Social/Comms: kumpulkan FAQ singkat untuk topic ini.",
                evidence_refs=[_source_ref(neu)],
            )
        )
    else:
        actions.append(
            _make_action(
                priority="LOW",
                action_type="Monitor Inquiry",
                focus_area="Neutral conversation",
                recommended_action="Monitor channel dengan volume/interactions terbesar untuk mendeteksi pertanyaan berulang.",
                rationale="Neutral topic evidence belum tersedia, tetapi channel driver tetap bisa dipakai untuk monitoring harian.",
                supporting_evidence=(
                    f"Top channel: {_clean_text(channel.get('channel'), 40)}; "
                    f"{_fmt_num(channel.get('interactions'))} interactions."
                    if channel
                    else "Channel evidence N/A."
                ),
                expected_impact="Menjaga tim tetap responsif tanpa membuat asumsi topic.",
                owner_next_step="Monitoring team: cek mention di top channel pada batch berikutnya.",
            )
        )

    actions.append(
        _make_action(
            priority="MEDIUM" if neg_focus else "LOW",
            action_type="Prepare Response",
            focus_area=_clean_text((neg_focus or {}).get("topic_label") or "risk watch", 90),
            recommended_action="Siapkan template respons 2 versi: public reply pendek dan internal escalation note.",
            rationale="Daily report perlu membuat tim siap sebelum isu membesar, bukan hanya membaca dashboard.",
            supporting_evidence=(
                _clean_text((neg_focus or {}).get("content_snippet"), 160)
                if neg_focus
                else "Belum ada negative evidence dominan; response template tetap disiapkan sebagai guardrail."
            ),
            expected_impact="Mempercepat respons bila isu yang sama naik lagi pada monitoring berikutnya.",
            owner_next_step="PR + Social care: review template sebelum shift monitoring berikutnya.",
            evidence_refs=[_source_ref(neg_focus)] if neg_focus else [],
        )
    )

    actions.append(
        _make_action(
            priority="MEDIUM",
            action_type="Content Opportunity",
            focus_area=_clean_text(channel.get("channel") or account.get("channel") or "top channel/account", 90),
            recommended_action="Buat konten/response follow-up yang meniru format/konteks dari top performing account/content hari ini.",
            rationale="Top account/channel menunjukkan lokasi perhatian audiens yang paling efisien untuk dimanfaatkan esok hari.",
            supporting_evidence=(
                f"{_clean_text(account.get('author'), 60)}; {_fmt_num(account.get('total_interactions'))} interactions."
                if account
                else "Top account evidence N/A."
            ),
            expected_impact="Meningkatkan efisiensi engagement dan menjaga brand tetap hadir di percakapan yang sudah aktif.",
            owner_next_step="Content team: draft 1-2 content angle untuk channel/account driver.",
            evidence_refs=[_source_ref(account)] if account else [],
        )
    )

    # Keep one row per action taxonomy in the canonical order.
    ordered: list[dict[str, Any]] = []
    for action_type in ACTION_TYPES:
        match = next((item for item in actions if item["action_type"] == action_type), None)
        if match:
            ordered.append(match)
    return ordered


def _build_thematic_topics(report_input: Mapping[str, Any]) -> dict[str, Any]:
    status = _view_status(report_input, "qt_dsm_top_topics_ranked")
    if status["status"] != "READY" or status["row_count"] == 0:
        return {
            "available": False,
            "reason": status.get("reason") or "Topic taxonomy/classification belum tersedia.",
            "positive": [],
            "neutral": [],
            "negative": [],
            "narrative": "Thematic Topics belum dapat dirender karena report-topic LLM belum tersedia untuk scope ini.",
        }

    topics = _top_topic_rows(report_input)
    evidence = _topic_evidence(report_input)
    out: dict[str, Any] = {"available": True, "positive": [], "neutral": [], "negative": []}
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
            }
            for row in rows[:3]
        ]
    top = topics[0] if topics else {}
    out["narrative"] = (
        f"Percakapan tematik paling kuat mengarah ke {_clean_text(top.get('topic_label'), 90)} "
        f"dengan {_fmt_num(top.get('interactions'))} interactions dan {_fmt_int(top.get('post_count'))} post."
        if top
        else "Topic ranking tersedia tetapi belum memiliki top topic yang cukup kuat."
    )
    return out


def _build_sentiment_section(report_input: Mapping[str, Any]) -> dict[str, Any]:
    sent = _sentiment_distribution(report_input)
    channels = _rows(report_input, "qt_dsm_sentiment_by_channel_table")
    top_negative = sorted(channels, key=lambda row: (_num(row.get("negative_posts")), _num(row.get("negative_share_pct"))), reverse=True)[:1]
    top_positive = sorted(channels, key=lambda row: (_num(row.get("positive_posts")), _num(row.get("positive_share_pct"))), reverse=True)[:1]
    readout = []
    if top_positive:
        row = top_positive[0]
        readout.append(f"Channel paling positif: {row.get('channel')} ({_fmt_pct(row.get('positive_share_pct'))} positif).")
    if top_negative:
        row = top_negative[0]
        readout.append(f"Channel risiko tertinggi: {row.get('channel')} ({_fmt_pct(row.get('negative_share_pct'))} negatif).")
    return {
        "distribution": sent,
        "channel_table": channels,
        "readout": " ".join(readout) if readout else "Readout channel sentiment N/A.",
    }


def _build_key_findings(report_input: Mapping[str, Any], executive: Mapping[str, Any], actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sent = _sentiment_distribution(report_input)
    top_positive = _content_evidence(report_input, "positive")[:1]
    top_negative = _content_evidence(report_input, "negative")[:1]
    channel = _top_channel(report_input, "interactions") or {}
    findings = [
        {
            "type": "Strengths",
            "finding": (
                f"Percakapan memiliki ruang positif yang dapat diamplifikasi; positif {_fmt_pct(sent.get('positive_share_pct'))}."
            ),
            "evidence": _clean_text((top_positive[0].get("content_snippet") if top_positive else "Positive evidence N/A."), 180),
        },
        {
            "type": "Weaknesses",
            "finding": (
                f"Risiko utama berada pada sentimen negatif {_fmt_pct(sent.get('negative_share_pct'))} dan perlu response rule yang jelas."
            ),
            "evidence": _clean_text((top_negative[0].get("content_snippet") if top_negative else "Negative evidence N/A."), 180),
        },
        {
            "type": "Opportunities",
            "finding": (
                f"Kanal {_clean_text(channel.get('channel'), 40) or 'N/A'} menjadi titik distribusi penting untuk monitoring/action harian."
            ),
            "evidence": (
                f"{_fmt_num(channel.get('interactions'))} interactions; {_fmt_int(channel.get('post_count'))} post."
                if channel
                else "Channel evidence N/A."
            ),
        },
    ]
    return findings


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
    content = _content_evidence(report_input)
    findings = _build_key_findings(report_input, executive, actions)

    meta = {
        "project_name": project,
        "period": period,
        "posture": executive["posture"],
        "kpi": kpi,
        "validation": report_input.get("validation"),
        "outline_status": outline.get("outline_status"),
    }

    slides = [
        _slide(
            "dsm_01_header",
            "DAILY SOCIAL MEDIA REPORT",
            f"{project} · {period.get('start_date')} to {period.get('end_date')} · Social Media Monitoring",
            [
                {"type": "hero_statement", "text": executive["bullets"][0] if executive["bullets"] else "Daily social snapshot."},
                {"type": "kpi_cards", "items": executive["kpi_cards"]},
                {"type": "posture_badge", "item": executive["posture"]},
            ],
            "Opening slide. Keep it executive and action-oriented.",
        ),
        _slide(
            "dsm_02_executive_summary",
            "EXECUTIVE SUMMARY",
            "Snapshot harian: what happened, why it matters, and where attention is concentrated.",
            [
                {"type": "bullet_summary", "items": executive["bullets"]},
                {"type": "top_topic_card", "item": executive.get("top_topic")},
                {"type": "top_engagement_account", "item": executive.get("top_account")},
            ],
            "This must appear before Action Plan and must not include unsupported recommendations.",
        ),
        _slide(
            "dsm_03_daily_action_plan",
            "DAILY ACTION PLAN",
            "Lima tindakan cepat: Amplify, Respond, Monitor, Prepare, dan Content Opportunity.",
            [
                {"type": "action_plan_table", "items": actions},
            ],
            "Action Plan is mandatory immediately after Executive Summary. Every row must keep its evidence.",
        ),
        _slide(
            "dsm_04_thematic_topics",
            "THEMATIC TOPICS",
            "Top positive, neutral, and negative topics as the primary evidence layer.",
            [
                {"type": "topic_cards_by_sentiment", "item": thematic},
            ],
            "If thematic.available=false, render this as an honest N/A slide with limitation text.",
        ),
        _slide(
            "dsm_05_sentiment_analysis",
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
            "dsm_06_top_performing_authors",
            "TOP PERFORMING AUTHORS",
            "Author ranking by volume, interactions, and representative content.",
            [
                {"type": "author_rank_table", "items": authors[:10]},
                {"type": "top_account_cards", "items": profiles[:3]},
            ],
            "Use ranked table; avoid generic influencer commentary without evidence.",
        ),
        _slide(
            "dsm_07_top_performing_content",
            "TOP PERFORMING CONTENT",
            "Evidence cards for highest positive and negative content.",
            [
                {"type": "positive_content_cards", "items": _content_evidence(report_input, "positive")[:5]},
                {"type": "negative_content_cards", "items": _content_evidence(report_input, "negative")[:5]},
            ],
            "Quotes/snippets must be copied only from content_snippet; do not rewrite as direct quote.",
        ),
        _slide(
            "dsm_08_key_findings",
            "KEY FINDINGS",
            "Strengths, weaknesses, and opportunities after the Action Plan.",
            [
                {"type": "finding_cards", "items": findings},
            ],
            "Findings support the Action Plan; do not introduce unsupported new claims.",
        ),
        _slide(
            "dsm_09_footer_disclaimer",
            "SOURCES & NOTES",
            "Data source, metric contract, limitations, and AI-assisted insight note.",
            [
                {"type": "scope", "item": {"project_name": project, "period": period, "channels": ctx.get("channels")}},
                {"type": "metric_contract", "item": _as_mapping(report_input.get("metric_readiness")).get("metric_contract")},
                {"type": "limitations", "items": report_input.get("limitations") or []},
                {"type": "note", "text": "Data internal: Cogan canonical social posts. Interactions exclude views. Topic Extraction raw tidak dipakai sebagai report topic."},
            ],
            "Use this as final source/limitation slide.",
        ),
    ]
    return slides, meta


def build_daily_social_report_package(
    report_input_id: str,
    *,
    allow_partial: bool = True,
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

    view_statuses = [
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

    return {
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
            "daily_social_order": [
                "Header / Identitas Report",
                "Executive Summary",
                "Daily Action Plan",
                "Thematic Topics",
                "Sentiment Analysis",
                "Top Performing Authors",
                "Top Performing Content",
                "Key Findings",
                "Footer / Disclaimer",
            ],
            "action_taxonomy": list(ACTION_TYPES),
        },
        "ppt_style_brief": {
            "format": "client-facing PPTX",
            "tone": "executive, direct, action-first, evidence-backed",
            "slide_count": len(slides),
            "visual_style": "card-based executive report; large KPI cards; compact tables; evidence cards with source URL",
            "must_follow": [
                "Action Plan must be slide 3, immediately after Executive Summary.",
                "Do not invent topics, quotes, source URLs, or metrics.",
                "Use N/A or limitation copy when a required view is NOT_AVAILABLE.",
                "Interactions and views must remain separate.",
                "Raw Topic Extraction is not a report topic source.",
            ],
        },
        "slides": slides,
        "view_statuses": view_statuses,
        "limitations": report_input.get("limitations") or [],
        "claude_instructions": [
            "Create a PPTX from the slides array. Keep the slide order exactly as provided.",
            "Use the PPT style brief and Action Plan First structure.",
            "For each action row, preserve priority, action type, rationale, supporting evidence, expected impact, and owner/next step.",
            "For content examples, use content_snippet/source_url only; do not create new quotes.",
            "When thematic topics are unavailable, render slide 4 as an explicit limitation/N/A slide rather than omitting it.",
        ],
    }


__all__ = ["build_daily_social_report_package", "DailySocialRendererError"]
