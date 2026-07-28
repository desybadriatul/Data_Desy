"""Regression checks for shared report enrichment registry v1."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from reporting.enrichment.report_enrichment_registry import (
    ReportEnrichmentRegistryError,
    clamp_enrichment_target,
    get_report_enrichment_requirements,
    validate_enrichment_request,
)
from reporting.task2.workflows.competitive_analysis_report_workflow import (
    create_competitive_analysis_report_workflow,
)
from reporting.task2.workflows.daily_social_report_workflow import (
    create_daily_social_report_workflow,
)
from reporting.task2.workflows.mainstream_media_report_workflow import (
    create_mainstream_media_report_workflow,
)


def _assert_plan(report_type_id: str, *, topic: bool, spokesperson: bool) -> None:
    plan = get_report_enrichment_requirements(report_type_id)
    assert plan["topic"]["enabled"] is topic
    assert plan["spokesperson"]["enabled"] is spokesperson
    assert plan["topic"]["allow_auto_expand"] is False


def main() -> None:
    _assert_plan("daily_social_media_report", topic=True, spokesperson=False)
    _assert_plan("competitive_analysis", topic=True, spokesperson=False)
    _assert_plan("mainstream_media_report", topic=True, spokesperson=True)
    print("REPORT_ENRICHMENT_MAPPING_OK")

    assert clamp_enrichment_target("daily_social_media_report", "topic", 999) == 100
    assert clamp_enrichment_target("competitive_analysis", "topic", 999) == 150
    assert clamp_enrichment_target("mainstream_media_report", "topic", 999) == 100
    assert clamp_enrichment_target("daily_social_media_report", "spokesperson", 50) == 0
    print("REPORT_ENRICHMENT_HARD_CAP_OK")

    try:
        validate_enrichment_request(
            "competitive_analysis",
            spokesperson_requested=True,
        )
    except ReportEnrichmentRegistryError:
        pass
    else:
        raise AssertionError("Competitive Analysis must reject spokesperson enrichment")

    validate_enrichment_request(
        "mainstream_media_report",
        topic_requested=True,
        spokesperson_requested=True,
    )
    print("REPORT_ENRICHMENT_GUARD_OK")

    daily_gate = create_daily_social_report_workflow(
        project_name="Demo",
        start_date="2026-01-01",
    )
    ca_gate = create_competitive_analysis_report_workflow(
        project_name="Demo",
        start_date="2026-01-01",
    )
    mmr_gate = create_mainstream_media_report_workflow(
        project_name="Demo",
        start_date="2026-01-01",
    )
    assert daily_gate["enrichment_requirements"]["spokesperson"]["enabled"] is False
    assert ca_gate["enrichment_requirements"]["spokesperson"]["enabled"] is False
    assert mmr_gate["enrichment_requirements"]["spokesperson"]["enabled"] is True
    print("REPORT_ENRICHMENT_AUDIENCE_GATE_OK")

    daily_source = inspect.getsource(create_daily_social_report_workflow)
    ca_source = inspect.getsource(create_competitive_analysis_report_workflow)
    mmr_source = inspect.getsource(create_mainstream_media_report_workflow)
    assert "get_report_enrichment_requirements" in daily_source
    assert "get_report_enrichment_requirements" in ca_source
    assert "get_report_enrichment_requirements" in mmr_source
    assert "prepare_spokesperson_enrichment_batch" not in daily_source
    assert "prepare_spokesperson_enrichment_batch" not in ca_source
    assert "prepare_spokesperson_enrichment_batch" in mmr_source
    print("REPORT_ENRICHMENT_WORKFLOW_ROUTING_OK")

    server_source = Path("server.py").read_text(encoding="utf-8")
    assert "def get_report_enrichment_plan(" in server_source
    assert "validate_enrichment_request(" in server_source
    assert "minimum 50, maximum 100" in server_source
    assert "main report pakai Evidence ID" not in ca_source
    assert "Buka post" in ca_source
    print("REPORT_ENRICHMENT_SERVER_POLICY_OK")

    print("REPORT_ENRICHMENT_REGISTRY_V1_OK")


if __name__ == "__main__":
    main()
