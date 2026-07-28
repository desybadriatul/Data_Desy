# QUALITY PRIORITY FRAMEWORK — A / B / C
## The balanced rulebook: what blocks delivery, what guides thinking, what stays internal

> Not every rule in `system-prompt.md` deserves the same weight. Treating craft preferences as
> fatal errors makes the deck rigid and templated; treating fatal errors as soft suggestions ships
> a deck that overclaims, invents scope, or oversells. This file sorts every quality rule into
> three tiers so the hard things stay hard and the flexible things stay flexible.
>
> **Tier A — Hard guardrails:** mandatory. A violation is a fatal error → fix before delivery, or
> set `content_gate_status: BLOCKED`.
> **Tier B — Thinking lenses:** flexible guidance for strategy and story. Adapt to the client;
> never a checkbox.
> **Tier C — Lightweight QA:** silent, internal self-checks. Run them before release; never
> surface them in client-facing output.

---

## TIER A — HARD GUARDRAILS (mandatory; block delivery)

These prevent fatal errors — the kind that would embarrass the sales team in the room or expose
Anthropic/Dataxet:Sonar to a commercial or factual liability. Each is binary: pass or fix. Never
ship a deck that fails one.

### A1 · Evidence integrity
Every material claim is classified per the Evidence & Claim Dictionary (`consistency_contract.md`
Part 1). A `STRATEGIC_HYPOTHESIS` or `ANALYTICAL_INFERENCE` is never worded as a
`CLIENT_CONFIRMED_FACT`. Internal metrics, quotes, and evidence come only from confirmed sources;
research fills context only.
- *Watch-out:* a confident headline built on a single social post or one competitor incident,
  presented as if it proves an ongoing pattern. One incident proves the event, not the trend.

### A2 · No invented commercials
Never fabricate price, discount, contract term, scope, SLA, timeline, or benchmark result. Every
price traces verbatim to `pricing.md`; every capability traces to `product-capability.md` with an
honest status (`CONFIRMED` / `PROPOSED` / `OPTIONAL` / `NEEDS_VALIDATION`). Alert speed or
detection time is never stated as a guaranteed SLA without a confirmed source — use "proposed
target" or "to be validated during pilot" instead.

### A3 · Single-language lock
All client-facing text — kicker, headline, chart labels, CTA, source notes — stays in
`deck_language` throughout. English is reserved for fixed product proper names and internal JSON
keys only. No mixing, no exceptions for "it sounds punchier in English."

### A4 · No pattern from a single source
A claim that generalizes from one incident, one post, or one data point to a "pattern" or "trend"
must be corroborated with a second independent source or downgraded to describe the single
instance only. This is the sales-deck equivalent of overclaiming on weak data.

### A5 · Client-owned decision, appropriately sized CTA
The CTA is the smallest decision that fits the client's confirmed readiness — never more than one
step beyond it. Forbidden phrasing: "contact us" · "reach out" · "book a demo" · "let's connect" ·
"you must act now." A deck never closes on manufactured urgency.

### A6 · Delivery format matches problem type
Monthly report is never the primary solution when the classified `primary_problem_type` is
`TIME_TO_KNOW` or `TIME_TO_REACT`. The delivery format (alert / dashboard / incident brief / digest
/ monthly report / executive readout / raw export) is chosen to match the bottleneck, not to what
is easiest to describe.

### A7 · Capability honesty
A capability marked `OPTIONAL`, `NEEDS_VALIDATION`, or `PROPOSED` never appears framed as a
committed deliverable anywhere in the deck — not on the solution slide, not in the pilot spec, not
in the battle card.

### A8 · Reconciliation gate (`consistency_contract.md` Part 2)
Before CONTENT_DRAFT is finalized, the reconciliation gate must pass: every stat/claim traces to a
source, every reused number is identical everywhere it recurs, every capability status is
consistent, pricing is consistent (or absent when `include_pricing: false`), and every
single-source-as-pattern or weak-evidence flag is resolved. A gap is not silently shipped — it is
fixed or logged as a `missing_data_flags` entry.

### A9 · Locked tokens & slide contract (`consistency_contract.md` Parts 3–4)
Every rendered color and font comes from the Brand Kit token table, never a hardcoded value that
disagrees with it. The required slide spine (cover → problem → cost of inaction → evidence →
reframe → solution fit → proof → risk reversal → CTA → references) holds in order, references is
always last, and there is exactly one editorial-statement/reframe slide.
`contract_version` and `theme_version` are stamped in `deck_metadata`.

