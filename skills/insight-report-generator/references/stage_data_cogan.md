---
name: cogan-data-execution
version: 3.2
description: >
  Panduan operasional untuk mengambil, memvalidasi, membekukan, dan melacak data
  report dari Cogan MCP. File ini menjelaskan urutan pemakaian tool, metric
  readiness, scope, evidence collection, dan data freeze. File ini tidak
  menentukan narasi, rekomendasi, desain, atau definisi metrik.
---

# COGAN DATA EXECUTION GUIDE

## 1. Otoritas file ini

File ini mengatur:

- urutan pemakaian tool Cogan MCP;
- cara memilih scope data;
- cara membedakan brand universe dan issue-only universe;
- cara menarik bukti konten;
- cara memeriksa coverage dan dedup;
- cara membekukan angka menjadi `deck_data.json`;
- cara melakukan validasi data sebelum narasi dibuat.

File ini **tidak boleh** mengatur:

- definisi resmi metrik dan rumus;
- headline;
- storyline;
- rekomendasi;
- jumlah slide;
- layout;
- kualitas bahasa client-facing;
- QA final desain.

Gunakan file lain untuk kebutuhan tersebut:

| Kebutuhan | File sumber |
|---|---|
| Definisi metrics, coverage threshold, dan metric admission | `consistency_contract.md` |
| Cerita, headline, narasi, dan rekomendasi | `skill_report.md` |
| Workflow end-to-end report | `system_prompt.md` |
| Visual/layout | `perpustakaan_resep_slide.md` |
| QA final report | `quality_framework.md` |

---

## 2. Prinsip kerja

Jangan mulai dari daftar tool.

Mulai dari:

1. Pertanyaan bisnis user.
2. Keputusan yang harus dibantu report.
3. Universe data yang diperlukan.
4. Bukti yang perlu dicari.
5. Tool MCP yang menjawab kebutuhan tersebut.

Prinsip utama:

> Data diambil untuk membuktikan atau menguji suatu pertanyaan, bukan untuk mengisi semua jenis chart yang tersedia.

Jangan:

- memanggil seluruh tool tanpa alasan;
- mengambil angka yang tidak akan dipakai;
- menentukan tema hanya dari wordcloud;
- menjadikan keyword match sebagai bukti final;
- mencampur scope berbeda dalam satu kesimpulan;
- menulis narasi sebelum data freeze selesai.

### 2.1 Prasyarat wajib sebelum tool analitis

Untuk request report/deck/narrative analysis, file ini hanya boleh digunakan
setelah user menyetujui `Intent Confirmation`.

Sebelum menarik aggregate metric atau memilih KPI:

```text
1. find_project()
2. validate_metric_readiness()
3. data_health()
```

Aturan status:

```text
PASS → lanjut ke evidence retrieval.
WARN → gunakan metric/channel siap pakai saja; catat caveat.
FAIL → jangan gunakan interactions sebagai KPI sampai masalah raw field,
       parser angka, atau channel mapping diperbaiki.
```

`validate_metric_readiness()` tidak menggantikan `data_health()`. Readiness
memeriksa sumber raw metric dan mapping; data health memeriksa canonical post,
dedup, periode aktual, serta coverage pada scope.

---

## 3. Standar scope Cogan

Setiap tool aggregate harus memakai scope yang eksplisit.

Format konseptual:

```json
{
  "universe": "brand | issue_only | activity_property | competitor_comparison",
  "start_date": "YYYY-MM-DD atau null",
  "end_date": "YYYY-MM-DD atau null",
  "channels": [],
  "keywords": [],
  "exclude_keywords": [],
  "match_mode": "any | all"
}
```

Tool Cogan akan mengembalikan object `scope` secara otomatis.

Jangan menulis ulang scope dari ingatan. Simpan scope yang dikembalikan tool ke data freeze.

### 3.1 Parameter scope

