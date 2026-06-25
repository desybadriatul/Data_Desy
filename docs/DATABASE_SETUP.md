# Setup Database Cogan (PostgreSQL)

> **Untuk langkah setup praktis (klik per klik), baca docs/SETUP_DATABASE_STEPS.md.**
> Model data sekarang berbasis CAMPAIGN (campaign = klien, 1 post bisa
> masuk beberapa campaign). Dokumen ini fokus ke biaya & catatan skala.

Dokumen ini menggantikan rencana lama di `DATABASE_DESIGN.md` (yang masih
menyebut SQLite/Excel dulu). Keputusan sekarang: **langsung PostgreSQL
managed**, karena skalanya jutaan baris/klien/bulan, banyak klien, dan
banyak request bersamaan.

---

## 1. Apa yang dibangun & kenapa begini

### Masalah yang ditemukan dari data asli
Tiap klien punya format kolom **berbeda**. AQUA punya 56 kolom, IMIP 21
kolom; 43 di antaranya tidak sama. IMIP bahkan tidak punya kolom
`Channel` (channel-nya ada di `Media Type`), dan penulisan sentiment beda
(`Negative` vs `positive`). Kalau dipaksa satu tabel berkolom tetap,
setiap klien baru dengan format beda akan memaksa kita merombak tabel.

### Solusi: pola "kolom inti + JSONB"
Tabel `posts` punya dua bagian:

1. **Kolom inti** — hanya field yang dipakai tool (tanggal, channel,
   author, judul, konten, sentiment, engagement, reach, url). Ini
   dinormalisasi saat load (tanggal diseragamkan, sentiment di-lowercase,
   channel diambil dari `Channel` atau `Media Type`). Inilah yang
   di-index dan di-query, jadi cepat.
2. **Kolom `raw` (JSONB)** — SELURUH kolom asli disimpan apa adanya.
   Tidak ada data hilang, dan klien baru berformat apapun tetap masuk
   tanpa ubah skema.

Tabel lain: `clients`, `project_guidance` (pengganti file JSON),
`generated_outputs` (histori semua hasil). Lihat `database/schema.sql`.

### File yang dibuat
```
database/
├── schema.sql          <- definisi semua tabel + index
├── db.py               <- SATU pintu ke database (semua tool baca lewat sini)
├── load_excel.py       <- loader: Excel/CSV/export Solr -> database
├── column_mapping.json <- peta kolom per klien (klien baru cukup tambah blok)
└── __init__.py
```
`server.py` sudah diubah supaya tool membaca dari database lewat `db.py`.
Logika wordcloud-nya **tidak berubah** — hanya sumber datanya yang pindah.

---

## 2. Pasang PostgreSQL di Railway (langkah konkret)

Kamu sudah punya service Cogan di Railway. Tinggal tambah database di
project yang sama:

1. Buka project Cogan di Railway → tombol **New** → **Database** →
   **Add PostgreSQL**.
2. Railway otomatis membuat variabel `DATABASE_URL`. Hubungkan ke service
   Cogan: buka service Cogan → tab **Variables** → **Add Reference** →
   pilih `DATABASE_URL` dari Postgres. (Inilah yang dibaca `db.py`.)
3. Redeploy service Cogan. Saat start, server otomatis menjalankan
   `init_db()` yang membuat semua tabel.

> Kode `db.py` sudah menangani perbedaan kecil: Railway kadang memberi
> `postgres://...`, kita ubah otomatis ke `postgresql://...`.

---

## 3. Muat data pertama kali

Set `DATABASE_URL` (ambil dari Railway → Postgres → tab Variables →
"Connect" → external URL) lalu jalankan **dari laptop kamu**:

```bash
export DATABASE_URL='postgresql://...isi dari Railway...'
pip install -r requirements.txt

# 1) buat tabel (aman diulang)
python -m database.load_excel --init

# 2) muat semua klien yang ada di folder data/
python -m database.load_excel --all --replace

# 3) pindahkan guidance JSON lama ke database
python -m database.load_excel --guidance
```

Menambah klien baru nanti (misal dari export Solr `.xlsx`/`.csv`):
```bash
python -m database.load_excel --client namaklien --file path/ke/export.xlsx --replace
```
Kalau klien baru punya nama kolom beda, tambahkan satu blok di
`database/column_mapping.json` — tidak perlu ubah kode.

Loader memakai **COPY** (cara muat massal tercepat di Postgres) dan
mengirim per batch 5000 baris, jadi file jutaan baris tidak menumpuk di
memori.

