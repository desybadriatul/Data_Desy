# Daily Social Natural Evidence Links V1

## Problem
Daily Social reports still rendered old audit labels such as `S01`, `S06`, and appendix copy such as `Evidence ID & Full URL`, while CA and MMR already use client-facing natural CTAs like `Lihat post` / `Buka artikel`.

## Fix
- Daily Social slide payloads now convert evidence refs into natural CTA objects:
  - `Lihat post ↗`
  - `Lihat komentar ↗`
  - `Buka link ↗`
- S## audit IDs and raw URLs remain available in the data pack/evidence index, but are removed from visible slide payloads.
- The appendix becomes `APPENDIX — SOURCE LINKS`, not `APPENDIX — EVIDENCE ID & FULL URL`.
- The final render quality gate now blocks visible Daily Social S## audit labels.

## Guardrail
Run:

```powershell
python .\scripts\test_daily_social_natural_evidence_links_v1.py
python .\scripts\test_render_package_quality_gate_v1.py
python .\scripts\test_report_presentation_quality_v1.py
```

Expected:

```text
DAILY_SOCIAL_NATURAL_EVIDENCE_LINKS_V1_OK
RENDER_PACKAGE_QUALITY_GATE_V1_OK
REPORT_PRESENTATION_QUALITY_V1_OK
```
