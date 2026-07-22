# EVO Metric Dictionary — the locked math

> Register these into the shared `consistency_contract.md` Metric Dictionary as new entries (same
> Definition / Formula / Grain / Rule format as existing metrics). None of the six current report types
> defines an attribute-level score, so these are pure additions — no collision to reconcile. `build_…ppt_package`
> consumes frozen values; it never improvises a formula at render time. Bump `contract_version` when this changes.

## 1. Metric table

| Metric | Definition | Formula / rule | Grain |
|---|---|---|---|
| **Driver Class** | Which driver a post belongs to | attribute → driver via registered map | post |
| **EVO Share** | Share of a brand's conversation carried by a driver | `driver_basis / brand_total_basis × 100` | brand × driver |
| **Driver Net Sentiment** | Sentiment balance of a driver | `%positive − %negative` (count-based) | brand × driver |
| **Sentiment Index** | Direction-preserving, category-centred tone | see §2 | brand × driver |
| **Virality / Engagement Index** | Amplification vs. category | `brand_avg_engagement / category_avg_engagement × 100` | brand × driver |
| **Total Driver Score** | Combined tone + amplification per driver | `mean(Sentiment Index, Virality Index)` | brand × driver |
| **EVOScore** | Brand's overall perception strength | `mean(Total Driver Score across E, V, O)` | brand |
| **Attribute Score** | Perception strength of one attribute | one approved formula, §3 | brand × attribute |
| **Attribute Contribution %** | Share of a driver's polarity pool held by an issue | `issue_basis / same-driver same-polarity total × 100` | driver × issue × polarity |
| **Best Brand** | Benchmark leader on an attribute | highest Attribute Score among **non-focus** brands | attribute |
| **Attribute Gap** | Distance to the leader | `Best-Brand score − focus score` | attribute |
| **Whitespace** | Owned by nobody / open to the focus brand | `best > 0 and focus = 0`, or attribute with material category demand and no clear owner | attribute |

**Basis lock.** Every metric declares its basis (posts / buzz / reach / engagement) and holds it constant
within a view. Mixing bases inside one comparison is a reconciliation failure.

## 2. Sentiment Index (the one that trips people up)

Convert net sentiment to a 0–100 point, then centre on the category:

```
p           = (net_sentiment + 100) / 2          # net_sentiment in [-100, +100] → p in [0, 100]
Sentiment Index = p_brand / p_category × 100      # >100 means better tone than the category average
```

A point-difference convention may substitute **only if declared once and held throughout.** Never mix the
two bases in one deck (they produce different numbers for the same pillar).

## 3. Attribute Score (distinct from Total Driver Score / EVOScore)

- **One** approved formula for the whole analysis; same basis throughout.
- Preserves direction (a negative-tone attribute cannot outscore a positive one on volume alone).
- The **same** Attribute Score feeds both Best Brand and Attribute Gap — you cannot rank by one score and
  compute the gap from another.
- Flags thin samples (`n < 30` directional, `n < 10` low-confidence).

## 4. Interpretation bands (category-centred, ×100 scale)

| Band | Canonical code | Reading |
|---|---|---|
| **< 90** | `underperform` | Underperforms the category |
| **90–110** | `on_par` | On par with the category |
| **> 110** | `outperform` | Outperforms the category |

**Semantic boundary lock.** Scores exactly equal to `90` or `110` are `on_par`. The workflow must not invent
a fourth band, use `overperform`, or rename `on_par` as `pair`. The canonical reading sequence is:
`Underperform → On Par → Outperform`. Visual placement and treatment remain flexible.

```yaml
evo_score_band_contract:
  scale: category_centred_x100
  category_centre: 100
  boundary_rule: inclusive_on_par

  bands:
    - code: underperform
      label_en: Underperform
      label_id: Di bawah kategori
      condition: score < 90
      range_display: "<90"

    - code: on_par
      label_en: On Par
      label_id: Setara kategori
      condition: 90 <= score <= 110
      range_display: "90–110"

    - code: outperform
      label_en: Outperform
      label_id: Di atas kategori
      condition: score > 110
      range_display: ">110"

  applies_to:
    - Sentiment Index
    - Virality / Engagement Index
    - Total Driver Score
    - EVOScore

  output_fields:
    - score_value
    - band_code
    - band_label
    - range_display

  scorecard_structure:
    include_band_reference: true
    band_order: [underperform, on_par, outperform]
    include_numeric_thresholds: true
    include_active_score_band: true
    visual_treatment: flexible
```

The score band and the diagnostic posture are **not the same output**:

- **Score band** reads one category-centred number: `underperform`, `on_par`, or `outperform`.
- **Posture** reads the relationship between Sentiment Index, Virality Index, sample adequacy, and direction.

A favourable-looking composite is **not** an automatic strength — amplification may be masking weak tone.
Read posture from the two components together:

| Posture | Condition |
|---|---|
| **Real Strength** | Both Sentiment Index and Virality Index outperform, adequate sample |
| **Fragile Strength** | Composite outperforms but tone is weak (volume is carrying it) |
| **Under-Built Territory** | Positive tone, thin volume — an owned meaning not yet amplified |
| **Active Vulnerability** | Negative tone with material volume |
| **Low-Confidence Signal** | Directional sample regardless of colour |
| **Whitespace** | Best > 0, focus = 0 |

## 5. Computation-source lock (the failure mode this pack exists to stop)

`Attribute Score`, `Attribute Contribution %`, `Best Brand`, `Attribute Gap`, and `Whitespace` are computed
**only** from row/post-level tagged content (the attribute chain). They are never inferred, estimated, or
backfilled from a driver-level aggregate (e.g. a pre-computed driver matrix). If only driver-level data
exists for a case:

- driver analysis (EVO Share, Driver Net Sentiment, Sentiment Index, Total Driver Score, EVOScore) may be produced;
- the attribute layer is declared **`unavailable`** in Integrity output;
- the system does **not** approximate attribute scores from driver shares.

This is the single rule that separates an EVO report from a re-skinned competitive-sentiment chart.

## 6. Reconciliation (inherits universal Gate C.5)

EVO passes the shared Stage C.5 reconciliation gate unchanged, plus two EVO-specific checks:
- **EVO Share sums.** For each brand, `Σ EVO Share across E, V, O` = 100 ± 0.1 (or footnote the residual /
  unmapped share).
- **Best-Brand exclusion.** The focus brand never appears in any Best-Brand cell. A focus brand in the
  Best-Brand pool is a hard fail.
