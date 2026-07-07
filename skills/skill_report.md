---
name: cogan-report-storytelling
version: 3.1
description: >
  Panduan editorial untuk mengubah data Cogan dan evidence yang sudah tervalidasi
  menjadi report client-facing yang menjawab pertanyaan bisnis, bukan tumpukan
  metric atau template slide.
---

# COGAN REPORT STORYTELLING GUIDE

## 1. Otoritas file ini

File ini adalah sumber aturan untuk:

- pertanyaan bisnis;
- editorial angle;
- storyline;
- headline;
- bahasa client-facing;
- penggunaan evidence dalam narasi;
- prioritisasi finding;
- rekomendasi dan decision framing;
- struktur main deck dan appendix.

File ini **tidak boleh** menentukan:

- formula metric;
- definition interactions, views, sentiment, SOV, ad value, atau coverage;
- canonical dedup;
- query keyword;
- urutan pemanggilan tool MCP;
- struktur data freeze;
- layout visual detail;
- quality status final.

Gunakan file berikut untuk hal tersebut:

| Kebutuhan | File sumber |
|---|---|
| Metrik, scope, coverage, denominator | `consistency_contract.md` |
| Tool MCP, data retrieval, data freeze | `stage_data_cogan.md` |
| Workflow end-to-end | `system_prompt.md` |
| Visual recipe | `perpustakaan_resep_slide.md` |
| QA final | `quality_framework.md` |
| Router / file authority | `SKILL.md` |

---

## 2. Standar report yang baik

Report yang baik membuat klien memahami:

1. **Apa yang terjadi?**
2. **Mengapa hal itu terjadi atau mengapa penting?**
3. **Apa yang perlu dipercaya, diverifikasi, atau diabaikan?**
4. **Apa implikasinya bagi brand/bisnis?**
5. **Apa pilihan tindakan atau keputusan berikutnya?**

Prinsip utama:

> Satu kesimpulan manusia  
> → satu bukti yang jelas  
> → satu implikasi bagi klien  
> → satu keputusan atau tindakan.

Jangan membuat slide hanya karena:

- data tersedia;
- tool dapat mengeluarkan angka;
- template punya ruang;
- chart terlihat bagus;
- report lama memiliki section yang sama.

---

## 3. Mulai dari keputusan, bukan data

Sebelum menyusun narrative, jawab secara internal:

```text
Siapa pembaca report?
Keputusan apa yang harus mereka ambil?
Apa risiko jika keputusan salah?
Apa yang perlu diketahui sebelum keputusan bisa dibuat?
```

Contoh perubahan cara berpikir:

| Jangan mulai dari | Mulai dari |
|---|---|
| “Ada berapa post negatif?” | “Apakah isu ini membutuhkan respons publik atau cukup disiapkan sebagai FAQ internal?” |
| “Brand mana SOV tertinggi?” | “Di area mana brand tertinggal atau unggul, dan apakah perbedaan itu berarti secara bisnis?” |
| “Konten mana paling viral?” | “Konten apa yang benar-benar memperluas exposure atau mendorong aksi pengguna?” |
| “Apa top media?” | “Outlet mana yang memperluas framing isu dan apakah coverage itu mengubah level risiko?” |
| “Apa topik teratas?” | “Narasi mana yang paling berpengaruh terhadap keputusan klien?” |

Data adalah bukti. Data bukan struktur cerita.

---

## 4. Satu report, satu cerita

Setiap report harus dapat diringkas dalam satu kalimat internal:

> “Report ini menjelaskan bahwa ...”

Contoh:

```text
“Percakapan tentang isu sumber air telah meluas, tetapi risikonya terutama
berasal dari framing tuduhan langsung pada konten ber-exposure tinggi,
bukan dari total volume percakapan brand.”
```

atau:

```text
“Kompetitor unggul pada volume percakapan, tetapi keunggulan itu ditopang
satu aktivitas besar; peluang brand terletak pada narasi yang lebih konsisten
di komunitas inti.”
```

Jika satu kalimat itu belum dapat ditulis, jangan mulai membuat slide.

---

## 5. Jenis report bukan menu tertutup

Contoh report seperti Crisis, Competitive, Sponsorship, Brand Health, dan
Segmentation adalah pola umum, bukan daftar report yang diizinkan.

Jika user meminta report yang tidak ada dalam contoh:

1. Tentukan pertanyaan bisnisnya.
2. Tentukan keputusan yang ingin dibantu.
3. Tentukan 2–4 dimensi analisis yang relevan.
4. Susun story berdasarkan keputusan itu.
5. Jangan memaksa report custom menjadi jenis report lain.

