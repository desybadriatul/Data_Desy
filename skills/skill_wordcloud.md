# Skill: Generate Wordcloud

Panduan detail. Tool Python hanya menghitung angka (frekuensi, engagement,
sentiment mayoritas per kandidat kata/frasa). **Claude yang menentukan kata
mana yang masuk wordcloud** — ini adalah pekerjaan kurasi editorial, bukan
filter otomatis. Gunakan penilaian bahasa dan konteks, bukan sekadar aturan
pattern-matching.

---

## Alur

1. `find_project(nama_client)` — pastikan project & periode datanya ada.
2. `get_project_wordcloud_guidance(project_id)` — baca objective & catatan
   khusus client ini (boleh kosong, baseline di bawah tetap berlaku).
3. `prepare_wordcloud_context(...)` — ambil kandidat kata/frasa dari
   kolom Title + Content, lengkap dengan frekuensi, engagement, dan
   sentiment mayoritas tiap kandidat.
4. **Kurasi kata/frasa** menggunakan kriteria di bawah.
5. `render_selected_wordcloud(...)` — buat PNG + CSV dari pilihan tersebut.

---

## Step 4 — Kurasi Kata/Frasa (Bagian Terpenting)

### 4A. Cleaning awal (sebelum kandidat dibaca)

Kandidat dari `prepare_wordcloud_context` sudah melalui cleaning teknis
(strip URL, hashtag, emoji, angka murni, lowercase). Namun Claude tetap
harus waspada terhadap sisa noise yang lolos.

### 4B. Buang kategori berikut — tanpa pengecualian

**1. Kata fungsi & stopword (bahasa Indonesia + Inggris)**
Kata yang hanya berfungsi sebagai perekat kalimat, tidak membawa makna
topik. Contoh: *yang, dan, di, ke, dari, ini, itu, dengan, untuk, pada,
oleh, dalam, sebagai, karena, namun, serta, bahwa, hingga, tersebut,
setiap, antara, maupun, agar, bila, maka, sehingga, terhadap, secara,
semua, antara* — dan padanannya dalam Inggris (the, of, and, in, to, a,
is, that, it, by, for, are, as, at, be, this, with, have, from, they,
on, or, an, not, but).

**2. Kata informal/filler tanpa makna**
*nih, tuh, udah, emang, kalo, gitu, gini, aja, cuma, cuman, doang,
banget, bgt, yg, dgn, utk, dll, dst, kan, lah, pun, sih, deh, dong,
nggak, nggaknya, kayak, kayaknya*

**3. Kata kerja generik (aksi umum, bukan topik)**
Kata kerja yang bisa dipakai di topik apa saja dan tidak memberi
informasi tentang *apa* yang dibicarakan. Contoh:
*melakukan, dilakukan, mengungkap, menemukan, mengatakan, menyebut,
disebut, membuat, melihat, menunjukkan, meminta, menjelaskan,
menegaskan, menyatakan, menggunakan, memiliki, mendapatkan,
mengetahui, dilaporkan, diketahui, diungkap, terkuak, terungkap*

> **Pengecualian:** kata kerja boleh masuk kalau spesifik ke topik dan
> tidak mungkin muncul di konteks lain — misalnya *menyedot* (dalam
> konteks eksploitasi air tanah) atau *diperas* (dalam konteks buruh).

**4. Nama media, platform, akun**
*inilah, kompas, detik, tribun, cnbc, youtube, tiktok, instagram,
twitter, facebook, media, sosial, berita, news, artikel, konten,
postingan, video, channel, akun, tayangan, upload*

**5. Nama orang & jabatan (kecuali jadi topik utama)**
Nama tokoh, jabatan, dan gelar umumnya adalah konteks, bukan topik.
Buang kecuali client secara eksplisit minta topik "siapa yang bicara".
Contoh yang dibuang: *dedi, mulyadi, jokowi, anies, pak, bu, kang,
gubernur, menteri, bupati, direktur, presiden*

**6. Kata waktu & unit umum**
*hari, bulan, tahun, minggu, jam, menit, detik, senin, selasa, rabu,
januari, februari, ..., waktu, saat, kali, per, tahun, lalu, kemarin,
besok* — dan angka satuan (*meter, kilometer, liter, ton, rupiah, ribu,
juta, miliar*) kecuali menjadi frasa bermakna (lihat 4C).

**7. Kata sifat & kata keterangan generik**
Kata yang mendeskripsikan tapi tidak memberi tahu *apa* yang
dideskripsikan: *besar, kecil, baru, lama, penting, utama, pertama,
berbagai, sangat, lebih, sangat, cukup, hampir, bahkan, ternyata,
langsung, memang, benar, tepat, jelas, nyata, viral, mengejutkan,
mencengangkan, kaget, heboh, ramai*

