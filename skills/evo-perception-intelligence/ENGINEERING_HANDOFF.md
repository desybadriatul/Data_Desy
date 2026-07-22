# EVO — Engineering Handoff (Jalur 1 tool registration)

> This file is the bridge between the skill pack (content, contracts, gates) and the three tools that must
> exist in `server.py` for EVO to leave `NOT_IMPLEMENTED`. It is written against the *live* Cogan tool
> surface, checked directly on 2026-07-22: `check_report_builder_availability()` currently returns EVO in
> neither its `ready` nor `not_ready` list, and the six live report types' low-level primitive
> (`prepare_report_input`) and outline primitive (`build_prepared_report_outline`) were inspected to ground
> the parameter and gating conventions below, rather than guessing at them.

## 0. What already exists vs. what's net-new

| Piece | Status |
|---|---|
| `report_type_id` dispatch via registry | Exists as a pattern (six live types); EVO's row is drafted in `registry_drafts/report_type_registry_entry.yaml` |
| Canonical data pull, dedup, coverage | Exists — EVO reuses it unchanged (`consistency_contract.md`) |
| Per-post **attribute** tagging | **Does not exist.** This is the one genuinely new Task 1 primitive (see `evo_classification_contract.md`) |
| Low-level debug primitive (`prepare_report_input` equivalent) | Not required for EVO's first release — the three Jalur-1 tools below are the only interface Jalur 1 needs |
| Task 2 render / PPT assembly | Exists as a pattern (`build_*_ppt_package`); EVO needs its own instance driven by `evo_report_structure.md` |

## 1. `create_evo_perception_intelligence_report_workflow`

Jalur 1 front door — same role as `create_bce_report_workflow` / `create_competitive_analysis_report_workflow`.
Parameter set below extends the shape already used by `prepare_report_input`, with two changes made
**required** rather than optional, because EVO cannot run meaningfully without them.

```yaml
parameters:
  project_name: string            # required — same as all six live workflows
  start_date: string               # required
  end_date: string                 # required
  focus_brand: string               # required — EVO's "client_brand" equivalent; renamed for clarity since
                                    # EVO always names a single perception subject, never a bare keyword set
  competitor_brands: string        # REQUIRED for EVO (differs from the optional field on the live types) —
                                    # comparative diagnosis (Best Brand, Attribute Gap, Whitespace) cannot run
                                    # on a single brand; see evo_report_structure.md A2 and the Non-negotiables
                                    # in SKILL.md
  primary_reader: string            # required — return NEEDS_AUDIENCE and stop if absent (SKILL.md
                                    # Non-negotiables; mirrors the audience gate other workflows already have)
  desired_perception: string        # optional — client's stated target meaning, if known; frames A1/A3
  attribute_map_source: enum        # optional, default "auto" — "client_approved" | "category" | "auto"
                                    # (auto = category -> evo_seed fallback ladder in evo_attribute_map.md)
  keywords: string                  # optional, same semantics as the live types
  exclude_keywords: string          # optional
  channels: string                  # optional
  match_mode: string                # optional, default "any" — same semantics as prepare_report_input
  analysis_objective: string        # optional
  confirmed_intent_id: string       # optional — search-trail label only, never verified against an Intent
                                    # Confirmation record, same convention as prepare_report_input
persist: true                      # not exposed as a parameter; EVO always persists Task 1 output, same as
                                    # the live types, because Task 2 depends on the frozen output list
```

**Guardrails at this layer:**
- If `primary_reader` is absent → return `NEEDS_AUDIENCE`, do not proceed.
- If `competitor_brands` is absent or empty → return `NEEDS_BENCHMARK` (new status, EVO-specific) with a
  message offering the documented fallback: a single-brand perception diagnosis with
  `competitive_analysis: unavailable` (per SKILL.md Non-negotiables) — proceed only if the caller explicitly
  confirms that fallback, mirroring how other gates require an explicit confirmation rather than a silent
  default.
