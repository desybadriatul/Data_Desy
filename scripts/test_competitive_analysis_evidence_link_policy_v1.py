from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from reporting.task2.renderers.competitive_analysis_report_renderer import (  # noqa: E402
    normalize_audience_context,
    validate_competitive_analysis_render_package,
)


def main() -> None:
    audience = normalize_audience_context("gak tau")
    print("AUDIENCE =", audience.get("audience"))
    print("DEFAULT_USED =", audience.get("default_used"))
    assert audience["audience"] == "Marketing / Brand Team"
    assert audience["default_used"] is True

    good_package = {
        "evidence_registry": {
            "E01": {
                "evidence_id": "E01",
                "source_url": "https://example.com/post/1",
                "content": "contoh evidence",
            }
        },
        "slides": [
            {
                "slide_no": 5,
                "title": "Issue Anatomy",
                "cards": [
                    {
                        "evidence_id": "E01",
                        "content": "contoh quote",
                        "evidence_link": {
                            "label": "Buka post",
                            "url": "https://example.com/post/1",
                            "evidence_id": "E01",
                        },
                    }
                ],
            }
        ],
    }
    good = validate_competitive_analysis_render_package(good_package)
    print("GOOD_STATUS =", good.get("status"))
    assert good["status"] == "PASS", good

    bad_package = {
        "evidence_registry": {
            "E01": {
                "evidence_id": "E01",
                "source_url": "https://example.com/post/1",
            }
        },
        "slides": [
            {
                "slide_no": 6,
                "title": "Bad Evidence",
                "cards": [{"evidence_id": "T04", "content": "old non-canonical id"}],
            }
        ],
    }
    bad = validate_competitive_analysis_render_package(bad_package)
    print("BAD_STATUS =", bad.get("status"))
    print("BAD_ERRORS =", len(bad.get("errors") or []))
    assert bad["status"] == "FAIL", bad

    print("COMPETITIVE ANALYSIS EVIDENCE LINK POLICY V1 OK")


if __name__ == "__main__":
    main()
