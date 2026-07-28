---
name: cogan-metric-and-data-contract
version: 3.2
description: >
  Satu-satunya sumber aturan untuk universe data, canonical post, definisi metrik,
  coverage, raw-metric readiness, perbandingan, metric admission, dan
  rekonsiliasi angka pada report Cogan. File ini harus selaras dengan db.py dan
  server.py versi 3.1.
---

# COGAN METRIC & DATA CONTRACT

## 1. Otoritas file ini

File ini adalah sumber kebenaran tunggal untuk:

- definisi universe data;
- dedup dan canonical post;
- definisi post, interactions, views, sentiment, buzz, SOV, dan ad value;
- coverage dan denominator;
- batas penggunaan metrik di main deck;
- aturan perbandingan;
- rekonsiliasi angka;
- data freeze dan provenance.

File ini **tidak boleh** menentukan:

- storyline report;
- headline;
- rekomendasi;
- urutan slide;
- jumlah slide;
- layout, warna, font, atau desain;
- prompt workflow;
- quality gate editorial.

Gunakan file lain untuk kebutuhan tersebut:

| Kebutuhan | File sumber |
|---|---|
| Cerita, headline, narasi, dan rekomendasi | `skill_report.md` |
| Cara mengambil dan membekukan data dari MCP | `stage_data_cogan.md` |
| Workflow eksekusi report | `system_prompt.md` |
| Pilihan visual | `perpustakaan_resep_slide.md` |
| QA final | `quality_framework.md` |

---

## 2. Prinsip data utama

1. **Satu angka hanya boleh memiliki satu arti.**
2. **Satu metrik hanya boleh memiliki satu rumus dalam satu report.**
3. **Views bukan interactions.**
4. **Interactions tidak boleh disebut “engagement” tanpa definisi.**
5. **Data yang tersedia tidak otomatis layak masuk main deck.**
6. **Post count, metric sum, timeline, coverage, dan top-post harus memakai canonical unique-post layer yang sama.**
7. **Total brand universe tidak boleh dipakai untuk menyimpulkan severity issue-only universe.**
8. **Metrik yang tidak dapat dipahami pembaca non-analis dalam satu kalimat tidak boleh menjadi headline.**
9. **Satu report hanya memakai data yang telah dibekukan dan direkonsiliasi.**
10. **Fakta eksternal tidak boleh disamarkan sebagai angka internal Cogan.**

---

## 2.1 Raw Metric Readiness Gate

Sebelum interactions atau views dipakai sebagai KPI, jalankan:

```text
validate_metric_readiness()
data_health()
```

Urutan ini dilakukan setelah Intent Confirmation disetujui dan sebelum metric
masuk ke `deck_data.json`.

`validate_metric_readiness()` menguji:

- apakah raw header metric ditemukan, dengan canonical header sebagai prioritas;
- apakah fallback alias digunakan;
- apakah nilai angka memakai format yang dapat diparse, termasuk `K`, `M`, dan `B`;
- apakah channel memiliki rumus interactions yang didefinisikan;
- apakah coverage interactions dan views tersedia per channel;
- apakah terdapat channel/raw value yang belum siap dipakai.

### Status readiness

| Status | Perlakuan |
|---|---|
| `PASS` | Lanjut ke `data_health()` dan Metric Admission Rule. |
| `WARN` | Gunakan hanya channel/metric yang lolos guardrail; catat caveat dan downgrade claim bila material. |
| `FAIL` | Jangan gunakan interactions sebagai KPI, SOV basis interactions, atau interaction efficiency sampai raw field, parser, atau mapping channel diperbaiki. |

Aturan:

1. Header Sonar canonical yang diprioritaskan adalah `Likes`, `Comments`,
   `Shares`, `Replies`, `Retweets`, dan `Views`.
2. Alias header hanya fallback kompatibilitas; alias yang terdeteksi harus
   tercatat di diagnostic.
3. Nilai `0` adalah data tersedia jika field mentahnya ada. Blank, `-`, dan
   `N/A` bukan data tersedia.
4. Channel yang belum punya rumus interactions tidak boleh diberi nilai `0`
   lalu ikut ranking lintas channel.
