# Global Relevance & Taxonomy Evolution V1

Purpose: prevent non-brand noise from entering report metrics and prevent new conversations from being collapsed into client-facing `Topik Baru` buckets.

## Scope

Applies before report metrics/evidence are built for:

- Daily Social Media Report
- Competitive Analysis
- Mainstream Media Report

## Global relevance gate

Rows are split into:

- `clean_rows`: used for KPI, SOV/SOE, sentiment, topic, evidence.
- `excluded_rows`: deterministic noise, excluded from report metrics.
- `review_rows`: uncertain relevance; retained by default but marked in audit scope.

The filter currently blocks high-confidence generic/ambiguous noise such as:

- Bluebird as plant/bird context.
- Aqua as aqua farming/aquarium/aquatic context.
- Pristine as a generic adjective.
- Generic Club / Apple / Orange contexts.
- Fleet/resale marketplace posts by default unless the scope explicitly includes resale/fleet analysis.

Summary is attached to `report_input.scope.global_relevance_filter`.

## Taxonomy evolution

`other_emerging_topic` is no longer allowed as `classification_status=classified`.
New conversations must be saved as:

```json
{
  "primary_topic_id": "other_emerging_topic",
  "classification_status": "review_needed",
  "emerging_topic_detail": "CEO Personal Branding"
}
```

Builders extract these saved review rows into `report_input.scope.taxonomy_evolution.candidates` so Claude can create a new taxonomy version and save it with the existing `save_topic_taxonomy` tool.

## Why this matters

The report should not count obvious keyword/campaign noise as brand conversation, and new stable conversation clusters should become taxonomy candidates instead of being forced into a permanent generic `Topik Baru` bucket.
