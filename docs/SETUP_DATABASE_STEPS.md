# Cara Setup Database Cogan — Langkah per Langkah

Panduan ini ditulis untuk diikuti tanpa perlu paham kode. Cukup ikuti
urutannya. Yang kamu butuhkan: akun Railway (tempat Cogan sudah dideploy)
dan komputermu.

Gambaran besarnya cuma 3 hal:
1. Nyalakan "gudang" (database) di Railway — beberapa klik.
2. Buat rak/lemarinya (tabel) — 1 perintah.
3. Masukkan datamu — 1 perintah.

Setelah itu, setiap mau nambah data, kamu cukup ulang langkah 3.

---

## BAGIAN A — Nyalakan database di Railway (klik-klik, tanpa kode)

1. Buka project Cogan kamu di railway.com.
2. Klik tombol **+ New** (atau **+ Create**) di dalam project itu.
3. Pilih **Database** → **Add PostgreSQL**.
4. Tunggu sebentar sampai muncul kotak baru bernama "Postgres". Itu
   gudangmu. Sudah nyala.

Sekarang sambungkan gudang itu ke server Cogan:

5. Klik kotak **service Cogan** kamu (yang servernya, bukan yang Postgres).
6. Buka tab **Variables**.
7. Klik **+ New Variable** → **Add Reference** → pilih **DATABASE_URL**
   dari Postgres. Simpan.
8. Railway akan otomatis men-deploy ulang Cogan. Saat menyala, server
   otomatis membuat semua tabel yang dibutuhkan. (Kamu tidak perlu apa-apa
   di sini.)

> DATABASE_URL itu ibarat "alamat + kunci" gudang. Server Cogan butuh ini
> untuk masuk ke gudang. Railway mengisinya otomatis.

---

## BAGIAN B — Siapkan komputermu (sekali saja)

Untuk memasukkan data, kamu menjalankan 1 perintah dari komputer. Perlu
disiapkan sekali:

1. Pastikan **Python** terpasang (cek dengan mengetik `python --version`
   di Terminal / Command Prompt). Kalau belum ada, unduh dari python.org.
2. Buka folder project Cogan di Terminal, lalu pasang komponennya:
   ```
   pip install -r requirements.txt
   ```

### Ambil "alamat gudang" (DATABASE_URL) untuk komputermu
3. Di Railway, klik kotak **Postgres** → tab **Variables** (atau
   **Connect**) → cari **DATABASE_URL** versi publik/eksternal → klik
   salin.
4. Di Terminal, tempelkan seperti ini (ganti bagian setelah `=` dengan
   yang kamu salin):
   - Mac/Linux:
     ```
     export DATABASE_URL='postgresql://....paste di sini....'
     ```
   - Windows (PowerShell):
     ```
     $env:DATABASE_URL='postgresql://....paste di sini....'
     ```

> Catatan: kamu perlu menempelkan ulang DATABASE_URL ini setiap kali buka
> Terminal baru. Itu normal.

---

## BAGIAN C — Buat tabel & masukkan data

Jalankan dari dalam folder project Cogan.

1. Buat tabel (aman walau diulang):
   ```
   python -m database.load_excel --init
   ```

2. Taruh file Excel datamu (format 56 kolom) ke dalam folder `data/`.
   Lalu masukkan:
   ```
   python -m database.load_excel --file data/namafilemu.xlsx
   ```
   Atau, kalau ada banyak file Excel sekaligus di folder `data/`:
   ```
   python -m database.load_excel --folder data
   ```

3. Selesai. Data sudah di gudang. Kolom **Campaigns** otomatis dipecah per
   koma, jadi satu post yang punya beberapa campaign tercatat ke semua
   campaign-nya.

### Kalau mau mulai dari nol (hapus data lama dulu)
Berguna saat masih testing dan mau bersih-bersih:
```
python -m database.load_excel --reset --folder data
```
`--reset` mengosongkan semua post lama, lalu memasukkan yang baru.

---

## BAGIAN D — Mengecek hasilnya lewat Cogan (tanpa kode)

Buka Claude yang terhubung connector Cogan, lalu ketik misalnya:
- "Pakai Cogan, campaign apa saja yang tersedia?"
- "Buat wordcloud campaign Aqua periode Oktober."

Cogan akan membaca langsung dari gudang. Temanmu yang pakai connector
tidak perlu upload data apa-apa.

---

## Yang sering bikin bingung (FAQ singkat)

**Apakah datanya harus saya isi semua 56 kolom?**
Tidak. Yang penting terisi: Campaigns, Date, Content. Channel, Title,
Sentiment, Engagement sangat membantu. Sisanya boleh kosong.

**Kalau nama campaign ketulis beda (huruf besar/kecil, ada spasi)?**
Otomatis dianggap sama. "Aqua", "aqua", dan " Aqua " masuk ke campaign
yang sama.

**Saya jalankan loader dua kali, datanya jadi dobel?**
Bisa. Kalau mau aman saat testing, pakai `--reset` supaya mulai bersih.

**Apakah saya merusak sesuatu kalau salah?**
Tidak gampang rusak. Perintah `--init` aman diulang. Kalau ragu, `--reset`
lalu muat ulang dari file Excelmu — file Excelmu tetap jadi sumber asli.

**Kapan butuh ke tim IT?**
Hanya nanti, kalau memutuskan data sebagian ditarik langsung dari Solr
(bukan disalin ke gudang). Sekarang tidak perlu — kita pakai file Excel
yang kamu siapkan.
