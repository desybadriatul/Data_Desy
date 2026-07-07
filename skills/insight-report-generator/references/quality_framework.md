---
name: cogan-report-quality-framework
version: 3.1
description: >
  Gerbang mutu final untuk report Cogan. File ini menguji apakah data, evidence,
  storyline, rekomendasi, visual, dan delivery sudah layak dikirim ke klien.
  File ini tidak membuat formula metric, narasi, layout, atau workflow baru.
---

# COGAN REPORT QUALITY FRAMEWORK

## 1. Otoritas file ini

File ini adalah quality gate terakhir sebelum report dikirim.

Gunakan file ini untuk:

- memeriksa kebenaran data;
- memeriksa scope dan coverage;
- memeriksa evidence dan claim;
- memeriksa kualitas storyline;
- memeriksa rekomendasi dan decision;
- memeriksa visual deck;
- menentukan status final: `PASS`, `PASS WITH NOTES`, atau `FAIL`.

File ini **tidak boleh** membuat aturan baru tentang:

- formula metrik;
- canonical dedup;
- definisi interactions, views, sentiment, SOV, atau ad value;
- urutan proses pengambilan data;
- storytelling framework;
- layout atau resep visual;
- wording headline spesifik.

Gunakan file sumber berikut saat audit:

| Yang diaudit | Sumber aturan |
|---|---|
| Metrik, scope, coverage, denominator, data freeze | `consistency_contract.md` |
| Penggunaan tool dan evidence collection | `stage_data_cogan.md` |
| Storyline, bahasa, headline, dan rekomendasi | `skill_report.md` |
| Urutan proses report | `system_prompt.md` |
| Visual/layout | `perpustakaan_resep_slide.md` |
| Router/otoritas dokumen | `SKILL.md` |

---

## 2. Prinsip quality gate

Quality gate tidak bertujuan membuat report terlihat “lebih lengkap”.

Quality gate bertujuan memastikan report:

1. benar;
2. jelas;
3. dapat ditelusuri;
4. tidak melebih-lebihkan evidence;
5. membantu keputusan;
6. layak ditunjukkan ke klien.

Prinsip utama:

> Report yang rapi tetapi tidak valid adalah gagal.  
> Report yang valid tetapi membingungkan adalah belum siap.  
> Report yang cantik tetapi tidak membantu keputusan adalah belum selesai.

---

## 3. Status kelulusan

### PASS

Semua hard gate lulus.

Report dapat dikirim ke klien tanpa perubahan material.

### PASS WITH NOTES

Tidak ada hard failure, tetapi ada caveat minor yang:

- sudah dijelaskan pada slide/appendix bila relevan;
- tidak mengubah kesimpulan utama;
- tidak membuat claim menjadi misleading.

Contoh:

- one decimal rounding membuat total 99,9%;
- satu metric dipindah ke appendix karena coverage sedang;
- beberapa source link tambahan tersedia di appendix.

### FAIL

Ada hard failure atau masalah material.

Report tidak boleh dikirim sebelum diperbaiki.

---

## 4. Cara menjalankan audit

Lakukan audit pada urutan berikut:

```text
A. Data correctness
B. Scope and metric integrity
C. Evidence and claim integrity
D. Storyline and decision usefulness
E. Recommendation integrity
F. Visual and delivery quality
```

Jangan mulai dari visual.

Jika A atau B gagal, jangan melanjutkan ke tahap berikutnya sebelum masalah data diperbaiki.

---

# A. DATA CORRECTNESS

## A1. Data freeze tersedia

### Test

Pastikan ada `deck_data.json` atau artifact data freeze setara.

Minimal harus memuat:

```text
contract_version
project_name
report type
data freeze timestamp
scope
data health
metric output
evidence post/source
limitations
reconciliation status
```

### PASS bila

- semua angka main deck dapat ditemukan di data freeze;
- semua scope terdokumentasi;
- file data freeze merupakan versi final yang dipakai untuk render.

### FAIL bila

- angka disalin manual tanpa sumber;
- deck memakai angka yang tidak ada di data freeze;
- ada lebih dari satu versi angka tanpa penjelasan;
- tidak jelas angka mana yang menjadi sumber final.

