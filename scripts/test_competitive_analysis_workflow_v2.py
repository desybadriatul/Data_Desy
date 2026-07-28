"""Smoke tests for Competitive Analysis workflow v2.

This test avoids DB calls. It checks:
- missing audience guard
- missing competitors guard
- classification target policy
- package version import
"""
from __future__ import annotations

from reporting.task2.renderers.competitive_analysis_report_renderer import RENDER_PACKAGE_VERSION
from reporting.task2.workflows.competitive_analysis_report_workflow import (
    WORKFLOW_VERSION,
    _classification_target,
    create_competitive_analysis_report_workflow,
)


def main() -> None:
    no_audience = create_competitive_analysis_report_workflow(
        project_name="BlueBird",
        start_date="2026-06-09",
        end_date="2026-06-10",
        client_brand="BlueBird",
        competitors="Grab,Gojek",
        require_audience=True,
    )
    print("NO_AUDIENCE_STATUS =", no_audience.get("workflow_status"))
    assert no_audience.get("workflow_status") == "NEEDS_AUDIENCE"

    no_competitors = create_competitive_analysis_report_workflow(
        project_name="BlueBird",
        start_date="2026-06-09",
        end_date="2026-06-10",
        audience="Marketing/Brand Team",
        client_brand="BlueBird",
        require_competitors=True,
    )
    print("NO_COMPETITORS_STATUS =", no_competitors.get("workflow_status"))
    assert no_competitors.get("workflow_status") == "NEEDS_COMPETITORS"

    print("TARGET_46 =", _classification_target(46))
    print("TARGET_150 =", _classification_target(150))
    print("TARGET_830 =", _classification_target(830))
    assert _classification_target(46) == 46
    assert _classification_target(150) == 150
    assert _classification_target(830) == 100

    print("WORKFLOW_VERSION =", WORKFLOW_VERSION)
    print("RENDER_PACKAGE_VERSION =", RENDER_PACKAGE_VERSION)
    assert WORKFLOW_VERSION == "competitive_analysis_report_workflow_v4_campaign_first_gate"
    assert RENDER_PACKAGE_VERSION == "competitive_analysis_report_render_package_v2"
    print("COMPETITIVE ANALYSIS WORKFLOW V2 OK")


if __name__ == "__main__":
    main()
