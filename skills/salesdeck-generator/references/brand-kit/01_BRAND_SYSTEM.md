# 01 · House Design System

The rules that make every Dataxet:Sonar deck feel like one studio made it. These are
client-agnostic; only the palette and logos change per client.

## Logos

- **Agency mark (Dataxet:Sonar)** sits top-left on every slide.
- **Client logo** sits top-right on every slide.
- Both are embedded from transparent PNGs and auto-trimmed so framing is tight.
- Agency wordmark target width ≈ 1.7"; client mark target height ≈ 0.66" (engine
  computes the other dimension to preserve aspect ratio — never stretch a logo).
- On dark/photo backgrounds, place a logo on a small white rounded plate if it would
  otherwise lose contrast. (The current decks use light backgrounds, so logos sit bare.)

## Typography

| Element | Font | Size | Weight |
|---|---|---|---|
| Slide title | Cambria (serif) | 23–24pt | Bold |
| Cover headline | Cambria | 40–42pt | Bold |
| Eyebrow / section label | Calibri | 12.5pt, +3 letter-spacing | Bold, UPPERCASE |
| Card heading | Calibri | 13–15pt | Bold |
| Body / caption | Calibri | 10.5–13.5pt | Regular |
| Footer | Calibri | 8.5–9pt | Regular, muted |

Serif headers (Cambria) + sans body (Calibri) gives contrast while staying on the
Office "safe-list" so the deck renders identically on any machine. Never use Aptos.

## Color usage (60 / 30 / 10)

- **60–70% dominant**: the client's deep brand color (navy/green) for titles, dark
  cards, kicker bars + a very light tint of it as the slide background.
- **30% secondary**: the client's mid brand color for accents, chart bars, eyebrows.
- **10% sharp accent**: the client's signal color (red for Le Minerale) for one thing
  per slide — a key stat, a warning, an arrow. Never spread the accent around.
- Dataxet:Sonar green/periwinkle is reserved for the agency mark only.

## Visual motif (repeat on every slide)

- **Rounded cards** (rectRadius ≈ 0.1") with a 1px brand-line border + a soft shadow.
- **Icon chips**: a white icon inside a small rounded brand-color square, top-left of each card.
- **Number ovals** for ordered steps; **arrows** (→) in the accent color between phases.
- **Kicker bar**: a navy rounded bar at the bottom carrying the one-line takeaway.

## Layout grid (16:9 wide = 13.33" × 7.5")

- Margins: 0.7" left/right; content starts ~1.4" (title), ~2.5" (body after a 2-line title).
- Card gaps: 0.27" (3-up), 0.16" (5-up). Pick one rhythm per slide, keep it.
- Bottom kicker around y≈5.95"; footer at y≈7.0". Keep ≥0.3" between blocks.

## Hard NOs (these read as "AI-generated")

- No accent underline beneath titles.
- No full-width header/footer color stripes; no thin edge-stripes on cards.
- No cream/beige default backgrounds — use the client's light tint or white.
- No centered body text; left-align paragraphs.
- No text-only slides — every slide carries a card, chart, icon, or placeholder.

## Copy rules

- **Reduce em-dashes (—).** House style replaces them with commas, colons, or periods.
  A sentence that leans on an em-dash can almost always be split or re-punctuated.
- One-line takeaway in the kicker bar per slide.
- Indonesian for client-facing copy; keep product terms (SoV, engagement quality) as-is.
- Every data claim must be traceable to the Sumber & Referensi slide.
