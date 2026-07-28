---
name: cogan-legacy-methodology
status: deprecated
deprecated_since: "3.1"
replacement:
  - "SKILL.md"
  - "references/consistency_contract.md"
  - "references/stage_data_cogan.md"
  - "references/skill_report.md"
  - "references/system_prompt.md"
  - "references/perpustakaan_resep_slide.md"
  - "references/quality_framework.md"
---

# DEPRECATED — DO NOT USE AS ACTIVE METHODOLOGY

File ini dipertahankan hanya untuk kompatibilitas struktur folder lama.

Jangan gunakan file ini untuk:

- definisi metric;
- aturan canonical post atau dedup;
- scope brand / issue-only;
- coverage dan denominator;
- penggunaan tool Cogan;
- storytelling;
- visual;
- recommendation;
- quality gate;
- workflow report.

Semua aturan aktif telah dipindahkan ke paket Cogan Insight Report Engine versi 3.1.

## Sumber aturan aktif

| Kebutuhan | Gunakan file |
|---|---|
| Router, urutan file, dan authority map | `../SKILL.md` |
| Metric, scope, coverage, denominator, rekonsiliasi | `consistency_contract.md` |
| Tool Cogan, evidence collection, dan data freeze | `stage_data_cogan.md` |
| Storyline, headline, bahasa klien, dan rekomendasi | `skill_report.md` |
| Orchestration dari brief sampai deliverable | `system_prompt.md` |
| Pilihan visual dan slide recipe | `perpustakaan_resep_slide.md` |
| Hard stop dan QA final | `quality_framework.md` |
| Mapping kebutuhan ke file/tool | `../skill_mapping.yaml` |

## Aturan migrasi

Jika menemukan instruksi lama yang merujuk `methodology.md`:

1. Jangan baca file ini sebagai sumber aturan.
2. Gunakan `SKILL.md` untuk melihat file yang berwenang.
3. Gunakan `skill_mapping.yaml` untuk memetakan kebutuhan report ke file/tool.
4. Terapkan aturan dari file aktif sesuai domainnya.

## Status runtime

```text
load_by_default: false
active_authority: none
```

Server Cogan versi 3.0 tidak memuat file ini sebagai bagian dari `get_insight_report_skill()`.

