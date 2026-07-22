# EVO Recommendation Vocabulary — the solution engine

> The whole report exists to produce this: a client-owned decision that closes the business problem.
> Diagnosis earns the right to recommend; it is not the product. This file defines the move types, the
> completeness bar for a recommendation, the messaging architecture, the activation roadmap, and the honest
> perception → business bridge.

## 1. The seven moves (map every priority attribute to exactly one)

| Move | When to use | Reads as |
|---|---|---|
| **Scale** | A credible, controllable strength that is under-amplified | "You already own this — put weight behind it." |
| **Fix** | A recurring negative issue or a broken proof point | "This is actively costing you; repair the cause." |
| **Protect** | A valuable asset that is exposed or fragile (thin proof, contested) | "You lead here but it's undefended — shore it up." |
| **Build** | An attribute the brand has a *right* to own but doesn't yet | "Open territory that fits you — construct it deliberately." |
| **Test** | Promising whitespace with limited evidence | "Might be yours; run a bounded experiment before betting." |
| **Monitor** | A weak or low-control signal worth watching, not acting on | "Keep an eye on it; don't over-invest yet." |
| **Avoid** | A pattern that works for a competitor but the brand has no right to copy | "Their win, not yours — don't chase it." |

**Deriving the move from the diagnosis (worked logic):**
- Real Strength + missing-Awareness leak → **Scale**.
- Real Strength + Engagement→Impact leak → **Protect** (+ build proof).
- Active Vulnerability (recurring negative) → **Fix**.
- Whitespace with category demand + brand right-to-play → **Build**.
- Whitespace, thin evidence → **Test**.
- Competitor winning pattern the brand can't credibly own → **Avoid**.

**Posture → move cross-reference (all six `evo_metric_dictionary.md` §4 postures, no gaps).**
The six-line worked logic above illustrates the reasoning; this table is the complete, authoritative
derivation. Every attribute's posture must resolve to exactly one default move before it can enter the
Attribute Priority Portfolio (E2) — an attribute with a posture but no move-derivation row is an incomplete
recommendation, not a stylistic choice.

| Posture (`evo_metric_dictionary.md` §4) | Default move | Escalation / de-escalation condition | Reads as |
|---|---|---|---|
| **Real Strength** | **Scale** | If journey shows an Engagement→Impact leak (visible/liked but not converting to organic public meaning) → **Protect** instead, and name the proof gap | "You already own this — put weight behind it." |
| **Fragile Strength** | **Protect** | If a specific recurring negative issue is identifiable inside the weak tone → reclassify that issue as **Fix**; the remaining composite stays **Protect** | "You look strong on volume, but the tone underneath is soft — shore up the proof before amplifying further." |
| **Under-Built Territory** | **Build** | If `n < 10` (thin evidence even by directional standards) → downgrade to **Test** | "You already own this quietly — give it deliberate weight before a competitor claims it." |
| **Active Vulnerability** | **Fix** | None — a recurring negative with material volume is never Monitored or Avoided | "This is actively costing you; repair the cause." |
| **Low-Confidence Signal** | **Monitor** | If a specific, named opportunity hypothesis exists (not just noise) → upgrade to **Test** | "Keep an eye on it; don't over-invest on a sample this thin." |
| **Whitespace** | **Build** (category demand + brand right-to-play) | Thin evidence → **Test**; winning pattern belongs to a competitor with no brand right-to-play → **Avoid** | "Might be yours; run a bounded experiment before betting," or "Their win, not yours — don't chase it." |

No posture may be left without a resolved move in delivered output. If a case genuinely doesn't fit any row
(a new posture pattern not yet in the metric dictionary), treat it as a metric-dictionary gap — file it there,
do not invent a move ad hoc in the deck.

**A second, independent route to a move: the journey diagnosis.** The posture table above answers "is this
attribute a strength or a gap." `evo_journey_model.md` §4 answers a different question — "where in
Awareness→Engagement→Impact does the problem actually sit, and is it a transition leak or a single-stage
problem" — and resolves to its own move recommendation from that stage-level diagnosis. The two routes are
read together, not merged into one rule: a posture can say "Real Strength" while the journey diagnosis says
"Impact is authored elsewhere" (§4.2c), and in that case the journey diagnosis wins because it identifies
*why* the strength is exposed, which the posture alone cannot see. Do not pick whichever route gives the more
convenient answer; if the two disagree, the journey diagnosis is the more specific instrument and the
component that carries it (`D3 Focus-Brand Intervention Map`) is where that reconciliation is shown.

