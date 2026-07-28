# Sonar / Cogan MCP Server

Server pusat yang menghubungkan Claude/LLM dengan tools otomasi internal Sonar
(Dataxet) — wordcloud, weekly report, dan ke depannya presales brief,
onboarding form, dll.

## Stack teknis

Python + MCP Python SDK (FastMCP). Python TIDAK memanggil Claude API —
Claude yang memanggil tool Python ini, memakai quota akun Claude milik user.
Python hanya bertugas: baca data, hitung, dan buat file output.

## Cara kerja singkat

1. Tim CX chat ke Claude (lewat connector "Cogan").
2. Claude memanggil tool yang sesuai (lihat `tools/`).
3. Tool membaca data (`data/`) + panduan (`config/` atau `skills/`).
4. Claude menyeleksi/mengolah hasil berdasarkan panduan tersebut.
5. Tool membuat file output (`output/`), Claude menampilkan ke user.

## Status saat ini (lihat docs/STATUS.md untuk tahapan detail)

Tahapan WAJIB urut: ping_cogan() dulu (buktikan connector hidup) → baru
lanjut find_project → guidance → candidates → render. Jangan loncat.

## Struktur folder

```
sonar-mcp/
├── server.py                  <- entry point MCP server (belum dibuat)
├── tools/                     <- satu folder = satu kemampuan (logic Python)
│   ├── wordcloud/
│   └── weekly_report/
├── skills/                    <- panduan tertulis CARA Claude menyeleksi/mengerjakan
├── data/                      <- raw data per client (Excel dulu, nanti DB)
│   └── imip/
├── config/                    <- guidance per client (JSON, nanti tabel DB)
├── output/                    <- hasil PNG/CSV wordcloud & report
├── database/                  <- untuk versi database nanti (SQLite)
└── docs/                      <- dokumen pendukung (status, rancangan DB, dll)
```

## Cara nambah kemampuan baru (misal request dari tim produk)

1. Buat folder baru di `tools/nama_tool_baru/`
2. Tulis skill panduannya di `skills/skill_nama_tool_baru.md`
3. Daftarkan tool baru itu di `server.py`
4. Tidak perlu ubah tool yang sudah ada — semuanya independen

