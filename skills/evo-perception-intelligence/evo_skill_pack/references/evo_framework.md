# EVO Framework — How to think in Experience / Values / Offer

> This is the reasoning layer. It sets the four EVO dials, defines the three drivers as a *business* lens,
> and installs the reframe engine that separates a consultant report from a dashboard export.

## 1. The three drivers, as a business lens (not a glossary)

All brand perception is carried by three drivers. In a report they must be **defined for the specific
category and desired perception**, never pasted as generic definitions.

| Driver | The question it answers | Generic definition | What it must become in a real report |
|---|---|---|---|
| **Experience** | *What is it like to engage with the brand's people, products, and services?* | Interactions that shape perception | The concrete moments this category is judged on — e.g. for telco: network reliability, app usability, support responsiveness, store experience |
| **Values** | *What does the brand believe, and does the audience believe it?* | Beliefs and sensibilities driving the relationship | The stances this audience rewards or punishes — e.g. local pride, sustainability, inclusion, accountability |
| **Offer** | *What do you get versus what you pay?* | Value proposition: features, benefits, cost | The deal as the market actually frames it — e.g. affordability, package design, incentives, access |

**Rule:** A3 (Case-Adaptive EVO Frame) is Core. If the three drivers in a deck could be lifted into any
other category unchanged, the frame has not been done. Define them against *this* category and *this* desired
perception before any scoring.

## 2. The unit hierarchy — never collapse it

```
Content (a post/article)
   → Material Issue (the thing being said: "slow connection", "giveaway with a K-pop artist")
      → Base Attribute (the perception it forms: Responsiveness, Collaboration, Affordability)
         → Driver (Experience | Values | Offer)
```

Two failure modes to police:
- **Topic-as-attribute.** "Giveaway" is a topic; the *attribute* it forms is Affordability or Incentive.
  Topics answer *what is being discussed*; attributes answer *what perception it builds*. Keep them distinct.
- **Driver-substitution.** Reporting only "Experience is 42%, negative" hides the issues. Driver aggregates
  are a *summary of* attribute-level truth, never a replacement for it. Attribute metrics are always computed
  from row level (see metric dictionary), never back-derived from the driver number.

## 3. The four EVO dials (set these before Stage A)

The universal engine has four adaptation dials. EVO fixes two and varies two:

- **Expert approach (fixed): perception strategist / brand semiotician.** The voice reads meaning, not
  volume. It asks "what does this make the brand *mean*," not "how much was posted."
- **Analytical lens (fixed): the EVO attribute-ownership lens.** The organizing frame is always
  *which attributes the brand owns, shares, contests, or has ceded, across E/V/O, versus the benchmark.*
- **Pain-point type (varies).** Diagnose which of the five the client actually has, because it sets the
  storyline weight:
  - *Blind-Spot* ("we don't know how we're perceived") → weight DIAGNOSE + EXPLAIN.
  - *Proof-to-Decide* ("we suspect a positioning gap, need evidence") → weight COMPETE + EVIDENCE.
  - *Signal-vs-Noise* ("lots of buzz, unclear what matters") → weight Traction/Issue Universe + Attribute Architecture.
  - *Time-to-React* (perception is slipping) → weight Barriers/Contradictions + Intervention Map.
  - *Time-to-Know* (periodic perception read) → balanced arc, heavier Scorecard + Journey.
- **Arc emphasis (varies).** Which beats expand vs. compress, driven by data materiality and the primary
  reader (a CMO wants COMPETE + DECIDE; a content lead wants EXPLAIN + ACTIVATE).

## 4. The narrative spine (logical, not a fixed slide order)

```
FRAME → DIAGNOSE → EXPLAIN → JOURNEY → COMPETE → ACTIVATE → DECIDE
```

- **FRAME** — business question, decision at stake, desired perception, benchmark charter, EVO frame, data
  confidence. Prevents EVO from drifting into aimless conversation exploration.
- **DIAGNOSE** — issue universe, attribute architecture, driver landscape, key distribution, scorecard.
  *What perception exists and what forms it.*
- **EXPLAIN** — barriers/triggers/contradictions, content & cultural mechanics, attribute capture + evidence.
  *Why it exists and why it's believed.* This beat is what makes attributes transferable learning.
- **JOURNEY** — Awareness/Engagement/Perception-Impact framework, comparative journey matrix, intervention
  map, source-role mechanics. *How perception moves and where it leaks.*
