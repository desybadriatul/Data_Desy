# Daily Social Workflow v3 Test Guide

## Tool baru

`create_daily_social_report_workflow`

Tujuan: supaya user tidak perlu prompt panjang. User cukup menyebut project dan tanggal. Tool akan mengorkestrasi Task 1, preview data, Task 2 outline, dan package PPT-ready.

## Behavior penting

Jika `audience` kosong dan `require_audience=True`, tool harus return:

```json
{
  "workflow_status": "NEEDS_AUDIENCE",
  "needs_clarification": true,
  "clarification_question": "Report ini dibuat untuk siapa?..."
}
```

Claude harus bertanya ke user dulu, bukan membuat report.

## Audience examples

- PR / Corporate Communications
- Insight / Analyst Team
- Management
- CEO / Board
- Social Care / Customer Care
- Marketing / Content Team
- Brand Team

## Test prompt di Claude

### Prompt pendek tanpa audience

```text
Buatkan Daily Social Media Report BlueBird tanggal 2026-06-10.
```

Expected: Claude tanya dulu report untuk siapa.

### Setelah user jawab

```text
Untuk tim PR/Corcom.
```

Expected: Claude call workflow dengan audience `PR/Corcom`, tampilkan preview data, lalu tanya apakah lanjut PPTX.

### Prompt pendek dengan audience langsung

```text
Buatkan Daily Social Media Report BlueBird tanggal 2026-06-10 untuk tim PR/Corcom. Tampilkan preview dulu sebelum PPT.
```

Expected: Claude langsung membuat preview + package, tanpa enrichment batch tambahan.

## Usage safety

Workflow ini tidak menjalankan:

- `get_unclassified_topic_batch`
- `save_topic_batch_results`

Jadi workflow tidak menghabiskan Claude usage untuk klasifikasi topic. Ia hanya memakai taxonomy/cache yang sudah ada.
