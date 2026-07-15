from pathlib import Path
import py_compile

ROOT = Path(__file__).resolve().parents[1]
server = ROOT / "server.py"
text = server.read_text(encoding="utf-8-sig")

required_server_terms = [
    "def get_intelligence_brief_guide",
    "INTELLIGENCE_BRIEF_DIR",
    "_INTELLIGENCE_BRIEF_FILES",
    "_JALUR0_CLIENT_BRIEF_GATE",
    "get_intelligence_brief_guide()",
    "client brief",
    "presales brief",
    "account brief",
    "meeting prep",
    "BD cheat-sheet",
    "intellifence brief",
    "WhatsApp",
    "PDF",
    "DOCX",
    "Markdown+JSON",
    "Jangan membuat file sebelum user memilih",
]
for term in required_server_terms:
    assert term in text, f"Missing server routing term: {term}"

for term in [
    "create_daily_social_report_workflow",
    "create_mainstream_media_report_workflow",
    "create_competitive_analysis_report_workflow",
    "create_bce_report_workflow",
    "create_industry_trend_report_workflow",
    "create_sfir_report_workflow",
    "JALUR 2",
]:
    assert term in text, f"Report routing regression: {term}"

skill_dir = ROOT / "skills" / "intelligence-brief-generator"
required_files = [
    skill_dir / "SKILL.md",
    skill_dir / "skill_mapping.yaml",
    skill_dir / "references" / "system_prompt.md",
    skill_dir / "references" / "user_prompt_template.md",
    skill_dir / "references" / "quality_framework.md",
    skill_dir / "references" / "consistency_contract.md",
]
for path in required_files:
    assert path.exists(), f"Missing skill file: {path}"

skill_text = (skill_dir / "SKILL.md").read_text(encoding="utf-8-sig")
for term in [
    "Jalur 0",
    "brief klien",
    "brief dari WhatsApp",
    "intellifence brief",
    "Default vendor/offering context for Cogan",
    "Do not auto-generate PDF",
    "DOCX/Google Docs",
    "PDF",
    "Markdown+JSON",
]:
    assert term in skill_text, f"Missing skill guidance: {term}"

py_compile.compile(str(server), doraise=True)
print("INTELLIGENCE_BRIEF_ROUTING_V1_OK")
