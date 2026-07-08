# Cogan LLM Topic Enrichment — Operating Workflow

## Prinsip

`Topic Extraction` dari raw Sonar tidak dipakai sebagai **report topic**. Nilainya seperti `Person`, `Activity`, `Location`, atau `Color` hanya dipertahankan sebagai metadata source.

Report topic dibuat oleh Claude dari `Title + Content`, lalu disimpan ke cache Cogan.

## Siapa yang mengerjakan apa

| Komponen | Tugas |
|---|---|
| Cogan | Mengambil canonical post, memilih post belum terklasifikasi, menyimpan taxonomy dan assignment |
| Claude yang terhubung ke Cogan MCP | Membuat taxonomy awal dan mengklasifikasikan satu batch post |
| Daily builder | Membaca hasil cache saja; tidak memanggil LLM dan tidak memakai quota Claude |

## Pertama kali sebuah project membutuhkan report topic

1. Jalankan `get_topic_taxonomy_sample(project_name, ...)`.
2. Claude membaca `taxonomy_instruction` dan `sample_posts`.
3. Claude menghasilkan JSON taxonomy sesuai `required_taxonomy_shape`.
4. Simpan dengan `save_topic_taxonomy(project_name, taxonomy_json, activate=true)`.
5. Jalankan `get_unclassified_topic_batch(...)`.
6. Claude mengembalikan satu result untuk setiap post batch.
7. Simpan hasilnya dengan `save_topic_batch_results(batch_id, results_json)`.
8. Ulangi batch hingga `get_topic_enrichment_status(...).unclassified = 0`.

Taxonomy dibuat per project dan berversi, misalnya:

```text
bluebird_social_topic_v1
aqua_social_topic_v1
imip_social_topic_v1
```

Jika topic taxonomy berubah secara material, buat versi baru (`_v2`). Jangan menimpa versi lama.

## Saat user lain membuat report pada project/data yang sama

Cogan mencari cache berdasarkan:

```text
campaign/project
+ canonical_key
+ content_hash
+ taxonomy_version
```

- Post yang sudah `classified` atau `not_relevant` tidak dikirim lagi ke Claude.
- Post yang sedang ada pada batch `issued` user lain juga tidak dikirim ulang; user kedua akan mendapat post pending lain.
- Batch `issued` yang tidak selesai selama enam jam otomatis `expired`, sehingga post bisa diambil lagi.
- Bila content berubah, `content_hash` berubah dan post diklasifikasikan ulang.
- Bila taxonomy diganti ke v2, post perlu diklasifikasikan untuk v2.

## Daily Social Media Report

Setelah topic enrichment scope Daily selesai atau cukup sesuai caveat:

```text
prepare_report_input(
  report_type_id="daily_social_media_report",
  ...
)
```

Daily builder melakukan:

```text
canonical social posts
→ cached LLM report topic
→ qt_dsm_* aggregates
→ ql_dsm_* evidence
→ validation
→ report_input_id
```

Daily builder mengecualikan Online Media dan tidak memakai raw `Topic Extraction` sebagai topik.

## LLM batch rule

- Maksimum 100 post per batch; default 50.
- Satu post mendapat satu `primary_topic_id`.
- Claude hanya boleh memilih `primary_topic_id` yang tersedia dalam taxonomy.
- `not_relevant` untuk post di luar scope.
- `review_needed` harus memakai `other_emerging_topic` + `emerging_topic_detail`.
- Hasil batch harus lengkap; Cogan menolak result dengan ID hilang, ID asing, topic baru, atau duplicate post.

## Tidak memakai API pada MVP

Python Cogan tidak memanggil API Claude. Claude yang sedang terhubung melalui MCP memakai quota Claude-nya sendiri untuk membaca dan menyimpan batch.

Untuk backfill yang sangat besar, proses dilakukan bertahap dan hasil disimpan. Daily report berikutnya hanya memproses post baru/pending, bukan seluruh data historis lagi.