Contoh report custom:

- evaluasi layanan/cabang;
- dampak perubahan harga;
- reputasi eksekutif;
- narasi ESG;
- kesiapan peluncuran produk;
- evaluasi kolaborasi;
- pemetaan komunitas;
- respons publik terhadap kebijakan;
- audit komunikasi;
- studi penggunaan produk;
- analisis perubahan persepsi.

Struktur universal report custom:

```text
Question
→ What happened
→ Evidence
→ Interpretation
→ Implication
→ Action / Decision
```

---

## 6. Struktur main deck

Main deck biasanya terdiri dari **6–10 content slides**, tetapi jumlah bukan target.

Gunakan hanya slide yang mendorong cerita.

Struktur default yang dapat dipakai bila relevan:

```text
1. Executive answer
2. What happened
3. Why it happened / what drove it
4. Evidence that changes the interpretation
5. What matters most
6. Action options
7. Decision / next step
```

Jangan memaksakan urutan ini.

Beberapa report lebih baik dimulai dengan:

- comparison;
- issue anatomy;
- trend;
- evidence post;
- scenario;
- operating decision.

### Main deck harus berisi

- jawaban;
- bukti yang paling penting;
- interpretasi;
- prioritas;
- tindakan atau keputusan.

### Appendix harus berisi

- data health;
- methodology detail;
- metric definition;
- source log;
- raw evidence tambahan;
- table panjang;
- semua topic sekunder;
- chart yang tidak mengubah keputusan;
- detail untuk audit.

---

## 7. Pola cerita per kebutuhan bisnis

## 7.1 Crisis / Issue / PR

Pertanyaan yang biasanya perlu dijawab:

```text
Apakah isu ini material?
Apa yang memicu dan memperluasnya?
Apakah brand menjadi target langsung atau hanya ikut diasosiasikan?
Apa risiko nyata bagi brand?
Apa yang perlu dilakukan sekarang, disiapkan, atau tidak perlu diamplifikasi?
```

Pola cerita yang sering tepat:

```text
Executive answer
→ issue size and trajectory
→ what is actually being said
→ evidence / high-exposure content
→ issue anatomy or actor pattern
→ priority and response posture
→ decision / operating plan
```

Jangan:

- memakai total brand volume untuk membuktikan issue severity;
- menyebut setiap rumor sebagai crisis;
- membuat “sentiment positif” sebagai tujuan crisis response;
- memaksa public response untuk semua isu;
- menyatakan claim publik sebagai fakta resmi.

---

## 7.2 Competitive

Pertanyaan yang biasanya perlu dijawab:

```text
Di mana brand unggul atau tertinggal?
Apakah gap itu material atau hanya efek satu outlier?
Narasi mana yang dimiliki kompetitor?
Apa celah yang dapat dimanfaatkan brand?
```

Pola cerita yang sering tepat:

```text
Executive answer
→ comparable market position
→ evidence behind the gap
→ narrative/attribute difference
→ concentration or outlier check
→ opportunity
→ strategic action
```

Jangan:

- menyebut “menang” hanya karena satu SOV metric;
- membandingkan channel/period/lifecycle yang tidak setara;
- menyimpulkan kualitas dari total interactions saja;
- memakai satu content viral sebagai bukti keunggulan sistemik.

---

## 7.3 Sponsorship / Campaign / Activation

Pertanyaan yang biasanya perlu dijawab:

```text
Apakah aktivitas menarik perhatian?
Apakah aktivitas menghasilkan aksi pengguna?
Apakah brand linkage terlihat?
Apakah performa tersebar atau ditopang satu konten?
Apa yang perlu diulang, diperbaiki, atau dihentikan?
```

Pola cerita yang sering tepat:

```text
Executive answer
→ performance and timing
→ what content drove exposure/action
→ evidence of brand linkage
→ concentration or creator pattern
→ what to scale / improve / stop
```

Jangan:

- menggunakan total views sebagai bukti brand association;
- menggunakan total interactions tanpa memeriksa outlier;
- hanya menampilkan top content tanpa menjelaskan pola;
- menyebut campaign sukses tanpa menghubungkan hasil dengan objective.

---

## 7.4 Brand Health / Weekly / Monthly

Pertanyaan yang biasanya perlu dijawab:

```text
Apa yang berubah?
Apa yang membutuhkan perhatian?
Apa yang tidak perlu dibesar-besarkan?
Apa implikasinya bagi komunikasi atau operasi?
```

