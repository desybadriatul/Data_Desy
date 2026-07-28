---
name: cogan-insight-report
version: 3.4
description: >
  Router utama untuk Cogan Insight Report Engine. Menentukan JALUR KERJA
  (bottom-up vs top-down), file mana yang berwenang, urutan kerja tingkat
  tinggi, intent confirmation wajib, artifact internal, dan batas antara deck
  client-facing dengan proses internal.
  Digunakan bersama Cogan MCP server.py dan db.py versi 3.1.
---

# COGAN INSIGHT REPORT ENGINE

## 0. LANGKAH PERTAMA — TENTUKAN JALUR

**Baca bagian ini sebelum bagian lain. Semua aturan di bawah hanya berlaku
setelah jalurnya ditentukan.**

Cogan punya dua jalur kerja yang sah, dan keduanya sudah benar. Yang selama ini
salah bukan aturannya, melainkan tidak adanya penentu kapan memakai yang mana.

Pertanyaannya satu:

> **User menyebut TIPE REPORT, atau tidak?**

---

### JALUR 1 — BOTTOM-UP (user MENYEBUT tipe report)

Pemicu: user menyebut salah satu jenis ini secara eksplisit.

| User menyebut | Tool |
|---|---|
| "daily report", "daily social report" | `create_daily_social_report_workflow` |
| "MMR", "mainstream media report" | `create_mainstream_media_report_workflow` |
| "competitive analysis", "CA" | `create_competitive_analysis_report_workflow` |
| "BCE", "brand content effectiveness" | `create_bce_report_workflow` |
| "industry trend" | `create_industry_trend_report_workflow` |
| "SFIR", "spokesperson report" | `create_sfir_report_workflow` |
| "EVO", "EVO perception", "perception intelligence", "brand perception report" | `create_evo_perception_intelligence_report_workflow` |

### SPECIALIST HANDOFF — SNA

Jika user menyebut **SNA**, **social network analysis**, **mention network**,
**actor network**, atau **penyebaran isu antar-akun**, baca dan ikuti
`../social-network-analysis/SKILL.md`.

SNA menghasilkan chart analitis, bukan salah satu workflow report Jalur 1.
Jangan memaksanya ke `create_*_report_workflow` dan jangan mengarang edge dari
jumlah reply/retweet tanpa akun tujuan.

Alur Jalur 1 sudah **pakem**:

```text
create_*_report_workflow
  -> (tanya audience bila workflow memintanya)
  -> Task 1: tarik data kuantitatif + kualitatif, format baku
  -> preview ke user
  -> user konfirmasi
  -> Task 2 -> PPT
```

**Di Jalur 1, aturan berikut TIDAK berlaku:**

- Bagian 5 dan 6 (Intent Confirmation 8 poin). Workflow punya gate sendiri.
  Jangan menjalankan dua gate.
- Bagian 7 (minimum workflow report).
- Bagian 10 (target 12-18 slide). Format deck sudah baku di renderer.
- Bagian 13 (completion conditions). Quality gate ada di dalam
  `build_*_ppt_package`.

**Di Jalur 1, JANGAN merakit slide manual** dari `perpustakaan_resep_slide.md`.
Deck dibangun oleh `build_*_ppt_package`.

Setelah jalur ini dipilih, **berhenti membaca SKILL.md**. Serahkan ke workflow.

---

### JALUR 2 — TOP-DOWN (user TIDAK menyebut tipe report)

Pemicu: user memberi **intent atau pertanyaan**, bukan nama report.

```text
"ada topik apa hari ini / minggu ini / bulan ini di brand A?"
"apa yang terjadi pada brand A periode B?"
"cek data brand A dan B"
"ada yang aneh nggak di brand A?"
"bikin laporan" / "saya mau PPT"     <- tanpa menyebut jenisnya
```

**Di Jalur 2, DILARANG memanggil:**

```text
create_*_report_workflow
prepare_report_input
build_*_ppt_package
```

Deck di Jalur 2 dirakit **dari skill ini**, bukan dari Task 1 / Task 2.

Urutan Jalur 2 — **jangan dibalik**:

```text
1. Intent Confirmation 8 poin (Bagian 6B)
   -> TAMPILKAN ke user, BERHENTI, tunggu persetujuan.
   -> Termasuk poin 7: output yang diharapkan (deck / narrative / memo).
   -> Belum boleh menarik data apa pun.

2. Setelah disetujui:
   validate_metric_readiness()
   data_health()

3. Diagnosis — cari tahu APA YANG TERJADI:
   scan_anomalies()   <- alat diagnosis utama
   timeline(), get_posts(), top_viral_posts(), top_authors(), dst

4. LAPORKAN TEMUAN ke user di chat lebih dulu.

5. Simpulkan JENIS MASALAHNYA (Bagian 6E) lalu konfirmasi singkat:
   "Ini Crisis/Issue/PR — saya susun deck-nya ya."

   JANGAN bertanya ulang "mau dibuatkan PPT atau tidak".
   Output sudah disepakati di langkah 1.

6. Rakit deck:
   skill_report.md              -> cerita, headline, rekomendasi
   perpustakaan_resep_slide.md  -> pilihan visual dan slide
   Target 12-18 slide main deck (Bagian 10).

7. Quality gate (Bagian 13).
```

---

### KALAU RAGU

Kalau ragu apakah user menyebut tipe report: berarti **TIDAK menyebut**.
Ambil **Jalur 2**.

> Bentuk report adalah **hasil diagnosis**, bukan menu yang dipilih dari cara
> user menyusun kalimat.

Isu krisis tidak otomatis menjadi "daily social report" hanya karena datanya
kebetulan sosial dan rentangnya harian. Kalau diagnosis menghasilkan
Crisis/Issue/PR atau Custom, bentuk deck-nya mengikuti masalah itu — bukan
dipaksa masuk cetakan salah satu dari tujuh tipe Jalur 1.

---

## 1. Tujuan

Gunakan engine ini untuk membuat report berbasis data Cogan yang:

- menjawab pertanyaan bisnis;
- memakai scope, metric, dan evidence yang valid;
- membedakan interactions dari views;
- membedakan brand universe dari issue-only universe;
- mengubah data menjadi keputusan yang jelas bagi klien;
- tidak terlihat seperti export dashboard atau process log internal.

Prinsip inti:

> Intent confirmation  
> → confirmed intent  
> → scope  
> → metric readiness  
> → data health  
> → evidence  
> → data freeze  
> → storyline  
> → visual  
> → quality gate  
> → deliverable

Jangan membalik urutan tersebut.

---

## 2. Struktur folder canonical

Gunakan struktur ini sebagai satu-satunya struktur aktif.

```text
skills/
└── insight-report-generator/
    ├── SKILL.md
    ├── skill_mapping.yaml
    └── references/
        ├── skill_report.md
        ├── consistency_contract.md
        ├── stage_data_cogan.md
        ├── system_prompt.md
        ├── quality_framework.md
        ├── perpustakaan_resep_slide.md
        └── methodology.md
```

`methodology.md` hanya deprecated stub. Jangan gunakan sebagai sumber aturan aktif.

---

## 3. File authority map

Jangan membuat aturan yang sama di beberapa file.

| File | Satu-satunya fungsi |
|---|---|
| `SKILL.md` | Router, urutan kerja tingkat tinggi, authority map |
| `references/skill_report.md` | Storytelling, headline, client-facing language, prioritisation, recommendation |
| `references/consistency_contract.md` | Metric definition, canonical post, scope, coverage, denominator, reconciliation |
| `references/stage_data_cogan.md` | Pemakaian MCP tools, evidence collection, data freeze |
| `references/system_prompt.md` | Orchestration detail dari brief hingga deliverable |
| `references/perpustakaan_resep_slide.md` | Pemilihan visual dan slide recipe |
| `references/quality_framework.md` | Quality gate akhir dan hard stop |
| `skill_mapping.yaml` | Mapping kebutuhan/report type ke file dan tool |
| `references/methodology.md` | Deprecated compatibility stub; tidak berwenang membuat aturan |

Jika file saling bertentangan, gunakan prioritas berikut:

```text
1. consistency_contract.md untuk data dan metric
2. stage_data_cogan.md untuk penggunaan tool dan data freeze
3. skill_report.md untuk cerita dan bahasa
4. quality_framework.md untuk keputusan lulus/tidak
5. perpustakaan_resep_slide.md untuk visual
6. system_prompt.md untuk orchestration
7. SKILL.md untuk routing
```

