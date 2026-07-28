# EVO Visual Guidance — flexible rendering under a locked structure

> This reference is a **visual guidance layer**, not a visual lock. The structure, metrics, labels, evidence
> status, and required information are locked by `evo_report_structure.md`, `evo_metric_dictionary.md`, and
> the frozen data contract. The renderer is free to choose the most effective layout for the client template,
> audience, content density, and narrative flow.

## 1. Governing principle

**Structure locks what must be communicated. Visual design decides how it is communicated.**

The renderer may use a table, band scale, cards, matrix, chart, or another suitable composition as long as:

- every required structural field is present;
- metric values and semantic labels remain unchanged;
- confidence, limitation, evidence status, and hypothesis status remain visible where structurally required;
- the client template remains the source of truth for theme, typography, palette, master elements, and page geometry;
- no visual device implies a conclusion that is not supported by the frozen output.

This reference must not require one fixed layout, one fixed component arrangement, or one mandatory visual
recipe across all clients.

## 2. What is locked vs. flexible

| Layer | Status | Meaning |
|---|---|---|
| Metric formula and value | **Locked** | Never recalculated or changed during rendering |
| Band threshold and canonical label | **Locked** | `<90 Underperform`, `90–110 On Par`, `>110 Outperform` |
| Required component fields | **Locked** | Defined in `evo_report_structure.md` |
| Confidence / evidence / hypothesis status | **Locked** | Must remain explicit when required by structure |
| Storyline role and component objective | **Locked** | The slide or slide sequence must answer the intended question |
| Slide layout | **Flexible** | Table, cards, scale, chart, or hybrid |
| Object position and hierarchy | **Flexible** | Adapt to template and content density |
| Colour treatment | **Flexible** | Use client-template colours; labels must preserve meaning |
| Number of slides used for one component | **Flexible** | Split when needed for readability; do not drop required content |
| Visual emphasis | **Flexible** | Highlight the most decision-relevant result for the audience |

## 3. Score-band guidance

The score-band semantics are defined in `evo_metric_dictionary.md` and must not change:

| Code | Label | Range |
|---|---|---:|
| `underperform` | Underperform / Di bawah kategori | `<90` |
| `on_par` | On Par / Setara kategori | `90–110` |
| `outperform` | Outperform / Di atas kategori | `>110` |

The B5 structure requires the three band labels and thresholds to be available to the reader. Their visual
form is flexible. Valid examples include:

- a compact text legend;
- a horizontal band scale with a score marker;
- three labelled chips;
- a side note beside the EVOScore;
- a table footnote;
- a clearly connected opening slide when B5 spans multiple slides.

The renderer is **not** required to use a hero card, a fixed left-to-right arrangement, fixed colours, or a
specific active-band marker. It only needs to preserve the structural meaning and make the active result
understandable.

## 4. B5 Focus-Brand Scorecard — adaptable visual options

The structural content is defined in `evo_report_structure.md`. Possible visual treatments include:

### Option A — score table + compact band guide
Best when the audience needs detailed driver comparison.

### Option B — EVOScore scale + three driver cards
Best when the main decision is the composite posture and the driver tension.

### Option C — heatmap / matrix + interpretation panel
Best when Sentiment Index and Virality Index divergence is the main story.

### Option D — two-slide sequence
Best when the score table is dense:

1. composite EVOScore and band reading;
2. driver decomposition and diagnostic posture.

These are examples, not registered mandatory recipes.

## 5. General visual principles

- One slide should answer one primary strategic question.
- Split overloaded content rather than shrinking text until it is unreadable.
- Use labels, values, and annotations so colour is never the only carrier of meaning.
- Keep confidence and evidence status visible, but let the renderer choose placement and treatment.
- Preserve the semantic distinction between internal evidence, benchmark learning, external analogy, target,
  and hypothesis.
- Use the client template consistently; do not create a parallel EVO theme.
- Different components may use different layouts when that improves the storyline.

## 6. Renderer freedom

The renderer may:

- choose different layouts for different clients;
- adapt the same component to executive, strategist, or analyst audiences;
- combine or split slides while preserving all required structural outputs;
- use a new visual treatment not listed in this reference;
- omit decorative elements that do not improve comprehension.

The renderer may not:

- drop a structurally required field;
- change a threshold, label, confidence status, or evidence status;
- turn a directional result into a definitive visual claim;
- present an External Analogy as internal proof;
- imply business impact as measured when it is only a hypothesis or target.

## 7. QA principle

Visual QA checks readability, overflow, overlap, hierarchy, and faithful translation of the frozen structure.
It does **not** fail a deck merely because the layout differs from another EVO deck or because a preferred
visual example was not used.
