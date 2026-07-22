# EVO Evidence Standard — proof discipline

> Every strategic conclusion in an EVO report must be traceable to real content. This file defines the
> evidence card, the traceability chain, and the no-fabrication rules that make the reframe and the
> recommendations auditable rather than asserted.

## 1. The traceability chain (every priority claim reaches all six links)

```
Real content  →  Audience response  →  Issue  →  Attribute  →  Perception consequence  →  Business implication
```

If a finding can't produce this chain, it is prose, not evidence. A driver-level posture claim with no
attribute-level evidence card behind it is incomplete — no matter how confident the sentence reads.

## 2. Evidence card schema

A priority evidence card carries:

1. **Attribute + segment** — the registered `attribute_id` and the brand/segment it belongs to.
2. **2–3 genuine snippets** — real excerpts, or clearly labelled paraphrases (paraphrase is never dressed
   as a quotation).
3. **Provenance** — source, channel, source role, date, metric, and link/URL.
4. **Business meaning** — why it matters to the client's decision (not "this was a popular post").
5. **Client-owned action + owner** — the move it implies and who on the client's team owns it.
6. **Confidence / sample status** — `hard fact | tagged sample | directional | hypothesis`, with `n`.

```json
{
  "attribute_id": "ATTR_EXP_RELIABILITY",
  "brand": "Telkomsel",
  "snippets": ["\"udah 3 hari sinyal ilang di daerah gue\" (paraphrased)"],
  "source": "X/Twitter", "source_role": "Organic UGC", "channel": "X", "date": "2021-11-14",
  "metric": {"basis":"engagement","value":4200}, "url": "https://…",
  "business_meaning": "Reliability complaints cluster in non-metro areas — the exact segment the 'Indonesian' positioning targets.",
  "action": "Fix — publish region-level restoration status; route to Network Comms.",
  "owner": "Network Communications",
  "confidence": "tagged sample", "n": 46
}
```

## 3. Minimum-evidence trigger (mandatory cards)

At least one evidence card is **required** for every attribute the gap analysis classifies as:

- **Real Strength** — Fragile Strength — **Active Vulnerability** (recurring negative) —
  **Contested Attribute** — **Recommended Whitespace** — **Priority gap.**

A Diagnose section that argues from driver posture without a card behind each priority attribute is
incomplete and does not pass QA (see `evo_quality_gate.md` G1).

## 4. No-fabrication rules (hard)

- No fabricated quote, no invented source, no invented activity, no invented causal conclusion.
- Never reuse the **same** excerpt to prove **different** attributes without a valid, stated reason.
- Paraphrase is labelled as paraphrase. A translation is labelled as a translation.
- A card without real supporting evidence is not made — the finding is downgraded or dropped, not
  manufactured into completeness.

## 5. Excerpt-type labels

Tag each snippet so the reader knows its weight: `direct quote · paraphrase · translated · summary ·
metric-only`. A "metric-only" card (numbers, no verbatim) can support magnitude but not tone or meaning —
don't let it carry an audience-perception claim by itself.


## 6. External analogy boundary

An external success story is **not** a focus-brand evidence card. It cannot:

- satisfy the mandatory-card trigger in §3;
- prove an Attribute Score, Gap, Best Brand, Whitespace, journey stage, or perception shift;
- raise the confidence of an internal finding;
- substitute for a citation to the focus brand's real content.

Store it separately as `evidence_status: External Analogy`, with a credible source, `what_to_adapt`, and
`what_not_to_copy`. The internal evidence chain must establish the recommendation first; the analogy only
helps illustrate a mechanism for activation. See `evo_external_strategic_analogies.md`.
