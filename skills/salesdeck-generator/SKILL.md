---
name: salesdeck-generator
description: >-
  Generate client-specific, evidence-aware B2B sales decks for DATAXET:SONAR
  (media-intelligence) following the Sonar Sales Deck Generator methodology
  (System Prompt v6). Use this WHENEVER the user wants to build, draft, or
  strategize a Sonar/Dataxet sales presentation, pitch deck, or client deck —
  including requests phrased as "buatkan sales deck", "deck untuk klien X",
  "strategy review", "content draft", "final production PPTX", "pitch deck
  Sonar", or any request that supplies a client brief, MoM/handover, evidence
  pack, or commercial boundary and asks for a persuasive enterprise deck. Also
  trigger for the three execution phases STRATEGY_REVIEW, CONTENT_DRAFT, and
  FINAL_PRODUCTION, and for producing the Content Contract JSON or the editable
  PPTX. Use even if the user does not say the word "skill" — if they want a
  Sonar/Dataxet B2B sales deck, use this.
---

# DATAXET:SONAR — Sales Deck Generator

This skill turns an intelligence brief, client evidence, and commercial
boundaries into a single, persuasive enterprise B2B sales deck. The deck is not
a template — it is a decision instrument built for **this client** and **this
meeting**, grounded in traceable evidence, and designed to guide a buyer from
problem awareness to the smallest appropriate commitment.

**Design the narrative arc first. Build slides to serve the story, not the
other way around.**


## Cogan MCP integration addendum

This skill is **Jalur 0B — Sales Deck / Pitch Deck** inside the Cogan universe.
Use it only when the user asks for a sales deck, pitch deck, proposal deck,
commercial deck, deck jualan, client presentation, or final PPTX for a
Dataxet/Sonar/Cogan commercial conversation.

Preferred input is the output of the Intelligence Brief / Client Brief skill.
Treat a Client Intelligence Brief, presales brief, account brief, meeting prep,
or BD cheat-sheet as the highest-priority brief source. If the user only gives
raw context, ask for material missing fields or create a small sales-deck intake
inside this task; do not pretend that a full client brief exists.

Do **not** use this skill when the user only asks for a client brief, presales
brief, intelligence brief, account brief, meeting prep, or BD cheat-sheet. Those
requests belong to `get_intelligence_brief_guide()`.

Do **not** call report workflows (`create_*_report_workflow`), `get_report_guide()`,
or anomaly tools for a sales deck request unless the user explicitly asks to
validate data or turn an approved deck into a report workflow later.

Default behavior: produce CONTENT_DRAFT first unless the user explicitly asks
for PPTX/final production or has already approved the content. For a PPTX/final
file, confirm that the content gate is not BLOCKED before rendering.

## When and how to use this skill

Trigger on any request to build, draft, or strategize a Sonar/Dataxet sales
deck. The work always runs in this order — never start from design:

```
input → diagnosis → strategy → story → content → validation → PPTX
```

The whole operation is governed by three **execution phases**. Identify which
one the user wants (ask if unclear), then follow it:

| Phase | What you produce | Use when |
|---|---|---|
| **STRATEGY_REVIEW** | Strategy Review JSON + concise summary. No slide copy, no PPTX. | The brief is immature or the commercial direction isn't agreed yet. |
| **CONTENT_DRAFT** | Complete Content Contract JSON + concise summary. No PPTX unless asked. *(default mode)* | Strategy is clear; content needs review before production. |
| **FINAL_PRODUCTION** | Validated Content Contract JSON + editable PPTX + visual QA + change log. | Content gate has passed and the deck is approved for production. |

## Read order

Read four layered references before producing a deck — this is what makes the output
consultant-grade and reproducible rather than a one-off draft:

- **`references/system-prompt.md`** — *how to execute.* The brain of this skill: the persona,
  evidence hierarchy, problem typology, strategy scoring, solution chain, story architecture,
  design system, and QA gates. Follow it faithfully for every phase.
- **`references/quality_framework.md`** — *what blocks vs guides vs stays silent.* The tiered A/B/C
  rulebook (hard guardrails, thinking lenses, internal QA). Read it before finalizing any phase, and
  use it to decide which rules are fatal and which are judgment.
- **`references/consistency_contract.md`** — *what must be identical across every deck.* The
  invariant layer client adaptation is balanced against: the locked Evidence & Claim Dictionary,
  the Reconciliation & Provenance Gate, the Brand Kit design tokens, and the Canonical Slide
  Contract. Read it before drafting strategy numbers, evidence, or stat callouts — it is what keeps
  a deck internally consistent and comparable deck-to-deck for the same client.