| Parameter | Fungsi | Aturan |
|---|---|---|
| `start_date` | Tanggal awal | Gunakan format `YYYY-MM-DD` |
| `end_date` | Tanggal akhir | Bersifat inklusif untuk seluruh hari |
| `channel` | Satu channel untuk tool tertentu | Gunakan hanya ketika memang perlu isolasi satu channel |
| `channels` | Beberapa channel | Pisahkan dengan koma bila tool mendukung |
| `keywords` | Filter teks awal | Bukan klasifikasi isu final |
| `exclude_keywords` | Mengeluarkan false positive/noise | Gunakan hanya setelah ada bukti false positive |
| `match_mode="any"` | Lolos jika memuat minimal satu keyword | Default untuk exploratory issue scope |
| `match_mode="all"` | Lolos jika memuat seluruh keyword | Gunakan hati-hati karena dapat terlalu menyempitkan scope |

### 3.2 Aturan keyword scope

Keyword scope hanya melakukan pencocokan pada title dan content.

Gunakan keyword scope untuk:

- membuat issue-only candidate universe;
- menyaring aktivitas tertentu;
- mengambil data topik awal;
- mempercepat pembacaan raw data.

Jangan gunakan keyword scope saja untuk:

- menyatakan seluruh post benar-benar membahas satu isu;
- menghitung tuduhan langsung tanpa membaca post;
- membuat tema final;
- menyimpulkan niat publik;
- menyimpulkan fakta hukum/regulator.

### 3.3 Membuat keyword scope isu

Susun keyword dari:

1. Nama isu yang disebut user.
2. Istilah teknis yang dipakai publik.
3. Sinonim, variasi ejaan, slang, dan kata terkait.
4. Nama tokoh, lokasi, produk, atau kejadian bila relevan.
5. Kata yang membedakan isu dari noise.

Contoh konseptual:

```text
Isu:
“Sumur bor vs mata air”

Candidate keywords:
sumur bor, akuifer, mata air, air tanah, sumber air

Candidate exclusion:
nama tempat/produk yang ternyata menimbulkan false positive
```

Lalu lakukan proses berikut:

```text
1. get_posts() dengan candidate keywords
2. baca hasil top post dan sampel lain
3. identifikasi false positive / missing term
4. revisi keywords / exclusions
5. ulangi data_health() dan count_posts()
6. bekukan scope yang sudah layak
```

---

## 4. Urutan wajib sebelum membuat report

## Step 0 — Confirm project and available data

Panggil:

```text
find_project(project_name)
```

Tujuan:

- memastikan campaign tersedia;
- melihat periode data yang tersedia;
- melihat channel yang tersedia;
- memastikan title/content ada untuk analisis isi.

Jangan mengasumsikan data tersedia hanya karena user menyebut nama client.

---

## Step 1 — Cek metric readiness dan data health pada brand universe

Panggil berurutan:

```text
validate_metric_readiness(
  project_name,
  start_date,
  end_date,
  channels=""
)

data_health(
  project_name,
  start_date,
  end_date,
  channels=""
)
```

Tujuan:

- memastikan raw fields dan channel mapping siap dipakai;
- mengetahui jumlah canonical unique posts;
- mengetahui raw rows dan duplicate yang dihapus;
- mengecek actual date range;
- mengecek sentiment coverage;
- mengecek interaction coverage;
- mengecek views coverage;
- mengecek channel yang tersedia.

Catat minimal:

```text
n_posts_unique
n_rows_raw
duplicate_rows_removed
actual date range
sentiment coverage
interaction coverage
views coverage
channel availability
```

Jangan memilih metric utama sebelum membaca hasil
`validate_metric_readiness()` dan `data_health()`.

---

## Step 2 — Tentukan scope analisis

Pilih salah satu atau beberapa lane berikut.

| Lane | Tujuan | Scope |
|---|---|---|
| Brand context | Memahami kondisi brand secara umum | Brand universe |
| Issue proof | Memahami satu isu spesifik | Issue-only universe |
| Activity evaluation | Menilai campaign/event/property | Activity/property universe |
| Competitor comparison | Membandingkan brand | Competitor comparison universe |
| Historical comparison | Membandingkan periode | Scope yang sama pada dua periode |

Satu report boleh memakai lebih dari satu lane, tetapi setiap angka harus mempertahankan label universe-nya.

