"""
Registry loader for Cogan Task 1 / Task 2.

The two JSON registries are the shared source of truth for:
- supported report types;
- report section order;
- required qt_* and ql_* logical input views;
- report-specific action taxonomy;
- minimum validation rules.

Builders must use this loader instead of hardcoding report requirements.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
from typing import Any


REPORT_TYPE_REGISTRY_FILENAME = (
    "report_type_registry.mvp.v2_2_action_plan_first.json"
)
DATA_INPUT_REGISTRY_FILENAME = (
    "data_input_registry.mvp.v2_2_action_plan_first.json"
)

EXPECTED_REPORT_TYPE_REGISTRY_NAME = "report_type_registry"
EXPECTED_DATA_INPUT_REGISTRY_NAME = "data_input_registry"

# reporting/registry/registry_loader.py -> repository root is parents[2]
DEFAULT_REGISTRIES_DIR = Path(__file__).resolve().parents[2] / "registries"


class RegistryError(RuntimeError):
    """Raised when registry files are missing, malformed, or inconsistent."""


def _require_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RegistryError(f"Registry field '{field_name}' harus berupa string.")
    return value.strip()


def _resolve_registry_dir(registry_dir: str | Path | None = None) -> Path:
    """Resolve registry folder, allowing an alternate folder for tests."""
    directory = Path(registry_dir) if registry_dir is not None else DEFAULT_REGISTRIES_DIR
    directory = directory.expanduser().resolve()

    if not directory.exists():
        raise RegistryError(
            f"Folder registries tidak ditemukan: {directory}"
        )
    if not directory.is_dir():
        raise RegistryError(
            f"Registry path harus folder, bukan file: {directory}"
        )

    return directory


def _load_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RegistryError(
            f"File registry tidak ditemukan: {path.name}. "
            "Pastikan kedua JSON berada di folder registries/."
        )

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise RegistryError(
            f"JSON registry tidak valid: {path.name} "
            f"(baris {exc.lineno}, kolom {exc.colno})."
        ) from exc
    except OSError as exc:
        raise RegistryError(
            f"Registry tidak dapat dibaca: {path.name}."
        ) from exc

    if not isinstance(data, dict):
        raise RegistryError(
            f"Root JSON {path.name} harus object/dictionary."
        )

    return data


def _list_view_ids(items: Any, field_name: str) -> set[str]:
    """Extract input_id values from registry requirement list."""
    if not isinstance(items, list):
        raise RegistryError(
            f"'{field_name}' harus berupa list pada registry."
        )

    result: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise RegistryError(
                f"{field_name}[{index}] harus berupa object."
            )

        input_id = _require_text(
            item.get("input_id"),
            f"{field_name}[{index}].input_id",
        )

        if input_id in result:
            raise RegistryError(
                f"Duplicate input_id '{input_id}' pada {field_name}."
            )
        result.add(input_id)

    return result


def _index_report_types(report_types: Any) -> dict[str, dict[str, Any]]:
    """Index report-type definitions and reject duplicate report_type_id."""
    if not isinstance(report_types, list) or not report_types:
        raise RegistryError(
            "'report_types' harus berupa list yang tidak kosong."
        )

    index: dict[str, dict[str, Any]] = {}

    for position, definition in enumerate(report_types):
        if not isinstance(definition, Mapping):
            raise RegistryError(
                f"report_types[{position}] harus berupa object."
            )

        report_type_id = _require_text(
            definition.get("report_type_id"),
            f"report_types[{position}].report_type_id",
        )

        if report_type_id in index:
            raise RegistryError(
                f"Duplicate report_type_id '{report_type_id}'."
            )

        index[report_type_id] = dict(definition)

    return index


def _validate_section_order(
    report_type_id: str,
    definition: Mapping[str, Any],
) -> None:
    """Ensure section_order points to actual sections in exactly one order."""
    section_order = definition.get("section_order")
    sections = definition.get("sections")

    if not isinstance(section_order, list) or not section_order:
        raise RegistryError(
            f"{report_type_id}.section_order harus list yang tidak kosong."
        )
    if not isinstance(sections, list) or not sections:
        raise RegistryError(
            f"{report_type_id}.sections harus list yang tidak kosong."
        )

    section_ids: list[str] = []
    for index, section in enumerate(sections):
        if not isinstance(section, Mapping):
            raise RegistryError(
                f"{report_type_id}.sections[{index}] harus object."
            )
        section_id = _require_text(
            section.get("section_id"),
            f"{report_type_id}.sections[{index}].section_id",
        )
        section_ids.append(section_id)

    if len(set(section_ids)) != len(section_ids):
        raise RegistryError(
            f"{report_type_id} memiliki duplicate section_id."
        )

    normalized_order = [
        _require_text(section_id, f"{report_type_id}.section_order")
        for section_id in section_order
    ]

    if len(set(normalized_order)) != len(normalized_order):
        raise RegistryError(
            f"{report_type_id}.section_order memiliki section ID ganda."
        )

    if normalized_order != section_ids:
        raise RegistryError(
            f"{report_type_id}: section_order harus sama dengan urutan "
            "section_id di sections."
        )

    # Action Plan First is a global non-negotiable rule.
    if len(sections) < 3 or sections[2].get("architecture_role") != "action_plan":
        raise RegistryError(
            f"{report_type_id}: Action Plan harus berada pada urutan 2."
        )


def _validate_registry_bundle(
    report_type_registry: Mapping[str, Any],
    data_input_registry: Mapping[str, Any],
) -> None:
    """Validate both registry files and their cross-file alignment."""
    report_registry_name = _require_text(
        report_type_registry.get("registry_name"),
        "report_type_registry.registry_name",
    )
    if report_registry_name != EXPECTED_REPORT_TYPE_REGISTRY_NAME:
        raise RegistryError(
            "registry_name report type tidak sesuai: "
            f"'{report_registry_name}'."
        )

    data_registry_name = _require_text(
        data_input_registry.get("registry_name"),
        "data_input_registry.registry_name",
    )
    if data_registry_name != EXPECTED_DATA_INPUT_REGISTRY_NAME:
        raise RegistryError(
            "registry_name data input tidak sesuai: "
            f"'{data_registry_name}'."
        )

    report_version = _require_text(
        report_type_registry.get("registry_version"),
        "report_type_registry.registry_version",
    )
    data_version = _require_text(
        data_input_registry.get("registry_version"),
        "data_input_registry.registry_version",
    )
    if report_version != data_version:
        raise RegistryError(
            "Versi dua registry harus sama. Ditemukan "
            f"report='{report_version}', data_input='{data_version}'."
        )

    report_type_index = _index_report_types(
        report_type_registry.get("report_types")
    )

    inputs_by_report_type = data_input_registry.get("inputs_by_report_type")
    if not isinstance(inputs_by_report_type, Mapping):
        raise RegistryError(
            "'inputs_by_report_type' harus berupa object/dictionary."
        )

    data_report_type_ids = set(inputs_by_report_type.keys())
    report_type_ids = set(report_type_index.keys())

    missing_in_data_registry = report_type_ids - data_report_type_ids
    if missing_in_data_registry:
        raise RegistryError(
            "Report type tidak memiliki data-input definition: "
            + ", ".join(sorted(missing_in_data_registry))
        )

    extra_in_data_registry = data_report_type_ids - report_type_ids
    if extra_in_data_registry:
        raise RegistryError(
            "Data-input registry memiliki report type yang tidak ada di "
            "report-type registry: "
            + ", ".join(sorted(extra_in_data_registry))
        )

    section_mappings = data_input_registry.get("section_mappings_by_report_type")
    if not isinstance(section_mappings, Mapping):
        raise RegistryError(
            "'section_mappings_by_report_type' harus berupa object/dictionary."
        )

    for report_type_id, definition in report_type_index.items():
        _validate_section_order(report_type_id, definition)

        input_definition = inputs_by_report_type.get(report_type_id)
        if not isinstance(input_definition, Mapping):
            raise RegistryError(
                f"Input definition '{report_type_id}' harus berupa object."
            )

        data_quantitative = _list_view_ids(
            input_definition.get("quantitative"),
            f"inputs_by_report_type.{report_type_id}.quantitative",
        )
        data_qualitative = _list_view_ids(
            input_definition.get("qualitative"),
            f"inputs_by_report_type.{report_type_id}.qualitative",
        )

        declared_quantitative = _list_view_ids(
            definition.get("required_quantitative_inputs"),
            f"report_types.{report_type_id}.required_quantitative_inputs",
        )
        declared_qualitative = _list_view_ids(
            definition.get("required_qualitative_inputs"),
            f"report_types.{report_type_id}.required_qualitative_inputs",
        )

        missing_quantitative = declared_quantitative - data_quantitative
        if missing_quantitative:
            raise RegistryError(
                f"{report_type_id}: quantitative view dideklarasikan tetapi "
                "tidak ada pada data_input_registry: "
                + ", ".join(sorted(missing_quantitative))
            )

        missing_qualitative = declared_qualitative - data_qualitative
        if missing_qualitative:
            raise RegistryError(
                f"{report_type_id}: qualitative view dideklarasikan tetapi "
                "tidak ada pada data_input_registry: "
                + ", ".join(sorted(missing_qualitative))
            )

        minimum_viable_inputs = definition.get("minimum_viable_inputs")
        if not isinstance(minimum_viable_inputs, list) or not minimum_viable_inputs:
            raise RegistryError(
                f"{report_type_id}.minimum_viable_inputs harus list tidak kosong."
            )

        available_views = data_quantitative | data_qualitative
        invalid_minimum_inputs = {
            _require_text(view_id, f"{report_type_id}.minimum_viable_inputs")
            for view_id in minimum_viable_inputs
        } - available_views
        if invalid_minimum_inputs:
            raise RegistryError(
                f"{report_type_id}: minimum_viable_inputs tidak ditemukan: "
                + ", ".join(sorted(invalid_minimum_inputs))
            )

        if report_type_id not in section_mappings:
            raise RegistryError(
                f"{report_type_id} tidak memiliki section mapping."
            )


@lru_cache(maxsize=8)
def _load_registry_bundle_cached(
    registry_dir_text: str,
) -> dict[str, dict[str, Any]]:
    """Load once per registry folder; callers receive deep copies."""
    registry_dir = Path(registry_dir_text)

    report_type_registry = _load_json_file(
        registry_dir / REPORT_TYPE_REGISTRY_FILENAME
    )
    data_input_registry = _load_json_file(
        registry_dir / DATA_INPUT_REGISTRY_FILENAME
    )

    _validate_registry_bundle(report_type_registry, data_input_registry)

    return {
        "report_type_registry": report_type_registry,
        "data_input_registry": data_input_registry,
    }


def load_registry_bundle(
    registry_dir: str | Path | None = None,
    *,
    refresh: bool = False,
) -> dict[str, dict[str, Any]]:
    """
    Load and validate the two registry JSON files.

    Returned data is deep-copied so individual builders cannot accidentally
    mutate shared cached registry data.
    """
    resolved_dir = _resolve_registry_dir(registry_dir)

    if refresh:
        _load_registry_bundle_cached.cache_clear()

    bundle = _load_registry_bundle_cached(str(resolved_dir))
    return deepcopy(bundle)


def registry_health(
    registry_dir: str | Path | None = None,
    *,
    refresh: bool = False,
) -> dict[str, Any]:
    """Return a compact diagnostic suitable for startup checks and tests."""
    bundle = load_registry_bundle(registry_dir, refresh=refresh)
    report_registry = bundle["report_type_registry"]
    data_registry = bundle["data_input_registry"]

    report_types = list_report_types(registry_dir)
    report_type_ids = [item["report_type_id"] for item in report_types]

    return {
        "status": "PASS",
        "registry_version": report_registry["registry_version"],
        "report_type_registry": REPORT_TYPE_REGISTRY_FILENAME,
        "data_input_registry": DATA_INPUT_REGISTRY_FILENAME,
        "report_type_count": len(report_type_ids),
        "report_type_ids": report_type_ids,
        "data_input_report_type_ids": sorted(
            data_registry["inputs_by_report_type"].keys()
        ),
    }


def list_report_types(
    registry_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    """List supported report types for MCP/UI routing."""
    bundle = load_registry_bundle(registry_dir)
    report_types = bundle["report_type_registry"]["report_types"]

    result: list[dict[str, Any]] = []
    for definition in report_types:
        result.append(
            {
                "report_type_id": definition["report_type_id"],
                "display_name": definition["display_name"],
                "short_code": definition["short_code"],
                "primary_goal": definition["primary_goal"],
                "use_when": definition["use_when"],
                "minimum_viable_inputs": deepcopy(
                    definition["minimum_viable_inputs"]
                ),
            }
        )

    return result


def get_report_type_definition(
    report_type_id: str,
    registry_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Return complete report blueprint by report_type_id."""
    report_type_id = _require_text(report_type_id, "report_type_id")
    bundle = load_registry_bundle(registry_dir)

    for definition in bundle["report_type_registry"]["report_types"]:
        if definition["report_type_id"] == report_type_id:
            return deepcopy(definition)

    supported = ", ".join(
        item["report_type_id"] for item in list_report_types(registry_dir)
    )
    raise RegistryError(
        f"report_type_id '{report_type_id}' tidak ditemukan. "
        f"Pilihan: {supported}."
    )