**8. Kata generik lintas-topik**
Kata yang bisa muncul di berita/konten apapun tanpa memberi identitas
topik: *fakta, data, informasi, temuan, hasil, laporan, kasus, masalah,
isu, kondisi, situasi, proses, hal, cara, soal, tentang, terkait*

---

### 4C. Prioritaskan frasa 2–3 kata

Kata tunggal seringkali ambigu. Frasa lebih spesifik dan lebih berguna
untuk pembaca memahami topik.

**Cara mengenali frasa yang baik:**
- Maknanya berubah kalau salah satu katanya dihapus → frasa yang kuat.
  Contoh: *air tanah* ≠ *air* + *tanah*; *sumur bor* ≠ *sumur* saja.
- Frasa memberi gambaran *apa* yang terjadi, bukan sekadar entitas.
  Contoh: *beban muatan berlebih* lebih informatif dari *muatan* saja.
- Frasa yang sering muncul bersama di banyak kalimat berbeda → sinyal
  kuat bahwa ini memang istilah/konsep, bukan kebetulan.

**Kata tunggal tetap boleh masuk kalau:**
- Sudah cukup spesifik tanpa konteks tambahan: *longsor, korupsi,
  kebakaran, banjir, lockdown, resesi, aqua, danone, subang*
- Tidak punya frasa yang lebih baik untuk mewakili konsep tersebut.

**Gabungkan variasi yang sama:**
Kalau ada *sumur bor* dan *pengeboran* yang merujuk hal sama, pilih
frasa yang lebih sering muncul dan lebih deskriptif. Jangan tampilkan
keduanya — pilih satu yang paling representatif.

---

### 4D. Test akhir per kandidat (tanya ke diri sendiri)

Sebelum memasukkan sebuah kata/frasa, jawab pertanyaan ini:

> *"Kalau seseorang hanya melihat kata/frasa ini di wordcloud, apakah
> mereka langsung paham ini tentang topik apa?"*

- Kalau **ya** → masuk.
- Kalau **mungkin / tergantung konteks** → lihat apakah ada frasa yang
  lebih baik. Kalau ada, pakai frasa itu. Kalau tidak ada, masukkan
  kata tunggalnya tapi dengan catatan.
- Kalau **tidak / terlalu generik** → buang.

---

### 4E. Target jumlah & cara mengisi kuota

Jumlah kata/frasa mengikuti permintaan user (default: 30, maksimal: 50).

**Jangan berhenti terlalu cepat.** Kalau kuota belum terpenuhi, lanjutkan
menilai kandidat berikutnya — bukan hanya 10–15 teratas. Kandidat dengan
frekuensi lebih rendah tetap bisa bermakna kalau topiknya spesifik.

Urutan prioritas pengisian kuota:
1. Frasa 2–3 kata yang lolos 4D → selalu prioritas pertama.
2. Kata tunggal spesifik (nama produk, lokasi, istilah teknis, nama
   kejadian) yang sudah jelas tanpa konteks tambahan.
3. Kata tunggal semi-spesifik yang tidak punya frasa lebih baik, dan
   masih lolos test 4D.

Boleh kurang dari kuota **hanya** kalau semua kandidat tersisa benar-benar
tidak lolos 4D. Kalau kurang, jelaskan ke user berapa yang bisa masuk
dan kenapa sisanya dibuang.

---

## Ukuran & warna

- **Ukuran** mengikuti mode yang diminta: `frequency` (default) atau
  `engagement`. Makin besar nilainya, makin besar tampilannya. Ukuran
  juga mempengaruhi kecerahan warna — kata paling besar tampil paling
  cerah/saturasi tinggi; kata kecil tampil lebih redup.
- **Warna dari sentiment mayoritas** kata/frasa tersebut (dilihat dari
  distribusi sentiment konten tempat kata itu muncul):
  - Positif (≥50% dari kemunculannya di konten positif) → **hijau**
  - Negatif (≥35% dari kemunculannya di konten negatif) → **merah**
  - Sisanya → **abu-abu**
- Background gelap (#0d0d1a atau serupa) agar warna sentiment lebih
  terbaca kontrasnya.
- Sertakan legenda warna di wordcloud.

---

## Kalau data kosong di periode yang diminta

Sampaikan ke user, sebutkan rentang periode yang datanya tersedia
(dari `find_project`), tanyakan mau pakai periode lain.

---

## Checklist sebelum render

Sebelum memanggil `render_selected_wordcloud`, pastikan:

- [ ] Tidak ada stopword / kata fungsi yang lolos
- [ ] Tidak ada nama media, platform, atau akun
- [ ] Frasa 2–3 kata diprioritaskan atas kata tunggal ambigu
- [ ] Variasi istilah yang sama sudah digabung jadi satu term
- [ ] Semua kata/frasa lolos test 4D
- [ ] Jumlah mendekati kuota yang diminta user
- [ ] Sentiment per kata dihitung dari distribusi konten, bukan asumsi