---

## 4. Dependency dengan MCP server

Engine ini dirancang untuk Cogan MCP `server.py` dan `db.py` versi 3.1.

Sebelum interactions atau views dipakai sebagai KPI report, wajib jalankan:

```text
validate_metric_readiness()
data_health()
```

`validate_metric_readiness()` memeriksa raw field, numeric format, channel mapping,
dan kesiapan coverage. `data_health()` memeriksa canonical post, dedup, periode,
dan coverage metric pada scope report.

Aturan metric server:

```text
Instagram  = Likes + Comments
Facebook   = Likes + Comments + Shares
YouTube    = Likes + Comments
TikTok     = Likes + Comments + Shares
X/Twitter  = Likes + Replies + Retweets
Views      = metric terpisah
```

Jangan menganggap `source_engagement` sebagai KPI report.

Jangan menggunakan istilah `engagement` ambigu untuk menggantikan `interactions`.

Semua aggregate report harus berasal dari canonical unique-post layer yang
disediakan server/database.

---

## 5. Intent confirmation dan artifact wajib

> **Bagian ini HANYA berlaku untuk JALUR 2 (top-down).**
> Di Jalur 1, workflow punya gate sendiri (audience → Task 1 preview →
> konfirmasi). Jangan menjalankan dua gate.

Untuk setiap permintaan **report, deck, narrative analysis, atau analisis yang
berujung pada insight/rekomendasi** yang masuk **Jalur 2**, lakukan
`intent_confirmation` terlebih dahulu.

`intent_confirmation` adalah respons yang **ditunjukkan kepada user** sebelum
analisis data dimulai. Setelah user menyetujui, simpan hasilnya sebagai
`confirmed_intent` internal.

Urutan artifact:

```text
0. intent_confirmation          # user-facing; wajib disetujui
1. confirmed_intent             # versi final setelah user setuju
2. report_brief
3. analysis_plan
4. deck_data.json
5. evidence_log
6. storyline
7. slide_plan
8. quality_report.json
9. final deliverable
```

Artifact internal tidak perlu masuk main deck kecuali user meminta audit detail.

`intent_confirmation` tidak diperlukan untuk permintaan operasional yang
benar-benar sempit, misalnya:

- daftar campaign;
- cek satu angka dengan scope yang sudah final;
- ekspor raw data;
- mengambil satu chart/table yang tidak meminta interpretasi atau rekomendasi.

Namun, jika output tersebut akan dipakai untuk membuat **kesimpulan, report,
atau rekomendasi**, intent confirmation tetap wajib.

---

## 6. Routing awal dan Intent Confirmation Gate

> **Bagian ini HANYA berlaku untuk JALUR 2 (top-down).**
> Kalau user menyebut tipe report secara eksplisit, itu Jalur 1 — lewati
> seluruh bagian ini dan serahkan ke `create_*_report_workflow`.

Setelah Bagian 0 menetapkan Jalur 2, lakukan routing ini.

### A. Tentukan apakah Intent Confirmation Gate wajib

Gate ini wajib untuk:

```text
deck
report
memo analitis
narrative analysis
competitive / crisis / campaign / brand-health analysis
custom analysis
permintaan yang membutuhkan conclusion, recommendation, atau decision support
```

Gate ini tidak wajib hanya bila user benar-benar meminta output operasional
sempit tanpa interpretasi, misalnya raw export atau satu angka yang scope-nya
sudah jelas.

Jangan diam-diam menganggap intent sudah jelas hanya karena prompt user panjang.

### B. Kirim Intent Confirmation kepada user dan berhenti dulu

Sebelum memanggil tool aggregate, membaca top post, mencari fakta eksternal,
menyusun storyline, atau memberi rekomendasi, tampilkan format berikut:

```text
Intent Confirmation — menunggu persetujuan

1. Pembaca report:
   [siapa yang akan memakai report]

2. Masalah yang akan dianalisis:
   [problem / opportunity yang ingin dipahami]

3. Pertanyaan bisnis:
   [pertanyaan yang harus dijawab report]

4. Keputusan yang perlu dibantu:
   [pilihan keputusan atau jenis rekomendasi yang report harus bantu jawab;
   bukan solusi final yang sudah diputuskan]

5. Scope awal:
   [brand / issue-only / activity / competitor]
   [periode, channel, competitor atau issue bila relevan]

6. Bukti yang akan dicari:
   [mis. ukuran dan tren isu, konten pemicu, views, interactions,
   actor/media penggerak, serta sumber eksternal bila diperlukan]

7. Output yang akan dibuat:
   [deck / narrative / memo / appendix / chart]
   [batas slide, bahasa, atau constraint bila ada]

8. Asumsi atau informasi yang masih perlu dikonfirmasi:
   [hanya yang material]
```

Tutup dengan satu pertanyaan eksplisit:

```text
Apakah pemahaman ini sudah benar? Balas “setuju” untuk lanjut,
atau koreksi bagian yang perlu diubah.
```

Aturan penting:

- Bukti pada poin 6 adalah **rencana evidence**, bukan claim bahwa bukti itu
  sudah ditemukan.
- Poin 4 menjelaskan keputusan yang ingin dibantu, bukan rekomendasi final.
- Jika audience, problem, business question, decision, scope/period, atau
  output masih materially unclear, tandai `Belum dikonfirmasi`.
- Jangan memulai analisis hingga user menyetujui atau memperbaiki ringkasan.
- Jika user mengoreksi, kirim ulang Intent Confirmation versi revisi dan
  tunggu persetujuan lagi.
- Jawaban seperti `setuju`, `ya`, `lanjut`, atau persetujuan jelas lainnya
  hanya dianggap valid bila tidak ada field material yang masih
  `Belum dikonfirmasi`.
- Untuk revisi lanjutan dalam report yang sama, gunakan `confirmed_intent`
  yang sudah ada selama user tidak mengubah problem, audience, scope,
  periode, atau output.

### C. Validasi project/data setelah intent disetujui

Panggil atau gunakan:

```text
ping_cogan()
find_project(project_name)
```

Jika project tidak tersedia, jangan mengarang data.

### D. Buat report brief dari confirmed intent

Identifikasi dan simpan:

```text
client / project
report request
audience
business problem
business question
decision to support
period
data source
competitor bila relevan
issue/activity scope bila relevan
desired output
constraints
confirmed assumptions
```

### E. Tentukan jenis kebutuhan

Pilih salah satu atau beberapa:

```text
Crisis / Issue / PR
Competitive
Campaign / Sponsorship / Activation
Brand Health / Weekly / Monthly
Segmentation / Research
Custom
```

Jenis ini adalah shortcut untuk data plan dan storyline, bukan menu tertutup.

**Jangan tertukar dengan tujuh tipe report Jalur 1.**

Keduanya adalah **sumbu yang berbeda**, bukan dua nama untuk hal yang sama:

| Taksonomi Jalur 2 (bagian ini) | Taksonomi Jalur 1 (workflow tool) |
|---|---|
| menjawab: **masalahnya apa** | menjawab: **formatnya apa** |
| Crisis / Issue / PR | daily_social_media_report |
| Competitive | mainstream_media_report |
| Campaign / Sponsorship / Activation | competitive_analysis |
| Brand Health / Weekly / Monthly | brand_content_effectiveness |
| Segmentation / Research | industry_trend |
| Custom | spokesperson_intelligence |

Aturan:

- Jenis di bagian ini **ditentukan SETELAH data dibaca**, sebagai hasil
  diagnosis. Bukan ditebak dari kalimat user.
- Jenis ini **tidak dipetakan** ke workflow tool Jalur 1. Sekali masuk Jalur 2,
  deck tetap dirakit dari skill.
- Kasus Crisis/Issue/PR **tidak punya padanan** di Jalur 1. Jangan memaksanya
  menjadi "daily social report" hanya karena datanya sosial dan rentangnya
  harian.

### F. Tentukan data universe

Pilih sesuai kebutuhan:

```text
brand
issue_only
activity_property
competitor_comparison
historical_comparison
```

### G. Pilih file yang diperlukan

Gunakan `skill_mapping.yaml`.

Jangan membaca semua file secara membabi buta bila hanya satu file yang relevan.

Namun sebelum membuat report final, minimal harus menggunakan:

