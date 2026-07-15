from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server.py"
if not SERVER.exists():
    raise SystemExit("server.py tidak ditemukan. Jalankan dari repo root atau pastikan script ada di scripts/.")

text = SERVER.read_text(encoding="utf-8-sig")
original = text

needle = 'ENGINE_DIR = SKILLS_DIR / "insight-report-generator"\n'
insert = '''ENGINE_DIR = SKILLS_DIR / "insight-report-generator"
INTELLIGENCE_BRIEF_DIR = SKILLS_DIR / "intelligence-brief-generator"

_INTELLIGENCE_BRIEF_FILES = [
    ("SKILL.md — router dan usage guide", "SKILL.md"),
    ("system_prompt.md — execution engine", "references/system_prompt.md"),
    ("consistency_contract.md — invariant schema and evidence tags", "references/consistency_contract.md"),
    ("quality_framework.md — quality gate", "references/quality_framework.md"),
    ("user_prompt_template.md — intake template", "references/user_prompt_template.md"),
    ("skill_mapping.yaml — trigger and mapping", "skill_mapping.yaml"),
]
'''
if "INTELLIGENCE_BRIEF_DIR" not in text:
    if needle not in text:
        raise SystemExit("Tidak menemukan ENGINE_DIR marker di server.py")
    text = text.replace(needle, insert, 1)

jalur0_block = '''_JALUR0_CLIENT_BRIEF_GATE = """
    JALUR 0 - CLIENT / INTELLIGENCE BRIEF. Panggil bila user meminta client brief,
    presales brief, account brief, meeting prep, BD cheat-sheet, intelligence brief,
    intel brief, intellifence brief, brief klien, brief calon klien, atau meminta
    merapikan raw context dari chat, WhatsApp/WA, email, call note, meeting note,
    CRM/SCS handover, atau RFP menjadi brief.

    Untuk Jalur 0: panggil get_intelligence_brief_guide(). Jangan panggil
    get_report_guide(), jangan panggil create_*_report_workflow, dan jangan scan
    data Cogan kecuali user eksplisit meminta validasi data.

    Output Jalur 0 adalah Client Intelligence Brief / Presales Brief. Setelah brief
    selesai di chat, tanya konfirmasi apakah user mau file DOCX/Google Docs, PDF,
    Markdown+JSON, atau cukup di chat. Jangan membuat file sebelum user memilih.
"""

'''
if "_JALUR0_CLIENT_BRIEF_GATE" not in text:
    marker = '_JALUR1_GATE = """\n'
    if marker not in text:
        raise SystemExit("Tidak menemukan _JALUR1_GATE marker di server.py")
    text = text.replace(marker, jalur0_block + marker, 1)

if "Jika user meminta client brief / presales brief" not in text:
    target = '    JALUR 1 - BOTTOM-UP. Panggil HANYA bila user MENYEBUT tipe report ini\n    secara eksplisit (contoh: {contoh}).\n'
    repl = target + '''\n    Jika user meminta client brief / presales brief / account brief / meeting prep /\n    BD cheat-sheet / intelligence brief / brief dari chat, WA, email, CRM, RFP,\n    JANGAN panggil tool Jalur 1 ini. Panggil get_intelligence_brief_guide().\n'''
    if target in text:
        text = text.replace(target, repl, 1)

