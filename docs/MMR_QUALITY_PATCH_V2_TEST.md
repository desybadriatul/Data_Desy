# MMR Quality Patch v2 Test Guide

Patch v2 upgrades the Mainstream Media Report renderer/workflow for crisis/legal-quality output.

## Adds

- Brand-facing risk posture separate from raw sentiment posture.
- Fact vs Allegation slide payload.
- Media Response Action Plan with Owner / Trigger / Do / Do Not / Deadline / Evidence URL.
- Timeline / Escalation Pattern slide payload.
- Issue Risk Map using severity × exposure.
- Noise/off-topic evidence guard: noise is excluded from main callouts and kept for audit/data pack only.
- Spokesperson normalization hints, e.g. Dedi/KDM/Dedi Mulyadi merged.
- URL display policy: clickable label on main slides, full URL in appendix.

## Test

```powershell
python -m py_compile .eporting	ask2enderers\mainstream_media_report_renderer.py
python -m py_compile .eporting	ask2\workflows\mainstream_media_report_workflow.py
python -m py_compile .\scripts	est_mainstream_media_quality_v2.py
python .\scripts	est_mainstream_media_quality_v2.py
```

Expected:

- render_package_version = mainstream_media_report_render_package_v2
- slides include FACT VS ALLEGATION, TIMELINE / ESCALATION PATTERN, ISSUE RISK MAP
- brand_facing_risk_posture appears in preview/package
- noise candidates are excluded from main slides
