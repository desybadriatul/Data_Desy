# Spokesperson Server Tools v1

Patch ini menambahkan dua MCP tool ke `server.py`:

```text
prepare_spokesperson_enrichment
save_spokesperson_enrichment_response
```

Tujuannya agar Claude/MCP bisa menjalankan enrichment spokesperson secara reusable untuk report apa pun yang butuh spokesperson analysis.

## Flow

```text
report workflow
→ prepare_spokesperson_enrichment
→ jika NEEDS_AUTO_SPOKESPERSON_ENRICHMENT, Claude proses prompt_batches
→ save_spokesperson_enrichment_response
→ rerun report workflow
→ builder/workflow attach hasil cache ke report_input dengan attach_spokesperson_views()
```

## Catatan

Patch ini hanya menambahkan server tools. Report tertentu tetap harus opt-in di workflow/builder masing-masing jika ingin hasil spokesperson muncul di preview/PPT.
