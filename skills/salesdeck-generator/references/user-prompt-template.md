# User Prompt Template — Fill per client/meeting

Collect this context for every deck. Fields not yet available may be filled
`Unknown / Not Provided`. **Do not complete with assumptions just to look more
complete** — input quality determines whether the deck feels specific or
generic. If a critical field is missing (business question, stakeholder, core
evidence), issue a CLARIFICATION REQUEST before generating.

```
Run the DATAXET:SONAR Sales Deck Generator.

## 1. Execution Mode
- execution_mode: [STRATEGY_REVIEW / CONTENT_DRAFT / FINAL_PRODUCTION]

## 2. Company and Meeting Context
- Company name:
- Industry / sub-industry:
- Market / region:
- Sales stage: [Introduction / Discovery / Demo / Follow-up / Proposal / Renewal / Upsell / Executive Readout]
- Meeting objective:
- Presentation duration (minutes):
- Deck language: [Bahasa Indonesia / English / other]

## 3. Stakeholders and Decision
- Primary stakeholder and authority level:
- Other stakeholders present:
- Target decision from this deck:
- Target decision owner:
- Known decision blockers / likely objections:

## 4. Strategic Direction
- Primary business question (one question only):
- Requested deck archetype (optional):
- Preferred strategic angle (optional): [Risk-led / Opportunity-led / Control & efficiency-led / other]
- Desired buyer orientation (optional): [Reputation protection / Control & clarity / Growth / Alignment / other]
- Sensitive or prohibited topics:

## 5. Client Evidence Status
- Client-confirmed needs / statements:
- Client-confirmed constraints:
- Known public or client-specific evidence:
- Assumptions that must be treated as hypotheses:
- Known evidence or source gaps:
- Existing client terminology that should be used:

## 6. Product and Commercial Guardrails
- Approved Sonar product reference / capability document:
- Approved credentials / case studies allowed for client use:
- Commercial boundary / proposal / SOW / pricing schema:
- Include pricing: [true / false]
- Scope that is confirmed vs still proposed:

## 7. Reference Files Attached
- Pre-Sales / Intelligence Brief:
- Handover / MoM / conversation notes:
- Insight report / screenshots / evidence pack:
- Public research / source list:
- Brand guide / logo / reference deck:

## 8. Design and Output Preferences
- Client brand assets available: [yes / no]
- Design reference (optional):
- Required visual or chart preferences:
- Required sections or slides:
- Slides or claims to avoid:
- Need speaker notes: [yes / no]
- Need battle card / champion script: [yes / no]

## 9. Output Required
- For STRATEGY_REVIEW: return source assessment, 2-3 scored angles, selected strategy,
  primary business question, proposed story arc, and critical missing data.
- For CONTENT_DRAFT: return a concise executive summary and valid Content Contract JSON.
- For FINAL_PRODUCTION: return the validated Content Contract JSON, editable PPTX,
  rendered slides, visual/content QA, and change log.

## Final Instruction
Use only supported facts and approved Sonar claims. Keep all client-facing text in
deck_language. Do not invent pricing, scope, implementation timing, SLA, capability detail,
or case-study results. Flag unresolved gaps clearly and propose the smallest appropriate CTA.
```

## Input priority (which inputs win)

When inputs conflict, weigh them by this priority — and when a product reference
or pricing schema is missing, never fabricate detail; mark it as missing data,
use more general wording, and set `include_pricing = false`.

1. Client-confirmed statements — MoM, handover, email, meeting notes, written
   approval.
2. Commercial documents and product reference — proposal, SOW, product
   capability, credentials, pricing boundary.
3. Pre-Sales / Intelligence Brief — synthesis of client needs, validation needs,
   initial angle.
4. Client-specific evidence — insight report, social listening, clipping,
   screenshot, campaign data.
5. Credible public sources — official site, regulator, company report, industry
   research, credible media.
6. Inference and hypothesis — only as indication or validation question, never
   as fact.

## What stays fixed vs. what changes per request

- **System Prompt (do not change per request):** the base rules — evidence,
  strategy, visual, CTA, output contract, quality gate. Change only through a
  targeted change request so the output flow is not broken.
- **User Prompt (change every request):** locks the client context, target
  decision, sources, scope, and required output. Input quality decides whether
  the deck feels specific or generic.
