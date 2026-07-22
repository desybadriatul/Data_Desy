# EVO Report Structure — the component contract

> Task 2 does not lock a fixed slide list. It locks the **components** that must exist to answer an EVO
> business problem: each component's objective, required output, tier, and `storyline_role`. The renderer
> then decides whether a component becomes one slide, several, a merge, or an appendix — driven by data
> materiality, the primary reader, and the storyline. Slides are derived; components are contracted.

## 1. Component schema

```yaml
component_id:
section:               # A | B | C | D | E | F
title_role:            # what its headline must do (insight-led, never a noun phrase)
objective:
purpose:
required_outputs:      # the fields that must be present
source_views:          # which frozen Task 1 views feed it
evidence_requirement:  # what proof it needs
tier:                  # Core | Conditional | Supporting
confidence_rule:
visual_recipe_id:      # registered recipe from evo_visual_contract.md
legend_contract:       # required legend / semantic key; null only when not applicable
storyline_role:        # frames the problem | establishes evidence | diagnoses | explains cause | establishes comparison | translates gap | supports decision
```

## 2. Narrative spine → sections

```
FRAME → DIAGNOSE → EXPLAIN → JOURNEY → COMPETE → ACTIVATE → DECIDE
  A         B          C         D         (B/C)      E          F
```

The spine is a logical relationship between components, not a rigid slide order. Every report keeps the
spine; each beat expands or compresses to materiality but never silently disappears.

## 3. Component library (Core / Conditional / Supporting)

### Section A — Decision Frame & Evidence Integrity
| Component | Tier | Objective → required output | storyline_role |
|---|---|---|---|
| **A1 Decision Frame** | Core | Set the business question + decision → `business_question, decision_at_stake, desired_perception, perception_shift, scope, period, primary_reader, intended_use` | frames the problem |
| **A2 Benchmark & Segment Charter** | Core | Lock the comparison system → `benchmark_segments, focus_brand, competitor/teacher/adjacent brands, inclusion_logic, exclusions, contamination_status, benchmark_confidence` | establishes comparison |
| **A3 Case-Adaptive EVO Frame** | Core | Define E/V/O for *this* category + desired perception → `experience_def, values_def, offer_def, category_attributes, relationship_to_desired_perception` | frames the problem |
| **A4 Data, Sampling & Confidence** | Core | Show evidence quality + limits → `total_population, tagged_population, sampling_method, coverage, metric_basis, sample_size, confidence per brand/driver/attribute, limitations` | establishes evidence |

### Section B — Perception Diagnosis
| Component | Tier | Objective → required output | storyline_role |
|---|---|---|---|
| **B1 Traction & Issue Universe** | Core | Turn top content into issues → `Story → Issue → Attribute → Driver → Polarity → Magnitude → Implication` | establishes evidence |
| **B2 Attribute Architecture** | Core | Full attribute universe per E/V/O → shared / unique / weak / absent / contaminated / no-evidence status for **every registered attribute** | diagnoses perception |
| **B3 Driver Landscape** | Core | Distribution across E/V/O → share, polarity balance, amplification, focus vs. competitor shape, dependency diagnosis | diagnoses perception |
| **B4 Key Distribution & Reputation Drivers** | Core | Concrete pos/neg issues per driver → `driver, polarity, attribute, issue, magnitude, share_of_pool, evidence, business_meaning` | explains cause |
| **B5 Focus-Brand Scorecard** | Core | Comparable diagnosis → Sentiment Index, Engagement/Virality Index, Total Driver Score, EVOScore, `band_code + band_label` per index, sample, confidence, diagnostic posture, and the three score-band labels + thresholds needed to interpret the result | diagnoses perception |
| **B6 Competitive Posture & Positioning** | Core | Brand × E/V/O posture → defensible / fragile / exposed strengths, contested territories, low-confidence cells | establishes comparison |
| **B7 Attribute Gap, Best Brand & Whitespace** | Core | Scoreboard → learning → focus score, Best Brand (non-focus), gap, confidence, whitespace, winning pattern, transferable lesson, pattern-not-to-copy, right-to-play | translates gap |