---

## A2. Reconciliation PASS

### Test

Pastikan `reconciliation.overall_status = PASS`.

Minimum pemeriksaan:

```text
channel post breakdown = total canonical posts
sentiment counts + unclassified = total canonical posts
sentiment share = 100% ± rounding
SOV = 100% ± rounding
headline numbers ada di data freeze
```

### PASS bila

- seluruh check lulus;
- rounding difference terdokumentasi dan kecil;
- overlap topic diberi footnote bila relevan.

### FAIL bila

- chart dan tabel memakai angka berbeda;
- total tidak sesuai dengan sum-of-parts;
- headline number tidak dapat ditelusuri;
- SOV tidak menjumlah 100% tanpa alasan;
- narrative memakai angka dari scope yang berbeda.

---

## A3. Canonical post integrity

### Test

Pastikan report memakai canonical unique-post layer.

Periksa:

```text
n_posts_unique
n_rows_raw
duplicate_rows_removed
```

### PASS bila

- total post berasal dari canonical unique posts;
- metric sum/timeline/top post juga memakai canonical layer;
- duplicate row tidak dihitung ganda.

### FAIL bila

- post count memakai unique URL tetapi metric sum memakai raw rows;
- raw rows dipakai sebagai total post tanpa label;
- duplicate data membuat interactions/views/ad value dihitung dua kali;
- raw export dan deck count tidak dapat direkonsiliasi.

---

## A4. Actual date range

### Test

Bandingkan:

```text
requested date range
actual date range
```

### PASS bila

- actual range sesuai request;
- jika data lebih pendek, gap dinyatakan;
- tanggal akhir dihitung inklusif.

### FAIL bila

- deck menyatakan periode yang tidak tersedia;
- chart mencakup tanggal di luar scope;
- perbandingan memakai periode dengan panjang berbeda tanpa caveat;
- tanggal akhir tidak termasuk karena query cutoff.

---

# B. SCOPE AND METRIC INTEGRITY

## B1. Scope integrity

### Test

Setiap chart, table, headline number, dan evidence penting harus memiliki scope yang jelas.

Scope minimum:

```text
universe
period
channel
keywords
exclude keywords
match mode
```

### PASS bila

- brand universe dan issue-only universe dipisahkan;
- scope comparison setara;
- keyword scope yang dipakai dicatat;
- slide tidak mencampur scope tanpa label.

### FAIL bila

- total brand universe dipakai untuk menyimpulkan severity issue-only;
- issue-only trend dibanding brand-level baseline;
- satu chart memakai channel tertentu tetapi headline menyebut semua channel;
- keyword scope berubah antar slide tanpa penjelasan;
- user tidak dapat mengetahui basis angka.

---

## B2. Interactions and views separation

### Test

Periksa seluruh deck dan appendix untuk istilah:

```text
interactions
views
engagement
source engagement
```

### PASS bila

- interactions dan views selalu dipisahkan;
- views tidak dijumlahkan sebagai interactions;
- interactions mengikuti formula per channel;
- istilah “engagement” tidak dipakai ambigu;
- online media tidak dipaksa memiliki interactions.

### FAIL bila

- “42 juta engagement” sebenarnya adalah views;
- interactions disebut views;
- likes/comments/shares/replies/retweets tidak mengikuti channel formula;
- ad value dicampur dengan interactions;
- `source_engagement` muncul sebagai KPI client-facing.

---

## B3. Coverage integrity

### Test

Periksa coverage untuk metric utama.

Minimum yang dicek:

```text
sentiment classification coverage
interaction coverage of applicable posts
views coverage of canonical posts
buzz coverage
ad value coverage
```

### PASS bila

- denominator coverage benar;
- metric utama memenuhi threshold di `consistency_contract.md`;
- coverage rendah diberi caveat/downgrade;
- zero metric tidak disalahartikan sebagai field tidak tersedia.

### FAIL bila

- interaction coverage dihitung dari semua post termasuk online media;
- views coverage dihitung dari interactions > 0;
- coverage rendah tetapi metric jadi cover KPI;
- coverage tidak diketahui;
- wording claim lebih kuat daripada coverage data.

---

## B4. Sentiment integrity

### Test

