# CONSISTENCY CONTRACT — The Invariant Layer
## What must be identical across every brief, so adaptation never drifts into inconsistency

> The four dials (vendor/offering context · client segment · sector adaptation · meeting stage) exist to
> make every brief **adapt** to its engagement. This file is their counterweight: it locks the parts that
> must **never** vary, so two briefs — for two different clients, or for the same client at two different
> meeting stages — are *comparable, reproducible, and recognizably the same product*.
>
> **The reconciliation:** the dials adapt CONTENT (the angle, the emphasis, the framing). This contract
> locks FORM, EVIDENCE DISCIPLINE, and SCHEMA (the scaffold, the citation system, the JSON shape). A fixed
> scaffold is not a template — identical *content* is. The brief still breaks if you swap the client's name
> and evidence for another client's.

---

## PART 1 — EVIDENCE TAGGING SYSTEM (LOCKED)

Every specific claim in every brief uses exactly one of three tags, with exactly this meaning:

| Tag | Meaning | Rule |
|---|---|---|
| `[Cx]` | Client-Provided Context | Something the client already said, in any channel. Never replaced by inference. |
| `[Sx]` | Public Web Source | A cited, dated, sourced fact from independent research. Logged in `source_registry.web_sources`. |
| `[Hx]` | Hypothesis / Inference | Anything inferred rather than stated or sourced. Always labeled "Hypothesis" or "Needs confirmation" in the body text — never bare. |

No specific, checkable claim in either layer may go untagged. This tagging system does not change between
briefs, vendors, or industries.

## PART 2 — LAYER RECONCILIATION GATE (Tier-A · run before delivery)

Before returning the output, verify:

1. Every number, name, or claim that appears in both layers is identical in both places.
2. Every `[Cx]`/`[Sx]` cited in Layer 1 has a matching entry in Layer 2 `source_registry`.
3. `meta.primary_problem` in Layer 2 matches the framing used in Layer 1 "The Angle" and "Snapshot".
4. `meta.handover_readiness` in Layer 2 matches whatever "Next Step" in Layer 1 implies about deck/
   onboarding readiness.
5. Every schema key in Layer 2 is present (never deleted), even when empty.

If any check fails, fix it before delivery — never ship two layers that disagree.

## PART 3 — LENGTH & FORMAT CONTRACT (LOCKED)

| Element | Contract |
|---|---|
| Layer 1 | Markdown, ≤2 pages / ~900 words outside tables. Section order fixed: Snapshot → The Angle → Why Now → Top Pain Points → Opening & Demo Cheat-Sheet → Top 5 Discovery Questions → Red Flags → Pre-Meeting Checklist → Next Step. |
| Layer 2 | One JSON object, full schema from `system_prompt.md`, never truncated for length. |
| Separator | A single `---` line between Layer 1 and Layer 2. |
| Language | One language throughout both layers, matching the User Prompt's specified output language. No mixing. |
| File naming (if saved) | `ExecBrief_[Client]_[Date].md` and `IntelRepo_[Client]_[Date].json`. |

## PART 4 — SCHEMA LOCK

The Layer 2 JSON schema in `system_prompt.md` is the contract every downstream consumer (deck generator,
CRM, onboarding generator, proposal tool) is built against. Do not rename, remove, or restructure keys
between briefs — if a new field is genuinely needed for a specific engagement, add it as an additional key
rather than repurposing an existing one, so older consumers don't silently misread new data.

## PART 5 — ONBOARDING HANDOFF CONTRACT

When `onboarding_handoff.ready_for_onboarding` is `true`, the `onboarding_handoff.confirmed_scope_summary`
field must contain enough confirmed detail (offering, primary problem, data/configuration scope) that a
separate onboarding-brief step could start from it without re-asking the basics. If scope isn't confirmed
enough, set the flag `false` and list what's missing in `open_items_before_onboarding` rather than
guessing at scope to make the flag look ready.