Contoh crisis report:

```text
Brand context:
Seluruh percakapan AQUA

Issue proof:
AQUA + scope “sumur bor / akuifer / mata air”

Evidence:
Top post issue-only berdasarkan views dan interactions

Historical:
Issue-only periode current vs baseline
```

---

## Step 3 — Tarik aggregate yang benar

Gunakan tool sesuai pertanyaan.

| Pertanyaan | Tool |
|---|---|
| Berapa post unik dan sentiment by count? | `count_posts()` |
| Berapa interactions dan views per channel? | `metrics_summary()` |
| Kapan percakapan naik/turun? | `timeline()` |
| Kapan hari anomali/spike? | `detect_spikes()` |
| Konten mana yang paling tinggi views/interactions? | `top_viral_posts()` |
| Siapa akun penggerak? | `top_authors()` |
| Media mana paling banyak memberi eksposur? | `top_media()` |
| Apa isi post sebenarnya? | `get_posts()` |
| Bagaimana perubahan antar periode? | `compare_periods()` |
| Bagaimana posisi kompetitif? | `compare_campaigns()` / `share_of_voice()` |
| Butuh audit/coding lebih luas? | `export_raw_data()` |

Jangan memakai satu tool untuk semua pertanyaan.

---

## 5. Aturan penggunaan metric tool

## 5.1 `count_posts()`

Gunakan untuk:

- total canonical post;
- breakdown channel;
- sentiment by count;
- net sentiment by count;
- classification coverage.

Jangan gunakan untuk:

- views;
- interactions;
- weighted sentiment;
- top content;
- penilaian severity issue tanpa issue-only scope.

Contoh panggilan brand universe:

```text
count_posts(
  project_name="AQUA",
  start_date="2025-10-21",
  end_date="2025-10-31"
)
```

Contoh panggilan issue-only:

```text
count_posts(
  project_name="AQUA",
  start_date="2025-10-21",
  end_date="2025-10-31",
  keywords="sumur bor,akuifer,mata air,air tanah",
  match_mode="any"
)
```

Selalu simpan:

```text
scope
total_posts_unique
sentiment.classified_posts
sentiment.classification_coverage_pct
sentiment.by_sentiment
sentiment.net_sentiment_by_count
```

---

## 5.2 `metrics_summary()`

Gunakan untuk:

- interactions per channel;
- views per channel;
- coverage interactions;
- coverage views;
- likes/comments/shares/replies/retweets bila dibutuhkan;
- buzz/ad value/pr value sebagai contextual metrics.

Gunakan field:

```text
interactions
views
interaction_formula
interaction_coverage_pct
views_coverage_pct
```

Jangan gunakan `source_engagement` untuk report client-facing.

Jangan menyebut `interactions` sebagai `engagement` tanpa menjelaskan definisinya.

Contoh panggilan:

```text
metrics_summary(
  project_name="AQUA",
  start_date="2025-10-21",
  end_date="2025-10-31",
  keywords="sumur bor,akuifer,mata air,air tanah",
  match_mode="any"
)
```

Aturan baca output:

- `interactions` = aksi pengguna sesuai rumus platform.
- `views` = tayangan, terpisah.
- `ad_value` = nilai eksposur media online, bukan interaction.
- Online media tidak memiliki interaction formula.

---

## 5.3 `timeline()`

Gunakan untuk:

- melihat tren harian;
- melihat puncak post;
- melihat puncak interactions;
- melihat puncak views;
- menghubungkan perubahan dengan peristiwa atau konten.

Jangan hanya mengambil puncak angka.

Setelah menemukan puncak, wajib lanjut:

```text
get_posts(
  project_name,
  start_date="tanggal puncak",
  end_date="tanggal puncak",
  sort_by="interactions atau views"
)
```

Bandingkan tiga hal:

```text
peak posts
peak interactions
peak views
```

Ketiganya bisa terjadi pada hari berbeda dan berarti hal berbeda.

---

## 5.4 `detect_spikes()`

