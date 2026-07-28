"""
anomaly_tools.py — MCP tool layer untuk anomaly engine.

VERSI 1.2
  1.0 — 3 tool: scan_anomalies, list_anomaly_detectors, configure_anomaly_terms
  1.1 — docstring scan_anomalies dipasangi gate Jalur 1 / Jalur 2.
        Versi 1.0 menyebut dirinya "entry point default untuk request
        eksploratif", dan itu bertabrakan dengan Intent Confirmation:
        pertanyaan seperti "ada topik apa minggu ini?" butuh interpretasi,
        jadi WAJIB lewat gate dulu, bukan langsung scan.
  1.2 — BUG FIX: project yang tidak ditemukan dulu menghasilkan found=True
        dengan 0 finding, sehingga asisten melapor "tidak ada anomali" padahal
        datanya tidak pernah dicek. Sekarang mengembalikan found=False dengan
        error yang jelas.

Butuh: server.py dengan RUNTIME GATE dua jalur, SKILL.md >= 3.4,
       skill_report.md >= 3.3.

Modul ini SENGAJA berdiri sendiri supaya server.py hampir tidak berubah.
Pola registrasinya mengikuti workflow report yang sudah ada di server.py:

    from anomaly_tools import (
        scan_anomalies,
        list_anomaly_detectors,
        configure_anomaly_terms,
    )

    mcp.tool()(scan_anomalies)
    mcp.tool()(list_anomaly_detectors)
    mcp.tool()(configure_anomaly_terms)

Itu saja. Empat baris. `detect_spikes` dan `scan_all_anomalies` yang lama
TIDAK DISENTUH, jadi seluruh workflow report yang sudah jalan tetap aman.

GUARDRAIL TERHADAP ALUR REPORT
------------------------------
Tool ini untuk monitoring / eksplorasi. BUKAN pintu belakang untuk membuat deck.

Secara struktur output-nya memang tidak bisa dipakai membangun deck:
- tidak mengembalikan `report_input_id`;
- tidak kompatibel dengan `build_*_ppt_package`;
- tidak menyimpan apapun ke prepared report input.

Kalau hasil scan mau dinaikkan menjadi report/deck, panggil get_report_guide().
Jika user TIDAK menyebut tipe report, lanjutkan Jalur 2 dan rakit deck
dari skill; jangan otomatis memetakan hasil diagnosis ke workflow Jalur 1.
"""

from __future__ import annotations

from typing import Any, Iterable

import anomaly
from database import anomaly_queries as aq
from database import db


# ---------------------------------------------------------------------
# Helper lokal (sengaja tidak import dari server.py, hindari circular import)
# ---------------------------------------------------------------------

