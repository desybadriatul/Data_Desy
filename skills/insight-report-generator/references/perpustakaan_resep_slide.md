---
name: cogan-slide-visual-library
version: 3.1
description: >
  Perpustakaan pilihan visual untuk report Cogan. File ini membantu memilih bentuk
  slide yang paling tepat berdasarkan pesan dan bukti yang sudah tersedia. File ini
  tidak menentukan storytelling, metrik, workflow, maupun quality gate.
---

# COGAN SLIDE VISUAL LIBRARY

## 1. Otoritas file ini

File ini hanya mengatur:

- cara memilih bentuk visual untuk sebuah pesan;
- struktur visual per slide;
- kapan memakai chart, diagram, screenshot, table, card, atau decision tree;
- cara menampilkan evidence dengan jelas;
- cara menjaga main deck agar editorial, bukan dashboard dump.

File ini **tidak boleh** mengatur:

- formula atau definisi metrik;
- scope data, coverage, denominator, atau canonical dedup;
- urutan cerita report;
- headline dan wording narasi;
- rekomendasi bisnis;
- jumlah slide wajib;
- quality status `PASS` atau `FAIL`;
- detail teknis query/tool MCP.

Gunakan file sumber berikut untuk kebutuhan tersebut:

| Kebutuhan | File sumber |
|---|---|
| Metrik, scope, coverage, dan label resmi | `consistency_contract.md` |
| Pengambilan data dan data freeze | `stage_data_cogan.md` |
| Storyline, headline, dan rekomendasi | `skill_report.md` |
| Urutan proses end-to-end | `system_prompt.md` |
| QA final | `quality_framework.md` |
| Router / pembagian dokumen | `SKILL.md` |

Prinsip:

> Visual mengikuti pesan dan bukti.  
> Visual tidak boleh menentukan pesan hanya karena sebuah layout tersedia.

---

## 2. Prinsip visual utama

### 2.1 Satu slide, satu pesan

Setiap slide harus memiliki satu hal utama yang ingin dipahami pembaca.

Jangan membuat satu slide untuk:

- menjelaskan tren;
- menampilkan top post;
- membandingkan kompetitor;
- memberi rekomendasi;
- dan menyampaikan caveat;

secara bersamaan.

Jika semua itu perlu, pecah menjadi beberapa slide atau pindahkan detail ke appendix.

---

### 2.2 Headline lebih penting daripada layout

Mulai dari headline yang sudah disetujui dalam storyline.

Baru tanyakan:

```text
Bukti visual apa yang paling cepat membuat pembaca memahami headline ini?
```

Jangan mulai dari:

```text
Saya punya layout tiga kartu, angka apa yang bisa dimasukkan?
```

---

### 2.3 Bukti harus terlihat, bukan hanya disebut

Jika suatu finding bergantung pada:

- satu post viral;
- framing publik;
- komentar penting;
- headline media;
- perbedaan klaim;
- respons brand;

gunakan evidence visual yang nyata bila memungkinkan:

- screenshot post;
- potongan artikel;
- quote dengan source;
- timeline dengan annotation;
- diagram sebab-akibat.

Jangan mengganti bukti penting dengan kartu berisi angka saja.

---

### 2.4 Chart bukan dekorasi

Chart hanya dipakai ketika pembaca perlu melihat:

- perubahan;
- perbandingan;
- ranking;
- komposisi;
- distribusi;
- konsentrasi;
- hubungan sebab-akibat berbasis waktu.

Jangan membuat chart hanya karena angkanya ada.

Jika satu kalimat + satu angka lebih jelas, gunakan satu kalimat + satu angka.

---

### 2.5 Editorial, bukan dashboard

Main deck harus terasa seperti report yang dipikirkan, bukan dashboard yang diekspor.

Hindari pola berulang seperti:

```text
judul
→ tiga KPI cards
→ empat finding cards
→ tiga recommendation cards
→ table
```

Gunakan card hanya ketika beberapa informasi benar-benar independen dan perlu dipindai cepat.

---

### 2.6 Konsistensi lebih penting daripada variasi dekoratif

Tidak semua slide harus memakai layout berbeda.

Gunakan layout yang sama bila:

- pertanyaannya sama;
- pembaca perlu membandingkan slide secara langsung;
- struktur visual membantu konsistensi.

Ubah layout ketika:

- jenis bukti berubah;
- pertanyaan pembaca berubah;
- cara memahami pesan perlu berubah.

Jangan mengubah layout hanya agar deck terlihat “variatif”.

---

## 3. Aturan pemilihan visual

Gunakan tabel ini sebelum memilih resep slide.

