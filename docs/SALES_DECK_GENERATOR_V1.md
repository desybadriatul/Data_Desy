# Sales Deck Generator V1

Scope: add a standalone Cogan Jalur 0B skill for sales deck, pitch deck, proposal deck, commercial deck, and PPTX proposal requests.

This patch installs `skills/salesdeck-generator/` and registers `get_sales_deck_guide()` in `server.py`.

## Routing

- Client brief / presales brief / intelligence brief / meeting prep only → `get_intelligence_brief_guide()`.
- Sales deck / pitch deck / proposal deck / deck jualan / commercial deck / PPTX proposal → `get_sales_deck_guide()`.
- Fixed reports named explicitly → existing Jalur 1 report workflows.
- Open-ended data diagnosis → existing Jalur 2.

## Default output

Default sales deck output is `CONTENT_DRAFT` unless the user explicitly requests PPTX/final production or approved content already exists. PPTX production must not run when content gate is `BLOCKED`.

## Non-goals

This patch does not modify report renderers, anomaly tools, onboarding, or existing fixed report workflows.
