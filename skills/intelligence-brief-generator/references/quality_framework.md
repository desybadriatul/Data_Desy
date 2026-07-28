# QUALITY PRIORITY FRAMEWORK — A / B / C
## The balanced rulebook: what blocks delivery, what guides thinking, what stays internal

> Not every rule deserves the same weight. Treating craft preferences as fatal errors makes the brief
> rigid and templated; treating fatal errors as soft suggestions ships an unusable or misleading brief.
> This file sorts every quality rule into three tiers.
>
> **Tier A — Hard guardrails:** mandatory. A violation is a fatal error → fix before delivery, or halt.
> **Tier B — Thinking lenses:** flexible guidance for reasoning. Adapt per engagement; never a checkbox.
> **Tier C — Lightweight QA:** silent, internal self-checks. Run them; never surface them in the output.

---

## TIER A — HARD GUARDRAILS (mandatory; block delivery)

### A1 · Evidence tagging discipline
Every specific claim carries `[Cx]` (client-provided), `[Sx]` (public source), or `[Hx]`
(hypothesis/inference). No untagged specific fact. A claim without a tag is either removed or converted
into a tagged, qualified statement before delivery.

### A2 · No invented vendor capability, pricing, or client fact
The vendor's capability catalog comes only from what the user supplied, a researched URL (cited `[Sx]`),
or a prior brief carried over in this conversation — never from assumption. Client facts come only from
`[C]` or cited `[S]`. If the vendor context is thin, keep the fit mapping general and say so in
`meta.vendor_context_status` and `assumptions_and_missing_info` — never fill the gap with a fabricated
feature or price.

### A3 · Layer 1 length cap
Layer 1 stays at or under ~2 pages (~900 words outside tables). If it runs long, cut Layer 1 content —
never truncate Layer 2. Layer 2 is the repository and must stay complete regardless of Layer 1's length.

### A4 · Layer 1 ↔ Layer 2 consistency
No fact, number, or claim may contradict between the two layers. Layer 1 is a derived summary of Layer 2,
never an independent draft.

### A5 · Complete, valid Layer 2 JSON
Every schema key from `system_prompt.md` is present, using `null`, `[]`, or `""` where empty — never a
deleted key. The object must be valid, parseable JSON (no trailing commas, no comments). Downstream
systems consume this directly; a malformed or incomplete object breaks the handoff.

### A6 · Source quality for sensitive/material claims
Financial, legal, safety, regulatory, reputational, or named-competitor claims need a credible, dated,
cited source. Single-source or blog/UGC-supported claims are explicitly qualified as such, never presented
with the confidence of a well-supported fact.

### A7 · Client-stated needs are never silently overridden
If independent research (`[S]`) suggests something different from what the client explicitly stated
(`[C]`), both are shown, with the disagreement flagged as a confirmation item — never resolved unilaterally
by picking the "more credible-looking" source.

### A8 · No manufactured urgency
"Why Now" / cost-of-delay content is evidence-based (a real event, trend, or client-stated timeline) —
never a scarcity gimmick, invented deadline, or generic "act now" framing.

---

## TIER B — THINKING LENSES (flexible; guide reasoning, don't gate)

### B1 · Primary-problem classification
Classify from the client's stated objective, not an assumed risk category — but use judgment for how
`secondary_problem` and framing interact. A client talking about awareness measurement may still need
crisis-monitoring scope; the classification choice shapes "The Angle" without ignoring the safety layer.

### B2 · Sector adaptation
Reinterpret field meaning for non-consumer sectors (competitors → narrative actors/comparators/regulators;
marketing strategy → public affairs/ESG communication) — a judgment call per client, not a fixed mapping
table to apply mechanically.

### B3 · Meeting-stage emphasis
Use the stage-to-focus map in `system_prompt.md` as a starting weight, not a rule that empties the other
sections. Every Layer 1 block still appears; the emphasis simply shifts where the meeting needs it.

### B4 · Opening/demo variant selection
Choosing Variant A (provocative) vs. B (empathetic) is a judgment call based on contact seniority, known
sensitivities, and context — not a coin flip. State the reasoning in one short clause in Layer 1.

---

## TIER C — LIGHTWEIGHT QA (internal only; never in the output)

Run these as silent self-checks before delivery. Never narrate them, never add a "QA" section to the brief.

### C1 · Citation consistency pass
Re-trace every `[Cx]`/`[Sx]` in the document; confirm it resolves to a real, matching `source_registry`
entry. Fix mismatches; remove claims that can't be traced.

### C2 · Anti-generic scan
For every pain point and recommendation: would this read identically for any similar client in this
industry? If yes, rewrite it as specific to this client's actual evidence.

### C3 · Personal-data scrub
Confirm no private phone numbers, personal emails, or unnecessary personal detail from `[C]` made it into
either layer. Reduce to role/title.

### C4 · Schema completeness check
Confirm every Layer 2 key from the schema exists in the output, even if empty, and that the JSON parses
cleanly.

---

## HOW THE TIERS INTERACT

- **A overrides everything.** A sharp opening hook (B4) built on an unverified capability claim (A2) is
  rejected — fix the claim first. A well-argued urgency case (B1 framing) that isn't evidence-based (A8) is
  rejected — strengthen the evidence or cut it.
- **B is where the brief earns "consultant-grade."** Two briefs can both pass all of A and still differ
  entirely in usefulness because of B — this is the craft layer where judgment matters most.
- **C never appears.** Its job is to make A and B true in the final artifact, silently. If a C check fails,
  fix the brief — do not add commentary explaining that you checked.
