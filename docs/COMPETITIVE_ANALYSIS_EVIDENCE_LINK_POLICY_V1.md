# Competitive Analysis Evidence Link Policy v1

Patch ini membuat Competitive Analysis lebih aman untuk user awam:

1. Audience tetap ditanya satu kali.
2. Jika user menjawab `gak tau`, `terserah`, `umum`, atau `semua aja`, workflow memakai default `Marketing / Brand Team`.
3. Main slide tidak lagi mengandalkan Evidence ID sebagai UI utama.
4. Evidence di main slide harus dirender sebagai tombol/link manusiawi: `Buka post` atau `Lihat post`.
5. Tombol tersebut harus hyperlink ke `source_url`.
6. Evidence ID dan URL penuh tetap disimpan di Appendix/Data Pack untuk audit.
7. Renderer membuat satu evidence registry canonical dengan format `E01`, `E02`, dst supaya tidak ada campuran `P##`, `T##`, `E##` di main slide.
8. Render package membawa `quality_checks.evidence_integrity` agar Claude/MCP bisa melihat apakah package siap dirender.
9. Jika topic coverage rendah, package membawa `topic_coverage_policy` dan Claude wajib memakai wording `classified sample`, bukan klaim sensus penuh.

## Expected behavior di PPT

Main slide:

```text
“hubungan kita sampai sini saja ya”
TikTok · negatif
[Buka post]
```

Appendix/Data Pack:

```text
E04 = https://www.tiktok.com/...
```

## Test lokal

```powershell
python -m py_compile .\server.py
python -m py_compile .\reporting\task2\renderers\competitive_analysis_report_renderer.py
python -m py_compile .\reporting\task2\workflows\competitive_analysis_report_workflow.py
python -m py_compile .\scripts\test_competitive_analysis_evidence_link_policy_v1.py
python .\scripts\test_competitive_analysis_evidence_link_policy_v1.py
```

Expected:

```text
AUDIENCE = Marketing / Brand Team
DEFAULT_USED = True
GOOD_STATUS = PASS
BAD_STATUS = FAIL
COMPETITIVE ANALYSIS EVIDENCE LINK POLICY V1 OK
```


## Patch v1.1

Fix QA validator agar tidak salah membaca objek `evidence_link` sebagai evidence card yang membutuhkan nested `evidence_link` lagi.