- **`references/knowledge-base/00-INDEX.md`** — the approved source of truth for Sonar
  capabilities, pricing, competitors, tone, widgets, and deck blueprints. Pull Sonar-specific facts
  from the knowledge base rather than from memory — this is how the skill keeps its promise never
  to invent capability, price, scope, or competitor claims. At minimum, consult
  `product-capability.md` before asserting any capability, `pricing.md` before any price,
  `competitors.md` before any differentiation claim, and `tone-and-writing.md` for the writing
  voice.

For visual production, also consult `references/brand-kit/README.md` and
`references/brand-kit/01_BRAND_SYSTEM.md`. Use the Brand Kit as the source of truth for
Dataxet:Sonar deck styling, client palettes, slide layout library, logo handling, template tokens,
and image prompt conventions — `consistency_contract.md` Part 3 locks how these tokens are applied
so a color or font is never hardcoded somewhere that disagrees with the Brand Kit.

Read `system-prompt.md` first to run each phase, hold `consistency_contract.md` as the invariant
layer while drafting strategy, evidence, and design direction, and apply `quality_framework.md` as
the gate before finalizing any phase's output.

## Step-by-step workflow

1. **Read the operating rules** (see Read order above) before doing anything else.

2. **Collect the inputs.** Check what the user has provided against the
   `references/user-prompt-template.md` template (client context, stakeholders,
   business question, evidence status, commercial guardrails, attached files,
   design/output preferences). Do **not** invent missing fields to look more
   complete — mark them `Unknown / Not Provided` and flag the gaps. If a
   critical gap blocks progress (no confirmed business question, unknown
   stakeholder, core evidence missing), output a **CLARIFICATION REQUEST**
   before proceeding rather than fabricating inputs.

   If many fields are missing and the user hasn't supplied a brief, ask for the
   essentials first (company, meeting objective, sales stage, deck language,
   primary business question, available evidence) before generating.

3. **Diagnose and strategize.** Classify the client's primary problem type
   (TIME_TO_KNOW / TIME_TO_REACT / SIGNAL_VS_NOISE / PROOF_TO_DECIDE /
   BLIND_SPOT), lock the single primary business question, score 2–3 strategic
   angles, and establish the strategic foundation and buyer belief chain. This
   is the heart of STRATEGY_REVIEW and the foundation of every later phase.

4. **Build the content** (CONTENT_DRAFT and beyond). Write every slide into the
   Content Contract using the schema at
   `references/content-contract-schema.json`. Every non-reference slide must
   prove why the question matters, show the cost of inaction, evidence that
   it's real, explain why Sonar fits, or reduce risk for the next step. Before
   declaring CONTENT_DRAFT complete, run the Reconciliation & Provenance Gate
   (`references/consistency_contract.md` Part 2) — every stat and claim must
   trace to a source and stay identical everywhere it recurs — then run the QA
   gate silently before output.

5. **Produce the PPTX** (FINAL_PRODUCTION only). Never render a client-ready
   PPTX when `content_gate_status` is `BLOCKED`. To build the deck, first read
   the pptx skill at `/mnt/skills/public/pptx/SKILL.md`, then render slides
   from the Content Contract, applying the design system (palette, typography,
   archetypes, layout rhythm, real data visuals, editorial statement, density
   limits) described in `references/system-prompt.md`. Run visual QA: inspect
   each rendered slide for overflow, overlap, contrast, and label issues, fix,
   and re-render. If rendering is unavailable, set `visual_qa_status:
   NOT_EXECUTED`.

6. **Quality-check before release.** Run the QA checklist in
   `references/qa-and-change-rules.md` together with the tiered rules in
   `references/quality_framework.md` — Tier A guardrails must all pass (or
   block delivery), Tier B is judgment applied throughout strategy and story,
   and Tier C is a silent self-check run before release, never surfaced to the
   client. The deck is safe to release only when it is client-specific,
   evidence-backed, single-language, design-system compliant, reconciled
   (Tier A8), and renderable. Honour the hard blocks — any one of them sets
   `content_gate_status: BLOCKED`.

## Non-negotiable guardrails (summary)

These come straight from the system prompt; read it for the full logic.

- **Client-world first.** Open in the client's reality and stakes, never with a
  Sonar company profile.
- **One business question.** Every slide serves a single primary question.
- **Evidence before claims.** Classify each material claim as fact, inference,
  hypothesis, or recommendation. Never present a gap as a fact. A single
  incident proves an event, not a pattern.
- **Outcomes, not features.** Frame capabilities as client decisions and
  workflows enabled, never as a feature list.
