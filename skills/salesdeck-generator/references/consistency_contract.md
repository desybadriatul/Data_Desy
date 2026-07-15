# CONSISTENCY CONTRACT — The Invariant Layer
## What must be identical across every deck, so client-adaptation never drifts into inconsistency

> Strategy, story, and design direction all **adapt** per client — that is the point of
> STRATEGY_REVIEW and CONTENT_DRAFT. This file is their counterweight: it locks the parts that
> must **never** vary, so two decks — for two different clients, or two decks for the same client
> across sales stages — are *comparable, traceable, and recognizably the same product* built by
> the same studio.
>
> **The reconciliation:** strategy and story adapt CONTENT (the argument, the angle, the emphasis).
> This contract locks EVIDENCE, NUMBERS, THEME, and STRUCTURE (the proof, the math, the look, the
> scaffold). Anti-template still holds — the scaffold is empty structure; the client-specific
> argument still fills it, and the deck still fails the **client-specificity test** if the client
> name were swapped out. A fixed skeleton is not a template; identical *content* is.
>
> This contract is **versioned**. Stamp `contract_version` and `theme_version` into
> `deck_metadata` in the Content Contract JSON. If a client requests a revised deck later in the
> sales cycle, the same `contract_version` should apply unless a formula, gate, or token changed —
> so any drift between decks is attributable to the deal, not to the engine.

---

## PART 1 — EVIDENCE & CLAIM DICTIONARY (LOCKED)

Every claim that reaches a slide carries exactly ONE evidence class, ONE confidence rating, and —
if it is a number reused anywhere else in the deck — exactly ONE frozen value. Nothing is
re-derived, re-rounded, or re-worded differently at a different point in the deck.

### 1.1 Evidence classes (unchanged from `system-prompt.md`, restated here as the locked list)

`CLIENT_CONFIRMED_FACT` · `PUBLIC_VERIFIED_FACT` · `INTERNAL_SONAR_FACT` ·
`ANALYTICAL_INFERENCE` · `STRATEGIC_HYPOTHESIS` · `RECOMMENDATION` · `UNRESOLVED_GAP`

Every entry in `evidence_pack` and every `stat_callout` on the cover carries one of these. A
`STRATEGIC_HYPOTHESIS` or `ANALYTICAL_INFERENCE` is never worded as if it were a
`CLIENT_CONFIRMED_FACT` or `PUBLIC_VERIFIED_FACT`, no matter how confident the copy sounds.

### 1.2 Source Truth Hierarchy (unchanged from `system-prompt.md`)

Client-confirmed statements → approved commercial docs / Product Capability doc / approved
credentials → Pre-Sales/Intelligence Brief → Insight Report / client-specific evidence → verified
public sources → industry research / competitor evidence → analytical inference → strategic
hypothesis. A lower-ranked source never silently overrides a higher-ranked one; a conflict is
logged in `source_conflicts`, not resolved by picking whichever number sounds better.

### 1.3 Stat-reuse rule (new — the sales-deck equivalent of a metric dictionary)

A deck almost always repeats its strongest numbers: on the cover as a stat callout, again in an
evidence slide, again in the cost-of-inaction framing, sometimes again in the CTA. **The same
number, in the same unit, with the same period, must appear identically everywhere it recurs.**

- Freeze every reused number once, in `data_sources_used`, with a `source_id`.
- Every later appearance of that number (cover, evidence, cost-of-inaction, CTA) references the
  same `source_id` — it is not retyped from memory or re-approximated.
- If two legitimate sources give two different numbers for what looks like the same claim (e.g. a
  client-confirmed figure vs. a public estimate), pick ONE as the deck's number per the Source
  Truth Hierarchy, and do not let the other quietly surface elsewhere in the deck.
- *Watch-out:* a "cost of inaction" percentage computed one way in the strategy stage and rounded
  or recomputed differently by the time it reaches the cover stat callout. Lock it once.