Periksa:

- sentiment basis;
- sentiment coverage;
- top-content validation;
- wording claim.

### PASS bila

- sentiment dipresentasikan sebagai `by count` bila digunakan;
- denominator classified post;
- top content yang material sudah dibaca;
- mismatch material sudah dicatat;
- sentiment tidak menjadi satu-satunya indikator risiko.

### FAIL bila

- net sentiment interaction-weighted muncul di main deck;
- post tidak terklasifikasi masuk denominator;
- top post salah label tetapi aggregate sentiment tetap jadi headline;
- wording “publik positif” hanya berasal dari sentiment score;
- sentiment brand universe dipakai untuk menyimpulkan sentiment issue-only.

---

## B5. Comparison integrity

### Test

Untuk setiap comparison, periksa:

```text
period
scope keyword
channel
lifecycle
sample size
metric definition
coverage
outlier concentration
```

### PASS bila

- unit yang dibandingkan setara;
- basis metric jelas;
- caveat diberikan bila ada perbedaan penting;
- outlier tidak disamarkan sebagai pola.

### FAIL bila

- TikTok views dibanding Instagram interactions;
- ad value dibanding social interactions;
- pre-event dibanding post-event tanpa label;
- satu post viral dipakai untuk menyimpulkan campaign lebih unggul;
- coverage antar brand jauh berbeda tanpa caveat;
- SOV basis berubah antar chart.

---

## B6. Ad value and media integrity

### Test

Periksa semua penggunaan:

```text
ad value
PR value
top media
media tier
```

### PASS bila

- ad value dilabelkan sebagai nilai eksposur media online;
- ranking media menyebut articles + ad value bila relevan;
- kualitas/credibility media tidak disimpulkan dari ad value saja.

### FAIL bila

- ad value disebut engagement;
- ad value disebut views;
- ad value dipakai sebagai bukti tier-1;
- ad value dicampur ke total social interactions;
- satu outlet disebut paling kredibel hanya karena nilai tinggi.

---

# C. EVIDENCE AND CLAIM INTEGRITY

## C1. Claim-to-evidence mapping

### Test

Setiap claim penting di main deck harus punya evidence yang dapat ditelusuri.

Minimum evidence mapping:

```text
claim
scope
metric/evidence type
source tool/source link
numerator
denominator bila ada
date range
limitation
```

### PASS bila

- claim utama memiliki evidence ID atau source log;
- angka dapat ditemukan lagi;
- quote dapat dikembalikan ke source;
- evidence sesuai dengan claim.

### FAIL bila

- headline hanya opini model;
- angka tidak jelas asalnya;
- quote tanpa source;
- screenshot tanpa identitas/URL;
- source tidak mendukung klaim yang dibuat.

---

## C2. Social content evidence

### Test

Periksa cara post sosial digunakan.

### PASS bila

- post sosial dipakai untuk menunjukkan persepsi, framing, tuntutan, atau percakapan;
- post memiliki date, author/channel, content, URL, dan metric yang relevan;
- konten dibaca sebelum disimpulkan;
- screenshot/post evidence dipakai secara proporsional.

### FAIL bila

- post sosial menjadi satu-satunya bukti hukum, regulator, keselamatan, kesehatan, atau tanggung jawab resmi;
- satu post dipakai untuk menggeneralisasi seluruh publik tanpa volume/trend;
- screenshot tidak dapat ditelusuri;
- content evidence dipotong sehingga mengubah makna.

---

## C3. External facts and sensitive claims

### Test

Periksa semua claim terkait:

```text
regulator
legal
safety
health
financial impact
ownership
official statement
government decision
competitor fact
```

### PASS bila

- claim didukung sumber primer, regulator, official statement, atau outlet kredibel;
- source eksternal dipisahkan dari data Cogan;
- level kepastian sesuai kualitas evidence.

### FAIL bila

- claim sensitif berasal hanya dari komentar sosial;
- rumor diperlakukan sebagai fakta;
- statement tidak diverifikasi;
- source tidak cukup untuk dampak claim;
- report menyatakan legal conclusion tanpa dasar.

---

## C4. Fact, claim, perception, and unknown separation

### Test

Periksa apakah report membedakan:

```text
verified fact
public claim/allegation
public perception
unverified rumor
unknown / not measured
```

### PASS bila

- label dan wording berbeda;
- unknown dinyatakan jujur;
- claim tidak dinaikkan menjadi fact;
- fact tidak dibungkus sebagai opini.

### FAIL bila

- “publik menuduh” ditulis sebagai fakta;
- “diduga” hilang dari claim yang belum terbukti;
- absence of evidence ditulis sebagai “tidak ada”;
- rumor kecil dijadikan prioritas tanpa evidence.

---

## C5. Issue severity integrity

### Test

Untuk report crisis/issue, periksa apakah severity disimpulkan dari evidence yang tepat.

### PASS bila

- risk memakai issue-only universe;
- direct allegation dipisahkan dari brand mention;
- source quality dan trend dipertimbangkan;
- top exposure/content dibaca;
- recommendation menyesuaikan level risk.

### FAIL bila

- total brand post dipakai sebagai severity issue;
- satu viral post otomatis disebut crisis besar;
- issue kecil diamplifikasi oleh slide khusus tanpa alasan;
- risk status tidak memiliki definisi atau evidence;
- “belum terukur” dipaksakan menjadi low/medium/high.

---

# D. STORYLINE AND DECISION USEFULNESS

## D1. Business question answered

### Test

Baca executive answer dan closing decision.

### PASS bila

- report menjawab pertanyaan bisnis;
- pembaca tahu apa yang terjadi;
- pembaca tahu kenapa penting;
- pembaca tahu tindakan/keputusan yang tersedia.

### FAIL bila

- deck hanya daftar metrik;
- executive answer tidak menjawab brief;
- conclusion berbeda dengan evidence;
- reader masih harus menebak “so what”.

---

## D2. One story, not a dashboard dump

### Test

Periksa hubungan antar slide.

### PASS bila

- ada satu cerita utama;
- setiap slide mendorong cerita tersebut;
- tidak ada slide hanya karena data tersedia;
- detail teknis dipindahkan ke appendix;
- pengulangan dikurangi.

### FAIL bila

- topik/metric muncul tanpa kaitan;
- deck memuat semua output tool;
- banyak slide menjawab pertanyaan berbeda tanpa prioritas;
- isi main deck lebih cocok menjadi appendix;
- storyline berubah tanpa transisi/evidence.

---

## D3. Headline quality

### Test

Periksa seluruh judul slide main deck.

### PASS bila

- headline adalah kesimpulan;
- headline spesifik;
- headline didukung evidence;
- bahasa dapat dipahami pembaca non-analis;
- istilah internal tidak muncul.

### FAIL bila

- judul hanya “Sentiment Analysis”, “Issue Mapping”, atau “Data Overview”;
- headline memakai jargon seperti “reframe”, “tension”, atau “signal vs noise”;
- headline terlalu dramatis dibanding data;
- headline berupa angka tanpa arti bisnis;
- headline bertentangan dengan chart.

---

## D4. Priority and decision clarity

### Test

Periksa apakah report membedakan:

```text
priority utama
risk/opportunity sekunder
noise/watchlist
```

### PASS bila

- prioritas utama jelas;
- hal yang tidak perlu direspons juga jelas;
- decision yang dibutuhkan klien dinyatakan;
- owner/next step tersedia bila relevan.

### FAIL bila

- semua isu diperlakukan sama penting;
- rekomendasi meminta respons pada rumor kecil;
- client tidak tahu siapa harus melakukan apa;
- deck berhenti pada “monitor”.

---

# E. RECOMMENDATION INTEGRITY

## E1. Recommendation evidence basis

### Test

Setiap rekomendasi harus bisa ditelusuri kembali ke finding/evidence.

### PASS bila

- recommendation menjawab masalah yang ditemukan;
- action spesifik terhadap brand/issue;
- tindakan dapat dilakukan klien;
- owner dan trigger ada bila diperlukan.

### FAIL bila

- rekomendasi generik;
- recommendation tidak terkait finding;
- action hanya “monitor”;
- target palsu dibuat hanya untuk mengisi slide;
- action tidak jelas siapa pemiliknya.

---

## E2. Recommendation realism

