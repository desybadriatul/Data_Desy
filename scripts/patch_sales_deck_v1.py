from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server.py"
if not SERVER.exists():
    raise SystemExit("server.py tidak ditemukan. Jalankan dari repo root atau pastikan script ada di scripts/.")

text = SERVER.read_text(encoding="utf-8-sig")
original = text

# -----------------------------------------------------------------------------
# Constants and file registry
# -----------------------------------------------------------------------------
if "SALES_DECK_DIR" not in text:
    if 'INTELLIGENCE_BRIEF_DIR = SKILLS_DIR / "intelligence-brief-generator"\n' in text:
        needle = 'INTELLIGENCE_BRIEF_DIR = SKILLS_DIR / "intelligence-brief-generator"\n'
        insert = '''INTELLIGENCE_BRIEF_DIR = SKILLS_DIR / "intelligence-brief-generator"
SALES_DECK_DIR = SKILLS_DIR / "salesdeck-generator"

_SALES_DECK_FILES = [
    ("SKILL.md — router dan usage guide", "SKILL.md"),
    ("system-prompt.md — execution engine", "references/system-prompt.md"),
    ("consistency_contract.md — invariant claims, evidence, and design contract", "references/consistency_contract.md"),
    ("quality_framework.md — hard gates and QA", "references/quality_framework.md"),
    ("qa-and-change-rules.md — final QA and revision rules", "references/qa-and-change-rules.md"),
    ("content-contract-schema.json — content output schema", "references/content-contract-schema.json"),
    ("user-prompt-template.md — sales deck intake template", "references/user-prompt-template.md"),
    ("skill_mapping.yaml — trigger and routing map", "skill_mapping.yaml"),
    ("knowledge-base/00-INDEX.md — knowledge base index", "references/knowledge-base/00-INDEX.md"),
    ("knowledge-base/product-capability.md — approved Sonar capabilities", "references/knowledge-base/product-capability.md"),
    ("knowledge-base/pricing.md — approved pricing boundaries", "references/knowledge-base/pricing.md"),
    ("knowledge-base/competitors.md — approved competitor framing", "references/knowledge-base/competitors.md"),
    ("knowledge-base/tone-and-writing.md — writing voice", "references/knowledge-base/tone-and-writing.md"),
    ("knowledge-base/deck-structure-guidance.md — deck structure guidance", "references/knowledge-base/deck-structure-guidance.md"),
    ("brand-kit/README.md — brand kit index", "references/brand-kit/README.md"),
    ("brand-kit/01_BRAND_SYSTEM.md — design tokens", "references/brand-kit/01_BRAND_SYSTEM.md"),
    ("brand-kit/03_SLIDE_LIBRARY.md — slide archetypes", "references/brand-kit/03_SLIDE_LIBRARY.md"),
]
'''
        text = text.replace(needle, insert, 1)
    elif 'ENGINE_DIR = SKILLS_DIR / "insight-report-generator"\n' in text:
        needle = 'ENGINE_DIR = SKILLS_DIR / "insight-report-generator"\n'
        insert = '''ENGINE_DIR = SKILLS_DIR / "insight-report-generator"
SALES_DECK_DIR = SKILLS_DIR / "salesdeck-generator"

_SALES_DECK_FILES = [
    ("SKILL.md — router dan usage guide", "SKILL.md"),
    ("system-prompt.md — execution engine", "references/system-prompt.md"),
    ("consistency_contract.md — invariant claims, evidence, and design contract", "references/consistency_contract.md"),
    ("quality_framework.md — hard gates and QA", "references/quality_framework.md"),
    ("qa-and-change-rules.md — final QA and revision rules", "references/qa-and-change-rules.md"),
    ("content-contract-schema.json — content output schema", "references/content-contract-schema.json"),
    ("user-prompt-template.md — sales deck intake template", "references/user-prompt-template.md"),
    ("skill_mapping.yaml — trigger and routing map", "skill_mapping.yaml"),
    ("knowledge-base/00-INDEX.md — knowledge base index", "references/knowledge-base/00-INDEX.md"),
    ("knowledge-base/product-capability.md — approved Sonar capabilities", "references/knowledge-base/product-capability.md"),
    ("knowledge-base/pricing.md — approved pricing boundaries", "references/knowledge-base/pricing.md"),
    ("knowledge-base/competitors.md — approved competitor framing", "references/knowledge-base/competitors.md"),
    ("knowledge-base/tone-and-writing.md — writing voice", "references/knowledge-base/tone-and-writing.md"),
    ("knowledge-base/deck-structure-guidance.md — deck structure guidance", "references/knowledge-base/deck-structure-guidance.md"),
    ("brand-kit/README.md — brand kit index", "references/brand-kit/README.md"),
    ("brand-kit/01_BRAND_SYSTEM.md — design tokens", "references/brand-kit/01_BRAND_SYSTEM.md"),
    ("brand-kit/03_SLIDE_LIBRARY.md — slide archetypes", "references/brand-kit/03_SLIDE_LIBRARY.md"),
]
'''
        text = text.replace(needle, insert, 1)
    else:
        raise SystemExit("Tidak menemukan ENGINE_DIR / INTELLIGENCE_BRIEF_DIR marker di server.py")