Gunakan ketika user belum tahu apa yang terjadi atau ingin memeriksa lonjakan.

Metric yang disarankan:

```text
posts
interactions
views
```

Jangan pakai `engagement`, meski server menerima alias lama tersebut.

Aturan:

- spike hanya menunjukkan hari yang tidak biasa;
- spike bukan penjelasan;
- spike bukan otomatis crisis;
- pemicu harus dibuktikan lewat pembacaan post.

---

## 5.5 `get_posts()`

Gunakan untuk membaca konten asli.

Gunakan setelah:

- menemukan spike;
- mendapat top post;
- menentukan candidate issue scope;
- ingin membuktikan narrative;
- memeriksa mismatch sentiment;
- perlu kutipan/evidence link;
- ingin mengecek false positive keyword.

Sort yang dianjurkan:

| Tujuan | `sort_by` |
|---|---|
| Konten dengan aksi pengguna tertinggi | `interactions` |
| Konten dengan tayangan tertinggi | `views` |
| Konten yang paling banyak dibagikan | `shares` |
| Perkembangan kronologis awal ke akhir | `date` |
| Konten terbaru | `date_desc` |

Jangan menggunakan sort default lama `engagement`.

### Minimum evidence reading

Untuk claim yang akan muncul di main deck:

1. Baca top 10 post berdasarkan interactions.
2. Baca top 10 post berdasarkan views, bila views relevan.
3. Baca post negatif tertinggi bila report membahas issue/reputasi.
4. Baca post pada seluruh tanggal spike utama.
5. Baca sample tambahan bila keyword scope terlihat noisy.

Jika total content kecil, baca seluruh post relevan.

Jika total content sangat besar, gunakan export raw data untuk coding/validasi yang lebih sistematis.

---

## 5.6 `top_viral_posts()`

Gunakan untuk memilih bukti konten individual.

Pilihan basis:

```text
interactions
views
shares
likes
comments
viral_score
```

Aturan:

- Gunakan `views` saat ingin membuktikan exposure.
- Gunakan `interactions` saat ingin membuktikan aksi pengguna.
- Gunakan `shares` saat ingin mengukur potensi penyebaran.
- Jangan menyebut satu post viral sebagai pola performa campaign.
- Selalu baca content/URL post sebelum memasukkannya ke deck.

Untuk crisis report, biasanya tarik dua daftar terpisah:

```text
top_viral_posts(... by="views")
top_viral_posts(... by="interactions")
```

---

## 5.7 `top_authors()`

Gunakan untuk:

- mencari akun/kreator/media sosial penggerak;
- membedakan satu akun outlier dari pola akun yang lebih luas;
- melihat apakah percakapan digerakkan akun besar, komunitas, atau banyak akun kecil.

Jangan menyimpulkan “aktor utama” hanya dari total interactions.

Periksa juga:

```text
posts
total_interactions
total_views
top_post
sentiment
channel
```

Satu author dengan satu post besar tidak sama dengan author yang konsisten menciptakan banyak post berpengaruh.

---

## 5.8 `top_media()`

Gunakan hanya untuk online media.

Output utama:

```text
articles
ad_value
pr_value
```

Jangan:

- menyebut ad value sebagai interactions;
- menyebut ad value sebagai media tier;
- menyebut outlet “paling berpengaruh” hanya dari ad value;
- menggabungkan ad value media dengan views/interactions sosial.

Gunakan `keyword` bila ingin mencari outlet yang membahas isu tertentu.

---

## 5.9 `compare_periods()`

Gunakan hanya bila current period dan baseline menggunakan:

- scope keyword yang sama;
- channel yang sama;
- lifecycle aktivitas yang sebanding;
- panjang periode yang comparable atau diberi caveat;
- definisi metric yang sama.

Bandingkan:

```text
posts
interactions
views
negative posts
negative share
sentiment coverage
interaction coverage
views coverage
```

Jangan membandingkan:

```text
pre-event vs post-event
periode 1 hari vs periode 1 bulan
issue-only current vs brand-level baseline
```

tanpa label dan alasan metodologis yang jelas.

---