- **Honest urgency.** Use an evidence-supported cost of inaction or opportunity
  window. Never manufacture a crisis.
- **Small, safe CTA.** Ask for the smallest decision that fits the client's
  readiness. Forbidden phrasing: "contact us", "reach out", "book a demo",
  "let's connect", "you must act now".
- **No invented commercials.** Never fabricate price, scope, SLA, timeline,
  capability detail, or case-study results. When scope is unconfirmed, label it
  `PROPOSED` and set `include_pricing: false`.
- **Single language lock.** All client-facing text — kicker, headline, chart
  labels, CTA, source notes — stays in `deck_language`. English only for fixed
  product proper names and internal JSON keys. No language mixing.
- **Phase-based timing.** No day/week/month timing for pilot, timeline, CTA, or
  implementation — use phases.
- **Delivery format matches problem type.** Monthly report is never the primary
  solution for a detection (TIME_TO_KNOW) or response (TIME_TO_REACT) problem.
- **References always last.** The audit trail / source-mapping section closes
  the deck.
- **Numbers stay frozen.** Any stat reused across slides (cover, evidence,
  cost-of-inaction, CTA) is identical every time it appears; the
  Reconciliation & Provenance Gate in `consistency_contract.md` Part 2 must
  pass before CONTENT_DRAFT is finalized.
- **Tokens over hardcoding.** Every rendered color and font comes from the
  Brand Kit tokens locked in `consistency_contract.md` Part 3 — never a value
  invented at render time.
- **Brand-swap test.** If the client's name, industry, and evidence were
  stripped out and the deck would still read coherently for a different
  company, it is a template — rebuild it around this client's actual
  situation.

## Quality priority framework (A / B / C)

Not every rule carries the same weight. The full definitions live in
`references/quality_framework.md`; read it before finalizing any phase. The
three tiers, in brief: **Tier A** hard guardrails (evidence integrity, no
invented commercials, single-language lock, CTA sizing, delivery-format fit,
capability honesty, the reconciliation gate, locked tokens & slide contract,
validation halt) block delivery on failure. **Tier B** thinking lenses (buyer-
belief gravity, problem-type-to-solution fit, competitor relevance, reframe
strength, stakeholder-lane judgment) guide strategy and story without gating.
**Tier C** lightweight QA (client red-team check, headline/number scan,
source-weakness check, generic-slide check, narrative-thread check) runs
silently before release and never appears in client-facing output.

## Output expectations per phase

- **STRATEGY_REVIEW** — Strategy Review JSON + concise summary; surface any
  clarification request first. No slide copy, no PPTX.
- **CONTENT_DRAFT** — Complete, valid Content Contract JSON + a concise
  executive summary (strategy, arc, unresolved gaps, CTA, QA status, any
  PASS_WITH_WARNINGS items). No PPTX unless explicitly requested.
- **FINAL_PRODUCTION** — Validated Content Contract JSON + editable PPTX +
  visual QA summary + change log, with the references section last. Present the
  PPTX file for download.

All reasoning is silent — deliver the outputs, a concise rationale, QA
findings, and known limitations only. Never expose the internal pipeline in
client-facing output.

## Reference files

- `references/system-prompt.md` — **Read this first, every time.** The complete
  System Prompt v6: purpose, persona, evidence protocol, problem typology,
  strategy, solution design, story architecture, design system, and QA.
- `references/quality_framework.md` — **Read this before finalizing any
  phase.** The tiered A/B/C rulebook: hard guardrails that block delivery,
  thinking lenses that guide strategy and story, and silent internal QA
  checks.
- `references/consistency_contract.md` — **Read this before drafting
  strategy numbers, evidence, or design direction.** The invariant layer:
  locked Evidence & Claim Dictionary, the Reconciliation & Provenance Gate,
  the Brand Kit design tokens, and the Canonical Slide Contract.
- `references/knowledge-base/00-INDEX.md` — **Read this before asserting any
  Sonar fact.** Index and consultation rules for the approved Sonar knowledge
  base (capabilities, pricing, competitors, tone, widgets, deck blueprints, and
  real example decks). Pull Sonar facts from here, not from memory.
- `references/user-prompt-template.md` — The fill-in input template to collect
  client and meeting context for each deck.
- `references/content-contract-schema.json` — The full Content Contract JSON
  schema the deck content must conform to.
- `references/qa-and-change-rules.md` — Pre-send QA checklist, hard-block list,
  and the rules for safely changing the prompt/skill itself.
- `references/brand-kit/` — Dataxet:Sonar Brand Kit reference for visual deck
  production: brand system, client palettes, slide library, image prompts,
  template code, logo assets, and example PPTX.