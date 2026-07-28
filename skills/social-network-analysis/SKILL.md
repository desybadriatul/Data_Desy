---
name: social-network-analysis
description: Build a directed social-network analysis from Cogan social-media data and render a brand-team-ready PNG. Use for requests about issue propagation, actor maps, mention networks, influential accounts, bridge accounts, network communities, or SNA outputs from Twitter/X data or an attached Cogan raw-data XLSX.
---

# Social Network Analysis

Create an auditable actor network from Cogan data. Default to a directed
author-to-mentioned-account graph when relationship endpoints for replies,
quotes, and retweets are unavailable.

## Workflow

1. Confirm project, period, channel, analytical question, audience, and output.
2. Run Cogan `find_project`, `validate_metric_readiness`, and `data_health`.
3. Inspect raw columns before choosing an edge model.
4. Select the strongest defensible edge:
   - reply/repost/quote source fields -> interaction diffusion network;
   - otherwise `Author -> @mention in Content` -> mention network;
   - otherwise stop. Do not infer actor-to-actor edges from engagement counts.
5. Export canonical raw data with `export_raw_scope_data`.
6. Run `scripts/generate_sna.py`.
7. Inspect the PNG and the printed audit summary.
8. State the edge definition, retained-node filter, period, channel, coverage,
   and limitations alongside the output.

## Generate from Cogan MCP

```bash
python skills/social-network-analysis/scripts/generate_sna.py \
  --project "Le Minerale" \
  --channel twitter \
  --start-date 2026-06-20 \
  --end-date 2026-06-30 \
  --mcp-url "https://sonar-cogan-database-production.up.railway.app/mcp" \
  --output output/le-minerale-twitter-sna.png
```

## Generate from an attached export

```bash
python skills/social-network-analysis/scripts/generate_sna.py \
  --input-xlsx raw-data.xlsx \
  --project "Le Minerale" \
  --channel twitter \
  --start-date 2026-06-20 \
  --end-date 2026-06-30 \
  --output output/le-minerale-twitter-sna.png
```

Use `--max-nodes` and `--max-edges` only to control visual legibility. Calculate
centrality on the full graph before visual filtering.

## Interpretation rules

- Call the default output **Mention-based Issue Propagation Network**.
- Treat an edge as observable attention or message routing, not proof of
  endorsement, persuasion, coordinated behavior, or causal diffusion.
- Keep interaction counts separate from relationship endpoints. A tweet with
  ten retweets does not identify ten retweeter accounts.
- Describe PageRank as structural prominence, weighted out-degree as
  amplification activity, and betweenness as bridging potential.
- Describe detected communities as structural conversation communities. Use
  their top content terms only as directional issue labels.
- Do not expose raw tweet text in the client-facing PNG.
- Read [methodology.md](references/methodology.md) when writing findings,
  limitations, or QA notes.

## Release gate

Do not deliver when there are no defensible edges, fewer than two connected
actors, an unreadable PNG, a scope mismatch, or an edge label that overstates
the available relationship data.
