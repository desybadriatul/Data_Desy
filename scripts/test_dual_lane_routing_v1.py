from __future__ import annotations

import ast
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def assert_contains(text: str, needle: str, label: str) -> None:
    assert needle in text, f"Missing {label}: {needle}"

def assert_not_contains(text: str, needle: str, label: str) -> None:
    assert needle not in text, f"Unexpected {label}: {needle}"

def function_docstrings(path: str) -> dict[str, str]:
    tree = ast.parse(read(path))
    return {
        node.name: ast.get_docstring(node) or ""
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }

def main() -> None:
    for path in [
        "server.py",
        "anomaly.py",
        "anomaly_tools.py",
        "database/anomaly_queries.py",
    ]:
        py_compile.compile(str(ROOT / path), doraise=True)

    skill = read("skills/insight-report-generator/SKILL.md")
    skill_report = read("skills/insight-report-generator/references/skill_report.md")
    server = read("server.py")
    anomaly_tools = read("anomaly_tools.py")

    assert_contains(skill, "version: 3.4", "SKILL version")
    assert_contains(skill_report, "version: 3.3", "skill_report version")
    assert_contains(skill, "JALUR 1 — BOTTOM-UP", "Jalur 1 route")
    assert_contains(skill, "JALUR 2 — TOP-DOWN", "Jalur 2 route")
    assert_contains(skill, "user TIDAK menyebut tipe report", "Jalur 2 trigger")
    assert_contains(skill, "DILARANG memanggil", "Jalur 2 hard ban")
    assert_contains(skill, "create_*_report_workflow", "workflow ban mention")
    assert_contains(skill, "tidak dipetakan", "taxonomy non-mapping")
    assert_contains(skill, "JANGAN bertanya ulang", "no repeated PPT question")

    assert_contains(skill_report, "tidak dipakai", "skill_report Jalur 1")
    assert_contains(skill_report, "Di Jalur 2, **dilarang** memanggil", "skill_report Jalur 2 ban")

    assert_contains(server, "_apply_jalur1_gate", "external workflow docstring gate")
    assert_contains(server, "_strip_bottom_up_pull", "bottom-up pull sanitizer")
    assert_contains(server, "LANGKAH 0 — TENTUKAN JALUR", "get_report_guide runtime gate")
    assert_contains(server, "Di Jalur 2, DILARANG memanggil", "get_report_guide Jalur 2 ban")
    assert_not_contains(server, '# RUNTIME GATE: Untuk report/deck/narrative analysis, lakukan Intent ', "old broad get_insight_report_skill header")

    docs = function_docstrings("server.py")
    for name in [
        "create_daily_social_report_workflow",
        "create_mainstream_media_report_workflow",
        "create_competitive_analysis_report_workflow",
    ]:
        doc = docs.get(name, "")
        assert_contains(doc, "Panggil HANYA bila user MENYEBUT tipe report ini", name)
        assert_contains(doc, "JANGAN panggil tool ini", name)
        assert_not_contains(doc.lower(), "preferred tool", name)
        assert_not_contains(doc.lower(), "use this first", name)

    assert_contains(anomaly_tools, "VERSI 1.2", "anomaly_tools v1.2")
    assert_contains(anomaly_tools, "JANGAN simpulkan 'tidak ada anomali'", "not-found guard")
    assert_contains(anomaly_tools, "lanjutkan Jalur 2 dan rakit deck", "scan guardrail Jalur 2")
    assert_not_contains(anomaly_tools, "workflow report yang sesuai", "old scan guardrail wording")
    assert_contains(anomaly_tools, "scan_anomalies()   <-- TOOL INI DI SINI", "scan after gate")

    print("DUAL_LANE_ROUTING_V1_OK")

if __name__ == "__main__":
    main()
