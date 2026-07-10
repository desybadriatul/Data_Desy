from __future__ import annotations

from pathlib import Path

SERVER_PATH = Path("server.py")
START_MARKER = "# ---------------------------------------------------------------------\n# Spokesperson enrichment MCP tools — shared foundation v1\n# ---------------------------------------------------------------------"
END_MARKER = "# ---------------------------------------------------------------------\n# End spokesperson enrichment MCP tools — shared foundation v1\n# ---------------------------------------------------------------------"

BLOCK = r'''
# ---------------------------------------------------------------------
# Spokesperson enrichment MCP tools — shared foundation v1
# ---------------------------------------------------------------------
def _spokesperson_split_csv(value: str | None) -> list[str]:
    """Split comma-separated campaign/brand values while preserving order."""
    if not value:
        return []
    seen: set[str] = set()
    result: list[str] = []
    for item in str(value).split(","):
        cleaned = item.strip()
        key = cleaned.casefold()
        if cleaned and key not in seen:
            result.append(cleaned)
            seen.add(key)
    return result


def _spokesperson_parse_json(value: str, field_name: str = "results_json") -> Any:
    """Parse JSON payload from Claude for spokesperson enrichment."""
    if value is None:
        raise ValueError(f"{field_name} wajib diisi.")
    if isinstance(value, (dict, list)):
        return value
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} kosong.")
    return json.loads(text)


@mcp.tool()
def prepare_spokesperson_enrichment(
    project_name: str,
    start_date: str,
    end_date: str = "",
    client_brand: str = "",
    competitors: str = "",
    competitor_brands: str = "",
    campaign_universe: str = "",
    sample_pct: float = 0.10,
    min_articles: int = 50,
    max_articles: int = 100,
    llm_batch_size: int = 20,
    include_prompts: bool = True,
) -> dict[str, Any]:
    """Prepare reusable spokesperson enrichment for report workflows.

    Use this before report preview/PPT when a report type needs spokesperson
    analysis. The tool checks cached spokesperson results first. If selected
    articles are missing cache, it returns NEEDS_AUTO_SPOKESPERSON_ENRICHMENT
    plus prompt_batches for Claude to process.

    Typical flow:
    report workflow -> prepare_spokesperson_enrichment -> Claude extracts ->
    save_spokesperson_enrichment_response -> rerun report workflow.
    """
    try:
        from reporting.enrichment.spokesperson_enrichment_workflow import (
            prepare_spokesperson_enrichment_batch as _prepare_spokesperson_batch,
        )

        explicit_universe = _spokesperson_split_csv(campaign_universe)
        competitor_list = _spokesperson_split_csv(competitor_brands or competitors)
        brand = (client_brand or project_name or "").strip()

        return _prepare_spokesperson_batch(
            client_brand=brand,
            competitors=competitor_list,
            campaign_universe=explicit_universe or None,
            start_date=start_date,
            end_date=end_date or start_date,
            sample_pct=float(sample_pct or 0.10),
            min_articles=max(0, int(min_articles or 50)),
            max_articles=max(1, int(max_articles or 100)),
            llm_batch_size=max(1, int(llm_batch_size or 20)),
            include_prompts=bool(include_prompts),
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "success": False,
            "workflow_status": "ERROR",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "instruction": "Pastikan reporting/enrichment/spokesperson_* ada dan DATABASE_URL aktif.",
        }


@mcp.tool()
def save_spokesperson_enrichment_response(
    results_json: str,
    candidates_json: str = "",
    model_version: str = "claude_spokesperson_extraction_v1",
    overwrite: bool = True,
) -> dict[str, Any]:
    """Validate and save Claude spokesperson extraction results to cache.

    results_json may be:
    - {"results": [...]}
    - {"rows": [...]}
    - [...]

    candidates_json is optional. If supplied, it should contain the candidate
    rows returned by prepare_spokesperson_enrichment().
    """
    try:
        from reporting.enrichment.spokesperson_enrichment_workflow import (
            save_spokesperson_enrichment_batch_response as _save_response,
        )

        payload = _spokesperson_parse_json(results_json, "results_json")
        if isinstance(payload, list):
            payload = {"results": payload}
        if not isinstance(payload, dict):
            return {
                "success": False,
                "workflow_status": "ERROR",
                "error": "results_json harus JSON object atau array.",
            }
        if "results" not in payload and "rows" in payload:
            payload = {"results": payload.get("rows") or []}
        if not isinstance(payload.get("results"), list):
            return {
                "success": False,
                "workflow_status": "ERROR",
                "error": "results_json harus punya field results[] atau rows[].",
            }

        candidates = None
        if candidates_json and str(candidates_json).strip():
            parsed_candidates = _spokesperson_parse_json(candidates_json, "candidates_json")
            if isinstance(parsed_candidates, dict):
                candidates = parsed_candidates.get("candidates") or parsed_candidates.get("rows")
            elif isinstance(parsed_candidates, list):
                candidates = parsed_candidates

        result = _save_response(
            payload,
            candidates=candidates,
            model_version=model_version or "claude_spokesperson_extraction_v1",
            overwrite=bool(overwrite),
        )
        if result.get("success"):
            result.setdefault(
                "next_step",
                "Rerun the requesting report workflow; cached spokesperson results should now be available.",
            )
        return result
    except Exception as exc:  # noqa: BLE001
        return {
            "success": False,
            "workflow_status": "ERROR",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


# ---------------------------------------------------------------------
# End spokesperson enrichment MCP tools — shared foundation v1
# ---------------------------------------------------------------------
'''.strip("\n") + "\n\n"


def remove_existing_block(text: str) -> str:
    if START_MARKER not in text:
        return text
    start = text.index(START_MARKER)
    if END_MARKER not in text[start:]:
        raise RuntimeError("Found spokesperson start marker but not end marker in server.py")
    end = text.index(END_MARKER, start) + len(END_MARKER)
    while end < len(text) and text[end] in "\r\n":
        end += 1
    return text[:start].rstrip() + "\n\n" + text[end:].lstrip()


def insert_block(text: str) -> str:
    if "def prepare_spokesperson_enrichment(" in text or "def save_spokesperson_enrichment_response(" in text:
        print("server.py already has spokesperson tools; no insert needed.")
        return text

    insertion_markers = [
        "@mcp.tool()\ndef prepare_report_input(",
        "@mcp.tool()\r\ndef prepare_report_input(",
    ]
    for marker in insertion_markers:
        idx = text.find(marker)
        if idx >= 0:
            return text[:idx].rstrip() + "\n\n\n" + BLOCK + text[idx:].lstrip()

    main_markers = ["if __name__ == \"__main__\":", "if __name__ == '__main__':"]
    for marker in main_markers:
        idx = text.find(marker)
        if idx >= 0:
            return text[:idx].rstrip() + "\n\n\n" + BLOCK + text[idx:].lstrip()

    return text.rstrip() + "\n\n\n" + BLOCK


def main() -> None:
    if not SERVER_PATH.exists():
        raise FileNotFoundError("server.py tidak ditemukan. Jalankan script ini dari root repo.")

    text = SERVER_PATH.read_text(encoding="utf-8-sig")
    text = remove_existing_block(text)
    new_text = insert_block(text)
    SERVER_PATH.write_text(new_text, encoding="utf-8")
    print("SERVER_SPOKESPERSON_TOOLS_PATCHED")
    print("tools: prepare_spokesperson_enrichment, save_spokesperson_enrichment_response")


if __name__ == "__main__":
    main()