5. `WARN` tidak otomatis berarti metric boleh menjadi KPI utama; guardrail
   coverage pada Section 6 dan Metric Admission Rule tetap berlaku.

---

## 3. Canonical post dan deduplication

### 3.1 Definisi canonical post

Satu canonical post adalah satu post unik dalam satu campaign.

Aturan dedup di database:

```text
Primary key:
- normalized URL bila URL tersedia

Fallback:
- post ID bila URL kosong
```

Artinya:

- satu URL yang muncul berulang di raw data dihitung satu kali;
- post tanpa URL tidak dipaksa digabung dengan post lain;
- dedup dilakukan **sebelum** post count, interactions, views, timeline, coverage, top author, top post, dan media aggregation dihitung.

### 3.2 Memilih row representatif bila URL duplikat

Jika beberapa raw row memiliki URL yang sama dalam campaign yang sama, database memilih satu row representatif dengan urutan:

1. `source_engagement` tertinggi;
2. tanggal post paling baru;
3. ID database paling baru.

`source_engagement` pada aturan ini hanya dipakai untuk memilih row representatif dan audit internal.

`source_engagement` **bukan KPI report client-facing.**

### 3.3 Konsekuensi

Jangan membandingkan:

```text
raw rows
vs
canonical unique posts
```

tanpa label yang jelas.

Seluruh angka report harus memakai canonical unique posts, kecuali slide metodologi sedang menjelaskan duplicate rows yang berhasil dihapus.

---

## 4. Universe data dan scope

Setiap perhitungan wajib punya scope eksplisit.

Scope minimum:

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

### 4.1 Brand universe

Seluruh canonical post yang relevan dengan satu campaign/brand dalam periode dan channel tertentu.

Gunakan untuk:

- konteks kesehatan brand secara umum;
- total percakapan brand;
- proporsi issue terhadap keseluruhan percakapan;
- perubahan brand-level antar periode yang comparable.

Jangan gunakan brand universe untuk menyimpulkan severity issue tertentu.

### 4.2 Issue-only universe

Canonical post yang lolos scope isu tertentu melalui:

- `keywords`;
- `exclude_keywords`;
- `match_mode`;
- channel;
- periode;
- lalu dibaca/diverifikasi lewat `get_posts()` atau raw export.

Gunakan untuk:

- tren isu;
- sentimen isu;
- top content isu;
- aktor penyebar isu;
- volume tuduhan langsung;
- rekomendasi crisis/PR.

Aturan penting:

> Keyword scope adalah saringan teks awal, bukan klasifikasi tema final.

Model/analis tetap wajib membaca konten asli untuk memastikan:

- post memang relevan;
- post tidak sekadar menyebut kata;
- klaim, fakta, rumor, dan komentar dipisahkan;
- istilah yang sama tidak memiliki makna berbeda.

### 4.3 Activity/property universe

Canonical post yang relevan dengan satu campaign, event, sponsorship, partnership, atau aktivitas.

Gunakan untuk:

- evaluasi campaign;
- evaluasi sponsorship;
- performa kreator;
- perbandingan properti;
- keputusan scale, improve, hold, atau stop.

### 4.4 Competitor comparison universe

Set canonical post untuk seluruh brand pembanding dengan:

- periode yang sama;
- channel yang setara;
- query yang setara;
- lifecycle aktivitas yang setara;
- metric basis yang sama.

Gunakan untuk:

- SOV;
- share of interactions;
- perbandingan volume;
- perbandingan narasi;
- competitive scorecard.

### 4.5 Date range

Tanggal akhir bersifat inklusif secara kalender.

Contoh:

```text
start_date = 2025-10-21
end_date   = 2025-10-31
```

berarti seluruh post dari 21 Oktober 00:00 sampai 31 Oktober 23:59:59 ikut dihitung.

---

## 5. Kamus metrik resmi

## 5.1 Posts / Content Count

**Definisi:** jumlah canonical post unik dalam scope.

**Rumus:**

```text
posts = count(canonical unique posts)
```

**Label yang diperbolehkan:**

- post;
- post unik;
- artikel;
- konten;
- percakapan, hanya bila definisinya memang satu post = satu unit percakapan.

