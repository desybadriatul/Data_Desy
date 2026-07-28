# 03 · Slide Library

The reusable layouts in `build_deck.js`. Mix and match per report. Each is already
wired to the theme, so they recolor automatically per client. The Le Minerale deck in
`examples/` shows all of them in action.

| # | Layout | When to use | Key elements |
|---|---|---|---|
| 1 | **Cover** | Opening | Light bg + soft brand circles, eyebrow, big serif headline, subhead question, 3 stat cards, both logos |
| 2 | **5-card grid** | Listing options/segments (e.g. the 5 narratives) | 5 narrow cards, icon chip + "?" overlay, kicker |
| 3 | **3-card "cost of silence"** | 3 risks/forces in play | 3 cards, accent icon on the most urgent, kicker |
| 4 | **Stat stack + chart** | Proof with data | 3 stacked stat callouts (left) + native bar chart (right) + source line |
| 5 | **Formula** | Explaining a composite metric | 3 component cards joined by `+`, navy result bar with `=` |
| 6 | **Deliverables + diagram placeholder** | Product/solution | 3 deliverable rows (left) + dashboard illustration placeholder w/ GPT prompt (right) |
| 7 | **Social-proof grid** | "real examples, not simulation" | 3 cards each with a SCREENSHOT placeholder + caption |
| 8 | **3-column comparison** | Us vs alternatives | 3 cards, the "winner" column filled navy/highlighted |
| 9 | **3-card reassurance** | De-risking the ask | 3 cards (keep / learn / commitment), kicker |
| 10 | **Phase timeline** | Next steps | 3 phase cards joined by `→`, a "why now" callout, contact line |
| 11 | **Source table** | References | Branded table, zebra rows, navy header, links + slide map |

## Reusable components (functions in `build_deck.js`)

- `header(slide, eyebrow, color)` — logos in corners + colored eyebrow label.
- `footer(slide, n)` — confidentiality line + page `n / total`.
- `title(slide, txt)` / `subtitle(slide, txt, y)` — house title/subtitle rhythm.
- `iconChip(slide, x, y, iconData, size, bg)` — white icon in a rounded brand square.
- `kicker(slide, txt, y)` — navy takeaway bar.
- `placeholder(slide, x, y, w, h, label, promptText?)` — dashed placeholder box.
  Pass `promptText` to make it a **diagram-illustration** placeholder that prints a
  GPT Image prompt inside; omit it for a plain **screenshot/photo** placeholder.

## Adding a slide

Copy the closest block in `build_deck.js`, change the `items`/`stats`/`rows` array and
the title. Keep the y-coordinates and card sizes so it aligns with the rest. Always run
the visual QA loop (render to images, inspect) before shipping.

## QA checklist (every deck)

- Titles never collide with the subtitle (long titles wrap to 2 lines — keep subtitle at y≈2.5").
- Kicker bar clears the footer (≥0.3" gap).
- No text overflow inside any card.
- Logos present, undistorted, correct corners.
- `extract-text deck.pptx | grep "—"` returns nothing (em-dash house rule).
