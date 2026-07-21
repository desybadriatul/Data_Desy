---
name: onboarding-generator
description: >-
  Universal, consultant-grade Client Onboarding Output Generator. Turns a closed deal's sales
  artifacts (SOW/contract, intelligence brief, sales deck, MoM, onboarding form) into five
  onboarding outputs: Project Brief, Configuration Package (scope/setup as Markdown + CSV
  bundle), Final Handover, Kickoff Summary, and Client Welcome Summary, traceable to what was
  sold. Works for ANY vendor and ANY offering type (media/social monitoring, SaaS, professional
  services, media buying, analytics); what counts as a scope item and delivery channel is set per
  engagement, never hardcoded. Use whenever the user wants onboarding documents for a new client,
  a project brief from sales/SOW/MoM inputs, a configuration or scope package, a kickoff deck, or
  a client welcome summary. Trigger even when phrased as "buatkan onboarding klien baru",
  "generate project brief", "proses input klien untuk onboarding", "buat paket
  konfigurasi/keyword", or any request supplying a closed deal's inputs to prep a client for
  delivery.
---

# Universal Onboarding Output Generator

This skill turns a closed deal's sales-side artifacts into the operational package delivery/CX
teams need to start work — five connected outputs, each built strictly from the one before it, so
nothing promised at sales time gets lost and nothing new gets invented at onboarding time.

It is **not** a sales tool and **not** a discovery brief — that is the Intelligence Brief
(`intelligence-brief-generator`) and a separate deck-generation step's job. This skill starts once
a deal is confirmed and turns commitments into a scoped, traceable delivery setup.

## What "universal" means here

There is no fixed product or industry baked into this skill. Every onboarding run is built from
**adaptation dials** set from the actual engagement:

1. **Offering Type** — what was sold: a media/social monitoring service, a SaaS/software
   implementation, a professional-services or consulting engagement, a media-buying/ad campaign, a
   data/analytics engagement, or another offering entirely. This dial decides what a "scope item"
   and a "delivery channel" concretely mean (see the table below). Supplied by the user or inferred
   from the sales inputs — never assumed to be one fixed product.
2. **Client Segment / Onboarding Complexity** — Simple/self-serve vs. multi-stakeholder enterprise
   — changes how much of Training & Enablement, Escalation Path, Risk Register, and Stakeholder
   sign-off gets built out (present at every tier, but proportionate).
3. **Source Documents Available** — contract/SOW, intelligence brief, sales deck, MoM, onboarding
   form, manual scope input — whatever exists. Missing documents narrow what can be confirmed, not
   a reason to invent content.
4. **Delivery Cadence** — one-time setup vs. recurring reporting/service cadence — shapes the
   Reporting Preferences and Communication Cadence Plan sections.

| Offering Type (examples) | "Scope item" means | "Delivery channel" means |
|---|---|---|
| Media / social monitoring | A brand, competitor, product, campaign, issue, or event to track | A social/media platform or query surface (Twitter/X, TikTok, online media, forums, ...) |
| SaaS / software implementation | A module, feature set, or workflow to configure | An environment, integration, or user role |
| Professional services / consulting | A workstream or deliverable | A stakeholder touchpoint or reporting forum |
| Media buying / ad campaign | A campaign or line item | An ad platform or placement |
| Data / analytics engagement | A dataset, metric, or dashboard to build | A data source or reporting destination |

Not a closed list — for an offering type not shown, define the scope-item/delivery-channel meaning
explicitly in the Project Brief's `expert_approach` note and hold it consistently through all five
outputs.

One engine, every offering. The same five-output, build-from-the-previous-output machinery runs
each time; only what fills "scope item" and "delivery channel" changes.

## Read order

- **`references/system_prompt.md`** — *how to execute.* The full engine: role determination, the
  research protocol and status labels, the Scope Source Registry discipline, the five output
  schemas, the CSV/JSON output format, and the final validation rules. This is the operative
  document — follow it exactly.
- **`references/quality_framework.md`** — *what blocks vs guides vs stays silent.* The tiered A/B/C
  rulebook. Read before finalizing.
- **`references/consistency_contract.md`** — *what must be identical across every onboarding run.*
  The invariant layer: the build-from-previous-output rule, the coverage rule, the status-label
  lock, and the file/CSV format contract.
- **`references/user_prompt_template.md`** — the fill-in template for collecting engagement inputs.

Read `system_prompt.md` first to run the engine end to end, hold `consistency_contract.md` as the
invariant layer while building each output, and apply `quality_framework.md` as the gate before
delivery.

## When to use

Use this skill when the user wants:

- onboarding documents for a client whose deal has just closed
- a project brief built from a contract/SOW, MoM, sales deck, or intelligence brief
- a configuration/scope package (keywords, modules, workstreams — whatever the offering needs) in a
  reviewable, operations-ready format
- an internal handover document consolidating everything sales promised
- an onboarding kickoff deck outline or a client-facing welcome summary

If an **Intelligence Brief** (`intelligence-brief-generator`) exists for this client and its
`onboarding_handoff.ready_for_onboarding` is `true`, start from its
`confirmed_scope_summary` rather than re-discovering scope from scratch.

## Required inputs

Check against `references/user_prompt_template.md`:

- **Offering type** — required if it can't be inferred from the sales inputs.
- Client context and project objective (industry, business model, pain points, expected outcome)
- Sales-side documents: contract/SOW, intelligence brief, sales deck, MoM/email/chat notes — as many
  as exist; "not provided" is fine, invented content is not
- Onboarding/account setup details: PIC, admin/user contacts, package, timezone, limits
- Manual scope input (optional) — if incomplete, extract scope from the documents above instead
- Output language and expected file list

## Workflow summary

Follow `system_prompt.md` exactly. In order:

1. **Set the four dials**, especially Offering Type — this decides what a "scope item" and
   "delivery channel" mean for every output that follows.
2. **Choose expert lenses per output** — document the chosen approach in each output's
   `expert_approach` field; do not default to one fixed persona for every section.
3. **Build the Scope Source Registry** before writing the Project Brief — extract every entity with
   an onboarding/setup need from all inputs, classify it, and decide whether it needs a standalone
   scope item.
4. **Output 1 — `project_brief`** — the strategic foundation. Everything downstream traces to it.
5. **Output 2 — `configuration_package`** — Markdown + CSV bundle, built strictly from
   `project_brief`'s confirmed scope. Run the Completeness Gate before writing it.
6. **Output 3 — `final_handover`** — pure consolidation of Outputs 1–2. No new content.
7. **Output 4 — `onboarding_kickoff_summary`** — converts `final_handover` into a kickoff-deck
   blueprint. No new content.
8. **Output 5 — `client_welcome_summary`** — extracts client-facing content from `final_handover`.
   No internal flags, no over-promise warnings, no raw configuration syntax.
9. **Run the Final Validation Rules** (see `system_prompt.md`) before returning output.

## Non-negotiable rules

- **Build from the previous output.** `configuration_package` takes every scope item, language,
  region, and channel from `project_brief` — it never invents a new one. `final_handover`,
  `onboarding_kickoff_summary`, and `client_welcome_summary` contain **no content that isn't
  sourced from the outputs before them.**
- **Scope completeness.** Every entity in the Scope Source Registry that needs a standalone scope
  item must appear as one in `project_brief.scope_and_configuration_setup` — and every scope item
  there must have configuration components, delivery-channel setup, and a coverage-matrix row in
  `configuration_package`. Nothing silently disappears; excluded items keep a documented reason.
- **Optional/deferred items are drafts, not deletions.** Anything marked optional, deferred,
  pending approval, or needs-validation stays as a draft scope item with that status — never
  dropped.
- **Research what's publicly verifiable; ask only for what isn't.** Use status labels honestly (see
  `system_prompt.md`) — `Need Client Confirmation` / `Need Internal Confirmation` are for things no
  public search could ever answer (internal KPIs, internal PIC names, contract structure), not a
  shortcut for things that just weren't searched yet.
- **Client-facing output never leaks internal material.** `client_welcome_summary` excludes
  internal flags, over-promise warnings, sensitive internal notes, and raw configuration/query
  syntax.
- **Configuration package is never a spreadsheet file.** Deliver it as Markdown (readable) + a CSV
  bundle (operational), per the schema in `system_prompt.md` — never as a single XLSX.
- **Format output strictly.** Return valid JSON with Markdown only inside designated
  `markdown_content`/`csv_content` fields, per `system_prompt.md`'s FORMAT OUTPUT section.

## Quality priority framework (A / B / C)

Full definitions live in `references/quality_framework.md`. In brief:

**A — Hard guardrails (mandatory; block delivery).**
- Scope Source Registry completeness before Project Brief is finalized
- Every scope item traceable from Project Brief through Configuration Package (components →
  delivery-channel setup → coverage matrix)
- No new content introduced in Outputs 3–5 beyond Outputs 1–2
- Client-facing output (`client_welcome_summary`) never contains internal flags or raw
  configuration syntax
- Valid, complete JSON per the schema; configuration package never delivered as XLSX
- Coverage Matrix has no unresolved FAIL rows before `Ready for Setup` is declared

**B — Thinking lenses (flexible; guide reasoning, don't gate).**
- Offering-type interpretation of "scope item" and "delivery channel"
- Expert-lens selection per output
- Onboarding-complexity proportionality (how much Risk Register / Training Plan / Stakeholder
  sign-off detail a given client segment needs)

**C — Lightweight QA (internal only; never in the output).**
- Status-label honesty check (nothing marked "Need Confirmation" that a search would have answered)
- CSV formatting check (headers, quoting, no embedded line breaks)
- Client-facing leak check on `client_welcome_summary`

## Expected output

Depending on what the user asks for and what execution environment is available:

- `01_Project_Brief.md`
- `02_Configuration_Package_Readable.md` + a CSV bundle (scope summary, research intelligence,
  configuration components, delivery-channel setup, coverage matrix, exclusions/edge cases,
  validation checklist, ops setup notes, missing information, glossary)
- `03_Final_Onboarding_Handover.md`
- `04_Onboarding_Kickoff_Summary` (blueprint, or a rendered `.pptx` when code execution/pptx
  rendering is available — see `/mnt/skills/public/pptx/SKILL.md`)
- `05_Client_Welcome_Summary.md`
