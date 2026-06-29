# PANDUAN: Competitive / Brand Intelligence Report (gaya "EVO")

Panduan ini dipakai SETIAP KALI user minta **report**, **competitive analysis**,
**brand report**, **laporan perbandingan**, atau sejenisnya. Tujuannya: report
yang **insight-led** (digerakkan wawasan, bukan tumpukan angka) — selevel report
intelligence yang baik, bukan dump dashboard.

Baca seluruh panduan ini SEBELUM mulai menarik data atau menyusun report.

---

## 1. FORMAT OUTPUT

- **Default: PPTX (PowerPoint).** Buat file deck yang rapi dan siap kirim.
- **Chart WAJIB di-embed sebagai objek/gambar di dalam slide.** JANGAN PERNAH
  bikin report HTML yang menarik library chart dari internet (CDN seperti
  Chart.js dari cdnjs). Itu bikin chart kosong/blank di komputer orang lain.
  Di PPTX, gunakan chart native PowerPoint atau gambar chart yang sudah dirender.
- Sediakan **PDF** hanya jika user minta. HTML hanya untuk eksplorasi internal,
  bukan deliverable ke klien.
- Bahasa report: **ikuti bahasa user** (default Bahasa Indonesia untuk tim CX).

---

## 2. ENAM PRINSIP NARASI (INI YANG BIKIN "JAGO")

Report yang bagus BUKAN soal chart cantik. Ini intinya:

1. **Setiap slide diawali "kalimat so-what" (headline insight), bukan judul
   deskriptif.** Contoh BENAR: *"Dominasi Aqua adalah beban krisis, bukan
   kemenangan brand."* Contoh SALAH: *"Data Engagement per Channel."* Pembaca
   harus dapat kesimpulan dulu, baru lihat angkanya sebagai bukti.
2. **Organisir pakai kerangka.** Gunakan lensa **EVO (Experience / Values /
   Offer)** bila membantu (lihat bagian 7). Report harus punya tulang punggung,
   bukan slide acak.
3. **Selalu BANDINGKAN.** Angka tunggal nyaris tak bermakna. Bandingkan brand vs
   brand, vs rata-rata kategori, vs periode lain. Insight lahir dari perbandingan.
4. **Dukung klaim dengan BUKTI nyata.** Setiap tema penting sertai 1-3 contoh
   post asli (kutip ringkas + link URL + channel). Jangan klaim tanpa bukti.
5. **Tutup tiap bagian dengan REKOMENDASI yang bisa ditindaklanjuti.** Pola:
   "Untuk [brand]: lakukan X." Data -> insight -> aksi.
6. **Nada konsultatif & strategis**, seperti analis brand senior — bukan operator
   dashboard. Pimpin dengan insight, dukung dengan data secukupnya. Hindari
   membacakan angka tanpa makna.

Uji tiap slide: "Apakah ada SATU kalimat insight di atasnya, dan apakah angkanya
MENDUKUNG kalimat itu?" Kalau tidak, perbaiki.

---

## 3. DATA YANG HARUS DITARIK (urutan kerja)

Tarik data Cogan SEBELUM menulis. Untuk competitive report dua brand (A vs B):

1. `find_project` / `list_campaigns` — konfirmasi nama campaign yang benar.
2. `compare_campaigns` — skor head-to-head (volume, engagement, sentimen).
3. `share_of_voice` (metric **buzz** = default) — dominasi percakapan.
4. `metrics_summary` tiap brand — breakdown per channel (PAKAI metrik yang
   relevan per platform; lihat catatan di bawah).
5. `timeline` tiap brand + `detect_spikes` — tren harian & hari puncak.
6. `top_viral_posts` tiap brand — bukti konten teratas (+ link).
7. `get_posts` tiap brand (urut by engagement, ~80-150 post) — **BACA konten
   asli** untuk menyimpulkan ISU/tema & pendorong sentimen. JANGAN menyimpulkan
   isu dari frekuensi kata wordcloud.
8. `top_media` (bila ada online media) — media outlet & ad value per media.
9. `count_posts` — breakdown sentimen bila perlu detail.

**Catatan metrik per channel (penting, jangan keliru):**
- TikTok: like, comment, share. Instagram: like, comment.
- Twitter/X: like, reply, retweet. Facebook: like, comment, share.
- YouTube: like, comment. **Online Media: TIDAK punya engagement** — pakai
  Ad Value (lewat `top_media`), bukan engagement.

---

## 4. STRUKTUR REPORT (slide demi slide)

