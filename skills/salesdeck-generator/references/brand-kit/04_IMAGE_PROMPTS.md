# 04 · Image & Placeholder Prompts

When a slide needs a real image, leave a **placeholder** rather than a fake. Two kinds:

1. **Screenshot / photo placeholder** — for a real social post or photo. Just a labeled
   box; the team pastes the real asset. No prompt needed.
2. **Diagram / illustration placeholder** — for something we generate. The box carries a
   **GPT Image prompt** so anyone can produce an on-brand image in one paste.

## Rules for every GPT Image prompt

Always include, in this order:

1. **What** to draw (subject + key elements).
2. **Brand consistency** — name the client's hex tokens explicitly and say "palette WAJIB
   konsisten brand". Pull hex from `02_CLIENT_PALETTES.md`.
3. **Style** — flat UI, rounded cards, clean sans typography, "selaras desain slide".
4. **Aspect ratio** — must match the placeholder box on the slide (state it, e.g. "Rasio 2:1").
5. **Guards** — "resolusi tinggi, tanpa teks acak, tanpa logo asli".

> Match the ratio to the box. A 2:1 box → "Rasio 2:1 (landscape)". A 4:5 box → "Rasio 4:5
> (portrait)". A 1:1 box → "Rasio 1:1 (square)". Mismatched ratios get cropped or letterboxed.

## Template — product dashboard (ratio 2:1), Le Minerale

> PROMPT → GPT Image: Mockup dashboard SaaS modern platform media-intelligence
> 'dataxet:sonar': panel 'Narrative Effectiveness Ranking' berisi 5 narasi dengan bar
> chart, gauge sentimen, dan panel share-of-voice kompetitor. Palet WAJIB konsisten
> brand: navy #0E2A6B, biru azure #2E86C8, putih, aksen merah #E1251B seperlunya. Gaya
> flat UI, kartu rounded, tipografi sans bersih, selaras desain slide. Rasio 2:1
> (landscape), resolusi tinggi, tanpa teks acak, tanpa logo asli.

## Template — abstract section illustration (ratio 16:9)

> PROMPT → GPT Image: Ilustrasi abstrak modern bertema [TOPIK], gaya flat geometric
> dengan bentuk gelombang/lingkaran halus. Palet WAJIB konsisten brand klien: [DEEP] ,
> [MID] , putih, aksen [ACCENT] seperlunya. Bersih, banyak ruang kosong, selaras desain
> slide. Rasio 16:9 (landscape), resolusi tinggi, tanpa teks, tanpa logo asli.

## Template — data/process diagram (ratio 4:3)

> PROMPT → GPT Image: Diagram alur [PROSES] dengan 3–4 langkah berlabel ikon sederhana
> dan panah penghubung. Palet WAJIB konsisten brand klien: [DEEP] dominan, [MID] aksen,
> putih latar. Gaya flat, garis tipis, kartu rounded, tipografi sans bersih. Rasio 4:3,
> resolusi tinggi, label singkat dan jelas, tanpa logo asli.

## Swapping per client

Replace the bracketed tokens with the client's hex from `02_CLIENT_PALETTES.md`:

- **GoPay** → DEEP `#052B4E`, MID `#00AAE4`, ACCENT `#00AA13` (Gojek green).
- **Kementan** → DEEP `#0F4F28`, MID `#2E8B4E`, ACCENT `#F2B807` (gold).

Keep the structure identical so generated images always sit consistently inside the deck.