- **COMPETE** — competitive posture, Attribute Gap, Best Brand, Whitespace. *Where the brand wins, loses,
  and can learn.*
- **ACTIVATE** — strategic reframe, attribute priority portfolio, messaging architecture, channel/source-role
  opportunity, external strategic analogies, activation roadmap. *What to do, what borrowed mechanism helps
  explain it, and in what order — without treating analogy as proof.*
- **DECIDE** — recommended decision, measurement contract, business-impact bridge, decision closure.
  *The single call and the smallest next move.*

Each report keeps the spine but sizes each beat to materiality. A beat with thin data compresses to a
half-slide and says so; it does not vanish (component-completeness rule).

## 5. The reframe engine (the heart of "world-class")

Exactly one strategic reframe per report, delivered on its own full-bleed slide. A reframe is not a summary;
it is a **new way to understand the business problem** that the evidence forces. Build it in four moves:

1. **Surface problem** — how the client currently states it. *"Our engagement is lower than competitors."*
2. **Actual perception problem** — what the data shows underneath. *"You own Offer (incentives) but rent
   Experience and Values; audiences reward you for cheap data, not for being modern or Indonesian."*
3. **Evidence chain** — the specific issues/attributes/gaps that prove it (traceable to row-level content).
4. **Desired perception shift** — from → to. *"From 'the affordable big operator' → 'the operator that
   makes being connected feel effortless and locally proud.'"*

**Anti-template test (mandatory):** write the reframe, then mentally swap the focus brand for a random
competitor. If it still reads true, delete it and rebuild — it is a generic observation, not a diagnosis.
The reframe must be false for every brand except this one.

## 6. The convergent method — two directions that must be allowed to disagree

EVO is built from both ends at once, and the disagreement between them is often the best finding.

- **Top-down (decision-led).** Start from the business decision at stake and produce a *reframe
  hypothesis* — specific enough to be wrong. Strong: *"Visibility is high but attached to Offer, not to
  trusted Experience."* Weak: *"The brand should improve Experience, Values, and Offer."*
- **Bottom-up (evidence-led).** Rebuild the answer from the ground:
  `real content → issue → base attribute → dominant driver → sentiment/magnitude → source role/stage → metric`.
  This pass must be able to **challenge** the hypothesis — it is not a hunt for confirming quotes.
- **Convergence.** Classify the result as:
  - **Confirmed** — evidence supports the hypothesis.
  - **Reframed** — the real problem sits elsewhere than the hypothesis assumed. *(Usually the most valuable
    outcome — this is where the reframe slide is born.)*
  - **Unresolved** — contradictory, contaminated, thin, or incomplete; disclose, don't force a verdict.

Hard principle: narrative ambition never overrides evidence; raw evidence never becomes strategy without
business context. Record `convergence_status` in the semantic output.

## 7. Who reads this — one spine, reader-appropriate emphasis

A perception report is read by different people for different reasons, often in the same PDF. Identify (or
ask for) the **primary reader** and let it set sequencing and register. The component set (see
`evo_report_structure.md`) never changes; what *leads* and how much detail each part carries does.

| Reader | Wants first | Depth | Register |
|---|---|---|---|
| **Decision Owner** (CMO, Brand Director, sponsor) | Reframe → decision → smallest next move | Headline diagnosis; evidence on demand | Plain, consequence-first, no jargon |
| **Activation Owner** (Brand/Comms Manager) | Messaging territories, channel roles, roadmap | Full activation chain; moderate evidence | Operational — owner, proof, sequence |
| **Evidence Owner** (Insights/Analytics lead) | Metric contract, attribute map, confidence | Full traceability, formulas, sample sizes | Precise, auditable; caveats not rounded away |
| **Execution Team** (agency, creative, CX) | Attribute capture, cultural + content mechanics, avoid-list | Concrete examples over abstraction | Tactical, example-led |

If the primary reader is unknown, default to **Decision Owner sequencing** (reframe + decision up front,
the other layers underneath) — it is the only ordering every other reader can also use as an entry point.
Never produce four separate reports; produce one spine with reader-appropriate emphasis. Record
`primary_reader_role` and `sequencing_applied` in the semantic output.

## 8. From diagnosis to decision — the discipline

DIAGNOSE and EXPLAIN earn the right to recommend; they are not the product. A finding is only finished when
it names: the attribute, its move type (§ recommendation vocabulary), the owner, the intervention, the proof
required, the metric, and the smallest next move. A report that ends at "here is what we found" is unfinished.
The client bought a decision, not a description.
