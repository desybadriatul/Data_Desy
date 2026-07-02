# CONSISTENCY CONTRACT — The Invariant Layer
## What must be identical across every report, so adaptation never drifts into inconsistency

> The four dials (expert approach · pain-point type · analytical lens · arc emphasis) exist to make every
> report **adapt** to its client. This file is their counterweight: it locks the parts that must **never**
> vary, so two runs of the engine — for two clients, or for the same client across months — produce
> deliverables that are *comparable, reproducible, and recognizably the same product*.
>
> **The reconciliation:** the dials adapt CONTENT (the argument, the lens, the emphasis). This contract
> locks FORM, METRICS, THEME, and RECONCILIATION (the scaffold, the math, the look, the proof). Anti-template
> still holds — the scaffold is empty structure; the brand-specific argument still fills it, and the report
> still BREAKS when you swap the brand name. A fixed skeleton is not a template; identical *content* is.
>
> This contract is **versioned**. Stamp `contract_version` into `deck_data.json` and onto the methodology
> slide. A client's month-over-month reports must share the same `contract_version`, or differences in the
> numbers may come from the engine, not from the market.

---

## PART 1 — METRIC DICTIONARY (LOCKED)

Every internal metric has exactly ONE definition, formula, grain, dedup rule, and rounding rule. Stage C
computes from this table and nothing else. If a metric the storyline needs is not here, define it here
first (and bump `contract_version`) — never improvise a formula at compute time.

