# CONSISTENCY CONTRACT — The Invariant Layer
## What must be identical across every onboarding run, so adaptation never drifts into inconsistency

> The four dials (offering type · client segment/complexity · source documents available · delivery
> cadence) exist to make every onboarding run **adapt** to its engagement. This file is their
> counterweight: it locks the parts that must **never** vary, so two runs — for two different
> clients, or for the same client's renewal — are *comparable, reproducible, and recognizably the
> same product*.

---

## PART 1 — BUILD-FROM-PREVIOUS-OUTPUT CHAIN (LOCKED)

```
project_brief  (foundation — scope, objectives, promises, Scope Source Registry)
      ↓
configuration_package  (every scope item/channel/language/region traced from project_brief)
      ↓
final_handover  (pure consolidation — zero new content)
      ↓
onboarding_kickoff_summary  (pure conversion of final_handover into a slide blueprint)
      ↓
client_welcome_summary  (pure extraction of client-facing content from final_handover)
```

This chain does not change between engagements. Each downstream output may reformat, summarize, or
select from what came before — it may never add new facts, new scope items, or new promises.

## PART 2 — COVERAGE RULE (LOCKED)

Every scope item that is `Included/Confirmed` or a preserved draft (`Optional`/`Deferred`/`Pending
Approval`/`Needs Validation`) in `project_brief.scope_and_configuration_setup` must have, in
`configuration_package`:
1. A row in `scope_summary`.
2. At least one row in `configuration_components`.
3. At least one row in `delivery_channel_setup` per target channel.
4. A row in `coverage_matrix` with a PASS/FAIL result.

Only `Excluded`/`Not Required` items are exempt — and only with a documented exclusion reason.

## PART 3 — STATUS LABEL LOCK

The eleven status labels in `system_prompt.md` ("STATUS LABELS") are the only labels used across all
five outputs. Do not invent new status labels or rename existing ones between engagements — a
downstream reader (or automated consumer) relies on the label set staying fixed.

## PART 4 — ARTIFACT FORMAT CONTRACT (LOCKED)

| Output | Format |
|---|---|
| `project_brief` | Markdown (`01_Project_Brief.md`) |
| `configuration_package` | Markdown (`02_Configuration_Package_Readable.md`) + CSV bundle (10 files, see `system_prompt.md`) — never XLSX |
| `final_handover` | Markdown (`03_Final_Onboarding_Handover.md`) |
| `onboarding_kickoff_summary` | Slide blueprint, or rendered `.pptx` (`04_Onboarding_Kickoff_Summary.pptx`) when rendering is available |
| `client_welcome_summary` | Markdown (`05_Client_Welcome_Summary.md`) |

The full JSON response wraps all five as structured fields; Markdown/CSV content lives only inside
their designated `markdown_content`/`csv_content` fields, never as loose text in the response.

## PART 5 — INTELLIGENCE BRIEF HANDOFF CONTRACT

If an Intelligence Brief (`intelligence-brief-generator` Layer 2) is supplied as input and its
`onboarding_handoff.ready_for_onboarding` is `true`, treat its `confirmed_scope_summary` as a
Tier-1 input to the Scope Source Registry (same priority as a Contract/SOW) rather than
re-researching scope from zero. If `ready_for_onboarding` is `false`, treat it as context only and
still build the registry from the other available sources.

## PART 6 — TRACEABILITY, NOT TEMPLATING

The chain and format above are fixed scaffolding — they must never contain identical scope items,
promises, or configuration content across two different clients. If swapping the client's name would
leave the configuration package still making sense unchanged, the scope work wasn't done — the
scope items, components, and channels must come from this client's actual sales inputs and research.