## 5.10 `compare_campaigns()` dan `share_of_voice()`

Gunakan setelah memastikan:

1. Campaign yang dibandingkan benar-benar brand/property yang setara.
2. Periodenya sama.
3. Scope keyword sama.
4. Channel sama.
5. Lifecycle setara.
6. Coverage cukup.

Untuk `share_of_voice()`, pilih satu basis:

```text
posts
buzz
interactions
```

Jangan tulis `SOV` tanpa menulis basisnya.

Contoh yang benar:

> Share of Voice berdasarkan post.

Contoh yang salah:

> SOV AQUA 42%.

---

## 6. Workflow per jenis report

## 6.1 Crisis / Issue / PR

### Lane data minimum

```text
1. Brand universe health
2. Issue-only health
3. Issue-only post/sentiment count
4. Issue-only interactions/views by channel
5. Issue-only timeline and spike
6. Top issue posts by views
7. Top issue posts by interactions
8. Post reading / evidence validation
9. Top authors jika actor mapping dibutuhkan
10. Top media jika mainstream media relevan
```

### Urutan tool minimum

```text
find_project()

data_health()                      # brand universe
count_posts()                      # brand universe

get_posts(keywords=...)            # exploratory issue scope
data_health(keywords=...)          # issue-only health
count_posts(keywords=...)          # issue-only count/sentiment
metrics_summary(keywords=...)      # interactions/views
timeline(keywords=...)             # issue trend
detect_spikes(keywords=...)        # spike
top_viral_posts(by="views")        # exposure proof
top_viral_posts(by="interactions") # action proof
get_posts(...)                     # read all critical evidence
```

### Minimum outputs untuk data freeze

```text
brand universe total
issue-only total
issue share of brand total
issue-only sentiment by count
issue-only interactions and views
channel contribution
timeline peak(s)
top content by views
top content by interactions
evidence links
coverage for each scope
```

---

## 6.2 Competitive

### Lane data minimum

```text
1. Data health tiap brand
2. Comparable total post/interactions/views/buzz
3. SOV dengan basis eksplisit
4. Top posts tiap brand
5. Narasi/attribute reading
6. Lifecycle and outlier check
```

### Urutan tool minimum

```text
find_project() untuk setiap brand

data_health() untuk setiap brand
compare_campaigns()
share_of_voice(metric="posts" atau "buzz" atau "interactions")
top_viral_posts() untuk setiap brand
get_posts() untuk setiap brand
```

### Aturan tambahan

- Jangan menggunakan SOV sebagai satu-satunya bukti kekuatan kompetitif.
- Cek apakah performance satu brand ditopang satu post.
- Cek apakah channel mix sebanding.
- Cek apakah semua brand berada pada fase activity yang sama.
- Gunakan `compare_campaigns()` untuk angka utama dan `get_posts()` untuk penjelasan narasi.

---

## 6.3 Sponsorship / Campaign / Activation

### Lane data minimum

```text
1. Activity/property scope
2. Data health
3. Post/interactions/views
4. Timeline
5. Top posts
6. Top authors
7. Evidence of brand linkage
8. Comparison activity lain bila scope comparable
```

### Urutan tool minimum

```text
data_health(keywords=activity terms)
count_posts(keywords=activity terms)
metrics_summary(keywords=activity terms)
timeline(keywords=activity terms)
top_viral_posts(by="interactions")
top_viral_posts(by="views")
top_authors(keywords=activity terms)
get_posts(keywords=activity terms)
```

### Aturan tambahan

Jangan hanya melaporkan peak content.

Cek:

- apakah performa tersebar pada beberapa post;
- apakah aktivitas menghasilkan creator/community participation;
- apakah views tinggi tetapi interactions rendah;
- apakah interactions tinggi tetapi hanya dari satu akun;
- apakah content benar-benar menghubungkan brand dengan aktivitas.

---

## 6.4 Brand Health / Weekly / Monthly

### Lane data minimum

```text
1. Brand health
2. Overall count and sentiment
3. Interactions/views per channel
4. Daily timeline
5. Spikes
6. Top content
7. Targeted issue scopes bila muncul sinyal tertentu
```