def _csv(value: str | Iterable[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = value.split(",")
    else:
        parts = list(value)
    return [str(item).strip() for item in parts if str(item).strip()]


def _severity_icon(severity: str) -> str:
    return {
        "critical": "CRITICAL",
        "high": "HIGH",
        "medium": "MEDIUM",
        "low": "LOW",
    }.get(severity, severity.upper())


def _headline(
    findings: list[dict[str, Any]],
    scanned: list[str] | None = None,
    not_found: list[str] | None = None,
) -> str:
    """
    Satu kalimat teratas, supaya jawaban tidak dimulai dari tabel angka.

    Wajib jujur: "nol finding" hanya boleh disebut "tidak ada anomali" bila
    datanya memang benar-benar diperiksa.
    """
    if not findings:
        if not_found:
            return (
                "Sebagian project tidak ditemukan ("
                + ", ".join(not_found)
                + "). Untuk project yang berhasil di-scan, tidak ada anomali "
                "yang melewati ambang."
            )
        if not scanned:
            return "Tidak ada project yang di-scan."
        return "Tidak ada anomali yang melewati ambang pada periode ini."

    top = findings[0]
    return (
        f"Temuan teratas ({_severity_icon(top['severity'])}) pada {top['date']}: "
        f"{top['narrative']}"
    )


# ---------------------------------------------------------------------
# TOOL 1 — scan_anomalies
# ---------------------------------------------------------------------

def scan_anomalies(
    project_name: str = "",
    project_names: str = "",
    start_date: str = "",
    end_date: str = "",
    channel: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
    sensitivity: str = "medium",
    families: str = "",
    detectors: str = "",
    max_findings: int = 25,
) -> dict[str, Any]:
    """
    Cek menyeluruh hal-hal mencurigakan pada data klien. SATU panggilan,
    17 detector sekaligus.

    POSISI TOOL INI DALAM ALUR
    --------------------------
    Ini alat DIAGNOSIS untuk JALUR 2 (top-down), dipakai SETELAH Intent
    Confirmation disetujui. Bukan pintu masuk, bukan pengganti gate.

    Alur Jalur 2 yang benar:
        get_report_guide()
          -> Intent Confirmation 8 poin, TAMPILKAN ke user, TUNGGU persetujuan
          -> validate_metric_readiness() + data_health()
          -> scan_anomalies()   <-- TOOL INI DI SINI
          -> get_posts() untuk membaca pemicunya
          -> laporkan temuan ke user
          -> rakit deck dari skill (bila output-nya deck)

    JANGAN panggil tool ini SEBELUM Intent Confirmation, bila permintaan user
    akan berujung pada kesimpulan, insight, atau rekomendasi. Contoh yang
    WAJIB lewat gate dulu:
        "ada topik apa minggu ini di brand A?"
        "apa yang terjadi pada brand A periode B?"
        "cek data brand A dan B"

    BOLEH dipanggil langsung tanpa gate HANYA untuk pengecekan operasional
    sempit yang tidak meminta interpretasi, misalnya:
        "scan semua klien, ada data yang rusak nggak?"
        "coverage bulan ini bolong nggak?"

    JANGAN memakai tool ini di JALUR 1 (user menyebut tipe report). Jalur 1
    punya alurnya sendiri: create_*_report_workflow -> Task 1 preview ->
    konfirmasi -> Task 2 -> PPT.

    Output tool ini TIDAK report-ready (tidak ada report_input_id, tidak
    kompatibel dengan build_*_ppt_package), jadi tidak bisa dipakai untuk
    menyerobot alur Jalur 1 maupun melewati Intent Confirmation Jalur 2.

    YANG DIDETEKSI (17 detector, 6 family)
    --------------------------------------
    volume         : volume_spike, volume_drop, sustained_elevation
    amplification  : interactions_spike, views_spike, engagement_concentration,
                     engagement_rate_outlier
    sentiment      : sentiment_divergence, negative_share_spike
    actors         : single_author_flood, coordinated_burst, new_author_surge
    risk_content   : trigger_term_appearance
    data_integrity : noise_contamination, coverage_gap, unclassified_surge,
                     views_interactions_ratio

    Yang paling sering terlewat oleh spike detector biasa, dan justru paling
    penting:
    - trigger_term_appearance : volume kecil, risiko besar (BPKN/YLKI/DPR/audit)
    - sentiment_divergence    : sentimen hijau tapi yang viral justru negatif
    - engagement_concentration: satu post menguasai mayoritas interaksi
    - coordinated_burst       : banyak akun, teks nyaris sama, jendela pendek
    - noise_contamination     : scope kotor, semua angka jadi tidak sah

    PARAMETER
    ---------
    project_name / project_names : satu project, atau beberapa dipisah koma.
                                   Kosongkan project_names untuk scan SEMUA project.
    sensitivity                  : low | medium | high (default medium)
    families                     : batasi ke family tertentu, dipisah koma
    detectors                    : batasi ke detector tertentu, dipisah koma

    LANGKAH BERIKUTNYA
    ------------------
    Setiap finding membawa `evidence` (canonical_key) dan `next_tool`.
    Angka tidak pernah menjadi kesimpulan — selalu baca konten pemicunya dulu
    lewat get_posts() sebelum menyampaikan apapun ke user.
    """
    names = _csv(project_names) or ([project_name] if project_name.strip() else [])
    if not names:
        names = db.list_campaigns()

    if not names:
        return {
            "found": False,
            "error": "Tidak ada project yang bisa di-scan.",
        }

    sensitivity_clean = (sensitivity or "medium").strip().lower()
    if sensitivity_clean not in {"low", "medium", "high"}:
        sensitivity_clean = "medium"

    family_filter = _csv(families)
    detector_filter = _csv(detectors)

    all_findings: list[dict[str, Any]] = []
    scanned: list[str] = []
    not_found: list[str] = []
    per_project: dict[str, Any] = {}

    for name in names:
        frames = aq.collect_frames(
            name,
            start_date or None,
            end_date or None,
            channel or None,
            keywords or None,
            exclude_keywords or None,
            match_mode or "any",
        )
        if frames is None:
            not_found.append(name)
            continue

        if not frames["daily"]:
            per_project[name] = {
                "days_analysed": 0,
                "findings": 0,
                "note": "Tidak ada post pada scope ini.",
            }
            scanned.append(name)
            continue

        context = anomaly.ScanContext(
            daily=frames["daily"],
            author_daily=frames["author_daily"],
            duplicate_clusters=frames["duplicate_clusters"],
            term_daily=frames["term_daily"],
            sensitivity=sensitivity_clean,
        )
        result = anomaly.run_scan(
            context,
            families=family_filter or None,
            detectors=detector_filter or None,
        )

        scanned.append(name)
        for finding in result["findings"]:
            finding["project_name"] = name
            # next_args dilengkapi project supaya bisa langsung dieksekusi.
            finding["next_args"] = {"project_name": name, **finding["next_args"]}
            all_findings.append(finding)

        per_project[name] = {
            "days_analysed": result["baseline"]["days_analysed"],
            "findings": result["summary"]["total_findings"],
            "by_severity": result["summary"]["by_severity"],
            "noise_terms_configured": bool(frames["config"]["noise_terms"]),
            "trigger_terms_source": frames["config"]["trigger_source"],
        }

    # BUG GUARD — jangan pernah melaporkan "tidak ada anomali" kalau yang
    # sebenarnya terjadi adalah project-nya tidak ditemukan.
    #
    # Tanpa ini, salah ketik nama project menghasilkan found=True dengan 0
    # finding, lalu asisten melapor "aman, tidak ada masalah" — padahal
    # datanya tidak pernah dicek sama sekali. Diam-diam salah, dan tidak
    # ketahuan.
    if not scanned and not_found:
        return {
            "found": False,
            "error": (
                "Project tidak ditemukan: "
                + ", ".join(not_found)
                + ". Tidak ada data yang di-scan. "
                "JANGAN simpulkan 'tidak ada anomali' — datanya belum diperiksa."
            ),
            "projects_not_found": not_found,
            "next_step": "Cek ejaan nama project dengan find_project() atau list_campaigns().",
        }

    all_findings.sort(
        key=lambda item: (item["score"], item["confidence"]),
        reverse=True,
    )
    trimmed = all_findings[: max(1, int(max_findings))]

    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for finding in all_findings:
        severity_counts[finding["severity"]] = severity_counts.get(finding["severity"], 0) + 1

    unconfigured_noise = [
        name
        for name, info in per_project.items()
        if info.get("noise_terms_configured") is False
    ]

    return {
        "found": True,
        "mode": "monitoring_scan",
        "scope": {
            "projects_scanned": scanned,
            "projects_not_found": not_found,
            "from": start_date or None,
            "to": end_date or None,
            "channel": channel or None,
            "keywords": _csv(keywords),
            "exclude_keywords": _csv(exclude_keywords),
            "sensitivity": sensitivity_clean,
            "families": family_filter or "all",
            "detectors": detector_filter or "all",
        },
        "headline": _headline(trimmed, scanned, not_found),
        "summary": {
            "total_findings": len(all_findings),
            "shown": len(trimmed),
            "by_severity": severity_counts,
        },
        "findings": trimmed,
        "per_project": per_project,
        "baseline_method": (
            "Rolling median + MAD pada trailing window 14 hari (hari yang diuji "
            "dikecualikan), dengan koreksi day-of-week dan lantai absolut. "
            "Ini menggantikan pendekatan rata-rata sederhana yang membuat satu "
            "spike besar menutupi spike hari berikutnya."
        ),
        "setup_hint": (
            f"Project berikut belum punya noise_terms: {', '.join(unconfigured_noise)}. "
            "Pakai configure_anomaly_terms() supaya noise_contamination bisa bekerja "
            "(mis. Aqua: 'elektronik,badminton'; Bluebird: 'ASTS,satelit')."
        )
        if unconfigured_noise
        else None,
        "next_step": (
            "Untuk setiap finding, panggil next_tool dengan next_args-nya, atau "
            "get_posts() memakai canonical_key di field evidence. Baca konten "
            "aslinya SEBELUM menyimpulkan penyebab atau tingkat risiko."
        ),
        "guardrail": (
            "Ini hasil monitoring, BUKAN bahan deck. Jangan dipakai untuk "
            "melewati Intent Confirmation. Jika user ingin menjadikannya report/deck, "
            "mulai dari get_report_guide(). Jika user TIDAK menyebut tipe report, "
            "lanjutkan Jalur 2 dan rakit deck dari skill; jangan otomatis "
            "memetakan hasil diagnosis ke workflow Jalur 1."
        ),
    }


# ---------------------------------------------------------------------
# TOOL 2 — katalog detector
# ---------------------------------------------------------------------

def list_anomaly_detectors() -> dict[str, Any]:
    """
    Daftar seluruh detector anomaly beserta family dan bobot risikonya.

    Berguna ketika user bertanya "anomali apa saja yang bisa dideteksi?"
    atau ketika ingin membatasi scan ke family tertentu.
    """
    catalog = anomaly.list_detectors()

    by_family: dict[str, list[dict[str, Any]]] = {}
    for item in catalog:
        by_family.setdefault(item["family"], []).append(item)

    return {
        "found": True,
        "total_detectors": len(catalog),
        "families": sorted(by_family.keys()),
        "detectors_by_family": by_family,
        "sensitivity_levels": {
            "low": "hanya anomali sangat mencolok (z>=3.5, efek >=1.8x)",
            "medium": "default seimbang (z>=2.5, efek >=1.5x)",
            "high": "sensitif, lebih banyak temuan (z>=1.8, efek >=1.3x)",
        },
        "known_limits": [
            "Bot tidak bisa dipastikan: tabel posts tidak menyimpan follower "
            "count atau umur akun. coordinated_burst hanya indikasi koordinasi.",
            "Parafrase berat tidak tertangkap coordinated_burst (memakai "
            "bag-of-words hash, bukan kemiripan semantik).",
            "Eskalasi social -> mainstream perlu scan multi-project, karena "
            "keduanya tersimpan sebagai campaign terpisah.",
        ],
    }


# ---------------------------------------------------------------------
# TOOL 3 — konfigurasi trigger / noise term
# ---------------------------------------------------------------------

def configure_anomaly_terms(
    project_name: str,
    trigger_terms: str = "",
    noise_terms: str = "",
    show_only: bool = False,
) -> dict[str, Any]:
    """
    Atur trigger term (kosakata risiko) dan noise term (kontaminasi scope)
    untuk satu project.

    Disimpan di tabel campaign_guidance yang SUDAH ADA. Tidak ada tabel baru.

    trigger_terms : kosakata yang menentukan risk posture meski volumenya kecil.
                    Kalau dikosongkan, dipakai default 57 istilah
                    (BPKN, YLKI, DPR, BPOM, audit, investigasi, sidak, somasi,
                    gugatan, boikot, pencemaran, dst).

    noise_terms   : kata yang menandai post di luar scope brand. Ini yang
                    menyelamatkan angka dari kasus nyata:
                    - Aqua      : "elektronik, badminton" (AQUA Elektronik)
                    - Bluebird  : "ASTS, satelit, AST SpaceMobile"

    show_only=True : hanya menampilkan konfigurasi saat ini, tanpa mengubah.
    """
    if not project_name.strip():
        return {"found": False, "error": "project_name wajib diisi."}

    if show_only or (not trigger_terms.strip() and not noise_terms.strip()):
        config = aq.get_anomaly_config(project_name)
        return {
            "found": True,
            "action": "read",
            "project_name": project_name,
            "trigger_terms": config["trigger_terms"],
            "trigger_source": config["trigger_source"],
            "noise_terms": config["noise_terms"],
            "note": (
                "noise_terms masih kosong. Tanpa ini, detector "
                "noise_contamination tidak bisa bekerja."
            )
            if not config["noise_terms"]
            else None,
        }

    config = aq.set_anomaly_config(
        project_name,
        trigger_terms=trigger_terms or None,
        noise_terms=noise_terms or None,
    )

    return {
        "found": True,
        "action": "saved",
        "project_name": project_name,
        "trigger_terms": config["trigger_terms"],
        "trigger_source": config["trigger_source"],
        "noise_terms": config["noise_terms"],
        "next_step": (
            "Jalankan scan_anomalies() lagi untuk melihat efeknya."
        ),
    }
