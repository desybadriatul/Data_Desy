# EVO Activation Status

EVO Perception Intelligence is active on the `insight-report` branch.

## Status by layer

| Layer | Status | Implementation |
|---|---|---|
| Registry and routing | READY | Report/data-input registries, dispatcher, registry loader, and skill router |
| Task 1 builder | READY | Canonical enriched-post pull, EVO metrics, evidence, journey, benchmark, and frozen report input |
| Task 2 workflow and renderer | READY | Audience/benchmark gates, preview, PPT-ready package, audit pack, and quality gates |
| Attribute enrichment | READY | Incremental stratified sampling, map/store, validation, cache reuse, and batch tools |
| Shared contracts | READY | EVO metric addendum, R-EVO recipes, and quality-framework integration |
| MCP tool surface | READY | Workflow, preview, package, attribute-map, status, batch, and save tools |

## Definition of Done

```yaml
registry_status: READY
task1_builder_status: READY
task2_structure_status: READY
workflow_tools_status: READY
skill_router_status: READY
attribute_enrichment_status: READY
overall_status: READY
```

Runtime use still requires a configured database and campaign data. The workflow deliberately returns
`NEEDS_AUDIENCE`, `NEEDS_BENCHMARK`, or an attribute-classification batch when those inputs are incomplete;
these are operating gates, not implementation gaps.
