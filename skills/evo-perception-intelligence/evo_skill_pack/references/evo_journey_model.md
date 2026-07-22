# EVO Journey Model — how perception moves

> Perception doesn't appear; it travels. This file defines the three-stage journey, the source-role
> taxonomy, and the two ways to read them — so the report can say *where a brand only gets seen* versus
> *where it actually changes public meaning*, and locate the leak.

## 1. The three stages (assign by observable function, not by channel)

| Stage | What it is | What it is NOT |
|---|---|---|
| **Awareness** | Visibility, framing, facts introduced — usually brand-initiated or media-carried | Not proof that anyone believes it |
| **Engagement** | Audiences react, participate, amplify, or contest the framing | Not proof the meaning stuck |
| **Perception Impact** | Meaning becomes external: organic association, validation, advocacy, recurring criticism, memes, institutional reaction beyond brand control | Not the same as high reach or high likes |

**The core discipline:** Awareness and Engagement are **not** Perception Impact. A viral brand post is
Awareness with amplification; it becomes Impact only when the audience independently carries the meaning.
Most decks overclaim here — resist it. Virality filters for *materiality* (which signals are worth reading);
it does not upgrade a signal's stage.

## 2. Source roles (who forms perception, and how the signal travels)

Source role is not the channel and not virality — it is the *function* a voice plays.

```
Owned / Official · Earned Media · Creator / Influencer · Expert / Authority ·
Community / Fanbase · Organic UGC · Retail / Reseller / Marketplace ·
Institution / Regulator · Brand / Event Partner
```

Why it matters: a recommendation to "post more on TikTok" is a platform checklist. A recommendation to "move
Reliability proof from Owned claims to Expert/Authority validation, because audiences discount the brand's
own reliability claims but trust third-party teardown creators" is a *role* strategy — and only the second
shifts perception. Choose channels by the role they play in the journey, never by platform popularity.

## 3. Two reads (use either or both, per the business question)

**A. Comparative Journey Matrix** — `Brands × (Awareness · Engagement · Perception Impact)`.
Reveals which brands only generate visibility and which convert it into organic perception. Each cell can
carry: attribute, issue, source role, channel, evidence, magnitude, function.

**B. Focus-Brand Intervention Map** — `(Experience · Values · Offer) × (Awareness · Engagement · Impact)`.
Finds the focus brand's weak stage and the required intervention. Each cell: stage weakness, source-role
gap, journey leak, required intervention, owner, required proof, expected movement.

Don't force a complete cell where no tracked signal exists — mark it "no tracked signal," don't invent one.

## 4. Journey-diagnosis (the actionable output)

A journey problem takes two different shapes, and a report must be able to name either — they call for
different interventions, so collapsing them into one label loses the thing that makes the diagnosis
actionable.

### 4.1 Transition leaks — strength at one stage fails to reach the next

| Leak | Pattern | Implication |
|---|---|---|
| **Awareness → Engagement** | Big reach, little reaction | The framing isn't relevant or participatory; fix the message/mechanic, not the spend |
| **Engagement → Impact** | Lots of reaction, no organic association | People engage with the *content* but not the *brand meaning*; the attribute isn't sticking — needs proof, not more posts |
| **Missing Awareness** | Impact-worthy attribute nobody sees | An owned meaning under-amplified; a scale/amplification opportunity |

The leak points directly at the move type (`evo_recommendation_vocabulary.md`): an Engagement→Impact leak on
a strength is usually **Protect + Build proof**; a missing-Awareness leak on a positive attribute is **Scale**.

### 4.2 Single-stage problems — the problem lives *inside* one stage, not in the handoff between two

A transition leak assumes the stage itself is healthy and the *handoff* fails. That's not always true — a
stage can be the problem in its own right. Diagnose which case applies before recommending anything; the two
require different interventions even when the surface symptom (weak Impact, say) looks similar.

| Stage | Where the problem sits (diagnostic signal) | What to do |
|---|---|---|
| **Awareness** | **(a) Absent** — an attribute that matters in the category has no visibility for the focus brand at all. **(b) Hijacked framing** — visibility exists, but someone other than the brand is setting the frame (a reseller, an unaffiliated persona, a competitor narrative); the brand is "seen" but not on its own terms. **(c) Wrong-segment** — awareness is real but concentrated outside the primary reader's actual audience or the category's real buyers. | **(a)** category demand + brand right-to-play → **Build** the frame deliberately; don't wait for organic uptake. **(b)** name who currently owns the framing and **Fix** the distribution/partnership gap that let them own it — this is a structural gap, not a "post more" problem. **(c)** redirect distribution/source-role toward the right segment; **Scale**-ing the wrong audience wastes the move rather than fixing it. |
| **Engagement** | **(a) No reaction** — reach without participation; a relevance or mechanic failure. **(b) Negative/contesting reaction** — the audience engages by pushing back, mocking, or correcting the framing. **(c) Narrow source-role diversity** — engagement is real but confined to one role (e.g. only Owned channels react; no Earned, Creator, or Community layer picks it up). | **(a)** → **Fix** the message or mechanic, not the media spend. **(b)** → **Fix** the underlying claim or proof gap causing the pushback *before* any further Awareness spend; amplifying a contested claim compounds the damage rather than curing it. **(c)** → deliberately widen source-role diversity, naming the specific missing role (e.g. "needs Expert/Authority validation, not another Owned post") rather than repeating the same channel. |
| **Perception Impact** | **(a) No conversion** — engagement never becomes organic, brand-independent association; people react to the content, not to the brand's meaning. **(b) Negative/recurring** — the organic association that does form is negative, and it recurs rather than appearing as a one-off issue; a criticism has become entrenched reputation. **(c) Authored elsewhere** — the dominant organic narrative is carried by an unintended actor (e.g. a reseller or affiliate community becomes the loudest definition of the brand), displacing the brand's own intended meaning. | **(a)** → **Protect + Build proof**: name the specific third-party validation mechanism (Expert/Authority, Community) still missing between consumed content and believed meaning. **(b)** → **Fix at the root cause**, not the symptom — a recurring negative Impact-stage pattern needs an operational or product-level intervention, not a messaging patch. **(c)** → this is **reframe-worthy**, not a routine Fix: surface it explicitly in E1 Strategic Reframe, because the brand's actual problem is that someone else is authoring its meaning. The intervention is a deliberate choice — formalise or co-opt that actor's role on purpose, or actively compete for the frame — not a default assumption that the current holder is a threat to remove. |

**How this feeds the report:** `D3 Focus-Brand Intervention Map` (`evo_report_structure.md`) carries whichever
diagnosis applies — `journey leak` (§4.1) or `stage weakness` (§4.2) — in its `required intervention` field;
the diagnosis and the move type it resolves to should read as one continuous sentence, not two disconnected
labels. `E6 Activation Roadmap`'s `first problem` field is this diagnosis, stated in the same terms.

## 5. Integrity

Journey claims obey the same confidence rules as everything else — a stage assignment on a handful of posts
is directional. Never present Awareness or Engagement counts as evidence of Impact, and never assign a stage
by a channel rule ("TikTok = Engagement"); assign by what the content and audience actually did.
