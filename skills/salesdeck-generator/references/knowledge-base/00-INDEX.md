# Knowledge Base — Approved Sonar Reference Material

This folder is the skill's source of truth for everything Sonar-specific. The
System Prompt forbids inventing capabilities, pricing, scope, SLAs, and
competitor metrics — these files are how you avoid that. Pull facts from here
instead of from memory. All files are converted from internal Dataxet:Sonar
reference documents (REF-01…REF-09).

## Mandatory consultation rules

- **Before stating any product capability, output, data field, or limitation**
  → read `product-capability.md` and frame the claim within what that document
  supports. Honour every "Do not claim" line. If a capability isn't covered
  there, label it `PROPOSED` or `NEEDS_VALIDATION` — never assert it.
- **Before showing any price, tier, add-on, or contract term** → read
  `pricing.md`. Use the exact figures, never alter them, and only surface
  pricing when `include_pricing: true`. The minimum contract is 6 months.
- **Before any differentiation / "why Sonar over X" content** → read
  `competitors.md`. Use the approved positioning. Never fabricate a
  competitor's numbers; the doc itself notes where Sonar is weaker.
- **For every client-facing line (headlines, body, CTA)** → apply
  `tone-and-writing.md`: headline-as-answer, strong verbs, no empty jargon,
  diction library, before/after standard.
- **When specifying a visual (`visual_spec` / `render_payload`) or proposing a
  dashboard demo** → check `widget-guideline.md` for what each widget actually
  shows, its metrics, and applicable channels, so the visual is real and
  faithful.
- **When sequencing slides for a given problem** → consult
  `deck-blueprint-20-problems.md` and `deck-structure-guidance.md` for proven
  flows, then adapt to the specific client and classified problem type. Never
  ship a generic template unchanged.
- **For storytelling craft and worked examples** → the `example-*.md` files are
  real decks. Learn the patterns (cover formula, case-study framing,
  before/after, credentials). Do not copy their content verbatim into a client
  deck.

## File index

| File | Source | Use it for |
|---|---|---|
| `product-capability.md` | REF-04 | Capability honesty: 43 features with capabilities, KPIs, outputs, data coverage, **limitations and "do not claim"**. The most important file. |
| `pricing.md` | REF-05 | Subscription tiers (Basic/Corporate/Enterprise/White Label), add-on rates, 6-month minimum. |
| `competitors.md` | REF-07 | Local (NoLimit, Ivosights/Ripple10, Kazee, Drone Emprit, MediaWave) and global (Brandwatch, Talkwalker, Meltwater, Sprinklr) positioning + SWOT. |
| `tone-and-writing.md` | REF-09 | Voice, behaviour, headline formula, diction library, per-slide writing patterns, QA checklist. |
| `widget-guideline.md` | REF-08 | DXT360 dashboard widgets: definition, metrics, visualizations, applicable channels, business use. |
| `deck-blueprint-20-problems.md` | REF-06 | Problem→deck-structure blueprint for ~20 common client problems. |
| `deck-structure-guidance.md` | REF-01 | General deck structures and slide-by-slide prompt patterns. |
| `example-deck-structure.md` | REF-01 | Example deck (structure reference). |
| `example-storytelling.md`, `example-credentials-deck.md`, `example-storytelling-3.md` | REF-02 | Storytelling examples incl. the Dataxet credentials deck (company intro, coverage, clients, case studies). |
| `example-problem-based-1/2/3.md` | REF-03 | Problem-based deck examples to learn narrative flow. |

## Durable Sonar facts worth remembering

These recur across the references and are safe, approved anchors:

- Dataxet is a media-intelligence group across Asia (Thailand: Infoquest;
  Indonesia: Sonar; Malaysia/Singapore: Nama/Truescope). Sonar (PT Sonar
  Analitika Indonesia) is the Indonesia platform. Over 1000+ clients in APAC;
  50+ active clients across 10+ industries in Indonesia.
- Indonesia coverage highlights: 2M+ conversations/day; 10K+ IG influencers
  tracked; 2K+ TikTok influencers; 5K+ Facebook pages. Channels span X,
  Facebook, Instagram, YouTube, TikTok, online media, blogs, forums,
  marketplace/e-commerce, and traditional (print/TV/radio).
- Core stack: DXT360 Platform (Analytics, TrendWatch/Viral Meter, Social Media
  Management), plus Insight Reports and EVO consultancy (Experience, Values,
  Offers).
- Real client references that appear in approved material: Telkomsel, Frisian
  Flag, Anteraja, OVO, AirAsia Indonesia (testimonials). Use only as approved.