### Test

Periksa apakah action dapat dilakukan dan proporsional terhadap risk.

### PASS bila

- action sesuai tingkat bukti;
- action mempertimbangkan risiko amplifikasi;
- tindakan lintas fungsi disebut bila diperlukan;
- decision/next step realistis.

### FAIL bila

- meminta public response tanpa trigger;
- memerintahkan rebuttal rumor kecil;
- meminta target “sentiment positif”;
- menyatakan crisis selesai tanpa evidence;
- meminta aksi yang tidak dapat dikendalikan klien.

---

## E3. Trigger and owner

### Test

Untuk action penting, periksa:

```text
owner
timing
trigger
expected output
success indicator bila valid
```

### PASS bila

- action yang material punya owner;
- trigger response jelas bila bersifat conditional;
- success indicator hanya muncul bila baseline valid.

### FAIL bila

- recommendation hanya slogan;
- owner tidak jelas;
- deadline dibuat-buat tanpa dasar;
- success indicator tidak dapat diukur atau dikendalikan.

---

# F. VISUAL AND DELIVERY QUALITY

## F1. Main deck focus

### Test

Periksa jumlah dan isi slide.

### PASS bila

- main deck biasanya 6–10 content slides, kecuali user membutuhkan bentuk lain;
- appendix dipisahkan;
- setiap slide memiliki satu pesan utama;
- methodology detail tidak mengganggu executive story.

### FAIL bila

- slide ditambah hanya agar terlihat lengkap;
- deck berisi terlalu banyak appendix dalam main flow;
- internal process tampil sebagai slide;
- deck mengulang informasi untuk mengisi jumlah slide.

---

## F2. Readability

### Test

Periksa font, density, chart, dan hierarchy.

### PASS bila

- body text terbaca pada ukuran presentasi;
- slide tidak memuat paragraf panjang;
- angka besar tidak bersaing dengan banyak angka kecil;
- chart labels dapat dibaca;
- footnote cukup singkat dan relevan.

### FAIL bila

- body text terlalu kecil;
- slide penuh 8–10 pt text;
- table terlalu padat;
- chart label tumpang tindih;
- footnote digunakan untuk menyembunyikan claim penting.

---

## F3. Visual-message fit

### Test

Periksa apakah bentuk visual membantu pesan.

### PASS bila

- visual dipilih setelah message jelas;
- chart menjelaskan perubahan/perbandingan;
- screenshot digunakan ketika content evidence penting;
- diagram digunakan ketika akar masalah perlu dijelaskan;
- table dipakai ketika pembaca perlu membandingkan item.

### FAIL bila

- card grid dipakai untuk semua slide;
- chart dibuat tanpa takeaway;
- screenshot dekoratif tanpa peran evidence;
- table menggantikan narasi;
- layout berubah hanya demi variasi tetapi mengurangi kejelasan.

---

## F4. Metric label clarity

### Test

Periksa label chart, KPI, table, dan footer.

### PASS bila

- interactions, views, buzz, ad value, dan sentiment diberi nama jelas;
- SOV menyebut basis metric;
- scope disebut bila penting;
- coverage/caveat muncul bila diperlukan;
- source footer dapat ditelusuri.

### FAIL bila

- “engagement” ambigu;
- “SOV” tanpa basis;
- “sentiment” tanpa denominator;
- “top media” tanpa dasar ranking;
- angka tidak memiliki unit;
- label chart tidak menjelaskan apa yang dibandingkan.

---

## F5. Client ownership and confidentiality

### Test

Periksa brand, footer, dan internal labels.

### PASS bila

- deck terlihat milik client;
- footer menggunakan format seperti `CONFIDENTIAL · [CLIENT]` bila diperlukan;
- vendor label hanya muncul bila user meminta;
- source/log disimpan dengan aman.

### FAIL bila

- deck terasa seperti sales deck vendor;
- `sonar.id` atau brand internal mendominasi footer tanpa kebutuhan;
- internal prompt/framework muncul;
- confidentiality label salah atau tidak konsisten.

---

# 5. HARD STOP LIST

Report otomatis `FAIL` dan tidak boleh dikirim bila salah satu terjadi:

