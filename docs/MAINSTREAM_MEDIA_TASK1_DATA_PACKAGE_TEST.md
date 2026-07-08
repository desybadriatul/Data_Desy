# Mainstream Media Report — Task 1 Data Package Patch

Patch ini menambahkan `reporting/task1/builders/mainstream_media_report.py`.

## Scope MVP

- Source/channel: `Online Media` + `Printmedia`.
- KPI/sentiment/media/evidence memakai full canonical data.
- Raw `Topic Extraction` tidak dipakai sebagai final issue/topic report.
- Issue/topic report membaca cached LLM assignment dari Title + Content melalui topic enrichment cache.
- Jika `issue_taxonomy_version` / `topic_taxonomy_version` belum tersedia, issue-based views menjadi `NOT_AVAILABLE`, bukan diisi paksa.

## Views yang dibangun

Quantitative:

- `qt_mm_kpi_tiles`
- `qt_mm_channel_distribution`
- `qt_mm_sentiment_distribution`
- `qt_mm_main_topics_top3`
- `qt_mm_sentiment_matrix_by_channel`
- `qt_mm_spokesperson_overview`
- `qt_mm_media_contributors_table`

Qualitative:

- `ql_mm_article_enriched`
- `ql_mm_top_issues_cards`
- `ql_mm_sentiment_issue_cards`
- `ql_mm_headlines_summary`

## Expected behavior

Tanpa issue taxonomy/cache:

- Minimum viable views tetap READY: KPI, channel distribution, article enriched.
- Issue views `qt_mm_main_topics_top3`, `ql_mm_top_issues_cards`, `ql_mm_sentiment_issue_cards` menjadi NOT_AVAILABLE.
- Validation kemungkinan `PARTIAL_PASS`.

Dengan issue taxonomy/cache:

- Issue views menjadi READY.
- Validation bisa PASS kalau field lain cukup.