```text
consistency_contract.md
stage_data_cogan.md
skill_report.md
quality_framework.md
```

## 7. Minimum workflow report

> **Bagian ini HANYA berlaku untuk JALUR 2 (top-down).**
> Jalur 1 memakai alur pakem-nya sendiri: workflow → Task 1 preview →
> konfirmasi → Task 2 → PPT.

### Step 0 — Intent confirmation

Buat dan tampilkan `intent_confirmation`.

Tunggu user mengonfirmasi:

```text
pembaca
masalah
pertanyaan bisnis
keputusan yang perlu dibantu
scope/periode
bukti yang akan dicari
output yang diharapkan
```

Jangan menarik data untuk analisis sebelum intent disetujui.

### Step 1 — Confirmed brief

Setelah user setuju, buat `confirmed_intent` lalu turunkan menjadi
`report_brief`.

Jangan mulai dari chart atau layout.

### Step 2 — Data plan

Buat `analysis_plan`.

Tentukan:

- universe;
- question to test;
- metric yang dibutuhkan;
- evidence yang dibutuhkan;
- limitation yang diperkirakan;
- tool MCP yang relevan.

### Step 3 — Data validation

Minimal jalankan setelah Intent Confirmation disetujui:

```text
find_project()
validate_metric_readiness()
data_health()
```

Jangan memakai interactions atau views sebelum status readiness dan coverage
diperiksa. Jika readiness `FAIL`, jangan gunakan interactions sebagai KPI.
Jika readiness `WARN`, gunakan hanya channel/metric yang lolos guardrail dan
catat caveat pada data freeze.

### Step 4 — Evidence gathering

Gunakan tool sesuai pertanyaan:

```text
scan_anomalies()          # alat diagnosis utama Jalur 2 — 17 detector
count_posts()
metrics_summary()
timeline()
detect_spikes()
top_viral_posts()
top_authors()
top_media()
get_posts()
compare_periods()
compare_campaigns()
share_of_voice()
export_raw_data()
```

Jangan memanggil seluruh tool hanya karena tersedia.

### Step 5 — Data freeze

Buat `deck_data.json`.

Seluruh angka deck harus berasal dari file ini.

### Step 6 — Storyline

Gunakan `skill_report.md`.

Buat:

```text
executive answer
what happened
why it matters
priority
action / option
decision
```

### Step 7 — Slide plan dan visual

Gunakan `perpustakaan_resep_slide.md`.

Visual dipilih setelah message dan evidence jelas.

### Step 8 — Quality gate

Gunakan `quality_framework.md`.

Jangan kirim bila hard stop ditemukan.

---

## 8. Mandatory data rules

Aturan ini wajib dipatuhi oleh semua jenis report.

### 8.1 Scope

Setiap metric utama harus memiliki scope yang jelas:

```text
universe
period
channel
keyword/exclusion bila ada
match mode bila ada
```

### 8.2 Interactions dan views

Selalu perlakukan sebagai metric terpisah:

```text
Interactions = aksi pengguna
Views = exposure/tayangan
```

Jangan menggabungkan keduanya.

### 8.3 Brand versus issue

Jangan menggunakan total brand universe untuk mengukur severity satu isu.

Gunakan:

```text
brand universe
→ context

issue-only universe
→ risk / trend / sentiment / evidence issue
```

### 8.4 Social post versus external fact

Post sosial menunjukkan:

- persepsi;
- framing;
- opini;
- tuntutan;
- pola percakapan.

Post sosial tidak otomatis membuktikan:

- fakta legal;
- keputusan regulator;
- keselamatan;
- kesehatan;
- tanggung jawab resmi.

Gunakan sumber eksternal yang dapat diverifikasi untuk claim tersebut.

### 8.5 Data limitation

Jika coverage tidak cukup:

- turunkan wording;
- gunakan sebagai directional;
- pindahkan ke appendix;
- atau jangan gunakan.

Jangan menyembunyikan keterbatasan dengan desain atau bahasa yang meyakinkan.

---

## 9. Main deck versus internal material

### Main deck boleh berisi

- executive answer;
- finding;
- evidence;
- metric yang relevan;
- implication;
- action;
- decision;
- limitation material.