1. **Cover** — judul, brand yang dibandingkan, periode, "CONFIDENTIAL".
2. **Executive Summary** — 3-5 takeaway "so-what" paling penting.
3. **Konteks Periode** — isu/peristiwa dominan yang jadi tulang punggung cerita
   (mis. sebuah kampanye, krisis, atau momen viral).
4. **Scoreboard Head-to-Head** — tabel: volume, SOV (buzz), engagement, sentimen
   net, engagement/post. Tiap baris kasih label unggul/seri/kalah (lihat bagian
   6). Diawali headline insight.
5. **Share of Voice & Timeline** — chart SOV + chart tren harian; tandai lonjakan
   dan jelaskan pemicunya.
6. **Channel Battleground** — breakdown per channel (metrik sesuai platform);
   di channel mana tiap brand menang.
7. **Apa yang Menggerakkan Sentimen** — isu positif & negatif utama tiap brand
   (sertakan buzz/engagement + link). Ini slide paling bernilai.
8. **Konten Viral / Bukti** — post teratas tiap brand (kutipan + link + metrik).
9. **Online Media & Ad Value** — media mana yang memberitakan, ad value per
   media (hanya bila ada data online media).
10. **Tema/Narasi Utama** — hasil membaca konten: kelompokkan jadi 3-6 tema per
    brand (boleh diorganisir lewat lensa EVO).
11. **Rekomendasi** — terpisah per brand, pola "Untuk [brand]: ...".
12. **Kesimpulan Strategis** — rangkuman visual yang mengikat semuanya.
13. **Metodologi & Catatan** — lihat bagian 8.

Boleh menyesuaikan jumlah slide; pertahankan alur: konteks -> skor -> sentimen ->
bukti -> tema -> rekomendasi -> kesimpulan.

---

## 5. SCORECARD BENCHMARK (JUJUR, BUKAN "EVOScore" rahasia)

Cogan TIDAK punya rumus EVOScore proprietari. JANGAN mengarang angka index.
Sebagai gantinya, buat scorecard transparan dari data nyata:

- Untuk tiap dimensi (volume, engagement, engagement/post, sentimen net, SOV):
  bandingkan brand A vs brand B (atau vs rata-rata kategori bila >2 brand).
- Beri label: **Unggul** (lebih baik dari pembanding), **Seri** (selisih tipis),
  **Tertinggal**. Sertakan angka mentahnya supaya transparan.
- Selalu jelaskan ASUMSI: angka ini dari data Cogan langsung, bukan skor resmi.

---

## 6. LENSA EVO (opsional, untuk menyusun tema)

EVO membagi persepsi brand jadi 3 pilar (boleh dipakai untuk mengelompokkan tema
di slide 10):
- **Experience** — pengalaman berinteraksi dgn brand (mis. responsiveness,
  layanan, daily pleasure, creativity).
- **Values** — nilai/keyakinan brand (mis. empowerment, accountability,
  sustainability, collaboration, local pride, entertainment).
- **Offer** — proposisi nilai/penawaran (mis. incentives/promo, affordability,
  access).

Claude boleh mengklasifikasi percakapan ke pilar/atribut ini DENGAN MEMBACA
konten (penalaran), lalu menamai temanya. **Catat dengan jujur** bahwa ini
klasifikasi berbasis penalaran, BUKAN tagging resmi metodologi Sonar.

---

## 7. CATATAN METODOLOGI WAJIB (taruh di slide terakhir)

Selalu cantumkan, supaya report jujur & dipercaya:
- Periode & sumber data (percakapan media sosial via Cogan).
- **Sentimen** = klasifikasi otomatis konten; bisa keliru pada konten satir/
  ambigu.
- **Volume** dihitung post unik per URL dalam 1 campaign; bila satu post terdaftar
  di beberapa campaign, ia dihitung di masing-masing (share antar-campaign bisa
  tumpang-tindih).
- **Online media tidak punya engagement**; dinilai lewat ad value.
- Scorecard = perbandingan data langsung, bukan skor index proprietari.

---

## 8. DO / DON'T

DO:
- Pimpin tiap slide dengan insight; dukung dengan data & bukti post nyata + link.
- Bandingkan, beri konteks, beri rekomendasi.
- Pakai PPTX dengan chart ter-embed.

DON'T:
- JANGAN bikin chart yang bergantung CDN/internet (bikin blank).
- JANGAN mengarang angka EVOScore atau metrik yang tak ada datanya.
- JANGAN menyimpulkan isu dari wordcloud; baca konten asli via `get_posts`.
- JANGAN menjumlahkan engagement antar-campaign yang tumpang-tindih.
- JANGAN mengarang kutipan; kutip hanya post yang benar-benar ada (+ link).
