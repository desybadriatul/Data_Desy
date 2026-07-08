from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from reporting.task2.workflows.mainstream_media_report_workflow import create_mainstream_media_report_workflow


def main() -> None:
    print("=== TEST 1: no audience ===")
    result = create_mainstream_media_report_workflow(
        project_name="BlueBird",
        start_date="2026-06-10",
        end_date="2026-06-10",
    )
    print("SUCCESS =", result.get("success"))
    print("STATUS =", result.get("workflow_status"))
    print("QUESTION =", result.get("clarification_question"))

    print("\n=== TEST 2: with audience, skip auto issue for local preview ===")
    result = create_mainstream_media_report_workflow(
        project_name="BlueBird",
        start_date="2026-06-10",
        end_date="2026-06-10",
        audience="PR/Corcom",
        force_skip_auto_issue=True,
    )
    print("SUCCESS =", result.get("success"))
    print("STATUS =", result.get("workflow_status"))
    print("VERSION =", result.get("workflow_version"))
    print("REPORT_INPUT_ID =", result.get("report_input_id"))
    print("HAS_PREVIEW =", bool(result.get("data_preview")))
    print("HAS_PACKAGE =", bool(result.get("render_package")))
    print("\n=== PREVIEW SAMPLE ===")
    print((result.get("data_preview") or {}).get("markdown", "")[:2500])


if __name__ == "__main__":
    main()