# -----------------------------------------------------------------------------
# Routing guardrail block
# -----------------------------------------------------------------------------
sales_gate = '''_JALUR0_SALES_DECK_GATE = """
    JALUR 0B - SALES DECK / PITCH DECK. Panggil bila user meminta sales deck,
    pitch deck, proposal deck, deck proposal, deck jualan, sales presentation,
    commercial deck, client presentation, PPTX proposal, final production PPTX,
    atau deck dari client/intelligence/presales brief.

    Untuk Jalur 0B: panggil get_sales_deck_guide(). Jangan panggil
    get_report_guide(), jangan panggil create_*_report_workflow, dan jangan scan
    data Cogan kecuali user eksplisit meminta validasi data/evidence lookup.

    Preferred input adalah Client Intelligence Brief / Presales Brief / Account Brief.
    Jika user hanya memberi raw sales context, kumpulkan field material yang hilang
    atau bentuk sales-deck intake ringan. Jangan klaim ada client brief final bila
    belum ada.

    Default output adalah CONTENT_DRAFT. Buat PPTX/final production hanya bila user
    eksplisit meminta PPTX/final production atau konten sudah disetujui dan content
    gate tidak BLOCKED.
"""

'''
if "_JALUR0_SALES_DECK_GATE" not in text:
    marker = '_JALUR1_GATE = """\n'
    if marker not in text:
        raise SystemExit("Tidak menemukan _JALUR1_GATE marker di server.py")
    text = text.replace(marker, sales_gate + marker, 1)

# Add Jalur 1 warning so fixed report tools do not capture sales deck requests.
if "Jika user meminta sales deck / pitch deck" not in text:
    target = '    JALUR 1 - BOTTOM-UP. Panggil HANYA bila user MENYEBUT tipe report ini\n    secara eksplisit (contoh: {contoh}).\n'
    repl = target + '''
    Jika user meminta sales deck / pitch deck / proposal deck / deck jualan /
    commercial deck / client presentation / PPTX proposal, JANGAN panggil tool
    Jalur 1 ini. Panggil get_sales_deck_guide().
'''
    if target in text:
        text = text.replace(target, repl, 1)

