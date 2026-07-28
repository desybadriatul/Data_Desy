# QA Checklist & Change Rules

Run this before any deck reaches a client, or before the prompt/skill is
changed. This is the operational checklist; the underlying logic and the A/B/C
severity of each rule live in `quality_framework.md`, and the locked
evidence/number/design invariants it checks against live in
`consistency_contract.md`.

## Pre-send QA checklist

| Area | Validation question |
|---|---|
| **Strategy** | One primary business question, a selected angle, and a CTA that fits readiness. |
| **Client specificity** | Problem, evidence, solution, and decision use client anchors, not an industry template. Would the deck survive the brand-swap test (`consistency_contract.md` Part 4)? |
| **Evidence** | Every external claim has a source, date, and unit/period where relevant; inference is not presented as fact. |
| **Reconciliation** | The Reconciliation & Provenance Gate (`consistency_contract.md` Part 2) shows `overall_status: PASS` — every reused stat is identical everywhere it appears, every capability/price status is consistent. |
| **Commercial safety** | No invented price, scope, SLA, timeline, or product claim. |
| **Story** | Problem and urgency appear before the solution; the deck does not open with a vendor profile; references are last. |
| **Visual** | At least 2–3 real evidence charts, 1 editorial statement, varied layout, no three card-grids in a row, and every color/font traces to the locked tokens (`consistency_contract.md` Part 3). |
| **Language** | Kicker, title, chart labels, CTA, and source notes are all in one client language. |
| **Production** | FINAL_PRODUCTION passes only after the PPTX is rendered and visually inspected. |

## Hard blocks (any one sets `content_gate_status: BLOCKED`)

- An unsupported material claim is stated as confirmed fact.
- Scope, pricing, or implementation detail was invented.
- Client-facing content mixes two languages.
- A single source is used as evidence of a recurring pattern without
  corroboration.
- The CTA exceeds the client's confirmed decision readiness by more than one
  step.
- A HIGH-impact missing-data flag is unresolved and its claim remains in the
  deck as fact.
- Solution framing is inconsistent with the classified `primary_problem_type`
  and no override is documented.
- Alert speed or detection time is stated as a guaranteed SLA without a
  confirmed source.
- Monthly report is the primary solution when the primary problem type is
  TIME_TO_KNOW or TIME_TO_REACT.
- A capability marked OPTIONAL, NEEDS_VALIDATION, or PROPOSED is presented as a
  committed deliverable.
- The Reconciliation & Provenance Gate has an unresolved fail — a reused
  number, capability status, or price is inconsistent across slides.
- A rendered color, font, or slide order disagrees with the locked tokens and
  Canonical Slide Contract.

## Actively hunt for, before release

Inference presented as fact; metric mismatch; repeated argument; generic
language that could fit any client; invented scope; feature dumping; narrative
thread breaks; language drift; layouts too repetitive or dense; a solution chain
broken between problem and decision enabled. See `quality_framework.md` Tier C
for the full silent self-check list (client red-team check, headline/number
scan, source-weakness check, generic-slide check, narrative-thread check).

## Rules for changing the prompt/skill itself

Treat the System Prompt, `quality_framework.md`, and `consistency_contract.md`
as stable infrastructure. Change them only through a targeted change request,
never casually:

1. **Targeted edit only** — change only the section that genuinely needs
   updating.
2. **Preserve by default** — no large refactor without a reason and approval.
3. **Dependency check** — check the impact on the User Prompt, output contract,
   renderer, QA, and — for anything touching evidence rules, numbers, tokens,
   or the slide spine — on `consistency_contract.md`.
4. **No silent rename** — do not change a JSON key, layout type, mode order, or
   evidence class without approval.
5. **Version bump** — if the change alters a formula, a reconciliation check,
   a design token, or the required slide spine, bump `contract_version` and/or
   `theme_version` so deck-to-deck differences stay attributable to the deal,
   not the engine.
6. **Test with one real use case** — verify content, evidence, CTA, and render
   stay safe after the change.
