# PERPUSTAKAAN RESEP SLIDE — Build Recipes untuk Stage E → F
## Kamus cara-bikin per slide: dari nama peran → jadi slide beneran

> **Posisi file ini di dalam engine.** Ini bukan paket tandingan. `consistency_contract.md`
> Part 4 sudah **menamai** peran slide (cover, tension, reframe, …) dan `system_prompt.md`
> Stage E sudah memberi **layout_type** satu baris. Yang belum ada di antara keduanya:
> **resep konkret per slide** — tugasnya, cocok report tipe apa, langkah bikinnya (PptxGenJS +
> token), dan **tool Cogan mana yang mengisinya (beserta parameter aslinya)**. File ini mengisi
> celah itu. Baca saat menyusun **Stage E** (production brief) dan mengeksekusi **Stage F** (render).
>
> **Read order (nyambung ke skill_mapping.yaml):** `methodology.md` → `system_prompt.md` →
> pegang `consistency_contract.md` sebagai lapisan invarian → **file ini** saat menulis brief per
> slide (Stage E) & merender (Stage F) → `quality_framework.md` sebagai gerbang sebelum kirim.
>
> **Sumber kebenaran tetap di file lain.** Warna/font/ukuran **selalu** dari `theme.json`
> (`consistency_contract.md` Part 3) — file ini menyebut token, tidak menaruh hex. Peran & urutan
> spine **selalu** dari Canonical Slide Contract (Part 4). Metrik **selalu** dari Metric Dictionary
> (Part 1). Kalau ada bentrok, file lain menang; ini cuma "cara bikin".

---

## 0 · CARA MEMBACA TOKEN (dipakai di semua resep)

Stage F membangun satu lookup token sekali, lalu semua resep merujuk ke situ — **jangan hardcode
hex/font di slide manapun** (aturan A9 · quality_framework):

```js
const pptxgen = require("pptxgenjs");
const T = require("./theme.json");                 // consistency_contract Part 3
const C = T.color, F = T.font, S = T.size_pt;      // shortcut warna / font / ukuran
let pres = new pptxgen(); pres.layout = "LAYOUT_16x9";
// contoh pakai: fill:{color:C.card_negative}, color:C.bg_light, fontFace:F.header_family, fontSize:S.title
```

**Konvensi resep di bawah** — tiap kartu dibaca sama:

- **Tugas** — pekerjaan slide ini dalam satu kalimat (fungsinya di arc, bukan judulnya).
- **Cocok untuk** — report tipe / beat mana slide ini paling kepakai.
- **layout_type** — dari LAYOUT ROTATION RULE (`system_prompt.md` Stage E). Ingat: **2 slide berturut
  tak boleh sama layout_type-nya** (ANTI-REPEAT GATE).
- **Cara bikin** — langkah PptxGenJS konkret, merujuk token `T`.
- **Data & tool Cogan** — tool(param) → field yang dipakai. Angka **selalu** dari data beku
  (`deck_data.json`, hasil Stage C/C.5) — resep cuma bilang tool mana yang men-supply-nya.
- **Jebakan / QA** — kesalahan paling sering + gerbang mana yang menangkapnya.

> **Aturan tarik data (dari skill_report.md, tetap berlaku):** ANGKA → tool agregat; KUTIPAN/isu →
> `get_posts` (baca konten asli, bukan wordcloud); BARIS MENTAH banyak → `export_raw_data` lalu olah
> pakai kode. Tool dipanggil hanya kalau sebuah **beat** membutuhkannya (Langkah 4 skill_report /
> Stage D), bukan sebaliknya.

---

## 1 · RESEP SPINE WAJIB (selalu ada, urut ini — Part 4)