## 2. A complete recommendation (the bar)

A recommendation is finished only when it names all of:

```
desired outcome + evidence trigger + owner + attribute/driver + journey intervention
              + mechanism/proof + success metric + smallest next move
```

Recommendations should be **few, sequenced, and decision-relevant** — state what happens first, what
follows, and what is deliberately deferred. A flat verb list ("improve Experience, boost Values") is not a
recommendation; it's a wish.

**Worked example (dashboard → consultant):**
> *Dashboard:* "Improve Experience."
> *EVO:* "**Fix** Reliability (Experience). Slow-connection and outage complaints are the largest negative
> Experience pool (32% of negative Experience, n=46, directional). The Best Brand neutralised the same issue
> by publishing region-level restoration status as on-record Expert/Authority posts, converting Awareness
> complaints into resolved-in-public Impact. Owner: Network Comms. Proof: public restoration tracker.
> Metric: Reliability Attribute Net Sentiment + Organic Evidence Share. Smallest next move: pilot public
> status replies in the three worst-affected regions this month."

Swap "Telkomsel" for any competitor and that recommendation is false — which is the point.

## 3. Messaging architecture (attribute priority → communication direction)

This is not final advertising copy. For each priority attribute produce:

```
desired consumer meaning · attribute · EVO driver · current barrier ·
message territory · proof requirement · voice & tone · source role · content mechanic · avoid-list
```

The **avoid-list** matters as much as the territory: it names what the brand must *stop* saying because it
contradicts the evidence (e.g. stop claiming "fastest network" while Reliability net sentiment is negative —
the claim amplifies the very gap it's trying to hide).

## 4. External strategic analogies — design input, not proof

After the priority attribute, journey leak, and required proof are fixed, use 2–4 external success stories
to make the activation mechanism concrete:

```
internal evidence → priority move → borrowed mechanism → adapt → don't copy → client-owned next step
```

Every case is labelled `External Analogy`, cited, and mapped to the exact EVO driver, attribute, journey
route, source role / channel, and proof mechanism it informs. It never replaces the internal evidence trigger
or guarantees the outcome. A famous case with no mechanism fit is excluded. See
`evo_external_strategic_analogies.md`.

## 5. Activation roadmap (sequenced, executable — not a calendar)

The roadmap's mandatory shape is a dependency chain, not dates:

```
problem → intervention → proof → perception movement → measurement
```

For each step: first problem to solve, move type, intervention, owner, required asset/proof, source-role
route, expected perception movement, KPI, dependency, sequence. Sequence by dependency — you cannot Scale an
attribute whose proof you haven't Built; you cannot Build trust while an active Fix is bleeding it.

## 6. Perception → behaviour → business bridge (honest by construction)

Listening data proves perception. It does **not** prove sales, conversion, switching, or retention. So the
bridge is explicit about where certainty ends:

```
EVO intervention → perception outcome → behavioural signal → business outcome → validation data
     (planned)        (measurable via      (hypothesised)       (hypothesised)     (what would confirm it)
                        listening)
```

Every business-outcome link carries a validation status: **Measured** (external data in hand) · **Target**
(agreed goal) · **Hypothesis** (plausible, unproven) · **Not Available**. Business Impact may be stated as
`MEASURED` only when survey/brand-lift, web analytics, search, CRM, conversion, sales, retention, or
operational data is actually present. Absent that, the bridge stops at `Hypothesis` — and says so.

## 7. Decision closure

Every EVO analysis ends on a resolved decision, expressed as:

```
Stop  — what the brand should stop doing (from the avoid-list / active vulnerabilities)
Start — the first new move (the smallest next step, not a program)
Measure — the perception KPI that proves movement (Attribute-level, from F2)
Owner — the client-side team accountable
```

The deck closes here — on a client decision and a smallest next move — never on a buy / demo / pilot CTA for
the monitoring tool. The tool appears at most once in the whole report, as an enabler of measurement.