- Dispatch to `reporting.task1.builders.evo_perception_intelligence` via the registry, exactly like the six
  live types dispatch through their `module_path`.

## 2. `build_evo_perception_intelligence_report_data_preview`

Task 1 preview — same role as `build_prepared_report_outline`, but EVO-specific because its preview surfaces
attribute-layer content the other six types don't have (attribute map, classification confidence, journey
stages, external analogies, component completeness) in addition to the scope/data-health preview they all
share.

```yaml
parameters:
  report_input_id: string   # from the workflow call above
  allow_partial: boolean    # default true, same convention as build_prepared_report_outline

returns:                    # evo_data_preview.json — user-facing Task 1 preview
  scope_and_data_health: {...}          # shared shape with the other six types
  evo_frame: { experience_def, values_def, offer_def, category_attributes }
  attribute_map: { source, version, attributes: [...] }
  classification_audit: {...}           # the nested funnel object specified in evo_classification_contract.md §6
  attribute_gap_preview: [...]          # Attribute Score / Best Brand / Gap / Whitespace, focus brand excluded
  journey_preview: {...}                # Awareness/Engagement/Impact stage counts per evo_journey_model.md
  external_analogy_candidates: [...]    # unvalidated candidates only; validation happens before Task 2 freezes them
  component_completeness_forecast: {...}  # which Core components the current data can and cannot support
```

`preview_confirmed` (user) must precede any call to the PPT-package tool below — same pakem as every other
Jalur 1 type.

## 3. `build_evo_perception_intelligence_report_ppt_package`

Task 2 — selects material components per `evo_report_structure.md`, sizes slides, renders PPTX + audit pack.
Never recomputes a metric or invents evidence (SKILL.md Non-negotiables); reads only from the frozen output
list in `skill_mapping.yaml`.

```yaml
parameters:
  report_input_id: string
  preview_confirmation_token: string   # proof the preview gate was passed, same convention as other build_*_ppt_package tools

returns:
  pptx_path: string
  audit_pack:
    evo_quality_report.json
    evo_component_completeness_audit.json   # includes renumbering map for any skipped Conditional component
    evo_metric_manifest.json
    evo_classification_audit.json
    evo_external_analogy_manifest.json
```

**Guardrails at this layer (enforced by `evo_quality_gate.md` before the PPTX is returned):**
- G1–G13 run as documented; **G14 (client-facing language integrity)** scans the rendered text layer for the
  jargon/procedural-language list before the file is returned — this is the concrete regression test for the
  bug this pack was revised to close.
- Component-completeness audit must show every Core component `produced` or `skipped — reason`; any skipped
  Conditional component must show a clean renumbering map, not a silent gap.

## 4. Registration checklist

- [ ] Add `evo_perception_intelligence` row to the live `report_type_registry.yaml` (draft: `registry_drafts/report_type_registry_entry.yaml`)
- [ ] Add `brand_perception_and_positioning` row to the live `business_problem_registry.yaml` (draft: `registry_drafts/business_problem_registry_entry.yaml`)
- [ ] Write `reporting.task1.builders.evo_perception_intelligence`, including the attribute-tagging primitive
- [ ] Register the three tools above in `server.py`
- [ ] Add EVO metric entries (Sentiment Index, Attribute Score, Attribute Gap, Whitespace, EVOScore) to the
      shared `consistency_contract.md` Metric Dictionary
- [ ] Add the `"attribute"` enrichment block to whatever function backs `get_report_enrichment_plan()`, in the
      same shape as the existing `topic` / `spokesperson` blocks (see `readiness_gap.md`, live-verification note)
- [ ] Add R-EVO visual recipes to `perpustakaan_resep_slide.md` per `evo_visual_contract.md`
- [ ] Flip each status in `readiness_gap.md`'s Definition of Done as the corresponding piece lands; only set
      `overall_status: READY` once every layer is true — EVO should stay `NOT_IMPLEMENTED` in
      `check_report_builder_availability()` until then, same discipline the pack has held since the audit
