"""Shared contract for LLM-created report topics."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import re
from typing import Any

TAXONOMY_VERSION_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,79}$")
TOPIC_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,79}$")

SYSTEM_TOPIC_IDS = frozenset({"other_emerging_topic", "not_relevant"})
CLASSIFICATION_STATUSES = frozenset(
    {"classified", "not_relevant", "review_needed"}
)
CONFIDENCE_LEVELS = frozenset({"high", "medium", "low"})

TITLE_MAX_CHARS = 80
CONTENT_MAX_CHARS = 780
CONTENT_HEAD_CHARS = 234
CONTENT_MIDDLE_WINDOW_CHARS = 104
CONTENT_MIDDLE_WINDOW_COUNT = 3
CONTENT_TAIL_CHARS = 234


class TopicContractError(ValueError):
    """Raised when taxonomy or classification data violates the contract."""


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _require_text(value: Any, field: str) -> str:
    clean = normalize_text(value)
    if not clean:
        raise TopicContractError(f"'{field}' wajib berupa string tidak kosong.")
    return clean


def canonical_content_hash(title: Any, content: Any) -> str:
    """Stable cache fingerprint. It changes only when title/content changes."""
    basis = f"{normalize_text(title).casefold()}\n{normalize_text(content).casefold()}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def canonical_key_from_values(*, url: Any, canonical_post_id: Any) -> str:
    """Matches db.py canonical identity policy: URL first, database ID fallback."""
    clean_url = normalize_text(url)
    if clean_url:
        return f"url:{clean_url.casefold()}"
    if canonical_post_id is None or str(canonical_post_id).strip() == "":
        raise TopicContractError(
            "canonical_post_id wajib tersedia bila URL kosong."
        )
    return f"id:{canonical_post_id}"


def trim_content_for_topic_llm(content: Any) -> str:
    """Balanced long-content trim: 234 head + 3x104 middle + 234 tail."""
    text = normalize_text(content)
    if len(text) <= CONTENT_MAX_CHARS:
        return text

    head = text[:CONTENT_HEAD_CHARS]
    tail = text[-CONTENT_TAIL_CHARS:]
    middle = text[CONTENT_HEAD_CHARS:-CONTENT_TAIL_CHARS]

    windows: list[str] = []
    if len(middle) <= CONTENT_MIDDLE_WINDOW_CHARS:
        windows.append(middle)
    else:
        max_start = len(middle) - CONTENT_MIDDLE_WINDOW_CHARS
        for idx in range(CONTENT_MIDDLE_WINDOW_COUNT):
            ratio = idx / (CONTENT_MIDDLE_WINDOW_COUNT - 1)
            start = round(max_start * ratio)
            windows.append(middle[start : start + CONTENT_MIDDLE_WINDOW_CHARS])

    return " … ".join([head, *[x for x in windows if x], tail])


def topic_text_for_llm(title: Any, content: Any) -> str:
    """The only text Claude needs for topic classification."""
    clean_title = normalize_text(title)[:TITLE_MAX_CHARS]
    clean_content = trim_content_for_topic_llm(content)

    if clean_title and clean_content:
        return f"Judul: {clean_title}\nKonten: {clean_content}"
    if clean_title:
        return f"Judul: {clean_title}"
    return f"Konten: {clean_content}"


def validate_taxonomy_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate taxonomy before it is allowed into the shared cache."""
    if not isinstance(payload, Mapping):
        raise TopicContractError("taxonomy harus berupa object/dictionary.")

    version = _require_text(payload.get("taxonomy_version"), "taxonomy_version").casefold()
    if not TAXONOMY_VERSION_RE.fullmatch(version):
        raise TopicContractError(
            "taxonomy_version hanya boleh lowercase a-z, angka, '_' atau '-'."
        )

    name = _require_text(payload.get("taxonomy_name"), "taxonomy_name")
    description = normalize_text(payload.get("description"))
    topics_raw = payload.get("topics")

    if not isinstance(topics_raw, list) or not (3 <= len(topics_raw) <= 30):
        raise TopicContractError(
            "taxonomy.topics wajib list berisi 3 sampai 30 topic."
        )

    topics: list[dict[str, str]] = []
    topic_ids: set[str] = set()
    labels: set[str] = set()

    for idx, topic in enumerate(topics_raw):
        if not isinstance(topic, Mapping):
            raise TopicContractError(f"topics[{idx}] harus object.")

        topic_id = _require_text(topic.get("topic_id"), f"topics[{idx}].topic_id").casefold()
        if not TOPIC_ID_RE.fullmatch(topic_id):
            raise TopicContractError(
                f"topics[{idx}].topic_id tidak valid: '{topic_id}'."
            )
        if topic_id in topic_ids:
            raise TopicContractError(f"topic_id duplikat: '{topic_id}'.")

        label = _require_text(topic.get("label"), f"topics[{idx}].label")
        if label.casefold() in labels:
            raise TopicContractError(f"label topic duplikat: '{label}'.")

        topic_description = _require_text(
            topic.get("description"),
            f"topics[{idx}].description",
        )
        topics.append(
            {
                "topic_id": topic_id,
                "label": label,
                "description": topic_description,
            }
        )
        topic_ids.add(topic_id)
        labels.add(label.casefold())

    missing = SYSTEM_TOPIC_IDS - topic_ids
    if missing:
        raise TopicContractError(
            "taxonomy wajib punya system topic: " + ", ".join(sorted(missing))
        )

    return {
        "taxonomy_version": version,
        "taxonomy_name": name,
        "description": description,
        "topics": topics,
    }


def taxonomy_instruction() -> str:
    return (
        "Buat taxonomy topic REPORT-LEVEL untuk satu project, bukan daftar "
        "entity. Gunakan hanya tema yang meaningful dan actionable untuk "
        "report. JANGAN gunakan raw Sonar Topic Extraction seperti Person, "
        "Activity, Location, Color, atau Company sebagai topic report. "
        "Buat 5–15 topic utama dan WAJIB sertakan "
        "`other_emerging_topic` serta `not_relevant`. Topic harus stabil, "
        "tidak tumpang tindih, dan punya topic_id lowercase snake_case."
    )


def classification_instruction(taxonomy: Mapping[str, Any]) -> str:
    validated = validate_taxonomy_payload(taxonomy)
    options = "\n".join(
        f"- {topic['topic_id']}: {topic['label']} — {topic['description']}"
        for topic in validated["topics"]
    )
    return (
        "Klasifikasikan setiap post ke TEPAT SATU allowed topic. Gunakan "
        "Judul + Konten saja; abaikan raw Sonar Topic Extraction. Jangan "
        "menciptakan topic_id baru. Return satu result per canonical_key tanpa "
        "missing/duplicate. content_hash tidak perlu dikirim; server memakai "
        "hash dari issued batch.\n\nAllowed topics:\n" + options
    )


__all__ = [
    "CLASSIFICATION_STATUSES",
    "CONFIDENCE_LEVELS",
    "CONTENT_MAX_CHARS",
    "SYSTEM_TOPIC_IDS",
    "TopicContractError",
    "canonical_content_hash",
    "canonical_key_from_values",
    "classification_instruction",
    "normalize_text",
    "taxonomy_instruction",
    "topic_text_for_llm",
    "trim_content_for_topic_llm",
    "validate_taxonomy_payload",
]
