from pathlib import Path
import py_compile

ROOT = Path(__file__).resolve().parents[1]
server = ROOT / "server.py"
text = server.read_text(encoding="utf-8-sig")

required_server_terms = [
    "def get_sales_deck_guide",
    "SALES_DECK_DIR",
    "_SALES_DECK_FILES",
    "_JALUR0_SALES_DECK_GATE",
    "get_sales_deck_guide()",
    "sales deck",
    "pitch deck",
    "proposal deck",
    "deck jualan",
    "commercial deck",
    "client presentation",
    "PPTX proposal",
    "CONTENT_DRAFT",
    "FINAL_PRODUCTION",
    "Jangan panggil report workflow",
]
for term in required_server_terms:
    assert term in text, f"Missing server routing term: {term}"

# Existing lanes must remain visible.
for term in [
    "def get_report_guide",
    "JALUR 1",
    "JALUR 2",
    "create_daily_social_report_workflow",
    "create_mainstream_media_report_workflow",
    "create_competitive_analysis_report_workflow",
    "create_bce_report_workflow",
    "create_industry_trend_report_workflow",
    "create_sfir_report_workflow",
]:
    assert term in text, f"Report routing regression: {term}"

# If intelligence brief is installed, sales deck must not override it.
for term in ["def get_intelligence_brief_guide", "client brief", "intelligence brief"]:
    assert term in text, f"Intelligence brief routing regression: {term}"

skill_dir = ROOT / "skills" / "salesdeck-generator"
required_files = [
    skill_dir / "SKILL.md",
    skill_dir / "skill_mapping.yaml",
    skill_dir / "references" / "system-prompt.md",
    skill_dir / "references" / "content-contract-schema.json",
    skill_dir / "references" / "quality_framework.md",
    skill_dir / "references" / "consistency_contract.md",
    skill_dir / "references" / "qa-and-change-rules.md",
    skill_dir / "references" / "user-prompt-template.md",
    skill_dir / "references" / "knowledge-base" / "00-INDEX.md",
    skill_dir / "references" / "knowledge-base" / "product-capability.md",
    skill_dir / "references" / "knowledge-base" / "pricing.md",
    skill_dir / "references" / "knowledge-base" / "competitors.md",
    skill_dir / "references" / "brand-kit" / "README.md",
    skill_dir / "references" / "brand-kit" / "01_BRAND_SYSTEM.md",
    skill_dir / "references" / "brand-kit" / "03_SLIDE_LIBRARY.md",
]
for path in required_files:
    assert path.exists(), f"Missing skill file: {path}"

skill_text = (skill_dir / "SKILL.md").read_text(encoding="utf-8-sig")
for term in [
    "Cogan MCP integration addendum",
    "Jalur 0B",
    "sales deck",
    "pitch deck",
    "proposal deck",
    "deck jualan",
    "Preferred input",
    "Client Intelligence Brief",
    "Do **not** use this skill when the user only asks",
    "CONTENT_DRAFT",
    "PPTX",
]:
    assert term in skill_text, f"Missing skill guidance: {term}"

mapping_text = (skill_dir / "skill_mapping.yaml").read_text(encoding="utf-8-sig")
for term in ["JALUR_0B_SALES_DECK", "get_sales_deck_guide", "must_not_trigger_for", "client brief only"]:
    assert term in mapping_text, f"Missing mapping guidance: {term}"

py_compile.compile(str(server), doraise=True)
print("SALES_DECK_ROUTING_V1_OK")