def get_report_input_requirements(
    report_type_id: str,
    registry_dir: str | Path | None = None,
) -> dict[str, Any]:
    """
    Return report-specific logical input views and minimum validation rules.

    Task 1 builders use this to know which qt_* and ql_* views they must build.
    """
    report_type_id = _require_text(report_type_id, "report_type_id")
    bundle = load_registry_bundle(registry_dir)
    report_definition = get_report_type_definition(report_type_id, registry_dir)

    input_definition = bundle["data_input_registry"]["inputs_by_report_type"][
        report_type_id
    ]
    validation_by_type = bundle["data_input_registry"].get(
        "validation_minimum_by_report_type",
        {},
    )

    return {
        "report_type_id": report_type_id,
        "registry_version": bundle["report_type_registry"]["registry_version"],
        "required_context": deepcopy(report_definition["required_context"]),
        "optional_context": deepcopy(report_definition["optional_context"]),
        "minimum_viable_inputs": deepcopy(
            report_definition["minimum_viable_inputs"]
        ),
        "quantitative": deepcopy(input_definition["quantitative"]),
        "qualitative": deepcopy(input_definition["qualitative"]),
        "validation_minimum": deepcopy(
            validation_by_type.get(
                report_type_id,
                report_definition.get("validation_minimum", []),
            )
        ),
    }


