# EVO External Success Stories & Strategic Analogies — borrowed patterns, inspiration not proof

> External cases help the client see **how a strategic mechanism can travel**. They do not prove that the
> same result will occur for the focus brand. Use them only after the internal EVO diagnosis has established
> the priority attribute, journey leak, proof gap, and client right-to-play.

## 1. Role in the EVO logic

External success stories sit inside **ACTIVATE**, between Messaging / Channel Translation and the Activation
Roadmap:

```
internal diagnosis → priority attribute + journey leak → external pattern → adapt / do-not-copy boundary
                  → client-owned move → proof → metric → smallest next step
```

Their evidence status is always **`External Analogy`**. They are strategic inspiration, not:

- evidence that the focus brand owns an attribute;
- evidence that perception has changed;
- proof that a recommendation will work;
- a substitute for a valid benchmark, Best Brand, Attribute Gap, or focus-brand evidence card;
- a basis for sales, ROI, conversion, or other business-impact claims.

A recommendation must remain defensible from the focus brand's own evidence even if every external analogy
is removed.

## 2. Trigger and quantity

For a full EVO report with recommendations, include **2–4 external success stories or strategic analogies**
when credible research is available. Use fewer only when the fit is genuinely narrow; record the reason.

Run the component only after E1–E4 have fixed:

- the actual perception problem;
- the priority EVO driver and attribute;
- the Awareness → Engagement → Perception Impact leak;
- the source-role / channel function;
- the proof the focus brand must create.

If no credible analogy or source can be verified, mark the component:

```yaml
status: skipped
reason: no_credible_external_analogy_found
```

Never fabricate a case to complete the deck.

## 3. Selection test — mechanism match, not category resemblance

Choose cases because the **mechanism** matches the focus-brand problem, not merely because the brand is
famous or operates in a similar category. A strong analogy can explain one of the following:

- how official Awareness became community-led Perception Impact;
- how participation became recurring Experience proof;
- how expert / authority voices built credible Values proof;
- how sponsorship became an owned content ecosystem rather than a one-off event;
- how a brand handled memes, criticism, or public humour without overreacting;
- how community, reseller, creator, or employee voices made Offer / access feel real;
- how a proof asset travelled across channel and source roles.

Every selected case must pass all of these checks:

1. **Analogous issue:** the focus-brand tension is materially similar.
2. **EVO fit:** a named driver and priority attribute are supported.
3. **Journey fit:** the case shows a clear stage movement or leak solution.
4. **Mechanism fit:** the source role, channel route, voice, content mechanic, proof, or CTA is transferable.
5. **Right-to-play:** the focus brand can credibly adapt the mechanism.
6. **Boundary:** the parts that must not be copied are explicit.
7. **Source quality:** a credible citation or evidence source is recorded.

## 4. Required card schema

Each analogy card must contain:

| Field | Requirement |
|---|---|
| `case_brand` | External company / brand |
| `industry` | Industry or adjacent category |
| `strategy_pattern` | The mechanism that made the case useful |
| `analogous_issue` | Why it is relevant to the focus brand's diagnosed problem |
| `priority_attribute` | Focus-brand attribute the analogy informs |
| `evo_driver` | Experience / Values / Offer |
| `journey_route` | e.g. Awareness → Engagement, Engagement → Impact, Awareness → Impact |
| `channel_source_role` | Channel and role that carried the mechanism |
| `proof_mechanism` | What made the claim credible or socially repeatable |
| `what_to_adapt` | The transferable principle for the client |
| `what_not_to_copy` | Category, claim, aesthetic, operating model, or risk boundary |
| `client_right_to_play` | Why the focus brand can credibly use the adapted pattern |
| `linked_move_type` | Scale / Fix / Protect / Build / Test / Monitor / Avoid |
| `evidence_source` | URL, citation, report, official case material, or source note |
| `evidence_status` | Always `External Analogy` |
| `applicability_confidence` | High / Medium / Low, with rationale |

## 5. Journey-route discipline

Do not assign stage movement from reach or engagement alone.

- **Awareness → Engagement** requires observable participation, response, or amplification.
- **Engagement → Perception Impact** requires organic association, validation, advocacy, recurring framing,
  or other public meaning beyond the brand's control.
- **Awareness → Impact** may be used only when the case clearly contains an earned validation mechanism;
  visibility by itself never qualifies.

Use the same journey definitions as `evo_journey_model.md`.

## 6. Deck expression

Recommended component headline:

> **Borrowed patterns — inspiration, not proof**

Render 2–4 concise cards. Each card should show:

```
case + strategy pattern
E/V/O driver · journey route
how the mechanism worked
Adapt: the focus-brand translation
Don't copy: the boundary
Source: citation · External Analogy
```

The component belongs after Messaging Architecture / Channel Opportunity and before the Activation Roadmap.
It should not become a long case-study chapter. Its job is to make the activation mechanism easier to see,
then hand the reader directly into a client-owned move.

## 7. Good-use examples

Use external analogies to illuminate patterns such as:

- converting race or event sponsorship into recurring participant testimony;
- turning a community structure into self-published Experience proof;
- pairing product communication with credible functional, safety, or expert validation;
- building an owned content system that outlives a sponsored moment;
- using creator, reseller, employee, or user voices to make Offer and access tangible.

These are pattern categories, not reusable recommendations. The selected cases must still be researched and
mapped to the current focus brand.

## 8. Failure modes

Reject or rebuild the component when:

- the story is included only because the external brand is famous;
- `what_to_adapt` is generic ("build community", "create engagement");
- `what_not_to_copy` is missing;
- the case is treated as proof of likely sales or perception lift;
- the analogy replaces internal evidence or benchmark learning;
- the journey route is inferred only from reach, likes, or attendance;
- the same case could be pasted into any brand deck without changing its logic;
- the citation is missing, unverifiable, or materially weaker than the claim.

## 9. Frozen output contract

External research must be resolved before rendering and frozen as:

```json
{
  "external_analogies": [
    {
      "case_brand": "...",
      "industry": "...",
      "strategy_pattern": "...",
      "analogous_issue": "...",
      "priority_attribute": "...",
      "evo_driver": "Experience|Values|Offer",
      "journey_route": "Awareness -> Engagement -> Impact",
      "channel_source_role": "...",
      "proof_mechanism": "...",
      "what_to_adapt": "...",
      "what_not_to_copy": "...",
      "client_right_to_play": "...",
      "linked_move_type": "Scale|Fix|Protect|Build|Test|Monitor|Avoid",
      "evidence_source": "...",
      "evidence_status": "External Analogy",
      "applicability_confidence": "High|Medium|Low",
      "applicability_rationale": "..."
    }
  ]
}
```

Task 2 may select or compress frozen cards. It may not invent a new case, source, claim, or analogy.