**Jangan gunakan:**

- mention, jika yang dihitung sebenarnya URL/post unik;
- raw rows, kecuali untuk audit duplicate data.

---

## 5.2 Interactions

### Definisi

Interactions adalah aksi pengguna terhadap konten sosial, dihitung sesuai capability platform.

Interactions tidak memasukkan views.

### Rumus per channel

| Channel | Rumus interactions |
|---|---|
| Instagram | Likes + Comments |
| Facebook | Likes + Comments + Shares |
| YouTube | Likes + Comments |
| TikTok | Likes + Comments + Shares |
| X / Twitter | Likes + Replies + Retweets |
| Online Media | Tidak berlaku |
| Channel lain | Tidak berlaku sampai ada definisi eksplisit |

### Aturan penting

1. Views tidak masuk interactions.
2. Saves tidak dimasukkan karena belum tersedia dalam standard raw data saat ini.
3. Interactions dihitung hanya bila seluruh field yang diwajibkan channel tersedia.
4. Nilai `0` tetap dianggap data tersedia bila field mentahnya ada dan tidak kosong.
5. Field tidak tersedia berbeda dari nilai `0`.
6. Online media tidak memiliki interactions dan tidak boleh dipaksa menjadi nol untuk tujuan ranking lintas channel.
7. Gunakan istilah `interactions` pada output report dan deck, bukan `engagement`, kecuali user secara eksplisit meminta “engagement” lalu definisinya dijelaskan sebagai interactions.

### Label client-facing yang dianjurkan

- “interactions”
- “interaksi pengguna”
- “aksi pengguna terhadap konten”

### Total interactions lintas channel

Total interactions lintas channel boleh digunakan sebagai **jumlah platform-native interactions** bila:

- channel yang masuk dijelaskan;
- online media tidak dicampurkan;
- interaction coverage memadai;
- tidak dipakai untuk membandingkan kualitas aksi antar platform secara langsung.

Gunakan wording:

> “Konten sosial dalam scope ini menghasilkan X platform-native interactions.”

Jangan gunakan wording:

> “X engagement lintas kanal membuktikan kualitas konten lebih baik.”

---

## 5.3 Views / Plays

### Definisi

Jumlah tayangan video atau konten ketika field views tersedia.

**Rumus:**

```text
views = sum(Views pada canonical posts yang memiliki field Views)
```

### Aturan penting

1. Views bukan interactions.
2. Views tidak boleh dijumlahkan sebagai likes, comments, shares, replies, atau retweets.
3. Views menunjukkan exposure/tayangan, bukan aksi pengguna.
4. Views lintas platform hanya boleh dibandingkan bila scope dan definisi views setara atau diberi label channel.
5. Jika coverage views rendah, total views hanya dibaca directional.
6. Online media tidak boleh diperlakukan seolah memiliki views sosial.

### Label client-facing yang dianjurkan

- “views”
- “tayangan”
- “video views”
- “plays”

Contoh benar:

> Video eksposé mencapai 42,2 juta views.

Contoh salah:

> Video eksposé menghasilkan 42,2 juta engagement.

---

## 5.4 Source Engagement — Diagnostic Only

### Definisi

`source_engagement` adalah nilai dari kolom source lama `posts.engagement`.

Nilai ini dapat memiliki definisi yang tidak konsisten antar channel atau dataset.

### Status

```text
DIAGNOSTIC ONLY
```

### Boleh digunakan untuk

- memilih row representatif ketika URL duplikat;
- audit kualitas source data;
- memeriksa perbedaan antara nilai source dan interactions hasil rumus resmi;
- appendix teknis jika definisi source telah diverifikasi.

### Tidak boleh digunakan untuk

- cover;
- executive summary;
- KPI utama;
- headline;
- ranking client-facing;
- SOV;
- comparison utama;
- recommendation;
- decision slide.

---

## 5.5 Average Interactions per Applicable Post

### Definisi

Rata-rata interactions per post pada channel yang memiliki rumus interactions.

**Rumus:**

```text
average interactions per applicable post
= total interactions / total posts pada channel interactions-applicable
```

### Gunakan hanya bila

