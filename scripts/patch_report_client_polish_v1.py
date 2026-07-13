"""Patch report renderers with client-facing language polish v1.

This patch is intentionally append-only for renderer modules so it can be
applied safely on top of the current integration branch without replacing the
teammate merge or shared server registrations.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path.cwd()


def append_once(path: str, marker: str, block: str) -> None:
    p = ROOT / path
    if not p.exists():
        raise FileNotFoundError(f"Missing target file: {path}")
    text = p.read_text(encoding="utf-8")
    if marker in text:
        print(f"SKIP already patched: {path}")
        return
    if not text.endswith("\n"):
        text += "\n"
    p.write_text(text + "\n\n" + block.strip() + "\n", encoding="utf-8")
    print(f"PATCHED: {path}")


DAILY_BLOCK = r'''
# ---------------------------------------------------------------------------
# report_client_polish_v1: Daily Social client-facing wording polish.
#
# Keeps the existing v5 natural evidence links, then removes client-visible
# labels that read like data-quality/audit language (e.g. "Tidak relevan") and
# makes low-coverage/low-context findings more suitable for management decks.
# ---------------------------------------------------------------------------
_BUILD_DSM_PACKAGE_BEFORE_CLIENT_POLISH_V1 = build_daily_social_report_package
REPORT_CLIENT_POLISH_V1_DAILY = True

_DAILY_CLIENT_POLISH_TEXT_REPLACEMENTS_V1 = (
    ("Tidak relevan", "Penyebutan brand insidental"),
    ("tidak relevan", "penyebutan brand insidental"),
    ("konten yang tidak terkait produk", "konten dengan penyebutan brand insidental"),
    ("Konten ulang tahun anak — tidak membicarakan produk.", "Konten ulang tahun anak — penyebutan brand bersifat insidental."),
    ("Throwback ulang tahun anak — tidak membicarakan produk.", "Throwback ulang tahun anak — penyebutan brand bersifat insidental."),
    ("low-confidence", "low-context"),
    ("Low-confidence", "Low-context"),
    ("tingkat keyakinan rendah", "konteks brand rendah"),
    ("Konten tersebut tetap dihitung dan ditandai untuk audit.", "KPI perlu dibaca directional; detail konten tersedia di paket data untuk audit."),
    ("TEMA PERCAKAPAN", "SINYAL AWAL TEMA PERCAKAPAN"),
    ("Tema Percakapan", "Sinyal Awal Tema Percakapan"),
)

_DAILY_RESPONSE_DELIVERABLES_V1 = (
    "Output wajib: 1-page internal Q&A, approved response line, regulatory/legal position note, dan escalation trigger list."
)


def _daily_client_polish_text_v1(value):
    if isinstance(value, list):
        return [_daily_client_polish_text_v1(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_daily_client_polish_text_v1(item) for item in value)
    if isinstance(value, dict):
        return {key: _daily_client_polish_text_v1(child) for key, child in value.items()}
    if not isinstance(value, str):
        return value
    text = value
    for old, new in _DAILY_CLIENT_POLISH_TEXT_REPLACEMENTS_V1:
        text = text.replace(old, new)
    return text


def _daily_add_action_deliverables_v1(value):
    if isinstance(value, list):
        return [_daily_add_action_deliverables_v1(item) for item in value]
    if not isinstance(value, dict):
        return value
    out = {key: _daily_add_action_deliverables_v1(child) for key, child in value.items()}
    action_type = str(out.get("action_type") or out.get("Action Type") or "")
    focus = str(out.get("focus_area") or out.get("focus") or out.get("Focus Area") or "")
    action = str(out.get("recommended_action") or out.get("action") or out.get("Recommended Action") or "")
    candidate = "prepare response" in action_type.casefold() or "penjelasan" in action.casefold() or "p3i" in focus.casefold() or "pengawas periklanan" in focus.casefold()
    if candidate:
        out.setdefault("expected_output", _DAILY_RESPONSE_DELIVERABLES_V1)
        if "Q&A" not in action and "approved response line" not in action:
            out["recommended_action"] = (action.rstrip(".") + ". " + _DAILY_RESPONSE_DELIVERABLES_V1).strip()
    return out


def _daily_add_relevance_confidence_note_v1(slide):
    if not isinstance(slide, dict):
        return slide
    title = str(slide.get("title") or "").casefold()
    section = str(slide.get("section") or "").casefold()
    if "sumber" not in title and "sources" not in title and "notes" not in title and "footer" not in section:
        return slide
    components = list(slide.get("components") or [])
    blob = str(slide).casefold()
    if "catatan kualitas relevansi" not in blob:
        components.append({
            "type": "client_note",
            "title": "Catatan kualitas relevansi",
            "items": [
                "Konten noise dikeluarkan dari KPI utama sebelum analisis.",
                "Penyebutan brand berkonteks rendah tetap dibaca sebagai directional signal, bukan bukti sentimen/ketertarikan publik yang kuat.",
                "Jika proporsi low-context mention tinggi, gunakan KPI bersama source-of-interaction dan top-content concentration check.",
            ],
        })
        slide["components"] = components
    return slide


def _daily_client_polish_package_v1(package):
    out = dict(package or {})
    slides = []
    for slide in out.get("slides") or []:
        s = _daily_client_polish_text_v1(slide)
        s = _daily_add_action_deliverables_v1(s)
        if isinstance(s, dict):
            if str(s.get("title") or "").strip().casefold() == "tema percakapan":
                s["title"] = "SINYAL AWAL TEMA PERCAKAPAN"
            if str(s.get("title") or "").strip().casefold() == "thematic topics":
                s["title"] = "EARLY THEME SIGNAL"
            s = _daily_add_relevance_confidence_note_v1(s)
        slides.append(s)
    out["slides"] = slides
    out["quality_upgrade"] = str(out.get("quality_upgrade") or "") + "+client_polish_v1"
    style = dict(out.get("ppt_style_brief") or {})
    avoid = list(style.get("avoid") or [])
    avoid.extend(["visible label 'Tidak relevan'", "raw low-confidence audit wording", "final topic ranking wording when theme coverage is low"])
    style["avoid"] = avoid
    must_follow = list(style.get("must_follow") or [])
    must_follow.extend([
        "Use 'Penyebutan brand insidental' or 'brand-adjacent/low-context mention' instead of 'Tidak relevan' on client-facing slides.",
        "When theme coverage is low, label topic slides as early theme signal, not final topic ranking.",
        "Prepare Response actions must include concrete deliverables such as Q&A, approved response line, and escalation triggers.",
    ])
    style["must_follow"] = must_follow
    out["ppt_style_brief"] = style
    return out


def build_daily_social_report_package(
    report_input_id: str,
    *,
    allow_partial: bool = True,
    audience_context: str | None = None,
    audience_pov: str | None = None,
) -> dict[str, Any]:  # override report_client_polish_v1
    package = _BUILD_DSM_PACKAGE_BEFORE_CLIENT_POLISH_V1(
        report_input_id,
        allow_partial=allow_partial,
        audience_context=audience_context,
        audience_pov=audience_pov,
    )
    package = _daily_client_polish_package_v1(package)
    try:
        from reporting.task2.renderers.render_quality_gate import apply_render_package_quality_gate
        return apply_render_package_quality_gate(package, report_type=REPORT_TYPE_ID)
    except Exception:
        return package
'''

CA_BLOCK = r'''
# ---------------------------------------------------------------------------
# report_client_polish_v1: Competitive Analysis action/evidence wording polish.
# ---------------------------------------------------------------------------
_BUILD_CA_PACKAGE_BEFORE_CLIENT_POLISH_V1 = build_competitive_analysis_report_package
REPORT_CLIENT_POLISH_V1_CA = True

_CA_CLIENT_POLISH_TEXT_REPLACEMENTS_V1 = (
    ("mitra dagang", "akun retail/komersial pihak ketiga"),
    ("Mitra dagang", "Akun retail/komersial pihak ketiga"),
    ("partner-generated", "third-party/retail-like generated"),
    ("partner-like", "third-party retail-like"),
    ("partner", "third-party"),
)

_CA_WHITE_SPACE_ANGLES_V1 = [
    "product proof / pembuktian kualitas",
    "hydration for sport & community moments",
    "retail/third-party commercial content yang tervalidasi",
    "taste/preference correction",
]


def _ca_client_polish_text_v1(value):
    if isinstance(value, list):
        return [_ca_client_polish_text_v1(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_ca_client_polish_text_v1(item) for item in value)
    if isinstance(value, dict):
        return {key: _ca_client_polish_text_v1(child) for key, child in value.items()}
    if not isinstance(value, str):
        return value
    text = value
    for old, new in _CA_CLIENT_POLISH_TEXT_REPLACEMENTS_V1:
        text = text.replace(old, new)
    return text


def _ca_link_from_supporting_evidence_v1(card):
    if not isinstance(card, dict):
        return card
    ev = card.get("supporting_evidence") or card.get("evidence")
    if isinstance(ev, dict):
        link = ev.get("evidence_link")
        if isinstance(link, dict) and link.get("url"):
            card.setdefault("evidence_link", link)
            card.setdefault("link_label", link.get("label") or ev.get("link_label") or "Lihat post ↗")
            card.setdefault("evidence_cta", card.get("link_label"))
    return card


def _ca_polish_action_card_v1(card):
    if not isinstance(card, dict):
        return card
    out = dict(card)
    action_type = str(out.get("action_type") or "")
    out = _ca_link_from_supporting_evidence_v1(out)
    if "Exploit White Space" == action_type:
        out.setdefault("concrete_angles", list(_CA_WHITE_SPACE_ANGLES_V1))
        angles_text = "; ".join(_CA_WHITE_SPACE_ANGLES_V1)
        rec = str(out.get("recommended_action") or "")
        if "product proof" not in rec.casefold() and "pembuktian kualitas" not in rec.casefold():
            out["recommended_action"] = (rec.rstrip(".") + f". Prioritaskan angle konkret: {angles_text}.").strip()
        rationale = str(out.get("rationale") or "")
        if "white space" not in rationale.casefold() and "angle konkret" not in rationale.casefold():
            out["rationale"] = (rationale.rstrip(".") + f". White space harus dipilih sebagai angle pesan, bukan sekadar channel/format: {angles_text}.").strip()
        out.setdefault("expected_impact", "Content plan berikutnya memiliki territory pesan yang lebih jelas dan tidak hanya meniru format kompetitor.")
    elif action_type:
        out.setdefault("expected_impact", "Action menghasilkan keputusan channel/content yang lebih terukur dan evidence-backed.")
    return out


def _ca_client_polish_value_v1(value):
    value = _ca_client_polish_text_v1(value)
    if isinstance(value, list):
        return [_ca_client_polish_value_v1(item) for item in value]
    if not isinstance(value, dict):
        return value
    out = {key: _ca_client_polish_value_v1(child) for key, child in value.items()}
    if out.get("action_type"):
        out = _ca_polish_action_card_v1(out)
    if isinstance(out.get("cards"), list):
        out["cards"] = [_ca_polish_action_card_v1(c) if isinstance(c, dict) else c for c in out["cards"]]
    return out


def _ca_client_polish_package_v1(package):
    out = dict(package or {})
    out["slides"] = [_ca_client_polish_value_v1(slide) for slide in out.get("slides") or []]
    out["quality_upgrade"] = str(out.get("quality_upgrade") or "") + "+client_polish_v1"
    style = dict(out.get("ppt_style_brief") or {})
    avoid = list(style.get("avoid") or [])
    avoid.extend(["overclaiming third-party accounts as partners/mitra", "action plan without evidence CTA", "abstract white-space recommendation"])
    style["avoid"] = avoid
    must_follow = list(style.get("must_follow") or [])
    must_follow.extend([
        "Competitive Action Plan cards should carry direct natural evidence CTA when evidence exists.",
        "Do not call third-party retail/commercial accounts 'mitra/partner' unless relationship is explicitly validated.",
        "Exploit White Space must include concrete narrative/content angles, not only channel/format names.",
    ])
    style["must_follow"] = must_follow
    out["ppt_style_brief"] = style
    return out


def build_competitive_analysis_report_package(
    report_input_id: str,
    *,
    allow_partial: bool = True,
    audience_context: str | None = None,
    audience_pov: str | None = None,
) -> dict[str, Any]:  # override report_client_polish_v1
    package = _BUILD_CA_PACKAGE_BEFORE_CLIENT_POLISH_V1(
        report_input_id,
        allow_partial=allow_partial,
        audience_context=audience_context,
        audience_pov=audience_pov,
    )
    package = _ca_client_polish_package_v1(package)
    try:
        from reporting.task2.renderers.render_quality_gate import apply_render_package_quality_gate
        return apply_render_package_quality_gate(package, report_type=REPORT_TYPE_ID)
    except Exception:
        return package
'''

MMR_BLOCK = r'''
# ---------------------------------------------------------------------------
# report_client_polish_v1: MMR action wording polish.
# ---------------------------------------------------------------------------
_BUILD_MMR_PACKAGE_BEFORE_CLIENT_POLISH_V1 = build_mainstream_media_report_package
REPORT_CLIENT_POLISH_V1_MMR = True

_MMR_CLIENT_POLISH_TEXT_REPLACEMENTS_V1 = (
    ("Activate Spokesperson\nDedi Mulyadi", "Activate Spokesperson\nAqua/Danone technical spokesperson"),
    ("Activate Spokesperson — Dedi Mulyadi", "Activate Spokesperson — Aqua/Danone technical spokesperson"),
    ("dasar klarifikasi terkuat justru datang dari pihak ketiga", "dapat menjadi basis penjelasan teknis pihak ketiga, tetapi tetap perlu dikunci oleh legal dan technical team Aqua/Danone"),
    ("dasar klarifikasi terkuat", "basis penjelasan teknis yang perlu divalidasi legal/technical team"),
)

_MMR_EXTERNAL_ACTOR_NAMES_V1 = {"dedi mulyadi", "kdm", "mufti mubarok", "kawendra lukistian", "ylki", "bpkn", "dpr"}


def _mmr_client_polish_text_v1(value):
    if isinstance(value, list):
        return [_mmr_client_polish_text_v1(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_mmr_client_polish_text_v1(item) for item in value)
    if isinstance(value, dict):
        return {key: _mmr_client_polish_text_v1(child) for key, child in value.items()}
    if not isinstance(value, str):
        return value
    text = value
    for old, new in _MMR_CLIENT_POLISH_TEXT_REPLACEMENTS_V1:
        text = text.replace(old, new)
    return text


def _mmr_polish_action_card_v1(card):
    if not isinstance(card, dict):
        return card
    out = dict(card)
    action_type = str(out.get("action_type") or out.get("Action Type") or "")
    focus_key = "focus_area" if "focus_area" in out else "focus" if "focus" in out else "Focus Area" if "Focus Area" in out else None
    focus = str(out.get(focus_key) or "") if focus_key else ""
    if action_type == "Activate Spokesperson" and any(name in focus.casefold() for name in _MMR_EXTERNAL_ACTOR_NAMES_V1):
        if focus_key:
            out["external_framing_actor"] = focus
            out[focus_key] = "Aqua/Danone technical spokesperson"
        else:
            out["focus_area"] = "Aqua/Danone technical spokesperson"
            out["external_framing_actor"] = focus
        out["rationale"] = "Aktor eksternal mendominasi framing; brand perlu juru bicara teknis bernama untuk menjelaskan fakta, batas klaim, dan proses verifikasi."
        out["owner_next_step"] = "PR + Legal + technical team: tunjuk spokesperson, kunci message territory, dan validasi Q&A sebelum media response."
    return out


def _mmr_add_media_follow_up_mode_v1(card):
    if not isinstance(card, dict):
        return card
    out = dict(card)
    priority = str(out.get("priority") or out.get("Priority") or "").casefold()
    media = str(out.get("media_name") or out.get("source") or out.get("Media") or "").casefold()
    framing = str(out.get("framing") or out.get("dominant_framing") or out.get("role") or "").casefold()
    if "follow_up_mode" not in out:
        if "high" in priority or "regulator" in framing or "tajam" in framing or media in {"rmol", "gelora.co", "suara"}:
            out["follow_up_mode"] = "Monitor + prepare clarification / technical background if framing repeats."
        else:
            out["follow_up_mode"] = "Passive monitor; use clarification only if article is repeated or syndicated widely."
    return out


def _mmr_client_polish_value_v1(value):
    value = _mmr_client_polish_text_v1(value)
    if isinstance(value, list):
        return [_mmr_client_polish_value_v1(item) for item in value]
    if not isinstance(value, dict):
        return value
    out = {key: _mmr_client_polish_value_v1(child) for key, child in value.items()}
    if out.get("action_type") or out.get("Action Type"):
        out = _mmr_polish_action_card_v1(out)
    section = str(out.get("section") or out.get("title") or "").casefold()
    if "media contributor" in section and isinstance(out.get("cards"), list):
        out["cards"] = [_mmr_add_media_follow_up_mode_v1(c) if isinstance(c, dict) else c for c in out["cards"]]
    if isinstance(out.get("cards"), list):
        out["cards"] = [_mmr_polish_action_card_v1(c) if isinstance(c, dict) else c for c in out["cards"]]
    return out


def _mmr_client_polish_package_v1(package):
    out = dict(package or {})
    out["slides"] = [_mmr_client_polish_value_v1(slide) for slide in out.get("slides") or []]
    out["quality_upgrade"] = str(out.get("quality_upgrade") or "") + "+client_polish_v1"
    style = dict(out.get("ppt_style_brief") or {})
    avoid = list(style.get("avoid") or [])
    avoid.extend(["Activate Spokesperson focused on external critic", "technical validation overclaim", "media priority without follow-up mode"])
    style["avoid"] = avoid
    must_follow = list(style.get("must_follow") or [])
    must_follow.extend([
        "Activate Spokesperson must focus on brand/technical spokesperson, not the external actor who triggered framing.",
        "Third-party technical explanation may support clarification but must be validated by legal/technical team.",
        "Media contributor cards should include a practical follow-up mode.",
    ])
    style["must_follow"] = must_follow
    out["ppt_style_brief"] = style
    return out


def build_mainstream_media_report_package(
    report_input_id: str,
    *,
    allow_partial: bool = True,
    audience_context: str | None = None,
    audience_pov: str | None = None,
) -> dict[str, Any]:  # override report_client_polish_v1
    package = _BUILD_MMR_PACKAGE_BEFORE_CLIENT_POLISH_V1(
        report_input_id,
        allow_partial=allow_partial,
        audience_context=audience_context,
        audience_pov=audience_pov,
    )
    package = _mmr_client_polish_package_v1(package)
    try:
        from reporting.task2.renderers.render_quality_gate import apply_render_package_quality_gate
        return apply_render_package_quality_gate(package, report_type=REPORT_TYPE_ID)
    except Exception:
        return package
'''

GATE_BLOCK = r'''
# ---------------------------------------------------------------------------
# report_client_polish_v1: extra client-language QA checks.
# ---------------------------------------------------------------------------
_VALIDATE_RENDER_PACKAGE_QUALITY_GATE_BEFORE_CLIENT_POLISH_V1 = validate_render_package_quality_gate
REPORT_CLIENT_POLISH_V1_GATE = True

_CLIENT_POLISH_FORBIDDEN_VISIBLE_PHRASES_V1 = (
    "tidak relevan",
    "evidence id & full url",
)


def _check_report_client_polish_v1(package: Mapping[str, Any], report_type: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    visible_strings: list[str] = []
    for slide in _slides(package):
        visible_strings.extend(_walk_visible_strings(slide))
    visible_blob = "\n".join(visible_strings)
    visible_lc = visible_blob.casefold()

    for phrase in _CLIENT_POLISH_FORBIDDEN_VISIBLE_PHRASES_V1:
        if phrase in visible_lc:
            errors.append(f"Client-facing wording is not polished: {phrase}")

    if report_type == "daily_social_media_report":
        if "klasifikasi tema" in visible_lc and "10%" in visible_lc and "sinyal awal" not in visible_lc and "early" not in visible_lc:
            warnings.append("Daily theme coverage appears low but slide does not clearly say early signal.")
        if "konteks brand rendah" in visible_lc and "directional" not in visible_lc:
            warnings.append("Daily low-context relevance is mentioned without directional-read caveat.")

    if report_type == "competitive_analysis":
        if "mitra dagang" in visible_lc or " partner" in visible_lc:
            errors.append("CA may overclaim third-party relationship as mitra/partner.")
        action_slide = next((s for s in _slides(package) if isinstance(s, Mapping) and _clean(s.get("section")) == "Competitive Action Plan"), {})
        action_blob = "\n".join(_walk_visible_strings(action_slide)).casefold()
        if "exploit white space" in action_blob and "product proof" not in action_blob and "pembuktian" not in action_blob:
            warnings.append("CA Exploit White Space action lacks concrete narrative angles.")

    if report_type == "mainstream_media_report":
        action_slide = next((s for s in _slides(package) if isinstance(s, Mapping) and _clean(s.get("section")) == "Media Response Action Plan"), {})
        action_blob = "\n".join(_walk_visible_strings(action_slide)).casefold()
        if "activate spokesperson" in action_blob and "dedi mulyadi" in action_blob:
            errors.append("MMR Activate Spokesperson should not focus on external actor Dedi Mulyadi; use brand/technical spokesperson.")
        if "dasar klarifikasi terkuat" in visible_lc:
            warnings.append("MMR technical third-party wording may overclaim validation strength.")
    return errors, warnings


def validate_render_package_quality_gate(
    package: Mapping[str, Any],
    *,
    report_type: str | None = None,
) -> dict[str, Any]:  # override report_client_polish_v1
    result = dict(_VALIDATE_RENDER_PACKAGE_QUALITY_GATE_BEFORE_CLIENT_POLISH_V1(package, report_type=report_type))
    rt = report_type or _clean(package.get("report_type_id"))
    errors = list(result.get("errors") or [])
    warnings = list(result.get("warnings") or [])
    extra_errors, extra_warnings = _check_report_client_polish_v1(package, rt)
    errors.extend(extra_errors)
    warnings.extend(extra_warnings)
    result["errors"] = errors
    result["warnings"] = warnings
    result["status"] = "PASS" if not errors else "FAIL"
    result["version"] = str(result.get("version") or REPORT_RENDER_QA_GATE_VERSION) + "+client_polish_v1"
    return result
'''

append_once(
    "reporting/task2/renderers/daily_social_media_report_renderer.py",
    "REPORT_CLIENT_POLISH_V1_DAILY",
    DAILY_BLOCK,
)
append_once(
    "reporting/task2/renderers/competitive_analysis_report_renderer.py",
    "REPORT_CLIENT_POLISH_V1_CA",
    CA_BLOCK,
)
append_once(
    "reporting/task2/renderers/mainstream_media_report_renderer.py",
    "REPORT_CLIENT_POLISH_V1_MMR",
    MMR_BLOCK,
)
append_once(
    "reporting/task2/renderers/render_quality_gate.py",
    "REPORT_CLIENT_POLISH_V1_GATE",
    GATE_BLOCK,
)

print("REPORT_CLIENT_POLISH_V1_PATCH_APPLIED")
