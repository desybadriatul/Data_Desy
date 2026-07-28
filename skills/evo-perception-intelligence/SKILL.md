---
name: evo-perception-intelligence
report_type_id: evo_perception_intelligence
display_name: "EVO Perception Intelligence Report"
version: "1.3"
status: ACTIVE
owner: Dataxet Sonar
description: >-
  Consultant-grade engine for the EVO Perception Intelligence Report — a standalone Jalur 1 report type
  that reads a brand through Experience / Values / Offer, diagnoses which attributes own perception,
  compares the focus brand against a benchmark set (Best Brand, Attribute Gap, Whitespace), traces
  perception through Awareness → Engagement → Perception Impact, and closes on a client-owned
  perception-building decision (Scale / Fix / Protect / Build / Test / Monitor / Avoid). Use whenever the
  business question is about perception, association, attribute ownership, positioning, or
  perception-building activity — triggers include "EVO", "EVO report", "EVO perception", "persepsi EVO",
  "perception intelligence", "brand perception report", "competitive perception", "Experience Values Offer".
---

# EVO Perception Intelligence Report — Skill Pack

EVO is **not** a generic lens on top of the universal engine. It has its own taxonomy, its own row-level
classification, its own attribute-level metrics, its own journey model, its own recommendation vocabulary,
and its own quality gates. That is why it is a dedicated skill pack owned by one `report_type_id`, not a
selectable option inside another report.

The one job of this pack: turn listening data into **what a brand means, why it means that, where it loses
to the benchmark, and the smallest move that shifts meaning** — evidence-traceable end to end. If the output
reads as "top content + attribute labels," the pack has failed. The reference EVO deck (Telkomsel) literally
labels its own opening as *"informative, but lacks insights"*; this pack exists to close that exact gap.

## What "world-class" means here, concretely

A dashboard says *"Responsiveness is negative."* A consultant says *"Slow-connection complaints, spam
messages, and unanswered support tickets are the three issues dragging Experience down — the same three the
Best Brand solved by turning support into public, on-record replies; closing that gap is the smallest move
that makes Telkomsel feel Indonesian-and-modern rather than big-and-slow."* Every EVO finding must reach the
second form: **issue-level, comparative, causal, and tied to a decision.** Eleven reference files below encode
how to get there.

## Read order (layered — read before producing any EVO output)

1. **`references/evo_framework.md`** — *how to think in EVO.* Experience/Values/Offer as a business lens
   (not a methodology definition), the reframe engine, the seven-beat narrative spine
   (FRAME → DIAGNOSE → EXPLAIN → JOURNEY → COMPETE → ACTIVATE → DECIDE), and the anti-template test.
2. **`references/evo_attribute_map.md`** — *the perception vocabulary.* The seed attribute taxonomy, the
   attribute-map priority ladder (client-approved → category → seed), and how attributes differ from topics.
3. **`references/evo_classification_contract.md`** — *how content becomes signal.* The row-level
   Content → Material Issue → Base Attribute → E/V/O pipeline, the classification prompt, stratified
   sampling, confidence, rationale, and audit.
4. **`references/evo_metric_dictionary.md`** — *the locked math.* Numeric formulas for EVO Share, Driver
   Score, EVOScore, Attribute Score, Attribute Gap, Best Brand, Whitespace, and the journey metrics. Extends
   (never contradicts) the universal `consistency_contract.md` Metric Dictionary.
5. **`references/evo_journey_model.md`** — *how perception moves.* Awareness → Engagement → Perception Impact
   classification rules, source-role taxonomy, transition-leak diagnosis, single-stage problem diagnosis
   (where the problem sits *inside* a stage, not just in the handoff between two), and intervention mapping.
6. **`references/evo_evidence_standard.md`** — *proof discipline.* The evidence card schema, the
   Real content → Response → Issue → Attribute → Consequence → Business implication chain, no-fabrication rules.
7. **`references/evo_report_structure.md`** — *the component contract.* Structures A–F, each component's
   objective / required output / tier / storyline_role, and the component-completeness rule. Slides are
   derived from components, not fixed.
8. **`references/evo_visual_contract.md`** — *adaptive visual guidance.* Template-safe options for translating
   the locked component structure into readable slides. It does not prescribe one layout, one recipe, or one
   visual arrangement across clients.
9. **`references/evo_recommendation_vocabulary.md`** — *the solution engine.* Scale / Fix / Protect / Build /
   Test / Monitor / Avoid decision logic, messaging architecture, activation roadmap, and the
   perception→behaviour→business bridge with validation status.