### A10 · Validation halt / clarification request
If a critical gap blocks progress — no confirmed business question, unknown stakeholder, core
evidence missing — output a `CLARIFICATION REQUEST` before proceeding. Never fabricate a missing
input to force the deck to look complete.

---

## TIER B — THINKING LENSES (flexible; guide strategy and story, don't gate)

These shape *how* to think about a deal. Use judgment; adapt per client. None of them is a
checkbox, and a deck is not "wrong" for exercising them differently — only for ignoring the spirit
of building a decision instrument that fits this specific buyer.

### B1 · Buyer-belief gravity
Every slide should pull toward one of the four buyer-belief steps (real problem → real cost →
Sonar fit → safe next step) — but not always literally. Context and evidence slides earn their
place by building the case, not by restating the CTA. Ask of each slide: *does this move the buyer
closer to the smallest safe yes?* If a slide serves no commercial pillar (`WHY NOW` / `WHY SONAR` /
`WHY SAFE` / `PROVE FIRST`), cut it.

### B2 · Problem-type-to-solution fit
Classifying the primary problem type (Time-to-Know / Time-to-React / Signal-vs-Noise /
Proof-to-Decide / Blind-Spot) is Tier A discipline; *how* that classification shapes the story,
which secondary type gets a supporting lane, and how much weight each gets, is a thinking choice.
Fit the narrative to the client's actual bottleneck, not to whichever problem type is easiest to
pitch with Sonar's current feature set.

### B3 · Competitor relevance
Compare competitors by their **role in the client's decision**, not by pelting every metric at
every rival. If the buyer is comparing Sonar against one incumbent tool, a sharp one-slide contrast
on the dimension that matters to them beats an exhaustive feature matrix. Pull facts only from
`competitors.md`; never invent a rival's number to make the contrast land harder.

### B4 · Governing point of view / reframe strength
A deck carries exactly one strategic reframe (Tier A discipline) — but *which* reframe, and how
sharply it's phrased, is a thinking choice. Pick the one that is most evidence-backed and most
decision-shaping for this buyer: it should name the real bottleneck, survive the buyer's own
scrutiny, and change what they're willing to approve next. Test candidate framings against the
evidence and choose the sharpest, not the catchiest.

### B5 · Stakeholder lane judgment
When multiple stakeholders are in the room with meaningfully different needs, deciding whether they
need fully separate solution lanes or can share one slide with role-specific callouts is a judgment
call — driven by how different their pains actually are, not by a fixed rule of "always separate"
or "always merge."

---

## TIER C — LIGHTWEIGHT QA (internal only; never in the output)

Run these as silent self-checks before release. They are reasoning steps, not slides — never
narrate them, never add a "QA" or "self-critique" section to the client-facing deck.

### C1 · Client red-team sanity check
Read the deck as the buyer's sharpest skeptic. Where would they say "that's not true," "that's
generic," "you don't understand our business," or "this could be sent to any competitor unchanged"?
Fix what wouldn't survive that room. This is the client-specificity test and the brand-swap test
run together.

### C2 · Headline / number scan
Scan every headline, stat callout, and CTA number against `data_sources_used`. Does each figure
exist, mean what the headline implies, and match everywhere it repeats? Catch drift, rounding
mismatches, and a number quietly rewritten between the strategy stage and the final slide copy.

### C3 · Source-weakness check
List every external and competitor claim and its source. Flag any sensitive or quantified claim
resting on a weak or single source (Tier A4) and any number that reads as internal Sonar data but
actually came from an unverified public post. Strengthen or drop.

### C4 · Generic-slide check
For each problem, evidence, solution, and CTA slide, ask: would this read identically for any other
client in this category, or could it be a Sonar sales-deck template with the logo swapped? If yes,
rewrite it around this client's specific evidence and situation.

### C5 · Narrative-thread check
For every consecutive slide pair, apply the test: "We established [X], so the audience is now ready
to consider [Y]." If the thread breaks anywhere, resequence, merge, or cut rather than letting the
deck jump.

---

## HOW THE TIERS INTERACT

- **A overrides everything.** A sharp reframe (B4) that rests on an unresolved reconciliation gap
  (A8) is rejected — resolve the gap first. A compelling competitive contrast (B3) built on an
  invented rival number (A2) is rejected — pull the real number or drop the claim.
- **B is where the deck earns "senior commercial leader in the room."** Two decks can both pass
  every Tier-A check and still differ entirely in persuasive quality because of B. This is the
  craft layer; spend judgment here.
- **C never appears.** Its job is to make A and B true in the final artifact, silently. If a C
  check fails, fix the deck — do not add commentary explaining that you checked.