| Pertanyaan pembaca | Visual utama yang biasanya tepat |
|---|---|
| Apa jawaban paling penting? | Executive answer frame |
| Apa yang berubah dari waktu ke waktu? | Trend / timeline |
| Siapa atau apa yang paling besar? | Ranking / comparison |
| Dari mana komposisi percakapan berasal? | Composition / stacked distribution |
| Mengapa publik salah memahami sesuatu? | Issue anatomy |
| Konten apa yang menjadi bukti utama? | Evidence board |
| Apakah performa ditopang satu outlier? | Concentration / distribution |
| Siapa penggerak utama? | Actor / author landscape |
| Media mana yang paling banyak mengangkat isu? | Media landscape |
| Mana yang harus ditindak sekarang? | Priority / action matrix |
| Kapan brand perlu bicara atau tidak? | Decision tree |
| Siapa melakukan apa? | Operating plan |
| Apa detail yang perlu dibandingkan presisi? | Compact comparison table |
| Apa keterbatasan data yang perlu diungkap? | Limitation / scope panel |

Jangan memaksa tabel ini. Gunakan sebagai titik awal.

---

## 4. Struktur dasar slide

Setiap slide idealnya memiliki empat lapisan.

```text
1. Headline
   Kesimpulan yang ingin dipahami pembaca.

2. Main evidence
   Chart, screenshot, diagram, comparison, atau table.

3. So what
   Satu sampai dua kalimat yang menjelaskan arti untuk klien.

4. Context / source
   Scope, period, basis metric, atau source note bila diperlukan.
```

Tidak semua lapisan harus berukuran sama.

Contoh:

- Slide dengan screenshot besar dapat memakai sedikit angka.
- Slide trend dapat memakai event annotation sebagai “so what”.
- Slide decision dapat memakai minim chart.
- Slide appendix dapat lebih detail, tetapi tetap harus terbaca.

---

## 5. Visual evidence hierarchy

Pilih bentuk evidence dari yang paling sesuai dengan pesan.

| Level | Bentuk evidence | Gunakan ketika |
|---|---|---|
| 1 | Screenshot post / artikel / quote | Framing atau statement asli adalah inti finding |
| 2 | Trend chart dengan annotation | Waktu, perubahan, atau spike menjelaskan finding |
| 3 | Ranking / comparison chart | Prioritas atau gap antar unit adalah inti finding |
| 4 | Diagram issue anatomy | Pembaca perlu memahami hubungan sebab-akibat |
| 5 | Compact table | Pembaca perlu membandingkan beberapa item secara presisi |
| 6 | Cards | Hanya untuk beberapa fakta ringkas yang independen |

Urutan ini bukan urutan kualitas mutlak. Ini urutan berdasarkan kebutuhan pembaca.

---

## 6. Aturan label metric pada visual

Gunakan label yang sama dengan `consistency_contract.md`.

### 6.1 Interactions dan views

Selalu pisahkan:

```text
Interactions
Views
```

Jangan menulis:

```text
Engagement
```

kecuali user secara eksplisit memerlukan istilah itu dan definisinya sudah dijelaskan sebagai interactions.

Gunakan label yang jelas:

```text
Interactions (platform-native)
Views
Views available on X% of posts
```

### 6.2 Jangan taruh unit yang berbeda dalam satu axis

Jangan membuat satu bar chart yang mencampurkan:

- views;
- interactions;
- ad value;
- buzz;

dalam satu axis atau satu ranking tanpa pemisahan visual yang jelas.

Gunakan salah satu:

- dua panel terpisah;
- satu chart utama + mini supporting metric;
- table dengan kolom yang jelas;
- satu metric per slide.

### 6.3 Scope dan basis metric

Tambahkan scope ringkas bila tanpa scope pembaca berisiko salah paham.

Contoh footer:

```text
Source: Cogan | Issue-only scope: “sumur bor”, “akuifer”, “mata air” | 21–31 Oct 2025
```

Contoh label SOV:

```text
Share of Voice berdasarkan post
Share of Interactions
Share of Voice berdasarkan buzz
```

Jangan menulis hanya:

```text
SOV
Sentiment
Top Media
Engagement
```

tanpa basis.

---

## 7. Resep visual

Resep di bawah adalah pilihan visual.

Setiap resep memiliki:

- tujuan;
- kapan digunakan;
- kapan tidak digunakan;
- susunan visual;
- input minimum;
- catatan implementasi.

Resep tidak pernah menjadi slide wajib.

---

# R01 — Executive Answer Frame

## Tujuan

Memberi jawaban langsung terhadap pertanyaan bisnis pada awal report.

## Gunakan ketika

- pembaca senior membutuhkan jawaban cepat;
- report memiliki satu kesimpulan utama;
- perlu menyatukan beberapa bukti menjadi satu keputusan;
- cover perlu lebih dari sekadar judul.

## Jangan gunakan ketika

- belum ada evidence yang cukup;
- report masih exploratory;
- jawaban harus dipisahkan menjadi beberapa scenario yang tidak dapat diringkas jujur.