### `cover` · layout_type: **HERO + 3 KPI CARDS**
- **Tugas:** bingkai satu pertanyaan bisnis + tiga angka yang jadi taruhan cerita. Bukan halaman judul kosong.
- **Cocok untuk:** semua report.
- **Cara bikin:** background `{color:C.bg_dark}`; judul 36pt bold `C.bg_light` (`F.header_family`);
  subtitle 18pt `C.accent_cool`; brand/period 12pt `C.muted`. Strip 3 KPI card di sepertiga bawah,
  lebar sama, bottom-aligned. **Kartu positif/netral** → fill `C.card_positive`, angka `C.bg_light`,
  label `C.muted`. **Kartu negatif/alert** → fill `C.card_negative`, angka `C.bg_light`, label
  `C.label_on_neg`. Metrik primer font +20% (kpi_card_rule di theme).
- **Data & tool Cogan:** `metrics_summary(project_name, start, end)` → total engagement/buzz;
  `count_posts(...)` → jumlah post unik + net sentiment. Pilih 3 angka yang benar-benar dipakai di arc.
- **Jebakan / QA:** KPI card yang cuma pajangan tanpa nyambung ke cerita = data dump. Semua angka
  cover **wajib** lolos "headline existence" (C.5 check 2) — ada verbatim di `deck_data.json`.

### `scope_metodologi` · layout_type: **TABLE / 3-COLUMN INFO BOX**
- **Tugas:** buktikan data tidak ngasal — total data, periode, channel/sumber, definisi metrik kunci,
  `contract_version`. Ini slide "kejujuran".
- **Cocok untuk:** semua report. **Selalu slide ke-2** (invarian Part 4).
- **Cara bikin:** tabel atau 3 kolom info-box (BUKAN paragraf naratif). Kolom: (1) cakupan data
  n + rentang tanggal aktual + channel; (2) definisi metrik kunci yang dipakai deck ini; (3)
  keterbatasan jujur + `contract_version`/`theme_version`.
- **Data & tool Cogan:** **`data_health(project_name, start, end)`** — ini tool inti slide ini:
  `n_posts_unique`, `date_range_actual`, `channels_present`, dan `coverage_percent`
  (sentiment_classified / engagement_gt0 / buzz_gt0 / ad_value_gt0). Coverage rendah → tulis
  keterbatasannya di sini ("engagement hanya di X% post", "online media tak punya engagement").
- **Jebakan / QA:** metrik dengan coverage rendah tapi dipakai absolut di slide lain = langgar A4.
  Slide ini yang menyediakan angka **n** untuk penanda `directional`. Jangan naratif (layout FAIL).

### `executive_summary` · layout_type: **QUESTION BOX + 4 FINDING CARDS + DECISION BANNER**
- **Tugas:** satu pertanyaan di atas, 3–4 temuan inti, satu banner keputusan. Seluruh deck dalam satu slide.
- **Cocok untuk:** semua report (terutama audiens eksekutif).
- **Cara bikin:** question box tipis di atas (`C.accent_cool` bg tint / `C.ink` teks); 4 finding
  card grid (`C.bg_light`, drop shadow, **bukan** border satu sisi); decision banner bawah
  (`C.bg_dark` fill, teks `C.bg_light`). Tiap finding = headline mini + 1 angka.
- **Data & tool Cogan:** tidak menarik tool baru — merangkum angka beku dari beat Stage D.
- **Jebakan / QA:** banner keputusan **bukan** CTA beli/demo (SALES-DECK gate). Empat kartu yang cuma
  angka tanpa "so what" = dump.

### `context` · layout_type: **CHART LEFT + INSIGHT PANEL RIGHT**
- **Tugas:** bingkai **masalahnya**, bukan datanya. Kenapa report ini ada sekarang.
- **Cocok untuk:** semua report; di crisis sering dipadukan "kenapa sekarang" (lonjakan).
- **Cara bikin:** chart native kiri (`pres.charts.LINE`/`BAR`, `chartColors:[C.accent_cool,...]`,
  `valGridLine:{color:C.grid,size:0.5}`, `catGridLine:{style:"none"}`, `showValue:true`); panel
  kanan 3 insight berlabel (teks pendek verb-led, bukan bullet panjang).
