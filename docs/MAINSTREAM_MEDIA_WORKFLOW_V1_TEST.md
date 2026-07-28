# Mainstream Media Report Workflow v1 Test Guide

Patch ini menyelesaikan Mainstream Media Report sampai flow seperti Daily Social v5:

1. User bisa prompt pendek.
2. Audience wajib ditanya kalau belum disebut.
3. KPI/sentiment/media/article evidence memakai full canonical mainstream data.
4. Issue analysis memakai smart sample dari Title + Content melalui topic enrichment cache.
5. Preview data Task 1 tampil dulu.
6. PPT package hanya bisa dibuat setelah preview dikonfirmasi.

## MCP tools added

- `create_mainstream_media_report_workflow`
- `build_mainstream_media_report_data_preview`
- `build_mainstream_media_report_ppt_package`

## Default source scope

- Online Media
- Printmedia

## Default smart issue policy

- 10% dari issue-eligible articles
- minimum 20 artikel
- maksimum 100 artikel
- raw `Topic Extraction` tidak dipakai sebagai final issue

## Local test

```powershell
python -m py_compile .\reporting\task1\builders\mainstream_media_report.py
python -m py_compile .\reporting\task2\renderers\mainstream_media_report_renderer.py
python -m py_compile .\reporting\task2\workflows\mainstream_media_report_workflow.py
python -m py_compile .\scripts\patch_server_mainstream_media_workflow_v1.py
python -m py_compile .\scripts\test_mainstream_media_workflow_v1.py

python .\scripts\test_mainstream_media_workflow_v1.py
```

Expected:

- Test tanpa audience returns `NEEDS_AUDIENCE`.
- Test dengan audience + `force_skip_auto_issue=True` returns preview and no package.

## Claude short-prompt test

Prompt:

```text
Buatkan Mainstream Media Report BlueBird tanggal 2026-06-10.
```

Expected:

- Claude asks audience.
- After audience is provided, Claude calls `create_mainstream_media_report_workflow`.
- If `NEEDS_AUTO_ISSUE_TAXONOMY`, Claude creates taxonomy from sample and saves it.
- If `NEEDS_AUTO_ISSUE_CLASSIFICATION`, Claude classifies the batch and saves it.
- Claude shows `data_preview.markdown`.
- Claude waits for user confirmation before PPTX.

After user says `Lanjut buat PPTX`, Claude calls:

```text
build_mainstream_media_report_ppt_package(..., preview_confirmed=True)
```

Then creates PPTX from `slides` array.
