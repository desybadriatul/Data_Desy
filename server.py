"""
server.py — Cogan MCP Server

VERSI 3.1 — metric-safe report API + readiness guardrails

Aturan utama server ini:
- Interactions dihitung per channel:
  IG / YouTube = Likes + Comments
  Facebook / TikTok = Likes + Comments + Shares
  X / Twitter = Likes + Replies + Retweets
- Views selalu dipisahkan dari interactions.
- Seluruh aggregate report memakai canonical unique-post layer dari db.py.
- Semua tool aggregate mendukung scope issue-only melalui keywords /
  exclude_keywords / match_mode bila relevan.
- Net sentiment interaction-weighted tidak lagi dikembalikan sebagai KPI default.
- Kolom source `engagement` lama hanya diagnostic internal dan tidak dipakai
  sebagai metrik client-facing default.

File ini harus dipakai bersama db.py versi 3.1.
"""

from __future__ import annotations

import csv
import json
import os
import re
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import FileResponse, PlainTextResponse
from wordcloud import WordCloud

from database import db


# ---------------------------------------------------------------------
# Server / folders
# ---------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
os.environ.setdefault("MPLCONFIGDIR", str(BASE_DIR / "output" / ".matplotlib"))

mcp = FastMCP("Cogan", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))

DATA_DIR = BASE_DIR / "data"
CONFIG_DIR = BASE_DIR / "config"
SKILLS_DIR = BASE_DIR / "skills"

