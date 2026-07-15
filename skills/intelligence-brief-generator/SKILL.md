---
name: intelligence-brief-generator
description: >-
  Universal, consultant-grade Pre-Sales / Account Intelligence Brief engine. Turns client context
  (chat, email, call notes, CRM handover, RFP) plus independent web research into a two-layer output:
  a scannable Executive Brief for the sales/BD team and a structured Intelligence Repository (JSON)
  that downstream tools (sales-deck, CRM, proposal, or onboarding generators) can consume directly.
  Works for ANY vendor, product, or service and ANY client industry; offering, evidence, and framing
  are supplied per engagement, never hardcoded. Use whenever the user wants a pre-sales brief, account
  intelligence brief, meeting prep, discovery brief, deal brief, or BD cheat-sheet, or asks to turn
  client notes plus research into something a sales team can use minutes before a meeting. Trigger
  even when phrased as "buatkan intelligence brief", "brief pre-sales untuk klien X", "siapkan meeting
  prep", "riset klien untuk meeting besok", or any request supplying client context and a company name
  for a pre-meeting brief.
---

# Universal Intelligence Brief Generator


## Cogan MCP runtime addendum — Jalur 0 Client / Intelligence Brief

In the Cogan MCP universe, this skill is **Jalur 0**: the first presales artifact that normalizes raw client/prospect context into a Client Intelligence Brief. It runs before any downstream sales deck, onboarding, campaign setup, or report-generation step.

Use this skill for any of these user phrasings, including Indonesian and typo variants:

- client brief / brief klien / brief calon klien
- presales brief / pre-sales brief / brief presales
- account brief / account intelligence brief
- meeting prep / meeting prep klien
- BD cheat-sheet / BD cheatsheet
- intelligence brief / intel brief / intellifence brief / inteligence brief
- brief dari chat / brief dari WhatsApp / brief dari WA
- brief dari email / percakapan email klien
- brief dari call note, meeting note, CRM, SCS handover, RFP, or pasted conversation

Routing rule:

- If the user asks for any of the above, call `get_intelligence_brief_guide()`.
- Do **not** call `get_report_guide()` first.
- Do **not** call any `create_*_report_workflow` tool.
- Do **not** scan Cogan data unless the user explicitly asks to validate the brief against available monitoring data.
- Do **not** generate downstream artifacts in this skill. Sales deck, onboarding, and report generation are later steps and must not be produced here.

Default vendor/offering context for Cogan:

If the user does not specify what is being offered, use this default instead of halting: Dataxet/Sonar/Cogan media intelligence, social listening, mainstream media monitoring, competitive intelligence, reputation intelligence, campaign monitoring, anomaly detection, spokesperson/media analysis, dashboard/reporting, and insight/report generation. Mark it as default context, not client-provided context. If the user supplies another vendor/offering, the user-supplied context overrides this default.

Output-format confirmation:

After producing the brief in chat, stop and ask whether the user wants it packaged as a file. Do not auto-generate PDF, DOCX, Google Docs, Markdown, or JSON files before confirmation.

Ask exactly in this spirit:

> Brief sudah siap. Mau saya jadikan file juga? Pilih: DOCX/Google Docs, PDF, Markdown+JSON, atau cukup di chat.

If the user chooses a file format, generate only that requested format in the follow-up step.

This skill turns client context (what the client has already said, in any channel) plus independent
public research into a single, two-layer **Intelligence Brief**: a short document a sales or account
team can act on within five minutes, backed by a complete, machine-consumable research repository.

It is **not** a sales deck and **not** a company research dump. It is the *intelligence layer* that
sits before storytelling — it prepares what to say and prove; a separate deck-generation step (this
skill's or another tool's) decides how to say it.

## What "universal" means here

There is no fixed vendor, product catalog, or industry baked into this skill. Every brief is built
from **adaptation dials** set from the actual engagement:

1. **Vendor / Offering Context** — what is being sold: the product, service, or capability catalog.
   Supplied by the user (a short capability list, a URL to research, or attached collateral) or
   carried over from a prior brief for the same vendor in this conversation. Never invented.
2. **Client Segment** — Startup / SME / Enterprise / Publicly Listed / Government / Non-profit — changes which
   sections matter (e.g. MEDDIC and procurement readiness for enterprise; budget-cycle and
   accountability framing for government) and the formality of tone.
3. **Sector Adaptation** — for non-consumer clients (industrial, government, B2B, regulated),
   "competitors" may mean narrative actors, comparator entities, or regulators rather than commercial
   rivals; "marketing strategy" may mean public affairs or stakeholder communication. Reinterpret
   field *meaning*, never drop the field.
4. **Meeting Stage** — Introduction / Demo / Follow-up / Proposal / Negotiation / Deck-Trigger — sets
   which parts of the brief get emphasis (see the stage-to-focus map in `system_prompt.md`).

One engine, every deal. The same two-layer machinery runs each time; only these four dials change
what fills it.

## Read order

Read all three references before producing a brief. They are layered:

- **`references/system_prompt.md`** — *how to execute.* The full engine: evidence hierarchy and
  citation system, source-quality rules, primary-problem classification, the Layer 1 / Layer 2
  output format, the JSON repository schema, and the internal quality gate. This is the operative
  document — follow it exactly.
- **`references/quality_framework.md`** — *what blocks vs guides vs stays silent.* The tiered A/B/C
  rulebook. Read it before finalizing, and use it to decide which issues are fatal and which are
  judgment calls.
- **`references/consistency_contract.md`** — *what must be identical across every brief.* The
  invariant layer the four dials are balanced against: the locked evidence-tagging system, the
  Layer 1 ↔ Layer 2 reconciliation rule, the JSON schema lock, and the length/format contract. Read
  it before writing so the brief stays comparable brief-to-brief and system-to-system.
- **`references/user_prompt_template.md`** — the fill-in template for collecting engagement inputs.
  Use it to check what's missing before generating, or hand it to the user directly if they haven't
  supplied enough context.

Read `system_prompt.md` first to run the engine end to end, hold `consistency_contract.md` as the
invariant layer while writing, and apply `quality_framework.md` as the gate before delivery.

## When to use

Use this skill when the user wants:

- a pre-sales / discovery / account intelligence brief before a client or prospect meeting
- a "meeting prep" or "BD cheat-sheet" document built from client notes plus research
- a structured research repository that a sales-deck generator, CRM, or proposal tool can consume
- a brief that separates what the client already said from what was found via independent research
- an account brief for an existing client (renewal, QBR, expansion) — same engine, different
  `meeting_stage`

Do **not** use this skill to write the persuasive sales narrative or slide deck itself — that is a
separate step (`sales_deck_mapping` in Layer 2 is the handoff point to whatever deck-generation tool
the user has, generic or otherwise). This skill prepares the thinking; it does not tell the story.

## Required inputs

Collect from the user or infer from attachments — check against `references/user_prompt_template.md`:

- **Vendor / offering context** — what is being sold (product name, capability catalog, or a URL to
  research). If the user has used this skill before in the conversation for the same vendor, this may
  carry over; otherwise ask rather than inventing a capability catalog.
- Client company name and industry (or enough to extract them from the context below)
- Client context — chat/email/call transcript, CRM notes, RFP, or "none — web research only"
- Meeting purpose and stage, meeting schedule (matters for urgency flags), contact name/title,
  lead source — optional but sharpen the brief when present
- Output language

If the vendor/offering context is missing entirely and cannot be inferred, ask for it before
generating — a brief that guesses the vendor's capabilities is not usable by a real sales team.

## Workflow summary

Follow `system_prompt.md` exactly. In order:

1. **Set the four dials** from the engagement (vendor context, client segment, sector adaptation,
   meeting stage).
