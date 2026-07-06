---
name: insight-report-generator
description: >-
  Universal, story-first / solution-first engine that turns raw social, media, survey, or other data
  plus journey artifacts into a consultant-grade executive insight report and an editable PPTX.
  Works for ANY report type — the type, narrative, analytical lens, and solution framing are DERIVED
  from the client's business problem, pain point, and objective, not picked from a fixed menu. Use
  whenever the user wants an insight report, reporting deck, executive report, periodic analysis, brand
  perception, competitive, issue/crisis, segmentation, PR/campaign, industry/trend, or custom report, or
  wants to turn rawdata into a PPTX that closes a client's original pain with evidence, research,
  client-owned recommendations, and a decision slide. Trigger even when phrased as "buatkan insight
  report", "generate report PPTX", "laporan dari rawdata", "reporting deck", "ubah data jadi report",
  "bikin report untuk klien X", or any request to turn a dataset into a decision-first deck —
  whether or not a report type is named.
---

# Universal Insight Report Generator

This skill turns raw data (social, media, survey, CRM, sales, operational — whatever is supplied) plus
inherited client-journey context into a single, story-first executive insight report and, when code
execution is available, an editable PPTX.

The report is **not** a dashboard dump and **not** a vendor sales deck. It is a consultant-style
deliverable that answers one business question and recommends client-owned business actions.

## What "universal" means here

There is **no fixed menu of report types**. The engine diagnoses the client's business problem, pain
point, and objective, then **derives** four adaptation dials from that situation:

1. **Expert approach** — the sub-expertise the report needs (crisis communicator, segmentation
   ethnographer, competitive analyst, measurement scientist, or a self-named hybrid for a custom report).
2. **Pain-point type** — one of five (Time-to-Know · Time-to-React · Signal-vs-Noise · Proof-to-Decide ·
   Blind-Spot); sets the storyline and the solution framing.
3. **Analytical lens** — the frame that organizes the report; chosen to fit the problem, or **invented and
   named** for a custom report. Not selected from a closed list.
4. **Arc emphasis** — which canonical beats expand and which compress for this specific report.

One engine, every report type. The same Stage A→F machinery runs each time; only the four dials change.

## Read order

Read all three references before producing a report. They are layered:

- **`references/methodology.md`** — *how to think.* The consultant DNA, the three voices, the five
  pain-point types, the lens library, the narrative arc, bridge sentences, insight-led headlines, and the
  universality principle. Read this to set the four dials and decide the angle.
- **`references/system_prompt.md`** — *how to execute.* The full universal engine: the Universal
  Adaptation block, Stages A→F, evidence hierarchy, missing-data protocol, layout rotation rules, PptxGenJS
  technical rules, QA gates, the user-input template, and the output contract.
- **`references/quality_framework.md`** — *what blocks vs guides vs stays silent.* The tiered A/B/C
  rulebook (hard guardrails, thinking lenses, internal QA). Read it before finalizing, and use it to
  decide which rules are fatal and which are judgment.
- **`references/consistency_contract.md`** — *what must be identical across every report.* The invariant
  layer the four dials are balanced against: the locked Metric Dictionary, the Reconciliation & Provenance
  Gate (Stage C.5), the Design Token theme, and the Canonical Slide Contract. Read it before Stage C
  compute; it is what keeps output reproducible and comparable across clients and across months.
- **`references/perpustakaan_resep_slide.md`** — *how to build each slide.* The per-slide recipe library
  that turns the Canonical Slide Contract's named roles into concrete builds: each slide's job, which
  report type/beat it fits, the PptxGenJS + theme-token steps, and which Cogan tool feeds it. Read it
  while writing the Stage E production brief and rendering Stage F.
- **`references/stage_data_cogan.md`** — *how to pull data from Cogan.* When the data source is the live
  Cogan database (not an uploaded Excel), this replaces only the *source* in Stage C: prove-first with
  `data_health`, pull the metrics each beat needs via Cogan tools mapped to the Metric Dictionary, freeze,
  then run the C.5 gate. The rest of the engine (Stages A, B, D, E, F) is unchanged.

Read `methodology.md` first to frame the problem, run `system_prompt.md` end to end (using
`stage_data_cogan.md` for the Stage C data pull when Cogan is the source), hold
`consistency_contract.md` as the invariant layer while computing and rendering, follow
`perpustakaan_resep_slide.md` when building each slide in Stage E/F, and apply
`quality_framework.md` as the gate before delivery.

## When to use

Use this skill when the user wants:

- an insight report deck from rawdata, for any report type or none specified
- a reporting PPTX for a client engagement
- a brand, perception, issue, crisis, competitive, PR, campaign, segmentation, industry, trend, or custom
  report
- a story-first executive analysis grounded in data evidence
- recommendations and a decision grounded in rawdata + client journey artifacts

## Required inputs

Collect or infer from attachments when available:

- rawdata (Excel / CSV) — the only source of internal metrics
- field definition / data dictionary
- client name, report period, market, language, audience
- one business question or the client's original pain point
- journey artifacts if available: Intelligence Brief, Sales Deck, Project Brief, Final Handover, Keyword
  Package, MoM, onboarding notes
- preferred output language and any PPTX requirements

If rawdata is missing, do **not** invent internal metrics. Ask for the rawdata, or produce only a
planning/diagnostic response (Stages A–B) with a clear missing-input status.

