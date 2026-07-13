from __future__ import annotations

from pathlib import Path

SERVER = Path("server.py")
if not SERVER.exists():
    raise SystemExit("server.py tidak ditemukan. Jalankan dari root repo sonar-cogan-database.")

text = SERVER.read_text(encoding="utf-8")

if "mcp.tool()(scan_anomalies)" in text and "list_anomaly_detectors" in text and "configure_anomaly_terms" in text:
    print("ANOMALY_SERVER_REGISTRATION_ALREADY_OK")
    raise SystemExit(0)

block = '''

# ---------------------------------------------------------------------
# Anomaly detection engine V1 — monitoring only, not report-ready
# ---------------------------------------------------------------------
# New MCP tools:
# - scan_anomalies
# - list_anomaly_detectors
# - configure_anomaly_terms
#
# Guardrail: scan_anomalies() does not create report_input_id and must not
# bypass get_report_guide() / Intent Confirmation for report workflows.
from anomaly_tools import (
    scan_anomalies,
    list_anomaly_detectors,
    configure_anomaly_terms,
)

mcp.tool()(scan_anomalies)
mcp.tool()(list_anomaly_detectors)
mcp.tool()(configure_anomaly_terms)
'''

markers = [
    "\n# ---------------------------------------------------------------------\n# Cross-project anomaly scan",
    "\n@mcp.tool()\ndef scan_all_anomalies",
    "\n@mcp.tool()\ndef get_report_guide",
    "\nif __name__",
]

for marker in markers:
    idx = text.find(marker)
    if idx != -1:
        text = text[:idx].rstrip() + block + "\n" + text[idx:].lstrip()
        SERVER.write_text(text, encoding="utf-8")
        print("ANOMALY_SERVER_REGISTRATION_ADDED")
        break
else:
    text = text.rstrip() + block + "\n"
    SERVER.write_text(text, encoding="utf-8")
    print("ANOMALY_SERVER_REGISTRATION_APPENDED")