### Urutan tool minimum

```text
data_health()
count_posts()
metrics_summary()
timeline()
detect_spikes(metric="posts")
detect_spikes(metric="interactions")
top_viral_posts(by="interactions")
top_viral_posts(by="views")
get_posts()
```

Kemudian hanya buat issue-only scope untuk topik yang memang relevan terhadap keputusan mingguan.

Jangan membuat semua topik kecil menjadi slide.

---

## 6.5 Segmentation / Research / Custom

Untuk report custom, buat data plan dulu.

Format internal:

| Pertanyaan bisnis | Data yang diperlukan | Scope | Tool | Output yang dibekukan |
|---|---|---|---|---|
| Apa yang ingin diketahui? | Bukti apa yang diperlukan? | Brand/issue/activity/competitor | Tool MCP | Angka/evidence final |

Contoh:

| Pertanyaan | Data | Tool |
|---|---|---|
| Apakah keluhan harga meningkat? | Issue-only price scope + timeline | `data_health`, `count_posts`, `timeline`, `get_posts` |
| Siapa akun penggerak isu? | Top author + top post scope isu | `top_authors`, `get_posts` |
| Apakah isu perlu respons publik? | Tuduhan langsung, sumber, tren, media | `count_posts`, `timeline`, `top_viral_posts`, `top_media`, `get_posts` |

Jangan memaksa report custom menjadi crisis, competitive, atau sponsorship.

---

## 7. Sentiment validation procedure

Sentiment dari Cogan harus diperlakukan sebagai structured signal, bukan kebenaran otomatis.

### 7.1 Kapan harus diperiksa manual

Wajib lakukan content reading bila:

- sentiment menjadi headline;
- top content memiliki views/interactions tinggi;
- issue bersifat reputasional, legal, keselamatan, atau regulator;
- ada gap antara angka sentiment dan kesan dari top post;
- volume negatif rendah tetapi top exposure sangat negatif;
- wording post ambigu/sarkastik;
- sentiment coverage tidak penuh.

### 7.2 Prosedur minimum

```text
1. Tarik top post berdasarkan interactions.
2. Tarik top post berdasarkan views.
3. Tarik post negatif tertinggi bila issue-related.
4. Baca title/content/link.
5. Tandai mismatch:
   - label sentiment salah;
   - post tidak relevan terhadap issue;
   - post duplicate narasi;
   - post tidak mengandung claim yang diasumsikan.
6. Catat dampak mismatch terhadap aggregate sentiment.
7. Jika mismatch material:
   - turunkan sentimen menjadi directional;
   - jangan jadikan headline;
   - atau lakukan coding ulang bila data memungkinkan.
```

### 7.3 Mismatch material

Anggap mismatch material bila:

- satu atau lebih top content yang sangat berpengaruh salah label;
- mismatch mengubah interpretasi arah percakapan;
- post exposure tertinggi bertentangan dengan sentiment aggregate;
- issue besar ternyata mayoritas berada di post yang tidak valid scope.

---

## 8. Evidence collection procedure

Setiap insight yang masuk main deck harus memiliki bukti yang bisa ditelusuri.

### 8.1 Evidence minimum

Untuk tiap finding penting, simpan:

```text
finding_id
scope
metric / evidence type
numerator
denominator jika ada
date range
source tool
source post URL atau source media
interpretation note
limitations
```

### 8.2 Evidence dari social content

Untuk post sosial yang dipakai sebagai bukti:

```text
date
channel
author
content excerpt
url
interactions
views
sentiment label
manual reading note
```

### 8.3 Evidence dari media online

Untuk artikel/media:

```text
media_name
article count
ad_value
article URL bila ada
claim/topic
source quality note
```

### 8.4 Jangan memakai evidence yang tidak lengkap

Jangan gunakan di main deck:

- screenshot tanpa URL/identitas;
- angka tanpa scope;
- post tanpa tanggal;
- ranking tanpa basis metric;
- quote tanpa konteks;
- claim besar tanpa source berkualitas.

---

## 9. Data freeze

