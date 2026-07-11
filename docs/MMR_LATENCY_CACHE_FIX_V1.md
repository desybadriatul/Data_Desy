# MMR Latency + Cache Fix V1

Target branch: `feat/report-input-tama-dsm-mmr-ca` at baseline commit `cf48c4b`.

## What changes

1. Audience and topic enrichment run before spokesperson enrichment.
2. MMR channel scope remains locked to `Online Media` + `Printmedia` when no channel is supplied.
3. Spokesperson candidates are restricted to articles already classified as relevant by the issue taxonomy.
4. Spokesperson `content_hash` is hydrated by the server from canonical post IDs. Claude no longer needs to copy the hash.
5. Topic `content_hash` is taken from the issued batch manifest. Missing or mistyped hashes from Claude no longer invalidate the whole batch.
6. Issue sample has a fixed hard stop. Default MMR target is 10%, minimum 50, maximum 100, with no automatic expansion after preview.
7. The duplicate late override that raised the MMR maximum to 150 is removed.

## Files replaced

- `server.py`
- `reporting/enrichment/spokesperson_enrichment_workflow.py`
- `reporting/enrichment/topic_result_validator.py`
- `reporting/enrichment/topic_batch_builder.py`
- `reporting/enrichment/topic_contract.py`
- `reporting/task2/workflows/mainstream_media_report_workflow.py`

## Test

Run from repository root:

```powershell
python -m py_compile .\server.py
python .\scripts\test_mmr_latency_cache_fix_v1.py
```

Expected final line:

```text
MMR_LATENCY_CACHE_FIX_V1_OK
```

## Expected MMR flow

```text
Audience confirmation
→ topic taxonomy/classification until fixed target
→ spokesperson enrichment only for topic-classified relevant articles
→ save once; server injects trusted hashes
→ rerun same locked scope
→ preview
→ user approval
→ PPT package
```
