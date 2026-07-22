# EVO Classification Contract — how content becomes signal

> This is the one genuinely new data-layer step EVO needs that the other six Cogan report types don't: a
> per-post attribute tagging pass. There is no existing Cogan primitive for it. This file specifies the
> pipeline, the classification prompt, sampling, confidence, and audit so the tags are reproducible and
> defensible — and so the workflow never stalls just because tags are missing.

## 1. The pipeline (row-level, one row = one post/article)

```
canonical post
  → material issue        (what is actually being said)
    → base attribute      (which registered attribute_id it forms; use cues from evo_attribute_map)
      → primary driver    (Experience | Values | Offer — derived from the attribute, not guessed)
        → polarity        (positive | negative | neutral, from sentiment)
```

Output row (minimum):

```json
{
  "post_id": "…",
  "brand": "…",
  "issue_id": "…",
  "issue_name": "Balance deducted but merchant unpaid",
  "primary_attribute_id": "ATTR_EXP_RELIABILITY",
  "primary_driver": "Experience",
  "secondary_attribute_id": null,
  "sentiment": "negative",
  "classification_confidence": 0.82,
  "classification_rationale": "Explicit failed-transaction complaint; matches reliability negative_cues.",
  "classification_source": "auto_llm | human | client_tag",
  "attribute_map_version": "1.0"
}
```

`primary_driver` is **only** Experience, Values, or Offer. Never invent a fourth driver.

## 2. When to run automatic classification

| Situation | Action |
|---|---|
| Full EVO tags already present (client or prior run) | Use the whole tagged population. No auto pass. |
| Tags absent or partial | Run automatic classification on a stratified sample (below). Mark output `tagged sample` / `directional`. |
| Classification genuinely fails (API error, unreadable content) | Only then use a blocking status (`BLOCKED_EVO_CLASSIFICATION`). |

**`NEEDS_EVO_CLASSIFICATION` is never a default terminal state.** The workflow must not stop merely because
tags weren't pre-computed. Missing tags → sample and classify → proceed with disclosed confidence.

## 3. Stratified sampling (so the sample represents the population)

- Sample ratio: **10%** of eligible content per brand.
- Hard cap: **≤ 100 content per request** (batch if larger).
- Minimum-sample guard for small-volume brands: never let a brand fall below a floor that would make its
  attribute cells uninterpretable; if it does, tag its output `low-confidence` and prefer "No prominent
  issue" over a forced winner.
- Stratify across, at minimum: `brand · channel · sentiment · content type · source type · period ·
  engagement tier`. A sample skewed to one channel or one week produces a skewed attribute picture.

## 4. Classification prompt contract

The tagging step should hand the model each post plus the resolved attribute map and ask for **structured
JSON only** (no prose), one object per post, matching the row schema in §1. The prompt must:

1. Provide the registered attributes with their `working_definition`, `positive_cues`, `negative_cues`,
   and `exclusion_cues`. The model classifies *into the registered set*, not into free text.
2. Require the model to pick the **single best-fitting attribute_id** (plus optional secondary), derive the
   driver from that attribute, and give a one-sentence rationale grounded in the post's actual words.
3. Require a `classification_confidence` in [0,1] and force `attribute_id: UNMAPPED` (not a guess) when no
   registered attribute fits — UNMAPPED posts are counted and disclosed, never silently dropped or
   force-fitted.
4. Forbid inventing quotes: rationale may paraphrase but must be traceable to the post.

Skeleton (adapt to the live tagging harness):

```
SYSTEM: You classify social/media posts into a fixed EVO attribute map. Return JSON array only,
        one object per post, matching the schema. No commentary.
        Registered attributes: <attribute_map with definitions + cues>.
        Rules: choose one primary attribute_id from the set (or UNMAPPED); derive driver from it;
        confidence 0-1; rationale grounded in the post; never fabricate text.
USER:   Posts: <batch of posts with post_id, brand, title, content, sentiment>.
```

## 5. Confidence and disclosure (ties to metric + quality gates)

- `n < 30` at any reported grain → **directional** wording, show `n`.
- `n < 10` → visible **low-confidence** warning; prefer "No prominent issue" over a forced winner; a
  low-sample cell may not independently anchor the reframe.
- Confidence is reported at the grain a claim is made — **brand, driver, and attribute × brand.** Attribute
  cells are smaller than driver cells, so `n < 10` is the norm there, not the exception. One driver-level
  caveat does not cover an attribute-level claim made from the same data.

## 6. Classification audit (frozen output: `evo_classification_audit.json`)

Every run records enough to reproduce and defend the tags. The funnel is **nested and single-basis**: every
count below traces to exactly one parent, and no two sibling counts may be computed from different bases.
This directly implements consistency_contract.md principle #6 (post count, coverage, and top-post figures
must all share the same canonical unique-post layer) for the attribute-tagging step specifically — the
failure this schema exists to prevent is a slide showing "tagged" against the sample basis while "unmapped"
is silently computed against the population basis, so the two numbers no longer subtract to anything real.

```json
{
  "attribute_map_version": "1.0",
  "map_source": "evo_seed (fallback)",
  "basis": "canonical_unique_post",
  "funnel": {
    "population_total": 21736,
    "sampling": {
      "method": "stratified_10pct",
      "sample_ratio": 0.10,
      "sampled_total": 2174,
      "stratification": ["brand","channel","sentiment","content_type","source_type","period","engagement_tier"]
    },
    "not_sampled_total": 19562,
    "reconciliation_population": "population_total == sampled_total + not_sampled_total",
    "classification_result": {
      "tagged_total": 2111,
      "unmapped_total": 63,
      "reconciliation_sample": "sampled_total == tagged_total + unmapped_total"
    }
  },
  "confidence_summary": { "median": 0.79, "below_0_5": 118 },
  "per_brand": [
    { "brand": "Telkomsel", "sampled": 540, "tagged": 517, "unmapped": 23, "median_conf": 0.81 }
  ],
  "method": "auto_llm",
  "prompt_version": "evo-classify-1.0"
}
```

Both `reconciliation_population` and `reconciliation_sample` are computed and stored, not asserted — the
builder fails Task 1 (not a silent warning) if either arithmetic check does not hold. `unmapped_total` is
**always** the sample-basis residual (`sampled_total − tagged_total`); it is never computed from
`population_total`. Any renderer or slide showing a funnel figure traces it to exactly one field in this
object and never re-derives a subtraction on the slide itself — the same discipline as the metric-manifest
rule in `evo_quality_gate.md`'s Tier A extension. `per_brand` entries must independently reconcile
(`sampled == tagged + unmapped` per brand) before the aggregate is trusted.

Task 2 consumes these tags; it never re-tags and never recomputes attribute metrics from them (see the
computation-source lock in `evo_metric_dictionary.md`).