## Struktur visual

```text
Headline answer

1 visual anchor:
- mini trend
- mini comparison
- mini issue anatomy
- atau satu number dengan konteks

2–3 supporting proof points:
- bukan KPI dump
- bukan semua metrics
- pilih bukti yang paling menjelaskan jawaban

Bottom line:
- implication / decision prompt
```

## Input minimum

- executive answer;
- satu sampai tiga proof point dari data freeze;
- scope yang jelas;
- satu implication.

## Catatan implementasi

- Jangan menggunakan empat KPI besar hanya untuk terlihat seperti cover dashboard.
- Maksimal tiga angka penting.
- Jika satu angka saja sudah menjelaskan jawaban, jangan tambah angka lain.
- Jangan memasukkan methodology, contract, atau framework internal.

---

# R02 — Text + Proof Panel

## Tujuan

Menjelaskan satu finding penting yang belum membutuhkan chart kompleks.

## Gunakan ketika

- satu kesimpulan dapat didukung oleh satu number dan satu bukti;
- pembaca perlu membaca claim sebelum melihat detail;
- evidence berupa quote, short excerpt, atau mini screenshot.

## Jangan gunakan ketika

- data memiliki pola waktu yang lebih penting;
- pembaca perlu membandingkan banyak item;
- slide menjadi terlalu text-heavy.

## Struktur visual

```text
Left:
Headline + 1–2 sentence interpretation

Right:
One visual proof:
- screenshot
- quote
- mini bar
- mini table
- one key number

Footer:
scope + source
```

## Input minimum

- headline;
- satu evidence visual;
- satu to two explanatory sentences;
- source/scope note.

## Catatan implementasi

- Cocok untuk bridge slide antara chart besar dan recommendation.
- Jangan membuat bukti kecil sampai tidak terbaca.
- Jangan memakai quote tanpa source.

---

# R03 — Annotated Trend / Timeline

## Tujuan

Menjelaskan kapan sebuah perubahan terjadi dan apa pemicunya.

## Gunakan ketika

- pertanyaan utama adalah naik/turun;
- ada spike;
- timeline memperjelas hubungan antara event dan percakapan;
- current period dibanding baseline secara setara.

## Jangan gunakan ketika

- hanya ada satu data point;
- perubahan waktu tidak relevan;
- data harian terlalu sedikit atau coverage terlalu lemah;
- chart hanya menunjukkan angka tanpa peristiwa/pemicu.

## Struktur visual

```text
Headline

Main:
line / area / bar trend

Annotations:
- event
- post viral
- statement brand
- media pickup
- milestone

Side or below:
- peak value
- explanation of peak
- implication
```

## Input minimum

- timeline dari data freeze;
- metric basis yang jelas;
- satu atau lebih event/evidence date;
- explanation of what happened at peak.

## Catatan implementasi

- Gunakan satu metric utama per chart: posts atau interactions atau views.
- Jika perlu membandingkan posts dan views, gunakan dua panel atau dua line dengan label yang sangat jelas.
- Jangan memakai dual axis jika pembaca dapat salah memahami perbandingan.
- Semua annotation harus punya evidence link atau source log.

---

# R04 — Ranking / Comparison Bar

## Tujuan

Menunjukkan siapa/apa yang paling besar, paling tinggi, atau paling relevan.

## Gunakan ketika

- perlu ranking top issues, channels, competitors, authors, properties, atau media;
- perbandingan antar unit adalah inti pesan;
- pembaca perlu melihat gap secara cepat.

## Jangan gunakan ketika

- unit yang dibandingkan tidak comparable;
- ranking hanya berbeda tipis dan tidak punya arti;
- satu unit punya metric berbeda;
- terlalu banyak kategori sehingga label tidak terbaca.

## Struktur visual

```text
Headline

Main:
horizontal bar ranking

Optional:
one highlight annotation on the important gap

Bottom:
one interpretation sentence
```

## Input minimum

- daftar unit;
- satu metric basis;
- scope yang sama;
- sorting rule;
- evidence/limitation note bila needed.

## Catatan implementasi

- Gunakan horizontal bar untuk nama kategori panjang.
- Batasi main deck pada sekitar 5–8 items; sisanya appendix.
- Jangan mencampur views dan interactions pada bar yang sama.
- Untuk SOV, basis harus ditulis langsung pada chart.

---

# R05 — Composition / Mix

## Tujuan

Menunjukkan proporsi bagian dari satu total yang bermakna.

## Gunakan ketika

- breakdown sentiment;
- channel mix;
- share of voice;
- distribution issue;
- share of interaction;
- mix content type.

## Jangan gunakan ketika

- kategori banyak;
- nilai tidak benar-benar membentuk satu total;
- ranking lebih penting daripada proporsi;
- audience perlu membaca angka presisi satu per satu.

## Struktur visual