Pola cerita yang sering tepat:

```text
Executive answer
→ key movement
→ what drove the movement
→ top evidence
→ priority / watchlist
→ action for next period
```

Jangan:

- membuat slide untuk semua topik;
- mengulang metric yang sama di beberapa slide;
- menjadikan coverage/data limitation sebagai headline utama;
- memasukkan semua spike tanpa relevansi bisnis.

---

## 7.5 Segmentation / Research

Pertanyaan yang biasanya perlu dijawab:

```text
Segmen mana yang materially berbeda?
Apa kebutuhan, pola, atau hambatan masing-masing?
Apa implikasi terhadap action?
```

Pola cerita yang sering tepat:

```text
Executive answer
→ segmentation logic
→ segment differences
→ segment evidence
→ priority segment
→ action by segment
```

Jangan:

- membuat persona tanpa bukti data;
- menamai segmen secara dekoratif;
- memakai cluster/score tanpa menjelaskan implikasi;
- menyimpulkan kebutuhan individu dari group-level data.

---

## 7.6 Custom report

Pola cerita harus mengikuti pertanyaan user, bukan nama report.

Contoh:

| Permintaan user | Cerita yang perlu dibangun |
|---|---|
| “Apakah kenaikan harga membuat konsumen menjauh?” | perubahan keluhan harga → alasan → bukti dampak → pilihan respons |
| “Apakah kolaborasi ini layak diteruskan?” | exposure/action → brand linkage → kualitas audiens → scale/improve/stop |
| “Kenapa cabang ini diprotes?” | pola keluhan → lokasi/pemicu → evidence → action owner |
| “Apakah isu kebijakan ini berbahaya?” | issue scope → actor/source → trend → risk posture → decision |

---

## 8. Aturan bahasa client-facing

Gunakan bahasa yang jelas, spesifik, dan dekat dengan keputusan klien.

### 8.1 Hindari jargon internal

Jangan gunakan di main deck:

```text
reframe
tension
signal vs noise
adaptation dial
intent contract
stage A/B/C
model output
weighted metric
framework
battlefield
narrative architecture
```

Gunakan bahasa yang menjelaskan kejadian nyata:

| Hindari | Gunakan |
|---|---|
| “Sinyal yang menyesatkan” | “Skor sentimen terlihat positif, tetapi konten paling terekspos justru memuat kritik.” |
| “Tension utama” | “Publik mempertanyakan perbedaan antara klaim brand dan pengalaman yang mereka lihat.” |
| “Reframe percakapan” | “Brand perlu menjelaskan konteks sebelum asumsi publik mengeras.” |
| “Battlefield competitor” | “Kompetitor lebih dominan pada percakapan tentang ...” |
| “Signal vs noise” | “Isu ini perlu ditindak / cukup dipantau / belum perlu diamplifikasi.” |

### 8.2 Gunakan actor + event + consequence

Pola yang lebih mudah dipahami:

```text
Siapa
→ melakukan/mengatakan apa
→ memicu akibat apa
→ mengapa penting bagi klien
```

Contoh:

> Konten dari akun X memicu puncak tayangan pada 24 Oktober dan memperluas framing bahwa brand tidak transparan soal sumber air.

Lebih baik daripada:

> Terjadi amplification of negative perception.

### 8.3 Jangan memperkuat klaim melebihi evidence

Gunakan kata yang sesuai bukti:

| Evidence | Wording aman |
|---|---|
| Post sosial | “publik menyebut”, “komentar menyoroti”, “konten membingkai” |
| Data trend | “percakapan meningkat”, “views memuncak”, “interactions terkonsentrasi” |
| Source resmi | “menurut pernyataan resmi”, “regulator menyatakan” |
| Data belum cukup | “belum dapat dipastikan”, “belum terukur”, “perlu verifikasi” |

Jangan menulis:

```text
terbukti
pasti
seluruh publik
mayoritas masyarakat
krisis besar
gagal
berhasil
```

kecuali evidence benar-benar mendukung klaim tersebut.

---

## 9. Aturan penggunaan metrik dalam narasi

Gunakan definisi dari `consistency_contract.md`. File ini hanya mengatur cara membahas metrik dalam cerita.

### 9.1 Interactions

Gunakan untuk menjelaskan aksi pengguna terhadap konten.

Contoh:

> Konten tersebut menghasilkan interactions tertinggi di periode ini, terutama dari komentar dan shares.

Jangan gunakan:

> Konten tersebut memiliki engagement tinggi.

kecuali definisi interactions telah dinyatakan jelas dalam konteks user.

