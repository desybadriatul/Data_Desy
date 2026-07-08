from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from reporting.storage.report_input_store import list_report_inputs
from reporting.task2.renderers.mainstream_media_report_renderer import (
    build_mainstream_media_report_data_preview,
    build_mainstream_media_report_package,
)


def main() -> None:
    rows = list_report_inputs(
        project_name="KDM Sidak Pabrik Air",
        report_type_id="mainstream_media_report",
        limit=1,
    ) or list_report_inputs(report_type_id="mainstream_media_report", limit=1)
    if not rows:
        raise RuntimeError("Belum ada report_input mainstream_media_report. Jalankan workflow/Task 1 dulu.")

    report_input_id = rows[0]["report_input_id"]
    print("REPORT_INPUT_ID =", report_input_id)

    preview = build_mainstream_media_report_data_preview(report_input_id, include_evidence_limit=8)
    print("PREVIEW_SUCCESS =", preview["success"])
    print("POSTURE =", preview["brand_facing_risk_posture"]["label"])
    print("NOISE_EXCLUDED =", len(preview.get("noise_excluded_from_main_slides") or []))
    print("FACT_ALLEGATION_KEYS =", list(preview.get("fact_vs_allegation", {}).keys()))
    print("\n=== PREVIEW SAMPLE ===")
    print(preview["markdown"][:2500])

    pkg = build_mainstream_media_report_package(
        report_input_id,
        audience_context="Legal/Crisis Team",
        allow_partial=True,
    )
    print("\nPACKAGE_SUCCESS =", pkg["success"])
    print("VERSION =", pkg["render_package_version"])
    print("QUALITY =", pkg.get("quality_upgrade"))
    print("SLIDE_COUNT =", len(pkg["slides"]))
    for slide in pkg["slides"]:
        print("-", slide["slide_id"], "|", slide["title"])


if __name__ == "__main__":
    main()