# Set STORAGE_DIR ke Railway Volume (mis. /data) agar file hasil persisten.
OUTPUT_DIR = Path(os.environ.get("STORAGE_DIR") or (BASE_DIR / "output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TEXT_COLUMNS = ("Title", "Content")
DATE_COLUMN = "Date"
CHANNEL_COLUMN = "Channel"
SENTIMENT_COLUMN = "Sentiment"
INTERACTIONS_COLUMN = "Interactions"

SENTIMENT_COLORS = {
    "positive": "#16a34a",
    "negative": "#dc2626",
    "neutral": "#6b7280",
}


# ---------------------------------------------------------------------
# General helpers
# ---------------------------------------------------------------------
def _public_base_url() -> str:
    """Alamat publik server untuk link unduhan file hasil."""
    base = os.environ.get("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if base:
        return base

    domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip()
    if domain:
        return "https://" + domain

    return ""


def _project_id(project_name: str) -> str:
    return project_name.strip().lower()


def _available_projects() -> list[str]:
    return db.list_campaigns()


def _num_clean(value: Any) -> int | float:
    """Decimal / None -> angka Python yang rapi untuk JSON."""
    if value is None:
        return 0

    if isinstance(value, Decimal):
        number = float(value)
        return int(number) if number.is_integer() else round(number, 2)

    if isinstance(value, float):
        return int(value) if value.is_integer() else round(value, 2)

    return value


def _pct(part: int | float, base: int | float) -> float:
    return round(float(part) * 100 / float(base), 1) if base else 0.0


def _delta(current: int | float | None, baseline: int | float | None) -> dict[str, Any]:
    """Selisih periode/campaign current vs baseline."""
    a = _num_clean(current)
    b = _num_clean(baseline)
    difference = round(a - b, 2)
    percent_change = round((a - b) * 100 / b, 1) if b else None

    return {
        "current": a,
        "baseline": b,
        "difference": difference,
        "percent_change": percent_change,
    }


def _clean_csv(value: str | Iterable[str] | None) -> list[str]:
    """String comma-separated atau iterable -> list unik dan bersih."""
    if value is None:
        return []

    if isinstance(value, str):
        raw_items = value.split(",")
    else:
        raw_items = list(value)

    result: list[str] = []
    seen: set[str] = set()

    for item in raw_items:
        clean = str(item).strip()
        key = clean.lower()
        if clean and key not in seen:
            result.append(clean)
            seen.add(key)

    return result


def _normalise_match_mode(match_mode: str) -> str:
    return "all" if str(match_mode).strip().lower() == "all" else "any"


def _scope_payload(
    start_date: str = "",
    end_date: str = "",
    channels: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
) -> dict[str, Any]:
    """
    Scope transparan yang selalu dikembalikan tool aggregate.

    `keywords` hanya filter awal berbasis teks. Untuk report isu, hasilnya
    tetap harus dibaca melalui get_posts() agar tema tidak ditentukan dari
    keyword semata.
    """
    clean_keywords = _clean_csv(keywords)
    clean_excludes = _clean_csv(exclude_keywords)
    clean_channels = _clean_csv(channels)

    universe = "issue_only" if clean_keywords or clean_excludes else "brand"

    return {
        "universe": universe,
        "start_date": start_date or None,
        "end_date": end_date or None,
        "channels": clean_channels,
        "keywords": clean_keywords,
        "exclude_keywords": clean_excludes,
        "match_mode": _normalise_match_mode(match_mode),
        "keyword_filter_note": (
            "Keyword scope adalah saringan teks awal. Baca konten asli untuk "
            "memastikan relevansi dan jangan menyimpulkan tema hanya dari kata."
            if clean_keywords or clean_excludes
            else None
        ),
    }


def _scope_kwargs(scope: dict[str, Any]) -> dict[str, Any]:
    """Konversi scope payload ke parameter db.py."""
    return {
        "channels": scope["channels"] or None,
        "keywords": scope["keywords"] or None,
        "exclude_keywords": scope["exclude_keywords"] or None,
        "match_mode": scope["match_mode"],
    }


def _normalise_metric(metric: str, allowed: set[str], default: str) -> str:
    """
    Normalisasi alias lama `engagement` menjadi `interactions`.

    Alias diterima untuk kompatibilitas request lama, tetapi output selalu
    memakai nama metrik baru: interactions.
    """
    value = (metric or default).strip().lower()
    aliases = {
        "engagement": "interactions",
        "interaction": "interactions",
        "view": "views",
        "post": "posts",
    }
    value = aliases.get(value, value)
    return value if value in allowed else default


def _metric_formula(channel_norm: str | None) -> str | None:
    """Penjelasan rumus interaction per channel untuk output tool."""
    mapping = {
        "instagram": "Likes + Comments",
        "facebook": "Likes + Comments + Shares",
        "youtube": "Likes + Comments",
        "tiktok": "Likes + Comments + Shares",
        "x": "Likes + Replies + Retweets",
    }
    return mapping.get((channel_norm or "").strip().lower())


def _serialise_post(row: dict[str, Any]) -> dict[str, Any]:
    """Serialisasi satu post canonical dengan interactions dan views terpisah."""
    content = (row.get("content") or "").strip()
    title = (row.get("title") or "").strip()
    post_date = row.get("post_date")

    return {
        "date": post_date.strftime("%Y-%m-%d %H:%M") if post_date else None,
        "channel": row.get("channel"),
        "channel_type": row.get("channel_norm"),
        "author": row.get("author"),
        "sentiment": row.get("sentiment"),
        "url": row.get("url"),
        "title": title[:300],
        "content": content[:800],
        "interactions": _num_clean(row.get("interactions")),
        "views": _num_clean(row.get("views")),
        "likes": _num_clean(row.get("likes")),
        "comments": _num_clean(row.get("comments")),
        "shares": _num_clean(row.get("shares")),
        "replies": _num_clean(row.get("replies")),
        "retweets": _num_clean(row.get("retweets")),
        "interaction_formula": _metric_formula(row.get("channel_norm")),
        "interactions_available": bool(row.get("interactions_available")),
        "views_available": bool(row.get("has_views")),
    }


def _health_payload(
    project_name: str,
    start_date: str = "",
    end_date: str = "",
    channels: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
) -> dict[str, Any] | None:
    """Bentuk data health client/tool-ready dari output db.py."""
    scope = _scope_payload(
        start_date,
        end_date,
        channels,
        keywords,
        exclude_keywords,
        match_mode,
    )

    result = db.data_health(
        project_name,
        start_date or None,
        end_date or None,
        **_scope_kwargs(scope),
    )
    if result is None:
        return None

    row = result["row"] or {}
    n_unique = int(row.get("n_unique") or 0)
    n_raw = int(row.get("n_rows_raw") or 0)
    interaction_applicable = int(row.get("interactions_applicable_posts") or 0)
    interaction_available = int(row.get("interactions_available_posts") or 0)

    channels_output = []
    for item in result["channels"]:
        post_count = int(item.get("posts") or 0)
        channel_applicable = int(item.get("interactions_applicable_posts") or 0)
        channel_available = int(item.get("interactions_available_posts") or 0)
        channel_sentiment = int(item.get("sentiment_classified_posts") or 0)
        channel_views = int(item.get("views_available_posts") or 0)

        channels_output.append(
            {
                "channel": item.get("channel"),
                "channel_type": item.get("channel_norm"),
                "posts": post_count,
                "interaction_formula": _metric_formula(item.get("channel_norm")),
                "coverage_percent": {
                    "sentiment_classified": _pct(channel_sentiment, post_count),
                    "interactions_available_of_applicable": _pct(
                        channel_available, channel_applicable
                    )
                    if channel_applicable
                    else None,
                    "views_available_of_posts": _pct(channel_views, post_count),
                },
                "counts": {
                    "interaction_applicable_posts": channel_applicable,
                    "interaction_available_posts": channel_available,
                    "views_available_posts": channel_views,
                    "sentiment_classified_posts": channel_sentiment,
                },
            }
        )

    return {
        "found": True,
        "project_name": project_name,
        "scope": scope,
        "n_posts_unique": n_unique,
        "n_rows_raw": n_raw,
        "duplicate_rows_removed": max(0, n_raw - n_unique),
        "date_range_actual": {
            "from": str(row.get("date_min")) if row.get("date_min") else None,
            "to": str(row.get("date_max")) if row.get("date_max") else None,
        },
        "coverage_percent": {
            "sentiment_classified": _pct(
                int(row.get("sentiment_classified_posts") or 0),
                n_unique,
            ),
            "interactions_available_of_applicable": _pct(
                interaction_available,
                interaction_applicable,
            )
            if interaction_applicable
            else None,
            "views_available_of_posts": _pct(
                int(row.get("views_available_posts") or 0),
                n_unique,
            ),
            "buzz_available_of_posts": _pct(
                int(row.get("buzz_available_posts") or 0),
                n_unique,
            ),
            "ad_value_available_of_posts": _pct(
                int(row.get("ad_value_available_posts") or 0),
                n_unique,
            ),
        },
        "coverage_counts": {
            "sentiment_classified_posts": int(
                row.get("sentiment_classified_posts") or 0
            ),
            "interaction_applicable_posts": interaction_applicable,
            "interaction_available_posts": interaction_available,
            "views_available_posts": int(row.get("views_available_posts") or 0),
            "buzz_available_posts": int(row.get("buzz_available_posts") or 0),
            "ad_value_available_posts": int(row.get("ad_value_available_posts") or 0),
        },
        "channels_present": channels_output,
        "note": (
            "Coverage interactions memakai denominator post pada channel yang "
            "memang memiliki rumus interaction. Views dilaporkan terpisah dan "
            "coverage views memakai seluruh post dalam scope."
        ),
    }


def _readiness_status(
    readiness: dict[str, Any],
) -> tuple[str, list[str], list[str]]:
    """
    Menentukan status readiness metric sebelum interactions/views dipakai.

    PASS = field/coverage siap digunakan, tetap tunduk pada data_health.
    WARN = sebagian channel/field perlu caveat atau dikeluarkan dari metric.
    FAIL = tidak ada post canonical atau interaction source tidak siap sama sekali.
    """
    overview = readiness.get("overview") or {}
    total_posts = int(overview.get("canonical_posts") or 0)
    channel_rows = readiness.get("channels") or []
    unknown_channels = readiness.get("unknown_channel_rows") or []
    parse_warnings = readiness.get("parse_warnings") or {}

    warnings: list[str] = []
    blockers: list[str] = []

    if total_posts == 0:
        blockers.append("Tidak ada canonical post pada scope ini.")

    applicable_rows = [
        row for row in channel_rows
        if int(row.get("interactions_applicable_posts") or 0) > 0
    ]
    if not applicable_rows and total_posts > 0:
        warnings.append(
            "Tidak ada channel dengan rumus interactions yang berlaku pada scope ini."
        )

    for row in applicable_rows:
        applicable = int(row.get("interactions_applicable_posts") or 0)
        available = int(row.get("interactions_available_posts") or 0)
        channel = row.get("channel") or "(tidak diketahui)"
        coverage = _pct(available, applicable) if applicable else None

        if applicable and available == 0:
            blockers.append(
                f"{channel}: tidak ada post dengan komponen interactions lengkap."
            )
        elif coverage is not None and coverage < 60.0:
            warnings.append(
                f"{channel}: coverage interactions {coverage}% (<60%). "
                "Jangan jadikan total/average interactions sebagai KPI utama."
            )

    for row in channel_rows:
        posts = int(row.get("posts") or 0)
        views_available = int(row.get("views_available_posts") or 0)
        channel = row.get("channel") or "(tidak diketahui)"
        if posts and 0 < views_available < posts:
            coverage = _pct(views_available, posts)
            if coverage < 60.0:
                warnings.append(
                    f"{channel}: coverage views {coverage}% (<60%). "
                    "Views hanya boleh dibaca directional/contextual."
                )

    if unknown_channels:
        unknown_labels = ", ".join(
            sorted(
                {
                    str(item.get("channel") or "(tidak diketahui)")
                    for item in unknown_channels
                }
            )
        )
        warnings.append(
            "Channel belum memiliki rumus interactions dan tidak boleh dihitung "
            f"sebagai interactions: {unknown_labels}."
        )

    for field, diagnostic in parse_warnings.items():
        nonstandard = int(diagnostic.get("nonstandard_values_detected") or 0)
        if nonstandard:
            warnings.append(
                f"{field}: terdapat {nonstandard} nilai raw non-standar yang "
                "perlu diaudit sebelum dipakai sebagai metric headline."
            )

    if blockers:
        return "FAIL", warnings, blockers
    if warnings:
        return "WARN", warnings, blockers
    return "PASS", warnings, blockers


# ---------------------------------------------------------------------
# Public route for generated files
# ---------------------------------------------------------------------
@mcp.custom_route("/files/{filename}", methods=["GET"])
async def serve_output_file(request: Request):
    """
    Melayani file hasil PNG/CSV lewat URL publik.

    `basename` mencegah path traversal.
    """
    safe_filename = os.path.basename(request.path_params["filename"])
    path = OUTPUT_DIR / safe_filename

    if not path.exists():
        return PlainTextResponse(
            "File tidak ditemukan. Kemungkinan file terhapus saat server restart; "
            "silakan generate ulang.",
            status_code=404,
        )

    return FileResponse(str(path))


# ---------------------------------------------------------------------
# Wordcloud helpers
# ---------------------------------------------------------------------
def _load_stopwords() -> set[str]:
    """Baca stopword umum dari config/global_stopwords.json."""
    path = CONFIG_DIR / "global_stopwords.json"
    if not path.exists():
        return set()

    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return {
        word.strip().lower()
        for word in data.get("stopwords", [])
        if str(word).strip()
    }


def _read_guidance(project_name: str) -> dict[str, Any]:
    guidance = db.get_guidance(project_name)
    if guidance:
        return guidance

    return {
        "project_id": _project_id(project_name),
        "objective": None,
        "include": [],
        "exclude": [],
        "brand_term_policy": "Tidak ada guidance khusus.",
        "preferred_term_format": "Frasa 1 sampai 3 kata.",
        "default_max_output_terms": 50,
    }


def _read_filtered(
    project_name: str,
    start_date: str | None,
    end_date: str | None,
    channels: str | None,
    keywords: str | None = None,
    exclude_keywords: str | None = None,
    match_mode: str = "any",
) -> pd.DataFrame:
    """
    Ambil canonical data yang sudah tersaring di database.

    Wordcloud sekarang memakai Interactions, bukan Engagement ambigu.
    """
    return db.fetch_posts_df(
        project_name,
        start_date,
        end_date,
        channels,
        keywords,
        exclude_keywords,
        match_mode,
    )


def _prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    """Siapkan kolom gabungan title/content untuk proses kandidat term."""
    result = df.copy()

    text_parts = []
    for column in TEXT_COLUMNS:
        if column in result.columns:
            text_parts.append(result[column].fillna("").astype(str))

    if text_parts:
        result["_combined_text"] = text_parts[0]
        for part in text_parts[1:]:
            result["_combined_text"] = result["_combined_text"] + " " + part
    else:
        result["_combined_text"] = ""

    return result


def _tokenize(text: str) -> list[str]:
    text = re.sub(r"https?://\S+|www\.\S+", " ", text.lower())
    text = re.sub(r"#[\w_]+|@[\w_]+", " ", text)
    return re.findall(r"[a-zA-Z\u00C0-\u024F0-9]+", text)


def _candidate_terms(
    tokens: list[str],
    project_id: str,
    extra_blocklist: set[str] | None = None,
) -> set[str]:
    terms: set[str] = set()
    blocklist = _load_stopwords() | {project_id.lower()} | (extra_blocklist or set())

    for ngram_size in (1, 2, 3):
        for index in range(0, max(0, len(tokens) - ngram_size + 1)):
            gram_tokens = tokens[index : index + ngram_size]

            if any(token in blocklist for token in gram_tokens):
                continue
            if all(len(token) <= 2 for token in gram_tokens):
                continue
            if all(token.isdigit() for token in gram_tokens):
                continue

            term = " ".join(gram_tokens).strip()
            if len(term) >= 3:
                terms.add(term)

    return terms


def _majority_sentiment(values: list[str]) -> str:
    normalized = [
        str(value).strip().lower()
        for value in values
        if str(value).strip().lower() in {"positive", "negative", "neutral"}
    ]

    if not normalized:
        return "neutral"

    counts = Counter(normalized)
    ranked = counts.most_common()

    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return "neutral"

    return ranked[0][0]


def _term_matches_text(
    term_tokens: list[str],
    text_tokens: list[str],
    text_normalized: str,
) -> bool:
    if not term_tokens:
        return False

    term_normalized = " ".join(term_tokens)
    if term_normalized in text_normalized:
        return True

    if len(term_tokens) == 1:
        return term_tokens[0] in set(text_tokens)

    text_token_set = set(text_tokens)
    return all(token in text_token_set for token in term_tokens)


def _normalise_wordcloud_mode(mode: str) -> str:
    """
    Wordcloud old mode `engagement` tetap diterima sebagai alias `interactions`.

    Output dan dokumentasi baru selalu memakai `interactions`.
    """
    value = (mode or "frequency").strip().lower()
    if value == "engagement":
        value = "interactions"
    return value if value in {"frequency", "interactions"} else "frequency"


def _build_candidates(
    project_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    channels: str | None = None,
    keywords: str | None = None,
    exclude_keywords: str | None = None,
    match_mode: str = "any",
    candidate_pool_size: int = 200,
) -> list[dict[str, Any]]:
    project_id = _project_id(project_name)

    df = _prepare_df(
        _read_filtered(
            project_name,
            start_date,
            end_date,
            channels,
            keywords,
            exclude_keywords,
            match_mode,
        )
    )
    if df.empty:
        return []

    guidance = _read_guidance(project_name)
    extra_blocklist = {
        str(word).strip().lower()
        for word in guidance.get("extra_blocklist", [])
        if str(word).strip()
    }

    frequency: Counter[str] = Counter()
    interactions: defaultdict[str, float] = defaultdict(float)
    sentiments: defaultdict[str, list[str]] = defaultdict(list)
    examples: dict[str, str] = {}

    for _, row in df.iterrows():
        text = str(row.get("_combined_text", ""))
        tokens = _tokenize(text)
        row_terms = _candidate_terms(tokens, project_id, extra_blocklist)

        row_interactions = pd.to_numeric(
            row.get(INTERACTIONS_COLUMN, 0),
            errors="coerce",
        )
        if pd.isna(row_interactions):
            row_interactions = 0

        row_sentiment = str(row.get(SENTIMENT_COLUMN, "neutral")).strip().lower()

        for term in row_terms:
            frequency[term] += 1
            interactions[term] += float(row_interactions)
            sentiments[term].append(row_sentiment)
            examples.setdefault(term, text[:180])

    rows = []
    for term, term_frequency in frequency.items():
        rows.append(
            {
                "term": term,
                "frequency": int(term_frequency),
                "interactions": int(interactions[term]),
                "sentiment": _majority_sentiment(sentiments[term]),
                "example": examples.get(term, ""),
            }
        )

    rows.sort(
        key=lambda item: (
            item["frequency"],
            item["interactions"],
            len(item["term"]),
        ),
        reverse=True,
    )
    return rows[: max(1, int(candidate_pool_size))]


def _stats_for_selected_terms(
    project_name: str,
    selected_terms: list[str],
    start_date: str | None = None,
    end_date: str | None = None,
    channels: str | None = None,
    keywords: str | None = None,
    exclude_keywords: str | None = None,
    match_mode: str = "any",
) -> tuple[list[dict[str, Any]], list[str]]:
    df = _prepare_df(
        _read_filtered(
            project_name,
            start_date,
            end_date,
            channels,
            keywords,
            exclude_keywords,
            match_mode,
        )
    )

    rows: list[dict[str, Any]] = []
    unmatched: list[str] = []

    for raw_term in selected_terms:
        term = str(raw_term).strip()
        if not term:
            continue

        term_normalized = " ".join(_tokenize(term))
        if not term_normalized:
            unmatched.append(term)
            continue

        frequency = 0
        total_interactions = 0.0
        sentiments: list[str] = []
        example = ""

        for _, row in df.iterrows():
            text = str(row.get("_combined_text", ""))
            text_tokens = _tokenize(text)
            text_normalized = " ".join(text_tokens)

            if not _term_matches_text(
                term_normalized.split(),
                text_tokens,
                text_normalized,
            ):
                continue

            frequency += 1

            row_interactions = pd.to_numeric(
                row.get(INTERACTIONS_COLUMN, 0),
                errors="coerce",
            )
            if not pd.isna(row_interactions):
                total_interactions += float(row_interactions)

            sentiments.append(str(row.get(SENTIMENT_COLUMN, "neutral")).strip().lower())
            if not example:
                example = text[:180]

        if frequency == 0:
            unmatched.append(term)
            continue

        rows.append(
            {
                "term": term,
                "frequency": int(frequency),
                "interactions": int(total_interactions),
                "sentiment": _majority_sentiment(sentiments),
                "example": example,
            }
        )

    return rows, unmatched


# ---------------------------------------------------------------------
# Core reporting tools
# ---------------------------------------------------------------------
@mcp.tool()
def ping_cogan() -> str:
    """Cek apakah Cogan MCP Server berhasil terhubung."""
    return "Cogan is connected."


@mcp.tool()
def list_campaigns() -> dict[str, Any]:
    """Tampilkan daftar campaign/klien yang tersedia di database Cogan."""
    campaigns = db.list_campaigns()
    return {"count": len(campaigns), "campaigns": campaigns}


@mcp.tool()
def find_project(project_name: str) -> dict[str, Any]:
    """Cari project/client berdasarkan nama dan kembalikan informasi dasarnya."""
    summary = db.campaign_summary(project_name)

    if summary is None:
        return {
            "found": False,
            "error": f"Project '{project_name}' tidak ditemukan.",
            "available_projects": _available_projects(),
        }

    aggregate = summary["agg"]
    date_from = aggregate.get("date_from")
    date_to = aggregate.get("date_to")

    return {
        "found": True,
        "project_id": _project_id(project_name),
        "project_name": project_name,
        "total_posts_unique": int(aggregate.get("total_posts_unique") or 0),
        "available_data_period": {
            "from": date_from.strftime("%Y-%m-%d") if date_from else None,
            "to": date_to.strftime("%Y-%m-%d") if date_to else None,
        },
        "channels_available": summary["channels"],
        "has_title_column": bool(aggregate.get("has_title")),
        "has_content_column": bool(aggregate.get("has_content")),
        "note": (
            "Jumlah post memakai canonical unique-post layer: satu URL dihitung "
            "satu kali per campaign."
        ),
    }


@mcp.tool()
def data_health(
    project_name: str,
    start_date: str = "",
    end_date: str = "",
    channels: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
) -> dict[str, Any]:
    """
    Bukti data dan keterbatasan scope report.

    Panggil sebelum membuat report. Tool ini mengembalikan:
    - post unik canonical;
    - raw row dan duplicate yang dihapus;
    - periode aktual;
    - coverage sentiment;
    - coverage interactions berdasarkan channel yang applicable;
    - coverage views terpisah.

    Gunakan `keywords` untuk scope issue-only. `match_mode`:
    - any: post mengandung minimal satu keyword;
    - all: post harus mengandung semua keyword.
    """
    result = _health_payload(
        project_name,
        start_date,
        end_date,
        channels,
        keywords,
        exclude_keywords,
        match_mode,
    )

    if result is None:
        return {
            "found": False,
            "error": f"Campaign '{project_name}' tidak ditemukan.",
            "available_campaigns": _available_projects(),
        }

    return result


@mcp.tool()
def validate_metric_readiness(
    project_name: str,
    start_date: str = "",
    end_date: str = "",
    channels: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
) -> dict[str, Any]:
    """
    Preflight wajib sebelum interactions/views dijadikan KPI report.

    Tool ini memeriksa:
    - apakah raw fields Likes, Comments, Shares, Replies, Retweets, dan Views
      benar-benar ditemukan di database;
    - alias header fallback yang terdeteksi;
    - coverage interactions/views per channel;
    - channel yang belum memiliki rumus interactions;
    - nilai numeric non-standar yang perlu audit;
    - status PASS / WARN / FAIL.

    Gunakan sesudah Intent Confirmation disetujui dan sebelum data freeze.
    Tool ini tidak menggantikan `data_health()`; keduanya harus dibaca bersama.
    """
    scope = _scope_payload(
        start_date,
        end_date,
        channels,
        keywords,
        exclude_keywords,
        match_mode,
    )

    readiness = db.metric_readiness(
        project_name,
        start_date or None,
        end_date or None,
        scope["channels"] or None,
        scope["keywords"] or None,
        scope["exclude_keywords"] or None,
        scope["match_mode"],
    )
    if readiness is None:
        return {
            "found": False,
            "error": f"Campaign '{project_name}' tidak ditemukan.",
            "available_campaigns": _available_projects(),
        }

    status, warnings, blockers = _readiness_status(readiness)
    raw_fields = readiness.get("raw_field_status") or {}
    channel_rows = readiness.get("channels") or []
    parse_warnings = readiness.get("parse_warnings") or {}

    fields_output: dict[str, Any] = {}
    for field, info in raw_fields.items():
        detected = info.get("detected_headers") or []
        available_posts = int(info.get("available_on_canonical_posts") or 0)
        fields_output[field] = {
            "status": (
                "available"
                if available_posts > 0
                else "not_available_in_scope"
            ),
            "available_on_canonical_posts": available_posts,
            "detected_headers": detected,
            "configured_aliases": info.get("configured_aliases") or [],
        }

    channels_output = []
    for row in channel_rows:
        posts = int(row.get("posts") or 0)
        applicable = int(row.get("interactions_applicable_posts") or 0)
        interactions_available = int(
            row.get("interactions_available_posts") or 0
        )
        views_available = int(row.get("views_available_posts") or 0)
        channel_type = row.get("channel_norm")
        channels_output.append(
            {
                "channel": row.get("channel"),
                "channel_type": channel_type,
                "posts": posts,
                "interaction_formula": _metric_formula(channel_type),
                "interactions_applicable": bool(applicable),
                "interaction_coverage_pct": (
                    _pct(interactions_available, applicable)
                    if applicable
                    else None
                ),
                "views_coverage_pct": _pct(views_available, posts),
                "status": (
                    "unmapped"
                    if channel_type
                    not in {
                        "instagram",
                        "facebook",
                        "youtube",
                        "tiktok",
                        "x",
                        "online_media",
                        "forum",
                    }
                    else (
                        "not_applicable"
                        if not applicable
                        else (
                            "not_ready"
                            if interactions_available == 0
                            else "ready"
                        )
                    )
                ),
            }
        )

    parse_output = {
        field: {
            "suffix_values_detected": int(
                info.get("suffix_values_detected") or 0
            ),
            "nonstandard_values_detected": int(
                info.get("nonstandard_values_detected") or 0
            ),
        }
        for field, info in parse_warnings.items()
    }

    return {
        "found": True,
        "project_name": project_name,
        "scope": scope,
        "status": status,
        "release_decision": {
            "can_use_interactions_as_main_kpi": status == "PASS",
            "can_use_views_as_main_kpi": (
                status != "FAIL"
                and any(
                    item["views_coverage_pct"] is not None
                    and item["views_coverage_pct"] >= 60.0
                    for item in channels_output
                )
            ),
            "rule": (
                "PASS: lanjut ke data_health dan metric admission. "
                "WARN: gunakan hanya metric/channel yang coverage-nya cukup dan "
                "beri caveat. FAIL: jangan gunakan interactions sebagai KPI "
                "sebelum raw data atau mapping diperbaiki."
            ),
        },
        "raw_metric_fields": fields_output,
        "channel_readiness": channels_output,
        "unknown_channels": readiness.get("unknown_channel_rows") or [],
        "numeric_format_diagnostics": parse_output,
        "warnings": warnings,
        "blockers": blockers,
        "next_step": (
            "Jika status PASS/WARN, panggil data_health() lalu lanjutkan hanya "
            "dengan metric yang memenuhi guardrail coverage. Jika status FAIL, "
            "audit header/raw values atau mapping channel sebelum membuat report."
        ),
    }


@mcp.tool()
def count_posts(
    project_name: str,
    start_date: str = "",
    end_date: str = "",
    channels: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
) -> dict[str, Any]:
    """
    Hitung post unik canonical, breakdown channel, dan sentiment by count.

    Gunakan untuk:
    - total post;
    - porsi post negatif;
    - breakdown channel;
    - net sentiment by count.

    Penting:
    - scope issue-only harus memakai keywords/exclude_keywords bila report
      membahas satu isu khusus;
    - tool ini TIDAK mengembalikan net sentiment interaction-weighted;
    - views dan interactions bukan bagian dari tool ini.
    """
    scope = _scope_payload(
        start_date,
        end_date,
        channels,
        keywords,
        exclude_keywords,
        match_mode,
    )

    data = db.count_and_breakdown(
        project_name,
        start_date or None,
        end_date or None,
        **_scope_kwargs(scope),
    )
    if data is None:
        return {
            "found": False,
            "error": f"Campaign '{project_name}' tidak ditemukan.",
            "available_campaigns": _available_projects(),
        }

    total = int(data["total"] or 0)
    classified = int(data["classified_posts"] or 0)

    channel_breakdown = [
        {
            "channel": channel,
            "posts": int(count),
            "share_of_posts_pct": _pct(count, total),
        }
        for channel, count in data["channels"]
    ]

    sentiment_counts = {
        str(sentiment).lower(): int(count)
        for sentiment, count in data["sentiments"]
    }
    positive = sentiment_counts.get("positive", 0)
    negative = sentiment_counts.get("negative", 0)
    neutral = sentiment_counts.get("neutral", 0)
    unclassified = max(0, total - classified)

    sentiment_breakdown = [
        {
            "sentiment": "positive",
            "posts": positive,
            "share_of_classified_posts_pct": _pct(positive, classified),
        },
        {
            "sentiment": "neutral",
            "posts": neutral,
            "share_of_classified_posts_pct": _pct(neutral, classified),
        },
        {
            "sentiment": "negative",
            "posts": negative,
            "share_of_classified_posts_pct": _pct(negative, classified),
        },
    ]

    sentiment_coverage = _pct(classified, total)
    net_by_count = round(
        _pct(positive, classified) - _pct(negative, classified),
        1,
    ) if classified else None

    return {
        "found": True,
        "project_name": project_name,
        "scope": scope,
        "total_posts_unique": total,
        "raw_rows_in_scope": int(data["raw_rows"] or 0),
        "duplicate_rows_removed": int(data["duplicates_removed"] or 0),
        "by_channel": channel_breakdown,
        "sentiment": {
            "basis": "by_count",
            "classified_posts": classified,
            "unclassified_posts_excluded": unclassified,
            "classification_coverage_pct": sentiment_coverage,
            "by_sentiment": sentiment_breakdown,
            "net_sentiment_by_count": net_by_count,
            "directional": sentiment_coverage < 80.0,
        },
        "note": (
            "Sentiment share dihitung dari post terklasifikasi. "
            "Jika coverage <80%, gunakan wording directional. "
            "Net sentiment interaction-weighted sengaja tidak ditampilkan "
            "sebagai KPI default."
        ),
    }


@mcp.tool()
def metrics_summary(
    project_name: str,
    start_date: str = "",
    end_date: str = "",
    channel: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
    include_source_diagnostic: bool = False,
) -> dict[str, Any]:
    """
    Ringkasan metrics dengan interactions dan views TERPISAH.

    Interactions dihitung sesuai channel:
    - Instagram: Likes + Comments
    - Facebook: Likes + Comments + Shares
    - YouTube: Likes + Comments
    - TikTok: Likes + Comments + Shares
    - X/Twitter: Likes + Replies + Retweets

    Views tidak masuk interactions dan dilaporkan terpisah.

    `source_engagement` hanya bisa diminta melalui include_source_diagnostic=true
    untuk audit internal. Jangan gunakan sebagai KPI client-facing.
    """
    scope = _scope_payload(
        start_date,
        end_date,
        channel,
        keywords,
        exclude_keywords,
        match_mode,
    )

    rows = db.metrics_breakdown(
        project_name,
        start_date or None,
        end_date or None,
        channel or None,
        scope["keywords"] or None,
        scope["exclude_keywords"] or None,
        scope["match_mode"],
    )
    if rows is None:
        return {
            "found": False,
            "error": f"Campaign '{project_name}' tidak ditemukan.",
            "available_campaigns": _available_projects(),
        }

    totals = {
        "posts": 0,
        "interactions": 0,
        "views": 0,
        "likes": 0,
        "comments": 0,
        "shares": 0,
        "replies": 0,
        "retweets": 0,
        "buzz": 0,
        "ad_value": 0,
        "pr_value": 0,
        "interaction_applicable_posts": 0,
        "interaction_available_posts": 0,
        "views_available_posts": 0,
        "source_engagement_available_posts": 0,
        "source_engagement": 0,
    }

    by_channel = []
    for row in rows:
        item = {
            "channel": row.get("channel"),
            "channel_type": row.get("channel_norm"),
            "posts": int(row.get("posts") or 0),
            "interactions": _num_clean(row.get("interactions")),
            "views": _num_clean(row.get("views")),
            "interaction_formula": _metric_formula(row.get("channel_norm")),
            "interaction_coverage_pct": _pct(
                int(row.get("interaction_available_posts") or 0),
                int(row.get("interaction_applicable_posts") or 0),
            )
            if int(row.get("interaction_applicable_posts") or 0)
            else None,
            "views_coverage_pct": _pct(
                int(row.get("views_available_posts") or 0),
                int(row.get("posts") or 0),
            ),
            "metrics": {
                "likes": _num_clean(row.get("likes")),
                "comments": _num_clean(row.get("comments")),
                "shares": _num_clean(row.get("shares")),
                "replies": _num_clean(row.get("replies")),
                "retweets": _num_clean(row.get("retweets")),
                "buzz": _num_clean(row.get("buzz")),
                "ad_value": _num_clean(row.get("ad_value")),
                "pr_value": _num_clean(row.get("pr_value")),
            },
        }

        if include_source_diagnostic:
            item["diagnostic_only"] = {
                "source_engagement": _num_clean(row.get("source_engagement")),
                "source_engagement_available_posts": int(
                    row.get("source_engagement_available_posts") or 0
                ),
            }

        by_channel.append(item)

        for key in totals:
            if key in row:
                totals[key] += _num_clean(row.get(key))

    interaction_applicable = int(totals["interaction_applicable_posts"])
    interaction_available = int(totals["interaction_available_posts"])
    total_posts = int(totals["posts"])

    output_totals = {
        "posts": total_posts,
        "interactions": totals["interactions"],
        "views": totals["views"],
        "avg_interactions_per_applicable_post": round(
            totals["interactions"] / interaction_applicable,
            1,
        )
        if interaction_applicable
        else None,
        "interaction_coverage_pct": _pct(
            interaction_available,
            interaction_applicable,
        )
        if interaction_applicable
        else None,
        "views_coverage_pct": _pct(
            int(totals["views_available_posts"]),
            total_posts,
        ),
        "buzz": totals["buzz"],
        "ad_value": totals["ad_value"],
        "pr_value": totals["pr_value"],
    }

    if include_source_diagnostic:
        output_totals["diagnostic_only"] = {
            "source_engagement": totals["source_engagement"],
            "source_engagement_available_posts": int(
                totals["source_engagement_available_posts"]
            ),
            "warning": (
                "Source engagement berasal dari kolom sumber lama dan tidak "
                "boleh dipakai sebagai KPI client-facing tanpa audit definisi."
            ),
        }

    return {
        "found": True,
        "project_name": project_name,
        "scope": scope,
        "metric_definitions": {
            "interactions": (
                "Interaksi dihitung per channel; lihat interaction_formula "
                "pada breakdown channel."
            ),
            "views": "Views/tayangan dilaporkan terpisah dan tidak masuk interactions.",
            "ad_value": (
                "Nilai eksposur media online; bukan engagement dan bukan "
                "indikator otomatis tier media."
            ),
        },
        "totals": output_totals,
        "by_channel": by_channel,
        "note": (
            "Online media tidak memiliki rumus interactions. Jangan menjumlahkan "
            "ad value ke interactions atau views."
        ),
    }


@mcp.tool()
def timeline(
    project_name: str,
    start_date: str = "",
    end_date: str = "",
    channel: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
) -> dict[str, Any]:
    """
    Tren harian canonical posts, interactions, dan views.

    Gunakan untuk menjawab:
    - kapan percakapan naik/turun;
    - apakah puncak post sama atau berbeda dengan puncak interactions/views;
    - bagaimana sentimen by count berubah.

    Bila memakai keywords, output menjadi tren issue-only.
    """
    scope = _scope_payload(
        start_date,
        end_date,
        channel,
        keywords,
        exclude_keywords,
        match_mode,
    )

    rows = db.timeline(
        project_name,
        start_date or None,
        end_date or None,
        channel or None,
        scope["keywords"] or None,
        scope["exclude_keywords"] or None,
        scope["match_mode"],
    )
    if rows is None:
        return {
            "found": False,
            "error": f"Campaign '{project_name}' tidak ditemukan.",
            "available_campaigns": _available_projects(),
        }

    days = []
    for row in rows:
        posts = int(row.get("posts") or 0)
        positive = int(row.get("positive_posts") or 0)
        negative = int(row.get("negative_posts") or 0)
        neutral = int(row.get("neutral_posts") or 0)
        classified = positive + negative + neutral

        days.append(
            {
                "date": row["day"].strftime("%Y-%m-%d") if row.get("day") else None,
                "posts": posts,
                "interactions": _num_clean(row.get("interactions")),
                "views": _num_clean(row.get("views")),
                "sentiment": {
                    "positive_posts": positive,
                    "neutral_posts": neutral,
                    "negative_posts": negative,
                    "classified_posts": classified,
                    "negative_share_pct": _pct(negative, classified),
                    "net_sentiment_by_count": round(
                        _pct(positive, classified) - _pct(negative, classified),
                        1,
                    )
                    if classified
                    else None,
                },
            }
        )

    return {
        "found": True,
        "project_name": project_name,
        "scope": scope,
        "timeline": days,
        "note": (
            "Posts, interactions, dan views dipisahkan. Untuk setiap puncak, "
            "lanjutkan dengan get_posts() pada tanggal tersebut agar pemicu "
            "dibaca dari konten asli."
        ),
    }


@mcp.tool()
def detect_spikes(
    project_name: str,
    start_date: str = "",
    end_date: str = "",
    metric: str = "posts",
    channel: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
    threshold: float = 1.8,
) -> dict[str, Any]:
    """
    Deteksi hari yang nilainya jauh di atas rata-rata.

    Metric yang tersedia:
    - posts
    - interactions
    - views

    `engagement` masih diterima sebagai alias lama untuk interactions.
    Untuk menjelaskan spike, selalu lanjutkan dengan get_posts() pada tanggal
    spike dan baca konten pemicunya.
    """
    selected_metric = _normalise_metric(
        metric,
        {"posts", "interactions", "views"},
        "posts",
    )

    timeline_result = timeline(
        project_name,
        start_date,
        end_date,
        channel,
        keywords,
        exclude_keywords,
        match_mode,
    )
    if not timeline_result.get("found"):
        return timeline_result

    series = timeline_result["timeline"]
    values = [float(day.get(selected_metric) or 0) for day in series]
    average = sum(values) / len(values) if values else 0.0

    spikes = []
    for day in series:
        value = float(day.get(selected_metric) or 0)
        if average > 0 and value >= average * float(threshold):
            spikes.append(
                {
                    "date": day["date"],
                    "metric": selected_metric,
                    "value": _num_clean(value),
                    "x_above_average": round(value / average, 1),
                    "posts": day["posts"],
                    "interactions": day["interactions"],
                    "views": day["views"],
                    "sentiment": day["sentiment"],
                }
            )

    spikes.sort(key=lambda item: item["value"], reverse=True)
    peak = max(series, key=lambda item: float(item.get(selected_metric) or 0)) if series else None

    return {
        "found": True,
        "project_name": project_name,
        "scope": timeline_result["scope"],
        "metric": selected_metric,
        "threshold_x_average": float(threshold),
        "average_per_day": round(average, 1),
        "peak_day": {
            "date": peak["date"],
            "value": _num_clean(peak.get(selected_metric)),
        }
        if peak
        else None,
        "spikes": spikes,
        "timeline": series,
        "next_step": (
            "Panggil get_posts() dengan start_date=end_date tanggal spike dan "
            "sort_by sesuai metric untuk membaca pemicunya."
        ),
    }


@mcp.tool()
def get_posts(
    project_name: str,
    start_date: str = "",
    end_date: str = "",
    channel: str = "",
    sentiment: str = "",
    sort_by: str = "interactions",
    limit: int = 50,
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
) -> dict[str, Any]:
    """
    Ambil post canonical lengkap untuk analisis isi dan bukti report.

    Sort:
    - interactions (default)
    - views
    - shares
    - likes
    - comments
    - date
    - date_desc

    `engagement` diterima sebagai alias lama untuk interactions.
    Gunakan tool ini untuk membaca konten asli; jangan menentukan tema hanya
    dari frekuensi kata atau angka agregat.
    """
    scope = _scope_payload(
        start_date,
        end_date,
        channel,
        keywords,
        exclude_keywords,
        match_mode,
    )

    selected_sort = _normalise_metric(
        sort_by,
        {
            "interactions",
            "views",
            "shares",
            "likes",
            "comments",
            "date",
            "date_desc",
            "source_engagement",
        },
        "interactions",
    )

    max_limit = max(1, min(int(limit or 50), 200))
    rows = db.get_posts(
        project_name,
        start_date or None,
        end_date or None,
        channel or None,
        sentiment or None,
        selected_sort,
        max_limit,
        scope["keywords"] or None,
        scope["exclude_keywords"] or None,
        scope["match_mode"],
    )
    if rows is None:
        return {
            "found": False,
            "error": f"Campaign '{project_name}' tidak ditemukan.",
            "available_campaigns": _available_projects(),
        }

    return {
        "found": True,
        "project_name": project_name,
        "scope": scope,
        "returned": len(rows),
        "sort_by": selected_sort,
        "posts": [_serialise_post(row) for row in rows],
        "note": (
            "Interactions dan views dipisahkan. Post sosial menunjukkan "
            "persepsi/narasi publik; jangan perlakukan sebagai satu-satunya "
            "bukti untuk fakta hukum, keselamatan, kesehatan, atau regulator."
        ),
    }


@mcp.tool()
def top_viral_posts(
    project_name: str,
    start_date: str = "",
    end_date: str = "",
    by: str = "interactions",
    channel: str = "",
    limit: int = 10,
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
) -> dict[str, Any]:
    """
    Post individual tertinggi dalam scope.

    `by`:
    - interactions (default)
    - views
    - shares
    - likes
    - comments
    - viral_score

    `engagement` diterima sebagai alias lama untuk interactions.
    Gunakan output sebagai bukti konten individual, bukan sebagai bukti bahwa
    seluruh campaign atau seluruh narasi bekerja konsisten.
    """
    scope = _scope_payload(
        start_date,
        end_date,
        channel,
        keywords,
        exclude_keywords,
        match_mode,
    )

    selected_metric = _normalise_metric(
        by,
        {
            "interactions",
            "views",
            "shares",
            "likes",
            "comments",
            "viral_score",
            "viral",
            "source_engagement",
        },
        "interactions",
    )

    max_limit = max(1, min(int(limit or 10), 50))
    rows = db.top_posts(
        project_name,
        start_date or None,
        end_date or None,
        channel or None,
        selected_metric,
        max_limit,
        scope["keywords"] or None,
        scope["exclude_keywords"] or None,
        scope["match_mode"],
    )
    if rows is None:
        return {
            "found": False,
            "error": f"Campaign '{project_name}' tidak ditemukan.",
            "available_campaigns": _available_projects(),
        }

    posts = []
    for row in rows:
        post = _serialise_post(row)
        post["viral_score"] = _num_clean(row.get("viral_score"))
        posts.append(post)

    return {
        "found": True,
        "project_name": project_name,
        "scope": scope,
        "sorted_by": selected_metric,
        "posts": posts,
        "note": (
            "Satu post viral bukan bukti pola performa keseluruhan. Bandingkan "
            "dengan jumlah post, jumlah kreator, dan distribusi performa."
        ),
    }


@mcp.tool()
def top_authors(
    project_name: str,
    start_date: str = "",
    end_date: str = "",
    limit: int = 10,
    channels: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
) -> dict[str, Any]:
    """
    Top author/akun berdasarkan total interactions canonical.

    Identitas = author + channel. Views juga dikembalikan terpisah.
    Untuk isu, gunakan keywords agar ranking tidak tercampur percakapan brand
    umum yang tidak relevan.
    """
    scope = _scope_payload(
        start_date,
        end_date,
        channels,
        keywords,
        exclude_keywords,
        match_mode,
    )

    max_limit = max(1, min(int(limit or 10), 50))
    rows = db.top_authors(
        project_name,
        start_date or None,
        end_date or None,
        max_limit,
        scope["channels"] or None,
        scope["keywords"] or None,
        scope["exclude_keywords"] or None,
        scope["match_mode"],
    )
    if rows is None:
        return {
            "found": False,
            "error": f"Campaign '{project_name}' tidak ditemukan.",
            "available_campaigns": _available_projects(),
        }

    authors = []
    for row in rows:
        top_post = row.get("top_post") or {}
        authors.append(
            {
                "author": row.get("author"),
                "channel": row.get("channel"),
                "posts": int(row.get("posts") or 0),
                "total_interactions": _num_clean(row.get("total_interactions")),
                "total_views": _num_clean(row.get("total_views")),
                "sentiment": row.get("sentiment"),
                "top_post": _serialise_post(top_post) if top_post else None,
            }
        )

    return {
        "found": True,
        "project_name": project_name,
        "scope": scope,
        "limit": max_limit,
        "top_authors": authors,
        "note": (
            "Ranking berdasarkan interactions. Cek juga jumlah post dan top post "
            "agar satu outlier tidak dibaca sebagai pola kekuatan akun."
        ),
    }


@mcp.tool()
def top_media(
    project_name: str,
    start_date: str = "",
    end_date: str = "",
    keyword: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
    limit: int = 10,
) -> dict[str, Any]:
    """
    Ranking outlet online media berdasarkan ad value dan jumlah artikel.

    `keyword` memfokuskan satu isu. Ad value:
    - bukan interactions;
    - bukan views;
    - bukan bukti otomatis bahwa outlet adalah tier-1;
    - harus dibaca bersama jumlah artikel dan kualitas outlet.
    """
    scope = _scope_payload(
        start_date,
        end_date,
        "",
        keyword,
        exclude_keywords,
        match_mode,
    )

    max_limit = max(1, min(int(limit or 10), 50))
    rows = db.top_media(
        project_name,
        start_date or None,
        end_date or None,
        keyword or None,
        max_limit,
        scope["exclude_keywords"] or None,
        scope["match_mode"],
    )
    if rows is None:
        return {
            "found": False,
            "error": f"Campaign '{project_name}' tidak ditemukan.",
            "available_campaigns": _available_projects(),
        }

    media = [
        {
            "media_name": row.get("media_name"),
            "articles": int(row.get("articles") or 0),
            "ad_value": _num_clean(row.get("ad_value")),
            "pr_value": _num_clean(row.get("pr_value")),
        }
        for row in rows
    ]

    return {
        "found": True,
        "project_name": project_name,
        "scope": scope,
        "media": media,
        "note": (
            "Ad value adalah nilai eksposur media online. Gunakan sebagai konteks "
            "earned media, bukan sebagai pengganti engagement atau penilaian "
            "kredibilitas outlet."
        ),
    }


@mcp.tool()
def export_raw_data(
    project_name: str,
    start_date: str = "",
    end_date: str = "",
    limit: int = 0,
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
    channels: str = "",
) -> dict[str, Any]:
    """
    Ekspor canonical raw data ke CSV.

    CSV mempertahankan kolom sumber mentah dan menambahkan metadata:
    - `_cogan_interactions`
    - `_cogan_views`
    - `_cogan_interactions_available`
    - `_cogan_views_available`

    Gunakan untuk:
    - audit;
    - coding tema manual;
    - pembuktian issue-only;
    - olah pandas di luar tool.
    """
    scope = _scope_payload(
        start_date,
        end_date,
        channels,
        keywords,
        exclude_keywords,
        match_mode,
    )

    max_limit = int(limit) if limit and int(limit) > 0 else None
    records = db.fetch_raw_records(
        project_name,
        start_date or None,
        end_date or None,
        max_limit,
        scope["keywords"] or None,
        scope["exclude_keywords"] or None,
        scope["match_mode"],
        scope["channels"] or None,
    )
    if records is None:
        return {
            "success": False,
            "error": f"Campaign '{project_name}' tidak ditemukan.",
            "available_campaigns": _available_projects(),
        }
    if not records:
        return {
            "success": False,
            "project_name": project_name,
            "scope": scope,
            "message": "Tidak ada data pada scope tersebut.",
        }

    dataframe = pd.DataFrame(records)

    slug = re.sub(r"[^a-zA-Z0-9]+", "-", project_name.strip().lower()).strip("-")
    filename_parts = [slug or "data"]

    if start_date:
        filename_parts.append(start_date)
    if end_date:
        filename_parts.append(end_date)
    if scope["keywords"]:
        topic_slug = re.sub(
            r"[^a-zA-Z0-9]+",
            "-",
            "-".join(scope["keywords"])[:50].lower(),
        ).strip("-")
        if topic_slug:
            filename_parts.append("topic-" + topic_slug)
    if max_limit:
        filename_parts.append(f"first{max_limit}")

    filename = "_".join(filename_parts) + "_raw.csv"
    csv_path = OUTPUT_DIR / filename
    dataframe.to_csv(csv_path, index=False, encoding="utf-8-sig")

    public_base = _public_base_url()
    download_url = f"{public_base}/files/{filename}" if public_base else ""

    try:
        db.save_output(
            project_name,
            "raw_export",
            {
                "scope": scope,
                "limit": max_limit,
            },
            {
                "row_count": len(records),
                "file": filename,
                "download_url": download_url,
            },
        )
    except Exception:
        # Gagal simpan histori tidak boleh membuat ekspor gagal.
        pass

    return {
        "success": True,
        "project_name": project_name,
        "scope": scope,
        "row_count": len(records),
        "column_count": int(dataframe.shape[1]),
        "download_url": download_url,
        "note": (
            "CSV memakai canonical unique-post layer. Keywords adalah saringan "
            "teks awal; baca konten asli untuk memastikan relevansi."
            if download_url
            else "Link belum aktif. Set PUBLIC_BASE_URL atau RAILWAY_PUBLIC_DOMAIN."
        ),
    }


@mcp.tool()
def compare_periods(
    project_name: str,
    period_a_start: str,
    period_a_end: str,
    period_b_start: str,
    period_b_end: str,
    channel: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
) -> dict[str, Any]:
    """
    Bandingkan dua periode untuk scope yang sama.

    Period A = current period.
    Period B = baseline period.

    Output memisahkan posts, interactions, views, dan sentiment by count.
    Jangan gunakan perbandingan bila lifecycle aktivitas tidak setara
    (mis. pre-event vs pasca-event) tanpa label yang jelas.
    """
    scope = _scope_payload(
        "",
        "",
        channel,
        keywords,
        exclude_keywords,
        match_mode,
    )

    current = db.period_totals(
        project_name,
        period_a_start,
        period_a_end,
        channel or None,
        scope["keywords"] or None,
        scope["exclude_keywords"] or None,
        scope["match_mode"],
    )
    baseline = db.period_totals(
        project_name,
        period_b_start,
        period_b_end,
        channel or None,
        scope["keywords"] or None,
        scope["exclude_keywords"] or None,
        scope["match_mode"],
    )
    if current is None or baseline is None:
        return {
            "found": False,
            "error": f"Campaign '{project_name}' tidak ditemukan.",
            "available_campaigns": _available_projects(),
        }

    def pack(data: dict[str, Any], date_from: str, date_to: str) -> dict[str, Any]:
        posts = int(data.get("posts") or 0)
        positive = int(data.get("positive_posts") or 0)
        negative = int(data.get("negative_posts") or 0)
        neutral = int(data.get("neutral_posts") or 0)
        classified = int(data.get("classified_posts") or 0)

        return {
            "from": date_from,
            "to": date_to,
            "posts": posts,
            "interactions": _num_clean(data.get("interactions")),
            "views": _num_clean(data.get("views")),
            "sentiment": {
                "positive_posts": positive,
                "neutral_posts": neutral,
                "negative_posts": negative,
                "classified_posts": classified,
                "negative_share_pct": _pct(negative, classified),
                "net_sentiment_by_count": round(
                    _pct(positive, classified) - _pct(negative, classified),
                    1,
                )
                if classified
                else None,
                "coverage_pct": _pct(classified, posts),
            },
            "coverage": {
                "interactions_available_of_applicable_pct": _pct(
                    int(data.get("interaction_available_posts") or 0),
                    int(data.get("interaction_applicable_posts") or 0),
                )
                if int(data.get("interaction_applicable_posts") or 0)
                else None,
                "views_available_of_posts_pct": _pct(
                    int(data.get("views_available_posts") or 0),
                    posts,
                ),
            },
        }

    return {
        "found": True,
        "project_name": project_name,
        "scope": scope,
        "period_a_current": pack(current, period_a_start, period_a_end),
        "period_b_baseline": pack(baseline, period_b_start, period_b_end),
        "change": {
            "posts": _delta(current.get("posts"), baseline.get("posts")),
            "interactions": _delta(
                current.get("interactions"),
                baseline.get("interactions"),
            ),
            "views": _delta(current.get("views"), baseline.get("views")),
            "negative_posts": _delta(
                current.get("negative_posts"),
                baseline.get("negative_posts"),
            ),
        },
        "note": (
            "Perbandingan hanya valid bila query, channel, dan fase aktivitas "
            "setara. Interactions dan views tidak digabung."
        ),
    }


@mcp.tool()
def compare_campaigns(
    campaign_a: str,
    campaign_b: str,
    start_date: str = "",
    end_date: str = "",
    channel: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
) -> dict[str, Any]:
    """
    Bandingkan dua campaign pada scope yang sama.

    Metrik yang dikembalikan:
    - posts;
    - interactions;
    - views;
    - buzz;
    - sentiment by count;
    - coverage.

    Pastikan query brand, periode, channel, dan lifecycle aktivitas setara
    sebelum menyimpulkan siapa yang lebih kuat.
    """
    scope = _scope_payload(
        start_date,
        end_date,
        channel,
        keywords,
        exclude_keywords,
        match_mode,
    )

    a = db.period_totals(
        campaign_a,
        start_date or None,
        end_date or None,
        channel or None,
        scope["keywords"] or None,
        scope["exclude_keywords"] or None,
        scope["match_mode"],
    )
    b = db.period_totals(
        campaign_b,
        start_date or None,
        end_date or None,
        channel or None,
        scope["keywords"] or None,
        scope["exclude_keywords"] or None,
        scope["match_mode"],
    )

    missing = [
        name
        for name, data in ((campaign_a, a), (campaign_b, b))
        if data is None
    ]
    if missing:
        return {
            "found": False,
            "error": f"Campaign tidak ditemukan: {', '.join(missing)}",
            "available_campaigns": _available_projects(),
        }

    def pack(name: str, data: dict[str, Any]) -> dict[str, Any]:
        posts = int(data.get("posts") or 0)
        positive = int(data.get("positive_posts") or 0)
        negative = int(data.get("negative_posts") or 0)
        neutral = int(data.get("neutral_posts") or 0)
        classified = int(data.get("classified_posts") or 0)
        applicable = int(data.get("interaction_applicable_posts") or 0)

        return {
            "name": name,
            "posts": posts,
            "interactions": _num_clean(data.get("interactions")),
            "views": _num_clean(data.get("views")),
            "buzz": _num_clean(data.get("buzz")),
            "avg_interactions_per_applicable_post": round(
                _num_clean(data.get("interactions")) / applicable,
                1,
            )
            if applicable
            else None,
            "sentiment": {
                "positive_posts": positive,
                "neutral_posts": neutral,
                "negative_posts": negative,
                "classified_posts": classified,
                "negative_share_pct": _pct(negative, classified),
                "net_sentiment_by_count": round(
                    _pct(positive, classified) - _pct(negative, classified),
                    1,
                )
                if classified
                else None,
                "coverage_pct": _pct(classified, posts),
            },
            "coverage": {
                "interactions_available_of_applicable_pct": _pct(
                    int(data.get("interaction_available_posts") or 0),
                    applicable,
                )
                if applicable
                else None,
                "views_available_of_posts_pct": _pct(
                    int(data.get("views_available_posts") or 0),
                    posts,
                ),
            },
        }

    return {
        "found": True,
        "scope": scope,
        "campaign_a": pack(campaign_a, a),
        "campaign_b": pack(campaign_b, b),
        "difference_a_minus_b": {
            "posts": _delta(a.get("posts"), b.get("posts")),
            "interactions": _delta(
                a.get("interactions"),
                b.get("interactions"),
            ),
            "views": _delta(a.get("views"), b.get("views")),
            "buzz": _delta(a.get("buzz"), b.get("buzz")),
        },
        "note": (
            "Jangan menyimpulkan performa dari satu post viral. Baca top posts "
            "dan cek apakah performa tersebar pada beberapa post/kreator."
        ),
    }


@mcp.tool()
def share_of_voice(
    start_date: str = "",
    end_date: str = "",
    campaigns: str = "",
    metric: str = "buzz",
    channel: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
) -> dict[str, Any]:
    """
    Hitung share antar campaign.

    Metric:
    - buzz (default)
    - posts
    - interactions

    `engagement` diterima sebagai alias lama untuk interactions.
    Basis metric selalu dikembalikan agar SOV tidak ambigu.
    """
    selected_metric = _normalise_metric(
        metric,
        {"buzz", "posts", "interactions"},
        "buzz",
    )

    scope = _scope_payload(
        start_date,
        end_date,
        channel,
        keywords,
        exclude_keywords,
        match_mode,
    )

    names = _clean_csv(campaigns) or db.list_campaigns()
    rows = []
    total_value = 0.0
    missing_metrics = []

    for name in names:
        totals = db.period_totals(
            name,
            start_date or None,
            end_date or None,
            channel or None,
            scope["keywords"] or None,
            scope["exclude_keywords"] or None,
            scope["match_mode"],
        )
        if totals is None:
            continue

        value = _num_clean(totals.get(selected_metric))
        if value is None:
            missing_metrics.append(name)
            value = 0

        rows.append(
            {
                "campaign": name,
                "posts": int(totals.get("posts") or 0),
                "interactions": _num_clean(totals.get("interactions")),
                "buzz": _num_clean(totals.get("buzz")),
                "views": _num_clean(totals.get("views")),
                "value": value,
                "interaction_coverage_pct": _pct(
                    int(totals.get("interaction_available_posts") or 0),
                    int(totals.get("interaction_applicable_posts") or 0),
                )
                if int(totals.get("interaction_applicable_posts") or 0)
                else None,
            }
        )
        total_value += float(value or 0)

    for row in rows:
        row["share_pct"] = _pct(row["value"], total_value)

    rows.sort(key=lambda item: item["value"], reverse=True)

    return {
        "found": True,
        "metric_basis": selected_metric,
        "scope": scope,
        "total_value": _num_clean(total_value),
        "share_of_voice": rows,
        "campaigns_without_metric_value": missing_metrics,
        "note": (
            "SOV menjelaskan proporsi metric yang dipilih, bukan otomatis "
            "kualitas narasi, reputasi, atau efektivitas bisnis. "
            "Jika satu post berada di beberapa campaign, overlap dapat terjadi."
        ),
    }


# ---------------------------------------------------------------------
# Wordcloud MCP tools
# ---------------------------------------------------------------------
@mcp.tool()
def get_project_wordcloud_guidance(project_name: str) -> dict[str, Any]:
    """Ambil guidance wordcloud khusus project."""
    guidance = _read_guidance(project_name)
    return {
        **guidance,
        "guidance_file_exists": (
            CONFIG_DIR / f"{_project_id(project_name)}_wordcloud_guidance.json"
        ).exists(),
    }


@mcp.tool()
def get_wordcloud_candidates(
    project_name: str,
    start_date: str = "",
    end_date: str = "",
    channels: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
    candidate_pool_size: int = 200,
) -> dict[str, Any]:
    """
    Hitung kandidat term mentah dari Title + Content.

    Field performance term:
    - frequency
    - interactions (bukan views)
    - majority sentiment

    Kandidat mentah bukan term final. Model harus menyaring noise, kata generik,
    nama media, URL, dan duplikasi sebelum render.
    """
    candidates = _build_candidates(
        project_name=project_name,
        start_date=start_date or None,
        end_date=end_date or None,
        channels=channels or None,
        keywords=keywords or None,
        exclude_keywords=exclude_keywords or None,
        match_mode=match_mode,
        candidate_pool_size=max(1, int(candidate_pool_size)),
    )

    return {
        "project_id": _project_id(project_name),
        "scope": _scope_payload(
            start_date,
            end_date,
            channels,
            keywords,
            exclude_keywords,
            match_mode,
        ),
        "candidate_pool_size": int(candidate_pool_size),
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


@mcp.tool()
def get_wordcloud_selection_guide() -> str:
    """Baca panduan seleksi term wordcloud dari skills/skill_wordcloud.md."""
    candidates = [
        SKILLS_DIR / "skill_wordcloud.md",
        SKILLS_DIR / "insight-report-generator" / "references" / "skill_wordcloud.md",
    ]

    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8-sig")

    return (
        "PERINGATAN: skill_wordcloud.md tidak ditemukan. Pilih term yang "
        "menjelaskan isu spesifik; buang kata generik, nama media, URL, CTA, "
        "dan frase jurnalistik yang tidak informatif."
    )


@mcp.tool()
def prepare_wordcloud_context(
    project_name: str,
    start_date: str = "",
    end_date: str = "",
    channels: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
    max_output_terms: int = 50,
    mode: str = "frequency",
) -> dict[str, Any]:
    """
    Siapkan bahan untuk wordcloud.

    mode:
    - frequency
    - interactions

    `engagement` diterima sebagai alias lama untuk interactions.
    Tool ini tidak memilih term final; ia hanya memberi kandidat mentah.
    """
    selected_mode = _normalise_wordcloud_mode(mode)
    candidate_pool_size = max(200, int(max_output_terms) * 6)

    candidates = _build_candidates(
        project_name=project_name,
        start_date=start_date or None,
        end_date=end_date or None,
        channels=channels or None,
        keywords=keywords or None,
        exclude_keywords=exclude_keywords or None,
        match_mode=match_mode,
        candidate_pool_size=candidate_pool_size,
    )

    return {
        "selection_guide": get_wordcloud_selection_guide(),
        "project": find_project(project_name),
        "guidance": _read_guidance(project_name),
        "scope": _scope_payload(
            start_date,
            end_date,
            channels,
            keywords,
            exclude_keywords,
            match_mode,
        ),
        "mode": selected_mode,
        "max_output_terms": int(max_output_terms),
        "candidate_pool_size_used": candidate_pool_size,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "next_step": (
            "Nilai kandidat satu per satu sesuai guide. Jangan langsung ambil "
            "N kandidat teratas berdasarkan frequency/interactions. Setelah "
            "term final dipilih, panggil render_selected_wordcloud."
        ),
    }


@mcp.tool()
def render_selected_wordcloud(
    project_name: str,
    selected_terms: list[str],
    start_date: str = "",
    end_date: str = "",
    channels: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
    mode: str = "frequency",
) -> dict[str, Any]:
    """
    Render wordcloud dari term final pilihan model/user.

    Weight mode:
    - frequency
    - interactions

    Views tidak dipakai untuk bobot term agar tetap terpisah dari interactions.
    """
    selected_mode = _normalise_wordcloud_mode(mode)

    stats, unmatched_terms = _stats_for_selected_terms(
        project_name=project_name,
        selected_terms=selected_terms,
        start_date=start_date or None,
        end_date=end_date or None,
        channels=channels or None,
        keywords=keywords or None,
        exclude_keywords=exclude_keywords or None,
        match_mode=match_mode,
    )

    if not stats:
        return {
            "success": False,
            "error": "Tidak ada selected_terms yang ditemukan di data.",
            "project_id": _project_id(project_name),
            "unmatched_terms": unmatched_terms,
        }

    project_id = _project_id(project_name)
    suffix_bits = [project_id, "selected"]

    if start_date:
        suffix_bits.append(start_date)
    if end_date:
        suffix_bits.append(end_date)
    if channels:
        suffix_bits.append(
            re.sub(r"[^a-zA-Z0-9]+", "-", channels.strip()).strip("-")
        )
    suffix_bits.append(selected_mode)

    suffix = "_".join(suffix_bits)
    png_path = OUTPUT_DIR / f"{suffix}_wordcloud.png"
    csv_path = OUTPUT_DIR / f"{suffix}_terms.csv"

    frequencies = {
        item["term"]: max(1, int(item[selected_mode]))
        for item in stats
        if int(item[selected_mode]) > 0
    }
    sentiment_by_term = {
        item["term"]: item["sentiment"]
        for item in stats
    }

    def color_func(word: str, **_: Any) -> str:
        return SENTIMENT_COLORS.get(
            sentiment_by_term.get(word, "neutral"),
            "#6b7280",
        )

    cloud = WordCloud(
        width=1400,
        height=900,
        background_color="white",
        prefer_horizontal=0.9,
        collocations=False,
        random_state=42,
        min_font_size=16,
        max_words=len(frequencies),
    ).generate_from_frequencies(frequencies)
    cloud.recolor(color_func=color_func)
    cloud.to_file(str(png_path))

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "term",
                "frequency",
                "interactions",
                "sentiment",
                "example",
            ],
        )
        writer.writeheader()
        writer.writerows(stats)

    public_base = _public_base_url()
    result = {
        "success": True,
        "project_id": project_id,
        "scope": _scope_payload(
            start_date,
            end_date,
            channels,
            keywords,
            exclude_keywords,
            match_mode,
        ),
        "mode": selected_mode,
        "term_count": len(stats),
        "png_path": str(png_path),
        "csv_path": str(csv_path),
        "download_url": f"{public_base}/files/{png_path.name}" if public_base else "",
        "csv_url": f"{public_base}/files/{csv_path.name}" if public_base else "",
        "terms": stats,
        "unmatched_terms": unmatched_terms,
    }

    try:
        db.save_output(
            campaign_name=project_id,
            kind="wordcloud",
            params={
                "scope": result["scope"],
                "mode": selected_mode,
                "selected_terms": selected_terms,
            },
            result={
                "term_count": len(stats),
                "png_path": str(png_path),
                "csv_path": str(csv_path),
                "download_url": result["download_url"],
                "csv_url": result["csv_url"],
                "terms": stats,
            },
        )
    except Exception as exc:
        result["history_warning"] = f"Gagal menyimpan histori: {exc}"

    if public_base:
        result["note"] = (
            "Buka download_url untuk PNG wordcloud dan csv_url untuk daftar term. "
            "Bobot interactions tidak memasukkan views."
        )
    else:
        result["note"] = (
            "Link unduhan belum aktif. Set PUBLIC_BASE_URL atau "
            "RAILWAY_PUBLIC_DOMAIN."
        )

    return result



# ---------------------------------------------------------------------
# Topic enrichment + report-input MCP tools
# ---------------------------------------------------------------------
def _parse_topic_json(payload: str, field_name: str) -> Any:
    """Parse strict JSON payload supplied by Claude/tool caller."""
    try:
        value = json.loads(payload)
    except Exception as exc:
        raise ValueError(f"{field_name} bukan JSON valid: {exc}") from exc
    return value


@mcp.tool()
def get_topic_taxonomy_sample(
    project_name: str,
    start_date: str = "",
    end_date: str = "",
    channels: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
    sample_size: int = 80,
) -> dict[str, Any]:
    """
    Ambil sample canonical post untuk membuat taxonomy LLM report-topic project.

    Raw Sonar Topic Extraction TIDAK dipakai sebagai topic report. Claude harus
    membaca Title + Content pada sample, lalu membuat taxonomy report-level yang
    memenuhi required_taxonomy_shape.
    """
    try:
        from reporting.enrichment.topic_batch_builder import (
            get_topic_taxonomy_sample as _get_sample,
        )
        return _get_sample(
            project_name=project_name,
            start_date=start_date or None,
            end_date=end_date or None,
            channels=channels or None,
            keywords=keywords or None,
            exclude_keywords=exclude_keywords or None,
            match_mode=match_mode,
            sample_size=int(sample_size),
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def save_topic_taxonomy(
    project_name: str,
    taxonomy_json: str,
    activate: bool = True,
) -> dict[str, Any]:
    """
    Simpan taxonomy report topic baru untuk project.

    taxonomy_json harus object JSON dengan:
    taxonomy_version, taxonomy_name, description, topics[].
    topics wajib menyertakan other_emerging_topic dan not_relevant.

    Version tidak boleh ditimpa; buat v2 bila taxonomy berubah.
    """
    try:
        taxonomy = _parse_topic_json(taxonomy_json, "taxonomy_json")
        if not isinstance(taxonomy, dict):
            return {"success": False, "error": "taxonomy_json harus JSON object."}

        from reporting.enrichment.topic_store import save_taxonomy as _save_taxonomy
        result = _save_taxonomy(
            project_name=project_name,
            taxonomy=taxonomy,
            activate=bool(activate),
        )
        return {
            "success": True,
            "taxonomy": result,
            "next_step": (
                "Panggil get_unclassified_topic_batch untuk mengambil post "
                "yang belum punya cached report topic."
            ),
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def list_topic_taxonomies(project_name: str) -> dict[str, Any]:
    """Lihat taxonomy versions yang tersimpan untuk project."""
    try:
        from reporting.enrichment.topic_store import list_taxonomies as _list
        rows = _list(project_name)
        return {"success": True, "project_name": project_name, "taxonomies": rows}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def get_topic_enrichment_status(
    project_name: str,
    taxonomy_version: str = "",
    start_date: str = "",
    end_date: str = "",
    channels: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
) -> dict[str, Any]:
    """
    Cek jumlah post canonical yang sudah cached topic, pending, review, atau
    sedang direserve batch user lain.
    """
    try:
        from reporting.enrichment.topic_batch_builder import (
            get_topic_enrichment_status as _get_status,
        )
        return _get_status(
            project_name=project_name,
            taxonomy_version=taxonomy_version or None,
            start_date=start_date or None,
            end_date=end_date or None,
            channels=channels or None,
            keywords=keywords or None,
            exclude_keywords=exclude_keywords or None,
            match_mode=match_mode,
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def get_unclassified_topic_batch(
    project_name: str,
    taxonomy_version: str = "",
    start_date: str = "",
    end_date: str = "",
    channels: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
    batch_size: int = 50,
) -> dict[str, Any]:
    """
    Ambil batch post canonical yang BELUM memiliki cached LLM report topic.

    Post classified sebelumnya tidak dikirim ulang. Post yang sedang berada
    pada batch issued milik user lain juga direserve agar tidak diproses ganda.
    Claude wajib mengikuti classification_instruction dan result shape.
    """
    try:
        from reporting.enrichment.topic_batch_builder import (
            get_unclassified_topic_batch as _get_batch,
        )
        return _get_batch(
            project_name=project_name,
            taxonomy_version=taxonomy_version or None,
            start_date=start_date or None,
            end_date=end_date or None,
            channels=channels or None,
            keywords=keywords or None,
            exclude_keywords=exclude_keywords or None,
            match_mode=match_mode,
            batch_size=int(batch_size),
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def save_topic_batch_results(
    batch_id: str,
    results_json: str,
) -> dict[str, Any]:
    """
    Validasi dan simpan hasil topic batch dari Claude.

    results_json harus JSON array. Cogan menolak output yang:
    - tidak mencakup semua post batch;
    - memiliki duplicate/foreign post ID;
    - membuat topic_id baru;
    - memakai status/confidence di luar contract.
    """
    try:
        results = _parse_topic_json(results_json, "results_json")
        if not isinstance(results, list):
            return {"success": False, "error": "results_json harus JSON array."}

        from reporting.enrichment.topic_batch_builder import (
            submit_topic_batch_results as _save_results,
        )
        return _save_results(batch_id=batch_id, results=results)
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def prepare_report_input(
    report_type_id: str,
    project_name: str,
    start_date: str,
    end_date: str,
    confirmed_intent_id: str,
    channels: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
    client_brand: str = "",
    competitor_brands: str = "",
    analysis_objective: str = "",
    topic_taxonomy_version: str = "",
    persist: bool = True,
) -> dict[str, Any]:
    """
    Bangun Task 1 report-ready package dari data canonical.

    Satu interface ini memilih builder berdasarkan report_type_id. Saat ini
    builder yang sudah tersedia adalah daily_social_media_report. Builder lain
    akan aktif setelah file report owner masing-masing diimplementasikan.

    confirmed_intent_id wajib berasal dari Intent Confirmation yang telah
    disetujui; Task 1 tidak menulis recommendation atau slide.
    """
    try:
        from reporting.task1.report_input_dispatcher import (
            prepare_report_input as _prepare,
        )

        scope = _scope_payload(
            start_date,
            end_date,
            channels,
            keywords,
            exclude_keywords,
            match_mode,
        )
        request = {
            "project_name": project_name,
            "start_date": start_date,
            "end_date": end_date,
            "confirmed_intent_id": confirmed_intent_id,
            "channels": scope["channels"],
            "data_scope": scope["universe"],
            "client_brand": client_brand or None,
            "competitor_brands": _clean_csv(competitor_brands),
            "analysis_objective": analysis_objective or None,
            "scope": {
                **scope,
                "topic_taxonomy_version": topic_taxonomy_version or None,
            },
            # Builders hydrate report-specific readiness/data health from
            # canonical source. These placeholders remain explicit.
            "metric_readiness": {},
            "data_health": {},
        }
        result = _prepare(
            report_type_id=report_type_id,
            request=request,
            persist=bool(persist),
        )
        return {
            "success": True,
            "report_input_id": result["report_input_id"],
            "report_type_id": result["report_type_id"],
            "validation": result["validation"],
            "quantitative_view_ids": list(result["quantitative_views"].keys()),
            "qualitative_view_ids": list(result["qualitative_views"].keys()),
            "limitations": result["limitations"],
            "storage": result.get("storage"),
            "report_input": result if not persist else None,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def get_prepared_report_input(
    report_input_id: str,
) -> dict[str, Any]:
    """Ambil full package Task 1 yang telah disimpan dengan report_input_id."""
    try:
        from reporting.storage.report_input_store import get_report_input as _get
        package = _get(report_input_id)
        if package is None:
            return {"found": False, "error": "report_input_id tidak ditemukan."}
        return {"found": True, "report_input": package}
    except Exception as exc:
        return {"found": False, "error": str(exc)}


@mcp.tool()
def get_prepared_report_input_view(
    report_input_id: str,
    view_id: str,
) -> dict[str, Any]:
    """Ambil satu qt_* atau ql_* view dari stored report input."""
    try:
        from reporting.storage.report_input_store import get_report_input as _get
        package = _get(report_input_id)
        if package is None:
            return {"found": False, "error": "report_input_id tidak ditemukan."}
        for container in ("quantitative_views", "qualitative_views"):
            views = package.get(container) or {}
            if view_id in views:
                return {
                    "found": True,
                    "report_input_id": report_input_id,
                    "view": views[view_id],
                }
        return {"found": False, "error": f"view_id '{view_id}' tidak ditemukan."}
    except Exception as exc:
        return {"found": False, "error": str(exc)}


@mcp.tool()
def build_prepared_report_outline(
    report_input_id: str,
    allow_partial: bool = True,
) -> dict[str, Any]:
    """
    Buat Task 2 render plan dari report_input_id.

    Tool ini mengunci section order + source view berdasarkan registry. Ia tidak
    menulis Executive Summary, Action Plan, recommendation, atau PPT.
    """
    try:
        from reporting.task2.report_outline_builder import (
            build_report_outline_from_id as _build_outline,
        )
        return {
            "success": True,
            "outline": _build_outline(
                report_input_id,
                allow_partial=bool(allow_partial),
            ),
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------
# Task 2 Daily Social report renderer
# ---------------------------------------------------------------------
# Guarded Task 2 Daily Social report renderer
# ---------------------------------------------------------------------
@mcp.tool()
def build_daily_social_report_ppt_package(
    report_input_id: str,
    allow_partial: bool = True,
    audience: str = "",
    report_pov: str = "",
    preview_confirmed: bool = False,
) -> dict[str, Any]:
    """Build a PPT-ready Daily Social package only after audience + preview confirmation.

    Guardrail for user experience: for Daily Social reports, the assistant must
    know the target reader/POV and must show the Task 1 data preview first. If
    either is missing, this tool returns an actionable status instead of a PPT
    package, preventing accidental direct PPT creation from a short prompt.
    """
    clean_audience = " ".join(str(audience or "").split())
    clean_pov = " ".join(str(report_pov or "").split())
    if not clean_audience and not clean_pov:
        return {
            "success": False,
            "workflow_status": "NEEDS_AUDIENCE",
            "clarification_question": (
                "Report Daily Social ini dibuat untuk siapa? Pilih salah satu: "
                "PR/Corcom, Insight, Management, CEO/Board, Social Care, Marketing, atau Brand Team."
            ),
            "instruction_to_assistant": (
                "Ask the user who the report is for. Do not build PPTX yet. "
                "After audience is provided, call create_daily_social_report_workflow first to show data preview."
            ),
        }
    if not bool(preview_confirmed):
        return {
            "success": False,
            "workflow_status": "NEEDS_PREVIEW_CONFIRMATION",
            "report_input_id": report_input_id,
            "instruction_to_assistant": (
                "Show Task 1 data preview first using create_daily_social_report_workflow(output_mode='preview_only'). "
                "If the workflow returns NEEDS_AUTO_TOPIC_TAXONOMY or NEEDS_AUTO_TOPIC_CLASSIFICATION, continue those automated steps first. "
                "Then ask the user whether to continue to PPTX. Call this tool again with preview_confirmed=True only after the user confirms."
            ),
        }
    try:
        from reporting.task2.renderers.daily_social_media_report_renderer import (
            build_daily_social_report_package as _build_daily_social_package,
        )
        return _build_daily_social_package(
            report_input_id=report_input_id,
            allow_partial=bool(allow_partial),
            audience_context=clean_audience,
            audience_pov=clean_pov,
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}

# ---------------------------------------------------------------------
# Task 1 Daily Social data preview
# ---------------------------------------------------------------------
# Task 1 Daily Social data preview
# ---------------------------------------------------------------------
@mcp.tool()
def build_daily_social_report_data_preview(
    report_input_id: str,
    include_evidence_limit: int = 10,
) -> dict[str, Any]:
    """Build a user-facing Task 1 data preview before PPT creation.

    Use this to show KPI, sentiment/channel data, topic status, top authors,
    qualitative evidence, and source URLs before creating PPTX.
    """
    try:
        from reporting.task2.renderers.daily_social_media_report_renderer import (
            build_daily_social_report_data_preview as _build_preview,
        )
        return _build_preview(
            report_input_id=report_input_id,
            include_evidence_limit=int(include_evidence_limit),
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}

# ---------------------------------------------------------------------
# One-command Daily Social report workflow
# ---------------------------------------------------------------------
# One-command Daily Social report workflow with smart auto-topic planning
# ---------------------------------------------------------------------
@mcp.tool()
def create_daily_social_report_workflow(
    project_name: str,
    start_date: str,
    end_date: str = "",
    audience: str = "",
    report_pov: str = "",
    client_brand: str = "",
    topic_taxonomy_version: str = "",
    confirmed_intent_id: str = "",
    analysis_objective: str = "",
    channels: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
    output_mode: str = "preview_only",
    include_evidence_limit: int = 10,
    allow_partial: bool = True,
    require_audience: bool = True,
    ask_before_pptx: bool = True,
    auto_topic_mode: str = "smart_sample",
    auto_topic_enabled: bool = True,
    topic_sample_ratio: float = 0.10,
    topic_min_posts: int = 20,
    topic_max_posts: int = 100,
    taxonomy_sample_size: int = 30,
    force_skip_auto_topic: bool = False,
) -> dict[str, Any]:
    """Preferred tool for natural Daily Social report requests.

    Use this FIRST when the user asks naturally, e.g. "buatkan daily report
    Gojek tanggal 2026-05-08". If audience/reader is omitted, this returns
    NEEDS_AUDIENCE so the assistant must ask who the report is for.

    After audience is known, this workflow uses full canonical data for KPI,
    sentiment, author, and content views. For thematic topics, it uses existing
    cache/taxonomy or auto-plans a lightweight smart sample by default:
    10% of topic-eligible posts, minimum 20, maximum 100. The user should not
    be asked to manage taxonomy/enrichment/batches.

    Default output_mode is preview_only: show Task 1 data preview first, then
    wait for user confirmation before creating PPTX.
    """
    try:
        from reporting.task2.workflows.daily_social_report_workflow import (
            create_daily_social_report_workflow as _workflow,
        )
        return _workflow(
            project_name=project_name,
            start_date=start_date,
            end_date=end_date or None,
            audience=audience or None,
            report_pov=report_pov or None,
            client_brand=client_brand or None,
            topic_taxonomy_version=topic_taxonomy_version or None,
            confirmed_intent_id=confirmed_intent_id or None,
            analysis_objective=analysis_objective or None,
            channels=channels or None,
            keywords=keywords or None,
            exclude_keywords=exclude_keywords or None,
            match_mode=match_mode,
            output_mode=output_mode or "preview_only",
            include_evidence_limit=int(include_evidence_limit),
            allow_partial=bool(allow_partial),
            require_audience=bool(require_audience),
            ask_before_pptx=bool(ask_before_pptx),
            auto_topic_mode=auto_topic_mode or "smart_sample",
            auto_topic_enabled=bool(auto_topic_enabled),
            topic_sample_ratio=float(topic_sample_ratio),
            topic_min_posts=int(topic_min_posts),
            topic_max_posts=int(topic_max_posts),
            taxonomy_sample_size=int(taxonomy_sample_size),
            force_skip_auto_topic=bool(force_skip_auto_topic),
        )
    except Exception as exc:
        return {"success": False, "workflow_status": "ERROR", "error": str(exc)}

# ---------------------------------------------------------------------
# One-command Mainstream Media Report workflow with smart auto-issue planning
# ---------------------------------------------------------------------
@mcp.tool()
def create_mainstream_media_report_workflow(
    project_name: str,
    start_date: str,
    end_date: str = "",
    audience: str = "",
    report_pov: str = "",
    client_brand: str = "",
    topic_taxonomy_version: str = "",
    issue_taxonomy_version: str = "",
    confirmed_intent_id: str = "",
    analysis_objective: str = "",
    channels: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
    output_mode: str = "preview_only",
    include_evidence_limit: int = 10,
    allow_partial: bool = True,
    require_audience: bool = True,
    ask_before_pptx: bool = True,
    auto_issue_mode: str = "smart_sample",
    auto_issue_enabled: bool = True,
    issue_sample_ratio: float = 0.10,
    issue_min_articles: int = 20,
    issue_max_articles: int = 100,
    taxonomy_sample_size: int = 30,
    force_skip_auto_issue: bool = False,
) -> dict[str, Any]:
    """Preferred tool for natural Mainstream Media Report requests.

    Use this FIRST when the user asks naturally, e.g. "buatkan mainstream
    media report Gojek tanggal 2026-05-08". If audience/reader is omitted,
    this returns NEEDS_AUDIENCE so the assistant must ask who the report is for.

    After audience is known, the workflow uses full canonical mainstream data
    for KPI, sentiment, media contributors, and article evidence. For issue
    analysis, it uses existing cache/taxonomy or auto-plans a lightweight smart
    sample by default: 10% of issue-eligible articles, minimum 20, maximum 100.
    The user should not be asked to manage taxonomy/enrichment/batches.

    Default output_mode is preview_only: show Task 1 data preview first, then
    wait for user confirmation before creating PPTX.
    """
    try:
        from reporting.task2.workflows.mainstream_media_report_workflow import (
            create_mainstream_media_report_workflow as _workflow,
        )
        return _workflow(
            project_name=project_name,
            start_date=start_date,
            end_date=end_date or None,
            audience=audience or None,
            report_pov=report_pov or None,
            client_brand=client_brand or None,
            topic_taxonomy_version=topic_taxonomy_version or None,
            issue_taxonomy_version=issue_taxonomy_version or None,
            confirmed_intent_id=confirmed_intent_id or None,
            analysis_objective=analysis_objective or None,
            channels=channels or None,
            keywords=keywords or None,
            exclude_keywords=exclude_keywords or None,
            match_mode=match_mode,
            output_mode=output_mode or "preview_only",
            include_evidence_limit=int(include_evidence_limit),
            allow_partial=bool(allow_partial),
            require_audience=bool(require_audience),
            ask_before_pptx=bool(ask_before_pptx),
            auto_issue_mode=auto_issue_mode or "smart_sample",
            auto_issue_enabled=bool(auto_issue_enabled),
            issue_sample_ratio=float(issue_sample_ratio),
            issue_min_articles=int(issue_min_articles),
            issue_max_articles=int(issue_max_articles),
            taxonomy_sample_size=int(taxonomy_sample_size),
            force_skip_auto_issue=bool(force_skip_auto_issue),
        )
    except Exception as exc:
        return {"success": False, "workflow_status": "ERROR", "error": str(exc)}

# ---------------------------------------------------------------------
# Task 1 Mainstream Media data preview
# ---------------------------------------------------------------------
@mcp.tool()
def build_mainstream_media_report_data_preview(
    report_input_id: str,
    include_evidence_limit: int = 10,
) -> dict[str, Any]:
    """Build a user-facing Task 1 data preview before MMR PPT creation.

    Shows KPI, channel/media distribution, sentiment, top issues, top media,
    article evidence URLs, sensitive headlines, limitations, and readiness.
    """
    try:
        from reporting.task2.renderers.mainstream_media_report_renderer import (
            build_mainstream_media_report_data_preview as _build_preview,
        )
        return _build_preview(
            report_input_id=report_input_id,
            include_evidence_limit=int(include_evidence_limit),
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}

# ---------------------------------------------------------------------
# Guarded Task 2 Mainstream Media Report renderer
# ---------------------------------------------------------------------
@mcp.tool()
def build_mainstream_media_report_ppt_package(
    report_input_id: str,
    allow_partial: bool = True,
    audience: str = "",
    report_pov: str = "",
    preview_confirmed: bool = False,
) -> dict[str, Any]:
    """Build a PPT-ready Mainstream Media package only after audience + preview confirmation.

    Guardrail: assistant must know the target reader/POV and must show Task 1
    data preview first. If either is missing, this tool returns an actionable
    status instead of a PPT package.
    """
    clean_audience = " ".join(str(audience or "").split())
    clean_pov = " ".join(str(report_pov or "").split())
    if not clean_audience and not clean_pov:
        return {
            "success": False,
            "workflow_status": "NEEDS_AUDIENCE",
            "clarification_question": (
                "Mainstream Media Report ini dibuat untuk siapa? Pilih salah satu: "
                "PR/Corcom, Media Relations, Insight, Management, CEO/Board, Legal/Crisis Team, atau Marketing/Brand."
            ),
            "instruction_to_assistant": (
                "Ask the user who the report is for. Do not build PPTX yet. "
                "After audience is provided, call create_mainstream_media_report_workflow first to show data preview."
            ),
        }
    if not bool(preview_confirmed):
        return {
            "success": False,
            "workflow_status": "NEEDS_PREVIEW_CONFIRMATION",
            "report_input_id": report_input_id,
            "instruction_to_assistant": (
                "Show Task 1 data preview first using create_mainstream_media_report_workflow(output_mode='preview_only'). "
                "If the workflow returns NEEDS_AUTO_ISSUE_TAXONOMY or NEEDS_AUTO_ISSUE_CLASSIFICATION, continue those automated steps first. "
                "Then ask the user whether to continue to PPTX. Call this tool again with preview_confirmed=True only after the user confirms."
            ),
        }
    try:
        from reporting.task2.renderers.mainstream_media_report_renderer import (
            build_mainstream_media_report_package as _build_package,
        )
        return _build_package(
            report_input_id=report_input_id,
            allow_partial=bool(allow_partial),
            audience_context=clean_audience,
            audience_pov=clean_pov,
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}

# ---------------------------------------------------------------------
# One-command Competitive Analysis workflow v2
# ---------------------------------------------------------------------
@mcp.tool()
def create_competitive_analysis_report_workflow(
    project_name: str,
    start_date: str,
    end_date: str = "",
    audience: str = "",
    report_pov: str = "",
    client_brand: str = "",
    competitors: str = "",
    competitor_brands: str = "",
    confirmed_intent_id: str = "",
    analysis_objective: str = "",
    channels: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
    industry: str = "",
    market: str = "",
    topic_taxonomy_version: str = "",
    output_mode: str = "preview_only",
    include_evidence_limit: int = 10,
    allow_partial: bool = True,
    require_audience: bool = True,
    require_competitors: bool = True,
    ask_before_pptx: bool = True,
) -> dict[str, Any]:
    """Preferred tool for natural Competitive Analysis requests.

    Use this FIRST when user asks for Competitive Analysis. If audience or
    competitor list is missing, this returns NEEDS_AUDIENCE or NEEDS_COMPETITORS.
    If competitive topic/narrative taxonomy/classification is missing, this
    returns NEEDS_AUTO_COMPETITIVE_TAXONOMY or NEEDS_AUTO_COMPETITIVE_TOPIC_CLASSIFICATION.

    Topic policy: final CA topic/narrative metrics use cached LLM assignments
    from Title + Content. Raw Topic Extraction, legacy Aspect, and Entity
    Extraction are diagnostic only, not core source of truth.

    Main slide URL policy: use Evidence IDs only. Full URLs belong in Appendix
    and export_report_data_pack.
    """
    try:
        from reporting.task2.workflows.competitive_analysis_report_workflow import (
            create_competitive_analysis_report_workflow as _workflow,
        )
        return _workflow(
            project_name=project_name,
            start_date=start_date,
            end_date=end_date or None,
            audience=audience or None,
            report_pov=report_pov or None,
            client_brand=client_brand or None,
            competitors=competitors or None,
            competitor_brands=competitor_brands or None,
            confirmed_intent_id=confirmed_intent_id or None,
            analysis_objective=analysis_objective or None,
            channels=channels or None,
            keywords=keywords or None,
            exclude_keywords=exclude_keywords or None,
            match_mode=match_mode or "any",
            industry=industry or None,
            market=market or None,
            topic_taxonomy_version=topic_taxonomy_version or None,
            output_mode=output_mode or "preview_only",
            include_evidence_limit=int(include_evidence_limit),
            allow_partial=bool(allow_partial),
            require_audience=bool(require_audience),
            require_competitors=bool(require_competitors),
            ask_before_pptx=bool(ask_before_pptx),
        )
    except Exception as exc:
        return {"success": False, "workflow_status": "ERROR", "error": str(exc)}

# ---------------------------------------------------------------------
# Task 1 Competitive Analysis data preview
# ---------------------------------------------------------------------
@mcp.tool()
def build_competitive_analysis_report_data_preview(
    report_input_id: str,
    include_evidence_limit: int = 10,
) -> dict[str, Any]:
    """Build user-facing Task 1 preview before Competitive Analysis PPT creation.

    Shows brand universe, SOV/SOE, sentiment, channel/content benchmark,
    LLM topic/narrative coverage, limitations, and evidence IDs. Full URLs are
    kept for Appendix/Data Pack.
    """
    try:
        from reporting.task2.renderers.competitive_analysis_report_renderer import (
            build_competitive_analysis_report_data_preview as _build_preview,
        )
        return _build_preview(
            report_input_id=report_input_id,
            include_evidence_limit=int(include_evidence_limit),
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}

# ---------------------------------------------------------------------
# Guarded Task 2 Competitive Analysis renderer
# ---------------------------------------------------------------------
@mcp.tool()
def build_competitive_analysis_report_ppt_package(
    report_input_id: str,
    allow_partial: bool = True,
    audience: str = "",
    report_pov: str = "",
    preview_confirmed: bool = False,
) -> dict[str, Any]:
    """Build a PPT-ready Competitive Analysis package after preview confirmation.

    Guardrail: assistant must know target reader/POV and must show Task 1 data
    preview first. If missing, this returns an actionable status instead of a
    PPT package.
    """
    clean_audience = " ".join(str(audience or "").split())
    clean_pov = " ".join(str(report_pov or "").split())
    if not clean_audience and not clean_pov:
        return {
            "success": False,
            "workflow_status": "NEEDS_AUDIENCE",
            "clarification_question": (
                "Competitive Analysis ini dibuat untuk siapa? Pilih salah satu: "
                "Management, CEO/Board, Marketing/Brand, Marketing/Content, PR/Corcom, atau Insight Team."
            ),
            "instruction_to_assistant": (
                "Ask the user who the report is for. Do not build PPTX yet. "
                "After audience is provided, call create_competitive_analysis_report_workflow first to show data preview."
            ),
        }
    if not bool(preview_confirmed):
        return {
            "success": False,
            "workflow_status": "NEEDS_PREVIEW_CONFIRMATION",
            "report_input_id": report_input_id,
            "instruction_to_assistant": (
                "Show Task 1 data preview first using create_competitive_analysis_report_workflow(output_mode='preview_only'). "
                "Then ask the user whether to continue to PPTX. Call this tool again with preview_confirmed=True only after the user confirms."
            ),
        }
    try:
        from reporting.task2.renderers.competitive_analysis_report_renderer import (
            build_competitive_analysis_report_package as _build_package,
        )
        return _build_package(
            report_input_id=report_input_id,
            allow_partial=bool(allow_partial),
            audience_context=clean_audience,
            audience_pov=clean_pov,
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}

# ---------------------------------------------------------------------
# Insight report skill loaders
# ---------------------------------------------------------------------
ENGINE_DIR = SKILLS_DIR / "insight-report-generator"

# Semua path ini adalah canonical. methodology.md sengaja tidak lagi dimuat.
_ENGINE_FILES = [
    ("SKILL.md — router dan pembagian tugas", "SKILL.md"),
    ("skill_report.md — storytelling client-first", "references/skill_report.md"),
    ("consistency_contract.md — definisi metrik dan data", "references/consistency_contract.md"),
    ("stage_data_cogan.md — cara tarik dan freeze data", "references/stage_data_cogan.md"),
    ("system_prompt.md — workflow eksekusi report", "references/system_prompt.md"),
    ("perpustakaan_resep_slide.md — pilihan visual", "references/perpustakaan_resep_slide.md"),
    ("quality_framework.md — quality gate", "references/quality_framework.md"),
    ("skill_mapping.yaml — mapping tool opsional", "skill_mapping.yaml"),
]


def _first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


@mcp.tool()
def get_report_guide() -> str:
    """
    WAJIB dipanggil sebelum membuat report apa pun.

    Membaca panduan editorial client-first.

    Untuk request report/deck, tampilkan Intent Confirmation dan tunggu
    persetujuan user sebelum memanggil tool analitis. Setelah disetujui:
    - mulai dari pertanyaan bisnis dan keputusan;
    - data dipakai sebagai bukti, bukan kerangka;
    - issue-only harus dipisahkan dari brand universe;
    - client-facing deck tidak memuat framework internal.
    """
    guide_path = _first_existing(
        [
            ENGINE_DIR / "references" / "skill_report.md",
            SKILLS_DIR / "skill_report.md",
        ]
    )

    if guide_path is None:
        return (
            "PERINGATAN: skill_report.md tidak ditemukan. Mulai dari pertanyaan "
            "bisnis dan keputusan klien; tarik data hanya sebagai bukti; gunakan "
            "bahasa manusia; pisahkan issue-only dari brand universe; tutup "
            "dengan keputusan milik klien."
        )

    intent_gate = (
        "# RUNTIME GATE\n"
        "# Untuk report/deck/narrative analysis: tampilkan Intent Confirmation "
        "dan tunggu persetujuan user sebelum memanggil data_health(), "
        "metrics_summary(), timeline(), get_posts(), atau tool analitis lain.\n"
        "# Setelah persetujuan, panggil validate_metric_readiness() dan "
        "data_health() sebelum interactions/views dipakai sebagai KPI.\n\n"
    )
    return intent_gate + guide_path.read_text(encoding="utf-8-sig")


@mcp.tool()
def get_insight_report_skill() -> str:
    """
    Ambil paket skill report versi canonical.

    Urutan baca:
    1. SKILL.md
    2. skill_report.md
    3. consistency_contract.md
    4. stage_data_cogan.md
    5. system_prompt.md
    6. resep visual yang relevan
    7. quality_framework.md sebelum final delivery

    methodology.md tidak dimuat karena sudah deprecated.
    """
    header = (
        "# COGAN INSIGHT REPORT ENGINE — CANONICAL PACKAGE\n"
        "# Gunakan aturan terbaru saja. Jangan memuat methodology.md lama.\n"
        "# RUNTIME GATE: Untuk report/deck/narrative analysis, lakukan Intent "
        "Confirmation dan tunggu approval user sebelum tool analitis dipanggil.\n"
        "# Setelah approval, panggil validate_metric_readiness() dan "
        "data_health() sebelum interactions/views dipakai sebagai KPI.\n"
        "# Angka internal berasal dari Cogan/raw data; fakta eksternal harus "
        "# diberi sumber terpisah.\n"
    )

    parts = [header]
    missing = []

    for title, relative_path in _ENGINE_FILES:
        path = ENGINE_DIR / relative_path
        if path.exists():
            body = path.read_text(encoding="utf-8-sig")
            parts.append(f"\n\n{'=' * 72}\n### {title}\n{'=' * 72}\n\n{body}")
        else:
            missing.append(relative_path)

    if missing:
        parts.append(
            "\n\n[PERINGATAN] File skill belum ditemukan: "
            + ", ".join(missing)
            + ". Pastikan folder skills/insight-report-generator sudah "
            "memakai struktur versi baru."
        )

    return "".join(parts)


# ---------------------------------------------------------------------
# Output / report history tools
# ---------------------------------------------------------------------
@mcp.tool()
def get_recent_outputs(
    project_name: str = "",
    kind: str = "",
    limit: int = 10,
) -> dict[str, Any]:
    """Lihat histori file yang pernah digenerate, mis. wordcloud atau raw export."""
    rows = db.list_outputs(
        campaign_name=project_name or None,
        kind=kind or None,
        limit=max(1, int(limit)),
    )

    for row in rows:
        if row.get("created_at") is not None:
            row["created_at"] = row["created_at"].isoformat()

    return {"count": len(rows), "outputs": rows}


@mcp.tool()
def save_report(
    project_name: str,
    start_date: str = "",
    end_date: str = "",
    title: str = "",
    payload: str = "",
) -> dict[str, Any]:
    """
    Simpan report penuh ke database Cogan.

    Payload sebaiknya memuat:
    - deck_data.json yang sudah frozen/reconciled;
    - scope;
    - metric contract version;
    - narasi/slide brief;
    - sumber yang dipakai.

    Jangan menyimpan payload yang belum valid sebagai final report.
    """
    try:
        data = json.loads(payload) if payload else {}
    except Exception as exc:
        return {"saved": False, "error": f"payload bukan JSON valid: {exc}"}

    if not isinstance(data, dict):
        data = {"report": data}

    report_id = db.save_report(
        project_name or None,
        start_date or None,
        end_date or None,
        title or None,
        data,
    )

    return {
        "saved": True,
        "id": report_id,
        "project_name": project_name,
        "period": {"from": start_date or None, "to": end_date or None},
        "note": (
            "Report tersimpan. Pastikan payload berikutnya memakai scope dan "
            "contract version yang konsisten agar comparison antar periode valid."
        ),
    }


@mcp.tool()
def get_previous_report(
    project_name: str,
    before_date: str = "",
    period_start: str = "",
    period_end: str = "",
) -> dict[str, Any]:
    """Ambil satu report tersimpan untuk comparison atau audit historis."""
    row = db.get_previous_report(
        project_name,
        before_date or None,
        period_start or None,
        period_end or None,
    )

    if not row:
        return {
            "found": False,
            "project_name": project_name,
            "note": (
                "Belum ada report tersimpan untuk scope/periode ini. "
                "Comparison otomatis baru tersedia setelah report disimpan."
            ),
        }

    for key in ("period_start", "period_end", "created_at"):
        if row.get(key) is not None and hasattr(row[key], "isoformat"):
            row[key] = row[key].isoformat()

    return {"found": True, "project_name": project_name, "report": row}


@mcp.tool()
def list_saved_reports(
    project_name: str = "",
    limit: int = 20,
) -> dict[str, Any]:
    """Daftar report tersimpan tanpa payload besar."""
    rows = db.list_saved_reports(
        project_name or None,
        max(1, int(limit)),
    )

    for row in rows:
        for key in ("period_start", "period_end", "created_at"):
            if row.get(key) is not None and hasattr(row[key], "isoformat"):
                row[key] = row[key].isoformat()

    return {"count": len(rows), "reports": rows}


# --- REPORT DATA PACK EXPORT TOOLS V1 START ---
@mcp.tool()
def export_report_data_pack(
    report_input_id: str,
    output_format: str = "xlsx",
    include_raw_data: bool = True,
    raw_row_limit: int = 50000,
    include_task1_views: bool = True,
    include_file_base64: bool = False,
    max_base64_bytes: int = 4000000,
) -> dict[str, Any]:
    """
    Export audit data pack for a stored Task 1 report_input_id.

    Use this after prepare_report_input / workflow preview when the user asks
    for raw data, Excel, CSV, evidence pack, audit pack, or proof that report
    numbers are not invented.

    Output:
    - xlsx multi-sheet by default, fallback to csv_zip if xlsx writer is not available.
    - Task 1 quantitative and qualitative views.
    - limitations and evidence log.
    - optional raw canonical data for the exact report scope.
    - optional file_base64 for assistants that need to create a downloadable file.
    """
    try:
        from reporting.exports.report_data_pack_exporter import (
            export_report_data_pack as _export_report_data_pack,
        )

        return _export_report_data_pack(
            report_input_id=report_input_id,
            output_format=output_format,
            include_raw_data=include_raw_data,
            raw_row_limit=max(1, int(raw_row_limit or 1)),
            include_task1_views=include_task1_views,
            include_file_base64=bool(include_file_base64),
            max_base64_bytes=max(1, int(max_base64_bytes or 1)),
        )
    except Exception as exc:
        return {
            "success": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "report_input_id": report_input_id,
            "instruction": "Periksa report_input_id, DATABASE_URL, dan dependency xlsx writer. Coba output_format='csv_zip' jika xlsx gagal.",
        }


@mcp.tool()
def export_raw_scope_data(
    project_name: str,
    start_date: str,
    end_date: str,
    report_type_id: str = "",
    channels: str = "",
    output_format: str = "xlsx",
    row_limit: int = 50000,
    include_file_base64: bool = False,
    max_base64_bytes: int = 4000000,
) -> dict[str, Any]:
    """
    Export raw canonical data for an ad-hoc project/date/channel scope.

    Prefer export_report_data_pack(report_input_id) for report audit, because it
    exports the exact Task 1 package used for PPT. Use this tool only when user
    explicitly asks for raw scope data without a report_input_id.
    """
    try:
        from reporting.exports.report_data_pack_exporter import (
            export_raw_scope_data as _export_raw_scope_data,
        )

        channel_list = [item.strip() for item in (channels or "").split(",") if item.strip()]
        return _export_raw_scope_data(
            project_name=project_name,
            start_date=start_date,
            end_date=end_date,
            report_type_id=report_type_id,
            channels=channel_list,
            output_format=output_format,
            row_limit=max(1, int(row_limit or 1)),
            include_file_base64=bool(include_file_base64),
            max_base64_bytes=max(1, int(max_base64_bytes or 1)),
        )
    except Exception as exc:
        return {
            "success": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "project_name": project_name,
            "period": {"start_date": start_date, "end_date": end_date},
            "instruction": "Periksa project_name/periode/channel dan DATABASE_URL. Untuk audit report, pakai export_report_data_pack bila ada report_input_id.",
        }
# --- REPORT DATA PACK EXPORT TOOLS V1 END ---

# ---------------------------------------------------------------------
# Cross-project anomaly scan
# ---------------------------------------------------------------------
@mcp.tool()
def scan_all_anomalies(
    project_names: str = "",
    start_date: str = "",
    end_date: str = "",
    metric: str = "posts",
    threshold: float = 1.8,
    per_campaign: int = 1,
) -> dict[str, Any]:
    """
    Scan anomaly lintas campaign.

    Metric:
    - posts
    - interactions
    - views

    Gunakan hanya SETELAH Intent Confirmation disetujui, ketika report
    membutuhkan exploratory anomaly scan atau user meminta monitoring operasional.

    Jangan gunakan tool ini untuk melewati Intent Confirmation pada request
    report/deck. Setelah mendapat spike, baca konten pada tanggal tersebut
    dengan get_posts() sebelum menarik kesimpulan.
    """
    selected_metric = _normalise_metric(
        metric,
        {"posts", "interactions", "views"},
        "posts",
    )

    names = _clean_csv(project_names) or db.list_campaigns()
    anomalies: list[dict[str, Any]] = []
    scanned = 0
    missing: list[str] = []

    for name in names:
        result = detect_spikes(
            name,
            start_date,
            end_date,
            selected_metric,
            "",
            "",
            "",
            "any",
            threshold,
        )
        if not result.get("found"):
            missing.append(name)
            continue

        scanned += 1
        anomalies.extend(
            [
                {
                    "project_name": name,
                    **spike,
                }
                for spike in result["spikes"][: max(1, int(per_campaign))]
            ]
        )

    anomalies.sort(key=lambda item: item["x_above_average"], reverse=True)

    return {
        "found": True,
        "metric": selected_metric,
        "threshold_x_average": float(threshold),
        "period": {"from": start_date or None, "to": end_date or None},
        "campaigns_scanned": scanned,
        "campaigns_not_found": missing,
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
        "note": (
            "Anomali menunjukkan kapan perlu membaca data lebih lanjut, bukan "
            "kesimpulan otomatis tentang penyebab atau tingkat risiko."
        ),
    }


# ---------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------
if __name__ == "__main__":
    try:
        db.init_db()
    except Exception as exc:
        print(f"[warning] init_db gagal: {exc}")

    # Railway akan memberi PORT. Tanpa PORT (mis. Claude Desktop lokal),
    # FastMCP memakai stdio.
    if os.environ.get("PORT"):
        mcp.run(transport="streamable-http")
    else:
        mcp.run()
