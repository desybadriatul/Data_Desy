"""
Task 2 report-outline builder for Cogan.

This module turns a frozen Task 1 `report_input_v1` package into a structured
report-render plan based on the Action-Plan-First registry. It does NOT write
headlines, recommendations, Action Plan rows, or slides. Those are later Task 2
generation/rendering responsibilities.

The outline tells later steps:
- locked section order;
- which Task 1 view(s) may support each section;
- whether each source view is READY, N_A, NOT_AVAILABLE, EMPTY, or MISSING;
- action-plan taxonomy allowed for this report type;
- warnings/limitations that must be respected during narration.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from reporting.contracts.report_input_contract_v1 import (
    validate_report_input_shape,
)
from reporting.registry.registry_loader import (
    RegistryError,
    get_action_taxonomy,
    get_report_type_definition,
    get_section_input_mappings,
    get_sections,
)
from reporting.validators.report_input_validator import (
    validate_report_input,
)


OUTLINE_VERSION = "report_outline_v1"

VIEW_STATE_READY = "READY"
VIEW_STATE_NA = "N_A"
VIEW_STATE_NOT_AVAILABLE = "NOT_AVAILABLE"
VIEW_STATE_EMPTY = "EMPTY"
VIEW_STATE_MISSING = "MISSING"

RENDER_DECISION_RENDER = "RENDER"
RENDER_DECISION_RENDER_WITH_LIMITATIONS = "RENDER_WITH_LIMITATIONS"
RENDER_DECISION_RENDER_NA = "RENDER_NA"
RENDER_DECISION_STRUCTURAL_ONLY = "STRUCTURAL_ONLY"
RENDER_DECISION_BLOCKED = "BLOCKED"


class ReportOutlineError(RuntimeError):
    """Raised when Task 2 cannot create a safe render plan from Task 1 output."""


def _require_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReportOutlineError(
            f"'{field_name}' wajib berupa string yang tidak kosong."
        )
    return value.strip()


def _ordered_unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


def _title_key(value: str) -> str:
    """Use exact normalized titles only; no fuzzy matching is allowed."""
    return " ".join(value.casefold().strip().split())


def _create_outline_id(report_input_id: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"ro_{report_input_id}_{timestamp}_{uuid4().hex[:8]}"


def _get_view(
    report_input: Mapping[str, Any],
    view_id: str,
) -> tuple[str | None, Mapping[str, Any] | None]:
    """Locate a view in the Task 1 package and return its type + wrapper."""
    quantitative = report_input.get("quantitative_views")
    if isinstance(quantitative, Mapping) and view_id in quantitative:
        value = quantitative[view_id]
        return "quantitative", value if isinstance(value, Mapping) else None

    qualitative = report_input.get("qualitative_views")
    if isinstance(qualitative, Mapping) and view_id in qualitative:
        value = qualitative[view_id]
        return "qualitative", value if isinstance(value, Mapping) else None

    return None, None


def _inspect_view_availability(
    report_input: Mapping[str, Any],
    view_id: str,
) -> dict[str, Any]:
    """Summarize render readiness for one declared source view."""
    view_type, view = _get_view(report_input, view_id)

    if view is None:
        return {
            "view_id": view_id,
            "view_type": view_type,
            "state": VIEW_STATE_MISSING,
            "row_count": 0,
            "reason": "View tidak ada pada report input package.",
        }

    rows = view.get("rows")
    row_count = len(rows) if isinstance(rows, list) else 0
    metadata = view.get("metadata")
    metadata = metadata if isinstance(metadata, Mapping) else {}

    raw_status = metadata.get("status", VIEW_STATE_READY)
    declared_status = (
        raw_status.strip().upper()
        if isinstance(raw_status, str) and raw_status.strip()
        else "INVALID"
    )
    reason = metadata.get("reason")
    reason = reason.strip() if isinstance(reason, str) and reason.strip() else None

    if declared_status in {VIEW_STATE_NA, VIEW_STATE_NOT_AVAILABLE}:
        state = declared_status
    elif declared_status == VIEW_STATE_READY and row_count > 0:
        state = VIEW_STATE_READY
    elif declared_status == VIEW_STATE_READY and row_count == 0:
        state = VIEW_STATE_EMPTY
        reason = reason or (
            "View bertanda READY tetapi tidak memiliki rows."
        )
    else:
        state = VIEW_STATE_EMPTY
        reason = reason or (
            f"metadata.status '{declared_status}' tidak dapat dirender."
        )

    return {
        "view_id": view_id,
        "view_type": view_type,
        "state": state,
        "row_count": row_count,
        "reason": reason,
        "metadata": deepcopy(dict(metadata)),
    }


def _decide_section_render(
    *,
    architecture_role: str,
    view_availability: list[Mapping[str, Any]],
) -> str:
    """Make a conservative render decision without inventing evidence."""
    if not view_availability:
        if architecture_role in {"header", "footer_or_scope"}:
            return RENDER_DECISION_STRUCTURAL_ONLY
        return RENDER_DECISION_RENDER_WITH_LIMITATIONS

    states = {item["state"] for item in view_availability}

    if states == {VIEW_STATE_READY}:
        return RENDER_DECISION_RENDER

    if VIEW_STATE_READY in states:
        return RENDER_DECISION_RENDER_WITH_LIMITATIONS

    if states & {
        VIEW_STATE_NA,
        VIEW_STATE_NOT_AVAILABLE,
        VIEW_STATE_EMPTY,
        VIEW_STATE_MISSING,
    }:
        return RENDER_DECISION_RENDER_NA

    return RENDER_DECISION_RENDER_WITH_LIMITATIONS


def _build_exact_mapping_index(
    mappings: Iterable[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Index only exact section-title mappings from the registry."""
    index: dict[str, list[dict[str, Any]]] = {}
    for mapping in mappings:
        section_title = mapping.get("section_title")
        if not isinstance(section_title, str) or not section_title.strip():
            continue
        index.setdefault(_title_key(section_title), []).append(
            deepcopy(dict(mapping))
        )
    return index