10. **`references/evo_external_strategic_analogies.md`** — *borrowed patterns, inspiration not proof.* How to
   select 2–4 external success stories, map them to an EVO attribute + journey leak, state what to adapt and
   what not to copy, cite the source, and freeze them as `External Analogy` rather than focus-brand evidence.
11. **`references/evo_quality_gate.md`** — *what blocks vs. guides.* Fourteen EVO-specific gates (attribute
   integrity, component completeness, competitive integrity, driver non-substitution, confidence integrity,
   journey integrity, evidence integrity, business-impact boundary, decision integrity, report-type fit, role
   integrity, external-analogy integrity, structural presentation integrity, client-facing language integrity)
   layered on the universal A/B/C framework.

Also load, from the shared engine, the universal `consistency_contract.md` (locked theme + reconciliation
gate C.5), `quality_framework.md`, and **`skill_report.md`** — specifically its §8 client-facing language
rules, which EVO's G14 gate inherits unchanged rather than re-defining. EVO extends all three; it never forks
the theme, the reconciliation math, or the jargon-avoidance list.

## Tool sequence (Jalur 1 — bottom-up, pakem)

```
create_evo_perception_intelligence_report_workflow      # lock audience, focus + benchmark brands, scope, attribute map; run Task 1
        ↓
build_evo_perception_intelligence_report_data_preview   # Task 1 preview: scope, data health, E/V/O, attributes, gap, evidence, journey, external analogies, completeness
        ↓
preview_confirmed  (user)
        ↓
build_evo_perception_intelligence_report_ppt_package    # Task 2: select material components, size slides, render PPTX + audit pack
```

Task 1 freezes data, semantics, evidence, validated external-analogy sources, and component completeness;
**Task 2 never recomputes
a metric and never invents evidence or a case.** Audience is mandatory (return `NEEDS_AUDIENCE` and ask if absent). Preview must be confirmed before PPTX. Focus brand
is excluded from the Best-Brand pool. Do not mix this with Jalur 2's 8-point intent confirmation, and do not
assemble slides by hand.

## Non-negotiables (EVO)

- **Focus brand + at least one valid benchmark are required.** EVO's value is comparative; without a benchmark
  there is no Best Brand, no Attribute Gap, no transferable lesson. If only the focus brand exists, say so and
  fall back to a single-brand perception diagnosis with `competitive_analysis: unavailable`.
- **Attribute-level metrics are computed from row-level tagged content only** (Attribute Score, Contribution,
  Best Brand, Gap, Whitespace). They must never be derived from driver aggregates. Driver-only data → produce
  driver analysis, mark attribute analysis `unavailable`, never estimate.
- **Never let a missing EVO tag stop the workflow.** If tags are absent/partial, run automatic classification
  on a stratified 10% sample (≤100 content/request), store confidence + rationale, and mark output
  `tagged sample` / `directional`. `NEEDS_EVO_CLASSIFICATION` is not a default terminal state.
- **Awareness and Engagement are not Perception Impact.** Visibility and reaction do not equal a shift in
  public meaning; only organic association / validation / advocacy / recurring framing counts as Impact.
- **Business Impact is conditional.** Sales, conversion, retention, and ROI are never concluded from listening
  data alone. Without external data, output only the perception→behaviour→business→validation bridge, tagged
  `Hypothesis` or `Target`.
- **Every recommendation is a client-owned move** with a move type, priority attribute, owner, intervention,
  proof, metric, and smallest next step. The monitoring tool appears at most once, as an enabler. The deck
  closes on a decision, never a buy/demo CTA.
- **External success stories are analogies, never proof.** In recommendation mode, use 2–4 credible borrowed
  patterns only after the internal diagnosis is established. Label each `External Analogy`, cite its source,
  name `what_to_adapt` and `what_not_to_copy`, and never let it replace focus-brand evidence, Best Brand, or
  the benchmark lesson.
- **Structure locks; visual treatment adapts.** `evo_report_structure.md` locks the required components,
  fields, labels, confidence, evidence status, and storyline role. The client template and renderer may choose
  any effective visual composition. For B5, the three score bands and thresholds must be understandable, but
  their placement and visual form are not prescribed.
- **Swap-the-brand test.** If the reframe and recommendations still hold after replacing the focus brand with a
  random competitor, it is a template — rebuild. EVO output must break when the brand name changes.
