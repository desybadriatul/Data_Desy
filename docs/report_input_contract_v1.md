# Report Input Contract v1

Status: LOCKED

Setiap report type harus menghasilkan satu report-ready package dengan struktur:

- schema_version
- report_input_id
- report_type_id
- context
- scope
- metric_readiness
- data_health
- validation
- quantitative_views
- qualitative_views
- limitations
- evidence_log

## Context wajib

- project_name
- period.start_date
- period.end_date
- timezone
- channels
- data_scope

## Aturan view

- `qt_*` = hasil agregasi angka.
- `ql_*` = evidence content/article asli.
- Semua `ql_*` harus menyimpan source/link bila tersedia.
- Missing view harus dicatat pada `validation.missing_views`.
- Data tidak tersedia harus menjadi `N/A`, bukan diisi asumsi.

## Batas Task 1

Task 1 membangun quantitative views, qualitative views, validation,
limitation, dan evidence log.

Task 1 tidak menulis headline report, recommendation final, Action Plan final,
atau PPT.

## Batas Task 2

Task 2 membaca report input package, mengikuti registry section order,
menulis narrative, Action Plan, dan menghasilkan report/PPT.