def get_required_view_ids(
    report_type_id: str,
    *,
    view_type: str | None = None,
    minimum_viable_only: bool = False,
    registry_dir: str | Path | None = None,
) -> list[str]:
    """
    Return logical view IDs in registry order.

    view_type may be:
    - None: both qt_* and ql_*;
    - "quantitative";
    - "qualitative".
    """
    if view_type is not None:
        view_type = _require_text(view_type, "view_type").casefold()
        if view_type not in {"quantitative", "qualitative"}:
            raise RegistryError(
                "view_type harus 'quantitative', 'qualitative', atau None."
            )

    requirements = get_report_input_requirements(report_type_id, registry_dir)

    if minimum_viable_only:
        return list(requirements["minimum_viable_inputs"])

    view_ids: list[str] = []

    if view_type in {None, "quantitative"}:
        view_ids.extend(
            item["input_id"] for item in requirements["quantitative"]
        )

    if view_type in {None, "qualitative"}:
        view_ids.extend(
            item["input_id"] for item in requirements["qualitative"]
        )

    return view_ids


def get_sections(
    report_type_id: str,
    registry_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Return full section definitions in the locked section order."""
    definition = get_report_type_definition(report_type_id, registry_dir)
    return deepcopy(definition["sections"])


def get_section_order(
    report_type_id: str,
    registry_dir: str | Path | None = None,
) -> list[str]:
    """Return locked section IDs in rendering order."""
    definition = get_report_type_definition(report_type_id, registry_dir)
    return list(definition["section_order"])


def get_section_input_mappings(
    report_type_id: str,
    registry_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Return mapping from blueprint sections to Task 1 views."""
    report_type_id = _require_text(report_type_id, "report_type_id")
    bundle = load_registry_bundle(registry_dir)

    mappings = bundle["data_input_registry"][
        "section_mappings_by_report_type"
    ][report_type_id]
    return deepcopy(mappings)


def get_action_taxonomy(
    report_type_id: str,
    registry_dir: str | Path | None = None,
) -> list[str]:
    """Return report-specific allowed action types for Task 2."""
    definition = get_report_type_definition(report_type_id, registry_dir)
    return deepcopy(definition["action_plan_taxonomy"])


def get_legacy_input_aliases(
    report_type_id: str | None = None,
    registry_dir: str | Path | None = None,
) -> dict[str, str]:
    """
    Return canonical view_id -> legacy alias mapping.

    Legacy aliases may be used only to read older compatibility inputs.
    New Task 1 output must always use canonical qt_*/ql_* view IDs.
    """
    bundle = load_registry_bundle(registry_dir)
    aliases = bundle["data_input_registry"].get("input_aliases_from_v1", {})

    if report_type_id is None:
        return deepcopy(aliases)

    report_type_id = _require_text(report_type_id, "report_type_id")
    prefix_map = {
        "competitive_analysis": ("qt_ca_", "ql_ca_"),
        "industry_trend": ("qt_it_", "ql_it_"),
        "daily_social_media_report": ("qt_dsm_", "ql_dsm_"),
        "brand_content_effectiveness": ("qt_bce_", "ql_bce_"),
        "spokesperson_intelligence": ("qt_sfir_", "ql_sfir_"),
        "mainstream_media_report": ("qt_mm_", "ql_mm_"),
        "evo_perception_intelligence": ("qt_evo_", "ql_evo_"),
    }

    if report_type_id not in prefix_map:
        get_report_type_definition(report_type_id, registry_dir)

    allowed_prefixes = prefix_map[report_type_id]
    return {
        canonical_id: legacy_alias
        for canonical_id, legacy_alias in aliases.items()
        if canonical_id.startswith(allowed_prefixes)
    }


__all__ = [
    "DATA_INPUT_REGISTRY_FILENAME",
    "DEFAULT_REGISTRIES_DIR",
    "EXPECTED_DATA_INPUT_REGISTRY_NAME",
    "EXPECTED_REPORT_TYPE_REGISTRY_NAME",
    "REPORT_TYPE_REGISTRY_FILENAME",
    "RegistryError",
    "get_action_taxonomy",
    "get_legacy_input_aliases",
    "get_report_input_requirements",
    "get_report_type_definition",
    "get_required_view_ids",
    "get_section_input_mappings",
    "get_section_order",
    "get_sections",
    "list_report_types",
    "load_registry_bundle",
    "registry_health",
]
