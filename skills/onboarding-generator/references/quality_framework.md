# QUALITY PRIORITY FRAMEWORK — A / B / C
## The balanced rulebook: what blocks delivery, what guides thinking, what stays internal

> **Tier A — Hard guardrails:** mandatory. A violation is a fatal error → fix before delivery, or halt.
> **Tier B — Thinking lenses:** flexible guidance for reasoning. Adapt per engagement; never a checkbox.
> **Tier C — Lightweight QA:** silent, internal self-checks. Run them; never surface them in the output.

---

## TIER A — HARD GUARDRAILS (mandatory; block delivery)

### A1 · Scope Source Registry completeness
Every entity across all inputs that needs onboarding/configuration attention is classified in
`project_brief.scope_source_registry` before `scope_and_configuration_setup` is finalized. An
unmapped scope-requiring entity blocks `Ready for Setup`.

### A2 · Full traceability, scope item to configuration
Every scope item in `project_brief` has configuration components, delivery-channel setup, and a
coverage-matrix row in `configuration_package`. No scope item is silently dropped, merged, or
demoted into another item's sub-component.

### A3 · Build-from-previous-output discipline
`configuration_package` never introduces a scope item, language, region, or channel absent from
`project_brief`. `final_handover`, `onboarding_kickoff_summary`, and `client_welcome_summary`
contain zero content that isn't traceable to an earlier output.

### A4 · Client-facing leak prevention
`client_welcome_summary` never contains internal flags, over-promise warnings, sensitive internal
notes, or raw configuration/query syntax.

### A5 · No XLSX for configuration_package
The configuration/scope package is always delivered as Markdown + a CSV bundle — never a single
spreadsheet file, never a `workbook_spec`.

### A6 · Valid, complete JSON output
The full response is valid JSON, Markdown/CSV content is confined to designated fields, every CSV
has correct headers/quoting, and no text exists outside the JSON object.

### A7 · Coverage Matrix gate
`Ready for Setup` is never declared while any Coverage Matrix row is an unresolved FAIL. A FAIL
forces `overall_status = "Needs Revision"` at both the checklist and quality-review level.

### A8 · Status-label honesty
`Need Client Confirmation` / `Need Sales/Account Confirmation` / `Need Internal Confirmation` are
used only for data that genuinely cannot be found from any public source — never as a substitute for
skipping a search.

---

## TIER B — THINKING LENSES (flexible; guide reasoning, don't gate)

### B1 · Offering-type interpretation
"Scope item" and "delivery channel" take their meaning from the resolved Offering Type — apply the
dial table's logic with judgment for offering types not explicitly listed, rather than forcing a
media-monitoring frame onto a SaaS or services engagement.

### B2 · Expert-lens selection per output
Choose the expertise each output actually needs (documented in `expert_approach`) rather than
defaulting to one fixed persona across all five outputs.

### B3 · Onboarding-complexity proportionality
A simple/self-serve client still gets every required field, but proportionately brief; a
multi-stakeholder enterprise client gets fuller Risk Register, Training Plan, and Stakeholder
sign-off detail. Neither is "wrong" — match effort to actual complexity.

### B4 · Delivery-channel variant judgment
Some delivery channels legitimately need multiple configuration variants for full coverage (per
that channel's own convention); others don't. Decide per channel rather than applying a blanket
rule.

---

## TIER C — LIGHTWEIGHT QA (internal only; never in the output)

### C1 · Status-label honesty check
Scan every "Need Confirmation" item — could a public search plausibly have answered it? If so,
search first or downgrade the label.

### C2 · CSV formatting check
Headers match `columns`, every cell is quoted, no embedded line breaks, lists use ` | ` not commas.

### C3 · Client-facing leak check
Read `client_welcome_summary` as if forwarding it to the client right now — would anything internal
or raw-syntax slip through? Remove it.

### C4 · Traceability spot-check
Pick a few scope items at random and trace them from `scope_source_registry` through
`configuration_package` and into `final_handover` — confirm nothing was lost or altered in transit.

---

## HOW THE TIERS INTERACT

- **A overrides everything.** A well-organized configuration package (B-level craft) built on an
  incomplete Scope Source Registry (A1) is rejected — complete the registry first.
- **B is where the run earns "consultant-grade."** Two onboarding runs can both pass all of A and
  still differ in usefulness because of how well B was applied — proportionate depth, the right
  expert lens, the right channel-variant judgment.
- **C never appears.** Its job is to make A and B true in the final artifact, silently. If a C check
  fails, fix the output — do not add commentary explaining that you checked.