### 1.4 Pricing, capability, and competitor facts (unchanged authority, restated as locked)

- Every price figure traces verbatim to `knowledge-base/pricing.md`. Never adjusted, estimated, or
  rounded differently on different slides.
- Every capability claim traces to `knowledge-base/product-capability.md` and carries a status:
  `CONFIRMED` · `PROPOSED` · `OPTIONAL` · `NEEDS_VALIDATION`. A capability's status is set once and
  held everywhere it is mentioned — it does not read as "confirmed" on the solution slide and
  "proposed" in the pilot spec.
- Every competitor claim traces to `knowledge-base/competitors.md`. Never a fabricated competitor
  number, even when the story would be stronger with one.

---

## PART 2 — RECONCILIATION & PROVENANCE GATE (Tier-A · runs before CONTENT_DRAFT is finalized)

A mandatory gate that runs once, after `sales_strategy` and the `evidence_pack` / `stat_callouts`
are drafted and before the deck is declared content-complete. Its job: prove every number and
claim in the deck is internally consistent and fully traceable **before** QA is run and before
FINAL_PRODUCTION renders anything. This is the sales-deck equivalent of Stage C.5 in the insight
report engine, and it BLOCKS delivery on failure exactly like any Tier-A guardrail.

**Checks (all must pass or be explicitly resolved):**

1. **Source existence.** Every numeric claim in `cover_slide.stat_callouts` and every
   `evidence_pack` entry with `evidence_value` set has a matching entry in
   `deck_metadata.data_sources_used` (via `source_id`) or is explicitly labeled
   `STRATEGIC_HYPOTHESIS` / `UNRESOLVED_GAP` and never stated as fact.
2. **Stat-reuse consistency.** Any number appearing on more than one slide (cover ↔ evidence ↔
   cost-of-inaction ↔ CTA) is character-identical in value, unit, and period each time it appears.
   A mismatch is not shipped — fix the drift or explain it as two genuinely different metrics.
3. **Capability status consistency.** Each capability's status (`CONFIRMED` / `PROPOSED` /
   `OPTIONAL` / `NEEDS_VALIDATION`) is the same wherever it is referenced — solution slide, pilot
   spec, battle card. No capability is "confirmed" in one place and "proposed" in another.
4. **Pricing consistency.** If `include_pricing: true`, every price figure matches
   `pricing.md` verbatim and appears identically wherever it recurs. If `include_pricing: false`,
   no price figure appears anywhere in the deck.
5. **Single-source-as-pattern flag.** Any claim that generalizes from one incident, one post, or
   one data point to a "pattern" or "trend" is flagged and either corroborated with a second
   independent source or downgraded to describe the single instance only.
6. **Weak-evidence flag.** Any `ANALYTICAL_INFERENCE` or `STRATEGIC_HYPOTHESIS` that reads with
   confident, fact-like phrasing is flagged for rewrite into hedged language ("suggests",
   "indicates", "early signal") before it ships.

**Output a machine-checkable record** in the Content Contract JSON under `reconciliation`:

```json
"reconciliation": {
  "contract_version": "1.0",
  "checks": [
    { "name": "source_existence", "claims_checked": 14, "unsupported": 0, "status": "PASS" },
    { "name": "stat_reuse_consistency", "reused_numbers": 3, "mismatches": 0, "status": "PASS" },
    { "name": "capability_status_consistency", "capabilities_checked": 6, "conflicts": 0, "status": "PASS" },
    { "name": "pricing_consistency", "include_pricing": false, "status": "N/A" },
    { "name": "single_source_pattern_flags", "flagged": 1,
      "status": "RESOLVED", "resolution": "downgraded 'competitor is losing the narrative' to describe the one confirmed incident, not a trend" }
  ],
  "overall_status": "PASS"
}
```