Data freeze adalah snapshot terverifikasi yang menjadi satu-satunya sumber angka deck.

Buat data freeze sebelum narasi dan desain dimulai.

Nama file yang dianjurkan:

```text
deck_data.json
```

### 9.1 Struktur minimum

```json
{
  "report_metadata": {
    "contract_version": "3.1",
    "project_name": "Nama campaign",
    "report_type": "Crisis | Competitive | Campaign | Custom",
    "data_freeze_timestamp": "ISO-8601",
    "prepared_by": "Cogan MCP"
  },
  "scopes": {
    "brand": {},
    "issue_name": {}
  },
  "confirmed_intent_reference": "",
  "metric_readiness": {},
  "data_health": {},
  "metrics": {},
  "timeline": {},
  "evidence_posts": [],
  "evidence_media": [],
  "comparisons": {},
  "limitations": [],
  "reconciliation": {
    "overall_status": "PASS | FAIL",
    "checks": []
  }
}
```

### 9.2 Contoh data freeze crisis

```json
{
  "report_metadata": {
    "contract_version": "3.1",
    "project_name": "AQUA",
    "report_type": "Crisis",
    "data_freeze_timestamp": "2026-07-07T10:00:00+07:00"
  },
  "scopes": {
    "brand": {
      "universe": "brand",
      "start_date": "2025-10-21",
      "end_date": "2025-10-31",
      "channels": [],
      "keywords": [],
      "exclude_keywords": [],
      "match_mode": "any"
    },
    "source_water_issue": {
      "universe": "issue_only",
      "start_date": "2025-10-21",
      "end_date": "2025-10-31",
      "channels": [],
      "keywords": ["sumur bor", "akuifer", "mata air"],
      "exclude_keywords": [],
      "match_mode": "any"
    }
  },
  "metric_readiness": {
    "brand": {},
    "source_water_issue": {}
  },
  "data_health": {
    "brand": {},
    "source_water_issue": {}
  },
  "metrics": {
    "brand": {},
    "source_water_issue": {}
  },
  "timeline": {
    "source_water_issue": []
  },
  "evidence_posts": [],
  "limitations": [],
  "reconciliation": {
    "overall_status": "PASS",
    "checks": []
  }
}
```

Angka aktual tidak boleh diisi secara manual. Semua harus berasal dari output tool.

---

## 10. Rekonsiliasi sebelum narasi

Jalankan pemeriksaan berikut sebelum headline dibuat.

### 10.1 Scope integrity

- Setiap angka memiliki scope.
- Brand universe dan issue-only universe tidak tercampur.
- Keyword/exclusion yang dipakai tercatat.
- Date range actual sesuai request atau perbedaan dijelaskan.
- Channel filter konsisten antar chart yang dibandingkan.

### 10.2 Count integrity

- Channel post total = total canonical posts.
- Positive + neutral + negative + unclassified = total canonical posts.
- Duplicate rows removed tidak negatif.
- SOV total = 100% ± rounding.

### 10.3 Metric integrity

- Interactions tidak memasukkan views.
- Views tidak disebut interactions.
- Online media tidak diberi interaction formula.
- Ad value tidak dipakai sebagai interaction.
- Source engagement tidak dipakai sebagai KPI client-facing.
- Rumus interaction per channel tersedia bila interactions digunakan.

### 10.4 Coverage integrity

- Sentiment coverage memakai total canonical post.
- Interaction coverage memakai interaction-applicable post.
- Views coverage memakai total canonical post.
- Availability tidak dihitung dengan nilai `>0`.
- Guardrail dari `consistency_contract.md` diterapkan.

### 10.5 Evidence integrity

- Headline number ada di data freeze.
- Claim penting memiliki post/source evidence.
- Top content sudah dibaca.
- Mismatch sentiment sudah dicatat.
- Limitasi data tercatat.

Jika salah satu gagal, jangan mulai menulis deck.

---

## 11. Recommended tool call patterns

## 11.1 Brand baseline

```text
find_project()
validate_metric_readiness()
data_health()
count_posts()
metrics_summary()
timeline()
top_viral_posts(by="interactions")
top_viral_posts(by="views")
get_posts()
```