### Section C — Explanation & Evidence
| Component | Tier | Objective → required output | storyline_role |
|---|---|---|---|
| **C1 Barriers, Triggers & Contradictions** | Conditional* | What blocks/accelerates change → barriers, triggers, contradictions, proof gaps, operational gaps, conditions_for_change | explains cause |
| **C2 Content & Cultural Mechanics** | Core (priority attrs) | Why the attribute is socially real → benefit/tension, cultural behaviour, topic, tone, format, mechanic, source role, channel function, response, reason for traction, perception consequence | explains cause |
| **C3 Attribute Capture & Evidence** | Core | Prove strategic conclusions → `real content → response → issue → attribute → consequence → business implication` for reframe-carrying / biggest-gap / must-protect / recurring-liability attributes | establishes evidence |

\* C1 becomes mandatory when a material contradiction or perception leak exists.

### Section D — Perception Journey
| Component | Tier | Objective → required output | storyline_role |
|---|---|---|---|
| **D1 Awareness–Engagement–Impact Framework** | Core | Define how the report reads movement → stage definitions, classification rules, evidence per stage | frames the problem |
| **D2 Comparative Journey Matrix** | Core (when benchmark data supports) | Brands × stages → which brands convert visibility into organic perception | establishes comparison |
| **D3 Focus-Brand Intervention Map** | Core | E/V/O × stages → stage weakness or journey leak (`evo_journey_model.md` §4.1 transition / §4.2 single-stage), source-role gap, required intervention, owner, required proof, expected movement | translates gap |
| **D4 Source-Role Mechanics** | Core | Who forms perception and their function → role contribution, journey function | explains cause |

### Section E — Strategic Translation & Activation
| Component | Tier | Objective → required output | storyline_role |
|---|---|---|---|
| **E1 Strategic Reframe** | Core | One new way to understand the problem → surface problem, actual perception problem, evidence chain, competitive implication, desired shift | supports decision |
| **E2 Attribute Priority Portfolio** | Core | Classify action per attribute → attribute, move type (Scale/Fix/Protect/Build/Test/Monitor/Avoid), reason, evidence, priority, owner, dependency | supports decision |
| **E3 Messaging Architecture** | Core | Attribute priority → communication direction → desired meaning, attribute, driver, current barrier, message territory, proof requirement, tone, source role, mechanic, avoid-list | translates gap |
| **E4 Channel & Source-Role Opportunity** | Conditional | Channel/actor function → channel, source role, priority attribute, stage, function, required proof, expected outcome | translates gap |
| **E5 External Success Stories & Strategic Analogies** | Conditional (recommendation mode) | Borrowed patterns, inspiration not proof → 2–4 cards with `case_brand, industry, strategy_pattern, analogous_issue, priority_attribute, EVO driver, journey_route, channel/source role, proof_mechanism, what_to_adapt, what_not_to_copy, client_right_to_play, linked_move_type, citation, evidence_status=External Analogy, applicability_confidence`; may be skipped only with a recorded source/fit reason | supports decision |
| **E6 Activation Roadmap** | Core | Diagnosis → executable sequence → first problem, move type, intervention, owner, asset/proof, source-role route, expected movement, KPI, dependency, sequence | supports decision |
| **E7 Gap-to-Opportunity Guidance** | Conditional (per priority attr) | Design brief → `benefit/tension → public issue → brand gap → opportunity → activation principle` | translates gap |