1. Headline number tidak ada di data freeze.
2. Reconciliation status bukan `PASS`.
3. Views diperlakukan sebagai interactions.
4. `source_engagement` dipakai sebagai KPI client-facing.
5. Issue severity dihitung dari brand universe tanpa issue-only scope.
6. Coverage metric utama tidak diketahui atau terlalu rendah tanpa downgrade.
7. Top content yang material belum dibaca.
8. Sentiment aggregate menjadi headline meski top content mismatch material.
9. Post sosial menjadi satu-satunya bukti untuk claim legal/regulator/safety/health.
10. Ad value disebut engagement atau tier media.
11. SOV tanpa basis metric.
12. Comparison memakai period/channel/scope yang tidak comparable tanpa caveat.
13. Recommendation generik dan tidak punya kaitan dengan finding.
14. Main deck menampilkan framework internal atau process log.
15. Deck tidak menjawab pertanyaan bisnis user.

---

# 6. QUALITY REPORT FORMAT

Buat `quality_report.json` internal sebelum final delivery.

Format minimum:

```json
{
  "report_status": "PASS | PASS_WITH_NOTES | FAIL",
  "checked_at": "ISO-8601",
  "contract_version": "3.1",
  "summary": {
    "data_correctness": "PASS | FAIL",
    "scope_metric_integrity": "PASS | FAIL",
    "evidence_claim_integrity": "PASS | FAIL",
    "storyline_decision": "PASS | FAIL",
    "recommendation_integrity": "PASS | FAIL",
    "visual_delivery": "PASS | FAIL"
  },
  "hard_failures": [],
  "warnings": [],
  "required_fixes": [],
  "notes_for_delivery": []
}
```

### Status rule

```text
Jika hard_failures tidak kosong → FAIL

Jika hard_failures kosong tetapi warnings material ada
dan sudah didisclose → PASS_WITH_NOTES

Jika semua section lulus tanpa warning material → PASS
```

---

# 7. FINAL PRE-DELIVERY CHECKLIST

Sebelum mengirim report, jawab semua pertanyaan berikut.

## Data

- [ ] Apakah semua angka berasal dari data freeze?
- [ ] Apakah reconciliation PASS?
- [ ] Apakah canonical unique-post layer dipakai?
- [ ] Apakah actual date range sesuai?
- [ ] Apakah coverage metric utama diketahui?

## Metric

- [ ] Apakah interactions dan views dipisahkan?
- [ ] Apakah SOV memiliki basis metric?
- [ ] Apakah sentiment memakai denominator classified posts?
- [ ] Apakah source engagement tidak muncul sebagai KPI?
- [ ] Apakah ad value tidak diperlakukan sebagai engagement?

## Scope

- [ ] Apakah issue-only dan brand universe dipisahkan?
- [ ] Apakah keyword scope ditulis/dapat ditelusuri?
- [ ] Apakah comparison unit setara?
- [ ] Apakah scope chart konsisten dengan headline?

## Evidence

- [ ] Apakah top content telah dibaca?
- [ ] Apakah claim utama memiliki source/evidence?
- [ ] Apakah social perception dipisahkan dari external fact?
- [ ] Apakah source sensitif cukup kuat?
- [ ] Apakah quote/screenshot dapat ditelusuri?

## Story and recommendation

- [ ] Apakah report menjawab business question?
- [ ] Apakah setiap slide punya satu pesan?
- [ ] Apakah client tahu apa yang penting?
- [ ] Apakah recommendation berasal dari evidence?
- [ ] Apakah action/owner/trigger jelas bila diperlukan?

## Visual and delivery

- [ ] Apakah main deck fokus?
- [ ] Apakah teks dan chart terbaca?
- [ ] Apakah metric label jelas?
- [ ] Apakah internal framework tidak terlihat?
- [ ] Apakah deck terasa milik client?

---

# 8. Prinsip terakhir

Jangan meloloskan report hanya karena:

- semua slide terisi;
- semua chart tampak rapi;
- semua tool sudah dipanggil;
- bahasa terdengar profesional;
- banyak angka tersedia.

Report layak dikirim hanya ketika:

> Data benar, bukti cukup, cerita jelas, dan keputusan klien menjadi lebih mudah.
