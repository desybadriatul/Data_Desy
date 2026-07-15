# Dataxet:Sonar — Brand Kit & Master Deck Template

A reusable system for turning Dataxet:Sonar client reports and sales decks into
professional, on-brand presentations. Drop in a client's logo + palette, keep the
same house style, and every deck comes out consistent.

## What's inside

```
Dataxet_Sonar_Brand_Kit/
├── README.md                  ← you are here
├── 01_BRAND_SYSTEM.md         ← house design system (type, motif, layout, do/don't)
├── 02_CLIENT_PALETTES.md      ← color tokens per client (Le Minerale, GoPay, Kementan)
├── 03_SLIDE_LIBRARY.md        ← catalog of reusable slide layouts
├── 04_IMAGE_PROMPTS.md        ← GPT Image prompt templates for diagram/illustration placeholders
├── assets/
│   └── logos/                 ← brand logos (dataxet-sonar.png, le-minerale.png, + add clients)
├── template/
│   ├── theme.js               ← THE brand kit in code: palette + logo per client
│   ├── build_deck.js          ← the deck engine (components + example Le Minerale content)
│   └── package.json           ← dependencies
└── examples/
    └── Sonar_x_LeMinerale_Sales_Deck_BRANDED.pptx   ← finished reference deck
```

## Quick start

```bash
cd template
npm install                      # pptxgenjs, react-icons, react, react-dom, sharp
node build_deck.js leminerale    # -> Deck_leminerale.pptx
```

Swap the client by passing its key: `node build_deck.js gopay` / `node build_deck.js kementan`
(add the official client logo + verify the palette first — see `02_CLIENT_PALETTES.md`).

## How to make a NEW client deck

1. **Add the logo** — put the official PNG (transparent bg) in `assets/logos/<client>.png`.
2. **Add/confirm the palette** — add a block under `clients` in `template/theme.js`
   (copy the Le Minerale block, swap hex). Lock exact hex from the client's brand guideline.
3. **Write the content** — copy `build_deck.js` to a new file and replace the slide
   text/data with the new report's content. Layout components stay the same.
4. **Build & QA** — render to images and eyeball every slide before sending.

## The two-layer idea

- **theme.js = brand kit.** Colors + logos, one block per client. The *client* palette
  dominates the deck; Dataxet:Sonar appears as the agency mark (top-left) + accent.
- **build_deck.js = house style.** Cover, card grids, stat callouts, formula, comparison,
  timeline, source table, and placeholders. These never change between clients — that's
  what makes the decks feel like one studio made them.

## Notes

- Logos are embedded from local PNGs (transparent, auto-trimmed for tight framing).
- Real social posts and product screenshots are left as labeled **placeholders**.
- Diagram/illustration placeholders contain a ready **GPT Image prompt** (see `04_IMAGE_PROMPTS.md`)
  that already specifies brand-color consistency and the correct aspect ratio.
- Copy avoids em-dashes by house rule (see `01_BRAND_SYSTEM.md`).
