# CA Strategic QA V1

Fixes Competitive Analysis render-package defects found during live smoke test:

- Prevent SOV/SOE fallback to 0.0 by reading client metrics from `qt_ca_brand_volume_engagement`.
- Align risk evidence with the claim: `Mitigate Competitive Risk` uses negative client evidence, not top positive posts.
- Add a concentration check under the Competitive Landscape Evidence section so one viral post is not framed as systemic advantage.
- Deduplicate cross-brand evidence rows and infer the visible brand from content when possible.
- Hide internal topic labels such as `Unclassified / Needs LLM` from client-facing slides.
- Add strategic QA validation beyond link integrity.