```text
Headline

Main:
stacked bar / 100% stacked bar / simple composition

Supporting:
- key share
- one implication
```

## Input minimum

- categories yang mutually exclusive atau overlap-nya sudah dijelaskan;
- total denominator;
- percentage basis;
- scope.

## Catatan implementasi

- Gunakan 100% stacked bar untuk sentiment atau channel share.
- Jangan gunakan pie chart bila kategori lebih dari lima atau ranking penting.
- Jangan menggunakan composition chart jika topic overlap tetapi total seolah-olah 100%.
- Bila sentiment coverage rendah, tampilkan caveat dengan jelas dan jangan jadikan slide hero.

---

# R06 — Issue Anatomy

## Tujuan

Menjelaskan akar masalah, salah paham publik, atau rantai sebab-akibat.

## Gunakan ketika

- isu teknis perlu diterjemahkan menjadi risiko reputasi;
- publik membaca satu fakta secara berbeda dari brand;
- hubungan antara claim, perception, risk, dan response perlu dibuat jelas;
- crisis report membutuhkan penjelasan, bukan hanya angka.

## Jangan gunakan ketika

- belum ada evidence yang cukup mengenai framing publik;
- issue terlalu luas dan belum diprioritaskan;
- diagram menjadi terlalu spekulatif.

## Struktur visual

```text
Trigger / claim publik
        ↓
Interpretasi publik
        ↓
Kekhawatiran / tuduhan
        ↓
Risiko untuk brand
        ↓
Evidence / response gap
        ↓
Tindakan yang perlu disiapkan
```

## Input minimum

- verified evidence;
- public framing evidence;
- distinction between fact and allegation;
- implication for brand;
- action implication.

## Catatan implementasi

- Gunakan panah dan hubungan sederhana.
- Jangan memasukkan terlalu banyak cabang.
- Bedakan visual antara verified fact, public perception, dan unknown.
- Jangan menulis seolah claim publik sudah terbukti benar.
- Cocok untuk AQUA-like case: claim → interpretasi → reputational consequence.

---

# R07 — Evidence Board

## Tujuan

Menempatkan konten/source asli sebagai bukti utama tanpa membuat slide menjadi scrapbook.

## Gunakan ketika

- satu post, artikel, atau respons brand merupakan pemicu penting;
- content framing lebih kuat daripada angka aggregate;
- perlu membuktikan apa yang benar-benar dilihat publik.

## Jangan gunakan ketika

- screenshot tidak terbaca;
- konten tidak punya peran penting dalam cerita;
- sumber tidak dapat ditelusuri;
- jumlah screenshot terlalu banyak.

## Struktur visual

```text
Main:
one large screenshot / article excerpt / post card

Callout 1:
what it says / framing

Callout 2:
why it matters

Supporting mini-chart or small stat:
views / interactions / timeline position

Footer:
author, channel, date, URL/source
```

## Input minimum

- source visual yang jelas;
- metadata post/article;
- evidence reading note;
- one supporting metric;
- scope.

## Catatan implementasi

- Gunakan satu screenshot besar daripada empat screenshot kecil.
- Crop hanya untuk fokus, jangan mengubah arti.
- Screenshot tidak boleh menjadi dekorasi.
- Jika evidence adalah social post, jelaskan bahwa ia merepresentasikan public framing, bukan fakta resmi.
- Jangan tampilkan screenshot tanpa link/source log.

---

# R08 — Concentration / Outlier Diagnostic

## Tujuan

Menunjukkan apakah performa ditopang satu konten atau tersebar secara lebih konsisten.

## Gunakan ketika

- total interactions/views terlihat tinggi tetapi perlu dicek apakah ada outlier;
- user ingin tahu apakah campaign bekerja secara sistemik;
- comparative report berisiko menyimpulkan pemenang dari satu post viral.

## Jangan gunakan ketika

- hanya ada beberapa post;
- data metric coverage rendah;
- audience tidak membutuhkan detail distribusi.

## Struktur visual

Pilihan A:

```text
Top post contribution
vs
rest of posts
```

Pilihan B:

```text
Top 5 content contribution
vs
remaining content
```

Pilihan C:

```text
Ranked bars of individual posts
with top-post annotation
```

## Input minimum

- total metric;
- metric per post;
- top post;
- count of posts;
- coverage note.

## Catatan implementasi

- Gunakan label “ditopang satu post” hanya jika kontribusi outlier benar-benar material.
- Jangan memakai chart ini hanya untuk membuat top post terlihat penting.
- Cocok untuk sponsorship, campaign, creator, dan competitive analysis.

---

# R09 — Actor / Author Landscape

## Tujuan

Menunjukkan siapa yang menggerakkan percakapan dan pola perannya.

## Gunakan ketika

- perlu membedakan akun besar, komunitas, media, influencer, atau akun brand;
- actor mapping relevan terhadap action;
- report perlu menjelaskan penyebaran narasi.

