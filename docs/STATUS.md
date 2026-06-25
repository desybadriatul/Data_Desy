# Status Project

Update file ini setiap kali ada progress. Supaya kalau ditanya atasan,
tinggal buka file ini dan tidak perlu mengingat manual.

## Fase 1 - Tahapan teknis

| Tahap | Item | Status | Catatan |
|---|---|---|---|
| 0 | Setup struktur project | DONE | folder skeleton sudah dibuat |
| 0 | Skill panduan wordcloud | DONE (draft) | lihat `skills/skill_wordcloud.md`, masih bisa direvisi |
| 1 | Tool `ping_cogan()` | DONE | berhasil di Claude Desktop: "Cogan is connected." |
| 2 | Tool `find_project("AQUA")` | DONE | baca dari `data/aqua/raw_data.xlsx` |
| 3 | Tool `get_project_wordcloud_guidance()` | DONE | baca `config/aqua_wordcloud_guidance.json` |
| 4 | Tool `get_wordcloud_candidates()` | DONE | baca Excel, hitung kandidat frasa |
| 5 | Claude menyeleksi term | READY | bisa dilakukan dari kandidat yang dihitung tool |
| 6 | Tool `render_wordcloud()` | DONE | hasil PNG + CSV ke `output/` |
| - | Tool generate_weekly_report | BLOCKED | menunggu skill report dari rekan tim |
| - | Deploy ke hosting | NOT STARTED | baru perlu setelah demo lokal sukses |

## Fase 2

- generate_presales_brief
- generate_onboarding_form
- client_journey_tracker
- tool ad-hoc lain dari request tim produk

## Log perubahan

- [2026-06-24] Project skeleton dibuat. Struktur folder: tools/, skills/,
  database/, docs/.
- [2026-06-24] MCP lokal berhasil tersambung ke Claude Desktop.
- [2026-06-24] Data AQUA ditambahkan dan tool wordcloud end-to-end dibuat:
  find project, guidance, candidates, dan render PNG/CSV.
- [2026-06-25] Database PostgreSQL dirancang & dibangun (folder database/):
  schema.sql (pola kolom inti + JSONB), db.py (akses + connection pool),
  load_excel.py (loader COPY + normalisasi antar-klien), column_mapping.json.
  server.py disambungkan ke database (find_project pakai agregat SQL,
  fetch tersaring di sisi DB, histori hasil disimpan ke generated_outputs,
  tool baru get_recent_outputs). Panduan: docs/DATABASE_SETUP.md.
  Belum dijalankan di Postgres asli (menunggu service DB di Railway).
