# QUALITY PRIORITY FRAMEWORK — A / B / C
## The balanced rulebook: what blocks delivery, what guides thinking, what stays internal

> Not every rule deserves the same weight. Treating craft preferences as fatal errors makes the engine
> rigid and templated; treating fatal errors as soft suggestions ships broken reports. This file sorts
> every quality rule into three tiers so the hard things stay hard and the flexible things stay flexible.
>
> **Tier A — Hard guardrails:** mandatory. A violation is a fatal error → fix before delivery, or halt.
> **Tier B — Thinking lenses:** flexible guidance for reasoning. Adapt to the report; never a checkbox.
> **Tier C — Lightweight QA:** silent, internal self-checks. Run them; never surface them in the output.

---

## TIER A — HARD GUARDRAILS (mandatory; block delivery)

These prevent fatal errors. Each is binary: pass or fix. Never ship a report that fails one.

### A1 · Metric consistency
A number means the same thing everywhere it appears. The same metric must not drift between the cover,
a chart, the body, and the decision slide. Freeze every internal metric once (the Stage F data-freeze)
and read from that frozen source — never re-derive a figure at render time.
- *Watch-out:* recomputing on a different filter, rounding differently in two places, or carrying a
  figure from an earlier draft computed on a smaller sample. (In testing, a "55%" from a 52-row sample
  became "31%" on the full 13k-row dataset — both correct for their data, but mixing them in one deck
  would be a fatal inconsistency.) Lock the dataset and the definitions first.

### A2 · No invented timeline
Do not promise 30/60/90 days, "weeks", "months", "quarters", or any dated milestone unless it comes from
the brief, the journey artifacts, or the user. Recommendations name the action and the owner; cadence
words ("establish a weekly cadence") are fine only if generic and not bound to a fabricated horizon.
- *Rewrite:* "stand up a safety-accountability narrative, owned by Corp Comms" — not "…over the next
  quarter" when no quarter was specified. If a timeframe genuinely helps, mark it as a suggestion the
  client confirms, not a stated plan.

### A3 · Source quality for sensitive claims
Any sensitive claim — safety, legal, health, financial, regulatory, reputational, or a statement about a
named competitor — must rest on a strong, citable source (official site, regulator, reputable news,
peer-reviewed/industry report) with a URL on the References slide. Weak sources (forums, SEO blogs,
unverified social posts) do not support sensitive claims. If no strong source exists, downgrade the claim
to a question or omit it.

### A4 · No overclaim on weak data
Match the strength of the wording to the strength of the evidence. Small samples, single data points, or
outliers get **directional** language ("suggests", "appears", "early signal"), never absolute claims, and
never a headline number that implies precision the data can't carry.
- *Watch-out:* an n=1 theme showing "net −100", or a 2-post pillar stated as a definitive share. Either
  pool it into a larger bucket, label the n, or frame it as directional. (In testing, a single Service
  post reading −100 was correctly dropped rather than charted as a finding.)

### A5 · Data integrity (internal metrics)
Internal metrics — volume, sentiment, share of voice/engagement, rankings, quotes — come ONLY from
rawdata. Quotes are real and verbatim. Public research fills context only and never substitutes an
internal metric. Inferences are signaled; hypotheses are framed as hypotheses.

### A6 · Client-owned recommendations
Every recommendation is a business action a client team owns (OWNER TEST + VENDOR-SWAP TEST). No
recommendation is a vendor feature, alert, dashboard, demo, or pilot purchase; the tool appears at most
once as an enabler. The deck closes on the client's decision, not a buy/demo/pilot CTA.