If `overall_status` ≠ `PASS` and any check is unresolved → **do not finalize CONTENT_DRAFT**, and
never proceed to FINAL_PRODUCTION. Surface the unresolved item as a `missing_data_flags` entry or a
`CLARIFICATION REQUEST` instead of shipping it silently.

---

## PART 3 — DESIGN TOKEN THEME (LOCKED)

Two things must never conflict: what `system-prompt.md` says about color and type, and what the
Brand Kit (`references/brand-kit/`) actually specifies. **The Brand Kit is the single source of
truth for every rendered hex and font.** Stage F / FINAL_PRODUCTION reads tokens; it never
hardcodes a hex or a font inline, and any color or font mentioned elsewhere in this skill's
references is a *description* of the token, not a second source of truth.

```json
{
  "theme_version": "1.0",
  "font": {
    "header_family": "Cambria",
    "body_family": "Calibri",
    "note": "Matches references/brand-kit/01_BRAND_SYSTEM.md and template/theme.js exactly. Never Aptos. Never substitute a heading font at render time."
  },
  "token_source_of_truth": "references/brand-kit/template/theme.js — one block per client under `clients`.",
  "token_slots": ["navy", "navy2", "blue", "blueMid", "blueSoft", "red", "redSoft", "ink", "slate", "cloud", "line", "white", "gold (optional, brand-dependent)"],
  "client_palette_rule": "When client_brand_assets_available is true and a client block exists in theme.js (or is added following 02_CLIENT_PALETTES.md), that palette drives 90%+ of the deck. It is the DOMINANT color system — titles, dark cards, kicker bars, chart accents.",
  "agency_accent_rule": "dataxet.green (2BA32B) and dataxet.periwinkle (7C86E8) are RESERVED for the Dataxet:Sonar agency wordmark only. They never become the deck's dominant color, a chart color, or a client-slide accent — regardless of which client palette is active.",
  "fallback_palette_rule": "When client_brand_assets_available is false or no client block exists yet, use a neutral Sonar-fallback palette (navy #1B3A6B / accent red #E63946 / positive green #2E8B57 / neutral grey #6B7280 / background #F7F9FC) as a STAND-IN token set only — never as the agency accent, and flag `client_brand_assets_available: false` plus a missing_data_flag so the palette gets replaced with the client's real brand before the deck ships.",
  "kicker_and_card_rule": "Rounded cards, icon chips, number ovals, and the navy kicker bar per references/brand-kit/01_BRAND_SYSTEM.md — these motifs are the house style and hold across every client palette.",
  "forbidden": ["accent underline beneath titles", "full-width header/footer color stripes", "thin single-side edge-stripes on cards", "cream/beige default background", "centered body paragraphs", "text-only slides with no card, chart, icon, or placeholder", "Aptos or any non-safe-list font"]
}
```

**Rule:** wherever `system-prompt.md`'s "Sonar defaults" or "DESIGN SYSTEM" section names a hex or
a font, treat that text as a *summary pointer* to this table, not an independent value. If they
ever appear to disagree, this contract wins, and `system-prompt.md` should be corrected to match on
the next edit (see `qa-and-change-rules.md`).

---

## PART 4 — CANONICAL SLIDE CONTRACT (fixed scaffold · adaptive fill)

Every deck ships the SAME required narrative spine in the SAME order. What varies is only the
*expandable* middle (evidence depth, number of stakeholder solution lanes, number of objections
addressed) and the slide count within the band for the meeting length. This keeps decks comparable
across clients and across a sales cycle without making any one of them a template — headlines,
evidence, and the argument stay 100% client-specific and the deck still fails the brand-swap test
if the client's identity is stripped out.

**REQUIRED roles (must appear, in this order):**

1. `cover` — client-world hero + 2–3 client-specific stat callouts + "prepared for"
2. `problem` — the client's reality and stakes, opened from their world, never a Sonar profile
3. `cost_of_inaction` — grounded cost of staying here, classed `QUANTIFIED` \|
   `EVIDENCE_SUPPORTED_QUALITATIVE` \| `HYPOTHESIS_ONLY` \| `NOT_REQUIRED`