## Jangan gunakan ketika

- ranking author saja tidak mengubah keputusan;
- actor identity tidak dapat diverifikasi;
- satu author dengan satu post terlalu mudah disalahartikan.

## Struktur visual

Pilihan A:

```text
Ranked author list
with posts + interactions + views
```

Pilihan B:

```text
2x2 landscape:
reach/exposure
vs
interaction/activity
```

Pilihan C:

```text
Actor role map:
media / creator / official / community / critic
```

## Input minimum

- author;
- channel;
- post count;
- interactions;
- views bila tersedia;
- top post evidence;
- role classification jika digunakan.

## Catatan implementasi

- Jangan hanya ranking berdasarkan interactions.
- Selalu tampilkan jumlah post untuk membedakan one-hit outlier dan consistent driver.
- Jangan menyebut “aktor utama” jika evidence hanya satu post.
- Gunakan role label hanya bila basisnya jelas.

---

# R10 — Media Landscape

## Tujuan

Menunjukkan outlet/media yang paling banyak atau paling bernilai dalam liputan online.

## Gunakan ketika

- mainstream/online media merupakan bagian penting dari report;
- user perlu tahu outlet mana yang memuat isu;
- perlu membedakan volume artikel dan ad value.

## Jangan gunakan ketika

- source data media terlalu lemah;
- label “top media” hanya berdasarkan ad value tanpa konteks;
- report utamanya tentang social media dan media coverage tidak relevan.

## Struktur visual

```text
Main:
ranked table / horizontal bar

Columns:
Media
Articles
Ad value
Optional: issue/article framing

Side:
one conclusion about distribution of coverage
```

## Input minimum

- media name;
- article count;
- ad value;
- scope issue;
- source note.

## Catatan implementasi

- Labelkan ad value sebagai “nilai eksposur media online”.
- Jangan menyebut outlet tier-1 dari ad value saja.
- Jangan mencampur ad value ke social interactions.
- Bila kualitas media penting, gunakan criteria terpisah dan source yang sesuai.

---

# R11 — Priority / Action Matrix

## Tujuan

Membantu klien melihat mana yang perlu ditindak, mana yang dipantau, dan mana yang tidak perlu diamplifikasi.

## Gunakan ketika

- report memiliki beberapa isu/opportunity;
- client perlu prioritas;
- keputusan bukan hanya satu tindakan;
- risk/impact dan evidence dapat dijelaskan dengan jujur.

## Jangan gunakan ketika

- prioritas belum memiliki basis data;
- matrix hanya diisi berdasarkan opini;
- semua item berada pada kuadran yang sama;
- ranking sederhana lebih jelas.

## Struktur visual

Pilihan A:

```text
Table:
Issue / evidence / implication / action
```

Pilihan B:

```text
2x2:
Business relevance
vs
evidence / urgency
```

Pilihan C:

```text
Three lanes:
Act now
Prepare / verify
Monitor only
```

## Input minimum

- list issue/opportunity;
- evidence;
- implication;
- recommended posture/action;
- owner atau condition jika relevant.

## Catatan implementasi

- Pilihan C sering paling mudah dipahami untuk crisis/PR.
- Jangan memberi label risk level tanpa definisi.
- Jangan menempatkan rumor kecil di “Act now” tanpa evidence.
- Jangan membuat 2x2 hanya karena terlihat konsultan.

---

# R12 — Conditional Decision Tree

## Tujuan

Membantu klien memilih respons berdasarkan trigger yang berbeda.

## Gunakan ketika

- action bergantung pada kondisi;
- crisis/PR membutuhkan decision rule;
- brand perlu membedakan kapan bicara dan kapan tidak;
- beberapa scenario sama-sama mungkin terjadi.

## Jangan gunakan ketika

- keputusan sudah tunggal dan sederhana;
- trigger tidak dapat diobservasi;
- tree menjadi terlalu rumit.

## Struktur visual

```text
Trigger / event
    ↓
Question 1
    ├── Yes → action / owner
    └── No  → question 2
                 ├── Yes → action / owner
                 └── No  → monitor / prepare
```

## Input minimum

- trigger;
- criteria decision;
- response option;
- owner;
- escalation path;
- outcome expected.

## Catatan implementasi

- Gunakan kata kerja jelas: klarifikasi, siapkan, verifikasi, eskalasi, jangan amplifikasi.
- Jangan membuat “monitor” sebagai akhir semua cabang tanpa tindakan persiapan.
- Jangan menjadikan tree sebagai pengganti recommendation yang berbasis evidence.

---

# R13 — Operating Plan / Owner Map

## Tujuan

Menutup report dengan tindakan yang dapat dilakukan tim klien.

## Gunakan ketika