- interaction coverage pada post applicable memadai;
- universe pembanding setara;
- outlier tidak mendominasi;
- pembaca memang perlu melihat efisiensi rata-rata, bukan hanya total volume.

### Jangan gunakan bila

- satu post viral mendominasi total;
- interaction coverage rendah;
- channel mix antar brand berbeda jauh;
- online media dicampurkan;
- ukuran sampel kecil.

Jika outlier kuat, gunakan:

- median sebagai analisis internal;
- distribusi;
- top-post share;
- atau narasi “ditopang satu post”.

---

## 5.6 Interaction Rate

### Definisi

Rasio interactions terhadap views.

**Rumus:**

```text
interaction rate = interactions / views × 100
```

### Boleh digunakan hanya jika

1. interactions dan views tersedia pada post/channel yang sama;
2. coverage kedua field memadai;
3. perbandingan dilakukan dalam platform yang sama;
4. scope content setara;
5. denominator views bukan hasil gabungan channel dengan definisi berbeda.

### Tidak boleh digunakan sebagai KPI lintas-platform universal.

Interaction rate tidak perlu ditampilkan jika hanya menambah angka tanpa mengubah keputusan.

---

## 5.7 Buzz

### Definisi

Proxy volume/reach yang disediakan sumber data.

**Rumus:**

```text
buzz = sum(Buzz pada canonical posts)
```

### Aturan

1. Buzz bukan views.
2. Buzz bukan interactions.
3. Buzz tidak boleh dijumlahkan dengan interactions.
4. SOV berbasis buzz harus dilabelkan secara eksplisit.
5. Bila coverage buzz rendah, jangan gunakan sebagai basis ranking absolut.

---

## 5.8 Share of Voice

### Definisi

Proporsi metric sebuah brand dibanding total metric seluruh brand pembanding.

**Rumus:**

```text
share = metric brand / total metric semua brand pembanding × 100
```

### Basis yang diperbolehkan

- `posts`
- `buzz`
- `interactions`

### Aturan

1. Basis metric wajib ditulis.
2. Satu visual SOV hanya boleh memakai satu basis utama.
3. Jangan menyebut hanya “SOV” tanpa basis.
4. SOV tidak otomatis berarti reputasi baik, kualitas narasi tinggi, atau efektivitas bisnis.
5. Jika satu post terdaftar di beberapa campaign, overlap dapat terjadi. Beri caveat bila relevan.
6. SOV berbasis interactions hanya boleh digunakan bila interaction coverage dan channel mix antar brand memadai.

### Label contoh

- “Share of Voice berdasarkan post”
- “Share of Voice berdasarkan buzz”
- “Share of Interactions”

---

## 5.9 Sentiment Share — By Count

### Definisi

Proporsi post positif, netral, dan negatif dari post yang memiliki klasifikasi sentimen.

**Rumus:**

```text
sentiment share
= jumlah post dengan label sentimen / total classified posts × 100
```

### Aturan denominator

1. Post tanpa sentiment valid dikeluarkan dari denominator.
2. Denominator selalu `classified_posts`, bukan total post.
3. Persentase positif + netral + negatif harus berjumlah 100,0% ± 0,1% karena rounding.
4. Coverage sentiment harus ditampilkan atau tersedia dalam data freeze.

### Label

- “sentimen berdasarkan jumlah post”
- “positive / neutral / negative share”
- “sentiment by count”

---

## 5.10 Net Sentiment — By Count

### Definisi

Keseimbangan sentimen berdasarkan jumlah post terklasifikasi.

**Rumus:**

```text
net sentiment by count
= % positif − % negatif
```

### Boleh digunakan bila

- sentiment coverage ≥ 80%;
- universe jelas;
- top content sudah diperiksa agar tidak ada mismatch besar;
- metrik benar-benar membantu pembaca memahami arah percakapan.

### Tidak boleh digunakan sebagai satu-satunya indikator risiko.

### Label wajib

```text
net sentiment (by count)
```

---

## 5.11 Net Sentiment — Interaction-Weighted

### Definisi

Keseimbangan sentimen yang dibobot berdasarkan interactions.

**Rumus:**

```text
net sentiment interaction-weighted
= (interactions positif − interactions negatif)
  / total interactions
  × 100
```

