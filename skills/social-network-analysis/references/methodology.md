# SNA methodology and quality contract

## Canonical graph

- Default node: normalized Twitter/X account handle.
- Default edge: directed `Author -> mentioned account`.
- Edge weight: count of distinct posts in which the author mentions the target.
- Self-mentions: excluded.
- Centrality basis: the full graph before visual pruning.
- Visual subset: highest-impact nodes and strongest edges, bounded by the
  requested `max_nodes` and `max_edges`.

## Metrics

| Metric | Use | Do not claim |
|---|---|---|
| Weighted in-degree | Attention received through mentions | Positive reputation |
| Weighted out-degree | Mention/amplification activity | Organic influence |
| PageRank | Structural prominence in observed graph | Causal influence |
| Betweenness | Potential bridge between graph regions | Deliberate coordination |
| Louvain community | Structurally dense conversation group | Demographic segment |

## Content labels

Derive directional issue labels from the most frequent non-stopword terms in
posts authored by each structural community. Do not present these labels as a
supervised taxonomy unless a client-approved issue taxonomy was supplied.

## Required disclosure

Every output must disclose:

- project, channel, and period;
- full post count and mention coverage;
- edge definition;
- number of full-graph versus displayed nodes and edges;
- filtering rule;
- missing relationship endpoints;
- that visibility in the network does not prove endorsement or coordination.

## Visual QA

- Use a 16:9 canvas and minimum 180 DPI.
- Label only the most prominent nodes.
- Keep the methodology note visible at normal presentation size.
- Use community colors consistently.
- Prevent raw tweet text, tokens, credentials, local paths, and MCP internals
  from appearing in the PNG.