- **Data & tool Cogan:** `timeline(project_name, start, end, channel)` untuk tren pembuka, atau
  `count_posts` untuk channel share. Untuk crisis: `detect_spikes(...)` menjawab "kenapa sekarang".
- **Jebakan / QA:** kalau context cuma "ini lho datanya" tanpa menautkan ke masalah klien → geser ke
  framing masalah (B1 Business Decision Gravity).

### `tension` · layout_type: **DIVERGING BAR / WATERFALL + BIG NUMBER CALLOUT**
- **Tugas:** kebenaran yang mahal — uncomfortable but important.
- **Cocok untuk:** semua; **beat berat di Issue/Crisis** (arc_emphasis melebarkan Tension).
- **Cara bikin:** diverging bar (pos vs neg) atau waterfall; big number callout di panel kanan
  (mis. net sentiment). Kartu positif `C.card_positive`, negatif `C.card_negative`.
- **Data & tool Cogan:** `count_posts(...)` → split sentiment & net sentiment **(by count)**;
  `metrics_summary(...)` bila mau **(engagement-weighted)**. **WAJIB** label basis net sentiment
  (Part 1 + C.5 check 4) — satu deck pegang satu basis primer.
- **Jebakan / QA:** mencampur net sentiment by-count dan engagement-weighted tanpa label = langgar A8.

### *(EVIDENCE BLOCK — pilih dari §2, minimal 1 slide)*
Sisipkan di sini. `arc_emphasis` menentukan berapa banyak: crisis melebarkan evidence tension/viral;
segmentation melebarkan per-persona; competitive melebarkan battleground. **Jangan** dua slide evidence
berturut pakai layout_type sama.

### `reframe` · layout_type: **DARK FULL-BLEED + SINGLE LARGE STATEMENT**
- **Tugas:** SATU kalimat yang menamai hambatan lewat kontras. Momen menonjol, **muncul persis sekali**.
- **Cocok untuk:** semua report (Tier-A discipline: tepat satu).
- **Cara bikin:** full-bleed `{color:C.bg_dark}`; satu statement besar (`F.header_family`, ~28–32pt)
  `C.bg_light`, frasa kunci diberi warna `C.accent_cool`. Tanpa chart, tanpa bullet.
