# Rancangan Database (Draft)

> CATATAN: Dokumen ini draft awal (rencana SQLite/Excel dulu). Sejak
> diputuskan langsung pakai PostgreSQL managed untuk skala besar, panduan
> yang berlaku ada di **docs/DATABASE_SETUP.md** dan implementasinya di
> folder **database/**. Dokumen ini disimpan sebagai catatan ide awal.

## Prinsip: mulai dari FILE, bukan database besar

Minggu ini fokusnya membuktikan connector-nya jalan dulu (lihat
`docs/STATUS.md` — tahapan ping_cogan → find_project → candidates →
render). Jadi untuk sekarang:

- Raw data: file Excel (`data/<client>/raw_data.xlsx`)
- Panduan wordcloud per client: file JSON (`config/<client>_wordcloud_guidance.json`)

Excel/JSON ini SAH dipakai dulu. Database (SQLite) baru dipakai setelah flow
sudah stabil — gantinya tinggal ganti "cara baca data" di tool Python,
cara CX minta hasil di Claude TIDAK berubah.

## Konsep besar: database BUKAN cuma raw data

Begitu pindah ke database, bentuknya bukan 1 tabel raksasa. Tiap jenis
informasi punya "kotak" (tabel) sendiri, dan tiap kotak punya tool MCP yang
bertugas membaca/menulis ke kotak itu. Supaya nanti ada fitur baru, kamu
cukup nambah kotak + tool baru tanpa ganggu yang lain.

| Tabel | Isinya | Tool terkait (sekarang/nanti) |
|---|---|---|
| `projects` | daftar client/project (IMIP, Le Minerale, dst) + periode data tersedia | `find_project()` |
| `project_guidance` | objective + include/exclude rules wordcloud per client (ganti dari file JSON) | `get_project_wordcloud_guidance()` |
| `raw_data` | data mentahan monitoring (ganti dari Excel) | `get_wordcloud_candidates()` |
| `company_research` | hasil riset cogan — bentuk bebas (teks/json), terserah Claude saat generate | tool baru (Fase 2) |
| `generated_outputs` | histori semua wordcloud/report yang pernah dibuat (biar tidak generate ulang dari nol) | `render_wordcloud()` menyimpan ke sini |

## Urutan migrasi yang disarankan

1. **Sekarang:** Excel + JSON untuk 1 client (IMIP) — buktikan flow jalan.
2. **Setelah stabil:** pindahkan `raw_data` dan `project_guidance` ke SQLite,
   masih untuk wordcloud saja.
3. **Setelah itu:** tambah tabel `generated_outputs` supaya ada histori.
4. **Fase 2:** tambah `company_research` dan tabel lain sesuai fitur baru
   (presales, onboarding form, dll) — tanpa mengubah tabel yang sudah ada.

## Yang masih perlu didiskusikan

- Format isi `company_research` — teks bebas atau terstruktur? (catatan:
  ini fleksibel, "serahin ke Claude" sesuai keputusan awal)
- Apakah `raw_data` ke depannya ditarik otomatis dari vendor scraping
  (Bright Data, dst) atau tetap upload manual per periode?

