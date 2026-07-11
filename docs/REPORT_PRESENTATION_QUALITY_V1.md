# Report Presentation Quality V1

Scope:
- Competitive Analysis renderer
- Mainstream Media Report renderer
- Shared evidence link helper

Changes:
1. Preserves Action-Plan-First blueprint order.
2. Removes client-facing Evidence ID/raw URL presentation from main slide payloads.
3. Keeps source URLs behind natural hyperlink labels: `Buka artikel`, `Lihat post`, `Lihat komentar`.
4. Improves MMR story readout inside existing sections: what happened, why it matters, issue response, spokesperson role, media contributor framing.
5. Keeps audit IDs and raw URLs in internal metadata/export paths, not as visible slide text.

Important rule:
- Do not change raw/source schema.
- Do not invent new mandatory fields.
- Extra slides are allowed only when attached to the nearest parent section in the registry structure.
