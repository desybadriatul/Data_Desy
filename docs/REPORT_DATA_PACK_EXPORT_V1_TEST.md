# Report Data Pack Export v1

Patch ini menambahkan export audit/evidence data pack untuk report Task 1.

## Tools MCP baru

- `export_report_data_pack`
- `export_raw_scope_data`

## Fungsi utama

`export_report_data_pack(report_input_id)` membuat file Excel/CSV ZIP berisi:

- scope report
- validation
- limitations
- evidence log
- semua quantitative views (`qt_*`)
- semua qualitative views (`ql_*`)
- optional raw canonical data sesuai scope report

Default output: `.xlsx`. Jika dependency writer Excel tidak tersedia, exporter fallback ke `.zip` berisi CSV per sheet.

## Kenapa perlu

PPT report tidak cukup untuk audit angka. Data pack memberi user file pendukung agar angka di report dapat dicek ulang dari Task 1 dan raw canonical rows.

## Test lokal

```powershell
python -m py_compile .\reporting\exports\report_data_pack_exporter.py
python -m py_compile .\scripts\patch_server_report_data_pack_export_v1.py
python -m py_compile .\scripts\test_report_data_pack_export_v1.py
python .\scripts\test_report_data_pack_export_v1.py
```

## Prompt Claude final

Setelah report preview/PPT selesai, user bisa bilang:

> Export data pack report ini ke Excel, termasuk raw data dan semua Task 1 views.

Claude harus memanggil:

```text
export_report_data_pack(report_input_id=<id>, output_format="xlsx", include_raw_data=true)
```

Untuk file download di chat, Claude dapat meminta `include_file_base64=true` jika ukuran file memungkinkan, lalu membuat attachment dari base64 tersebut.

## Catatan batasan

- Raw data export default dibatasi `raw_row_limit` agar tidak membebani DB/MCP.
- Untuk data sangat besar, gunakan `output_format="csv_zip"` atau row limit yang lebih kecil.
- Export berdasarkan `report_input_id` lebih aman daripada raw scope karena scope-nya sama dengan report yang dibuat.