### Status

```text
DIAGNOSTIC ONLY
```

### Tidak boleh muncul pada

- cover;
- executive summary;
- headline;
- KPI utama;
- recommendation;
- decision slide;
- client-facing scorecard.

### Boleh muncul hanya dalam appendix teknis bila seluruh syarat terpenuhi

1. interaction coverage ≥ 60% pada post/channel applicable;
2. top 20 content berdasarkan interactions atau views sudah diperiksa manual;
3. tidak ada mismatch sentimen material pada top content;
4. channel comparison cukup setara;
5. label `interaction-weighted` ditulis lengkap.

Jika salah satu syarat gagal, jangan hitung atau tampilkan metrik ini.

---

## 5.12 Ad Value

### Definisi

Nilai eksposur earned media online sesuai field sumber data.

**Rumus:**

```text
ad value = sum(Ad Value pada canonical media posts)
```

### Gunakan untuk

- konteks eksposur media online;
- ranking outlet berdasarkan ad value;
- distribusi nilai pemberitaan.

### Jangan gunakan untuk menyimpulkan

- kualitas jurnalisme;
- tier media;
- kredibilitas outlet;
- engagement;
- views;
- tingkat krisis;
- dampak bisnis;
- keberhasilan komunikasi secara otomatis.

### Label wajib

- “ad value media online”
- “nilai eksposur media online”

---

## 5.13 PR Value

### Definisi

Nilai PR sesuai field sumber data.

### Status

Contextual metric only.

Jangan gunakan tanpa memahami definisi provider/source dataset.

---

## 5.14 Topic / Issue Volume

### Definisi

Jumlah canonical post dalam scope issue atau tema tertentu.

### Aturan

1. Tema harus divalidasi melalui pembacaan post atau coding.
2. Keyword scope saja tidak cukup untuk menyatakan topik final.
3. Satu post dapat masuk lebih dari satu tema bila metode overlap dijelaskan.
4. Tema overlap tidak boleh dijumlahkan sebagai total tanpa footnote.
5. Gunakan issue-only universe untuk semua klaim tentang ukuran isu.

### Label yang dianjurkan

- “post membahas [isu]”
- “konten terkait [isu]”
- “percakapan tentang [isu]”

---

## 6. Coverage dan denominator

## 6.1 Coverage harus selalu tersedia

Setiap data freeze harus menyimpan:

- total canonical unique posts;
- raw rows dalam scope;
- duplicate rows removed;
- sentiment classified posts;
- interactions-applicable posts;
- interactions-available posts;
- views-available posts;
- buzz-available posts;
- ad-value-available posts;
- channel breakdown;
- actual date range.

## 6.2 Definisi coverage

### A. Sentiment classification coverage

```text
sentiment coverage
= classified posts / canonical unique posts × 100
```

### B. Interaction coverage

```text
interaction coverage
= interactions-available posts / interactions-applicable posts × 100
```

Denominator hanya post pada channel yang memiliki rumus interactions.

Online media tidak masuk denominator interaction coverage.

### C. Views coverage

```text
views coverage
= views-available posts / canonical unique posts × 100
```

### D. Availability bukan nilai positif

Jangan memakai:

```text
interactions > 0
views > 0
```

sebagai definisi availability.

Post dengan nilai `0` tetap dapat dianggap field tersedia bila field mentahnya memang ada.

---

## 6.3 Default guardrail

| Kondisi | Perlakuan |
|---|---|
| n < 30 | Gunakan wording directional dan tampilkan n bila menjadi dasar klaim |
| Sentiment coverage < 80% | Sentiment hanya directional; jangan jadi headline utama |
| Interaction coverage < 60% | Total/average interactions tidak boleh menjadi KPI utama |
| Views coverage < 60% | Total views hanya contextual/directional; jangan dipakai untuk klaim absolut universe |
| Top content sentiment mismatch | Sentiment aggregate tidak boleh menjadi headline |
| Channel mix tidak sebanding | Jangan buat ranking lintas channel tanpa caveat |
| Satu post mendominasi metric | Jangan simpulkan pola performa tanpa menyebut outlier |
| Scope issue hanya berbasis keyword | Wajib baca post untuk validasi sebelum membuat klaim final |

