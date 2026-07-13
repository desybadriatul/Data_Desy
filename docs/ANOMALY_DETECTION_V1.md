# Cogan Anomaly Detection V1

Adds a monitoring-only anomaly scan layer for Cogan.

## New tools

- `scan_anomalies`
- `list_anomaly_detectors`
- `configure_anomaly_terms`

## Design

- `anomaly.py` is pure computation: detector registry, baseline math, finding ranking.
- `database/anomaly_queries.py` reuses `db._canonical_cte()` and does not change schema.
- `anomaly_tools.py` exposes MCP tools and keeps output monitoring-only, not report-ready.
- `server.py` only gets a registration block. Existing report workflows and legacy spike tools are not overwritten.

## Guardrail

`scan_anomalies` does not return `report_input_id` and is not compatible with `build_*_ppt_package`. If a finding needs to become a report, use the normal flow: `get_report_guide()` -> Intent Confirmation -> relevant report workflow.

## Suggested post-deploy config

```text
configure_anomaly_terms("Aqua", noise_terms="elektronik,badminton,mesin cuci")
configure_anomaly_terms("Bluebird", noise_terms="ASTS,satelit,AST SpaceMobile")
```