- **Data & tool Cogan:** tidak ada — ini kalimat editorial (`client_reframe_line` dari Stage D).
- **Jebakan / QA:** dua reframe = FAIL. Reframe yang cuma recap temuan (bukan kontras "bukan X — tapi
  Y") = lemah (B4). Pilih yang paling didukung bukti terkuat.

### `implication` · layout_type: **SPLIT: internal panel | benchmark panel (NO BULLET)**
- **Tugas:** taruhannya kalau dibiarkan — dikaitkan ke KPI klien.
- **Cocok untuk:** semua; **front-loaded di Proof-to-Decide**.
- **Cara bikin:** kiri panel data internal, kanan panel benchmark (riset publik ber-URL). **Nol
  bullet text** — tiap insight = satu angka / satu % / satu stat terindeks; tren = mini chart 3–5 titik.
- **Data & tool Cogan:** internal dari `metrics_summary`/`count_posts` (beku); benchmark dari riset
  web (wajib URL → References). Cogan tidak menyediakan benchmark eksternal.
- **Jebakan / QA:** bullet text di slide ini = **FORBIDDEN** (Stage F). Benchmark tanpa URL = langgar A3/A5.

### `recommendation` · layout_type: **3-CARD GRID (FIX/SCALE/TEST) + OWNER STRIP**
- **Tugas:** aksi bisnis yang dijalankan **tim klien** — Scale/Fix/Test, dengan pemilik & dampak.
- **Cocok untuk:** semua report.
- **Cara bikin:** 3 kartu, tiap kartu: badge FIX/SCALE/TEST, rekomendasi (aksi klien), owner strip
  (fungsi klien: PR/Corp Comms, CX, Brand, IR, Product…), data rationale, expected impact. Tool boleh
  muncul **maksimal sekali** sebagai enabler note kecil — bukan isi kartu.
- **Data & tool Cogan:** tidak menarik tool — diturunkan dari temuan Stage D. Verb aksi klien
  (launch, establish, fix, publish, reallocate, train), **bukan** verb tool (monitor, alert, track).
- **Jebakan / QA:** OWNER TEST + VENDOR-SWAP TEST wajib lolos (A6). Kalau kartu kebaca sama untuk vendor
  manapun → itu CTA, tulis ulang jadi aksi spesifik klien.

### `decision` · layout_type: **DARK BG + SMALLEST STEP + 3-COL BEFORE→TARGET**
- **Tugas:** langkah terkecil & terjelas yang klien ambil. **Selalu slide konten terakhir** (Part 4).
- **Cocok untuk:** semua report.
- **Cara bikin:** `{color:C.bg_dark}`; headline insight-led; smallest step box (maks 1 kalimat ATAU 3
  micro-step bernomor — bukan dua-duanya); 3 kolom **Before → Target** (pasangan angka, **bukan**
  kalimat deskriptif). Enabler = 1 kalimat footer italic saja.
- **Data & tool Cogan:** angka Before dari data beku (mis. `count_posts` net sentiment sekarang);
  Target = angka sasaran yang diturunkan, ditandai jelas.
- **Jebakan / QA:** kalimat outcome deskriptif = FORBIDDEN → pakai "Net Sentiment: −43 → +10 or higher".
  CTA beli/demo/pilot = FAIL (SALES-DECK gate).

### `references` · layout_type: **NUMBERED LIST + URL (light bg)**
- **Tugas:** semua sumber web/riset dengan URL. **Selalu ada** (invarian Part 4).
- **Cocok untuk:** semua report yang memakai riset publik.
- **Cara bikin:** list bernomor rapi, `C.bg_light`, nama sumber + URL + (opsional) tanggal akses.
- **Data & tool Cogan:** N/A — dari `research_support_urls` Stage D/E.
- **Jebakan / QA:** klaim sensitif (safety/legal/finansial/kompetitor) tanpa sumber kuat ber-URL di sini
  = langgar A3. Angka internal **tidak** boleh muncul seolah dari web.

---

## 2 · RESEP EVIDENCE (expandable — count diatur `arc_emphasis`, minimal 1)

### `evidence_cards` · layout_type: **3-CARD GRID (big number + kategori + engagement + quote strip)**
- **Tugas:** bukti bertahap yang membangun keyakinan, dalam deep-dive rhythm (WHO/WHAT → WHERE/WHEN → SO-WHAT).
- **Cocok untuk:** semua; tulang evidence brand perception (per atribut EVO) & isu (per narasi).
- **Cara bikin:** 3 kartu (`C.bg_light`, drop shadow): angka besar + kategori + engagement, dengan
  **quote strip** kutipan asli di bawah. **BLOK BUKTI WAJIB per kartu:** kutipan verbatim + **handle
  author** + **tanggal** + **metrik** (engagement/views) + **link post (`url`) yang bisa diklik**. Kalau
  raw data punya gambar/thumbnail post, tampilkan sebagai thumbnail kecil di kartu (screenshot bukti);
  kalau tidak ada, blok kutipan+link itu sudah cukup jadi bukti. Kutipan verbatim, jangan parafrase.
- **Data & tool Cogan:** `top_viral_posts(project_name, start, end, by="engagement"|"views"|"shares"|"viral", limit)`
  → konten + metrik + URL; `get_posts(...)` → kutipan asli + `url` + author + tanggal (baca konten, jangan wordcloud).
- **Jebakan / QA:** klaim tanpa link = bukti lemah (tampilkan `url`). Kutipan fabrikasi = langgar A5
  (hanya kutipan asli). n kecil (<30) → tandai `directional`.

### `evidence_compare` · layout_type: **SIDE-BY-SIDE CARDS (A | B) + SYNTHESIS BANNER**
- **Tugas:** kontras dua unit (brand vs kompetitor, periode ini vs lalu) + satu banner sintesis.
- **Cocok untuk:** Competitive, Campaign (periode), semua yang butuh "vs".
- **Cara bikin:** kartu A kiri / B kanan (metrik sejajar), synthesis banner bawah (`C.bg_dark`).
- **Data & tool Cogan:** `compare_campaigns(campaign_a, campaign_b, start, end)` → posts/engagement/buzz/
  avg_engagement_per_post/sentiment + difference; ATAU `compare_periods(project_name, a_start, a_end,
  b_start, b_end, channel)` → perubahan + % untuk "vs periode lalu".
- **Jebakan / QA:** bandingkan kompetitor **by role in the problem**, bukan metric-by-metric (B3). Kalau
  cuma tembak semua metrik ke semua rival = data dump.

### `evidence_time` · layout_type: **MINI SPARKLINE / TIMELINE + split context panel**
- **Tugas:** tunjukkan **kapan** percakapan meledak & konteksnya (deteksi krisis / lonjakan).
- **Cocok untuk:** Issue/Crisis (beat berat), Campaign (kurva kampanye).
- **Cara bikin:** timeline/sparkline (`pres.charts.LINE`, titik puncak ditandai); panel kiri/kanan
  konteks (tanggal puncak, x-di-atas-rata-rata, sentimen hari itu).
- **Data & tool Cogan:** `detect_spikes(project_name, start, end, metric="posts"|"engagement", channel,
  threshold=1.8)` → `timeline` + `peak_day` + `spikes`; lalu `get_posts` pada tanggal lonjakan untuk
  **menjelaskan pemicunya** (jangan berhenti di "ada lonjakan").
- **Jebakan / QA:** menampilkan spike tanpa menjelaskan pemicu = setengah cerita. Puncak n kecil → directional.

### `radar_isu` · layout_type: **DAFTAR TOP ISU (kartu/baris) + STRIP "SINYAL KECIL"**
- **Tugas:** jawab "minggu ini lagi rame apa aja" dalam sekali lihat — Top 3–6 isu **plus** colek
  topik kecil/komunitas yang mulai nyambung ke brand (outlier). Ini slide yang bikin "WAH".
- **Cocok untuk:** hampir semua report (brand health, issue, weekly). Sering jadi jembatan sebelum
  mendalami 1 isu utama.
- **Cara bikin:** bagian atas = daftar **Top isu** (tiap baris: judul isu **bahasa manusia** +
  seberapa rame + sentimen + 1 kutipan pendek). Bagian bawah = strip **"Sinyal kecil / komunitas"**:
  1–3 topik niche yang volumenya kecil tapi relevan (mis. padel, HYROX, isu kemasan) — ditandai jelas
  sebagai **sinyal untuk dipantau**, bukan isu besar. Client-first: judul isu = arti buat klien, angka jadi pendukung.
- **Data & tool Cogan:** `get_posts(...)` lalu **kelompokkan konten jadi tema secara manual** (baca isi,
  jangan wordcloud); volume/sentimen per tema dari `count_posts`/hasil pengelompokan. Untuk niche spesifik
  (mis. brand × "padel") → `get_posts` + filter kata, atau `export_raw_data` lalu olah pandas. Anomali/tema
  yang tiba-tiba naik → silang-cek `detect_spikes`.
- **Jebakan / QA:** jangan cuma tampilkan 1 isu terbesar (itu masalah report lama). Tema dari **baca konten**,
  bukan frekuensi kata. Sinyal kecil (n kecil) → tandai **directional**, jangan diklaim sebagai tren pasti.

### `adopsi_friksi` · layout_type: **DONUT (kiri) + HORIZONTAL BAR (kanan)**
- **Tugas:** komposisi + peringkat berdampingan (mis. share channel + top author/aktor).
- **Cocok untuk:** semua yang butuh "komposisi + ranking" dalam satu slide.
- **Cara bikin:** `pres.charts.DOUGHNUT` kiri (share), `pres.charts.BAR barDir:"bar"` kanan (ranking).
- **Data & tool Cogan:** donut dari `count_posts` (channel/sentiment share); bar dari
  `top_authors(project_name, start, end, ...)` (aktor per author+channel by engagement).
- **Jebakan / QA:** sum-of-parts share harus = total (C.5 check 1); residu → footnote (residual rule).

### `battleground` *(competitive)* · layout_type: **SOV CHART + SCORECARD TABLE**
- **Tugas:** posisi relatif & whitespace kompetitif — siapa mendominasi percakapan, dan maknanya.
- **Cocok untuk:** Competitive Analysis (beat inti).
- **Cara bikin:** chart SOV (bar/doughnut share) + **scorecard tabel yang memuat SEMUA kompetitor yang
  disebut user** (SOV, net sentiment, %negatif/kanal) — jangan cuma tampilkan 1–2. Boleh mendalami rival
  utama di slide lain, tapi tabel ini harus menunjukkan seluruh medan supaya tak ada brand yang "hilang".
  **Wajib satu kalimat alasan** kalau pendalaman difokuskan ("Tier-2 < 10% SOV, dicatat tapi tak didalami
  karena tak mengancam posisi klien"). Ingat catatan overlap SOV → footnote.
- **Data & tool Cogan:** `share_of_voice(start, end, campaigns, metric="buzz"|"engagement"|"posts")`
  → ranking + share_pct SEMUA campaign (default buzz); lengkapi `compare_campaigns` untuk scorecard sentimen.
- **Jebakan / QA:** menghilangkan kompetitor tanpa alasan = bikin pembaca bertanya "kemana yang lain".
  Deklarasikan basis SOV (buzz/posts/engagement) — satu deck satu basis primer (Part 1). "Menang volume"
  ≠ "menang makna": pasangkan SOV dengan sentimen (hindari klaim dominasi buta).

### `top_media` *(online media / PR)* · layout_type: **RANKING BAR (ad value per outlet)**
- **Tugas:** untuk isu tertentu, media outlet mana yang paling banyak memberitakan & berapa ad value-nya.
- **Cocok untuk:** Issue/Crisis & PR yang porsi online media-nya besar.
- **Cara bikin:** horizontal bar ad value per media; label jumlah artikel.
- **Data & tool Cogan:** `top_media(project_name, start, end, keyword, limit)` → media + articles +
  ad_value + pr_value. **Online media tak punya engagement** — nilai lewat ad value, bukan engagement.
- **Jebakan / QA:** jangan campur ad value dengan engagement seolah metrik sama (Part 1: Ad Value terpisah).

### `persona_card` *(segmentation)* · layout_type: **PERSONA CARD GRID (per-persona deep-dive)**
- **Tugas:** satu kartu per persona/segmen dengan deep-dive rhythm; evidence dilebarkan per persona.
- **Cocok untuk:** Segmentation (arc_emphasis melebarkan Evidence jadi per-persona).
- **Cara bikin:** kartu per persona: siapa, ukuran, motivasi, kutipan, so-what. Rotasi layout antar
  slide persona bila banyak (jangan 3 slide identik beruntun).
- **Data & tool Cogan:** ukuran/aktivitas dari `count_posts`/`top_authors`; kutipan dari `get_posts`;
  baris mentah besar untuk profiling → `export_raw_data` lalu olah pakai pandas.
- **Jebakan / QA:** persona berdasarkan frekuensi kata wordcloud = dilarang — baca konten asli. n kecil → directional.

### `<custom_role>` — bila problem menuntut lensa baru
Ikut pola yang sama: nyatakan tugas beat, pilih layout_type yang **belum dipakai slide tetangga**,
petakan ke tool Cogan yang paling pas (§3), lewati gerbang QA §4. Lensa baru dinamai di Stage B.

---

## 3 · INDEX TOOL COGAN → SLIDE (peta cepat "beat butuh apa")

| Tool Cogan (param inti) | Mengisi slide | Beat / dipakai untuk |
|---|---|---|
| `data_health(project, start, end)` | scope_metodologi | bukti data + coverage% + keterbatasan + sumber n untuk `directional` |
| `count_posts(project, start, end)` | cover · tension · adopsi_friksi · decision | volume unik, sentiment split, net sentiment (by count), channel/sentiment share |
| `metrics_summary(project, start, end, ...)` | cover · tension · implication | total engagement/buzz/ad value, net sentiment (engagement-weighted) |
| `timeline(project, start, end, channel)` | context · evidence_time | tren harian pembuka |
| `detect_spikes(project, start, end, metric, channel, threshold)` | context · evidence_time | "kenapa sekarang" / deteksi lonjakan + hari puncak |
| `share_of_voice(start, end, campaigns, metric)` | battleground · evidence_compare | dominasi percakapan (default buzz) |
| `compare_campaigns(a, b, start, end)` | evidence_compare · battleground | brand vs kompetitor (posts/eng/buzz/sentimen + selisih) |
| `compare_periods(project, a…, b…, channel)` | evidence_compare | periode ini vs lalu (+% perubahan) |
| `top_viral_posts(project, start, end, by, channel, limit)` | evidence_cards | konten paling viral + metrik + URL |
| `top_authors(project, start, end, ...)` | adopsi_friksi · persona_card | aktor/akun berpengaruh (per author+channel) |
| `top_media(project, start, end, keyword, limit)` | top_media | ranking outlet + ad value untuk satu isu |
| `get_posts(project, start, end, ...)` | evidence_cards · persona_card · quote strip | konten asli → kutipan verbatim & identifikasi isu |
| `export_raw_data(project, ...)` | persona_card · appendix | baris mentah banyak → olah pandas / serahkan ke klien |
| `get_report_guide()` | — (dipanggil di awal) | memuat skill_report.md (cara berpikir top-down) sebelum menyusun |
| `find_project` · `list_campaigns` · `ping_cogan` | — | resolusi nama campaign & cek koneksi |

> **Tidak untuk workflow report:** `prepare_wordcloud_context`, `get_wordcloud_candidates`,
> `get_wordcloud_selection_guide`, `get_project_wordcloud_guidance`, `render_selected_wordcloud`.
> Isu **tidak** disimpulkan dari frekuensi kata — baca konten asli via `get_posts`.

---

## 4 · GERBANG QA PER SLIDE (jalankan sebelum render selesai)

Tiap slide harus lolos SEMUA (senada quality_framework Tier A + Stage F FORBIDDEN):

1. **Satu pesan / slide** + ada "so what" — tak ada slide metrik-saja.
2. **Headline = jawaban** 8–14 kata, pakai angka bila ada — bukan judul topik kata-benda.
3. **layout_type dideklarasikan** & **tak sama dengan slide tetangga** (ANTI-REPEAT GATE).
4. **Angka lolos rekonsiliasi** — ada verbatim di `deck_data.json`, sum-of-parts = total, net sentiment berlabel basis (C.5).
5. **Warna/font dari token** `theme.json` — tak ada hex/font hardcoded (A9).
6. **DILARANG visual:** garis/strip dekoratif di atas/bawah judul · sidebar vertikal · border satu-sisi
   pada kartu · bullet di slide implication · kalimat outcome deskriptif di decision · 2+ layout identik beruntun.
7. **Reframe persis sekali**, dark full-bleed.
8. **Rekomendasi/decision** lolos OWNER + VENDOR-SWAP + SALES-DECK — aksi klien, bukan CTA beli/demo/pilot.
9. **Klaim sensitif** ada sumber kuat ber-URL di References (A3); kutipan verbatim & internal-only dari rawdata (A5).
10. **Data lemah** (n<30 / coverage rendah dari `data_health`) → kata "directional" + n terlihat (A4).

---

## 5 · URUTAN SLIDE PER TIPE REPORT (titik awal, bukan template — 12–18 slide)

Spine wajib tetap; yang berubah cuma **blok evidence** (sesuai `arc_emphasis`). Tak ada dua slide
beruntun ber-layout sama. Nama brand dicabut → report **patah** (kalau tidak, itu template — bongkar).

**Competitive (Aqua vs Le Minerale):**
cover → scope_metodologi → executive_summary → context → tension → **battleground (SOV)** →
**evidence_compare (compare_campaigns)** → **evidence_cards (top_viral_posts + get_posts)** → reframe →
implication → recommendation → decision → references

**Issue / Crisis:**
cover → scope_metodologi → executive_summary → context → **radar_isu (top isu + sinyal kecil)** →
**evidence_time (detect_spikes)** → tension (net sentiment) → **evidence_cards (kutipan viral)** →
**top_media (ad value isu)** → reframe → implication → recommendation → decision → references

**Brand Perception (lensa EVO):**
cover → scope_metodologi → executive_summary → context → **radar_isu (lagi rame apa + komunitas)** →
**evidence_cards (per atribut E/V/O)** → tension → **evidence_compare (vs kompetitor)** → reframe →
implication → recommendation → decision → references

**Segmentation (persona):**
cover → scope_metodologi → executive_summary → context → **persona_card ×N** → tension → reframe →
implication → recommendation → decision → references

**Campaign / PR Effectiveness:**
cover → scope_metodologi → executive_summary → context → **evidence_time (kurva kampanye)** →
**evidence_compare (compare_periods)** → **top_media / evidence_cards** → implication →
recommendation → decision → references  *(reframe hanya bila ada aha nyata)*

**Performa Sponsorship / Aktivitas (mis. "performa event olahraga kita + kompetitor"):**
cover → scope_metodologi → executive_summary → **landscape (siapa aktif/tidak — tabel semua brand)** →
**performance (performa tiap properti/aktivitas)** → **evidence_cards (bukti + kutipan + LINK)** →
implication → recommendation → decision → references
→ **TANPA battleground/tension/reframe paksa.** Fokus: apa yang dilakukan, seberapa perform, siapa lagi
yang main. Judul = bahasa klien, bukan jargon ("Le Minerale jalan 4 properti; 5 kompetitor absen", bukan
"BATTLEGROUND").

**Brand Health / "lagi ada apa minggu ini":**
cover → scope_metodologi → executive_summary → **radar_isu (top isu + sinyal komunitas kecil)** →
evidence_cards → implication → recommendation → decision → references  *(reframe opsional)*

**Riset Market / Segmentasi:**
cover → scope_metodologi → executive_summary → **temuan/segmen (persona_card / findings)** →
implication → recommendation → decision → references  *(tanpa tension/reframe paksa)*

**Custom:** pakai anchor wajib (cover · scope · recommendation · decision · references), isi tengah dari
§2 sesuai intent & lensa yang dinamai di Stage B; reframe hanya bila ada aha; patuhi rotasi layout & band 10–16.

---
*Perpustakaan Resep Slide · v1.0 · melengkapi Canonical Slide Contract (Part 4) dengan cara-bikin per
slide + peta tool Cogan. Token, metrik, peran, dan gerbang tetap milik file inti Desy.*