- report berakhir pada action;
- beberapa fungsi perlu berkoordinasi;
- owner, timing, dan output perlu jelas.

## Jangan gunakan ketika

- rekomendasi masih generik;
- owner tidak diketahui sama sekali;
- action belum didukung evidence;
- decision tree lebih tepat daripada task list.

## Struktur visual

```text
Priority
Action
Owner
Timing / trigger
Expected output
```

## Input minimum

- action;
- owner;
- reason/evidence;
- timing atau trigger;
- expected output.

## Catatan implementasi

- Maksimal beberapa action paling penting.
- Jangan membuat 10 action dalam satu slide.
- Jangan membuat target angka palsu.
- Tidak semua action harus memiliki deadline; gunakan trigger bila lebih tepat.

---

# R14 — Compact Comparison Table

## Tujuan

Memberikan perbandingan presisi ketika chart tidak cukup.

## Gunakan ketika

- pembaca harus membandingkan beberapa unit di beberapa metric;
- detail penting perlu disimpan di main deck;
- decision membutuhkan angka yang presisi.

## Jangan gunakan ketika

- lebih dari lima sampai tujuh kolom penting;
- pembaca hanya perlu ranking sederhana;
- table menjadi tempat menumpuk seluruh raw data.

## Struktur visual

```text
Rows:
brand / activity / issue / channel / author / media

Columns:
2–4 metric paling relevan
+ one interpretation/status column
```

## Input minimum

- comparable units;
- consistent metric definitions;
- clear sorting;
- scope note.

## Catatan implementasi

- Gunakan satu unit per column; jangan memasukkan views, interactions, ad value, dan buzz tanpa struktur.
- Highlight hanya item yang benar-benar mendukung headline.
- Hindari borders berlebihan.
- Gunakan appendix untuk table lengkap.

---

# R15 — Limitation / Scope Panel

## Tujuan

Mengungkap keterbatasan data tanpa menjadikannya hero slide.

## Gunakan ketika

- coverage materially affects interpretation;
- scope keyword punya kemungkinan false positive;
- actual date range berbeda dari request;
- one metric tidak layak menjadi KPI;
- report perlu menjelaskan apa yang belum dapat disimpulkan.

## Jangan gunakan ketika

- keterbatasan minor yang tidak mengubah pembacaan;
- limitation dipakai untuk menghindari penjelasan penting;
- main deck sudah terlalu penuh.

## Struktur visual

```text
What the data can show
What the data cannot prove
Why it matters
How the report handles it
```

## Input minimum

- limitation;
- affected metric/scope;
- impact on conclusion;
- mitigation / treatment.

## Catatan implementasi

- Bisa berupa small panel pada slide relevant atau appendix.
- Jangan gunakan coverage percentage sebagai angka hero.
- Tidak perlu membuat satu slide khusus jika satu footnote cukup.
- Gunakan jika limitation mengubah level kepastian finding.

---

# R16 — Appendix Evidence Table

## Tujuan

Menyimpan detail audit yang tidak perlu mengganggu main deck.

## Gunakan ketika

- perlu menyediakan source log;
- perlu menampilkan list post/media;
- perlu menjaga auditability;
- client mungkin meminta bukti tambahan.

## Jangan gunakan ketika

- detail penting justru menjadi alasan utama kesimpulan;
- table tidak dapat dibaca bahkan di appendix.

## Struktur visual

```text
Finding / evidence type
Source / URL
Date
Metric
Scope
Note
```

## Input minimum

- source/evidence metadata;
- URL;
- metric;
- scope;
- interpretation note.

## Catatan implementasi

- Appendix harus tetap rapi dan searchable.
- Jangan menyembunyikan finding penting di appendix.
- Gunakan short URL label atau hyperlink, bukan raw URL panjang bila layout terbatas.

---

## 8. Penggunaan cards

Cards bukan dilarang. Cards hanya bukan default otomatis.

### Cards tepat digunakan ketika

- ada dua sampai tiga fakta yang independen;
- pembaca perlu memindai ringkasan cepat;
- tiap card memiliki fungsi berbeda;
- jumlah kata tiap card kecil;
- tidak ada hubungan sebab-akibat kompleks.

### Cards tidak tepat digunakan ketika

- perlu menjelaskan timeline;
- perlu menunjukkan perbandingan;
- perlu menunjukkan akar masalah;
- perlu membuktikan framing;
- perlu menunjukkan distribusi;
- card hanya berisi angka tanpa arti;
- semua slide di deck sudah memakai card grid.

### Aturan card

- Hindari lebih dari tiga card utama.
- Jangan letakkan paragraf panjang dalam card.
- Jangan membuat card sebagai pengganti headline.
- Jangan menggunakan warna berbeda hanya untuk dekorasi.
- Jangan membuat card dengan metric campur-aduk seperti views + ad value + sentiment tanpa struktur.

---

## 9. Penggunaan tables

