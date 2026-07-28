"""Task 2 preview and PPT-ready package builder for EVO."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from reporting.storage.report_input_store import get_report_input


REPORT_TYPE_ID = "evo_perception_intelligence"
PREVIEW_VERSION = "evo_data_preview_v1"
PACKAGE_VERSION = "evo_ppt_package_v1"
ACTION_TYPES = ("Scale", "Fix", "Protect", "Build", "Test", "Monitor", "Avoid")


class EVORendererError(RuntimeError):
    """Raised when a frozen EVO report input cannot be rendered safely."""


def _clean(value: Any, limit: int | None = None) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit] if limit else text


def _load(report_input_id: str) -> dict[str, Any]:
    report_input = get_report_input(report_input_id)
    if report_input is None:
        raise EVORendererError(f"report_input_id '{report_input_id}' tidak ditemukan.")
    if report_input.get("report_type_id") != REPORT_TYPE_ID:
        raise EVORendererError("report_input_id bukan paket EVO.")
    return report_input


def _view(report_input: Mapping[str, Any], view_id: str) -> dict[str, Any]:
    for key in ("quantitative_views", "qualitative_views"):
        value = (report_input.get(key) or {}).get(view_id)
        if isinstance(value, Mapping):
            return dict(value)
    return {}


def _rows(report_input: Mapping[str, Any], view_id: str) -> list[dict[str, Any]]:
    rows = _view(report_input, view_id).get("rows")
    return [dict(row) for row in rows] if isinstance(rows, list) else []


def _markdown_table(rows: list[dict[str, Any]], columns: list[str], limit: int = 12) -> str:
    if not rows:
        return "_N/A — data tidak tersedia._"
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows[:limit]:
        body.append(
            "| "
            + " | ".join(_clean(row.get(column), 100).replace("|", "/") or "N/A" for column in columns)
            + " |"
        )
    return "\n".join([header, divider, *body])


def build_evo_report_data_preview(
    report_input_id: str,
    *,
    allow_partial: bool = True,
) -> dict[str, Any]:
    report_input = _load(report_input_id)
    validation = dict(report_input.get("validation") or {})
    status = str(validation.get("status") or "UNKNOWN")
    if status == "FAIL" or (status == "PARTIAL_PASS" and not allow_partial):
        raise EVORendererError(
            f"Report input berstatus {status}; allow_partial diperlukan untuk preview."
        )

    context = dict(report_input.get("context") or {})
    period = dict(context.get("period") or {})
    brand_summary = _rows(report_input, "qt_evo_brand_summary")
    driver_rows = _rows(report_input, "qt_evo_driver_scorecard")
    focus_brand = context.get("client_brand") or context.get("project_name")
    attribute_rows = [
        row
        for row in _rows(report_input, "qt_evo_attribute_scorecard")
        if str(row.get("Brand") or "").casefold() == str(focus_brand or "").casefold()
    ]
    journey_rows = _rows(report_input, "qt_evo_journey_matrix")
    evidence_rows = _rows(report_input, "ql_evo_evidence_cards")
    recommendation_rows = _rows(report_input, "ql_evo_recommendation_inputs")
    evo = dict(report_input.get("evo") or {})
    audit = dict(evo.get("classification_audit") or {})

    markdown = f"""# EVO Perception Intelligence Preview — {focus_brand}

**Period:** {period.get('start_date')} → {period.get('end_date')}
**Validation:** {status}
**Tagged population:** {audit.get('sampled_total', 'N/A')} / {audit.get('population_total', 'N/A')}
**Coverage:** {audit.get('population_coverage_pct', 'N/A')}%

## Brand EVOScore

{_markdown_table(brand_summary, ['Brand', 'EVOScore', 'Score Band Label', 'Total Tagged Posts', 'Confidence'])}

## Driver Scorecard

{_markdown_table(driver_rows, ['Brand', 'Driver', 'EVO Share %', 'Net Sentiment', 'Sentiment Index', 'Virality Index', 'Total Driver Score', 'Score Band Label'])}

## Focus-brand Attribute Gap

{_markdown_table(attribute_rows, ['Attribute', 'Driver', 'Posts', 'Attribute Score', 'Best Brand', 'Best Brand Score', 'Attribute Gap', 'Whitespace', 'Confidence'])}

## Perception Journey

{_markdown_table(journey_rows, ['Brand', 'Awareness', 'Engagement', 'Perception Impact'])}

## Proposed Moves

{_markdown_table(recommendation_rows, ['Priority', 'Move Type', 'Attribute', 'Rationale', 'Evidence Status'])}