If the Cogan MCP server is connected, it may be used purely as a **data provider** to fetch the rawdata
(call `get_report_guide` first, then find_project, list_campaigns, data_health, metrics_summary,
count_posts, timeline, detect_spikes, share_of_voice, compare_campaigns, compare_periods, top_authors,
top_viral_posts, top_media, get_posts, export_raw_data). See `skill_mapping.yaml` for the slide-role→tool
map. Do not run the wordcloud workflow as part of this skill.

## Workflow summary

Follow `system_prompt.md` exactly. In order:

1. **Set the four dials** (Universal Adaptation) from the client's situation.
2. **Stage A — diagnose** the primary business problem, business question, decision at stake, reframe
   hypothesis.
3. **Stage B — architect the storyline** before choosing charts; name (or invent) the analytical lens.
4. **Stage C — validate and transform** the rawdata; halt before insight if validation FAILS.
5. **Stage D — develop insights**, bridge sentences, no standalone reframe slide (any contrast insight rides on a data slide's headline), and Scale/Fix/Test
   recommendations as client-owned actions with client owners.
6. **Stage E — build the production brief** with insight-led headlines and a declared layout per slide.
7. **Stage F — generate and QA the PPTX** when code execution is available (data freeze → PptxGenJS →
   render → QA → present).

## Non-negotiable rules

- Rawdata is the only source for internal metrics, rankings, quotes, sentiment, engagement, share of
  voice, or share of engagement. If it isn't in rawdata, it is not an internal finding.
- Public research may fill context, benchmarks, methodology, and public facts — but must be cited with a
  URL and listed on a References slide. It must never substitute internal metrics.
- Journey artifacts frame the problem and scope; they must never become vendor feature recommendations.
  Translate any product-action field back into the client business action it enables.
- Every recommendation is a business action owned by the client's own team (OWNER TEST + VENDOR-SWAP
  TEST). The monitoring/data tool appears at most once, as an enabler.
- Reframe is NOT a slide. Never render a standalone words-only/dark reframe slide (forbidden — reads empty). A "not X — but Y" insight, if it matters, becomes the HEADLINE of a data-bearing slide; default is none.
- No metric-only slides, no noun-phrase topic headlines, no two consecutive slides with the same layout.
- The deck ends on a client decision and smallest next step — never a buy/demo/pilot CTA.
- If data validation fails, stop before producing misleading slides.
- Every internal metric is computed from the locked Metric Dictionary; the Stage C.5 reconciliation gate
  (sum-of-parts = total, headline traceability, single definition, net-sentiment basis labeled) passes or
  every gap is resolved and footnoted before any narrative is written.
- All visual constants come from the locked `theme.json`; the required anchors and slide-count band of
  the Slide Contract hold (middle shape follows intent; reframe optional). `contract_version` and `theme_version` are stamped.
- Swapping the client/brand name must break the report; if it would still stand, it is a template — rebuild.

## Quality priority framework (A / B / C)

Not every rule carries the same weight. The full definitions live in `references/quality_framework.md`;
read it before finalizing any report. The three tiers, in brief:

**A — Hard guardrails (mandatory; block delivery).** Fatal errors. Fix before shipping, or halt.
- *Metric consistency* — a number means the same thing everywhere; freeze metrics once, never re-derive.
- *No invented timeline* — no 30/60/90-day, week, month, or quarter promises unless they come from the brief.
- *Source quality for sensitive claims* — safety, legal, financial, regulatory, or competitor claims need a
  strong, cited source with a URL on the References slide.
- *No overclaim on weak data* — small samples, single points, or outliers get directional wording, never absolutes.
- *Data integrity* — internal metrics and verbatim quotes come only from rawdata; research fills context only.
- *Client-owned recommendations* — every recommendation passes the OWNER and VENDOR-SWAP tests; the tool appears
  at most once as an enabler; the deck closes on a client decision, not a buy/demo/pilot CTA.
- *Validation halt* — if data validation fails, stop before producing narrative slides.

**B — Thinking lenses (flexible; guide reasoning, don't gate).** Use judgment, adapt per report.
- *Business Decision Gravity* — every slide pulls toward the one decision, though not always literally.
- *Diagnostic Lens Library* — choose (or invent and name) the lens that best fits the problem.
- *Competitor relevance* — compare competitors by their role in the problem, not metric-by-metric.
- *Reframe* — never a standalone words-only slide (forbidden); fold any contrast insight into a data slide's headline.

**C — Lightweight QA (internal only; never in the output).** Silent self-checks, run before delivery.
- Client red-team sanity check · headline-metric scan · source-weakness check · generic-recommendation check.
- Run them silently; fix what fails. Never add a "QA" or "self-critique" section to the client-facing deck.

Craft rules that still hold regardless: no standalone reframe slide (a contrast insight rides on a data slide's headline; never words-only), no
metric-only slides, no noun-phrase topic headlines, no two consecutive slides with the same layout, and a
report that would break if the client/brand name were swapped (if it would still stand, it's a template — rebuild).

## Expected output

Depending on environment and request:

- the four-dial adaptation block + Stage A diagnosis and Stage B storyline
- validated data layer (Stage C)
- insight layer with bridge sentences, reframe, and client-owned recommendations (Stage D)
- the Flexible Slide Production Brief (Stage E)
- executable PptxGenJS generation code and an editable `.pptx` (Stage F) when rendering is available
- QA notes covering overflow, overlap, contrast, provenance, layout rotation, and recommendation quality
