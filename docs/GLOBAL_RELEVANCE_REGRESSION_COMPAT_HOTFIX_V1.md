# Global Relevance Regression Compatibility Hotfix V1

This hotfix restores regression compatibility after `global_relevance_and_taxonomy_evolution_v1`:

- Topic classification `content_hash` remains server-managed from the issued batch manifest.
- Claude may omit or typo `content_hash`; validator still trusts the server-side batch value.
- New taxonomy evolution guard is preserved: `classified + other_emerging_topic` is rejected; emerging conversations must be `review_needed` with `emerging_topic_detail`.
- Mainstream Media Report builder keeps the spokesperson cache integration path (`build_mmr_spokesperson_overview`) while retaining global relevance filtering and taxonomy evolution metadata.
