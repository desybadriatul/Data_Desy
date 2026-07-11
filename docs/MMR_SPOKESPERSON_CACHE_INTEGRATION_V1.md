# MMR Spokesperson Cache Integration V1

This patch makes the Mainstream Media Report use the shared spokesperson
enrichment cache instead of grouping the raw `Spokesperson` source column.

## Behavior

- The MMR builder sends only mainstream articles with cached topic status
  `classified` to the spokesperson cache adapter.
- Named speakers are read from `spokesperson_enrichment_cache`.
- Missing `represented_campaign` is preserved and never filled from the source
  campaign.
- MMR overall speaker ranking may include regulators/government officials even
  when `represented_campaign` is null.
- Conservative alias normalization merges an unambiguous short name with a
  known full name, including same-article context matching.
- Brand personas and organization-only names are excluded from the MMR speaker
  overview.
- Representative title, media, and URL always come from the same cached article
  row.
- The renderer trusts cache-normalized rows and no longer contains project-
  specific alias mappings.

## Test

```powershell
python .\scripts\test_mmr_spokesperson_cache_integration_v1.py
```

Expected final line:

```text
MMR_SPOKESPERSON_CACHE_INTEGRATION_V1_OK
```