4. *(evidence block — see expandable)*
5. `strategic_insight` / `reframe` — **exactly one**, the governing point of view, ideally a
   dark/full-bleed editorial-statement slide (see Part 4 Invariants)
6. `solution_fit` — Sonar capability framed as client outcome, via the Solution Design chain
7. `proof` — case study, sample output, or methodology proof (never invented results)
8. `risk_reversal` — de-risking the ask: pilot terms, guardrails, "why safe to try"
9. `cta` — smallest appropriate decision, phrased per the forbidden/allowed CTA language rules
10. `references` — Source ID / Name / URL / Publication Date / Access Date / Description /
    Data-Claim-Used / Slide-Supported — always the final slide

**EXPANDABLE roles (count set by sales stage, stakeholder mix, and problem type; min 1 evidence
slide):** `evidence_cards` · `evidence_chart` · `stakeholder_solution_lane` (one per distinct
stakeholder need) · `battle_card_objection` · `pilot_use_case` · `<custom_role>`. These expand for
the deal's heavy beat (a crisis-driven deal leans on problem/cost-of-inaction/evidence; a
multi-stakeholder deal expands solution lanes) and compress elsewhere.

**SLIDE-COUNT BAND (references excluded):** ≤15 min → 6–9 · 16–25 min → 8–12 · 26–40 min → 10–15 ·
40+ min → 12–18, per `presentation_duration_minutes`. Do not pad to fill a range; a slide with no
job (see B1 in `quality_framework.md`) is cut, not kept for count.

**INVARIANTS that hold regardless of adaptation:**

- Exactly one editorial-statement / reframe slide, carrying the `governing_point_of_view`.
- `references` is always the final slide — never a generic "Thank You".
- `problem` opens the deck's substantive content — the deck never opens with a Sonar company
  profile ahead of the client's own situation.
- No two consecutive slides share a `layout_archetype` unless the repetition is an intentional,
  labeled comparison.
- **Brand-swap test:** if the client's name, industry, and evidence were stripped out and the deck
  would still read coherently for a different company in the same category, it is a template —
  rebuild the problem, evidence, and solution-fit slides around this client's actual situation.

---

## HOW THIS PLUGS INTO THE ENGINE

- **Read order:** read this file **after** `quality_framework.md`, **before** drafting
  `sales_strategy.cost_of_inaction`, `evidence_pack` entries, or `cover_slide.stat_callouts`. It is
  the invariant layer client adaptation is balanced against.
- **CONTENT_DRAFT → gate:** once strategy, evidence, and stat callouts are drafted and before the
  Content Contract JSON is declared complete, run Part 2 reconciliation. Do not finalize
  CONTENT_DRAFT on an unresolved fail.
- **FINAL_PRODUCTION:** load the Part 3 tokens from `references/brand-kit/template/theme.js` (or
  the fallback palette, flagged) once; build every visual from those tokens. Assemble slides
  against the Part 4 contract; verify required roles present and ordering held.
- **New Tier-A guardrails** (mirrored in `quality_framework.md`):
  - **A8 · Reconciliation gate** — Part 2 passes (or every gap resolved + flagged) before
    CONTENT_DRAFT is finalized.
  - **A9 · Locked tokens & slide contract** — every color/font comes from Part 3; the required
    slide spine and slide-count band from Part 4 hold; `contract_version` + `theme_version` are
    stamped in `deck_metadata`.
- **Versioning:** bump `contract_version` whenever the evidence dictionary, the reconciliation
  checks, the token table, or the slide spine changes; surface it so deck-to-deck differences are
  attributable to the deal, not the engine.

---
*Consistency Contract · v1.0 · strategy and story adapt the content; this contract locks the
evidence, the numbers, the look, and the scaffold.*