func = r'''@mcp.tool()
def get_intelligence_brief_guide() -> str:
    """
    JALUR 0 — Client / Intelligence Brief / Presales Brief.

    Panggil tool ini bila user meminta client brief, presales brief, account brief,
    meeting prep, BD cheat-sheet, intelligence brief, intel brief, intellifence brief,
    brief klien, brief calon klien, atau ingin mengubah chat/WhatsApp/WA/email/call
    note/meeting note/CRM/SCS/RFP menjadi brief.

    Jangan panggil get_report_guide() untuk request ini. Jangan panggil workflow
    report. Jangan scan data Cogan kecuali user eksplisit meminta validasi data.

    Setelah brief selesai di chat, tanya user apakah ingin dibuat sebagai
    DOCX/Google Docs, PDF, Markdown+JSON, atau cukup di chat. Jangan membuat file
    sebelum user memilih format.
    """
    header = (
        "# COGAN JALUR 0 — CLIENT / INTELLIGENCE BRIEF\n"
        "# Gunakan untuk client brief, presales brief, account brief, meeting prep, "
        "BD cheat-sheet, intelligence brief, intel brief, intellifence brief, "
        "brief klien, brief calon klien, atau brief dari chat/WA/email/RFP/CRM.\n"
        "# Jangan panggil report workflow dan jangan scan data Cogan kecuali user "
        "meminta validasi data secara eksplisit.\n"
        "# Setelah output brief selesai di chat, tanyakan format file: DOCX/Google Docs, "
        "PDF, Markdown+JSON, atau chat only. Jangan auto-generate file.\n"
        "# Default vendor/offering jika user tidak memberi konteks: Dataxet/Sonar/Cogan "
        "media intelligence, social listening, mainstream monitoring, competitive "
        "intelligence, reputation intelligence, campaign monitoring, anomaly detection, "
        "spokesperson/media analysis, dashboard/reporting, and insight/report generation.\n"
    )

    parts = [header]
    missing: list[str] = []

    for title, relative_path in _INTELLIGENCE_BRIEF_FILES:
        path = INTELLIGENCE_BRIEF_DIR / relative_path
        if path.exists():
            body = path.read_text(encoding="utf-8-sig")
            parts.append(f"\n\n{'=' * 72}\n### {title}\n{'=' * 72}\n\n{body}")
        else:
            missing.append(relative_path)

    if missing:
        parts.append(
            "\n\n[PERINGATAN] File intelligence brief belum ditemukan: "
            + ", ".join(missing)
            + ". Pastikan folder skills/intelligence-brief-generator sudah terpasang."
        )

    return "".join(parts)


'''
if "def get_intelligence_brief_guide" not in text:
    marker = '@mcp.tool()\ndef get_report_guide() -> str:\n'
    if marker not in text:
        raise SystemExit("Tidak menemukan get_report_guide marker di server.py")
    text = text.replace(marker, func + marker, 1)

if "# JALUR 0 — CLIENT / INTELLIGENCE BRIEF" not in text:
    target = '        "# Pertanyaannya satu: USER MENYEBUT TIPE REPORT, ATAU TIDAK?\\n"\n'
    repl = r'''        "# Pertama cek apakah ini CLIENT BRIEF/PRESALES BRIEF atau REPORT.\\n"
        "#\\n"
        "# ------------------------------------------------------------------\\n"
        "# JALUR 0 — CLIENT / INTELLIGENCE BRIEF\\n"
        "# ------------------------------------------------------------------\\n"
        "# Pemicu: client brief, presales brief, account brief, meeting prep,\\n"
        "# BD cheat-sheet, intelligence brief, intel brief, intellifence brief,\\n"
        "# brief klien, brief calon klien, brief dari chat/WA/email/RFP/CRM.\\n"
        "#\\n"
        "# Untuk Jalur 0: panggil get_intelligence_brief_guide(). Jangan\\n"
        "# panggil report workflow dan jangan scan data Cogan kecuali user\\n"
        "# eksplisit meminta validasi data. Setelah brief selesai di chat,\\n"
        "# tanya format file: DOCX/Google Docs, PDF, Markdown+JSON, atau\\n"
        "# cukup di chat. Jangan auto-generate file.\\n"
        "#\\n"
        "# Setelah bukan Jalur 0, baru pertanyaannya: USER MENYEBUT TIPE REPORT, ATAU TIDAK?\\n"
'''
    if target in text:
        text = text.replace(target, repl, 1)

SERVER.write_text(text, encoding="utf-8")
print("INTELLIGENCE_BRIEF_PATCH_APPLIED" if text != original else "INTELLIGENCE_BRIEF_PATCH_NO_CHANGE")
