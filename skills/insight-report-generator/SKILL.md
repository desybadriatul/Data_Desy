---
name: cogan-insight-report
version: 3.2
description: >
  Router utama untuk Cogan Insight Report Engine. Menentukan file mana yang
  berwenang, urutan kerja tingkat tinggi, intent confirmation wajib, artifact
  internal, dan batas antara deck client-facing dengan proses internal.
  Digunakan bersama Cogan MCP server.py dan db.py versi 3.0.
---

# COGAN INSIGHT REPORT ENGINE

## 1. Tujuan

Gunakan engine ini untuk membuat report berbasis data Cogan yang:

- menjawab pertanyaan bisnis;
- memakai scope, metric, dan evidence yang valid;
- membedakan interactions dari views;
- membedakan brand universe dari issue-only universe;
- mengubah data menjadi keputusan yang jelas bagi klien;
- tidak terlihat seperti export dashboard atau process log internal.

Prinsip inti:

> Decision  
> → scope  
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

Engine ini dirancang untuk Cogan MCP `server.py` dan `db.py` versi 3.0.

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

Untuk setiap permintaan **report, deck, narrative analysis, atau analisis yang
berujung pada insight/rekomendasi**, lakukan `intent_confirmation` terlebih dahulu.

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

Saat user meminta report apa pun, lakukan routing ini.

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

Minimal jalankan:

```text
find_project()
data_health()
```

Jangan memakai interactions, views, sentiment, buzz, atau ad value sebelum
coverage dan scope diperiksa.

### Step 4 — Evidence gathering

Gunakan tool sesuai pertanyaan:

```text
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

## 10. Default output policy

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

## 11. Prohibited behavior

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

## 12. Completion conditions

Report selesai hanya bila:

```text
[ ] Intent Confirmation telah disetujui user
[ ] Pembaca, problem, business question, decision, scope/periode, evidence plan, dan output telah dikonfirmasi
[ ] Project/data tersedia atau gap dijelaskan
[ ] Business question dan decision jelas
[ ] Scope data jelas
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

## 13. Prinsip terakhir

Jangan mengukur keberhasilan engine dari jumlah chart, jumlah slide, atau jumlah
tool yang dipanggil.

Engine berhasil bila:

> Klien menyetujui dulu apa yang sedang dianalisis, untuk siapa report dibuat,
> bukti apa yang akan dicari, dan keputusan apa yang perlu dibantu; lalu menerima
> report yang benar, mudah dipahami, berbasis bukti, dan membuat keputusan berikutnya lebih jelas.