# -----------------------------------------------------------------------------
# Tool function
# -----------------------------------------------------------------------------
func = r'''@mcp.tool()
def get_sales_deck_guide() -> str:
    """
    JALUR 0B — Sales Deck / Pitch Deck / Proposal Deck.

    Panggil tool ini bila user meminta sales deck, pitch deck, proposal deck,
    deck proposal, deck jualan, sales presentation, commercial deck, client
    presentation, PPTX proposal, final production PPTX, atau deck dari client
    brief / intelligence brief / presales brief.

    Jangan panggil get_report_guide() untuk request ini. Jangan panggil workflow
    report. Jangan scan data Cogan kecuali user eksplisit meminta validasi data
    atau evidence lookup.

    Preferred input adalah Client Intelligence Brief / Presales Brief / Account Brief.
    Jika brief resmi belum ada, kumpulkan field material atau bentuk sales-deck
    intake ringan. Default output adalah CONTENT_DRAFT; buat PPTX hanya jika user
    eksplisit meminta FINAL_PRODUCTION/PPTX atau konten sudah disetujui.
    """
    header = (
        "# COGAN JALUR 0B — SALES DECK / PITCH DECK\n"
        "# Gunakan untuk sales deck, pitch deck, proposal deck, deck proposal, "
        "deck jualan, commercial deck, client presentation, sales presentation, "
        "PPTX proposal, final production PPTX, atau deck dari client/intelligence/"
        "presales brief.\n"
        "# Jangan panggil report workflow, get_report_guide(), atau anomaly tools "
        "kecuali user eksplisit meminta validasi data/evidence lookup.\n"
        "# Preferred input: Client Intelligence Brief / Presales Brief / Account Brief. "
        "Kalau hanya raw sales context yang ada, minta field material yang hilang "
        "atau buat sales-deck intake ringan; jangan klaim ada client brief final.\n"
        "# Default: CONTENT_DRAFT. Buat PPTX/final production hanya jika user "
        "meminta PPTX/final production atau content sudah approved dan gate tidak BLOCKED.\n"
    )

    parts = [header]
    missing: list[str] = []

    for title, relative_path in _SALES_DECK_FILES:
        path = SALES_DECK_DIR / relative_path
        if path.exists():
            body = path.read_text(encoding="utf-8-sig")
            parts.append(f"\n\n{'=' * 72}\n### {title}\n{'=' * 72}\n\n{body}")
        else:
            missing.append(relative_path)

    if missing:
        parts.append(
            "\n\n[PERINGATAN] File sales deck belum ditemukan: "
            + ", ".join(missing)
            + ". Pastikan folder skills/salesdeck-generator sudah terpasang."
        )

    return "".join(parts)


'''
if "def get_sales_deck_guide" not in text:
    # Prefer placing after intelligence brief guide if present, otherwise before report guide.
    marker = '@mcp.tool()\ndef get_report_guide() -> str:\n'
    if marker not in text:
        raise SystemExit("Tidak menemukan get_report_guide marker di server.py")
    text = text.replace(marker, func + marker, 1)

# -----------------------------------------------------------------------------
# get_report_guide top gate augmentation
# -----------------------------------------------------------------------------
if "# JALUR 0B — SALES DECK" not in text:
    sales_intent_block = r'''        "# ------------------------------------------------------------------\n"
        "# JALUR 0B — SALES DECK / PITCH DECK\n"
        "# ------------------------------------------------------------------\n"
        "# Pemicu: sales deck, pitch deck, proposal deck, deck proposal,\n"
        "# deck jualan, sales presentation, commercial deck, client presentation,\n"
        "# PPTX proposal, final production PPTX, deck dari client brief,\n"
        "# deck dari intelligence brief, atau deck dari presales brief.\n"
        "#\n"
        "# Untuk Jalur 0B: panggil get_sales_deck_guide(). Jangan panggil\n"
        "# report workflow, get_report_guide(), atau anomaly tools kecuali user\n"
        "# eksplisit meminta validasi data/evidence lookup. Default output\n"
        "# CONTENT_DRAFT; PPTX hanya bila user meminta final production/PPTX.\n"
        "#\n"
'''
    if '        "# Setelah bukan Jalur 0, baru pertanyaannya: USER MENYEBUT TIPE REPORT, ATAU TIDAK?\\n"\n' in text:
        target = '        "# Setelah bukan Jalur 0, baru pertanyaannya: USER MENYEBUT TIPE REPORT, ATAU TIDAK?\\n"\n'
        text = text.replace(target, sales_intent_block + target, 1)
    elif '        "# Pertanyaannya satu: USER MENYEBUT TIPE REPORT, ATAU TIDAK?\\n"\n' in text:
        target = '        "# Pertanyaannya satu: USER MENYEBUT TIPE REPORT, ATAU TIDAK?\\n"\n'
        text = text.replace(target, sales_intent_block + target, 1)

SERVER.write_text(text, encoding="utf-8")
print("SALES_DECK_PATCH_APPLIED" if text != original else "SALES_DECK_PATCH_NO_CHANGE")
