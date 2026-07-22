# EVO Attribute Map — the perception vocabulary

> Topics answer *what content is about.* Attributes answer *what perception content forms.* EVO scores,
> gaps, best-brand, and whitespace all run on the attribute layer — so the attribute map is the single most
> load-bearing asset in the pack. This file defines its schema, its priority ladder, and a category-neutral
> **seed map** to use when nothing better is approved.

## 1. Why attributes, not topics

"Giveaway with a K-pop artist" is a topic. The *attribute* it forms is **Affordability/Incentive** (Offer)
or **Collaboration** (Values), depending on how the audience reads it. A report that scores topics has
measured conversation volume; a report that scores attributes has measured perception. Only the second
answers an EVO question.

The auditable bridge is the **attribute chain** — never classify a post straight into a driver when an
observable attribute exists:

```
content → material issue → base attribute → driver (E | V | O)
```

Issue expression format: `Theme — Issue name: Attribute`.
Example: `Payment — Balance deducted but merchant unpaid: Transaction Reliability`.
A driver bar with no issue behind it is not a finding.

## 2. Attribute map schema (minimum fields — names alone are insufficient)

```yaml
attribute_id:        ATTR_EXP_RESPONSIVENESS      # stable, unique
attribute:           "Responsiveness"
driver:              Experience                    # Experience | Values | Offer
working_definition:  "Perception that the brand answers, resolves, and shows up when the customer needs it."
positive_cues:       ["fast reply", "issue resolved", "proactive support", "24/7 help"]
negative_cues:       ["ignored complaint", "slow response", "unanswered ticket", "bot loop"]
exclusion_cues:      ["giveaway response rate", "campaign engagement"]  # look similar, are NOT this attribute
category:            telco                          # or 'generic' for seed entries
map_source:          client_approved | category_specific | evo_seed
map_version:         "1.0"
```

`positive_cues` / `negative_cues` / `exclusion_cues` are what make row-level classification reproducible and
auditable. Exclusion cues are as important as positive ones — they stop adjacent-but-different signals from
inflating an attribute.

## 3. Map priority ladder (disclose which tier was used)

```
1. Client-approved attribute map   — always preferred; reflects the client's own strategy language
2. Category-specific attribute map — a maintained map for the category (telco, banking, FMCG, …)
3. EVO seed attribute map (§5)     — category-neutral fallback; MUST be disclosed as seed in Integrity output
```

Using the seed map is legitimate but must be stated (`attribute_map_status: evo_seed (fallback)`), because a
client will read their own strategy vocabulary into the report otherwise.

## 4. Naming locks and defaults

- **V is always "Values," never "Value."** (The singular collapses Values into Offer.)
- Price / rewards / stock / distribution default to **Offer** unless the issue is explicitly about honesty,
  safety, or credibility (then Values).
- One issue can touch two drivers; assign a **primary** driver for scoring and note the secondary in
  rationale. Do not double-count a single post's basis across drivers.

## 5. EVO seed attribute map (category-neutral fallback)

Use only when no client-approved or category map exists. These are *starting* attributes — a real run
should localise the working definitions and cues to the category. Full set below; every registered
attribute must receive a status in the report (present, weak, absent, contaminated, or whitespace).

### Experience — *what it's like to engage*
| attribute_id | attribute | working definition (short) |
|---|---|---|
| ATTR_EXP_RELIABILITY | Reliability / Performance | The core product/service works as promised, consistently |
| ATTR_EXP_RESPONSIVENESS | Responsiveness / Care | The brand answers and resolves when the customer needs it |
| ATTR_EXP_EASE | Ease / Usability | Interactions are simple, fast, low-friction |
| ATTR_EXP_ENTERTAINMENT | Entertainment / Delight | Engaging with the brand is enjoyable, playful, culturally alive |
| ATTR_EXP_PARTICIPATION | Participation / Co-creation | Audiences do something *with* the brand, not just watch it |
| ATTR_EXP_INNOVATION | Innovation / Modernity | The brand feels current, inventive, ahead |

### Values — *what the brand believes, and whether the audience believes it*
| attribute_id | attribute | working definition (short) |
|---|---|---|
| ATTR_VAL_ACCOUNTABILITY | Accountability / Honesty | The brand owns problems, is transparent, keeps its word |
| ATTR_VAL_LOCALPRIDE | Local Pride / Cultural Legitimacy | The brand belongs to and champions its audience's identity |
| ATTR_VAL_SUSTAINABILITY | Sustainability / Responsibility | The brand acts on environmental/social responsibility credibly |
| ATTR_VAL_EMPOWERMENT | Empowerment / Inclusion | The brand lifts, includes, and gives agency to its audience |
| ATTR_VAL_COLLABORATION | Collaboration / Partnership | The brand allies with people/brands the audience trusts |
| ATTR_VAL_SAFETY | Safety / Security / Trust | The brand can be trusted with money, data, and wellbeing |

### Offer — *what you get versus what you pay*
| attribute_id | attribute | working definition (short) |
|---|---|---|
| ATTR_OFF_AFFORDABILITY | Affordability / Value-for-money | The price/benefit trade reads as fair or generous |
| ATTR_OFF_INCENTIVE | Incentive / Reward | Giveaways, loyalty, and perks that add tangible value |
| ATTR_OFF_ACCESS | Access / Availability | The offer is easy to reach, obtain, and use where needed |
| ATTR_OFF_PACKAGE | Package / Product Design | The way the offer is bundled fits how people actually buy |
| ATTR_OFF_CLARITY | Offer Clarity | Terms, pricing, and value are understandable, not hidden |
| ATTR_OFF_CHOICE | Choice / Flexibility | The audience can pick what fits them; not one-size-fits-all |

## 6. Anti-shortcut clause (this is what QA enforces)

Naming attribute-like phrases in prose does **not** satisfy the attribute layer. Every attribute referenced
in a Diagnose section must resolve to a registered `attribute_id` and carry its sample size (`n`), per-brand
distribution, and net sentiment. A narrative that names attributes without ID, `n`, or sentiment is
driver-level analysis wearing an attribute costume — reject it in QA, do not render it. See
`evo_classification_contract.md` for how the tags are produced and `evo_quality_gate.md` G1 for the gate.
