# EVO Readiness Gap — what's still needed to reach `overall_status: READY`

> The Lima-Layer spec defines *what* to implement across five layers. This file is the honest accounting of
> what is **done**, what is **content I can produce as skill files** (this pack), and what is **backend
> engineering that must happen in the Cogan codebase** and cannot be produced from a chat. The distinction
> matters: EVO must stay `NOT_IMPLEMENTED` in `check_report_builder_availability()` until the builder module
> exists, because a partial/approximate build would violate the computation-source lock this pack exists to
> enforce.

## Status by layer

| Layer | Lima-Layer spec | This pack delivers | Still requires engineering |
|---|---|---|---|
| **1. Registry & routing** | registry entry, business-problem entry, triggers, routing table | Draft registry + business-problem YAML, trigger list, routing rules (`skill_mapping.yaml`, SKILL.md) | Merge drafts into live `report_type_registry.yaml` / `business_problem_registry.yaml`; add the router row in the live SKILL.md |
| **2. Task 1 builder** | `reporting.task1.builders.evo_…` module: canonical pull, EVO enrichment, metrics, evidence, journey, frozen output | Full contracts for every step (attribute map, classification pipeline + prompt, metric formulas, evidence schema, journey model, frozen-output list) | **Write the Python builder module.** Includes the one net-new primitive: the per-post attribute-tagging pass (§3 below). No existing Cogan tool does this |
| **3. Task 2 structure** | component contract, tiers, storyline roles, completeness rule | Complete component library A–F with objective / required output / tier / storyline_role / completeness gate (`evo_report_structure.md`) | Wire the contract into the renderer + register R-EVO visual recipes |
| **4. Three tools** | workflow, data preview, ppt package | Full parameter, output, and guardrail spec for all three | Register the three tools in `server.py`; implement preview + package assembly |
| **5. Skill & router** | skill pack, router update, metric contract, QA | The complete skill pack (this) + EVO metric entries + EVO QA gate G1–G14 | Register EVO metrics into shared `consistency_contract.md`; add the QA gate section; add R-EVO recipes to `perpustakaan_resep_slide.md` |

## The three genuine gaps (in priority order)

**1. The attribute-tagging primitive (Task 1, Step 3) — the real engineering work.**
The other six report types never need a per-post attribute layer, so Cogan has no primitive for it. This
step resolves the attribute map, classifies each canonical post to an `attribute_id` with confidence and
rationale, and freezes the tags. `evo_classification_contract.md` specifies the pipeline, prompt, sampling,
and audit — but the module that runs it must be written. Everything downstream (Attribute Score, Best Brand,
Gap, Whitespace) depends on these row-level tags and, per the computation-source lock, must never be
backfilled from driver aggregates. **Until this exists, keep EVO `NOT_IMPLEMENTED`.**

**2. Tool registration (`server.py`) + preview/package assembly.**
The three tools are fully specified but not registered. `competitor_brands` should be **required** (not
optional) at the workflow layer for EVO specifically — the benchmark charter can't run without a locked
comparison set, unlike single-brand-capable Daily Social.

**3. Registry / contract reconciliation against live files.**
The registry, business-problem, metric-dictionary, and visual-recipe additions are drafted from the observed
Cogan pattern (six READY builders, the shared insight-report skill package), not copied from the live
`report_type_registry.yaml` / `consistency_contract.md`, which weren't in this session. They need field-name
reconciliation against the actual files before merge.

## Content assets this pack newly supplies (didn't exist before)

These are the things the spec *named* but did not *contain* — and that the reference deck lacked, which is
why it read as "informative but lacks insight":

- a category-neutral **seed attribute map** with cues (so tagging is reproducible without waiting for a client map);
- the **classification prompt + confidence + audit contract** (so tags are defensible);
- the **numeric metric formulas** (Sentiment Index, Attribute Score, Gap, Whitespace) the spec only named;
- the **reframe engine** and the **dashboard→consultant worked examples** that set the actual quality bar;
- the **move-derivation logic** (diagnosis pattern → Scale/Fix/Protect/Build/Test/Monitor/Avoid);
- the **perception→business bridge with validation status** (so business impact is claimed honestly);
- **fourteen EVO-specific QA gates** (G1–G14, including G14 client-facing language integrity, added after a
  delivered deck leaked an internal QA test name onto a client-facing slide) on top of the universal A/B/C
  framework.

## Live-system verification (this revision)

Checked directly against the running Cogan MCP server rather than assumed:

- `check_report_builder_availability()` confirms EVO does not yet appear in either the `ready` or `not_ready`
  builder list — the pack has not been wired in at all yet, consistent with keeping it `NOT_IMPLEMENTED`
  rather than a partial/approximate state.
- `get_report_enrichment_plan()` on a live report type (`competitive_analysis`) returns a shape like:
  `{"report_type_id", "topic": {"enabled", "mode", "hard_max_items", "allow_auto_expand"}, "spokesperson":
  {"enabled", "run_after_topic_ready"}}`. EVO's net-new attribute-tagging step should be registered as a
  sibling `"attribute"` block in this same shape (`enabled`, a sampling `mode` such as
  `stratified_10pct`, `hard_max_items`, `allow_auto_expand: false`) rather than as a free-form field —
  this keeps EVO consistent with how the other two enrichment types are already exposed, and is now
  reflected in `skill_mapping.yaml`'s `enrichment_plan` section.

## Definition of Done (unchanged from spec)

```
registry_status: READY          # layer 1 merged + reconciled
task1_builder_status: READY      # builder module written, incl. attribute-tagging primitive
task2_structure_status: READY    # component contract wired into renderer + R-EVO recipes registered
workflow_tools_status: READY     # three tools registered in server.py
skill_router_status: READY       # this pack + metric entries + QA gate live
overall_status: READY
```

This pack moves `skill_router_status` and the *content* of layers 1–4 to done. The remaining `READY` flips
are code changes in the Cogan repo — chiefly the Task 1 builder's attribute-tagging step — which I can spec
precisely (as above) but cannot deploy from here.