def _section_view_ids(
    section: Mapping[str, Any],
    exact_mappings: Iterable[Mapping[str, Any]],
) -> tuple[list[str], list[str]]:
    """
    Return direct views and exact title-mapped views in preserved registry order.

    The registry has a few combined evidence blocks, such as "Top Authors &
    Content". These remain in `evidence_blocks` below rather than being
    guessed/fuzzily assigned to a single section.
    """
    direct = _ordered_unique(
        list(section.get("depends_on_quantitative_inputs", []))
        + list(section.get("depends_on_qualitative_inputs", []))
    )

    mapped: list[str] = []
    for mapping in exact_mappings:
        mapped.extend(mapping.get("source_inputs", []))

    return direct, _ordered_unique(mapped)


def _build_evidence_blocks(
    report_input: Mapping[str, Any],
    mappings: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """
    Keep registered grouped mappings intact, even when they do not map one-to-one
    to a section title. This prevents Task 2 from making unsafe fuzzy matches.
    """
    blocks: list[dict[str, Any]] = []

    for mapping in mappings:
        copied = deepcopy(dict(mapping))
        source_views = _ordered_unique(copied.get("source_inputs", []))
        availability = [
            _inspect_view_availability(report_input, view_id)
            for view_id in source_views
        ]
        blocks.append(
            {
                "section_title": copied.get("section_title"),
                "output_need": copied.get("output_need"),
                "source_view_ids": source_views,
                "source_view_availability": availability,
                "implementation_notes": copied.get("implementation_notes"),
                "uses_all_quantitative": bool(
                    copied.get("uses_all_quantitative", False)
                ),
            }
        )

    return blocks


def _load_report_input_from_store(report_input_id: str) -> dict[str, Any]:
    """Read a frozen Task 1 package lazily to avoid requiring DB for imports."""
    report_input_id = _require_text(report_input_id, "report_input_id")
    try:
        from reporting.storage.report_input_store import get_report_input
    except ImportError as exc:
        raise ReportOutlineError(
            "Storage report input belum tersedia."
        ) from exc

    package = get_report_input(report_input_id)
    if package is None:
        raise ReportOutlineError(
            f"report_input_id '{report_input_id}' tidak ditemukan."
        )
    return package


def build_report_outline(
    report_input: Mapping[str, Any],
    *,
    registry_dir: str | Path | None = None,
    allow_partial: bool = True,
) -> dict[str, Any]:
    """
    Build a registry-grounded Task 2 render plan from a Task 1 package.

    PASS packages yield a READY outline. PARTIAL_PASS packages are allowed by
    default but retain limitations and section-level N/A decisions. FAIL packages
    are blocked because Task 2 must not fabricate a report from invalid input.
    """
    contract_errors = validate_report_input_shape(report_input)
    if contract_errors:
        raise ReportOutlineError(
            "Report input tidak sesuai shared contract: "
            + " | ".join(contract_errors)
        )

    report_type_id = _require_text(
        report_input.get("report_type_id"),
        "report_type_id",
    )
    report_input_id = _require_text(
        report_input.get("report_input_id"),
        "report_input_id",
    )

    validation_result = validate_report_input(
        report_input,
        registry_dir=registry_dir,
    )
    validation_status = validation_result["status"]

    if validation_status == "FAIL":
        raise ReportOutlineError(
            "Task 1 report input FAIL dan tidak boleh diteruskan ke Task 2: "
            + " | ".join(validation_result["errors"])
        )
    if validation_status == "PARTIAL_PASS" and not allow_partial:
        raise ReportOutlineError(
            "Task 1 report input PARTIAL_PASS. Lengkapi data/view terlebih "
            "dahulu atau jalankan dengan allow_partial=True."
        )

    try:
        definition = get_report_type_definition(
            report_type_id,
            registry_dir=registry_dir,
        )
        sections = get_sections(report_type_id, registry_dir=registry_dir)
        action_taxonomy = get_action_taxonomy(
            report_type_id,
            registry_dir=registry_dir,
        )
        section_mappings = get_section_input_mappings(
            report_type_id,
            registry_dir=registry_dir,
        )
    except RegistryError as exc:
        raise ReportOutlineError(
            f"Gagal membaca blueprint report '{report_type_id}': {exc}"
        ) from exc

    action_plan_indexes = [
        index
        for index, section in enumerate(sections)
        if section.get("architecture_role") == "action_plan"
    ]
    if action_plan_indexes != [2]:
        raise ReportOutlineError(
            "Registry tidak memenuhi Action-Plan-First: Action Plan harus "
            "menjadi section ke-3."
        )

    mapping_index = _build_exact_mapping_index(section_mappings)
    section_plans: list[dict[str, Any]] = []
    unmapped_evidence_sections: list[str] = []

    for position, section in enumerate(sections, start=1):
        section_title = _require_text(section.get("title"), "section.title")
        exact_mappings = mapping_index.get(_title_key(section_title), [])
        direct_view_ids, mapped_view_ids = _section_view_ids(
            section,
            exact_mappings,
        )
        source_view_ids = _ordered_unique(direct_view_ids + mapped_view_ids)
        availability = [
            _inspect_view_availability(report_input, view_id)
            for view_id in source_view_ids
        ]

        architecture_role = section.get("architecture_role", "")
        render_decision = _decide_section_render(
            architecture_role=architecture_role,
            view_availability=availability,
        )

        if (
            not source_view_ids
            and architecture_role not in {"header", "footer_or_scope"}
            and not exact_mappings
        ):
            unmapped_evidence_sections.append(section["section_id"])

        section_plans.append(
            {
                "position": position,
                "section_id": section["section_id"],
                "title": section_title,
                "architecture_role": architecture_role,
                "component_type": section.get("component_type"),
                "required": bool(section.get("required", False)),
                "purpose": section.get("purpose"),
                "render_decision": render_decision,
                "source_assignment": {
                    "direct_view_ids": direct_view_ids,
                    "exact_section_mapping_view_ids": mapped_view_ids,
                    "source_view_ids": source_view_ids,
                    "exact_registry_mapping_found": bool(exact_mappings),
                },
                "source_view_availability": availability,
                "registry_instructions": {
                    "must_include": deepcopy(section.get("must_include", [])),
                    "visuals": deepcopy(section.get("visuals", [])),
                    "tables": deepcopy(section.get("tables", [])),
                    "narrative_rules": deepcopy(
                        section.get("narrative_rules", [])
                    ),
                    "fallback_behavior": section.get("fallback_behavior"),
                    "implementation_notes": section.get(
                        "implementation_notes"
                    ),
                },
                "action_plan_rules": (
                    {
                        "allowed_action_types": deepcopy(action_taxonomy),
                        "must_be_evidence_backed": True,
                    }
                    if architecture_role == "action_plan"
                    else None
                ),
            }
        )

    outline_warnings = list(validation_result["warnings"])
    if unmapped_evidence_sections:
        outline_warnings.append(
            "Section evidence berikut belum memiliki direct/exact mapping. "
            "Gunakan `evidence_blocks` registry; jangan membuat fuzzy mapping: "
            + ", ".join(unmapped_evidence_sections)
        )

    task1_limitations = report_input.get("limitations", [])
    if not isinstance(task1_limitations, list):
        task1_limitations = []

    context = report_input.get("context")
    context_copy = deepcopy(dict(context)) if isinstance(context, Mapping) else {}

    return {
        "outline_version": OUTLINE_VERSION,
        "outline_id": _create_outline_id(report_input_id),
        "report_input_id": report_input_id,
        "report_type_id": report_type_id,
        "registry_version": definition.get("registry_version")
        or report_input.get("registry_version"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "context": context_copy,
        "task1_validation": {
            "status": validation_status,
            "missing_views": deepcopy(validation_result["missing_views"]),
            "warnings": deepcopy(validation_result["warnings"]),
            "errors": deepcopy(validation_result["errors"]),
        },
        "outline_status": (
            "READY"
            if validation_status == "PASS"
            else "READY_WITH_LIMITATIONS"
        ),
        "architecture": {
            "pattern": "Header -> Executive Summary -> Action Plan -> Evidence -> Footer",
            "action_plan_position": 3,
            "action_plan_first": True,
            "action_plan_taxonomy": deepcopy(action_taxonomy),
        },
        "sections": section_plans,
        "evidence_blocks": _build_evidence_blocks(
            report_input,
            section_mappings,
        ),
        "limitations": deepcopy(task1_limitations),
        "warnings": _ordered_unique(outline_warnings),
        "task2_boundary": {
            "this_module_does": [
                "lock section order",
                "assign registry-declared Task 1 source views",
                "mark N/A or missing source visibility",
            ],
            "this_module_does_not": [
                "write final Executive Summary",
                "write final Action Plan rows",
                "invent metrics, links, quotes, or recommendations",
                "render slides or HTML",
            ],
        },
    }


def build_report_outline_from_id(
    report_input_id: str,
    *,
    registry_dir: str | Path | None = None,
    allow_partial: bool = True,
) -> dict[str, Any]:
    """
    Build a Task 2 outline from a stored report_input_id.
    """
    package = _load_report_input_from_store(report_input_id)
    return build_report_outline(
        package,
        registry_dir=registry_dir,
        allow_partial=allow_partial,
    )


def get_outline_section(
    outline: Mapping[str, Any],
    section_id: str,
) -> dict[str, Any] | None:
    """Return one section plan by stable section_id."""
    section_id = _require_text(section_id, "section_id")
    sections = outline.get("sections")

    if not isinstance(sections, list):
        raise ReportOutlineError("outline.sections harus berupa list.")

    for section in sections:
        if isinstance(section, Mapping) and section.get("section_id") == section_id:
            return deepcopy(dict(section))

    return None


__all__ = [
    "OUTLINE_VERSION",
    "RENDER_DECISION_BLOCKED",
    "RENDER_DECISION_RENDER",
    "RENDER_DECISION_RENDER_NA",
    "RENDER_DECISION_RENDER_WITH_LIMITATIONS",
    "RENDER_DECISION_STRUCTURAL_ONLY",
    "ReportOutlineError",
    "VIEW_STATE_EMPTY",
    "VIEW_STATE_MISSING",
    "VIEW_STATE_NA",
    "VIEW_STATE_NOT_AVAILABLE",
    "VIEW_STATE_READY",
    "build_report_outline",
    "build_report_outline_from_id",
    "get_outline_section",
]