| Metric | Definition | Formula / rule | Grain | Dedup rule |
|---|---|---|---|---|
| **Count of Content (Posts)** | Number of unique posts | count of unique post (one URL = one post) | per campaign | unique per URL **per campaign**; the SAME post in two campaigns counts in EACH |
| **Buzz** | Reach/volume proxy | `sum(Buzz)`; fallback to Count of Content if Buzz field absent | per campaign | follows Count dedup |
| **Engagement** | Interaction volume | `sum(like+comment+share+view)` per available fields | per post → summed | NOT summed across campaigns (a shared post's engagement is not double-counted into a combined total) |
| **Avg Engagement / Content** | Engagement efficiency | `Total Engagement / Count of Content` | per campaign | — |
| **Share of Voice (SOV)** | Volume dominance | `campaign_buzz / Σ all-campaigns buzz × 100`; declare metric basis = buzz \| posts \| engagement | across compared set | overlapping shares allowed (shared post in each); footnote the overlap |
| **Share of Engagement (SOE)** | Engagement dominance | `campaign_engagement / Σ all-campaigns engagement × 100` | across compared set | — |
| **Sentiment Share** | % positive / neutral / negative | `sentiment_count / total_classified × 100` | per campaign | a post with no/null sentiment is **excluded from the denominator** and disclosed (see residual rule) |
| **Channel Share** | % volume per channel | `channel_count / total_count × 100` | per campaign | — |
| **Net Sentiment — by count** | Sentiment balance, unweighted | `(%positive − %negative)` in points | per campaign | label as **(by count)** |
| **Net Sentiment — engagement-weighted** | Sentiment balance, weighted by reach | `(pos_engagement − neg_engagement) / total_engagement`, scaled | per campaign | label as **(engagement-weighted)** |
| **Ad Value** | Earned-media value (online media) | as provided by source; per outlet | per outlet | online media has no engagement — value via ad value only |

**NET SENTIMENT — MANDATORY LABEL.** The two variants give different numbers for the same pillar (in the
Bluebird deck, the safety pillar read −43 **by count** and −89 **engagement-weighted**). Whenever a net
sentiment appears, the basis MUST be stated inline or in the axis/footnote, and a deck MUST NOT mix the two
bases for the same unit without saying so. Pick ONE basis as the deck's primary and hold it.

**ROUNDING (locked).** Percentages → 1 decimal, round-half-up. Counts → integer. A percentage breakdown
must sum to 100.0 ± 0.1. If it does not (rounding residue, multi-label, or null-sentiment rows), apply the
**residual rule**: disclose the residual once in a footnote (e.g. "0.1% rounding" or "n posts unclassified,
excluded from sentiment denominator") — never silently force-fit, and never let the gap surface as an
unexplained mismatch between two slides.

---

## PART 2 — RECONCILIATION & PROVENANCE GATE  (Tier-A · runs as STAGE C.5, after data-freeze)

A new mandatory gate between Stage C (validation) and Stage D (insight). It runs once on the frozen
`deck_data.json` and BLOCKS delivery on failure, exactly like A1. Its job: prove the numbers are internally
consistent and fully traceable **before** any narrative is written on top of them.

**Checks (all must pass or be explicitly resolved):**

1. **Sum-of-parts = total.** For every breakdown (channel, sentiment, topic, SOV set), `Σ parts` must equal
   the stated total within ±1 row OR ±0.1 pp. A larger gap → resolve via the residual rule (footnote +
   denominator note) or fix the query. *(This is the check that catches the live 21,756 vs 21,736 case.)*
2. **Headline existence.** Every number that appears on a cover KPI, a headline, the reframe, the implication,
   or the decision slide must exist verbatim in `deck_data.json`. No figure is born at render time.
3. **Single definition.** Each metric label maps to exactly one Part-1 formula across the whole deck. The
   same word ("net sentiment", "share") never means two things.
4. **Net-sentiment basis labeled.** Every net-sentiment figure carries its basis (by count \| engagement-weighted).
5. **Weak-data flag.** Any metric with n below the small-sample floor (default n < 30, configurable per
   report) is tagged `directional` and must be rendered with directional wording + visible n (ties to A4).

**Output a machine-checkable record** in `deck_data.json`:

```json
"reconciliation": {
  "contract_version": "1.0",
  "checks": [
    { "name": "channel_sum", "total": 21736, "parts_sum": 21736, "delta": 0, "status": "PASS" },
    { "name": "sentiment_sum", "total": 21736, "parts_sum": 21756, "delta": 20,
      "status": "RESOLVED", "resolution": "20 posts multi/null sentiment; excluded from denominator; footnoted" }
  ],
  "headline_numbers": [ { "value": "76.2%", "metric": "SOV_buzz", "source_key": "sov.aqua", "exists": true } ],
  "directional_metrics": [ { "metric": "green_taxi_share", "n": 93, "wording": "directional" } ],
  "overall_status": "PASS"
}
```

If `overall_status` ≠ PASS and any check is unresolved → **HALT before Stage D** (same severity as a Stage C FAIL).

---

## PART 3 — DESIGN TOKEN THEME (LOCKED · `theme.json`)

All visual constants live in ONE token object. Stage F reads tokens; it never hardcodes a hex or a font.
This guarantees every deck looks like the same product. Override a token only with an explicit client brand
kit (and stamp which kit was used).

```json
{
  "theme_version": "1.0",
  "color": {
    "bg_dark":        "1A1A2E",
    "bg_light":       "FFFFFF",
    "ink":            "1E293B",
    "muted":          "9CA3AF",
    "card_positive":  "1E3A5F",
    "card_negative":  "7F1D1D",
    "accent_cool":    "CADCFC",
    "label_on_neg":   "FFCDD2",
    "grid":           "E2E8F0"
  },
  "font": {
    "header_family":  "Cambria",
    "body_family":    "Calibri",
    "note": "Safe-list per pptx skill — render true-to-width in QA and ship with Office. Do not use Aptos."
  },
  "size_pt": { "title": 36, "section": 22, "body": 15, "caption": 11, "footer": 8 },
  "footer": { "text": "CONFIDENTIAL · sonar.id", "pagenum": true },
  "kpi_card_rule": "positive/neutral → card_positive fill; negative/alert → card_negative fill; primary metric +20% font",
  "forbidden": ["accent line under/above title", "vertical sidebar stripe", "single-side card border"]
}
```

**Rule:** the hardcoded colors currently scattered through `system_prompt.md` Stage F are superseded by these
tokens. Stage F builds a `T = theme.color.*` lookup once and references it everywhere.

---

## PART 4 — CANONICAL SLIDE CONTRACT (fixed scaffold · adaptive fill)

Every report ships the SAME required spine in the SAME order. What varies is only the *expandable* middle,
governed by the `arc_emphasis` dial. This makes decks comparable without making them templated — the
headlines, evidence, and argument are still 100% client-specific and still break on brand-swap.

**REQUIRED roles (must appear, in this order):**

1. `cover` — hero + 3 KPI cards
2. `scope_metodologi` — table / 3-column info box (incl. `contract_version`)
3. `executive_summary` — question box + finding cards + decision banner
4. `context`
5. `tension`
6. *(evidence block — see expandable)*
7. `reframe` — **exactly one**, dark full-bleed
8. `implication`
9. `recommendation` — Scale/Fix/Test, client owners
10. `decision` — Before→Target, smallest step
11. `references` — all URLs

**EXPANDABLE roles (count set by `arc_emphasis`, min 1 evidence slide):**
`evidence_cards` · `evidence_compare` · `evidence_time` · `adopsi_friksi` · `persona_card` (segmentation) ·
`battleground` (competitive) · `<custom_role>`. These expand for the report's heavy beat (crisis →
tension/evidence; segmentation → per-persona evidence) and compress elsewhere.

**SLIDE-COUNT BAND:** default **12–18** slides. Outside the band → justify in the brief or rebalance. Keeps
a monthly series and a cross-client set visually comparable in length.

**INVARIANTS that hold regardless of adaptation:** exactly one reframe slide · references slide always present ·
scope/methodology always slide 2 · decision always last content slide · no two consecutive slides share a
`layout_type` · the deck breaks if the brand name is swapped.

---

## HOW THIS PLUGS INTO THE ENGINE

- **Read order:** read this file **after** `quality_framework.md`, **before** Stage C compute. It is the
  invariant layer the dials are balanced against.
- **Stage C → C.5:** after the data-freeze (`deck_data.json`), run Part 2 reconciliation. HALT on unresolved fail.
- **Stage F:** load `theme.json` (Part 3) once; build all visuals from tokens. Assemble slides against the
  Part 4 contract; verify required roles present and ordering held.
- **New Tier-A guardrails** (add to `quality_framework.md`):
  - **A8 · Reconciliation gate** — Part 2 passes (or every gap resolved + footnoted) before Stage D.
  - **A9 · Locked definitions & theme** — every metric maps to a Part-1 formula; every visual constant comes
    from `theme.json`; `contract_version` + `theme_version` stamped in `deck_data.json` and on the methodology slide.
- **Versioning:** bump `contract_version` whenever a formula, the slide spine, or a token changes; surface it
  so report-to-report differences are attributable to the market, not the engine.

---
*Consistency Contract · v1.0 · the dials adapt the content; this contract locks the form, the math, the look, and the proof.*
