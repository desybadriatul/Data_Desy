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

### C.1b · DETEKSI PROBLEM (khusus Pintu B — user tak tahu problemnya; Stage 0.2)
Kalau user minta report tapi tak menyebut problem (mis. "buatin weekly/monthly, aku belum lihat
datanya"), **deteksi dulu** problem/anomali di periode itu, lalu tawarkan **top 5 paling krusial**:
- **Ranking krusial = engagement + jumlah post.** Sesuatu penting kalau ramai (banyak post) ATAU
  berdampak (engagement tinggi). Ambil 5 teratas.
- **Sumber deteksi (tool yang ada):** `detect_spikes`/`timeline` (lonjakan = "ada apa-apa"),
  `count_posts` (kluster sentimen negatif), `get_posts` (baca konten → kelompokkan tema; jangan wordcloud).
- **Saring noise:** hanya tawarkan yang benar-benar signifikan (di atas ambang) — jangan lempar 15 item.
- **Kembalikan ke user** (bahasa manusia): "Aku scan datamu: ada 5 hal menonjol — (1)…(2)…(3)…(4)…(5)…
  [tiap butir: 1 kalimat + jumlah post + engagement]. Mau fokus yang mana? Boleh satu, beberapa, atau
  semua kujadikan satu report." Tunggu pilihan sebelum lanjut. "Semua jadi satu" → tiap problem jadi satu
  bagian dalam satu report.

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
- **Tren & lonjakan (WAJIB dua garis)** → `timeline` ambil **volume (post) DAN engagement per hari**
  (bukan cuma volume). `detect_spikes(metric="engagement")` untuk puncak engagement. Untuk tiap
  puncak, `get_posts` di tanggal itu (urut engagement) → ambil **post pemicu + `url`** biar puncak
  engagement kebukti ("meledak karena post ini → ini linknya"), bukan cuma "ada lonjakan".
- **Perbandingan** → `compare_campaigns` (brand vs kompetitor), `compare_periods` (vs periode lalu).
- **Aktor** → `top_authors`. **Konten viral** → `top_viral_posts`. **Media isu** → `top_media`.
- **KUTIPAN asli + BUKTI** → `get_posts` (urut engagement, ~80–150 post). Untuk tiap kutipan yang
  dipakai di slide, simpan juga: **`url` (link post) + author/handle + tanggal + metrik**. Link WAJIB
  ikut ke slide bukti (bisa diklik/diverifikasi). Kalau `raw` punya field gambar/thumbnail, simpan untuk
  di-embed. Baca konten aslinya — **jangan** simpulkan isu dari frekuensi kata / wordcloud.
- **BARIS MENTAH banyak** (mis. minta 1000) → `export_raw_data` jadi CSV, lalu olah pakai kode (pandas).
  "Minta 1000" = untuk diproses kode / diserahkan ke klien, bukan dibaca mentah satu-satu.
- **CAKUPAN KOMPETITOR (wajib).** Untuk cerita competitive, tarik metrik headline (SOV, net sentiment,
  %negatif) untuk **SEMUA** kompetitor yang disebut user — bukan hanya yang didalami — supaya scorecard
  bisa tampilkan seluruh medan sekali. Pendalaman boleh fokus 1–2 rival; sisanya tetap di tabel + satu
  kalimat alasan kenapa tak didalami.
- **RADAR ISU + TOPIK KECIL (wajib, untuk slide `radar_isu`).** Jangan berhenti di isu terbesar.
  (a) `get_posts(...)` lintas periode → **kelompokkan konten jadi beberapa tema secara manual** (baca isi,
  bukan wordcloud) → untuk tiap tema hitung **jumlah post + total engagement + %pos/%neg** (angka pasti,
  untuk ditampilkan per isu) → ambil **Top 3–6**. Simpan juga `url` tiap kutipan (link wajib di slide). (b) **Sisir topik kecil/niche
  yang relevan** (komunitas, mis. padel/HYROX, isu kemasan) walau volumenya kecil → angkat sebagai sinyal
  (tandai `directional`). (c) Bila user minta niche spesifik ("brand × padel") → `get_posts` + filter kata
  ATAU `export_raw_data` lalu olah pandas. Silang-cek tema yang melonjak dengan `detect_spikes`/`timeline`.

### C.3 · Bekukan → `deck_data.json`
Tulis semua metrik terpakai + kutipan asli ke `deck_data.json`, termasuk `contract_version` dan
`theme_version`. Stage D–F membaca **hanya** file beku ini + brief Stage E + `theme.json`. Jangan hitung
ulang / mengarang angka saat render.

### C.5 · Gerbang rekonsiliasi — **JALANKAN PAKAI KODE, bukan nalar** (Poin 2)
Jangan cek angka pakai "kira-kira benar" di kepala. **Jalankan kode kecil (bash/python)** yang
BENAR-BENAR menghitung ulang di atas `deck_data.json` yang sudah dibekukan, SEBELUM menulis slide apa pun.
Kalkulator yang pasti, bukan perkiraan. Yang wajib dihitung ulang oleh kode:

1. **Sum-of-parts = total.** Untuk tiap breakdown (channel, sentimen, topik, SOV), jumlahkan bagian-bagian
   dari data → bandingkan dengan total tertulis. Selisih di luar toleransi (±1 baris / ±0,1 pp) → GAGAL.
2. **Tiap angka slide ADA di data.** Kumpulkan semua angka yang akan tampil di headline/KPI/reframe/
   implikasi/keputusan → cek satu per satu apakah nilainya ada verbatim di `deck_data.json`. Angka yang
   "lahir" saat render (tak ada di data) → GAGAL.
3. **Satu label = satu definisi**, **net sentiment berlabel basis**, **n<30 → directional**.

Pola kode (sesuaikan):
```python
import json
d = json.load(open("deck_data.json"))
errs = []
for name, b in d.get("breakdowns", {}).items():          # cek 1: jumlah = total
    s = round(sum(b["parts"].values()), 1)
    if abs(s - b["total"]) > max(1, 0.1):
        errs.append(f"{name}: parts={s} != total={b['total']}")
allowed = set(map(str, d.get("all_numbers", [])))          # cek 2: tiap angka slide ada di data
for n in d.get("slide_numbers", []):
    if str(n) not in allowed:
        errs.append(f"angka slide '{n}' tidak ada di data beku")
assert not errs, "REKONSILIASI GAGAL:\n" + "\n".join(errs)  # HALT kalau ada
print("REKONSILIASI PASS")
```
**HALT bila kode melaporkan gagal** — perbaiki angka/query dulu, jalankan lagi sampai `PASS`, baru tulis
slide. Tulis hasilnya (`reconciliation.overall_status`) ke `deck_data.json`. Ini mengubah C.5 dari
"aku cek manual" jadi "mesin hitung, kalau tak cocok berhenti" — angka salah tak bisa lolos karena lengah.

---

## YANG TIDAK BERUBAH

Stage A (diagnosis), B (storyline + lensa), D (insight + reframe + rekomendasi milik klien), E (brief per
slide → lihat `perpustakaan_resep_slide.md`), F (render PPTX) **semua tetap** seperti `system_prompt.md`
Desy. File ini hanya mengganti *dari mana* data Stage C diambil: dari Cogan, bukan file upload.

**Tidak dipakai untuk report:** `prepare_wordcloud_context`, `get_wordcloud_candidates`,
`get_wordcloud_selection_guide`, `get_project_wordcloud_guidance`, `render_selected_wordcloud`.

---
*Stage Data (Cogan edition) · v1.0 · mengganti sumber data Stage C ke Cogan; sisa mesin Desy utuh.*
