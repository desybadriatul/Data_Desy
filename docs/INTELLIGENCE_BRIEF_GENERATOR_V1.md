# Intelligence Brief Generator V1

Scope: install Jalur 0 for Client / Intelligence Brief generation.

This patch adds:

- `skills/intelligence-brief-generator/`
- `get_intelligence_brief_guide()` in `server.py`
- `scripts/test_intelligence_brief_routing_v1.py`

Use for client brief / presales brief / account brief / meeting prep / BD cheat-sheet / intelligence brief / intellifence brief / brief from chat, WhatsApp/WA, email, CRM/SCS, RFP.

Rules:

- This is Jalur 0, not report workflow.
- Do not call report workflows for client brief requests.
- Do not scan Cogan data unless user explicitly asks for validation.
- Generate the brief in chat first.
- Ask for file format confirmation before creating PDF/DOCX/Markdown+JSON.

This patch does not implement sales deck, onboarding, or report generation.