### A7 · Validation halt
If data validation fails (required fields missing, dataset can't support the requested claims), stop
before producing narrative slides. Never narrate on invalid data.

### A8 · Reconciliation gate (Stage C.5)
After the data-freeze and before any insight is written, the reconciliation gate in
`consistency_contract.md` (Part 2) must pass: every breakdown's parts sum to its stated total within
tolerance, every headline/KPI/reframe/decision number exists verbatim in the frozen `deck_data.json`,
each metric label maps to exactly one definition, and every net-sentiment figure carries its basis.
A gap is not silently shipped — it is either fixed or resolved with a disclosed residual footnote.
- *Watch-out:* a channel breakdown that sums to the total but a sentiment breakdown that overshoots by 20
  posts (null/multi-label rows) — disclose the residual and the excluded denominator; never let two slides
  imply two different totals.

### A9 · Locked definitions & theme
Internal metrics are computed only from the locked Metric Dictionary (`consistency_contract.md` Part 1);
no formula is improvised at compute time. All visual constants come from the locked `theme.json` (Part 3);
no hex or font is hardcoded at render time. The required slide spine and slide-count band (Part 4) hold.
`contract_version` and `theme_version` are stamped in `deck_data.json` and on the methodology slide so any
report-to-report difference is attributable to the market, not the engine.

---

## TIER B — THINKING LENSES (flexible; guide reasoning, don't gate)

These shape *how* to think. Use judgment; adapt per report. None of them is a checkbox, and a report is
not "wrong" for exercising them differently — only for ignoring the spirit of building a decision-first,
evidence-led argument.

### B1 · Business Decision Gravity
Every slide should pull toward the one decision at stake — but not always literally. Context, scope, and
evidence slides earn their place by building the case, not by restating the decision. Ask of each slide:
*does this move the reader closer to the decision?* If a slide serves no beat and no decision, cut it.

### B2 · Diagnostic Lens Library
Choose the analytical lens that best fits the client's problem — or invent and name one for a custom
report. The library (EVO, Awareness–Credibility–Influence, behavioural personas, SOV/scorecard,
Narrative Ownership, etc.) is a starting set, not a menu to pick from blindly. Fit beats familiarity.

### B3 · Competitor relevance
Compare competitors by their **role in the client's problem**, not by pelting every metric at every
rival. In a repositioning report, the competitive question is "who owns the narrative the client wants?"
— so contrast on that arena (e.g. who owns "sustainable"), not on a full metric-by-metric scorecard.
A small competitor may deserve one sharp slide; a category threat may deserve a battlefield table.

### B4 · Reframe strength
A report has exactly one editorial reframe (that part is Tier A discipline) — but *which* reframe is a
thinking choice. Pick the one that is most evidence-backed and most decision-shaping: it should name the
real bottleneck, survive scrutiny against the strongest data, and change what the client does next. Test
candidate reframes against the data and choose the sharpest, not the catchiest.

---

## TIER C — LIGHTWEIGHT QA (internal only; never in the output)

Run these as silent self-checks before delivery. They are reasoning steps, not slides — never narrate
them, never add a "QA" or "self-critique" section to the client-facing deck.

### C1 · Client red-team sanity check
Read the deck as the client's sharpest skeptic. Where would they say "that's not true," "that's obvious,"
"you don't understand our business," or "this could describe anyone"? Fix what wouldn't survive that room.

### C2 · Headline metric scan
Scan every headline and KPI number against the frozen data. Does each figure exist in the data, mean what
the headline implies, and match everywhere it repeats? Catch drift, rounding mismatches, and stale numbers.

### C3 · Source weakness check
List every external claim and its source. Flag any sensitive claim resting on a weak source (Tier A3) and
any number that looks internal but actually came from the web. Strengthen or drop.

### C4 · Generic recommendation check
For each recommendation, ask: would this read identically for any client in this category, or for any
monitoring vendor? If yes, it's generic — rewrite it as this client's specific move, grounded in this
report's finding, owned by a named client team.

---

## HOW THE TIERS INTERACT

- **A overrides everything.** A sharp reframe (B4) that overclaims on weak data (A4) is rejected — fix the
  claim first. A compelling competitive story (B3) built on a weak source for a sensitive claim (A3) is
  rejected — strengthen the source first.
- **B is where the report earns "consultant-grade."** Two reports can both pass all of A and still differ
  in quality entirely because of B. This is the craft layer; spend judgment here.
- **C never appears.** Its job is to make A and B true in the final artifact, silently. If a C check
  fails, fix the deck — do not add commentary explaining that you checked.