2. **Read and tag Client Context** — extract everything the client has already stated, tagged `[C]`.
   Classify the **primary problem** from the client's own stated objective, not an assumed risk
   category.
3. **Run independent web research** — company profile, digital presence, recent activity, market
   position, competitors/comparator entities, industry issues — every specific fact tagged `[S]` with
   a source-registry entry. Research is not limited to what `[C]` already mentions.
4. **Reconcile `[C]` vs `[S]`** — where they conflict, write it as a confirmation note; never
   silently pick a side or drop one.
5. **Map pain → business impact → vendor outcome** for each pain point, using the vendor capability
   catalog from dial 1 — never a generic feature list.
6. **Write Layer 1 — Executive Brief** (Markdown, ≤2 pages / ~900 words outside tables).
7. **Write Layer 2 — Intelligence Repository** (one JSON object, full schema, every key present).
8. **Run the Internal Quality Gate** (see `system_prompt.md`) before returning the output.

## Non-negotiable rules

- Client-stated needs anchor the brief. Web research validates and extends them — it never overrides
  or replaces an explicit client statement.
- Every specific claim is tagged `[Cx]` (client-provided), `[Sx]` (public source), or `[Hx]`
  (hypothesis/inference — never presented as fact).
- Never invent the vendor's capabilities, pricing, or product names. If the vendor context is thin,
  say so and keep the fit mapping general rather than fabricating specifics.
- Layer 1 stays ≤2 pages; if it runs long, cut Layer 1 — never cut Layer 2. Layer 2 is the repository
  and is never truncated for length.
- Layer 1 and Layer 2 must never contradict each other; Layer 1 is a summary derived from Layer 2.
- No absolute claims ("guaranteed", "100%", "will definitely"). No manufactured urgency — cost-of-delay
  and "why now" must be evidence-based, not scarcity gimmicks.
- No personal contact details (private phone/email) surfaced from client context — reduce to
  role/title.
- Sensitive or material claims (financial, legal, safety, regulatory, named-competitor) need a
  credible, dated source; single-source or blog/UGC sources are labeled as such.
- Every pain point follows **Problem → Evidence → Business Implication → Offering Action** — never a
  generic pain point that could describe any client in the category unchanged.
- Layer 2 is always valid, parseable JSON with every schema key present (use `null`, `[]`, or `""` —
  never delete a key), so downstream tools never break on a missing field.

## Quality priority framework (A / B / C)

Full definitions live in `references/quality_framework.md`; read it before finalizing. In brief:

**A — Hard guardrails (mandatory; block delivery).**
- Evidence tagging discipline (`[C]`/`[S]`/`[H]`, no untagged specific claims)
- No invented vendor capability, pricing, or client fact
- Layer 1 length cap (≤2 pages) without cutting Layer 2
- Layer 1 ↔ Layer 2 consistency
- Valid, complete Layer 2 JSON (all schema keys present)
- Source quality for sensitive/material claims
- Client-stated needs never silently overridden by inference

**B — Thinking lenses (flexible; guide reasoning, don't gate).**
- Primary-problem classification from stated objective, not assumed risk category
- Sector adaptation of field meaning (competitors, marketing strategy, etc.)
- Meeting-stage emphasis (which Layer 1 blocks get the most weight)
- Opening/demo variant selection (provocative vs. empathetic) based on context sensitivity

**C — Lightweight QA (internal only; never in the output).**
- Citation consistency pass (every `[Cx]`/`[Sx]` resolves to a real registry entry)
- Anti-generic scan on every pain point and recommendation
- Personal-data scrub
- JSON schema completeness check

## Expected output

- Layer 1 — Executive Brief (Markdown, ≤2 pages)
- a `---` separator
- Layer 2 — Intelligence Repository (one JSON object, full schema)
- Optionally, if the user wants a saved artifact: `ExecBrief_[Client]_[Date].md` and
  `IntelRepo_[Client]_[Date].json`, following the file-creation guidance for the current
  environment.
