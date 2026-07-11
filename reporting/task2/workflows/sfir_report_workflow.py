"""
Task 2 workflow: Spokesperson Intelligence Report (SFIR).

Berbeda dari Industry Trend / BCE: SFIR tidak memerlukan topic enrichment,
melainkan **spokesperson enrichment**. Alur preflight-nya mengikuti pola yang
Fuji tetapkan untuk MMR.

State machine (Claude memanggil ulang tiap tahap):
  1. Audience belum ada        -> NEEDS_AUDIENCE                     (tanya user)
  2. Cache spokesperson kurang -> NEEDS_AUTO_SPOKESPERSON_ENRICHMENT (Claude ekstraksi)
  3. Data siap                 -> DATA_PREVIEW_READY                 (tunggu konfirmasi)
  4. User konfirmasi           -> PACKAGE_READY                      (paket siap-PPT)

Prinsip:
- SFIR hanya berlaku untuk Online Media / Print. Bukan media sosial.
- Workflow TIDAK memanggil LLM sendiri; dia mengembalikan instruksi untuk Claude.
- Tidak pernah membuat PPTX sebelum user melihat data preview.
- Report ini menyebut NAMA ORANG SUNGGUHAN. Kalau tidak ada juru bicara yang
  benar-benar mewakili brand, report tidak dibuat (status NOT_RENDERABLE).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

from reporting.task1.report_input_dispatcher import prepare_report_input
from reporting.task2.renderers.sfir_report_renderer import (
    audience_clarification_payload,
    build_sfir_report_data_preview,
    build_sfir_report_package,
    normalize_audience_context,
)

WORKFLOW_VERSION = "sfir_report_workflow_v1"
REPORT_TYPE_ID = "spokesperson_intelligence"
SFIR_CHANNEL = "Online Media"

# Batas batch yang dikirim ke Claude sekali jalan.
MAX_ENRICHMENT_BATCH = 25


class SFIRWorkflowError(RuntimeError):
    """Raised when the SFIR workflow cannot proceed safely."""


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _csv_list(value: str | Iterable[str] | None) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(item).strip() for item in value if str(item).strip()]


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _clean(value).casefold()).strip("_") or "project"


def _period_label(start_date: str, end_date: str) -> str:
    return f"{start_date} → {end_date}" if start_date != end_date else start_date


def _base_payload(status: str, project_name: str, start_date: str,
                  end_date: str, audience: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "success": False,
        "workflow_version": WORKFLOW_VERSION,
        "workflow_status": status,
        "report_type_id": REPORT_TYPE_ID,
        "project_name": project_name,
        "period": {"start_date": start_date, "end_date": end_date},
        "audience_context": dict(audience),
    }


def _enrichment_state(project_name: str, start_date: str, end_date: str,
                      brand: str, competitors: list[str]) -> dict[str, Any]:
    """Hitung berapa artikel kandidat yang belum ter-enrich. Tidak memanggil LLM."""
    from reporting.enrichment.topic_batch_builder import get_enriched_scope_posts
    from reporting.enrichment.spokesperson_enrichment import (
        build_spokesperson_enrichment_candidates,
    )
    from reporting.enrichment.spokesperson_enrichment_store import (
        load_cached_spokesperson_results,
    )

    posts = get_enriched_scope_posts(
        project_name=project_name,
        start_date=start_date,
        end_date=end_date,
        channels=[SFIR_CHANNEL],
    )["posts"]
    if not posts:
        return {"articles": 0, "candidates": [], "sampling": {},
                "cached": 0, "missing": []}

    universe = [brand] + [c for c in competitors if c != brand]
    result = build_spokesperson_enrichment_candidates(posts, campaign_universe=universe)
    candidates = result.get("candidates") or []

    cached = load_cached_spokesperson_results(candidates)
    cached_ids: set[str] = set()
    if isinstance(cached, dict):
        for row in cached.values():
            cached_ids.add(str(row.get("canonical_post_id")))

    missing = [c for c in candidates
               if str(c.get("canonical_post_id")) not in cached_ids]

    return {
        "articles": len(posts),
        "candidates": candidates,
        "sampling": {
            "eligible_count": result.get("eligible_count"),
            "sample_size": result.get("sample_size"),
            "selected_count": result.get("selected_count"),
            "policy": result.get("selection_policy"),
        },
        "cached": len(cached_ids),
        "missing": missing,
    }


def _enrichment_payload(*, project_name: str, start_date: str, end_date: str,
                        brand: str, audience: Mapping[str, Any],
                        state: Mapping[str, Any]) -> dict[str, Any]:
    from reporting.enrichment.spokesperson_enrichment import (
        SPOKESPERSON_EXTRACTION_CONTRACT,
    )

    missing = list(state["missing"])[:MAX_ENRICHMENT_BATCH]
    batch = [{
        "canonical_post_id": c.get("canonical_post_id"),
        "content_hash": c.get("content_hash"),
        "media_name": c.get("media_name"),
        "title": c.get("title"),
        "spokesperson_raw": c.get("spokesperson_raw"),
        "llm_context": c.get("llm_context"),
    } for c in missing]

    payload = _base_payload("NEEDS_AUTO_SPOKESPERSON_ENRICHMENT",
                            project_name, start_date, end_date, audience)
    payload.update({
        "requires_user_action": False,
        "requires_claude_action": True,
        "brand": brand,
        "spokesperson_sampling": state.get("sampling"),
        "cached_article_count": state["cached"],
        "remaining_article_count": len(state["missing"]),
        "extraction_contract": SPOKESPERSON_EXTRACTION_CONTRACT,
        "enrichment_batch": batch,
        "assistant_next_steps": [
            "Jangan minta user memahami enrichment. Lanjutkan otomatis.",
            "Untuk SETIAP artikel di enrichment_batch, ekstraksi juru bicara "
            "dari llm_context sesuai extraction_contract.",
            "HANYA orang bernama yang dikutip atau diatribusikan berbicara. "
            "Perusahaan, asosiasi, lembaga, outlet media, dan netizen anonim "
            "BUKAN juru bicara.",
            "Pisahkan spokesperson_name, spokesperson_role, dan organization. "
            "Jangan gabung jadi satu string.",
            f"Isi represented_campaign HANYA bila orang tersebut berbicara "
            f"mewakili '{brand}'. Selain itu null. Ini mencegah report menyebut "
            "orang yang kebetulan dikutip sebagai juru bicara brand.",
            "Artikel tanpa juru bicara -> status not_relevant.",
            "Organisasi bicara tanpa nama orang -> status review_needed.",
            "Simpan lewat save_spokesperson_enrichment_results(response, "
            "candidates=candidates).",
            "Lalu panggil create_sfir_report_workflow lagi dengan audience sama.",
            "Jangan buat PPTX dulu; workflow harus menampilkan data preview.",
        ],
        "user_visible_progress_message": (
            f"Saya sedang mengekstraksi juru bicara dari artikel {SFIR_CHANNEL}, "
            "lalu menampilkan preview data sebelum PPT."
        ),
    })
    return payload


def _needs_ppt_confirmation(preview: Mapping[str, Any], ask_before_pptx: bool) -> bool:
    """Report dengan caveat WAJIB dikonfirmasi user sebelum dibuat PPTX."""
    if ask_before_pptx:
        return True
    readiness = str(preview.get("readiness") or "")
    return readiness in {"READY_WITH_THIN_EVIDENCE", "READY_WITH_LIMITATIONS"}


def create_sfir_report_workflow(
    *,
    project_name: str,
    start_date: str,
    end_date: str | None = None,
    audience: str | None = None,
    report_pov: str | None = None,
    client_brand: str | None = None,
    competitor_brands: str | Iterable[str] | None = None,
    auto_enrichment_enabled: bool = True,
    force_skip_enrichment: bool = False,
    confirm_pptx: bool = False,
    ask_before_pptx: bool = True,
    persist: bool = True,
) -> dict[str, Any]:
    """Satu perintah untuk membuat Spokesperson Intelligence Report end-to-end."""
    project_name = _clean(project_name)
    start_date = _clean(start_date)
    end_date = _clean(end_date) or start_date
    if not project_name or not start_date:
        raise SFIRWorkflowError("project_name dan start_date wajib diisi.")

    period_label = _period_label(start_date, end_date)
    brand = _clean(client_brand) or project_name
    competitors = _csv_list(competitor_brands)

    # --- TAHAP 1: audience wajib ---
    if not _clean(audience) and not _clean(report_pov):
        payload = audience_clarification_payload(project_name, period_label)
        payload["workflow_version"] = WORKFLOW_VERSION
        payload["report_type_id"] = REPORT_TYPE_ID
        payload["requires_user_action"] = True
        payload["requires_claude_action"] = False
        payload["note"] = (
            "Audience wajib karena narasi, action plan, dan level detail "
            "report akan disesuaikan."
        )
        return payload

    audience_ctx = normalize_audience_context(audience, report_pov)

    # --- TAHAP 2: preflight spokesperson enrichment ---
    if auto_enrichment_enabled and not force_skip_enrichment:
        try:
            state = _enrichment_state(project_name, start_date, end_date,
                                      brand, competitors)
        except Exception as exc:
            payload = _base_payload("SPOKESPERSON_ENRICHMENT_ERROR", project_name,
                                    start_date, end_date, audience_ctx)
            payload.update({
                "requires_user_action": False,
                "requires_claude_action": False,
                "error": str(exc),
                "fallback_instruction": (
                    "Lanjutkan prepare report dengan cache yang tersedia; "
                    "SFIR akan menampilkan limitation bila data tidak cukup."
                ),
            })
            return payload

        if state["articles"] == 0:
            payload = _base_payload("NO_ONLINE_MEDIA_ARTICLES", project_name,
                                    start_date, end_date, audience_ctx)
            payload.update({
                "requires_user_action": True,
                "requires_claude_action": False,
                "note": (
                    f"Campaign '{project_name}' tidak memiliki artikel "
                    f"{SFIR_CHANNEL} pada periode ini. SFIR membutuhkan data "
                    "pemberitaan media. Coba campaign lain atau perluas periode."
                ),
            })
            return payload

        if state["missing"]:
            return _enrichment_payload(
                project_name=project_name, start_date=start_date,
                end_date=end_date, brand=brand, audience=audience_ctx, state=state,
            )

    # --- TAHAP 3: jalankan Task 1 & tampilkan preview ---
    request: dict[str, Any] = {
        "project_name": project_name,
        "start_date": start_date,
        "end_date": end_date,
        "client_brand": brand,
        "channels": [SFIR_CHANNEL],
        "confirmed_intent_id": f"{WORKFLOW_VERSION}:{_slug(project_name)}",
    }
    if competitors:
        request["competitor_brands"] = competitors

    try:
        report_input = prepare_report_input(
            report_type_id=REPORT_TYPE_ID, request=request, persist=persist,
        )
    except Exception as exc:
        payload = _base_payload("TASK1_FAILED", project_name, start_date,
                                end_date, audience_ctx)
        payload["error"] = str(exc)
        payload["requires_user_action"] = True
        payload["requires_claude_action"] = False
        return payload

    report_input_id = report_input.get("report_input_id")
    if not report_input_id:
        raise SFIRWorkflowError(
            "Task 1 tidak mengembalikan report_input_id; tidak bisa lanjut."
        )

    # Renderer membaca report_input dari storage. Kalau Task 1 tidak menyimpan
    # (persist=False), report_input hanya ada di memori dan renderer tidak akan
    # menemukannya. Beri tahu pemanggil dengan jelas, bukan error "tidak ditemukan".
    if not persist:
        payload = _base_payload("NEEDS_PERSIST", project_name, start_date,
                                end_date, audience_ctx)
        payload.update({
            "requires_user_action": True,
            "requires_claude_action": False,
            "report_input_id": report_input_id,
            "note": (
                "report_input tidak disimpan (persist=False), sehingga tahap "
                "preview & package tidak dapat membacanya. Panggil ulang dengan "
                "persist=True untuk melanjutkan sampai PPTX."
            ),
        })
        return payload

    preview = build_sfir_report_data_preview(
        report_input_id, audience_context=audience, audience_pov=report_pov,
    )

    # SFIR menyebut nama orang. Kalau tak ada juru bicara brand, berhenti.
    if preview.get("readiness") == "NOT_RENDERABLE":
        payload = _base_payload("NOT_RENDERABLE", project_name, start_date,
                                end_date, audience_ctx)
        payload.update({
            "requires_user_action": True,
            "requires_claude_action": False,
            "report_input_id": report_input_id,
            "data_preview": preview,
            "note": (
                f"Tidak ditemukan juru bicara yang berbicara mewakili '{brand}' "
                "pada periode ini. SFIR tidak dibuat agar report tidak menyebut "
                "orang yang tidak pernah mewakili brand."
            ),
            "limitations": preview.get("limitations"),
        })
        return payload

    if not confirm_pptx and _needs_ppt_confirmation(preview, ask_before_pptx):
        payload = _base_payload("DATA_PREVIEW_READY", project_name,
                                start_date, end_date, audience_ctx)
        payload.update({
            "requires_user_action": True,
            "requires_claude_action": False,
            "report_input_id": report_input_id,
            "data_preview": preview,
            "confirmation_question": (
                f"Data preview SFIR {project_name} ({period_label}) sudah siap. "
                "Lanjut buat PPTX?"
            ),
            "assistant_next_steps": [
                "Tampilkan data_preview.markdown ke user.",
                "Sampaikan readiness & limitations apa adanya, termasuk nama "
                "yang TIDAK dihitung sebagai juru bicara brand.",
                "Jangan buat PPTX sebelum user setuju.",
                "Setelah user setuju, panggil workflow ini lagi dengan "
                "confirm_pptx=True.",
            ],
        })
        return payload

    # --- TAHAP 4: paket siap-PPT ---
    package = build_sfir_report_package(
        report_input_id, audience_context=audience, audience_pov=report_pov,
    )
    return {
        "success": True,
        "workflow_version": WORKFLOW_VERSION,
        "workflow_status": "PACKAGE_READY",
        "report_type_id": REPORT_TYPE_ID,
        "project_name": project_name,
        "period": {"start_date": start_date, "end_date": end_date},
        "audience_context": dict(audience_ctx),
        "report_input_id": report_input_id,
        "data_preview": preview,
        "ppt_package": package,
        "assistant_next_steps": [
            "Render PPTX dari ppt_package.slides sesuai ppt_style_brief.",
            "Jangan mengarang nama, jabatan, kutipan, atau URL.",
            "Jangan menyebut nama di luar qt_sfir_top5_spokesperson_rank "
            "sebagai juru bicara brand.",
            "Sertakan source_url pada setiap kutipan.",
        ],
    }


__all__ = [
    "create_sfir_report_workflow",
    "SFIRWorkflowError",
    "WORKFLOW_VERSION",
]