## Evidence Sample

{_markdown_table(evidence_rows, ['Brand', 'Issue', 'Attribute', 'Sentiment', 'Content', 'Interactions', 'Source URL'], 10)}
"""
    return {
        "success": True,
        "preview_version": PREVIEW_VERSION,
        "report_input_id": report_input_id,
        "report_type_id": REPORT_TYPE_ID,
        "readiness": "READY" if status == "PASS" else "READY_WITH_LIMITATIONS",
        "context": context,
        "classification_audit": audit,
        "metric_manifest": deepcopy(evo.get("metric_manifest") or {}),
        "component_completeness_forecast": deepcopy(
            evo.get("component_completeness_audit") or {}
        ),
        "brand_summary": brand_summary,
        "driver_scorecard": driver_rows,
        "attribute_gap_preview": attribute_rows,
        "journey_preview": journey_rows,
        "recommendation_preview": recommendation_rows,
        "evidence_preview": evidence_rows[:10],
        "limitations": list(report_input.get("limitations") or []),
        "markdown": markdown,
    }


def _table(
    title: str,
    rows: list[dict[str, Any]],
    columns: list[str],
    *,
    limit: int = 12,
) -> dict[str, Any]:
    return {
        "type": "table",
        "title": title,
        "columns": columns,
        "rows": [
            {column: row.get(column) for column in columns}
            for row in rows[:limit]
        ],
        "status": "READY" if rows else "N/A",
    }


def _bullets(title: str, items: list[str]) -> dict[str, Any]:
    clean = [_clean(item, 260) for item in items if _clean(item)]
    return {
        "type": "bullets",
        "title": title,
        "items": clean or ["N/A — bukti belum cukup."],
        "status": "READY" if clean else "N/A",
    }


def validate_evo_render_package(
    *,
    focus_brand: str,
    brand_summary: list[dict[str, Any]],
    driver_rows: list[dict[str, Any]],
    focus_attribute_rows: list[dict[str, Any]],
    evidence_rows: list[dict[str, Any]],
    move_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    focus_key = _clean(focus_brand).casefold()

    for row in focus_attribute_rows:
        if _clean(row.get("Best Brand")).casefold() == focus_key:
            errors.append(
                f"Best Brand includes focus brand for {row.get('Attribute ID')}."
            )

    allowed_moves = set(ACTION_TYPES)
    invalid_moves = sorted(
        {
            _clean(row.get("Move Type"))
            for row in move_rows
            if _clean(row.get("Move Type")) not in allowed_moves
        }
    )
    if invalid_moves:
        errors.append("Invalid EVO move types: " + ", ".join(invalid_moves))

    for row in brand_summary:
        score = row.get("EVOScore")
        band = _clean(row.get("Score Band"))
        if score is None:
            continue
        expected = "underperform" if float(score) < 90 else "on_par" if float(score) <= 110 else "outperform"
        if band != expected:
            errors.append(
                f"Score-band mismatch for {row.get('Brand')}: {score} -> {band}."
            )

    by_brand: dict[str, list[dict[str, Any]]] = {}
    for row in driver_rows:
        by_brand.setdefault(_clean(row.get("Brand")), []).append(row)
    for brand, rows in by_brand.items():
        shares = [row.get("EVO Share %") for row in rows if row.get("EVO Share %") is not None]
        if shares and abs(sum(float(value) for value in shares) - 100.0) > 0.11:
            errors.append(f"EVO Share does not reconcile to 100% for {brand}.")

    missing_links = [
        row for row in evidence_rows
        if _clean(row.get("Content")) and not _clean(row.get("Source URL"))
    ]
    if missing_links:
        errors.append(
            f"{len(missing_links)} evidence rows have content but no source URL."
        )
    if not evidence_rows:
        warnings.append("No client-facing EVO evidence rows are available.")

    return {
        "status": "FAIL" if errors else "PASS",
        "errors": errors,
        "warnings": warnings,
        "checks": [
            "row-level attribute source lock",
            "focus-brand Best Brand exclusion",
            "score-band boundaries",
            "E/V/O share reconciliation",
            "recommendation vocabulary",
            "evidence traceability",
        ],
    }


def build_evo_report_package(
    report_input_id: str,
    *,
    audience_context: str | None = None,
    audience_pov: str | None = None,
) -> dict[str, Any]:
    report_input = _load(report_input_id)
    preview = build_evo_report_data_preview(report_input_id, allow_partial=True)
    context = dict(report_input.get("context") or {})
    period = dict(context.get("period") or {})
    focus_brand = context.get("client_brand") or context.get("project_name")
    competitors = list(context.get("competitor_brands") or [])
    scope = dict(report_input.get("scope") or {})

    brand_summary = _rows(report_input, "qt_evo_brand_summary")
    drivers = _rows(report_input, "qt_evo_driver_scorecard")
    attributes = _rows(report_input, "qt_evo_attribute_scorecard")
    journey = _rows(report_input, "qt_evo_journey_matrix")
    evidence = _rows(report_input, "ql_evo_evidence_cards")
    moves = _rows(report_input, "ql_evo_recommendation_inputs")
    focus_attributes = [
        row for row in attributes
        if str(row.get("Brand") or "").casefold() == str(focus_brand or "").casefold()
    ]
    priority_moves = sorted(
        moves,
        key=lambda row: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(str(row.get("Priority")), 3),
    )
    desired = scope.get("desired_perception") or "Belum dikonfirmasi"
    question = scope.get("analysis_objective") or (
        f"Atribut persepsi apa yang perlu dibangun, diperbaiki, atau dilindungi oleh {focus_brand}?"
    )

    slides = [
        {
            "slide_id": "evo_01_identity",
            "section": "Decision Frame & Report Identity",
            "title": f"EVO Perception Intelligence — {focus_brand}",
            "subtitle": f"{period.get('start_date')} → {period.get('end_date')}",
            "components": [
                _bullets("Decision frame", [
                    f"Business question: {question}",
                    f"Desired perception: {desired}",
                    f"Primary reader: {audience_context or audience_pov or scope.get('primary_reader') or 'N/A'}",
                    f"Benchmark: {', '.join(competitors) or 'single-brand diagnosis'}",
                ])
            ],
        },
        {
            "slide_id": "evo_02_executive_answer",
            "section": "Executive Summary",
            "title": "Perception strength is visible only when tone and amplification agree",
            "subtitle": "Category-centred scorecard",
            "components": [
                _table(
                    "Brand EVOScore",
                    brand_summary,
                    ["Brand", "EVOScore", "Score Band Label", "Total Tagged Posts", "Confidence"],
                ),
                _bullets(
                    "Decision implications",
                    [
                        f"{row.get('Priority')} — {row.get('Move Type')} {row.get('Attribute')}: {row.get('Rationale')}"
                        for row in priority_moves[:3]
                    ],
                ),
            ],
        },
        {
            "slide_id": "evo_03_action_plan",
            "section": "Perception-Building Action Plan",
            "title": "Move the attributes with the clearest evidence and largest gap first",
            "subtitle": "Scale / Fix / Protect / Build / Test / Monitor / Avoid",
            "components": [
                _table(
                    "Attribute action portfolio",
                    priority_moves,
                    [
                        "Priority",
                        "Move Type",
                        "Attribute",
                        "Driver",
                        "Rationale",
                        "Evidence Status",
                        "Smallest Next Step",
                    ],
                    limit=18,
                )
            ],
        },
        {
            "slide_id": "evo_04_driver_landscape",
            "section": "Driver & Attribute Diagnosis",
            "title": "The E/V/O mix shows what currently carries each brand's meaning",
            "subtitle": "Experience / Values / Offer",
            "components": [
                _table(
                    "Driver scorecard",
                    drivers,
                    [
                        "Brand",
                        "Driver",
                        "EVO Share %",
                        "Net Sentiment",
                        "Sentiment Index",
                        "Virality Index",
                        "Total Driver Score",
                        "Score Band Label",
                    ],
                    limit=24,
                )
            ],
        },
        {
            "slide_id": "evo_05_attribute_gap",
            "section": "Driver & Attribute Diagnosis",
            "title": "Benchmark gaps identify where the focus brand can learn or build",
            "subtitle": "Best Brand excludes the focus brand",
            "components": [
                _table(
                    "Focus-brand attribute scoreboard",
                    focus_attributes,
                    [
                        "Attribute",
                        "Driver",
                        "Posts",
                        "Attribute Score",
                        "Best Brand",
                        "Best Brand Score",
                        "Attribute Gap",
                        "Whitespace",
                        "Confidence",
                    ],
                    limit=24,
                )
            ],
        },
        {
            "slide_id": "evo_06_journey",
            "section": "Perception Journey",
            "title": "Perception moves only when visibility becomes response and external meaning",
            "subtitle": "Awareness → Engagement → Perception Impact",
            "components": [
                _table(
                    "Comparative journey matrix",
                    journey,
                    ["Brand", "Awareness", "Engagement", "Perception Impact", "Basis"],
                )
            ],
        },
        {
            "slide_id": "evo_07_evidence",
            "section": "Evidence & Methodology",
            "title": "These posts carry the strongest traceable perception evidence",
            "subtitle": "Real content → issue → attribute → implication",
            "components": [
                _table(
                    "Evidence cards",
                    evidence,
                    [
                        "Brand",
                        "Issue",
                        "Attribute",
                        "Driver",
                        "Sentiment",
                        "Content",
                        "Interactions",
                        "Views",
                        "Source URL",
                    ],
                    limit=12,
                )
            ],
        },
        {
            "slide_id": "evo_08_measurement",
            "section": "Decision & Measurement",
            "title": "Measure perception movement before claiming business impact",
            "subtitle": "Perception measurement contract",
            "components": [
                _bullets("Measure", [
                    "Attribute Share and Attribute Net Sentiment.",
                    "Attribute Score and benchmark gap.",
                    "Organic evidence share and source-role diversity.",
                    "Recurring criticism and earned validation.",
                    "Treat sales, conversion, retention, and ROI as Hypothesis until external data validates them.",
                ]),
                _bullets("Stop / Start / Measure / Owner", [
                    "Stop: broad messaging that does not resolve a priority attribute.",
                    "Start: the highest-priority evidence-backed intervention.",
                    "Measure: repeat the same attribute map and score formula.",
                    f"Owner: {audience_context or audience_pov or scope.get('primary_reader') or 'assign before activation'}.",
                ]),
            ],
        },
        {
            "slide_id": "evo_09_scope",
            "section": "Evidence & Methodology",
            "title": "Scope, confidence, and limitations remain visible",
            "subtitle": "Methodology and evidence integrity",
            "components": [
                _bullets("Scope", [
                    f"Focus brand: {focus_brand}",
                    f"Competitors: {', '.join(competitors) or 'N/A'}",
                    f"Period: {period.get('start_date')} → {period.get('end_date')}",
                    "Metric basis: canonical unique tagged posts.",
                    "Attribute Score: count-based sentiment point (0–100).",
                ]),
                _bullets(
                    "Limitations",
                    [str(item) for item in report_input.get("limitations") or []],
                ),
            ],
        },
    ]

    evo_gate = validate_evo_render_package(
        focus_brand=str(focus_brand or ""),
        brand_summary=brand_summary,
        driver_rows=drivers,
        focus_attribute_rows=focus_attributes,
        evidence_rows=evidence,
        move_rows=moves,
    )
    package = {
        "success": True,
        "package_version": PACKAGE_VERSION,
        "report_input_id": report_input_id,
        "report_type_id": REPORT_TYPE_ID,
        "audience_context": audience_context or audience_pov,
        "slides": slides,
        "data_preview": preview,
        "quality_checks": {"evo_perception_integrity": evo_gate},
        "audit_pack": {
            "evo_quality_report": evo_gate,
            "evo_component_completeness_audit": deepcopy(
                (report_input.get("evo") or {}).get("component_completeness_audit") or {}
            ),
            "evo_metric_manifest": deepcopy(
                (report_input.get("evo") or {}).get("metric_manifest") or {}
            ),
            "evo_classification_audit": deepcopy(
                (report_input.get("evo") or {}).get("classification_audit") or {}
            ),
        },
        "ppt_style_brief": {
            "format": "client-facing PPTX",
            "tone": "executive, evidence-first, perception-strategy",
            "structure": "FRAME → DIAGNOSE → EXPLAIN → JOURNEY → COMPETE → ACTIVATE → DECIDE",
            "must_follow": [
                "Never recompute frozen metrics in Task 2.",
                "Never present social listening as proof of sales or conversion.",
                "Keep Experience, Values, and Offer visually distinct.",
                "Use Underperform <90, On Par 90–110, Outperform >110.",
                "Best Brand must exclude the focus brand.",
                "Every evidence card must retain its source URL.",
            ],
        },
    }
    try:
        from reporting.task2.renderers.render_quality_gate import (
            apply_render_package_quality_gate,
        )

        package = apply_render_package_quality_gate(package, report_type=REPORT_TYPE_ID)
    except Exception:
        pass
    return package


__all__ = [
    "ACTION_TYPES",
    "EVORendererError",
    "PACKAGE_VERSION",
    "PREVIEW_VERSION",
    "REPORT_TYPE_ID",
    "build_evo_report_data_preview",
    "build_evo_report_package",
    "validate_evo_render_package",
]