Threshold dapat diubah hanya jika alasan, scope, dan dampaknya dicatat pada data freeze.

---

## 7. Metric Admission Rule

Sebuah metrik hanya boleh masuk **main deck** jika seluruh syarat ini terpenuhi:

1. Pembaca non-analis dapat memahami artinya dalam satu kalimat.
2. Metrik menjawab pertanyaan bisnis atau membantu keputusan.
3. Definisi dan denominator konsisten.
4. Coverage memenuhi guardrail.
5. Metrik tidak bertentangan dengan pembacaan manual top content.
6. Metrik tidak mencampurkan views, interactions, buzz, ad value, atau source engagement.
7. Metrik tidak memerlukan penjelasan teknis panjang agar bermakna.
8. Scope universe ditulis atau jelas dari konteks slide.
9. Perbandingan dilakukan pada unit yang comparable.
10. Angka tersedia di data freeze dan telah lolos rekonsiliasi.
11. `validate_metric_readiness()` tidak berstatus `FAIL`; bila `WARN`, caveat
    dan channel/metric exclusion telah dicatat.

Jika satu syarat gagal:

- pindahkan ke appendix;
- ubah menjadi caveat metodologi;
- gunakan sebagai diagnostic internal;
- atau hapus dari report.

---

## 8. Aturan khusus issue dan crisis report

## 8.1 Issue Universe Gate

Setiap klaim tentang risiko isu harus memakai issue-only universe.

Contoh benar:

> Dari 6.809 post yang lolos scope “sumur bor”, “akuifer”, dan “mata air”, X% memuat tuduhan bahwa AQUA menyesatkan konsumen.

Contoh salah:

> Dari 16.358 percakapan AQUA, isu sumur bor adalah krisis besar.

Jika total brand universe dipakai, gunakan hanya sebagai konteks:

> Isu sumur bor mencakup 6.809 dari 16.358 post percakapan AQUA dalam periode analisis.

## 8.2 Direct allegation vs association

Jangan samakan:

- brand disebut;
- brand diasosiasikan;
- brand dituduh langsung;
- brand menjadi target tuntutan;
- brand menerima permintaan klarifikasi regulator.

Setiap status harus memiliki bukti:

| Status | Bukti minimum |
|---|---|
| Tidak ditemukan dalam scope | Query/scope dan periode dijelaskan |
| Ada asosiasi | Jumlah post + contoh post |
| Ada tuduhan langsung | Jumlah post + kutipan + sumber |
| Risiko meningkat | Tren naik + konten pemicu + sumber relevan |
| Belum terukur | Tulis “belum terukur”, jangan beri label pasti |

## 8.3 Rumor kecil

Rumor kecil tidak otomatis menjadi prioritas.

Rumor boleh disebut sebagai watchlist jika:

- volumenya terukur;
- ada tren naik;
- ada aktor/sumber relevan;
- ada potensi nyata memengaruhi keputusan klien.

Jika tidak, simpan sebagai appendix atau internal watchlist. Jangan memberi respons publik yang justru memperbesar rumor.

---

## 9. Aturan perbandingan

Perbandingan hanya valid bila unit yang dibandingkan setara.

Periksa:

- periode;
- scope keyword;
- channel;
- lifecycle aktivitas;
- coverage;
- sample size;
- jenis akun;
- definisi metric;
- status canonical dedup.

### Perbandingan yang tidak boleh dilakukan langsung

- TikTok views vs Instagram interactions;
- online media ad value vs social interactions;
- pre-event sponsorship vs post-event sponsorship;
- satu post viral vs total campaign;
- total brand sentiment vs issue-only sentiment;
- interaction coverage 90% vs 15% tanpa caveat;
- SOV posts vs SOV buzz dalam satu grafik;
- interactions total pada channel mix yang sangat berbeda tanpa label.

Jika tidak setara, lakukan salah satu:

- pisahkan unit;
- beri label lifecycle;
- ubah menjadi directional;
- gunakan satu channel;
- atau jangan bandingkan.

---

## 10. Evidence dan provenance

### 10.1 Internal evidence

