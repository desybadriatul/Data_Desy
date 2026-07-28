# USER PROMPT TEMPLATE

```text
Generate onboarding output artifacts for this client.

Output language: [language]

Offering type: [Media/Social Monitoring | SaaS/Software Implementation | Professional
Services/Consulting | Media Buying/Ad Campaign | Data/Analytics Engagement | Other — describe]

---

Client and project context:
[Client name, industry, region, monitoring/operating language, objective, pain points, expected
outcome]

Sales / pitch / proposal / SOW / contract notes:
[Fill in if available. If not: "Not provided"]

Intelligence Brief (if generated earlier with intelligence-brief-generator):
[Paste Layer 2 JSON, or "Not available"]

Sales/account / email / chat / MoM notes:
[Fill in if available. If not: "Not provided"]

Onboarding and account setup information:
[PIC, admin, user, report recipients, package, contract, timezone, channels, limits, etc. If none:
"Not provided"]

Scope / configuration input (manual, optional):
For each scope item, fill in the following:

- Scope Item Name:
- Scope Item Type:
- Objective:
- Target Region:
- Target Language:
- Target Delivery Channels:
- Main Configuration Terms/Components:
- Context/Supporting Terms:
- Exclusions:
- Official Accounts / Handles / Identifiers:
- Notes:

Important:
- Manual scope/configuration input is optional. If the scope-item list is incomplete or not given,
  extract it yourself from the Contract/SOW, Alignment Record, Onboarding/Handover record, MoM,
  Sales Deck, Intelligence Brief, and other scope documents.
- Build the Scope Source Registry before finalizing the scope-item list.
- Every own-brand, parent-company/ticker, product/service, competitor/comparator, campaign/
  workstream, issue, or event with an onboarding/configuration need must be classified.
- Every competitor/comparator needing monitoring, comparison, or benchmarking must become its own
  scope item with the offering-appropriate `Competitor` type.
- Optional/deferred/pending/needs-validation items must still be built as draft scope items with
  matching status — never dropped.
- Only items explicitly `Excluded`/`Not Required` may lack configuration.
- Do not demote a scope item into a sub-component of another scope item.
- If a delivery channel's own convention requires multiple configuration variants for coverage,
  generate all required variants.
- Do not merge multiple delivery channels into a single row.
- Configuration components must be traceable to delivery-channel setup via Scope Item Name +
  Channel + Component Type.

References:
[Short labels. Example:
REF-01 Sales deck format
REF-02 Configuration setup example
REF-03 Handover example
REF-04 Product/service capability reference
If none: "Not provided"]

Internal notes:
[Notes from CX/Ops/Insight/Product/Data teams. If none: "Not provided"]

Special instructions:
[Any additional constraints. If none: "Not provided"]

Expected artifact outputs:
- 01_Project_Brief.md
- 02_Configuration_Package_Readable.md
- 02_Configuration_Package_CSV/scope_summary.csv
- 02_Configuration_Package_CSV/research_intelligence.csv
- 02_Configuration_Package_CSV/configuration_components.csv
- 02_Configuration_Package_CSV/delivery_channel_setup.csv
- 02_Configuration_Package_CSV/coverage_matrix.csv
- 02_Configuration_Package_CSV/exclusion_edge_cases.csv
- 02_Configuration_Package_CSV/validation_checklist.csv
- 02_Configuration_Package_CSV/ops_setup_notes.csv
- 02_Configuration_Package_CSV/missing_info.csv
- 02_Configuration_Package_CSV/glossary.csv
- 03_Final_Onboarding_Handover.md
- 04_Onboarding_Kickoff_Summary.pptx
- 05_Client_Welcome_Summary.md
```