## 11.2 Issue-only analysis

```text
get_posts(keywords=...)             # validate scope dahulu
data_health(keywords=...)
count_posts(keywords=...)
metrics_summary(keywords=...)
timeline(keywords=...)
detect_spikes(keywords=...)
top_viral_posts(by="interactions", keywords=...)
top_viral_posts(by="views", keywords=...)
get_posts(keywords=..., sort_by="interactions")
get_posts(keywords=..., sort_by="views")
```

## 11.3 Competitor analysis

```text
find_project() per brand
validate_metric_readiness() per brand
data_health() per brand
compare_campaigns()
share_of_voice(metric="posts" | "buzz" | "interactions")
top_viral_posts() per brand
get_posts() per brand
```

## 11.4 Weekly monitor

```text
data_health()
count_posts()
metrics_summary()
timeline()
detect_spikes(metric="posts")
detect_spikes(metric="interactions")
detect_spikes(metric="views")
top_viral_posts(by="interactions")
top_viral_posts(by="views")
get_posts()
```

---

## 12. Tool limitations

Pahami keterbatasan Cogan MCP saat membuat kesimpulan.

### 12.1 Keyword filter

Keyword matching berbasis title/content.

Keterbatasan:

- dapat memasukkan false positive;
- dapat melewatkan istilah yang tidak ada di query;
- tidak memahami konteks/sarkasme;
- bukan coding issue final.

### 12.2 Interaction data

Interactions hanya dihitung pada channel dengan rumus yang tersedia.

Keterbatasan:

- channel mix dapat berbeda antar brand;
- field platform dapat tidak tersedia;
- total interactions lintas channel tidak otomatis comparable;
- coverage harus diperiksa sebelum dijadikan KPI.

### 12.3 Views

Views adalah exposure signal.

Keterbatasan:

- field tidak selalu tersedia;
- definisi platform dapat berbeda;
- views tidak membuktikan persuasion, sentiment, atau reputasi.

### 12.4 Sentiment

Sentiment adalah label data source.

Keterbatasan:

- dapat salah label;
- dapat tidak menangkap konteks;
- dapat tidak cocok dengan framing issue;
- perlu audit top content.

### 12.5 Social evidence

Post sosial membuktikan persepsi dan percakapan, bukan otomatis fakta eksternal.

Gunakan sumber primer/otoritatif untuk:

- regulator;
- legal;
- keselamatan;
- kesehatan;
- keputusan resmi;
- kepemilikan;
- kronologi fakta.

---

## 13. Do and don't

### Do

- Jalankan `validate_metric_readiness()` lalu `data_health()` sebelum memakai metric.
- Gunakan `interactions` dan `views` secara terpisah.
- Gunakan issue-only scope untuk report isu.
- Baca top post setelah melihat spike.
- Simpan scope/tool output penting ke data freeze.
- Gunakan `get_posts()` untuk validasi tema dan sentiment.
- Jelaskan keterbatasan coverage bila relevan.
- Bekukan angka sebelum membuat headline.

### Don't

- Jangan gunakan `engagement` sebagai istilah default.
- Jangan memakai `source_engagement` sebagai KPI.
- Jangan menggabungkan views dan interactions.
- Jangan hitung issue severity dari total brand post.
- Jangan gunakan keyword hit sebagai bukti final.
- Jangan membuat timeline hanya dari post count bila views/interactions menjawab pertanyaan lebih baik.
- Jangan menarik semua tool hanya karena tersedia.
- Jangan mulai desain sebelum reconciliation PASS.

---

## 14. Prinsip terakhir

Data workflow dinilai berhasil bila:

1. Setiap angka punya scope dan definisi.
2. Setiap insight punya bukti yang dapat ditelusuri.
3. Interactions dan views tidak tercampur.
4. Issue-only analysis tidak tercampur dengan brand-level context.
5. Semua headline number dapat ditemukan kembali di `deck_data.json`.
6. Model/analis tahu batas data sebelum menulis kesimpulan.
