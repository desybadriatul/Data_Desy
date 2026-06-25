# Cara Bikin Cogan Bisa Dipakai Orang Lain (Deploy ke Cloud)

Tujuan akhir: server Cogan kamu punya alamat URL (kayak alamat web), nyala
24 jam, dan orang lain bisa "Connect" pakai akun Claude mereka masing-masing
— tanpa install apapun di laptop mereka.

## TAHAP 1 — Push project ke GitHub

1. Buat repository baru di github.com, pilih **Private**
2. Lewat GitHub Desktop: File > Add Local Repository > pilih folder ini
3. Commit, lalu Push origin

## TAHAP 2 — Daftar Railway & deploy

1. Buka railway.com, Login with GitHub
2. New Project > Deploy from GitHub repo > pilih repo kamu
3. Tunggu build selesai
4. Settings > Networking > Generate Domain — simpan URL ini
5. URL lengkap untuk connector: `https://<url-railway-kamu>/mcp`

server.py di folder ini SUDAH mendukung dua mode otomatis:
- Lokal (laptop, lewat Claude Desktop) -> stdio
- Cloud (Railway, otomatis terdeteksi dari env var PORT) -> HTTP

Jadi tidak perlu ubah kode apapun untuk pindah dari lokal ke cloud.

## TAHAP 3 — Tambahkan sebagai Connector

1. Organization Settings > Connectors > Add > Custom > Web
2. Masukkan URL dari Tahap 2 (yang sudah ditambah /mcp)
3. Anggota tim lain: Settings > Connectors > cari "Cogan" > Connect

## Catatan penting

- Repo GitHub WAJIB private (ada data client di folder data/)
- Railway trial: $5 kredit gratis 30 hari, kartu kredit wajib didaftarkan
  untuk verifikasi (tidak langsung ditagih)
- File hasil (PNG/CSV) tersimpan di server cloud, bukan di laptop user —
  ini perlu dipikirkan lebih lanjut kalau mau lebih nyaman diakses
