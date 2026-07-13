# Report Client Polish V1

Polishes client-facing report package wording across Daily Social, Competitive Analysis, and Mainstream Media Report without changing server/MCP registration or report workflow structure.

## Scope

- Daily Social: removes visible `Tidak relevan` labels, reframes low-context mentions, labels low coverage topic charts as early theme signals, and adds concrete output deliverables to Prepare Response actions.
- Competitive Analysis: adds direct evidence CTA metadata to Action Plan cards when supporting evidence exists, makes Exploit White Space more concrete, and avoids unvalidated `mitra/partner` relationship claims.
- Mainstream Media Report: ensures Activate Spokesperson focuses on Aqua/Danone technical spokesperson rather than external framing actors, softens technical validation wording, and adds follow-up modes for media contributors.
- Render QA Gate: blocks unpolished client-facing labels such as `Tidak relevan` and guards against MMR spokesperson focus regressions.

## Non-goals

- Does not modify server.py.
- Does not alter report workflow routing.
- Does not change Task 1 extraction logic.
- Does not remove audit IDs/URLs from data packs; it only prevents them from becoming client-facing labels.