Angka internal, ranking, post, author, URL, sentiment, channel, dan metric hanya boleh berasal dari:

- Cogan MCP;
- raw data klien;
- coding yang terdokumentasi.

### 10.2 Public evidence

Fakta seperti:

- hukum;
- regulator;
- keselamatan;
- kesehatan;
- kepemilikan;
- statement resmi;
- benchmark;
- keputusan pemerintah;

harus berasal dari sumber eksternal yang dapat diverifikasi.

### 10.3 Social content

Post sosial boleh membuktikan:

- persepsi;
- framing narasi;
- komentar publik;
- tuntutan;
- konten viral;
- pola percakapan.

Post sosial tidak boleh menjadi satu-satunya bukti untuk menetapkan:

- fakta hukum;
- penyebab kecelakaan;
- tanggung jawab resmi perusahaan;
- keputusan regulator;
- diagnosis kesehatan;
- klaim keselamatan produk.

---

## 11. Data freeze dan rekonsiliasi

Sebelum headline, narasi, atau desain deck dibuat, simpan data freeze.

### 11.1 Field minimum data freeze

```json
{
  "contract_version": "3.2",
  "data_freeze_timestamp": "ISO-8601",
  "project_name": "Nama campaign",
  "scope": {
    "universe": "brand | issue_only | activity_property | competitor_comparison",
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "channels": [],
    "keywords": [],
    "exclude_keywords": [],
    "match_mode": "any | all"
  },
  "data_health": {
    "n_posts_unique": 0,
    "n_rows_raw": 0,
    "duplicate_rows_removed": 0,
    "coverage_percent": {}
  },
  "metrics": {},
  "reconciliation": {
    "overall_status": "PASS | FAIL",
    "checks": []
  }
}
```

### 11.2 Rekonsiliasi wajib

Sebelum report dirender, cek dengan kode:

1. **Canonical integrity**
   - total post = canonical unique posts;
   - raw rows dan duplicate rows disclosed.

2. **Sum-of-parts**
   - channel breakdown = total posts;
   - positive + neutral + negative + unclassified = total posts;
   - sentiment shares = 100% ± rounding;
   - SOV = 100% ± rounding.

3. **Metric integrity**
   - interactions tidak termasuk views;
   - online media tidak memiliki interactions;
   - source engagement tidak dipakai sebagai KPI;
   - ad value tidak dipakai sebagai engagement.

4. **Coverage integrity**
   - interaction coverage denominator = interactions-applicable posts;
   - views coverage denominator = canonical posts;
   - availability tidak dihitung dari nilai >0.

5. **Universe integrity**
   - issue-only metric tidak dicampur dengan total brand metric tanpa label;
   - period/channel/keyword scope sama pada comparison.

6. **Narrative integrity**
   - semua angka pada headline, cover, recommendation, dan decision tersedia pada data freeze.

Jika rekonsiliasi gagal, report tidak boleh masuk render final.

---

## 12. Larangan metrik dan presentasi yang membingungkan

Jangan tampilkan di main deck:

- `source_engagement`;
- net sentiment interaction-weighted;
- views yang disebut interactions;
- interactions yang disebut views;
- ad value yang disebut engagement;
- ad value yang disebut media tier-1;
- ratio mentah tanpa makna bisnis, misalnya `6.809 : 1.996`;
- coverage sebagai headline;
- total brand universe untuk membuktikan severity issue;
- rata-rata yang ditopang satu outlier tanpa caveat;
- target sentimen/media yang tidak dapat dikendalikan klien;
- composite score tanpa definisi jelas;
- metrik yang perlu lebih dari satu kalimat teknis untuk dimengerti.

Gunakan bentuk yang lebih manusiawi.

| Hindari | Gunakan |
|---|---|
| `+36 net sentiment engagement-weighted` | “Sentimen agregat tidak dipakai sebagai KPI utama karena konten terbesar perlu diverifikasi manual.” |
| `1 dari 4 post memiliki engagement` | “Data interactions tersedia pada X% post sosial yang memiliki rumus interaction.” |
| `6.809 : 1.996` | “Percakapan isu tiga kali lebih banyak daripada konten yang memuat respons resmi brand.” |
| `42,2 juta engagement` | “42,2 juta views.” |
| `Rp3,6 miliar media tier-1` | “Rp3,6 miliar ad value media online.” |

