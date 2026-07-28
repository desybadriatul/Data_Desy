from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from reporting.task1.report_input_dispatcher import prepare_report_input


def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-brand", required=True)
    parser.add_argument("--competitors", required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--channels", default="")
    parser.add_argument("--max-rows", type=int, default=5)
    parser.add_argument("--persist", action="store_true")
    args = parser.parse_args()

    client_brand = args.client_brand.strip()
    competitors = split_csv(args.competitors)
    channels = split_csv(args.channels)

    request = {
        "project_name": client_brand,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "confirmed_intent_id": f"local_ca_{client_brand}_{args.start_date}_{args.end_date}",
        "channels": channels,
        "data_scope": "competitive",
        "timezone_name": "Asia/Jakarta",
        "client_brand": client_brand,
        "competitor_brands": competitors,
        "analysis_objective": "Competitive Analysis Action-Plan-First",
        "scope": {
            "client_brand": client_brand,
            "competitor_brands": competitors,
            "channels": channels,
            "keywords": [],
            "exclude_keywords": [],
            "match_mode": "any",
            "topic_taxonomy_version": None,
            "competitive_taxonomy_version": None,
            "raw_topic_extraction_policy": "not_used_as_report_issue",
            "test_mode": "local_task1_smoke_test",
        },
    }

    result = prepare_report_input(
        report_type_id="competitive_analysis",
        request=request,
        persist=args.persist,
        allow_fail_to_persist=False,
    )

    out_path = REPO_ROOT / "output" / "competitive_analysis_task1_preview.json"
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    print("SUCCESS = True")
    print("REPORT_INPUT_ID =", result.get("report_input_id"))
    print("VALIDATION_STATUS =", (result.get("validation") or {}).get("status"))
    print("WROTE_JSON =", out_path)

    print("\nQUANTITATIVE VIEWS")
    for view_id, view in (result.get("quantitative_views") or {}).items():
        rows = view.get("rows") or []
        meta = view.get("metadata") or {}
        print(f"- {view_id}: status={meta.get('status')} rows={len(rows)}")
        for row in rows[: args.max_rows]:
            print("  ", json.dumps(row, ensure_ascii=False, default=str)[:500])

    print("\nQUALITATIVE VIEWS")
    for view_id, view in (result.get("qualitative_views") or {}).items():
        rows = view.get("rows") or []
        meta = view.get("metadata") or {}
        print(f"- {view_id}: status={meta.get('status')} rows={len(rows)}")
        for row in rows[: args.max_rows]:
            print("  ", json.dumps(row, ensure_ascii=False, default=str)[:500])

    limitations = result.get("limitations") or []
    print("\nLIMITATIONS")
    for item in limitations:
        print("-", item)


if __name__ == "__main__":
    main()
