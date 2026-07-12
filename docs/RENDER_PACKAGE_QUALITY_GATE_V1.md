# Render Package Quality Gate V1

Adds a final client-facing and strategic QA gate after report render-package creation and before PPT generation.

The gate blocks packages when:
- a sub quality check fails;
- Action Plan section order violates Action-Plan-First structure;
- visible raw URLs or audit IDs leak into client-facing slides;
- internal/system wording leaks into client-facing slides;
- URL-backed evidence is present without natural CTA labels (`Buka artikel`, `Lihat post`, `Lihat komentar`);
- Competitive Analysis renders false 0.0 SOV/SOE client metrics;
- Competitive Analysis risk actions use non-negative or non-client evidence;
- Competitive Analysis misses concentration check;
- MMR action cards use non-taxonomy action types or miss rationale.

If the gate fails, the package is returned as:

```json
{
  "success": false,
  "workflow_status": "BLOCKED_BY_RENDER_QA"
}
```

This prevents technically valid but strategically unsafe packages from being rendered as client decks.
