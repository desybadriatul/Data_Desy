# COGAN QUICK START — Raw Client Context to Client Intelligence Brief

Use this short version when the user pastes chat/WhatsApp/email/call notes and wants a client brief quickly.

```
Tolong ubah input berikut menjadi Client Intelligence Brief / Presales Brief.

Vendor/offering context:
[isi kalau ada. Kalau kosong, gunakan default Cogan/Dataxet Sonar media intelligence context]

Client/prospect context:
[paste chat, WA, email, meeting note, RFP, CRM/SCS handover, atau cerita singkat user]

Output language:
[Indonesia / English / other]

Research mode:
[client_context_only / client_context_plus_web_research]
```

After the brief is generated, ask the user whether they want DOCX/Google Docs, PDF, Markdown+JSON, or chat-only output. Do not generate files before confirmation.

---

# USER PROMPT TEMPLATE — Copy / Paste

Use this to collect engagement inputs before generating a brief. Delete lines that don't apply — the
engine treats a missing optional field as "not provided", not as a reason to invent one.

```
Please build an Intelligence Brief (Layer 1: Executive Brief + Layer 2: Intelligence Repository)
for the following prospect/account:

-- Vendor / Offering Context (required — do not skip): --
**What we're selling:** [product/service name + short capability list, OR a URL to research,
OR "same as the brief earlier in this conversation for [vendor]"]

**Company Name:** [FILL — or "extract from Client Context below" if already available]
**Industry:** [FILL — or "extract from Client Context"]
**Sub-Industry:** [FILL or delete this line]

-- Optional information, fill if available: --
**Company Size:** [Startup/SME/Enterprise/Publicly Listed/Government/Non-profit — or delete]
**Meeting Purpose & Stage:** [Introduction/Demo/Follow-up/Proposal/Negotiation/Deck-Trigger — or delete]
**Contact Name & Title:** [FILL — or delete]
**Lead Source:** [Referral/Cold Outreach/Event/Inbound/Other — or delete]
**Meeting Schedule:** [date & time — important so Next Action Plan knows if it's <72h away, or delete]
**Additional Notes:** [any other context the sales/BD team already knows — or delete]

-- Client Context (handover notes / chat-email-webchat transcript / CRM notes), paste text or
attach file: --
[paste here, or write "None — use web research only"]

**Instructions for using Client Context:** [optional — e.g. "prioritize the pain point about X,
don't focus on capability Y unless there's an actual need signal" — or delete]

**Output Language:** [language]

Please: extract [C] from the Client Context above, run independent and thorough web research for
[S] on [COMPANY NAME] (profile, recent news, competitors/comparator entities, market data, and —
if a vendor URL was given — check it for current offering details), then produce Layer 1
(Markdown, max 2 pages) followed by Layer 2 (one JSON object per the System Prompt schema). If [C]
and [S] conflict, write it as a confirmation note — don't drop either side. Run the Internal
Quality Gate before answering.
```
