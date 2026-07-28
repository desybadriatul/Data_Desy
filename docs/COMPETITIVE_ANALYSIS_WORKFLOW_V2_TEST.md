# Competitive Analysis Workflow Patch v2

## Purpose

Adds Competitive Analysis Task 1 + Task 2 workflow with the same guardrail pattern as Daily Social and Mainstream Media:

1. ask audience if missing;
2. ask competitors if missing;
3. require LLM Competitive Topic/Narrative taxonomy before final preview;
4. require LLM topic classification before topic-level views are used;
5. show Task 1 preview first;
6. build PPT package only after user confirms preview;
7. use Evidence IDs on main slides; keep full URLs only in Appendix/Data Pack.

## Core policy

- Raw `Topic Extraction` is diagnostic only.
- Legacy `Aspect` / `ABSA` is not a dependency.
- Raw `Entity Extraction` is not a dependency.
- Brand universe comes from `client_brand + competitors`, not entity extraction.
- Topic-level numbers are computed from cached LLM assignments over canonical rows.

## Classification target

- Eligible content <= 150: classify all.
- Eligible content > 150: classify 10%, min 100, max 150.
- Sampling is balanced per brand.

## Expected workflow statuses

- `NEEDS_AUDIENCE`
- `NEEDS_COMPETITORS`
- `NEEDS_AUTO_COMPETITIVE_TAXONOMY`
- `NEEDS_AUTO_COMPETITIVE_TOPIC_CLASSIFICATION`
- `READY_FOR_PREVIEW_AWAITING_USER_CONFIRMATION`

## Claude sequence when taxonomy is missing

1. Call `create_competitive_analysis_report_workflow`.
2. If response is `NEEDS_AUTO_COMPETITIVE_TAXONOMY`, create taxonomy JSON from `taxonomy_sample`.
3. Call `save_topic_taxonomy(project_name, taxonomy_json, activate=False)`.
4. Rerun `create_competitive_analysis_report_workflow` with `topic_taxonomy_version`.
5. If response is `NEEDS_AUTO_COMPETITIVE_TOPIC_CLASSIFICATION`, classify `batch.post_refs`.
6. Call `save_topic_batch_results(batch_id, results_json)`.
7. Repeat until preview is ready.

## Local test

```powershell
python -m py_compile .\server.py
python -m py_compile .\reporting\task1\builders\competitive_analysis.py
python -m py_compile .\reporting\task2\renderers\competitive_analysis_report_renderer.py
python -m py_compile .\reporting\task2\workflows\competitive_analysis_report_workflow.py
python -m py_compile .\scripts\patch_server_competitive_analysis_workflow_v2.py
python -m py_compile .\scripts\test_competitive_analysis_workflow_v2.py
python .\scripts\test_competitive_analysis_workflow_v2.py
```

Expected:

```text
NO_AUDIENCE_STATUS = NEEDS_AUDIENCE
NO_COMPETITORS_STATUS = NEEDS_COMPETITORS
TARGET_46 = 46
TARGET_150 = 150
TARGET_830 = 100
WORKFLOW_VERSION = competitive_analysis_report_workflow_v2
RENDER_PACKAGE_VERSION = competitive_analysis_report_render_package_v2
COMPETITIVE ANALYSIS WORKFLOW V2 OK
```

## Claude test prompt

```text
Buatkan Competitive Analysis BlueBird dibanding Grab dan Gojek periode 9-10 Juni 2026 untuk Marketing/Brand Team. Tampilkan preview dulu sebelum PPT.
```

## Evidence URL policy

Main slides:

```text
Evidence: P01 / T01 / E01
```

Appendix/Data Pack:

```text
Full source URL
```
