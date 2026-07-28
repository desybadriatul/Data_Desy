# Daily Social Workflow v5 Test

## Local test 1 — no audience

```powershell
@'
from reporting.task2.workflows.daily_social_report_workflow import create_daily_social_report_workflow

result = create_daily_social_report_workflow(
    project_name="BlueBird",
    start_date="2026-06-10",
    end_date="2026-06-10",
)

print("SUCCESS =", result["success"])
print("STATUS =", result["workflow_status"])
print("QUESTION =", result["clarification_question"])
'@ | python -
```

Expected: `NEEDS_AUDIENCE`.

## Local test 2 — audience + existing taxonomy/cache

```powershell
@'
from reporting.task2.workflows.daily_social_report_workflow import create_daily_social_report_workflow

result = create_daily_social_report_workflow(
    project_name="BlueBird",
    start_date="2026-06-10",
    end_date="2026-06-10",
    audience="PR/Corcom",
    topic_taxonomy_version="bluebird_daily_social_test_v1",
)

print("SUCCESS =", result["success"])
print("STATUS =", result["workflow_status"])
print("REPORT_INPUT_ID =", result.get("report_input_id"))
print("HAS_PREVIEW =", bool(result.get("data_preview")))
print("HAS_PACKAGE =", bool(result.get("render_package")))
print("VERSION =", result.get("workflow_version"))
print("\nPREVIEW SAMPLE:")
print((result.get("data_preview") or {}).get("markdown", "")[:2000])
'@ | python -
```

Expected: `READY_FOR_PREVIEW_AWAITING_USER_CONFIRMATION`, preview exists, package is False.

## Claude test — natural prompt

```text
Buatkan Daily Social Media Report BlueBird tanggal 2026-06-10.
```

Expected: Claude asks audience.

Then answer:

```text
Untuk PR/Corcom.
```

Expected: Claude handles auto-topic internally if needed, then shows data preview. It should not create PPTX yet.

Then answer:

```text
Lanjut buat PPTX.
```

Expected: Claude calls guarded package with `preview_confirmed=True` and creates PPTX.