### 9.2 Views

Gunakan untuk menjelaskan exposure atau tayangan.

Contoh:

> Konten eksposé menjadi sumber exposure terbesar dengan 42,2 juta views.

Jangan gunakan:

> 42,2 juta views membuktikan publik setuju.

Views menunjukkan exposure, bukan persuasion atau sentiment.

### 9.3 Sentiment

Gunakan dengan hati-hati.

Contoh:

> Secara count, post negatif lebih dominan dalam scope isu. Namun, kesimpulan ini dibaca bersama konten paling terekspos dan coverage data.

Jangan gunakan:

> Publik negatif terhadap brand.

tanpa scope, evidence, dan caveat yang tepat.

### 9.4 Ad value

Gunakan sebagai konteks eksposur media online.

Contoh:

> Outlet dengan ad value tertinggi memperluas jangkauan liputan isu, tetapi metrik ini tidak menunjukkan kualitas framing atau kredibilitas secara otomatis.

Jangan gunakan:

> Ad value tinggi berarti media paling berpengaruh atau tier-1.

### 9.5 Angka yang tidak perlu

Jangan memasukkan angka hanya karena tersedia.

Tanyakan:

```text
Apakah angka ini mengubah keputusan atau membuat pembaca lebih memahami?
```

Jika tidak, pindahkan ke appendix atau hapus.

---

## 10. Headline rules

Headline harus berupa jawaban, bukan nama topik.

### Headline lemah

```text
Issue Overview
Sentiment Analysis
Top Media
Social Media Performance
Competitive Landscape
Campaign Results
```

### Headline lebih baik

```text
Isu sumber air naik setelah video eksposé menghubungkan brand dengan dugaan penggunaan sumur bor.

Kompetitor unggul dalam volume, tetapi keunggulannya terkonsentrasi pada satu aktivitas besar.

Campaign mencapai exposure tinggi, namun aksi pengguna terkonsentrasi pada satu kreator.

Liputan media meluas, tetapi mayoritas artikel masih mengulang informasi tanpa tuduhan baru.
```

### Aturan headline

1. Satu headline = satu klaim.
2. Klaim harus didukung evidence.
3. Gunakan kata kerja dan consequence.
4. Hindari headline terlalu panjang.
5. Hindari jargon.
6. Jangan memasukkan tiga klaim dalam satu headline.
7. Jangan menulis angka tanpa arti bisnis.

---

## 11. Struktur isi per slide

Setiap slide main deck harus menjawab:

```text
Apa yang ingin pembaca pahami?
Bukti apa yang paling relevan?
Mengapa ini penting bagi klien?
```

Struktur copy yang dianjurkan:

```text
Headline:
Kesimpulan.

Evidence:
Chart / screenshot / comparison / quote / table.

Interpretation:
Satu sampai dua kalimat tentang arti evidence.

Implication:
Apa yang perlu diperhatikan atau diputuskan.
```

Jangan menulis paragraf panjang di slide.

Gunakan body copy untuk:

- menjelaskan arti;
- menghubungkan evidence;
- memberi caveat yang material;
- mengarahkan keputusan.

Jangan gunakan body copy untuk mengulang semua angka di chart.

---

## 12. Evidence hierarchy dalam narrative

Gunakan bukti sesuai kebutuhan claim.

| Claim | Bukti terbaik |
|---|---|
| Perubahan volume atau exposure | Timeline / trend |
| Konten tertentu menjadi pemicu | Screenshot / evidence board |
| Satu post mendominasi | Concentration visual |
| Kompetitor lebih dominan | Comparable ranking / SOV basis jelas |
| Narasi publik salah paham | Issue anatomy + source evidence |
| Media memperluas isu | Media landscape + article evidence |
| Perlu merespons atau tidak | Priority / decision tree |
| Siapa melakukan apa | Operating plan |

Jangan memakai metric aggregate untuk menggantikan bukti konten ketika framing konten adalah inti finding.

---

## 13. Prioritisation

Jangan menjadikan semua temuan sebagai prioritas.

Kelompokkan secara internal:

```text
Priority utama
→ materially memengaruhi reputasi, bisnis, atau keputusan

Risk / opportunity sekunder
→ relevan, tetapi belum memerlukan tindakan utama

Noise / watchlist
→ perlu dicatat atau dipantau, tidak perlu diamplifikasi
```

Gunakan kriteria:

- evidence strength;
- scale;
- velocity;
- source/actor relevance;
- business relevance;
- potential consequence;
- ability to act.

