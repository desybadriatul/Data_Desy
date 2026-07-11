# Report Enrichment Registry V1

## Tujuan

Mengunci kebutuhan enrichment di code agar Claude tidak menebak jalur report:

| Report | Topic/taxonomy | Spokesperson |
|---|---:|---:|
| Daily Social Media Report | Ya | Tidak |
| Competitive Analysis | Ya | Tidak |
| Mainstream Media Report | Ya | Ya, setelah topic siap |

## Guardrail

- Target topic adalah target terkunci dan tidak boleh diperluas otomatis.
- Hard cap Daily Social = 100 post.
- Hard cap Competitive Analysis = 150 canonical row.
- Hard cap Mainstream Media Report = 100 artikel.
- Tool spokesperson menolak `report_type_id` yang tidak mengizinkan spokesperson.
- Setiap continuation state dan preview membawa `enrichment_requirements`.
- CA main slide memakai link klik `Buka post` / `Lihat post`; Evidence ID dan full URL hanya di appendix/data pack.

## File

- `reporting/enrichment/report_enrichment_registry.py`
- `reporting/task2/workflows/daily_social_report_workflow.py`
- `reporting/task2/workflows/competitive_analysis_report_workflow.py`
- `reporting/task2/workflows/mainstream_media_report_workflow.py`
- `server.py`
- `scripts/test_report_enrichment_registry_v1.py`