### Section F — Decision & Measurement
| Component | Tier | Objective → required output | storyline_role |
|---|---|---|---|
| **F1 Recommended Decision** | Core | Answer the business question → recommended direction, priority attributes, over-relied driver, build/repair/protect, deliberate deprioritisation, smallest next move | supports decision |
| **F2 Perception Measurement Contract** | Core | Prove perception is moving → Attribute Share, Attribute Net Sentiment, Attribute Score, Organic Evidence Share, earned validation, source-role diversity, advocacy, recurring criticism (+ survey KPIs if available) | supports decision |
| **F3 Business Impact Bridge** | Conditional | Link perception to commercial objective → `EVO intervention → perception outcome → behavioural signal → business outcome → validation data`; status `Measured / Target / Hypothesis / Not Available` | supports decision |
| **F4 Decision Closure** | Core | Operational closure → **Stop / Start / Measure / Owner** | supports decision |

E5 belongs after Messaging / Channel Translation and before the Activation Roadmap. Its default title role is
**“Borrowed patterns — inspiration, not proof.”** External cases cannot satisfy C3 evidence requirements and
cannot replace B7 benchmark learning.

## 4. Headline discipline (title_role)

Every component's headline is **insight-led**, never a noun-phrase topic. Not "Driver Landscape" but
"Telkomsel's perception rests on Offer — the two drivers that build affinity are barely defended." No metric-only slides. Layout may vary according to the client template, audience, and density.

## 5. Structural presentation contract

The **component structure** is mandatory; the **visual layout** is adaptive. A component may use one slide or
several slides, and may be rendered as a table, cards, scale, chart, matrix, or hybrid, provided that every
required output remains visible and the storyline role is preserved.

For **B5 Focus-Brand Scorecard**, the delivered slide or connected slide sequence must communicate:

- Experience / Values / Offer results for Share, Net Sentiment, Sentiment Index, Virality Index, and
  Total Driver Score;
- the EVOScore value and its active `band_code / band_label`;
- the three canonical interpretation bands and thresholds:
  `Underperform <90`, `On Par 90–110`, `Outperform >110`;
- sample and confidence at the grain required by the analysis;
- the diagnostic posture or component tension that explains the composite.

The structure does **not** require a specific hero card, table design, legend placement, orientation, colour,
or active-band marker. `references/evo_visual_contract.md` provides adaptable guidance only. A B5 output is
incomplete when the reader cannot determine the applicable score band or when a required structural field is
missing—not because it uses a different layout.

## 6. Component-completeness gate (before rendering)

Every **Core** component is marked `produced` or `skipped — reason`. A Core component may be skipped only if
the case data genuinely cannot support it (state why) — never because computing it from row-level content
was more effort than pulling an aggregate. Record the result as `component_completeness_audit` in the frozen
output. Two specific rules this enforces:

- **Full-set coverage.** B2 and B7 must account for *every* registered `attribute_id` — an attribute with
  zero tagged evidence still appears, marked `no evidence / whitespace`, never silently dropped.
- **No-substitution.** B3 (Driver Landscape) is necessary but never sufficient; it must not stand in for B2
  (Attribute Architecture) or B4 (Key Distribution). All three are separate Core components.
- **Renumbering on skip.** When a Conditional component is skipped (e.g. E4 Channel & Source-Role Opportunity
  has no material finding), every subsequent component in that section closes the gap in the *visible*
  sequence and page footer — what would have been "E5, E6" becomes "E4, E5" on the rendered slide and its
  footer number, with no jump and no explanation needed on the slide itself. The original `component_id`
  (`E5`, `E6`, …) is preserved only inside the internal `component_completeness_audit` record, so the
  component's contract identity is never lost for QA or re-audit purposes — but the client never sees a
  numbering hole. A deck that jumps from a visible "24. …" to a visible "25. …" with a skipped component in
  between, or where footer page numbers stop matching the visible component count, fails G13 (see
  `evo_quality_gate.md`).

## 7. Slide target

Because the attribute layer alone is four separate Core components (B2, B4, B5, B7) that don't compress into
one slide each, the default main-deck target is **25–30 slides**, with any out-of-range reason logged in
`quality_report.json`. Supporting/appendix material (full maps, full tables, evidence library, methodology,
QA) sits outside that count.