Jangan memberi label “high risk” hanya karena sentimennya negatif.

---

## 14. Recommendation rules

Recommendation harus merupakan jawaban terhadap finding.

Format yang dianjurkan:

```text
Action
→ why now
→ owner
→ trigger / timing
→ expected output
```

Contoh:

| Finding | Action | Owner | Trigger | Output |
|---|---|---|---|---|
| Publik salah memahami istilah teknis | Siapkan FAQ dan proof points | Corporate comms + technical team | Sebelum puncak kedua / sebelum media inquiry | Klarifikasi berbasis bukti |
| Satu kreator menyumbang mayoritas interactions | Diversifikasi creator mix | Campaign team | Aktivasi berikutnya | Distribusi performance lebih merata |
| Rumor kecil belum berkembang | Siapkan monitoring cue, jangan respons publik | Social listening + comms | Jika volume/source melewati trigger | Watchlist dan escalation note |

### Jangan membuat rekomendasi seperti ini

```text
Tingkatkan engagement.
Perbaiki sentiment.
Lakukan monitoring.
Perkuat komunikasi.
Tingkatkan awareness.
```

Rekomendasi tersebut terlalu generik kecuali diperjelas menjadi tindakan nyata.

### Jangan membuat target palsu

Jangan menambahkan:

```text
target sentiment +20%
target engagement naik 50%
target media positif 80%
```

kecuali baseline, controllability, dan metode ukurnya memang tersedia.

---

## 15. Decision framing

Main deck sebaiknya berakhir pada satu dari bentuk berikut:

- keputusan yang perlu dibuat;
- action plan;
- scenario/trigger;
- operating posture;
- pilihan scale / improve / hold / stop;
- owner map.

Contoh:

```text
Decision requested:
Apakah brand perlu memberi klarifikasi publik sekarang, atau cukup menyiapkan
evidence pack sambil menunggu trigger tertentu?

Recommended posture:
Jangan memperbesar rumor kecil; siapkan klarifikasi yang dapat dikeluarkan
cepat bila isu mulai diangkat outlet media atau akun ber-exposure besar.
```

Jangan mengakhiri report dengan:

```text
Kesimpulan
Terima kasih
Monitor lebih lanjut
```

tanpa keputusan atau implication.

---

## 16. Client-facing deck vs internal artifact

### Client-facing deck boleh berisi

- finding;
- evidence;
- clear metric;
- implication;
- action;
- decision;
- limitation yang material.

### Client-facing deck tidak boleh berisi

- prompt;
- tool name;
- stage;
- framework;
- report workflow;
- data extraction log;
- quality score;
- metric admission rule;
- internal confidence score;
- raw system language;
- hidden reasoning.

### Internal artifact boleh berisi

- data health;
- scope detail;
- query/keyword;
- evidence log;
- reconciliation;
- quality report;
- source list;
- methodology detail.

---

## 17. Editorial checklist sebelum slide plan

Sebelum slide plan dibuat, periksa:

### Business question

- [ ] Apakah report menjawab pertanyaan bisnis?
- [ ] Apakah decision yang harus dibantu jelas?
- [ ] Apakah report type custom ditangani tanpa dipaksa ke template?

### Storyline

- [ ] Apakah ada satu cerita utama?
- [ ] Apakah executive answer benar-benar menjawab?
- [ ] Apakah setiap slide membantu cerita?
- [ ] Apakah slide yang hanya memuat data sudah dipindahkan ke appendix?

### Language

- [ ] Apakah headline adalah kesimpulan?
- [ ] Apakah jargon internal sudah dihapus?
- [ ] Apakah wording sesuai evidence strength?
- [ ] Apakah actor + event + consequence jelas?

### Metrics

- [ ] Apakah interactions dan views dibahas terpisah?
- [ ] Apakah ad value tidak disamakan dengan social metric?
- [ ] Apakah angka yang dipakai benar-benar penting?
- [ ] Apakah caveat yang material sudah masuk narrative?

### Recommendation

- [ ] Apakah action berasal dari finding?
- [ ] Apakah action spesifik?
- [ ] Apakah owner/trigger disebut bila relevan?
- [ ] Apakah recommendation tidak mengamplifikasi risiko kecil?

---

## 18. Prinsip terakhir

Report yang kuat tidak terasa seperti output sistem.

Report yang kuat terasa seperti seseorang telah:

- memahami masalah klien;
- memilah bukti penting dari data;
- menjelaskan apa yang benar-benar terjadi;
- dan membantu klien mengambil keputusan yang lebih baik.
