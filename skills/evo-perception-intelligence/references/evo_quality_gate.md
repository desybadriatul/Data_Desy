# EVO Quality Gate — what blocks, what guides, what stays silent

> EVO inherits the universal A/B/C quality framework and Stage C.5 reconciliation gate unchanged, then adds
> a perception-integrity gate (G) that catches the failure modes unique to attribute-level perception work.
> Gates in Tier A / Section G **block delivery**; the rest guide reasoning. Run silently — never add a "QA"
> section to the client-facing deck.

## Section G — EVO Perception Integrity (blocks delivery)

### G1. Attribute integrity
**Test:** every priority driver claim traces to a registered `attribute_id` + issue, with `n` and sentiment;
Attribute Score / Best Brand / Gap / Whitespace are computed from row-level tagged content.
**FAIL when:** driver aggregates are presented as attribute-level findings, or attribute prose carries no
`attribute_id` / `n` / sentiment. *(This is the single most common EVO failure — the anti-shortcut clause.)*

### G2. Component completeness integrity
**Test:** every Core component in `evo_report_structure.md` is marked `produced` or `skipped — reason` in
`component_completeness_audit`.
**FAIL when:** a Core component is silently missing, or was downgraded to an aggregate shortcut with no audit
entry.

### G3. Competitive integrity
**Test:** one benchmark set, stable across every comparative view, contamination-checked; focus brand
excluded from the Best-Brand pool.
**FAIL when:** the brand set changes between comparative slides without disclosure, or the focus brand
appears as a Best Brand.

### G4. Driver non-substitution
**Test:** Driver Landscape (B3) does not stand in for Attribute Architecture (B2) or Key Distribution (B4);
all three are present.
**FAIL when:** driver share/net is the *only* diagnostic layer and the attribute/issue layer is absent while
row-level data existed to build it.

### G5. Confidence integrity
**Test:** `n < 30` → directional wording + visible `n`; `n < 10` → low-confidence warning; disclosure exists
at the **attribute × brand** grain, not only driver grain.
**FAIL when:** a thin sample is presented as certain, or a driver-level caveat is used to cover an
attribute-level claim.

### G6. Journey integrity
**Test:** Awareness/Engagement counts are not presented as Perception Impact; stages assigned by observable
function, not channel rule; every material journey diagnosis in D3 (a transition leak per §4.1 or a
single-stage problem per §4.2 of `evo_journey_model.md`) resolves to exactly one move type, the same
completeness bar `evo_recommendation_vocabulary.md` applies to posture.
**FAIL when:** visibility or reaction is claimed as a shift in public meaning, or D3 names a stage weakness /
journey leak with no corresponding move in the required intervention field.

### G7. Evidence integrity
**Test:** no fabricated quote / source / activity; paraphrase labelled; no excerpt reused across different
attributes without stated reason; a card exists for every priority attribute.
**FAIL when:** any of the above is violated.

### G8. Business-impact boundary
**Test:** sales / conversion / retention / ROI are not concluded from listening data alone; the bridge
carries a validation status.
**FAIL when:** a commercial outcome is asserted as caused by perception with no external data.

### G9. Decision integrity
**Test:** every recommendation names desired outcome, priority attribute, owner, intervention, proof,
metric, and smallest next move; the deck closes on a client decision (Stop/Start/Measure/Owner).
**FAIL when:** recommendations are a flat verb list, or the deck ends on a description or a tool CTA.

### G10. Report-type fit
**Test:** the question is genuinely about perception / positioning / attribute ownership / perception-building.
**FAIL when:** EVO is forced onto a live-crisis, pure-campaign-performance, or sales-proof question that
another report type (SFIR, BCE, Competitive Analysis) fits better — say so and redirect.

### G11. Role integrity
**Test:** the primary reader is named (or inferred + stated); sequencing matches their decision.
**FAIL when:** default template sequencing is used with no reader stated or inferred.