---

## 13. MCP tool mapping

Gunakan tool berikut sesuai kebutuhan dan jangan memaksa satu tool menjawab semua pertanyaan.

| Kebutuhan | Tool MCP |
|---|---|
| Cek data tersedia dan periode | `find_project()` |
| Cek canonical count, coverage, dedup | `data_health()` |
| Total post, channel, sentiment by count | `count_posts()` |
| Interactions dan views per channel | `metrics_summary()` |
| Tren harian | `timeline()` |
| Deteksi puncak/anomali | `detect_spikes()` |
| Baca post asli dan validasi tema | `get_posts()` |
| Bukti konten tertinggi | `top_viral_posts()` |
| Akun/author penggerak | `top_authors()` |
| Outlet media online | `top_media()` |
| Perbandingan periode | `compare_periods()` |
| Perbandingan campaign | `compare_campaigns()` |
| SOV dengan basis eksplisit | `share_of_voice()` |
| Audit/coding manual | `export_raw_data()` |

Gunakan `data_health()` sebelum memakai metrik utama report.

Gunakan `get_posts()` setelah melihat anomaly, spike, top post, atau keyword issue scope.

---

## 14. Versioning

Naikkan `contract_version` bila ada perubahan pada:

- canonical dedup rule;
- rumus interactions per channel;
- definisi views;
- denominator coverage;
- metric admission rule;
- threshold guardrail;
- universe/scope rule;
- formula SOV;
- aturan rounding.

Jangan naikkan version hanya karena:

- perubahan storyline;
- layout;
- warna;
- font;
- copywriting;
- urutan slide.

Setiap report final wajib menyimpan:

```text
contract_version
data_freeze_timestamp
project_name
scope
actual_date_range
data_health
reconciliation_status
```

---

## 14.1 EVO Perception Intelligence metric addendum

Metric berikut aktif untuk `evo_perception_intelligence` dan hanya boleh
dihitung dari canonical post yang memiliki row-level attribute tag tersimpan:

| Metric | Formula | Grain | Guardrail |
|---|---|---|---|
| EVO Share | `driver tagged posts / brand tagged posts × 100` | brand × driver | E+V+O = 100% ±0.1 atau residual dijelaskan |
| Driver Net Sentiment | `(%positive - %negative)` berbasis count | brand × driver | unclassified tidak dipaksa menjadi neutral |
| Sentiment Index | `brand sentiment point / category sentiment point × 100`; sentiment point=`(net+100)/2` | brand × driver | category-centred |
| Virality Index | `brand average interactions / category average interactions × 100` | brand × driver | interactions terpisah dari views |
| Total Driver Score | mean dari Sentiment Index dan Virality Index yang tersedia | brand × driver | formula dibekukan di Task 1 |
| EVOScore | mean Total Driver Score across E/V/O yang tersedia | brand | missing driver wajib menjadi limitation |
| Attribute Score | `(attribute net sentiment + 100) / 2` berbasis count | brand × attribute | hanya row-level tagged posts |
| Best Brand | Attribute Score tertinggi di antara non-focus brands | attribute | focus brand wajib dikeluarkan |
| Attribute Gap | `Best Brand Score - focus Attribute Score` | attribute | score basis harus sama |
| Whitespace | `Best Brand Score > 0` dan `focus Attribute Score = 0` | attribute | no-evidence tetap ditampilkan |

Interpretasi index category-centred:

```text
Underperform < 90
On Par       90–110 (inklusif)
Outperform  > 110
```

Task 2 hanya membaca nilai beku dari `report_input_v1`; renderer tidak boleh
menghitung ulang metric EVO.

---

## 15. Prinsip terakhir

Metrik yang baik bukan metrik yang paling banyak atau paling rumit.

Metrik yang baik adalah metrik yang:

1. benar;
2. mempunyai definisi jelas;
3. memakai universe dan denominator yang tepat;
4. cukup lengkap coverage-nya;
5. tidak mencampurkan interactions dengan views;
6. tidak menyesatkan pembaca;
7. membantu klien membuat keputusan.