Table tepat untuk presisi, bukan untuk bercerita.

### Table tepat digunakan ketika

- pembaca perlu membandingkan beberapa unit;
- action/owner perlu terlihat;
- media/author/property perlu dibandingkan;
- detail adalah bagian dari keputusan.

### Table tidak tepat digunakan ketika

- chart dapat menjawab lebih cepat;
- data terlalu banyak;
- audiens executive tidak perlu detail;
- table hanya mengulang angka yang sudah dijelaskan.

### Aturan table

- Maksimal beberapa kolom penting.
- Sort berdasarkan metric/priority yang mendukung headline.
- Gunakan satu interpretation/status column jika perlu.
- Pindahkan detail panjang ke appendix.
- Jangan membuat semua cells memiliki text panjang.

---

## 10. Penggunaan screenshots dan quotes

### Screenshot tepat digunakan ketika

- konten asli adalah bukti;
- framing/wording menjadi inti insight;
- perlu menunjukkan bagaimana publik melihat isu;
- post/statement tertentu memicu spike.

### Screenshot tidak tepat digunakan ketika

- hanya untuk mempercantik slide;
- text tidak terbaca;
- source tidak dapat ditelusuri;
- ada terlalu banyak screenshot kecil.

### Quote tepat digunakan ketika

- satu kalimat benar-benar menjelaskan narasi;
- quote memiliki sumber dan konteks;
- quote tidak disunting sehingga mengubah arti.

### Aturan

Selalu sertakan, setidaknya dalam footer atau source log:

```text
author / outlet
channel
date
URL atau reference ID
metric yang relevan
```

---

## 11. Penggunaan warna dan emphasis

Brand template klien menjadi prioritas.

Jika tidak ada template, gunakan prinsip berikut:

1. Gunakan satu warna utama untuk struktur visual.
2. Gunakan accent hanya untuk highlight yang memiliki arti.
3. Gunakan warna risiko dengan hemat.
4. Jangan menggunakan merah hanya karena angka negatif.
5. Jangan memberi setiap kategori warna berbeda bila kategori dapat dibaca lewat label.
6. Jangan memakai gradien/dekorasi yang tidak menambah makna.
7. Pastikan screenshot, chart, dan callout memiliki hierarchy yang jelas.

### Meaningful color examples

- Highlight issue utama.
- Menandai current period vs baseline.
- Menandai action now vs monitor.
- Menandai positive/neutral/negative sentiment jika memang diperlukan.

Jangan menggunakan warna untuk:

- membedakan semua card;
- menghias chart;
- memberi kesan “lebih premium” tanpa fungsi informasi.

---

## 12. Typography dan density

### Headline

Headline harus menjadi elemen paling mudah dibaca di slide.

### Body copy

Gunakan body copy untuk menjelaskan arti, bukan mengulang angka dari chart.

### Density

Main deck harus memiliki ruang kosong yang cukup agar pembaca tahu:

- di mana harus melihat dulu;
- apa angka utama;
- apa bukti;
- apa implikasinya.

### Hindari

- paragraf panjang;
- font terlalu kecil;
- footnote yang memuat seluruh metodologi;
- table yang memerlukan zoom;
- lima angka besar yang bersaing;
- terlalu banyak icon dekoratif.

Jika detail harus sangat banyak, pindahkan ke appendix.

---

## 13. Urutan visual dalam satu deck

Tidak ada urutan visual wajib.

Namun gunakan ritme yang membantu pembaca:

```text
Answer
→ context or trend
→ evidence
→ implication / priority
→ decision / action
```

Contoh ritme crisis:

```text
Executive answer frame
→ annotated issue trend
→ issue anatomy
→ evidence board
→ priority matrix
→ decision tree / operating plan
```

Contoh ritme competitive:

```text
Executive answer frame
→ comparison ranking
→ concentration diagnostic
→ evidence board
→ whitespace / opportunity visual
→ action plan
```

Contoh ritme campaign:

```text
Executive answer frame
→ performance trend
→ top content evidence
→ concentration diagnostic
→ creator landscape
→ action plan
```

Ritme tersebut hanya contoh. Gunakan storyline sebagai penentu.

---

## 14. Visual anti-patterns

Jangan gunakan pola berikut sebagai default.

### A. KPI card wall

```text
4–6 angka besar tanpa hubungan
```

Masalah:

- pembaca tidak tahu mana yang penting;
- angka berbeda unit terlihat setara;
- tidak ada arti bisnis.

Perbaikan:

- pilih satu metric utama;
- tampilkan bukti pendukung;
- tambahkan implication.

---

### B. Card grid untuk masalah sebab-akibat

```text
Issue
Cause
Risk
Action
```

dalam empat card identik.

Masalah:

- hubungan antar elemen tidak terlihat;
- pembaca harus menebak alurnya.

