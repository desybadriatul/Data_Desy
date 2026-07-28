from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


from reporting.task1.report_input_dispatcher import prepare_report_input


PROJECT_NAME = "BlueBird"
START_DATE = "2026-06-10"
END_DATE = "2026-06-10"

request = {
    "project_name": PROJECT_NAME,
    "start_date": START_DATE,
    "end_date": END_DATE,
    "confirmed_intent_id": f"local_test_mmr_{PROJECT_NAME}_{START_DATE}",
    "channels": (),
    "data_scope": "brand",
    "client_brand": PROJECT_NAME,
    "competitor_brands": (),
    "analysis_objective": "Smoke test Mainstream Media Task 1 data package",
    "scope": {
        "channels": [],
        "universe": "brand",
        "issue_taxonomy_version": None,
        "keywords": [],
        "exclude_keywords": [],
        "match_mode": "any",
    },
    "metric_readiness": {},
    "data_health": {},
}

result = prepare_report_input(
    report_type_id="mainstream_media_report",
    request=request,
    persist=True,
)

print("REPORT_INPUT_ID =", result["report_input_id"])
print("VALIDATION =", result["validation"]["status"])
print("\nQUANTITATIVE VIEWS:")
for vid, view in result["quantitative_views"].items():
    rows = view.get("rows") or []
    status = (view.get("metadata") or {}).get("status", "READY")
    print("-", vid, "| rows:", len(rows), "| status:", status)

print("\nQUALITATIVE VIEWS:")
for vid, view in result["qualitative_views"].items():
    rows = view.get("rows") or []
    status = (view.get("metadata") or {}).get("status", "READY")
    print("-", vid, "| rows:", len(rows), "| status:", status)

print("\nLIMITATIONS:")
for item in result.get("limitations") or []:
    print("-", item)
