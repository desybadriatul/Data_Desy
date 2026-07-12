"""Competitive Analysis Task 2 renderer and data preview.

Converts a frozen Task 1 `competitive_analysis` report_input package into a
PPT-ready package for Claude rendering.

Evidence URL policy v2:
- Main slides should show human labels such as "Buka post" / "Lihat post".
- Those labels must be clickable hyperlinks to the source_url when available.
- Raw URLs and Evidence IDs are audit metadata, not the primary user-facing UI.
- Full URL tables remain available in Appendix / evidence_url_index / data pack.
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


UNCLEAR_AUDIENCE_INPUTS = {
    "gak tau",
    "ga tau",
    "nggak tau",
    "tidak tahu",
    "kurang tahu",
    "terserah",
    "bebas",
    "umum",
    "general",
    "semua",
    "semua aja",
    "all",
    "default",
}
DEFAULT_AUDIENCE_WHEN_UNCLEAR = "Marketing / Brand Team"


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
    default_used = False
    default_reason = None
    if not raw:
        label = "General Business User"
    else:
        key = raw.casefold()
        if key in UNCLEAR_AUDIENCE_INPUTS or any(phrase in key for phrase in ("gak tau", "ga tau", "nggak tau", "tidak tahu", "terserah", "bebas", "umum", "semua aja")):
            label = DEFAULT_AUDIENCE_WHEN_UNCLEAR
            default_used = True
            default_reason = "User gave unclear/general audience; defaulted to Brand/Marketing because Competitive Analysis usually drives brand, channel, and content decisions."
        else:
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
        "default_used": default_used,
        "default_reason": default_reason,
        **guidance,
    }


def audience_clarification_payload(project_name: str | None = None, period_label: str | None = None) -> dict[str, Any]:
    target = f" untuk {project_name}" if project_name else ""
    period = f" periode {period_label}" if period_label else ""
    return {
        "success": False,
        "workflow_status": "NEEDS_AUDIENCE",
        "needs_clarification": True,
        "clarification_question": (
            f"Competitive Analysis{target}{period} ini dibuat untuk siapa? "
            "Pilih salah satu: Management, CEO/Board, Marketing/Brand, Marketing/Content, PR/Corcom, atau Insight Team. "
            "Kalau belum tahu, jawab 'gak tau' dan saya pakai default Marketing/Brand Team."
        ),
        "why_needed": "Audience menentukan angle benchmark, action plan, dan depth narasi kompetitif. Jika user tidak tahu, workflow memakai default aman: Marketing/Brand Team.",
        "suggested_audiences": [
            "Management",
            "CEO / Board",
            "Marketing / Brand Team",
            "Marketing / Content Team",
            "PR / Corporate Communications",
            "Insight / Analyst Team",
        ],
        "example_user_reply": "Untuk Marketing/Brand Team. / Gak tau.",
        "default_if_unclear": DEFAULT_AUDIENCE_WHEN_UNCLEAR,
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


def _leader(rows: Any, field: str) -> Mapping[str, Any] | None:
    """Return the row with the highest numeric field value.

    Some report builders keep KPI rows as ``{brand: row}`` maps after
    normalization.  Iterating a dict directly yields brand-name strings, which
    previously caused ``'str' object has no attribute 'get'`` during CA Task 2
    package rendering.  Accept both list-like row collections and mapping
    values, and ignore any malformed non-dict entries defensively.
    """
    if isinstance(rows, Mapping):
        candidates = rows.values()
    else:
        candidates = rows or []
    valid_rows = [row for row in candidates if isinstance(row, Mapping)]
    if not valid_rows:
        return None
    return max(valid_rows, key=lambda row: _num(row.get(field)))


def _brand_row_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for row in rows:
        brand = _clean(row.get("brand") or row.get("campaign"))
        if brand:
            result[brand] = row
    return result


def _row_evidence_key(row: Mapping[str, Any]) -> str:
    url = _clean(row.get("source_url") or row.get("url") or row.get("link_url"))
    if url:
        return "url:" + url
    content = _clean(row.get("content") or row.get("title"), 180)
    if content:
        return "content:" + content.casefold()
    return ""


def _evidence_index(report_input: Mapping[str, Any], limit: int = 30) -> list[dict[str, Any]]:
    """Return one canonical E## evidence registry for the whole CA package.

    Task 1 rows may carry view-specific IDs such as P01/T09/E06. The renderer
    normalizes them into one E## namespace so main slides, evidence index, and
    appendix cannot drift from each other.
    """
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
            content = _clean(row.get("content") or row.get("title"), 180)
            key = _row_evidence_key(row)
            if not key or key in seen:
                continue
            seen.add(key)
            evidence_id = f"E{len(result)+1:02d}"
            original_evidence_id = _clean(row.get("evidence_id")) or None
            evidence_link = {
                "label": "Buka post",
                "url": url,
                "evidence_id": evidence_id,
                "audit_label": evidence_id,
            } if url else None
            result.append({
                "evidence_id": evidence_id,
                "original_evidence_id": original_evidence_id,
                "brand": _clean(row.get("brand") or row.get("campaign")),
                "source": _clean(row.get("author") or row.get("channel")),
                "channel": _clean(row.get("channel")),
                "sentiment": _clean(row.get("sentiment")),
                "metric": _num(row.get("engagement") or row.get("interactions")),
                "content": content,
                "url": url,
                "source_url": url,
                "view_id": view_id,
                "link_label": "Buka post" if url else "Link tidak tersedia",
                "evidence_link": evidence_link,
                "main_slide_display": "Buka post" if url else "Link tidak tersedia",
                "_evidence_key": key,
            })
            if len(result) >= limit:
                return result
    return result


def _evidence_lookup(evidence: list[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    lookup: dict[str, Mapping[str, Any]] = {}
    for item in evidence:
        key = _row_evidence_key(item)
        if key:
            lookup[key] = item
        original_id = _clean(item.get("original_evidence_id"))
        if original_id:
            lookup["id:" + original_id] = item
        evidence_id = _clean(item.get("evidence_id"))
        if evidence_id:
            lookup["id:" + evidence_id] = item
    return lookup


def _attach_clickable_evidence(row: Mapping[str, Any], lookup: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    item = dict(row)
    evidence = lookup.get(_row_evidence_key(row))
    if not evidence:
        original_id = _clean(row.get("evidence_id"))
        if original_id:
            evidence = lookup.get("id:" + original_id)
    if evidence:
        item["evidence_id"] = evidence.get("evidence_id")
        item["original_evidence_id"] = evidence.get("original_evidence_id")
        item["source_url"] = evidence.get("source_url") or evidence.get("url")
        item["evidence_link"] = evidence.get("evidence_link")
        item["link_label"] = evidence.get("link_label")
        item["main_slide_display"] = evidence.get("main_slide_display")
    else:
        item.setdefault("link_label", "Link tidak tersedia")
        item.setdefault("main_slide_display", "Link tidak tersedia")
    return item


def _evidence_registry(evidence: list[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    registry: dict[str, dict[str, Any]] = {}
    for item in evidence:
        evidence_id = _clean(item.get("evidence_id"))
        if evidence_id:
            clean_item = {k: v for k, v in dict(item).items() if not str(k).startswith("_")}
            registry[evidence_id] = clean_item
    return registry


def _find_dicts_with_key(value: Any, key: str) -> list[Mapping[str, Any]]:
    found: list[Mapping[str, Any]] = []
    if isinstance(value, Mapping):
        if key in value:
            found.append(value)
        for child in value.values():
            found.extend(_find_dicts_with_key(child, key))
    elif isinstance(value, list):
        for child in value:
            found.extend(_find_dicts_with_key(child, key))
    return found


def validate_competitive_analysis_render_package(package: Mapping[str, Any]) -> dict[str, Any]:
    """Pre-PPT QA for evidence link integrity.

    This validates the render package before Claude turns it into PPTX. It does
    not inspect the final PowerPoint binary, but it blocks the most common root
    cause: slide-level evidence objects that are not backed by registry URLs.
    """
    registry = dict(package.get("evidence_registry") or {})
    slides = package.get("slides") or []
    errors: list[str] = []
    warnings: list[str] = []
    referenced: set[str] = set()

    for slide in slides:
        slide_no = slide.get("slide_no") if isinstance(slide, Mapping) else "?"
        for item in _find_dicts_with_key(slide, "evidence_id"):
            evidence_id = _clean(item.get("evidence_id"))
            if not evidence_id:
                continue

            # _find_dicts_with_key walks recursively. If it lands on the
            # evidence_link object itself, that object is already the clickable
            # link, so do not require another nested evidence_link inside it.
            is_evidence_link_object = bool(_clean(item.get("url"))) and (
                "evidence_link" not in item
            ) and (
                "label" in item or "text" in item
            )

            if evidence_id.startswith("P") or evidence_id.startswith("T"):
                errors.append(f"Slide {slide_no}: evidence_id {evidence_id} uses non-canonical P/T prefix. Use E## only.")
            if evidence_id not in registry:
                errors.append(f"Slide {slide_no}: evidence_id {evidence_id} is not present in evidence_registry.")
                continue
            referenced.add(evidence_id)
            reg = registry[evidence_id]
            url = _clean(reg.get("source_url") or reg.get("url"))
            if not url:
                warnings.append(f"Slide {slide_no}: evidence_id {evidence_id} has no source_url; render as Link tidak tersedia.")

            if is_evidence_link_object:
                if url and _clean(item.get("url")) != url:
                    errors.append(f"Slide {slide_no}: evidence_id {evidence_id} evidence_link.url does not match evidence_registry source_url.")
                continue

            link = item.get("evidence_link")
            if url and not (isinstance(link, Mapping) and _clean(link.get("url")) == url):
                errors.append(f"Slide {slide_no}: evidence_id {evidence_id} is missing clickable evidence_link.url.")

    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "referenced_evidence_ids": sorted(referenced),
        "registry_count": len(registry),
    }


def _topic_coverage_context(report_input: Mapping[str, Any]) -> dict[str, Any]:
    scope = dict(report_input.get("scope") or {})
    policy = dict(scope.get("competitive_analysis_policy") or {})
    topic_enrichment = dict(policy.get("topic_enrichment") or {})
    if not topic_enrichment:
        topic_enrichment = dict(scope.get("competitive_topic_enrichment_target") or scope.get("competitive_topic_enrichment") or {})
    coverage = topic_enrichment.get("coverage_pct")
    if coverage is None:
        eligible = _num(topic_enrichment.get("eligible_rows") or topic_enrichment.get("eligible_content_count"))
        processed = _num(topic_enrichment.get("processed_rows") or topic_enrichment.get("processed_count"))
        coverage = round(processed * 100 / eligible, 1) if eligible else None
    label = None
    severity = "OK"
    if coverage is not None and float(coverage) < 20:
        severity = "LOW_SAMPLE"
        label = "Topic/narrative insight berbasis classified sample, bukan sensus penuh."
    if coverage is not None and float(coverage) < 10:
        severity = "VERY_LOW_SAMPLE"
        label = "Topic/narrative insight berbasis classified sample sangat terbatas; gunakan sebagai sinyal awal, bukan kesimpulan final."
    return {
        "coverage_pct": coverage,
        "severity": severity,
        "caveat_label": label,
        "raw": topic_enrichment,
    }


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
    ev_button = ev.get("evidence_link")
    actions = [
        {
            "priority": "HIGH",
            "action_type": "DEFEND POSITION" if client and sov_leader and sov_leader.get("brand") == client else "CLOSE VISIBILITY GAP",
            "focus_area": "Share of Voice / Share of Engagement",
            "recommended_action": "Prioritaskan pesan dan channel yang menaikkan visibility brand pada area kompetitor unggul; jangan membaca SOV tinggi sebagai kemenangan bila SOE rendah.",
            "rationale": f"Leader SOV: {_clean((sov_leader or {}).get('brand')) or 'N/A'} ({_fmt_pct((sov_leader or {}).get('sov_pct'))}); leader SOE: {_clean((soe_leader or {}).get('brand')) or 'N/A'} ({_fmt_pct((soe_leader or {}).get('soe_pct'))}).",
            "evidence_ref": ev_ref,
            "evidence_link": ev_button,
            "main_slide_display": "Buka post" if ev_button else ev_ref,
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
            "evidence_link": ev_button,
            "main_slide_display": "Buka post" if ev_button else ev_ref,
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
            "evidence_link": ev_button,
            "main_slide_display": "Buka post" if ev_button else ev_ref,
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
        "**Evidence policy:** main slide pakai tombol clickable 'Buka post'; Evidence ID + URL lengkap tetap ada di Appendix/Data Pack.",
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
    evidence = _evidence_index(report_input, limit=80)
    evidence_lookup_map = _evidence_lookup(evidence)
    evidence_registry = _evidence_registry(evidence)
    topics = [_attach_clickable_evidence(row, evidence_lookup_map) for row in topics]
    top_posts = [_attach_clickable_evidence(row, evidence_lookup_map) for row in top_posts]
    highlights = [_attach_clickable_evidence(row, evidence_lookup_map) for row in highlights]
    top_authors = [_attach_clickable_evidence(row, evidence_lookup_map) for row in top_authors]
    topic_coverage = _topic_coverage_context(report_input)
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
            "evidence_policy": "Main deck memakai tombol clickable 'Buka post'; Evidence ID + URL lengkap ada di Appendix/Data Pack.",
        },
        {
            "slide_no": 3,
            "title": "COMPETITIVE ACTION PLAN",
            "subtitle": "Priority · focus · action · evidence ID",
            "layout": "action_cards_clickable_evidence",
            "cards": action_plan,
            "url_policy": "No raw URLs on action plan. Render evidence_link as clickable text 'Buka post'; keep evidence_ref only for audit.",
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
            "topic_coverage_caveat": topic_coverage.get("caveat_label"),
            "topic_coverage": topic_coverage,
        },
        {
            "slide_no": 6,
            "title": "CHANNEL STRATEGY COMPARISON",
            "subtitle": "Channel mix by brand and engagement contribution",
            "layout": "channel_mix_cards",
            "table": channel_rows,
            "interpretation": "Gunakan channel dengan gap SOE terbesar sebagai prioritas optimasi, bukan semua channel sekaligus. Online Media engagement tidak selalu comparable dengan social interactions.",
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
            "top_posts": [{k: row.get(k) for k in ("evidence_id", "brand", "author", "channel", "sentiment", "engagement", "content", "source_url", "evidence_link", "link_label", "main_slide_display")} for row in top_posts[:10]],
            "top_authors": [{k: row.get(k) for k in ("evidence_id", "brand", "author", "channel", "sentiment", "engagement", "content", "source_url", "evidence_link", "link_label", "main_slide_display")} for row in top_authors[:10]],
            "rule": "Use as benchmark inspiration; do not copy competitor creative/message without brand/legal review.",
        },
        {
            "slide_no": 9,
            "title": "SUPPORTING EVIDENCE INDEX",
            "subtitle": "Evidence ID untuk audit — main slides tidak menampilkan URL mentah",
            "layout": "evidence_id_index",
            "table": [{k: row.get(k) for k in ("evidence_id", "brand", "source", "channel", "sentiment", "metric", "content", "evidence_link", "link_label", "main_slide_display")} for row in evidence[:15]],
            "note": "Full URL berada di Appendix dan export_report_data_pack.",
        },
        {
            "slide_no": 10,
            "title": "APPENDIX — EVIDENCE URL INDEX",
            "subtitle": "Full URL hanya di appendix/data pack",
            "layout": "appendix_url_table",
            "table": [{k: v for k, v in row.items() if not str(k).startswith("_")} for row in evidence[:30]],
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
            "topic_enrichment": topic_coverage,
            "limitations": limitations,
            "audit_tool": "Gunakan export_report_data_pack(report_input_id) untuk membuktikan angka/evidence tidak halu.",
        },
    ]

    outline = build_report_outline_from_id(report_input_id, allow_partial=allow_partial)
    package = {
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
            "main_slides": "Use clickable labels such as 'Buka post' linked to source_url. Do not display raw URLs or make Evidence ID the primary UI.",
            "appendix": "Full URLs allowed with canonical Evidence IDs.",
            "data_pack": "Full URLs required.",
        },
        "ppt_style_brief": {
            "tone": audience.get("tone"),
            "visual_direction": "executive consulting deck, card-based, benchmark matrix, LLM topic/narrative map, clickable evidence buttons",
            "avoid": ["raw URL spam on main slides", "Evidence ID as primary user-facing UI", "long tables without interpretation", "invented benchmarks", "using raw Topic Extraction/aspect/entity as final report source"],
            "preferred_components": ["decision cards", "SOV/SOE bars", "brand comparison matrix", "clickable 'Buka post' evidence buttons", "appendix URL table"],
        },
        "evidence_registry": evidence_registry,
        "evidence_link_policy": {
            "main_slide_label": "Buka post",
            "main_slide_rule": "Render 'Buka post' or 'Lihat post' as a clickable hyperlink to source_url. Do not show raw URLs on main slides. Do not use Evidence ID as the primary UI label.",
            "appendix_rule": "Appendix keeps Evidence ID + full URL for audit.",
            "missing_url_label": "Link tidak tersedia",
        },
        "topic_coverage_policy": topic_coverage,
        "claude_guardrails": [
            "Use only numbers and evidence from slides/report_input views.",
            "Do not invent competitor brands, metrics, URLs, quotes, or claims.",
            "On main slides, render evidence as clickable text 'Buka post' / 'Lihat post' using evidence_link.url. Do not display raw URLs on main slides.",
            "Do not use P##/T##/E## as the primary visible UI on main slides; Evidence IDs are audit metadata for appendix/data pack.",
            "Every evidence reference on a main slide must exist in evidence_registry and must have a matching source_url when link is available.",
            "Mention limitations when competitor universe or LLM topic/narrative coverage is incomplete.",
            "If topic_coverage_policy.severity is LOW_SAMPLE or VERY_LOW_SAMPLE, use wording 'classified sample' rather than definitive census language.",
        ],
    }
    package["quality_checks"] = {
        "evidence_integrity": validate_competitive_analysis_render_package(package)
    }
    return package


__all__ = [
    "RENDER_PACKAGE_VERSION",
    "REPORT_TYPE_ID",
    "audience_clarification_payload",
    "competitors_clarification_payload",
    "normalize_audience_context",
    "build_competitive_analysis_report_data_preview",
    "build_competitive_analysis_report_package",
    "validate_competitive_analysis_render_package",
]


# ---------------------------------------------------------------------------
# v3 client-facing presentation overlay
# - Preserve Action-Plan-First blueprint section order.
# - Hide audit Evidence IDs/raw URLs from client-facing slide text.
# - Keep URLs only inside evidence_link objects so PPT can render natural
#   hyperlinks such as "Lihat post" / "Buka artikel".
# ---------------------------------------------------------------------------

from reporting.task2.renderers.evidence_link_helper import (  # noqa: E402
    client_evidence_card,
    evidence_link,
    strip_client_visible_audit,
    validate_client_facing_presentation_package,
)

RENDER_PACKAGE_VERSION = "competitive_analysis_report_render_package_v3_client_facing"


def _ca_evidence_pool(report_input: Mapping[str, Any], limit: int = 30) -> list[dict[str, Any]]:
    views = [
        "ql_ca_positive_negative_highlights",
        "ql_ca_top_social_posts_by_brand",
        "ql_ca_topic_sentiment_by_brand",
        "ql_ca_top_authors_by_brand",
    ]
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for view_id in views:
        for row in _rows(report_input, view_id):
            url = _clean(row.get("source_url") or row.get("url") or row.get("link_url"))
            content = _clean(row.get("content") or row.get("title"), 200)
            key = url or content.casefold()
            if not key or key in seen:
                continue
            seen.add(key)
            item = dict(row)
            item["audit_evidence_id"] = f"E{len(out)+1:02d}"
            item["source_view_id"] = view_id
            item["evidence_link"] = evidence_link(item)
            item["client_evidence"] = client_evidence_card(item, text_limit=170)
            out.append(item)
            if len(out) >= limit:
                return out
    return out


def _ca_client_card(row: Mapping[str, Any], *, text_limit: int = 160) -> dict[str, Any]:
    return client_evidence_card(row, text_limit=text_limit)


def _ca_client_evidence_cards(rows: list[Mapping[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    cards = []
    seen: set[str] = set()
    for row in rows:
        url = _clean(row.get("source_url") or row.get("url") or row.get("link_url"))
        content = _clean(row.get("content") or row.get("title"), 120)
        key = url or content.casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        cards.append(_ca_client_card(row))
        if len(cards) >= limit:
            break
    return cards


def _ca_action_plan_v3(report_input: Mapping[str, Any], audience: Mapping[str, Any]) -> list[dict[str, Any]]:
    kpis = _brand_row_map(_rows(report_input, "qt_ca_kpi_summary_by_brand"))
    vol_rows = _rows(report_input, "qt_ca_brand_volume_engagement")
    sentiment_rows = _rows(report_input, "qt_ca_sentiment_by_brand")
    channel_rows = _rows(report_input, "qt_ca_channel_mix_by_brand")
    content_rows = _rows(report_input, "qt_ca_content_type_by_brand")
    evidence = _ca_evidence_pool(report_input, limit=12)
    client, competitors, _ = _brand_status(report_input)
    client_row = kpis.get(client or "") if client else None
    sov_leader = _leader(vol_rows, "sov_pct")
    soe_leader = _leader(vol_rows, "soe_pct")
    engagement_leader = _leader(kpis, "sum_engagement")
    top_negative = None
    for row in sentiment_rows:
        if _clean(row.get("sentiment")).casefold() == "negative":
            if top_negative is None or _num(row.get("engagement")) > _num(top_negative.get("engagement")):
                top_negative = row
    top_social = max(evidence, key=lambda row: _num(row.get("engagement") or row.get("interactions")), default={})
    top_client_evidence = next((row for row in evidence if _clean(row.get("brand") or row.get("campaign")).casefold() == _clean(client).casefold()), top_social)
    top_negative_card = client_evidence_card(top_client_evidence or top_social) if (top_client_evidence or top_social) else None
    top_benchmark_card = client_evidence_card(top_social) if top_social else None
    strongest_channel = _leader(channel_rows, "engagement")
    strongest_format = _leader(content_rows, "engagement")
    client_soe = _num((client_row or {}).get("soe_pct")) if client_row else 0
    client_sov = _num((client_row or {}).get("sov_pct")) if client_row else 0

    return [
        {
            "priority": "HIGH",
            "action_type": "Close the Gap",
            "focus_area": "SOV vs SOE gap",
            "recommended_action": "Tutup gap antara exposure dan interaksi dengan memprioritaskan channel/format yang paling terbukti menghasilkan respons, bukan sekadar menambah volume konten.",
            "rationale": f"{client or 'Client'} memiliki SOV {_fmt_pct(client_sov)} dan SOE {_fmt_pct(client_soe)}; leader SOE adalah {_clean((soe_leader or {}).get('brand')) or 'N/A'} ({_fmt_pct((soe_leader or {}).get('soe_pct'))}).",
            "supporting_evidence": top_benchmark_card,
            "expected_impact": "Engagement efficiency lebih kuat dan gap terhadap kompetitor utama lebih terukur.",
            "owner_next_step": "Brand/Marketing: pilih 1–2 channel prioritas dari gap SOV/SOE.",
        },
        {
            "priority": "HIGH" if top_negative else "MEDIUM",
            "action_type": "Mitigate Competitive Risk",
            "focus_area": "Negative issue / reputational trigger",
            "recommended_action": "Mitigasi sinyal negatif yang mulai konsisten dengan proof-point dan response posture ringan sebelum isu masuk akun/media besar.",
            "rationale": f"Engagement negatif terbesar terdeteksi pada {_clean((top_negative or {}).get('brand') or (top_negative or {}).get('campaign')) or 'N/A'} dengan engagement {_fmt_metric((top_negative or {}).get('engagement'))}.",
            "supporting_evidence": top_negative_card,
            "expected_impact": "Risiko isu kecil berkembang menjadi narasi kompetitif dapat ditekan lebih awal.",
            "owner_next_step": "PR/Insight: review bukti negatif utama dan siapkan wording monitoring.",
        },
        {
            "priority": "MEDIUM",
            "action_type": "Differentiate",
            "focus_area": "Narrative and product trust",
            "recommended_action": "Perkuat narasi pembeda yang tidak hanya meniru kompetitor, terutama pada pesan yang menjawab keraguan konsumen terhadap rasa, sumber, kualitas, atau manfaat produk.",
            "rationale": "Issue dan highlight konten menunjukkan risiko persepsi dapat muncul dari komentar kecil tetapi konsisten; diferensiasi harus berbasis proof-point, bukan klaim generik.",
            "supporting_evidence": top_negative_card or top_benchmark_card,
            "expected_impact": "Brand lebih punya wilayah pesan sendiri dan tidak hanya bereaksi pada framing kompetitor.",
            "owner_next_step": "Brand/Content: shortlist 3 angle pembeda untuk diuji di channel prioritas.",
        },
        {
            "priority": "MEDIUM",
            "action_type": "Exploit White Space",
            "focus_area": "Channel / content format opportunity",
            "recommended_action": "Ambil whitespace dari format/channel yang terbukti efektif di kategori tetapi belum dimaksimalkan oleh client.",
            "rationale": f"Channel/format terkuat dalam universe: {_clean((strongest_channel or {}).get('channel')) or 'N/A'} dan {_clean((strongest_format or {}).get('media_type')) or _clean((strongest_format or {}).get('content_type')) or 'N/A'}. ",
            "supporting_evidence": top_benchmark_card,
            "expected_impact": "Content plan berikutnya lebih berbasis benchmark performa, bukan asumsi kreatif.",
            "owner_next_step": "Content/Brand: adaptasi learning kompetitor dengan brand-fit check.",
        },
        {
            "priority": "LOW" if _clean((sov_leader or {}).get("brand")) != _clean(client) else "MEDIUM",
            "action_type": "Defend",
            "focus_area": "Existing strength",
            "recommended_action": "Pertahankan area yang sudah kuat sambil menghindari tone-deaf amplification ketika isu negatif masih aktif.",
            "rationale": f"Leader volume: {_clean((sov_leader or {}).get('brand')) or 'N/A'}; leader engagement: {_clean((engagement_leader or {}).get('brand')) or 'N/A'}.",
            "supporting_evidence": top_benchmark_card,
            "expected_impact": "Keunggulan yang sudah ada tidak tergerus oleh isu negatif atau respons yang tidak sesuai konteks.",
            "owner_next_step": "Marketing/PR: cek konten yang akan diamplifikasi terhadap risk signal terbaru.",
        },
    ]


def _ca_topic_caveat_client(topic_coverage: Mapping[str, Any]) -> str | None:
    coverage = topic_coverage.get("coverage_pct")
    if coverage is None:
        return None
    if float(coverage) < 20:
        return "Narrative signal masih bersifat directional karena klasifikasi topik belum mencakup seluruh konten."
    return None


def build_competitive_analysis_report_package(
    report_input_id: str,
    *,
    allow_partial: bool = True,
    audience_context: str | None = None,
    audience_pov: str | None = None,
) -> dict[str, Any]:  # override v2
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
    top_posts_raw = _rows(report_input, "ql_ca_top_social_posts_by_brand")
    highlights_raw = _rows(report_input, "ql_ca_positive_negative_highlights")
    top_authors_raw = _rows(report_input, "ql_ca_top_authors_by_brand")
    topics = _top_topics(report_input, limit=12)
    evidence = _ca_evidence_pool(report_input, limit=80)
    topic_coverage = _topic_coverage_context(report_input)
    action_plan = _ca_action_plan_v3(report_input, audience)
    limitations = list(report_input.get("limitations") or [])
    metric = dict(report_input.get("metric_readiness") or {})
    data_health = dict(report_input.get("data_health") or {})

    total_content = sum(_num(row.get("count_content")) for row in kpis)
    total_interactions = sum(_num(row.get("sum_engagement") or row.get("sum_interactions")) for row in kpis)
    sov_leader = _leader(vol_rows, "sov_pct")
    soe_leader = _leader(vol_rows, "soe_pct")
    efficiency_leader = _leader(kpis, "engagement_per_content")
    narrative_caveat = _ca_topic_caveat_client(topic_coverage)

    top_posts = _ca_client_evidence_cards(top_posts_raw, limit=10)
    highlights = _ca_client_evidence_cards(highlights_raw, limit=10)
    top_authors = [
        strip_client_visible_audit({
            "brand": _clean(row.get("brand") or row.get("campaign")),
            "author": _clean(row.get("author"), 80),
            "channel": _clean(row.get("channel"), 50),
            "sentiment": _clean(row.get("sentiment"), 40),
            "engagement": row.get("engagement"),
            "sample_content": _clean(row.get("content"), 140),
            "evidence_link": evidence_link(row),
        })
        for row in top_authors_raw[:10]
    ]
    topic_cards = [
        strip_client_visible_audit({
            "brand": _clean(row.get("brand") or row.get("campaign")),
            "topic": _clean(row.get("topic") or row.get("topic_extraction") or row.get("issue_label"), 100),
            "sentiment": _clean(row.get("sentiment"), 40),
            "engagement": row.get("engagement"),
            "count_content": row.get("count_content"),
            "sample_content": _clean(row.get("content"), 160),
            "evidence_link": evidence_link(row),
        })
        for row in topics[:10]
    ]

    slides = [
        {
            "slide_no": 1,
            "section": "Header / Report Identity",
            "title": "COMPETITIVE ANALYSIS",
            "subtitle": f"{client or context.get('project_name')} vs {', '.join(competitors) if competitors else 'benchmark universe'} · {period.get('start_date')}–{period.get('end_date')}",
            "layout": "cover_competitive_snapshot",
            "audience": audience,
            "kpi_tiles": [
                {"label": "BRANDS", "value": len(brands), "note": ", ".join(brands[:4])},
                {"label": "TOTAL CONTENT", "value": _fmt_int(total_content), "note": "canonical mapped rows"},
                {"label": "TOTAL INTERACTIONS", "value": _fmt_int(total_interactions), "note": "views reported separately when available"},
                {"label": "SOV LEADER", "value": _clean((sov_leader or {}).get("brand")) or "N/A", "note": _fmt_pct((sov_leader or {}).get("sov_pct"))},
                {"label": "SOE LEADER", "value": _clean((soe_leader or {}).get("brand")) or "N/A", "note": _fmt_pct((soe_leader or {}).get("soe_pct"))},
            ],
            "decision_implication": "Baca SOV dan SOE bersamaan: volume tinggi belum tentu efektif bila engagement share tertinggal.",
        },
        {
            "slide_no": 2,
            "section": "Executive Summary",
            "title": "EXECUTIVE SUMMARY",
            "subtitle": "Posisi kompetitif, gap utama, dan keputusan yang perlu diarahkan",
            "layout": "executive_summary_cards",
            "cards": [
                {"label": "SITUASI", "text": f"Scope memuat {_fmt_int(total_content)} konten dari {len(brands)} brand dalam competitive universe."},
                {"label": "LEADER BY SOV", "text": f"{_clean((sov_leader or {}).get('brand')) or 'N/A'} memimpin share of voice ({_fmt_pct((sov_leader or {}).get('sov_pct'))})."},
                {"label": "LEADER BY SOE", "text": f"{_clean((soe_leader or {}).get('brand')) or 'N/A'} memimpin share of engagement ({_fmt_pct((soe_leader or {}).get('soe_pct'))})."},
                {"label": "EFFICIENCY SIGNAL", "text": f"{_clean((efficiency_leader or {}).get('brand')) or 'N/A'} memiliki engagement per content tertinggi ({_fmt_metric((efficiency_leader or {}).get('engagement_per_content'))})."},
                {"label": "EXECUTIVE READOUT", "text": "Prioritasnya bukan hanya siapa paling ramai, tetapi channel/format mana yang menutup gap engagement dan risiko narasi mana yang perlu dimitigasi."},
            ],
            "narrative_caveat": narrative_caveat,
        },
        {
            "slide_no": 3,
            "section": "Competitive Action Plan",
            "title": "COMPETITIVE ACTION PLAN",
            "subtitle": "Defend · Close the Gap · Differentiate · Exploit White Space · Mitigate Competitive Risk",
            "layout": "action_plan_cards_natural_links",
            "cards": strip_client_visible_audit(action_plan),
        },
        {
            "slide_no": 4,
            "section": "Competitive Landscape Evidence",
            "title": "COMPETITIVE LANDSCAPE EVIDENCE",
            "subtitle": "Brand role, positioning, and competitive gap",
            "layout": "benchmark_table_and_readout",
            "table": vol_rows,
            "interpretation": "Brand dengan SOV tinggi tapi SOE rendah membutuhkan optimasi creative/channel, bukan sekadar tambahan volume.",
        },
        {
            "slide_no": 5,
            "section": "SOV, SOE & Engagement Efficiency Benchmark",
            "title": "SOV, SOE & ENGAGEMENT EFFICIENCY BENCHMARK",
            "subtitle": "Siapa paling ramai dan siapa paling efektif",
            "layout": "sov_soe_efficiency_benchmark",
            "brand_volume_engagement": vol_rows,
            "kpi_summary_by_brand": kpis,
        },
        {
            "slide_no": 6,
            "section": "Sentiment & Issue Landscape by Brand",
            "title": "SENTIMENT & ISSUE LANDSCAPE BY BRAND",
            "subtitle": "Driver positif/negatif dan risiko per brand",
            "layout": "sentiment_issue_cards",
            "sentiment_table": sentiment_rows,
            "topic_cards": topic_cards,
            "narrative_caveat": narrative_caveat,
        },
        {
            "slide_no": 7,
            "section": "Channel & Content Strategy Comparison",
            "title": "CHANNEL & CONTENT STRATEGY COMPARISON",
            "subtitle": "Channel mix dan format konten antar brand",
            "layout": "channel_content_strategy",
            "channel_mix": channel_rows,
            "content_type": content_rows,
            "interpretation": "Prioritaskan channel dengan gap SOE terbesar dan format yang terbukti efisien; jangan membagi effort merata ke semua channel.",
        },
        {
            "slide_no": 8,
            "section": "Best Practices & Competitive Playbook",
            "title": "BEST PRACTICES & COMPETITIVE PLAYBOOK",
            "subtitle": "Apa yang bisa ditiru, dihindari, atau diadaptasi dari kompetitor",
            "layout": "playbook_cards_natural_links",
            "top_posts": top_posts,
            "rule": "Gunakan sebagai inspirasi benchmark; jangan menyalin kreatif/pesan kompetitor tanpa brand-fit dan risk review.",
        },
        {
            "slide_no": 9,
            "section": "Supporting Content & Author Evidence",
            "title": "SUPPORTING CONTENT & AUTHOR EVIDENCE",
            "subtitle": "Contoh konten dan author yang mendukung action plan",
            "layout": "supporting_content_author_cards",
            "positive_negative_highlights": highlights,
            "top_authors": top_authors,
        },
        {
            "slide_no": 10,
            "section": "Scope & Methodology",
            "title": "SCOPE & METHODOLOGY",
            "subtitle": "Metric contract, limitations, and audit note",
            "layout": "sources_notes_clean",
            "scope": {
                "project": context.get("project_name"),
                "period": period,
                "client_brand": client,
                "competitors": competitors,
                "channels": context.get("channels"),
            },
            "metric_contract": [
                "SOV = content brand ÷ total content.",
                "SOE = interaction brand ÷ total interaction.",
                "Views dilaporkan terpisah dari interactions jika tersedia.",
                "Narrative/topic signal menggunakan classified sample dan harus dibaca sesuai coverage.",
            ],
            "data_health": data_health,
            "limitations": limitations + ([narrative_caveat] if narrative_caveat else []),
        },
    ]
    slides = [strip_client_visible_audit(slide) for slide in slides]
    outline = build_report_outline_from_id(report_input_id, allow_partial=allow_partial)
    evidence_registry = {
        item.get("audit_evidence_id") or f"E{idx+1:02d}": {
            "audit_evidence_id": item.get("audit_evidence_id") or f"E{idx+1:02d}",
            "source_url": item.get("source_url") or item.get("url") or item.get("link_url"),
            "content": _clean(item.get("content") or item.get("title"), 200),
            "brand": _clean(item.get("brand") or item.get("campaign")),
            "channel": _clean(item.get("channel")),
        }
        for idx, item in enumerate(evidence)
    }
    package = {
        "success": True,
        "report_type_id": REPORT_TYPE_ID,
        "render_package_version": RENDER_PACKAGE_VERSION,
        "quality_upgrade": "v3_client_facing_evidence_and_action_plan_first",
        "package_id": _now_id("pkg_ca"),
        "report_input_id": report_input_id,
        "outline_id": outline.get("outline_id"),
        "outline_status": outline.get("outline_status"),
        "audience_context": audience,
        "context": context,
        "client_brand": client,
        "competitor_brands": competitors,
        "section_order_policy": "Action Plan First blueprint preserved; extra slides must be attached to their parent section.",
        "slides": slides,
        "evidence_link_policy": {
            "main_slides": "Use natural clickable labels: Lihat post, Lihat komentar, Buka artikel. Do not render audit IDs or raw URLs as visible text.",
            "audit": "Audit identifiers and URLs remain available in evidence_registry/export data, not as client-facing labels.",
        },
        "ppt_style_brief": {
            "tone": audience.get("tone"),
            "visual_direction": "client-facing consulting deck, action-plan-first, natural evidence CTAs, no raw URL/evidence code clutter",
            "avoid": ["visible E01/T09/P06 style evidence codes", "raw URL text", "internal taxonomy/debug wording", "recommendations without rationale"],
            "preferred_components": ["decision cards", "action plan cards", "benchmark matrix", "natural hyperlink buttons", "content cards"],
        },
        "evidence_registry": evidence_registry,
        "topic_coverage_policy": topic_coverage,
        "claude_guardrails": [
            "Follow the section order in slides; do not invent new main sections outside the Action-Plan-First blueprint.",
            "If extra slides are needed, keep them under their parent section label.",
            "Render evidence links as natural clickable text only: Lihat post, Lihat komentar, or Buka artikel.",
            "Do not display audit IDs such as E01/T09/P06 on client-facing slides.",
            "Do not print raw URLs on client-facing slides.",
            "Do not show internal wording such as raw Topic Extraction policy, evidence registry, or URL appendix instructions.",
            "Use directional wording when topic coverage is low.",
        ],
    }
    package["quality_checks"] = {
        "evidence_integrity": validate_competitive_analysis_render_package(package),
        "client_facing_policy": validate_client_facing_presentation_package(package, report_type="competitive_analysis"),
    }
    return package


# ---------------------------------------------------------------------------
# v4 strategic QA overlay
# Fixes client-facing CA defects found in live smoke tests:
# - SOV/SOE lookup must use qt_ca_brand_volume_engagement, not KPI-only rows.
# - Risk evidence must match the claim sentiment/brand.
# - Cross-brand duplicate evidence must not be attributed to the wrong brand.
# - Internal topic labels such as "Unclassified / Needs LLM" must not render.
# - Executive readout must surface top-post concentration before treating SOE as systemic.
# ---------------------------------------------------------------------------

import re  # noqa: E402

RENDER_PACKAGE_VERSION = "competitive_analysis_report_render_package_v4_strategic_qa"

_INTERNAL_TOPIC_VALUES = {
    "unclassified",
    "unclassified / needs llm",
    "needs llm",
    "needs_llm",
    "unknown",
    "n/a",
    "na",
    "none",
}


def _brand_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", _clean(value).casefold())


def _row_brand(row: Mapping[str, Any]) -> str:
    return _clean(row.get("brand") or row.get("campaign") or row.get("client_brand"))


def _find_brand_row(rows: Any, brand: str | None) -> Mapping[str, Any] | None:
    if not brand:
        return None
    target = _brand_key(brand)
    candidates = rows.values() if isinstance(rows, Mapping) else (rows or [])
    for row in candidates:
        if isinstance(row, Mapping) and _brand_key(_row_brand(row)) == target:
            return row
    return None


def _field_num(row: Mapping[str, Any] | None, *fields: str) -> int | float:
    if not row:
        return 0
    for field in fields:
        if row.get(field) is not None:
            return _num(row.get(field))
    return 0


def _client_safe_topic(value: Any) -> str:
    text = _clean(value, 90)
    if not text or text.casefold() in _INTERNAL_TOPIC_VALUES:
        return ""
    if "needs llm" in text.casefold() or "unclassified" in text.casefold():
        return ""
    return text


def _ca_client_card(row: Mapping[str, Any], *, text_limit: int = 160) -> dict[str, Any]:  # override v3
    card = client_evidence_card(row, text_limit=text_limit)
    topic = _client_safe_topic(card.get("topic"))
    if topic:
        card["topic"] = topic
    else:
        card.pop("topic", None)
    return strip_client_visible_audit(card)


def _ca_content_key(row: Mapping[str, Any]) -> str:
    url = _clean(row.get("source_url") or row.get("url") or row.get("link_url") or row.get("full_url"))
    if url:
        return "url:" + url.casefold()
    content = _clean(row.get("content") or row.get("title") or row.get("snippet"), 220)
    author = _clean(row.get("author") or row.get("media_name") or row.get("source"), 80)
    return "content:" + (author + "|" + content).casefold() if content else ""


def _infer_brand_from_text(row: Mapping[str, Any], brands: list[str]) -> str | None:
    text = " ".join(
        _clean(row.get(key))
        for key in ("content", "title", "snippet", "topic", "topic_extraction", "author")
        if row.get(key)
    ).casefold()
    if not text:
        return None
    matches: list[str] = []
    for brand in brands:
        b = _clean(brand)
        if not b:
            continue
        # Word-boundary-ish matching prevents "Aqua" from matching "Aquviva".
        pattern = r"(?<![a-z0-9])" + re.escape(b.casefold()) + r"(?![a-z0-9])"
        if re.search(pattern, text):
            matches.append(brand)
    unique = []
    for brand in matches:
        if _brand_key(brand) not in {_brand_key(item) for item in unique}:
            unique.append(brand)
    if len(unique) == 1:
        return unique[0]
    if len(unique) > 1:
        return "Multi-brand"
    return None


def _merge_cross_brand_evidence_rows(rows: list[Mapping[str, Any]], brands: list[str]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    passthrough: list[dict[str, Any]] = []
    for row in rows:
        key = _ca_content_key(row)
        if not key:
            passthrough.append(dict(row))
            continue
        grouped.setdefault(key, []).append(row)

    merged: list[dict[str, Any]] = []
    for items in grouped.values():
        best = max(items, key=lambda item: _num(item.get("engagement") or item.get("interactions") or item.get("metric")))
        out = dict(best)
        row_brands = [_row_brand(item) for item in items if _row_brand(item)]
        inferred = _infer_brand_from_text(out, brands)
        if inferred:
            out["brand"] = inferred
            out["campaign"] = inferred
        else:
            normalized = []
            seen = set()
            for brand in row_brands:
                key = _brand_key(brand)
                if key and key not in seen:
                    seen.add(key)
                    normalized.append(brand)
            if len(normalized) > 1:
                out["brand"] = "Multi-brand"
                out["campaign"] = "Multi-brand"
                out["mentioned_brands"] = normalized
            elif len(normalized) == 1:
                out["brand"] = normalized[0]
                out["campaign"] = normalized[0]
        merged.append(out)
    merged.extend(passthrough)
    merged.sort(key=lambda row: _num(row.get("engagement") or row.get("interactions") or row.get("metric")), reverse=True)
    return merged


def _ca_all_evidence_rows(report_input: Mapping[str, Any], brands: list[str]) -> list[dict[str, Any]]:
    views = [
        "ql_ca_positive_negative_highlights",
        "ql_ca_top_social_posts_by_brand",
        "ql_ca_topic_sentiment_by_brand",
        "ql_ca_top_authors_by_brand",
    ]
    rows: list[dict[str, Any]] = []
    for view_id in views:
        for row in _rows(report_input, view_id):
            item = dict(row)
            item["source_view_id"] = view_id
            item["evidence_link"] = evidence_link(item)
            rows.append(item)
    return _merge_cross_brand_evidence_rows(rows, brands)


def _best_evidence(
    rows: list[Mapping[str, Any]],
    *,
    brand: str | None = None,
    sentiment: str | None = None,
    exclude_keys: set[str] | None = None,
) -> Mapping[str, Any] | None:
    exclude_keys = exclude_keys or set()
    candidates: list[Mapping[str, Any]] = []
    for row in rows:
        if _ca_content_key(row) in exclude_keys:
            continue
        if brand and _brand_key(_row_brand(row)) != _brand_key(brand):
            continue
        if sentiment and _clean(row.get("sentiment")).casefold() != sentiment.casefold():
            continue
        candidates.append(row)
    if not candidates:
        return None
    return max(candidates, key=lambda row: _num(row.get("engagement") or row.get("interactions") or row.get("metric")))


def _ca_client_evidence_cards(rows: list[Mapping[str, Any]], limit: int = 8, *, brands: list[str] | None = None) -> list[dict[str, Any]]:  # override v3
    source_rows = _merge_cross_brand_evidence_rows(rows, brands or []) if brands else list(rows)
    cards = []
    seen: set[str] = set()
    for row in source_rows:
        key = _ca_content_key(row)
        if not key or key in seen:
            continue
        seen.add(key)
        card = _ca_client_card(row)
        if card:
            cards.append(card)
        if len(cards) >= limit:
            break
    return cards


def _concentration_cards(
    *,
    brands: list[str],
    top_rows: list[Mapping[str, Any]],
    kpi_rows: list[Mapping[str, Any]],
    volume_rows: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    merged_top = _merge_cross_brand_evidence_rows(list(top_rows), brands)
    cards: list[dict[str, Any]] = []
    for brand in brands:
        brand_posts = [row for row in merged_top if _brand_key(_row_brand(row)) == _brand_key(brand)]
        if not brand_posts:
            continue
        top = max(brand_posts, key=lambda row: _num(row.get("engagement") or row.get("interactions")))
        total_row = _find_brand_row(kpi_rows, brand) or _find_brand_row(volume_rows, brand)
        total = _field_num(total_row, "sum_engagement", "sum_interactions", "engagement", "interactions")
        top_eng = _num(top.get("engagement") or top.get("interactions"))
        share = (top_eng / total * 100) if total else None
        level = "HIGH" if share is not None and share >= 50 else "MEDIUM" if share is not None and share >= 35 else "LOW"
        cards.append({
            "brand": brand,
            "top_content": _ca_client_card(top, text_limit=130),
            "top_interactions": top_eng,
            "brand_total_interactions": total,
            "top_post_share_pct": round(share, 1) if share is not None else None,
            "concentration_level": level,
            "readout": (
                f"{brand} sangat ditopang satu konten; jangan dibaca sebagai keunggulan sistemik."
                if level == "HIGH"
                else f"{brand} memiliki konsentrasi top-content yang perlu dipantau."
                if level == "MEDIUM"
                else f"{brand} relatif tidak bergantung pada satu konten utama."
            ),
        })
    cards.sort(key=lambda item: _num(item.get("top_post_share_pct")), reverse=True)
    return cards


def _ca_action_plan_v4(report_input: Mapping[str, Any], audience: Mapping[str, Any], *, concentration: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    vol_rows = _rows(report_input, "qt_ca_brand_volume_engagement")
    kpi_rows = _rows(report_input, "qt_ca_kpi_summary_by_brand")
    sentiment_rows = _rows(report_input, "qt_ca_sentiment_by_brand")
    channel_rows = _rows(report_input, "qt_ca_channel_mix_by_brand")
    content_rows = _rows(report_input, "qt_ca_content_type_by_brand")
    client, competitors, brands = _brand_status(report_input)
    evidence_rows = _ca_all_evidence_rows(report_input, brands)

    client_vol = _find_brand_row(vol_rows, client)
    client_sent_neg = next(
        (
            row for row in sentiment_rows
            if _brand_key(_row_brand(row)) == _brand_key(client) and _clean(row.get("sentiment")).casefold() == "negative"
        ),
        None,
    )
    sov_leader = _leader(vol_rows, "sov_pct")
    soe_leader = _leader(vol_rows, "soe_pct")
    strongest_channel = _leader(channel_rows, "engagement")
    strongest_format = _leader(content_rows, "engagement")

    client_sov = _field_num(client_vol, "sov_pct")
    client_soe = _field_num(client_vol, "soe_pct")
    client_negative_evidence = _best_evidence(evidence_rows, brand=client, sentiment="negative")
    client_positive_evidence = _best_evidence(evidence_rows, brand=client, sentiment="positive", exclude_keys={_ca_content_key(client_negative_evidence or {})})
    soe_leader_brand = _row_brand(soe_leader or {})
    benchmark_evidence = _best_evidence(evidence_rows, brand=soe_leader_brand) or _best_evidence(evidence_rows)
    concentration = concentration or []
    concentration_leader = next((item for item in concentration if _brand_key(item.get("brand")) == _brand_key(soe_leader_brand)), None)
    concentration_note = ""
    if concentration_leader and _num(concentration_leader.get("top_post_share_pct")) >= 50:
        concentration_note = f" Namun {_clean(soe_leader_brand)} ditopang satu konten utama ({_fmt_pct(concentration_leader.get('top_post_share_pct'))} dari interaksi brand), jadi gap ini perlu dibaca sebagai event/content-driven."

    return [
        {
            "priority": "HIGH",
            "action_type": "Close the Gap",
            "focus_area": "SOV vs SOE gap",
            "recommended_action": "Tutup gap antara volume dan interaksi dengan memprioritaskan format/channel yang terbukti menghasilkan respons, bukan sekadar menambah jumlah konten.",
            "rationale": f"{client or 'Client'} memiliki SOV {_fmt_pct(client_sov)} dan SOE {_fmt_pct(client_soe)}; leader SOE adalah {_clean(soe_leader_brand) or 'N/A'} ({_fmt_pct((soe_leader or {}).get('soe_pct'))}).{concentration_note}",
            "supporting_evidence": _ca_client_card(benchmark_evidence, text_limit=150) if benchmark_evidence else None,
            "expected_impact": "Gap engagement lebih jelas ditutup lewat creative/channel yang tepat, sambil menghindari salah baca outlier sebagai dominasi sistemik.",
            "owner_next_step": "Brand/Marketing: pilih 1–2 format dan channel prioritas dari gap SOV/SOE + concentration check.",
        },
        {
            "priority": "HIGH" if client_sent_neg else "MEDIUM",
            "action_type": "Mitigate Competitive Risk",
            "focus_area": "Negative issue / reputational trigger",
            "recommended_action": "Mitigasi sinyal negatif client dengan proof-point dan response posture ringan sebelum isu masuk akun/media besar.",
            "rationale": f"Konten negatif {client or 'client'} menghasilkan {_fmt_metric((client_sent_neg or {}).get('engagement'))} engagement; bukti yang dipakai harus berasal dari konten negatif client, bukan top post positif.",
            "supporting_evidence": _ca_client_card(client_negative_evidence, text_limit=150) if client_negative_evidence else None,
            "expected_impact": "Risiko isu kecil berkembang menjadi narasi kompetitif dapat ditekan lebih awal.",
            "owner_next_step": "PR/Insight: review bukti negatif utama dan siapkan wording monitoring.",
        },
        {
            "priority": "MEDIUM",
            "action_type": "Differentiate",
            "focus_area": "Narrative and product trust",
            "recommended_action": "Perkuat narasi pembeda yang menjawab keraguan konsumen terhadap rasa, sumber, kualitas, atau manfaat produk tanpa menyerang kompetitor.",
            "rationale": "Komentar negatif dan highlight konten menunjukkan persepsi produk dapat berubah dari preferensi menjadi keraguan; diferensiasi harus berbasis proof-point.",
            "supporting_evidence": _ca_client_card(client_negative_evidence or client_positive_evidence or benchmark_evidence, text_limit=150) if (client_negative_evidence or client_positive_evidence or benchmark_evidence) else None,
            "expected_impact": "Brand punya territory pesan sendiri dan tidak hanya bereaksi pada framing kompetitor.",
            "owner_next_step": "Brand/Content: shortlist 3 angle pembeda untuk diuji di channel prioritas.",
        },
        {
            "priority": "MEDIUM",
            "action_type": "Exploit White Space",
            "focus_area": "Channel / content format opportunity",
            "recommended_action": "Ambil whitespace dari format/channel yang terbukti efektif di kategori tetapi belum dimaksimalkan oleh client.",
            "rationale": f"Channel/format terkuat dalam universe: {_clean((strongest_channel or {}).get('channel')) or 'N/A'} dan {_clean((strongest_format or {}).get('media_type')) or _clean((strongest_format or {}).get('content_type')) or 'N/A'}.",
            "supporting_evidence": _ca_client_card(benchmark_evidence, text_limit=150) if benchmark_evidence else None,
            "expected_impact": "Content plan berikutnya lebih berbasis benchmark performa, bukan asumsi kreatif.",
            "owner_next_step": "Content/Brand: adaptasi learning kompetitor dengan brand-fit check.",
        },
        {
            "priority": "LOW" if _brand_key(_row_brand(sov_leader or {})) != _brand_key(client) else "MEDIUM",
            "action_type": "Defend",
            "focus_area": "Existing strength",
            "recommended_action": "Pertahankan area yang sudah kuat sambil menghindari amplifikasi tone-deaf ketika isu negatif masih aktif.",
            "rationale": f"Leader volume: {_clean(_row_brand(sov_leader or {})) or 'N/A'}; leader engagement: {_clean(_row_brand(soe_leader or {})) or 'N/A'}.",
            "supporting_evidence": _ca_client_card(client_positive_evidence or benchmark_evidence, text_limit=150) if (client_positive_evidence or benchmark_evidence) else None,
            "expected_impact": "Keunggulan yang sudah ada tidak tergerus oleh isu negatif atau respons yang tidak sesuai konteks.",
            "owner_next_step": "Marketing/PR: cek konten yang akan diamplifikasi terhadap risk signal terbaru.",
        },
    ]


def build_competitive_analysis_report_package(
    report_input_id: str,
    *,
    allow_partial: bool = True,
    audience_context: str | None = None,
    audience_pov: str | None = None,
) -> dict[str, Any]:  # override v3 with v4 strategic QA
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
    top_posts_raw = _rows(report_input, "ql_ca_top_social_posts_by_brand")
    highlights_raw = _rows(report_input, "ql_ca_positive_negative_highlights")
    top_authors_raw = _rows(report_input, "ql_ca_top_authors_by_brand")
    topics = _top_topics(report_input, limit=12)
    topic_coverage = _topic_coverage_context(report_input)
    limitations = list(report_input.get("limitations") or [])
    data_health = dict(report_input.get("data_health") or {})

    merged_top_posts = _merge_cross_brand_evidence_rows(top_posts_raw, brands)
    merged_highlights = _merge_cross_brand_evidence_rows(highlights_raw, brands)
    merged_authors = _merge_cross_brand_evidence_rows(top_authors_raw, brands)
    concentration = _concentration_cards(brands=brands, top_rows=merged_top_posts, kpi_rows=kpis, volume_rows=vol_rows)
    action_plan = _ca_action_plan_v4(report_input, audience, concentration=concentration)

    total_content = sum(_num(row.get("count_content")) for row in kpis)
    total_interactions = sum(_num(row.get("sum_engagement") or row.get("sum_interactions") or row.get("engagement")) for row in kpis)
    sov_leader = _leader(vol_rows, "sov_pct")
    soe_leader = _leader(vol_rows, "soe_pct")
    efficiency_leader = _leader(kpis, "engagement_per_content")
    narrative_caveat = _ca_topic_caveat_client(topic_coverage)
    soe_leader_concentration = next((item for item in concentration if _brand_key(item.get("brand")) == _brand_key(_row_brand(soe_leader or {}))), None)
    concentration_readout = None
    if soe_leader_concentration and _num(soe_leader_concentration.get("top_post_share_pct")) >= 50:
        concentration_readout = f"{_row_brand(soe_leader or {})} memimpin SOE, tetapi {_fmt_pct(soe_leader_concentration.get('top_post_share_pct'))} interaksinya berasal dari satu konten; baca sebagai event/content-driven, bukan otomatis keunggulan sistemik."

    top_posts = _ca_client_evidence_cards(merged_top_posts, limit=10, brands=brands)
    highlights = _ca_client_evidence_cards(merged_highlights, limit=10, brands=brands)
    top_authors = [
        strip_client_visible_audit({
            "brand": _row_brand(row),
            "author": _clean(row.get("author"), 80),
            "channel": _clean(row.get("channel"), 50),
            "sentiment": _clean(row.get("sentiment"), 40),
            "engagement": row.get("engagement"),
            "sample_content": _clean(row.get("content"), 140),
            "evidence_link": evidence_link(row),
        })
        for row in merged_authors[:10]
    ]
    topic_cards = []
    for row in topics[:10]:
        topic = _client_safe_topic(row.get("topic") or row.get("topic_extraction") or row.get("issue_label"))
        if not topic:
            continue
        topic_cards.append(strip_client_visible_audit({
            "brand": _row_brand(row),
            "topic": topic,
            "sentiment": _clean(row.get("sentiment"), 40),
            "engagement": row.get("engagement"),
            "count_content": row.get("count_content"),
            "sample_content": _clean(row.get("content"), 160),
            "evidence_link": evidence_link(row),
        }))

    slides = [
        {
            "slide_no": 1,
            "section": "Header / Report Identity",
            "title": "COMPETITIVE ANALYSIS",
            "subtitle": f"{client or context.get('project_name')} vs {', '.join(competitors) if competitors else 'benchmark universe'} · {period.get('start_date')}–{period.get('end_date')}",
            "layout": "cover_competitive_snapshot",
            "audience": audience,
            "kpi_tiles": [
                {"label": "BRANDS", "value": len(brands), "note": ", ".join(brands[:4])},
                {"label": "TOTAL CONTENT", "value": _fmt_int(total_content), "note": "canonical mapped rows"},
                {"label": "TOTAL INTERACTIONS", "value": _fmt_int(total_interactions), "note": "views reported separately when available"},
                {"label": "SOV LEADER", "value": _row_brand(sov_leader or {}) or "N/A", "note": _fmt_pct((sov_leader or {}).get("sov_pct"))},
                {"label": "SOE LEADER", "value": _row_brand(soe_leader or {}) or "N/A", "note": _fmt_pct((soe_leader or {}).get("soe_pct"))},
            ],
            "decision_implication": "Baca SOV, SOE, dan concentration check bersamaan: volume tinggi atau satu konten viral belum tentu berarti dominasi sistemik.",
        },
        {
            "slide_no": 2,
            "section": "Executive Summary",
            "title": "EXECUTIVE SUMMARY",
            "subtitle": "Posisi kompetitif, gap utama, dan keputusan yang perlu diarahkan",
            "layout": "executive_summary_cards",
            "cards": [
                {"label": "SITUASI", "text": f"Scope memuat {_fmt_int(total_content)} konten dari {len(brands)} brand dalam competitive universe."},
                {"label": "LEADER BY SOV", "text": f"{_row_brand(sov_leader or {}) or 'N/A'} memimpin share of voice ({_fmt_pct((sov_leader or {}).get('sov_pct'))})."},
                {"label": "LEADER BY SOE", "text": f"{_row_brand(soe_leader or {}) or 'N/A'} memimpin share of engagement ({_fmt_pct((soe_leader or {}).get('soe_pct'))})."},
                {"label": "CONCENTRATION CHECK", "text": concentration_readout or "Tidak ada satu konten utama yang mendominasi mayoritas interaksi leader."},
                {"label": "EXECUTIVE READOUT", "text": "Prioritasnya adalah menutup gap engagement, membaca outlier secara hati-hati, dan memitigasi isu negatif yang evidence-nya benar-benar relevan dengan client."},
            ],
            "narrative_caveat": narrative_caveat,
        },
        {
            "slide_no": 3,
            "section": "Competitive Action Plan",
            "title": "COMPETITIVE ACTION PLAN",
            "subtitle": "Defend · Close the Gap · Differentiate · Exploit White Space · Mitigate Competitive Risk",
            "layout": "action_plan_cards_natural_links",
            "cards": strip_client_visible_audit(action_plan),
        },
        {
            "slide_no": 4,
            "section": "Competitive Landscape Evidence",
            "title": "CONCENTRATION CHECK",
            "subtitle": "Cek apakah dominasi engagement berasal dari kekuatan sistemik atau satu konten besar",
            "layout": "top_content_concentration_check",
            "cards": strip_client_visible_audit(concentration),
            "interpretation": "Jika satu konten menyumbang mayoritas engagement brand, baca SOE sebagai event/content-driven dan jangan langsung disimpulkan sebagai keunggulan sistemik.",
        },
        {
            "slide_no": 5,
            "section": "Competitive Landscape Evidence",
            "title": "COMPETITIVE LANDSCAPE EVIDENCE",
            "subtitle": "Brand role, positioning, and competitive gap",
            "layout": "benchmark_table_and_readout",
            "table": vol_rows,
            "interpretation": "Brand dengan SOV tinggi tapi SOE rendah membutuhkan optimasi creative/channel, bukan sekadar tambahan volume.",
        },
        {
            "slide_no": 6,
            "section": "SOV, SOE & Engagement Efficiency Benchmark",
            "title": "SOV, SOE & ENGAGEMENT EFFICIENCY BENCHMARK",
            "subtitle": "Siapa paling ramai dan siapa paling efektif",
            "layout": "sov_soe_efficiency_benchmark",
            "brand_volume_engagement": vol_rows,
            "kpi_summary_by_brand": kpis,
        },
        {
            "slide_no": 7,
            "section": "Sentiment & Issue Landscape by Brand",
            "title": "SENTIMENT & ISSUE LANDSCAPE BY BRAND",
            "subtitle": "Driver positif/negatif dan risiko per brand",
            "layout": "sentiment_issue_cards",
            "sentiment_table": sentiment_rows,
            "topic_cards": topic_cards,
            "narrative_caveat": narrative_caveat,
        },
        {
            "slide_no": 8,
            "section": "Channel & Content Strategy Comparison",
            "title": "CHANNEL & CONTENT STRATEGY COMPARISON",
            "subtitle": "Channel mix dan format konten antar brand",
            "layout": "channel_content_strategy",
            "channel_mix": channel_rows,
            "content_type": content_rows,
            "interpretation": "Prioritaskan channel dengan gap SOE terbesar dan format yang terbukti efisien; jangan membagi effort merata ke semua channel.",
        },
        {
            "slide_no": 9,
            "section": "Best Practices & Competitive Playbook",
            "title": "BEST PRACTICES & COMPETITIVE PLAYBOOK",
            "subtitle": "Apa yang bisa ditiru, dihindari, atau diadaptasi dari kompetitor",
            "layout": "playbook_cards_natural_links",
            "top_posts": top_posts,
            "rule": "Gunakan sebagai inspirasi benchmark; jangan menyalin kreatif/pesan kompetitor tanpa brand-fit dan risk review.",
        },
        {
            "slide_no": 10,
            "section": "Supporting Content & Author Evidence",
            "title": "SUPPORTING CONTENT & AUTHOR EVIDENCE",
            "subtitle": "Contoh konten dan author yang mendukung action plan",
            "layout": "supporting_content_author_cards",
            "positive_negative_highlights": highlights,
            "top_authors": top_authors,
        },
        {
            "slide_no": 11,
            "section": "Scope & Methodology",
            "title": "SCOPE & METHODOLOGY",
            "subtitle": "Metric contract, limitations, and audit note",
            "layout": "sources_notes_clean",
            "scope": {
                "project": context.get("project_name"),
                "period": period,
                "client_brand": client,
                "competitors": competitors,
                "channels": context.get("channels"),
            },
            "metric_contract": [
                "SOV = content brand ÷ total content.",
                "SOE = interaction brand ÷ total interaction.",
                "Views dilaporkan terpisah dari interactions jika tersedia.",
                "Narrative/topic signal menggunakan classified sample dan harus dibaca sesuai coverage.",
            ],
            "data_health": data_health,
            "limitations": limitations + ([narrative_caveat] if narrative_caveat else []),
        },
    ]
    slides = [strip_client_visible_audit(slide) for slide in slides]
    outline = build_report_outline_from_id(report_input_id, allow_partial=allow_partial)
    evidence_rows = _ca_all_evidence_rows(report_input, brands)
    evidence_registry = {
        f"E{idx+1:02d}": {
            "audit_evidence_id": f"E{idx+1:02d}",
            "source_url": row.get("source_url") or row.get("url") or row.get("link_url"),
            "content": _clean(row.get("content") or row.get("title"), 200),
            "brand": _row_brand(row),
            "channel": _clean(row.get("channel")),
        }
        for idx, row in enumerate(evidence_rows[:80])
    }
    package = {
        "success": True,
        "report_type_id": REPORT_TYPE_ID,
        "render_package_version": RENDER_PACKAGE_VERSION,
        "quality_upgrade": "v4_strategic_qa_concentration_and_evidence_alignment",
        "package_id": _now_id("pkg_ca"),
        "report_input_id": report_input_id,
        "outline_id": outline.get("outline_id"),
        "outline_status": outline.get("outline_status"),
        "audience_context": audience,
        "context": context,
        "client_brand": client,
        "competitor_brands": competitors,
        "section_order_policy": "Action Plan First blueprint preserved; concentration check is attached to Competitive Landscape Evidence.",
        "slides": slides,
        "evidence_link_policy": {
            "main_slides": "Use natural clickable labels: Lihat post, Lihat komentar, Buka artikel. Do not render audit IDs or raw URLs as visible text.",
            "audit": "Audit identifiers and URLs remain available in evidence_registry/export data, not as client-facing labels.",
        },
        "ppt_style_brief": {
            "tone": audience.get("tone"),
            "visual_direction": "client-facing consulting deck, action-plan-first, concentration-aware, natural evidence CTAs",
            "avoid": ["visible E01/T09/P06 style evidence codes", "raw URL text", "internal taxonomy/debug wording", "recommendations without rationale", "reading one viral post as systemic dominance"],
            "preferred_components": ["decision cards", "action plan cards", "concentration check", "benchmark matrix", "natural hyperlink buttons", "content cards"],
        },
        "evidence_registry": evidence_registry,
        "topic_coverage_policy": topic_coverage,
        "claude_guardrails": [
            "Follow the section order in slides; do not invent new main sections outside the Action-Plan-First blueprint.",
            "If extra slides are needed, keep them under their parent section label.",
            "Render evidence links as natural clickable text only: Lihat post, Lihat komentar, or Buka artikel.",
            "Do not display audit IDs such as E01/T09/P06 on client-facing slides.",
            "Do not print raw URLs on client-facing slides.",
            "Do not show internal wording such as raw Topic Extraction policy, evidence registry, or URL appendix instructions.",
            "Use directional wording when topic coverage is low.",
            "When one post contributes a high share of a brand's engagement, state it as concentration risk rather than systemic brand advantage.",
        ],
    }
    package["quality_checks"] = {
        "evidence_integrity": validate_competitive_analysis_render_package(package),
        "client_facing_policy": validate_client_facing_presentation_package(package, report_type="competitive_analysis"),
        "strategic_qa": validate_ca_strategic_qa(package),
    }
    return package


def validate_ca_strategic_qa(package: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    slides = package.get("slides") or []
    action_slide = next((slide for slide in slides if isinstance(slide, Mapping) and slide.get("section") == "Competitive Action Plan"), {})
    cards = action_slide.get("cards") or []
    if isinstance(cards, list):
        for card in cards:
            if not isinstance(card, Mapping):
                continue
            text = " ".join(_clean(v) for v in card.values() if isinstance(v, str))
            if "SOV 0,0%" in text or "SOE 0,0%" in text:
                errors.append("Action Plan contains zero SOV/SOE fallback despite available brand metrics.")
            if card.get("action_type") == "Mitigate Competitive Risk":
                ev = card.get("supporting_evidence") or {}
                if isinstance(ev, Mapping) and _clean(ev.get("sentiment")).casefold() not in {"negative", "negatif"}:
                    errors.append("Mitigate Competitive Risk evidence must use negative evidence, not top positive/neutral evidence.")
    concentration_slide = next((slide for slide in slides if isinstance(slide, Mapping) and slide.get("title") == "CONCENTRATION CHECK"), None)
    if not concentration_slide:
        errors.append("Missing concentration check slide under Competitive Landscape Evidence.")
    visible = str(slides).casefold()
    for phrase in ("unclassified / needs llm", "needs llm", "evidence id", "url lengkap"):
        if phrase in visible:
            errors.append(f"Client-facing payload leaks internal wording: {phrase}")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}