Perbaikan:

- gunakan issue anatomy;
- gunakan decision tree;
- gunakan action matrix.

---

### C. Chart tanpa takeaway

Masalah:

- pembaca hanya melihat angka;
- presenter harus menjelaskan semua secara lisan;
- slide tidak berdiri sendiri.

Perbaikan:

- gunakan headline answer;
- tambahkan satu annotation;
- tambahkan one-line implication.

---

### D. Tabel sebagai tempat semua data

Masalah:

- tidak ada hierarchy;
- executive tidak tahu apa yang harus dilihat;
- deck tampak seperti export spreadsheet.

Perbaikan:

- gunakan ranking/chart di main deck;
- pindahkan table lengkap ke appendix;
- highlight hanya row yang penting.

---

### E. Screenshots kecil berjajar

Masalah:

- tidak terbaca;
- menjadi dekorasi;
- tidak menjelaskan evidence.

Perbaikan:

- gunakan satu screenshot besar;
- tambah callout;
- gunakan screenshot lain di appendix.

---

### F. Mixed-unit visual

Contoh buruk:

```text
Views + interactions + ad value + buzz
dalam empat cards yang terlihat setara
```

Masalah:

- unit berbeda;
- pembaca dapat menyimpulkan hubungan yang salah.

Perbaikan:

- pisahkan metric;
- beri label jelas;
- gunakan scope dan metric note.

---

### G. Visual yang lebih rumit dari pesannya

Masalah:

- pembaca harus memecahkan visual sebelum memahami finding.

Perbaikan:

- pilih chart/diagram paling sederhana yang masih benar;
- jangan gunakan matrix, waterfall, radar, atau bubble chart tanpa kebutuhan nyata.

---

## 15. Checklist visual sebelum render

Sebelum sebuah slide dibuat, periksa:

### Message

- [ ] Apakah saya tahu satu pesan utama slide?
- [ ] Apakah headline sudah menjawab, bukan hanya memberi nama topik?
- [ ] Apakah visual dipilih karena membantu pesan?

### Evidence

- [ ] Apakah chart/screenshot/table berasal dari data freeze?
- [ ] Apakah scope dan metric basis cukup jelas?
- [ ] Apakah evidence dapat ditelusuri?

### Layout

- [ ] Apakah elemen paling penting terlihat pertama?
- [ ] Apakah body text dapat dibaca?
- [ ] Apakah ada terlalu banyak card/table/number?
- [ ] Apakah visual lebih cepat dipahami daripada dijelaskan?

### Metric labels

- [ ] Apakah interactions dan views dipisahkan?
- [ ] Apakah ad value tidak tercampur dengan social metric?
- [ ] Apakah SOV memiliki basis?
- [ ] Apakah scope/caveat muncul bila diperlukan?

### Client use

- [ ] Apakah slide membantu pembaca membuat keputusan?
- [ ] Apakah slide dapat dipresentasikan tanpa menjelaskan framework internal?
- [ ] Apakah detail teknis sudah dipindahkan ke appendix?

---

## 15.1 R-EVO — visual recipes aktif

Gunakan recipe ini hanya untuk `evo_perception_intelligence`:

| Recipe | Tujuan | Input |
|---|---|---|
| `R-EVO-01` | Brand EVOScore + band interpretation | `qt_evo_brand_summary` |
| `R-EVO-02` | Experience / Values / Offer driver matrix | `qt_evo_driver_scorecard` |
| `R-EVO-03` | Focus Brand vs Best Brand attribute-gap matrix | `qt_evo_attribute_scorecard` |
| `R-EVO-04` | Awareness → Engagement → Perception Impact comparison | `qt_evo_journey_matrix` |
| `R-EVO-05` | Evidence cards with natural source CTA | `ql_evo_evidence_cards` |
| `R-EVO-06` | Scale / Fix / Protect / Build / Test / Monitor / Avoid portfolio | `ql_evo_recommendation_inputs` |

Aturan:

- E/V/O harus dapat dibedakan tanpa mengandalkan warna saja.
- Best Brand tidak boleh memuat focus brand.
- Band harus menampilkan angka dan label: `<90`, `90–110`, `>110`.
- Awareness atau Engagement tidak boleh diberi label Perception Impact.
- Evidence mempertahankan tautan sumber; URL mentah boleh dipindahkan ke CTA.
- No-evidence attribute tetap terlihat sebagai `N/A`/`no evidence`, bukan hilang.

---

## 16. Prinsip terakhir

Jangan bertanya:

> “Layout apa yang bisa dipakai untuk data ini?”

Tanyakan:

> “Apa yang harus dipahami klien setelah melihat slide ini, dan bukti visual apa yang paling cepat membuatnya percaya?”

Visual yang baik tidak membuat report terlihat lebih ramai.

Visual yang baik membuat keputusan terasa lebih jelas.