---

## 4. Jawaban untuk atasan: "berapa memori, berapa biaya"

Railway memakai pricing **pakai-baru-bayar** (per detik). Yang relevan
(verifikasi Juni 2026 di railway.com/pricing — harga bisa berubah):

- RAM ≈ **$10 / GB / bulan**
- CPU ≈ **$20 / vCPU / bulan**
- Storage ≈ **$0.25 / GB / bulan**
- Egress ≈ **$0.05–0.10 / GB**
- Plan Hobby $5/bln (kredit $5), Pro $20/seat/bln (kredit $20).

Estimasi kasar untuk database Cogan (compute + storage, di luar service
Cogan-nya sendiri):

| Ukuran instance DB | Cocok untuk | Perkiraan / bulan |
|---|---|---|
| 1 vCPU / 1 GB RAM + ~10 GB storage | testing / beberapa klien awal | ± **$15–25** |
| 2 vCPU / 4 GB RAM + ~50 GB storage | belasan klien aktif | ± **$50–80** |
| 4 vCPU / 8 GB RAM + ~200 GB storage | puluhan klien, data besar | ± **$120–200** |

Angka ini indikatif; biaya sebenarnya bergantung pemakaian nyata dan
harus dicek di dashboard Railway minggu pertama.

### Hitungan storage (ini yang penting buat skala kamu)
Satu post + JSON mentahnya ≈ 2–5 KB. Jadi:
- 1 juta baris ≈ **2–5 GB**
- 1 klien, 1 juta/bulan → tumbuh **2–5 GB/bulan**
- 10 klien → **20–50 GB/bulan**, terus bertambah tiap bulan

Artinya storage akan terus naik selama kita menyalin SEMUA raw data ke
database Cogan. Ini membawa ke keputusan arsitektur di bawah.

---

## 5. Keputusan besar yang masih perlu diputuskan (penting)

**Apakah Cogan perlu menyalin SEMUA raw data dari Solr ke databasenya
sendiri, selamanya?** Dua pilihan:

- **A — Salin semua (yang dibangun sekarang).** Sederhana, Cogan mandiri,
  tidak tergantung Solr saat melayani request. Tapi storage tumbuh terus
  dan biaya naik seiring waktu.
- **B — Hibrida.** Database Cogan menyimpan: guidance, histori hasil
  (`generated_outputs`), dan data "kerja" terbaru (mis. 3–6 bulan
  terakhir). Untuk riwayat lama, Cogan query langsung ke Solr saat
  diminta, tanpa menyalin semuanya.

Pilihan B jauh lebih hemat untuk jangka panjang, tapi butuh tahu **cara
Solr bisa diakses** (API? kredensial? rate limit?) dari tim IT. Desain
saat ini sudah siap untuk B: tinggal ubah isi `db.fetch_posts_df()` agar
sebagian menarik dari Solr — tool lain tidak tersentuh.

**Rekomendasi:** jalan dengan A sekarang (sudah jadi, bisa demo), dan
tanyakan akses Solr ke IT untuk memutuskan B nanti. Ini poin yang tepat
disampaikan ke atasan: keputusan ini yang paling memengaruhi biaya
jangka panjang, bukan sekadar "ukuran VM".

---

## 6. Apakah ini sudah siap skala besar?

Sudah ditangani:
- **Banyak request bersamaan** → ada connection pool di `db.py`.
- **Filter cepat di jutaan baris** → index `(client_id, post_date)` dan
  `(client_id, channel)`; penyaringan tanggal/channel dikerjakan di sisi
  database, bukan menarik semua baris ke Python.
- **`find_project`** memakai agregat SQL (COUNT/MIN/MAX), tidak menarik
  semua baris.
- **Muat data massal** → COPY + batch.

Catatan jujur (pekerjaan lanjutan, belum mendesak):
- Penghitungan kandidat wordcloud masih mengulang baris **di Python**.
  Untuk satu periode normal (ribuan–puluhan ribu post) aman. Tapi kalau
  satu wordcloud benar-benar mencakup jutaan post sekaligus, ini akan
  berat **terlepas dari** database apapun. Solusi nanti: batasi periode,
  atau geser perhitungan term ke sisi SQL / tabel term yang dipra-hitung.
- **Partisi tabel per bulan** (declarative partitioning) berguna saat
  total sudah puluhan juta baris. Belum dipasang sekarang karena menambah
  beban maintenance untuk satu orang; index sudah cukup untuk tahap awal.
  Bisa ditambah belakangan tanpa mengubah tool.