### G12. External-analogy integrity
**Test:** every external story is labelled `External Analogy`, source-cited, mapped to a diagnosed EVO
attribute + journey route, and contains both `what_to_adapt` and `what_not_to_copy`; internal evidence remains
sufficient without the analogy.
**FAIL when:** an external case is presented as proof the recommendation will work, substitutes for focus-brand
evidence / benchmark learning, has no credible citation, or is a famous-but-generic example with no mechanism
fit or client right-to-play.

### G13. Structural presentation integrity
**Test:** every rendered component preserves the required outputs, labels, confidence, evidence status, and
storyline role defined in `evo_report_structure.md`; score-band thresholds match
`evo_metric_dictionary.md`. Visual layout is free to adapt to the client template and audience.
**FAIL when:** a structurally required field is missing, B5 does not let the reader identify the active score
band and the three canonical thresholds, a renderer invents thresholds / labels, directional evidence is
shown as definitive, or External Analogies are presented as internal proof. This also fails when a skipped
Conditional component leaves an unrenumbered gap in the visible component sequence or page footer (see
`evo_report_structure.md` §6, renumbering-on-skip rule). A different layout or legend placement is not a
failure. Readability defects such as overflow, overlap, or illegible text are handled by normal render QA,
not by a fixed EVO visual recipe.

### G14. Client-facing language integrity
**Test:** no internal methodology name, QA test name, gate reference, or schema/field name appears verbatim
on a client-facing slide. This includes — but is not limited to — EVO-specific procedural language
(`swap-the-brand test`, `vendor-swap test`, `component_completeness_audit`, `attribute_id`, `confidence_rule`,
`evidence_status`, `Tier A/B/C`, any `G1`–`G13` gate label) and the shared jargon-avoidance list already
defined in the canonical engine's `skill_report.md` §8.1 (e.g. "reframe", "tension", "signal vs noise",
"framework", "stage A/B/C") — EVO inherits that list unchanged and does not relax it. Every internal term that
needs to reach the client is first translated through the actor + event + consequence pattern in
`skill_report.md` §8.2, not carried over as-is.
**FAIL when:** any internal test name, gate reference, schema field, or shared/EVO jargon term appears on a
client-facing slide — including inside a reframe headline (this exact failure mode occurred in a delivered
EVO deck: an internal QA instruction was left inside the client-facing reframe slide), a recommendation line,
or a footnote. Internal artifacts (`quality_report.json`, `component_completeness_audit`) may use this
language freely; the client-facing deck may not.

## Inherited universal gates (unchanged)

**Tier A — hard guardrails (block):** metric consistency (freeze once, never re-derive); no invented
timeline unless from the brief; source quality for sensitive/competitor claims (cited URL on References);
no overclaim on weak data; data integrity (internal metrics + quotes from rawdata only); client-owned
recommendations (OWNER + VENDOR-SWAP tests); validation halt; Stage C.5 reconciliation pass.

**Metric consistency — operational freeze-sheet protocol (EVO-specific application).** The first time any
number is computed (brand volume, EVO Share, Attribute Score, funnel count), it is written once to
`evo_metric_manifest.json` keyed by `{metric_id, brand, scope, basis}`. Every later appearance of that
number — headline, table, chart, appendix, or a different slide restating the same fact — reads from that
manifest entry; it is never recalculated inline from raw content a second time. If two slides show the same
`metric_id` for the same brand and scope, they must resolve to the same manifest value. A mismatch (e.g. one
brand's volume shown as 221 on one slide and 222 on another) is a Tier A fail regardless of which number is
"more correct" — the fix happens in the manifest and propagates outward; a slide is never patched in
isolation. This operationalises consistency_contract.md principle #1 ("one number, one meaning") for EVO's
attribute- and brand-level metrics specifically.

**Tier B — thinking lenses (guide):** business-decision gravity; diagnostic lens fit; competitor relevance
by role; exactly one evidence-backed reframe.

**Tier C — silent QA (internal only):** client red-team sanity check; headline-metric scan; source-weakness
check; generic-recommendation check. Fix what fails; never surface in the deck.

## The single test that catches the most
Swap the focus brand for a random competitor. If the reframe, the gaps, and the recommendations still hold,
it is a template — **rebuild.** EVO output must break when the brand name changes. This is the difference
between "informative" and the world-class bar the reference deck admitted it missed.
