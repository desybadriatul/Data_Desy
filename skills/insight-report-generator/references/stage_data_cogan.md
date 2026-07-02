# STAGE DATA — VERSI COGAN
## Sambungan: bikin mesin Desy menarik & membuktikan data dari database live Cogan (bukan file Excel)

> **Kenapa file ini ada.** Mesin Desy (`system_prompt.md` Stage C) mengasumsikan data datang dari
> **file rawdata yang diupload**. Cogan kamu menyediakan data dari **database live lewat tool**. File
> ini mengganti *sumber* datanya saja — seluruh cara berpikir, struktur, narasi, dan gerbang mutu Desy
> **tetap dipakai apa adanya**. Ini bukan mesin baru; ini colokan Cogan untuk mesin Desy.
>
> **Posisi:** dipakai saat **Stage C** (dan C.5). Sisa Stage (A, B, D, E, F) jalan seperti di
> `system_prompt.md`. Cara berpikir top-down & disiplin data tetap dari `skill_report.md`
> (dilayani `get_report_guide()`). Metrik & rekonsiliasi tetap dari `consistency_contract.md`.

---

## PRINSIP (tetap Tama & Desy)

- **Top-down.** Tarik data hanya untuk beat cerita yang sudah ditentukan (Stage A/B). Jangan buka daftar
  tool lalu bikin slide per tool. Tool dipanggil karena sebuah beat butuh bukti — bukan sebaliknya.
- **Buktikan dulu, baru cerita.** Sebelum menarik metrik apa pun, jalankan `data_health` — ini bukti
  data tidak ngasal + sumber daftar keterbatasan.
- **Anti-ngarang (keras).** Angka report **hanya** dari tool Cogan. Kalau data tidak ada / tidak cukup
  untuk sebuah klaim → **berhenti**, sampaikan kekurangannya, jangan dipaksakan jadi slide.
- **Satu angka = satu arti.** Kunci angka sekali di data beku; jangan hitung ulang beda-beda.

---

## ALUR STAGE C — VERSI COGAN

### C.0 · Resolusi campaign
`find_project(project_name)` atau `list_campaigns()` untuk memastikan nama campaign benar sebelum apa pun.

### C.1 · BUKTIKAN DATA DULU  *(langkah wajib — ranah Tama)*
`data_health(project_name, start, end)` →
- `n_posts_unique`, `date_range_actual`, `channels_present`
- `coverage_percent`: `sentiment_classified`, `engagement_gt0`, `buzz_gt0`, `ad_value_gt0`

Hasilnya langsung jadi isi slide **scope_metodologi** dan daftar **keterbatasan jujur**. Aturan:
- coverage rendah → tulis apa adanya ("engagement hanya di X% post", "online media tak punya engagement").
- metrik dengan n < 30 atau coverage rendah → tandai **directional** (kata "indikatif", bukan klaim pasti).

**HALT bila:** campaign tidak ditemukan, atau coverage tidak cukup untuk klaim yang mau dibuat →
keluarkan Stage C saja, jelaskan gap-nya, jangan lanjut ke insight. (Sama seperti Stage C FAIL Desy.)

### C.2 · Tarik HANYA yang dibutuhkan beat (top-down)
Peta **Kamus Metrik Desy (Part 1) → tool Cogan** yang menghitungnya:

| Metrik terkunci (consistency_contract Part 1) | Tool Cogan | Field / cara |
|---|---|---|
| Count of Content (Posts) — dedup per URL | `count_posts` | jumlah post unik + split sentimen + channel |
| Buzz (fallback Count) | `metrics_summary` | buzz per campaign |
| Engagement | `metrics_summary` / `count_posts` | sum like+comment+share+view |
| Avg Engagement / Content | `compare_campaigns` | `avg_engagement_per_post` (atau Engagement ÷ Count) |
| Share of Voice (basis buzz) | `share_of_voice(metric="buzz")` | `share_pct` per campaign |
| Share of Engagement | `share_of_voice(metric="engagement")` | `share_pct` |
| Sentiment Share (% pos/neu/neg) | `count_posts` | dari split sentimen (null dikecualikan dari denominator) |
| Channel Share | `count_posts` | per channel |
| Net Sentiment — **by count** | `count_posts` | (%pos − %neg) |
| Net Sentiment — **engagement-weighted** | `metrics_summary` | pakai engagement per sentimen; **label basisnya** |
| Ad Value (online media) | `top_media` | `ad_value` per outlet (BUKAN engagement) |

Bukti pendukung cerita:
- **Tren & lonjakan** → `timeline`, `detect_spikes` (untuk "kenapa sekarang" / deteksi krisis).
- **Perbandingan** → `compare_campaigns` (brand vs kompetitor), `compare_periods` (vs periode lalu).
- **Aktor** → `top_authors`. **Konten viral** → `top_viral_posts`. **Media isu** → `top_media`.
- **KUTIPAN asli** → `get_posts` (urut engagement, ~80–150 post). Baca konten aslinya — **jangan**
  simpulkan isu dari frekuensi kata / wordcloud.
- **BARIS MENTAH banyak** (mis. minta 1000) → `export_raw_data` jadi CSV, lalu olah pakai kode (pandas).
  "Minta 1000" = untuk diproses kode / diserahkan ke klien, bukan dibaca mentah satu-satu.

### C.3 · Bekukan → `deck_data.json`
Tulis semua metrik terpakai + kutipan asli ke `deck_data.json`, termasuk `contract_version` dan
`theme_version`. Stage D–F membaca **hanya** file beku ini + brief Stage E + `theme.json`. Jangan hitung
ulang / mengarang angka saat render.

### C.5 · Gerbang rekonsiliasi (tetap punya Desy)
Jalankan gerbang `consistency_contract.md` Part 2 pada angka beku: sum-of-parts = total; tiap angka
headline/KPI/reframe/decision ada verbatim di `deck_data.json`; tiap label metrik = satu definisi; net
sentiment berlabel basis; n kecil ditandai directional. **HALT** kalau ada yang gagal & tak terselesaikan.

---

## YANG TIDAK BERUBAH

Stage A (diagnosis), B (storyline + lensa), D (insight + reframe + rekomendasi milik klien), E (brief per
slide → lihat `perpustakaan_resep_slide.md`), F (render PPTX) **semua tetap** seperti `system_prompt.md`
Desy. File ini hanya mengganti *dari mana* data Stage C diambil: dari Cogan, bukan file upload.

**Tidak dipakai untuk report:** `prepare_wordcloud_context`, `get_wordcloud_candidates`,
`get_wordcloud_selection_guide`, `get_project_wordcloud_guidance`, `render_selected_wordcloud`.

---
*Stage Data (Cogan edition) · v1.0 · mengganti sumber data Stage C ke Cogan; sisa mesin Desy utuh.*
