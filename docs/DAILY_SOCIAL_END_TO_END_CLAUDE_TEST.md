# Claude End-to-End Test — Daily Social Report

Target: Claude bisa menjalankan Cogan MCP dari prepare data sampai PPTX.

## Prompt testing di Claude

Gunakan prompt ini setelah branch terdeploy ke Railway/MCP:

```text
Gunakan Cogan MCP untuk membuat Daily Social Media Report untuk project BlueBird periode 2026-06-29 sampai 2026-06-29.

Ikuti Action-Plan-First structure:
1. Header / Identitas Report
2. Executive Summary
3. Daily Action Plan
4. Thematic Topics
5. Sentiment Analysis
6. Top Performing Authors
7. Top Performing Content
8. Key Findings
9. Footer / Disclaimer

Langkah kerja wajib:
1. Panggil get_insight_report_skill.
2. Panggil prepare_report_input dengan:
   - report_type_id: daily_social_media_report
   - project_name: BlueBird
   - start_date: 2026-06-29
   - end_date: 2026-06-29
   - confirmed_intent_id: approved_daily_social_bluebird_20260629
   - client_brand: BlueBird
   - analysis_objective: Daily Social Media Report Action-Plan-First
   - persist: true
3. Panggil build_prepared_report_outline menggunakan report_input_id dari step 2.
4. Panggil build_daily_social_report_ppt_package menggunakan report_input_id dari step 2.
5. Buat file PPTX berdasarkan slides array dari tool step 4.

Aturan:
- Jangan mengarang metrik, quote, URL, topic, atau evidence.
- Jika Thematic Topics masih N/A karena taxonomy belum tersedia, render sebagai limitation slide, jangan dihapus.
- Action Plan wajib langsung setelah Executive Summary.
- Interactions dan views harus dipisah.
- Raw Topic Extraction tidak boleh dipakai sebagai report topic.
```

## Prompt opsional sebelum report final: topic enrichment

Agar Thematic Topics tidak N/A, jalankan dulu di Claude:

```text
Buat taxonomy report-topic untuk project BlueBird periode 2026-06-29.

Langkah:
1. Panggil get_topic_taxonomy_sample(project_name="BlueBird", start_date="2026-06-29", end_date="2026-06-29", sample_size=80).
2. Dari sample Title + Content, buat taxonomy JSON dengan taxonomy_version "bluebird_daily_social_topic_v1".
3. Wajib ada topic_id "other_emerging_topic" dan "not_relevant".
4. Panggil save_topic_taxonomy(project_name="BlueBird", taxonomy_json=<JSON>, activate=true).
5. Panggil get_unclassified_topic_batch(project_name="BlueBird", taxonomy_version="bluebird_daily_social_topic_v1", start_date="2026-06-29", end_date="2026-06-29", batch_size=50).
6. Klasifikasikan semua post pada batch ke taxonomy dan simpan dengan save_topic_batch_results.
7. Ulangi batch sampai status complete atau sampai tidak ada unclassified post.
```
