from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import server  # noqa: E402


def main() -> None:
    assert hasattr(server, "prepare_spokesperson_enrichment"), "missing prepare_spokesperson_enrichment"
    assert hasattr(server, "save_spokesperson_enrichment_response"), "missing save_spokesperson_enrichment_response"
    assert callable(server.prepare_spokesperson_enrichment)
    assert callable(server.save_spokesperson_enrichment_response)
    print("SERVER_SPOKESPERSON_TOOLS_OK")


if __name__ == "__main__":
    main()