### Main deck tidak boleh berisi

- prompt;
- tool name;
- stage;
- workflow;
- data extraction log;
- quality score;
- metric contract;
- query keyword detail;
- framework internal;
- system wording;
- source engagement diagnostic;
- net sentiment interaction-weighted.

### Internal artifact boleh berisi

- data health;
- scope detail;
- keywords;
- evidence log;
- reconciliation;
- quality report;
- methodology detail;
- source list;
- audit table.

---

## 10. Default main-deck target

> **Bagian ini HANYA berlaku untuk JALUR 2 (top-down).**
> Format deck Jalur 1 sudah baku di dalam `build_*_ppt_package`.

Untuk deck client-facing, target normal adalah **12–18 slide total main deck**.

Perhitungan:

```text
Termasuk:
- cover / report identity;
- executive summary;
- action / recommendation / decision;
- seluruh evidence slide yang berada dalam alur utama;
- closing/next-step bila digunakan.

Tidak termasuk:
- appendix;
- source log;
- methodology detail;
- audit table;
- raw evidence tambahan;
- technical notes.
```

Aturan:

- Gunakan 12–18 sebagai target desain, bukan alasan menambahkan filler.
- Bila kebutuhan bisnis dapat dijawab dengan lebih sedikit slide, tambahkan
  hanya evidence atau action layer yang benar-benar memperjelas keputusan.
- Bila main deck di luar 12–18, alasan harus dicatat di `quality_report.json`
  dan disetujui oleh kebutuhan user/audience, bukan oleh template.
- Setiap slide tetap harus memiliki satu pesan utama dan peran dalam storyline.

---

## 11. Default output policy

### Jika user meminta deck

Buat:

```text
main deck
appendix bila perlu
deck_data.json
evidence/source log
quality report internal
```

### Jika user meminta narrative report

Buat:

```text
narrative client-facing
deck_data.json internal
evidence/source log internal
quality report internal
```

### Jika user meminta chart/table

Tetap:

- lakukan data health;
- cek scope;
- gunakan metric label yang benar;
- jangan mencampurkan interactions dan views;
- sertakan source/scope jika tanpa itu chart berisiko disalahartikan.

---

## 12. Prohibited behavior

Jangan:

- memulai dari slide template;
- memulai dari semua tool;
- memakai semua metric yang tersedia;
- memakai `source_engagement` sebagai KPI;
- menyebut views sebagai interactions;
- memakai brand total untuk issue severity;
- memakai keyword match sebagai final classification;
- memakai satu post viral sebagai pola tanpa outlier check;
- memakai post sosial sebagai bukti tunggal facts sensitif;
- membuat target angka palsu;
- menulis recommendation generik;
- memasukkan internal framework ke main deck;
- mengirim deck sebelum reconciliation PASS.

---

## 13. Completion conditions

> **Bagian ini HANYA berlaku untuk JALUR 2 (top-down).**
> Jalur 1 punya quality gate sendiri di dalam `build_*_ppt_package`.

Report selesai hanya bila:

```text
[ ] Intent Confirmation telah disetujui user
[ ] Pembaca, problem, business question, decision, scope/periode, evidence plan, dan output telah dikonfirmasi
[ ] Project/data tersedia atau gap dijelaskan
[ ] Business question dan decision jelas
[ ] Scope data jelas
[ ] Metric readiness diperiksa: PASS, atau WARN sudah memiliki caveat/downgrade
[ ] Data health diperiksa
[ ] Evidence penting dibaca
[ ] deck_data.json selesai
[ ] Reconciliation PASS
[ ] Storyline menjawab question
[ ] Slide plan hanya memuat slide yang relevan
[ ] Quality report tidak memiliki hard failure
[ ] Final deliverable sesuai format user
```

---

## 14. Prinsip terakhir

Jangan mengukur keberhasilan engine dari jumlah chart, jumlah slide, atau jumlah
tool yang dipanggil.

Engine berhasil bila:

> Klien menyetujui dulu apa yang sedang dianalisis, untuk siapa report dibuat,
> bukti apa yang akan dicari, dan keputusan apa yang perlu dibantu; lalu menerima
> report yang benar, mudah dipahami, berbasis bukti, dan membuat keputusan berikutnya lebih jelas.
