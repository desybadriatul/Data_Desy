# Daily Social Quality Patch v2 — Claude Test Prompts

## 1. Cek tool baru

```text
Cek apakah Cogan MCP punya tool build_daily_social_report_data_preview dan build_daily_social_report_ppt_package.
```

## 2. Buat report input

```text
Buat Daily Social report input untuk project BlueBird tanggal 2026-06-10 dengan taxonomy bluebird_daily_social_test_v1.
Jangan buat PPT dulu.
```

## 3. Preview data Task 1 sebelum PPT

```text
Panggil build_daily_social_report_data_preview untuk report_input_id terakhir.
Tampilkan markdown preview ke saya. Fokuskan pada:
- KPI summary
- sentiment/channel table
- top topics
- top authors
- qualitative evidence dengan URL
- topic coverage caveat
- apakah aman dibuat PPT atau perlu enrichment dulu
Jangan buat PPT dulu.
```

## 4. Build package v2

```text
Panggil build_daily_social_report_ppt_package untuk report_input_id terakhir.
Tampilkan render_package_version, slide_count, slide_id + title, dan apakah ada slide optional Deep Dive / Appendix.
Jangan buat PPT dulu.
```

## 5. Buat PPTX

```text
Buat PPTX dari slides array package v2.
Wajib:
- Tampilkan source_url/top_post_url di Top Content, Action Plan evidence, Critical Issue Deep Dive, dan Appendix.
- Action Plan tetap slide 3.
- Jika topic coverage rendah, labeli sebagai early classified topic signal.
- Jangan mengarang quote, metric, URL, atau topic.
- Interactions dan Views harus dipisah.
```
