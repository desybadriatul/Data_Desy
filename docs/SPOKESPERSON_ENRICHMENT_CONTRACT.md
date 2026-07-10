# Spokesperson Enrichment Contract

## 1. Purpose

Spokesperson enrichment is a shared reporting enrichment layer for detecting **named people who speak, are quoted, or are attributed as making a statement** in media articles.

This contract is intended for:

- Spokesperson Intelligence Report / SFIR
- Mainstream Media Report / MMR
- Competitive Analysis when spokesperson/media comparison is needed

This enrichment is **not** intended for standard social media posts.

---

## 2. Definition

A spokesperson is:

> A named person who speaks, is quoted, or is attributed as making a statement in an article.

Valid examples:

- `CEO Danone Indonesia Laurent Boissier mengatakan bahwa ...`
- `Menurut Abdul Gofur, Ketua SP Antara, ...`
- `Pungkas Bahjuri Ali menjelaskan bahwa ...`
- `"...," ujar Laurent Boissier.`

Invalid examples:

- `Danone Indonesia hadir dalam acara ...`
- `Aqua menjadi sorotan publik ...`
- `Asosiasi Logistik menilai ...`
- `Pihak perusahaan menyatakan ...`
- `Netizen mengatakan ...`
- `Media menyebut ...`

A company, institution, association, media outlet, or anonymous public group is **not** a spokesperson unless a named person is present.

---

## 3. Eligible Scope

Eligible channels:

- Online Media
- Print
- Print Media
- Printmedia

Not applicable:

- Instagram
- TikTok
- Twitter / X
- Facebook
- YouTube
- Forum
- Other social/community channels

For non-media channels, the status should be `not_applicable` or the record should be excluded from spokesperson enrichment candidate selection.

---

## 4. Campaign Scope

Spokesperson enrichment must use **Campaigns** as the source of truth.

It must not rely on keyword matching in title/content as the primary scope mechanism.

If the report scope is:

```text
Aqua vs Le Minerale vs Cleo
```

then candidate articles must come from:

```text
Campaigns contains Aqua
OR Campaigns contains Le Minerale
OR Campaigns contains Cleo
```

If one article has multiple campaigns:

```text
Campaigns = Aqua, Le Minerale
```

the article is relevant to both campaigns, but LLM extraction should run only once for that canonical article.

---

## 5. Sampling Policy

Eligible articles are deduplicated by canonical post ID / content hash.

Sampling rule:

| Eligible article count | Enrichment sample size |
|---:|---:|
| `<= 50` | Enrich all |
| `> 50` | Enrich 10% |
| Minimum | 50 articles |
| Maximum | 100 articles per run |

Examples:

| Eligible articles | Selected for enrichment |
|---:|---:|
| 40 | 40 |
| 273 | 50 |
| 800 | 80 |
| 2,600 | 100 |

For multi-campaign reports:

- Quota is balanced across campaigns first.
- If one campaign has fewer eligible articles, leftover quota is reassigned to other campaigns.
- The same canonical article must not be sent to the LLM more than once.

---

## 6. Candidate Priority

Candidates are selected using this priority order:

1. Ad Value descending
2. PR Value descending
3. Readership descending
4. Quote signal score descending
5. Newest article date
6. Canonical post ID ascending

`Readership` is optional. If it is empty, candidate selection must still work using Ad Value, PR Value, quote signal, and date.

---

## 7. Attribution Signals

Attribution signals are used only for candidate scoring and context trimming. They are **not** final truth.

Final extraction must be decided by the LLM using the rule:

> Extract only named people who are quoted or attributed as making a statement.

Attribution signals:

```python
SPOKESPERSON_ATTRIBUTION_SIGNALS = [
    "mengatakan",
    "menyampaikan",
    "menjelaskan",
    "menyatakan",
    "menuturkan",
    "menegaskan",
    "menyebut",
    "menyebutkan",
    "mengungkapkan",
    "menerangkan",
    "memaparkan",
    "berpendapat",
    "menilai",
    "mengonfirmasi",
    "mengkonfirmasi",
    "membantah",
    "menyanggah",
    "mengakui",
    "menambahkan",
    "mengimbau",
    "mendesak",
    "mengusulkan",
    "menyarankan",
    "kata",
    "ujar",
    "ucap",
    "tutur",
    "ungkap",
    "papar",
    "jelas",
    "tegas",
    "tandas",
    "pungkas",
    "imbuh",
    "lanjut",
    "tambah",
    "terang",
    "sebut",
    "sanggah",
    "bantah",
    "menurut",
    "dalam keterangannya",
    "dalam keterangan resminya",
    "dalam sambutannya",
]
```

---

## 8. LLM Input Context

Do not send full long articles if avoidable.

Each candidate should send a trimmed spokesperson context containing:

- title
- lead paragraph
- sentence windows around attribution signals
- sentence windows around raw Sonar spokesperson if available

Recommended max context length:

```text
1,800 characters per article
```

This keeps token usage controlled while preserving attribution evidence.

---

## 9. Raw Sonar Spokesperson

The raw Sonar field must be preserved as:

```text
spokesperson_raw
```

It must not be treated as final truth.

Raw Sonar values may be:

- correct
- incomplete
- role/name merged
- multiple entities merged
- organization-only
- noisy

LLM normalization should produce final structured fields.

---

## 10. Output Contract

The enrichment output must return a list of spokespersons per article.

Article-level output:

```json
{
  "canonical_post_id": 123,
  "content_hash": "optional-content-hash",
  "status": "relevant",
  "source": "llm_enriched",
  "confidence": "high",
  "spokespersons": []
}
```

Allowed `status` values:

- `relevant`
- `not_relevant`
- `review_needed`

Allowed `source` values:

- `llm_enriched`
- `llm_checked`
- `sonar_raw_normalized`
- `llm_corrected_sonar`

Spokesperson-level output:

```json
{
  "spokesperson_name": "Laurent Boissier",
  "spokesperson_role": "CEO",
  "organization": "Danone Indonesia",
  "spokesperson_type": "company_representative",
  "represented_campaign": "Aqua",
  "evidence_sentence": "CEO Danone Indonesia Laurent Boissier mengatakan bahwa ...",
  "confidence": "high"
}
```

The final output must split:

- `spokesperson_name`
- `spokesperson_role`
- `organization`

Do not store final spokesperson as one combined string.

---

## 11. Extraction Rules

LLM must extract:

- named people who are quoted
- named people attributed as making a statement
- multiple named speakers if one article contains multiple spokespersons

LLM must not extract:

- company-only entities
- association-only entities
- institution-only entities
- media outlet names
- journalist narration
- anonymous public / netizens
- people who are mentioned but not speaking

If only an organization is speaking and no named person is present:

```json
{
  "canonical_post_id": 123,
  "status": "review_needed",
  "source": "llm_checked",
  "confidence": "low",
  "spokespersons": [],
  "reason": "There is an attributed organization statement, but no named person is present."
}
```

If no spokesperson exists:

```json
{
  "canonical_post_id": 123,
  "status": "not_relevant",
  "source": "llm_checked",
  "confidence": "high",
  "spokespersons": []
}
```

---

## 12. Current Implementation

Current implementation provides:

- field passthrough in `_normalise_post`
- candidate builder in `reporting/enrichment/spokesperson_enrichment.py`
- campaign-aware selection
- Online Media / Print filtering
- 10% sample rule, min 50, max 100
- Ad Value priority
- quote-window context trimming

Not yet implemented:

- LLM extraction call
- enrichment result cache
- workflow status `NEEDS_AUTO_SPOKESPERSON_ENRICHMENT`
- integration into SFIR/MMR renderers
