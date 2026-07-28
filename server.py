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
    GATE - TENTUKAN JALUR DULU BILA INI MENGARAH KE REPORT.
    Tool ini adalah tool diagnostik data, BUKAN pintu masuk report.

    Bila permintaan user mengarah ke report / laporan / PPT / deck / analisa
    mingguan-bulanan, JANGAN jadikan hasil tool ini sebagai jawaban akhir.
    Panggil get_report_guide() lebih dulu, lalu tentukan Jalur 1 (user
    menyebut tipe report) atau Jalur 2 (top-down). Ragu = Jalur 2.

    Bila user meminta client brief / presales brief / meeting prep, panggil
    get_intelligence_brief_guide(). Bila user meminta sales deck / pitch deck /
    proposal deck, panggil get_sales_deck_guide().

    Boleh dipakai langsung TANPA guide hanya untuk pertanyaan data ad-hoc yang
    tidak menghasilkan report: cek ketersediaan data, satu angka, atau
    verifikasi cepat.

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
    GATE - TENTUKAN JALUR DULU BILA INI MENGARAH KE REPORT.
    Tool ini adalah tool diagnostik data, BUKAN pintu masuk report.

    Bila permintaan user mengarah ke report / laporan / PPT / deck / analisa
    mingguan-bulanan, JANGAN jadikan hasil tool ini sebagai jawaban akhir.
    Panggil get_report_guide() lebih dulu, lalu tentukan Jalur 1 (user
    menyebut tipe report) atau Jalur 2 (top-down). Ragu = Jalur 2.

    Bila user meminta client brief / presales brief / meeting prep, panggil
    get_intelligence_brief_guide(). Bila user meminta sales deck / pitch deck /
    proposal deck, panggil get_sales_deck_guide().

    Boleh dipakai langsung TANPA guide hanya untuk pertanyaan data ad-hoc yang
    tidak menghasilkan report: cek ketersediaan data, satu angka, atau
    verifikasi cepat.

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
    GATE - TENTUKAN JALUR DULU BILA INI MENGARAH KE REPORT.
    Tool ini adalah tool diagnostik data, BUKAN pintu masuk report.

    Bila permintaan user mengarah ke report / laporan / PPT / deck / analisa
    mingguan-bulanan, JANGAN jadikan hasil tool ini sebagai jawaban akhir.
    Panggil get_report_guide() lebih dulu, lalu tentukan Jalur 1 (user
    menyebut tipe report) atau Jalur 2 (top-down). Ragu = Jalur 2.

    Bila user meminta client brief / presales brief / meeting prep, panggil
    get_intelligence_brief_guide(). Bila user meminta sales deck / pitch deck /
    proposal deck, panggil get_sales_deck_guide().

    Boleh dipakai langsung TANPA guide hanya untuk pertanyaan data ad-hoc yang
    tidak menghasilkan report: cek ketersediaan data, satu angka, atau
    verifikasi cepat.

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
    GATE - TENTUKAN JALUR DULU BILA INI MENGARAH KE REPORT.
    Tool ini adalah tool diagnostik data, BUKAN pintu masuk report.

    Bila permintaan user mengarah ke report / laporan / PPT / deck / analisa
    mingguan-bulanan, JANGAN jadikan hasil tool ini sebagai jawaban akhir.
    Panggil get_report_guide() lebih dulu, lalu tentukan Jalur 1 (user
    menyebut tipe report) atau Jalur 2 (top-down). Ragu = Jalur 2.

    Bila user meminta client brief / presales brief / meeting prep, panggil
    get_intelligence_brief_guide(). Bila user meminta sales deck / pitch deck /
    proposal deck, panggil get_sales_deck_guide().

    Boleh dipakai langsung TANPA guide hanya untuk pertanyaan data ad-hoc yang
    tidak menghasilkan report: cek ketersediaan data, satu angka, atau
    verifikasi cepat.

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
    GATE - TENTUKAN JALUR DULU BILA INI MENGARAH KE REPORT.
    Tool ini adalah tool diagnostik data, BUKAN pintu masuk report.

    Bila permintaan user mengarah ke report / laporan / PPT / deck / analisa
    mingguan-bulanan, JANGAN jadikan hasil tool ini sebagai jawaban akhir.
    Panggil get_report_guide() lebih dulu, lalu tentukan Jalur 1 (user
    menyebut tipe report) atau Jalur 2 (top-down). Ragu = Jalur 2.

    Bila user meminta client brief / presales brief / meeting prep, panggil
    get_intelligence_brief_guide(). Bila user meminta sales deck / pitch deck /
    proposal deck, panggil get_sales_deck_guide().

    Boleh dipakai langsung TANPA guide hanya untuk pertanyaan data ad-hoc yang
    tidak menghasilkan report: cek ketersediaan data, satu angka, atau
    verifikasi cepat.

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
    GATE - TENTUKAN JALUR DULU BILA INI MENGARAH KE REPORT.
    Tool ini adalah tool diagnostik data, BUKAN pintu masuk report.

    Bila permintaan user mengarah ke report / laporan / PPT / deck / analisa
    mingguan-bulanan, JANGAN jadikan hasil tool ini sebagai jawaban akhir.
    Panggil get_report_guide() lebih dulu, lalu tentukan Jalur 1 (user
    menyebut tipe report) atau Jalur 2 (top-down). Ragu = Jalur 2.

    Bila user meminta client brief / presales brief / meeting prep, panggil
    get_intelligence_brief_guide(). Bila user meminta sales deck / pitch deck /
    proposal deck, panggil get_sales_deck_guide().

    Boleh dipakai langsung TANPA guide hanya untuk pertanyaan data ad-hoc yang
    tidak menghasilkan report: cek ketersediaan data, satu angka, atau
    verifikasi cepat.

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
    GATE - TENTUKAN JALUR DULU BILA INI MENGARAH KE REPORT.
    Tool ini adalah tool diagnostik data, BUKAN pintu masuk report.

    Bila permintaan user mengarah ke report / laporan / PPT / deck / analisa
    mingguan-bulanan, JANGAN jadikan hasil tool ini sebagai jawaban akhir.
    Panggil get_report_guide() lebih dulu, lalu tentukan Jalur 1 (user
    menyebut tipe report) atau Jalur 2 (top-down). Ragu = Jalur 2.

    Bila user meminta client brief / presales brief / meeting prep, panggil
    get_intelligence_brief_guide(). Bila user meminta sales deck / pitch deck /
    proposal deck, panggil get_sales_deck_guide().

    Boleh dipakai langsung TANPA guide hanya untuk pertanyaan data ad-hoc yang
    tidak menghasilkan report: cek ketersediaan data, satu angka, atau
    verifikasi cepat.

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
    GATE - TENTUKAN JALUR DULU BILA INI MENGARAH KE REPORT.
    Tool ini adalah tool diagnostik data, BUKAN pintu masuk report.

    Bila permintaan user mengarah ke report / laporan / PPT / deck / analisa
    mingguan-bulanan, JANGAN jadikan hasil tool ini sebagai jawaban akhir.
    Panggil get_report_guide() lebih dulu, lalu tentukan Jalur 1 (user
    menyebut tipe report) atau Jalur 2 (top-down). Ragu = Jalur 2.

    Bila user meminta client brief / presales brief / meeting prep, panggil
    get_intelligence_brief_guide(). Bila user meminta sales deck / pitch deck /
    proposal deck, panggil get_sales_deck_guide().

    Boleh dipakai langsung TANPA guide hanya untuk pertanyaan data ad-hoc yang
    tidak menghasilkan report: cek ketersediaan data, satu angka, atau
    verifikasi cepat.

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
    GATE - TENTUKAN JALUR DULU BILA INI MENGARAH KE REPORT.
    Tool ini adalah tool diagnostik data, BUKAN pintu masuk report.

    Bila permintaan user mengarah ke report / laporan / PPT / deck / analisa
    mingguan-bulanan, JANGAN jadikan hasil tool ini sebagai jawaban akhir.
    Panggil get_report_guide() lebih dulu, lalu tentukan Jalur 1 (user
    menyebut tipe report) atau Jalur 2 (top-down). Ragu = Jalur 2.

    Bila user meminta client brief / presales brief / meeting prep, panggil
    get_intelligence_brief_guide(). Bila user meminta sales deck / pitch deck /
    proposal deck, panggil get_sales_deck_guide().

    Boleh dipakai langsung TANPA guide hanya untuk pertanyaan data ad-hoc yang
    tidak menghasilkan report: cek ketersediaan data, satu angka, atau
    verifikasi cepat.

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
    GATE - TENTUKAN JALUR DULU BILA INI MENGARAH KE REPORT.
    Tool ini adalah tool diagnostik data, BUKAN pintu masuk report.

    Bila permintaan user mengarah ke report / laporan / PPT / deck / analisa
    mingguan-bulanan, JANGAN jadikan hasil tool ini sebagai jawaban akhir.
    Panggil get_report_guide() lebih dulu, lalu tentukan Jalur 1 (user
    menyebut tipe report) atau Jalur 2 (top-down). Ragu = Jalur 2.

    Bila user meminta client brief / presales brief / meeting prep, panggil
    get_intelligence_brief_guide(). Bila user meminta sales deck / pitch deck /
    proposal deck, panggil get_sales_deck_guide().

    Boleh dipakai langsung TANPA guide hanya untuk pertanyaan data ad-hoc yang
    tidak menghasilkan report: cek ketersediaan data, satu angka, atau
    verifikasi cepat.

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




# ---------------------------------------------------------------------
# EVO attribute enrichment MCP tools
# ---------------------------------------------------------------------
@mcp.tool()
def save_evo_attribute_map(
    project_name: str,
    attribute_map_json: str,
    activate: bool = True,
) -> dict[str, Any]:
    """Simpan attribute map EVO client/category untuk dipakai ulang.

    Attribute map harus berisi map_version, map_name, map_source, category,
    dan attributes[]. Map version tidak ditimpa; buat map_id/version baru bila
    definisi berubah.
    """
    try:
        payload = _parse_topic_json(attribute_map_json, "attribute_map_json")
        if not isinstance(payload, dict):
            return {"success": False, "error": "attribute_map_json harus JSON object."}
        from reporting.enrichment.evo_attribute_store import save_attribute_map

        return {
            "success": True,
            "attribute_map": save_attribute_map(
                project_name=project_name or None,
                attribute_map=payload,
                activate=bool(activate),
            ),
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def list_evo_attribute_maps(project_name: str = "") -> dict[str, Any]:
    """Lihat EVO attribute map global/category/client yang tersedia."""
    try:
        from reporting.enrichment.evo_attribute_store import list_attribute_maps

        return {
            "success": True,
            "project_name": project_name or None,
            "attribute_maps": list_attribute_maps(project_name or None),
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def get_evo_attribute_enrichment_status(
    focus_brand: str,
    competitor_brands: str = "",
    map_id: str = "",
    category: str = "",
    start_date: str = "",
    end_date: str = "",
    channels: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
    target_per_brand: int = 0,
) -> dict[str, Any]:
    """Cek population, cache, target sampling, dan shortfall EVO per brand."""
    try:
        from reporting.enrichment.report_enrichment_registry import (
            validate_enrichment_request,
        )
        validate_enrichment_request(
            "evo_perception_intelligence",
            attribute_requested=True,
        )
        from reporting.enrichment.evo_attribute_batch_builder import (
            get_evo_attribute_enrichment_status as _status,
        )
        return _status(
            focus_brand=focus_brand,
            competitor_brands=competitor_brands or None,
            map_id=map_id or None,
            category=category or None,
            start_date=start_date or None,
            end_date=end_date or None,
            channels=channels or None,
            keywords=keywords or None,
            exclude_keywords=exclude_keywords or None,
            match_mode=match_mode,
            target_per_brand=int(target_per_brand) if int(target_per_brand or 0) > 0 else None,
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def get_unclassified_evo_attribute_batch(
    focus_brand: str,
    competitor_brands: str = "",
    map_id: str = "",
    category: str = "",
    start_date: str = "",
    end_date: str = "",
    channels: str = "",
    keywords: str = "",
    exclude_keywords: str = "",
    match_mode: str = "any",
    target_per_brand: int = 0,
    batch_size: int = 100,
) -> dict[str, Any]:
    """Ambil batch EVO baru tanpa mengirim ulang post yang sudah cached.

    Default target adalah 10% per brand, minimum 30, initial cap 100. User dapat
    menaikkan target_per_brand; tiap request AI tetap maksimal 100 post. Batch
    tambahan memperbaiki coverage channel, sentiment, content/source type,
    period, dan engagement tier.
    """
    try:
        from reporting.enrichment.report_enrichment_registry import (
            validate_enrichment_request,
        )
        validate_enrichment_request(
            "evo_perception_intelligence",
            attribute_requested=True,
        )
        from reporting.enrichment.evo_attribute_batch_builder import (
            get_unclassified_evo_attribute_batch as _batch,
        )
        return _batch(
            focus_brand=focus_brand,
            competitor_brands=competitor_brands or None,
            map_id=map_id or None,
            category=category or None,
            start_date=start_date or None,
            end_date=end_date or None,
            channels=channels or None,
            keywords=keywords or None,
            exclude_keywords=exclude_keywords or None,
            match_mode=match_mode,
            target_per_brand=int(target_per_brand) if int(target_per_brand or 0) > 0 else None,
            batch_size=int(batch_size),
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def save_evo_attribute_batch_results(
    batch_id: str,
    results_json: str,
) -> dict[str, Any]:
    """Validasi lengkap dan simpan hasil klasifikasi atribut EVO ke cache."""
    try:
        results = _parse_topic_json(results_json, "results_json")
        if not isinstance(results, list):
            return {"success": False, "error": "results_json harus JSON array."}
        from reporting.enrichment.evo_attribute_batch_builder import (
            submit_evo_attribute_batch_results,
        )
        return submit_evo_attribute_batch_results(
            batch_id=batch_id,
            results=results,
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------
# Shared report enrichment requirements
# ---------------------------------------------------------------------
@mcp.tool()
def get_report_enrichment_plan(report_type_id: str) -> dict[str, Any]:
    """Return the canonical enrichment plan for one report type.

    This is diagnostic and orchestration metadata. Report-specific workflows
    already enforce the same registry automatically:
    - Daily Social: topic only
    - Competitive Analysis: topic only
    - Mainstream Media Report: topic then spokesperson
    - EVO Perception Intelligence: attribute enrichment
    """
    try:
        from reporting.enrichment.report_enrichment_registry import (
            get_report_enrichment_requirements,
        )

        return {
            "success": True,
            "enrichment_requirements": get_report_enrichment_requirements(
                report_type_id
            ),
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------
# Spokesperson enrichment MCP tools
# ---------------------------------------------------------------------
@mcp.tool()
def prepare_spokesperson_enrichment(
    project_name: str,
    start_date: str,
    end_date: str = "",
    report_type_id: str = "mainstream_media_report",
    client_brand: str = "",
    competitors: str = "",
    competitor_brands: str = "",
    llm_batch_size: int = 20,
    include_prompts: bool = True,
) -> dict[str, Any]:
    """Prepare spokesperson enrichment batch for an allowed report type.

    The shared registry currently allows spokesperson enrichment for Mainstream
    Media Report only. Daily Social and Competitive Analysis are topic-only and
    are rejected before any database/LLM work starts.
    The tool checks the spokesperson cache first. If missing articles exist, it
    returns NEEDS_AUTO_SPOKESPERSON_ENRICHMENT plus prompt_batches for Claude.

    Claude must then extract spokespersons from each prompt batch and call
    save_spokesperson_enrichment_response(). After saving, rerun the report
    workflow.
    """
    try:
        from reporting.enrichment.report_enrichment_registry import (
            validate_enrichment_request,
        )

        enrichment_requirements = validate_enrichment_request(
            report_type_id or "mainstream_media_report",
            spokesperson_requested=True,
        )

        from reporting.enrichment.spokesperson_enrichment_workflow import (
            prepare_spokesperson_enrichment_batch as _prepare_spokesperson_batch,
        )

        competitor_list = _clean_csv(competitor_brands or competitors)
        result = _prepare_spokesperson_batch(
            client_brand=client_brand or project_name,
            competitors=competitor_list,
            start_date=start_date,
            end_date=end_date or start_date,
            llm_batch_size=max(1, int(llm_batch_size or 20)),
            include_prompts=bool(include_prompts),
        )
        result.setdefault("enrichment_requirements", enrichment_requirements)
        return result
    except Exception as exc:
        return {
            "success": False,
            "workflow_status": "ERROR",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "instruction": "Pastikan file reporting/enrichment/spokesperson_* sudah ada dan DATABASE_URL aktif.",
        }


@mcp.tool()
def save_spokesperson_enrichment_response(
    results_json: str,
    candidates_json: str = "",
    model_version: str = "claude_spokesperson_extraction_v1",
    overwrite: bool = True,
) -> dict[str, Any]:
    """Validate and save Claude spokesperson extraction results to cache.

    `content_hash` is server-managed. Claude only needs to return
    canonical_post_id plus the extraction result. `candidates_json` remains
    optional for backward compatibility; when omitted, the server hydrates
    candidate metadata and content_hash directly from canonical post IDs.
    """
    try:
        payload = _parse_topic_json(results_json, "results_json")
        if isinstance(payload, list):
            payload = {"results": payload}
        if not isinstance(payload, dict):
            return {"success": False, "error": "results_json harus JSON object atau array."}
        if "results" not in payload and "rows" in payload:
            payload = {"results": payload.get("rows") or []}
        if not isinstance(payload.get("results"), list):
            return {"success": False, "error": "results_json harus punya field results[] atau rows[]."}

        candidates = None
        if candidates_json and str(candidates_json).strip():
            parsed_candidates = _parse_topic_json(candidates_json, "candidates_json")
            if isinstance(parsed_candidates, dict):
                candidates = parsed_candidates.get("candidates") or parsed_candidates.get("rows")
            elif isinstance(parsed_candidates, list):
                candidates = parsed_candidates

        from reporting.enrichment.spokesperson_enrichment_workflow import (
            save_spokesperson_enrichment_batch_response as _save_response,
        )

        result = _save_response(
            payload,
            candidates=candidates,
            model_version=model_version or "claude_spokesperson_extraction_v1",
            overwrite=bool(overwrite),
        )
        if result.get("success"):
            result.setdefault(
                "next_step",
                "Rerun create_mainstream_media_report_workflow with the same scope; the cache should be read immediately.",
            )
        return result
    except Exception as exc:
        return {
            "success": False,
            "workflow_status": "ERROR",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


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

    INTERFACE TINGKAT RENDAH - BUKAN JALUR NORMAL PEMBUATAN REPORT.
    Tool ini melewati guardrail workflow (audience gate, preview gate,
    auto-taxonomy). Untuk permintaan report biasa JANGAN panggil tool ini:
    pakai create_*_report_workflow (Jalur 1) atau get_report_guide (Jalur 2).
    Pakai tool ini hanya untuk debugging/inspeksi Task 1 secara langsung.

    Builder dipilih berdasarkan report_type_id lewat registry + dispatcher.
    Jangan menebak builder mana yang sudah siap: panggil
    check_report_builder_availability() untuk melihat status aktualnya.

    confirmed_intent_id: WAJIB diisi (tidak boleh kosong), namun nilainya
    hanya dipakai sebagai LABEL PENELUSURAN yang ikut disimpan di paket -
    tidak pernah diverifikasi ke catatan Intent Confirmation mana pun.
    Isi dengan id dari Intent Confirmation bila ada; bila tidak, isi label
    deskriptif. Jangan mengarang id yang seolah-olah resmi.
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
def check_report_builder_availability() -> dict[str, Any]:
    """
    Cek builder Task 1 mana yang benar-benar siap dipakai (read-only).

    Tool ini TIDAK mengambil data dan TIDAK membuat report. Gunakan untuk
    memastikan status builder secara faktual, bukan menebak dari deskripsi
    tool. Status: READY, NOT_IMPLEMENTED, atau ROUTE_MISSING.
    """
    try:
        from reporting.task1.report_input_dispatcher import (
            builder_availability as _availability,
        )

        rows = _availability()
        return {
            "success": True,
            "ready": [r["report_type_id"] for r in rows if r["status"] == "READY"],
            "not_ready": [
                {"report_type_id": r["report_type_id"], "status": r["status"],
                 "reason": r["reason"]}
                for r in rows if r["status"] != "READY"
            ],
            "detail": rows,
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
    """Builder Daily Social Report (Jalur 1 — bottom-up).

    JALUR 1 — BOTTOM-UP. Panggil HANYA bila user MENYEBUT tipe report ini
    secara eksplisit (contoh: "bikin daily report", "daily social report Gojek 8 Mei").

    Bila user TIDAK menyebut tipe report — hanya bilang "report", "laporan",
    "PPT", "deck", atau memberi pertanyaan seperti "ada topik apa minggu ini",
    "apa yang terjadi pada brand A" — JANGAN panggil tool ini.
    Panggil get_report_guide() dan jalankan JALUR 2 (top-down).

    Ragu apakah user menyebut tipenya? Berarti TIDAK menyebut. Jalur 2.

    Alur Jalur 1 sudah pakem: workflow -> Task 1 preview -> konfirmasi user
    -> Task 2 -> PPT. Jangan campur dengan Intent Confirmation 8 poin milik
    Jalur 2, dan jangan merakit slide manual.

    Bila tipenya memang disebut eksplisit: kalau audience/reader tidak
    disebutkan, tool ini mengembalikan NEEDS_AUDIENCE dan asisten wajib
    menanyakan report ini untuk siapa.

    Enrichment policy: Daily Social is topic-only; never call spokesperson enrichment.

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
    issue_min_articles: int = 50,
    issue_max_articles: int = 100,
    taxonomy_sample_size: int = 30,
    force_skip_auto_issue: bool = False,
    auto_spokesperson_enabled: bool = True,
    spokesperson_llm_batch_size: int = 20,
    force_skip_auto_spokesperson: bool = False,
) -> dict[str, Any]:
    """Builder Mainstream Media Report / MMR (Jalur 1 — bottom-up).

    JALUR 1 — BOTTOM-UP. Panggil HANYA bila user MENYEBUT tipe report ini
    secara eksplisit (contoh: "bikin MMR", "mainstream media report Aqua").

    Bila user TIDAK menyebut tipe report — hanya bilang "report", "laporan",
    "PPT", "deck", atau memberi pertanyaan seperti "ada topik apa minggu ini",
    "apa yang terjadi pada brand A" — JANGAN panggil tool ini.
    Panggil get_report_guide() dan jalankan JALUR 2 (top-down).

    Ragu apakah user menyebut tipenya? Berarti TIDAK menyebut. Jalur 2.

    Alur Jalur 1 sudah pakem: workflow -> Task 1 preview -> konfirmasi user
    -> Task 2 -> PPT. Jangan campur dengan Intent Confirmation 8 poin milik
    Jalur 2, dan jangan merakit slide manual.

    Bila tipenya memang disebut eksplisit: kalau audience/reader tidak
    disebutkan, tool ini mengembalikan NEEDS_AUDIENCE dan asisten wajib
    menanyakan report ini untuk siapa.

    After audience is known, the workflow uses full canonical mainstream data
    for KPI, sentiment, media contributors, and article evidence. For issue
    analysis, it uses existing cache/taxonomy or auto-plans a lightweight smart
    sample by default: 10% of issue-eligible articles, minimum 50, maximum 100.
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
            auto_spokesperson_enabled=bool(auto_spokesperson_enabled),
            spokesperson_llm_batch_size=max(1, int(spokesperson_llm_batch_size or 20)),
            force_skip_auto_spokesperson=bool(force_skip_auto_spokesperson),
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
    """Builder Competitive Analysis (Jalur 1 — bottom-up).

    JALUR 1 — BOTTOM-UP. Panggil HANYA bila user MENYEBUT tipe report ini
    secara eksplisit (contoh: "bikin competitive analysis", "CA Le Minerale vs Aqua").

    Bila user TIDAK menyebut tipe report — hanya bilang "report", "laporan",
    "PPT", "deck", atau memberi pertanyaan seperti "ada topik apa minggu ini",
    "apa yang terjadi pada brand A" — JANGAN panggil tool ini.
    Panggil get_report_guide() dan jalankan JALUR 2 (top-down).

    Ragu apakah user menyebut tipenya? Berarti TIDAK menyebut. Jalur 2.

    Alur Jalur 1 sudah pakem: workflow -> Task 1 preview -> konfirmasi user
    -> Task 2 -> PPT. Jangan campur dengan Intent Confirmation 8 poin milik
    Jalur 2, dan jangan merakit slide manual.

    Bila tipenya memang disebut eksplisit: kalau audience atau daftar
    kompetitor belum ada, tool ini mengembalikan NEEDS_AUDIENCE atau
    NEEDS_COMPETITORS.
    If competitive topic/narrative taxonomy/classification is missing, this
    returns NEEDS_AUTO_COMPETITIVE_TAXONOMY or NEEDS_AUTO_COMPETITIVE_TOPIC_CLASSIFICATION.

    Enrichment policy: Competitive Analysis is topic-only; never call spokesperson enrichment.

    Topic policy: final CA topic/narrative metrics use cached LLM assignments
    from Title + Content. Raw Topic Extraction, legacy Aspect, and Entity
    Extraction are diagnostic only, not core source of truth.

    Main slide URL policy: use clickable labels such as "Buka post" / "Lihat post"
    linked to source_url. Evidence IDs and full URLs belong in Appendix/Data Pack.
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
                "Management, CEO/Board, Marketing/Brand, Marketing/Content, PR/Corcom, atau Insight Team. "
                "Kalau user jawab 'gak tau', pakai default Marketing/Brand Team."
            ),
            "instruction_to_assistant": (
                "Ask the user who the report is for once. Do not build PPTX yet. "
                "If user replies 'gak tau/terserah/umum', use default Marketing/Brand Team. "
                "After audience is provided/defaulted, call create_competitive_analysis_report_workflow first to show data preview."
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
INTELLIGENCE_BRIEF_DIR = SKILLS_DIR / "intelligence-brief-generator"
SALES_DECK_DIR = SKILLS_DIR / "salesdeck-generator"
ONBOARDING_DIR = SKILLS_DIR / "onboarding-generator"

_SALES_DECK_FILES = [
    ("SKILL.md — router dan usage guide", "SKILL.md"),
    ("system-prompt.md — execution engine", "references/system-prompt.md"),
    ("consistency_contract.md — invariant claims, evidence, and design contract", "references/consistency_contract.md"),
    ("quality_framework.md — hard gates and QA", "references/quality_framework.md"),
    ("qa-and-change-rules.md — final QA and revision rules", "references/qa-and-change-rules.md"),
    ("content-contract-schema.json — content output schema", "references/content-contract-schema.json"),
    ("user-prompt-template.md — sales deck intake template", "references/user-prompt-template.md"),
    ("skill_mapping.yaml — trigger and routing map", "skill_mapping.yaml"),
    ("knowledge-base/00-INDEX.md — knowledge base index", "references/knowledge-base/00-INDEX.md"),
    ("knowledge-base/product-capability.md — approved Sonar capabilities", "references/knowledge-base/product-capability.md"),
    ("knowledge-base/pricing.md — approved pricing boundaries", "references/knowledge-base/pricing.md"),
    ("knowledge-base/competitors.md — approved competitor framing", "references/knowledge-base/competitors.md"),
    ("knowledge-base/tone-and-writing.md — writing voice", "references/knowledge-base/tone-and-writing.md"),
    ("knowledge-base/deck-structure-guidance.md — deck structure guidance", "references/knowledge-base/deck-structure-guidance.md"),
    ("brand-kit/README.md — brand kit index", "references/brand-kit/README.md"),
    ("brand-kit/01_BRAND_SYSTEM.md — design tokens", "references/brand-kit/01_BRAND_SYSTEM.md"),
    ("brand-kit/03_SLIDE_LIBRARY.md — slide archetypes", "references/brand-kit/03_SLIDE_LIBRARY.md"),
]

_INTELLIGENCE_BRIEF_FILES = [
    ("SKILL.md — router dan usage guide", "SKILL.md"),
    ("system_prompt.md — execution engine", "references/system_prompt.md"),
    ("consistency_contract.md — invariant schema and evidence tags", "references/consistency_contract.md"),
    ("quality_framework.md — quality gate", "references/quality_framework.md"),
    ("user_prompt_template.md — intake template", "references/user_prompt_template.md"),
    ("skill_mapping.yaml — trigger and mapping", "skill_mapping.yaml"),
]

_ONBOARDING_FILES = [
    ("SKILL.md — router dan usage guide", "SKILL.md"),
    ("system_prompt.md — execution engine (5 output berantai)", "references/system_prompt.md"),
    ("consistency_contract.md — invariant build-chain dan format lock", "references/consistency_contract.md"),
    ("quality_framework.md — quality gate A/B/C", "references/quality_framework.md"),
    ("user_prompt_template.md — intake template", "references/user_prompt_template.md"),
    ("skill_mapping.yaml — trigger and mapping", "skill_mapping.yaml"),
]

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



# --- Teammate report MCP tool registrations: Industry Trend / BCE / SFIR ---
# These report-specific tools are registered directly so MCP can expose them
# without replacing the shared Daily/MMR/CA workflows and renderers.

from reporting.task2.workflows.industry_trend_report_workflow import create_industry_trend_report_workflow
from reporting.task2.workflows.bce_report_workflow import create_bce_report_workflow
from reporting.task2.workflows.sfir_report_workflow import create_sfir_report_workflow

from reporting.task2.renderers.industry_trend_report_renderer import (
    build_industry_trend_report_data_preview,
    build_industry_trend_report_package,
)
from reporting.task2.renderers.bce_report_renderer import (
    build_bce_report_data_preview,
    build_bce_report_package,
)
from reporting.task2.renderers.sfir_report_renderer import (
    build_sfir_report_data_preview,
    build_sfir_report_package,
)


# =====================================================================
# EVO — Perception Intelligence Report (Jalur 1)
# Status: ACTIVE. Builder Task 1/2, registry routing, dan enrichment atribut
# tersedia. Availability guard tetap dipertahankan untuk kegagalan import.
# Pola meniru: create_competitive_analysis_report_workflow,
# build_bce_report_ppt_package, prepare_spokesperson_enrichment.
# =====================================================================

# Seed attribute map (18 atribut) dari evo_attribute_map.md - dipakai sebagai
# default bila klien tidak punya map sendiri. Report menandai "evo_seed".
_EVO_SEED_ATTRIBUTES = [
    # Experience
    {"attribute_id": "ATTR_EXP_RELIABILITY", "attribute": "Reliability / Performance", "driver": "Experience"},
    {"attribute_id": "ATTR_EXP_RESPONSIVENESS", "attribute": "Responsiveness / Care", "driver": "Experience"},
    {"attribute_id": "ATTR_EXP_EASE", "attribute": "Ease / Usability", "driver": "Experience"},
    {"attribute_id": "ATTR_EXP_ENTERTAINMENT", "attribute": "Entertainment / Delight", "driver": "Experience"},
    {"attribute_id": "ATTR_EXP_PARTICIPATION", "attribute": "Participation / Co-creation", "driver": "Experience"},
    {"attribute_id": "ATTR_EXP_INNOVATION", "attribute": "Innovation / Modernity", "driver": "Experience"},
    # Values
    {"attribute_id": "ATTR_VAL_ACCOUNTABILITY", "attribute": "Accountability / Honesty", "driver": "Values"},
    {"attribute_id": "ATTR_VAL_LOCALPRIDE", "attribute": "Local Pride / Cultural Legitimacy", "driver": "Values"},
    {"attribute_id": "ATTR_VAL_SUSTAINABILITY", "attribute": "Sustainability / Responsibility", "driver": "Values"},
    {"attribute_id": "ATTR_VAL_EMPOWERMENT", "attribute": "Empowerment / Inclusion", "driver": "Values"},
    {"attribute_id": "ATTR_VAL_COLLABORATION", "attribute": "Collaboration / Partnership", "driver": "Values"},
    {"attribute_id": "ATTR_VAL_SAFETY", "attribute": "Safety / Security / Trust", "driver": "Values"},
    # Offer
    {"attribute_id": "ATTR_OFF_AFFORDABILITY", "attribute": "Affordability / Value-for-money", "driver": "Offer"},
    {"attribute_id": "ATTR_OFF_INCENTIVE", "attribute": "Incentive / Reward", "driver": "Offer"},
    {"attribute_id": "ATTR_OFF_ACCESS", "attribute": "Access / Availability", "driver": "Offer"},
    {"attribute_id": "ATTR_OFF_PACKAGE", "attribute": "Package / Product Design", "driver": "Offer"},
    {"attribute_id": "ATTR_OFF_CLARITY", "attribute": "Offer Clarity", "driver": "Offer"},
    {"attribute_id": "ATTR_OFF_CHOICE", "attribute": "Choice / Flexibility", "driver": "Offer"},
]

# Sampling EVO — dikunci sesuai pola spokesperson/topic (keputusan desain):
#   10% per brand, minimum 50, maksimum 100 per proses (sisanya batch),
#   urutan prioritas: engagement desc -> negative sentiment -> newest,
#   dedup canonical, cache reuse, low-confidence flag untuk brand kecil.
_EVO_SAMPLING_POLICY = {
    "ratio": 0.10,
    "min_per_brand": 50,
    "max_per_request": 100,
    "priority_order": ["engagement_desc", "negative_sentiment", "newest"],
    "dedup": "canonical_post_id",
    "cache_key": "project + canonical_post_id + content_hash + attribute_map_version",
    "small_brand_flag": "low-confidence",
}

_EVO_NOT_READY = (
    "EVO Perception Intelligence tidak tersedia karena modul implementasi gagal "
    "dimuat. Periksa instalasi dependensi dan log import server."
)


def _evo_builder_available() -> bool:
    """True hanya jika builder Task 1 EVO benar-benar bisa diimpor."""
    try:
        import importlib
        importlib.import_module("reporting.task1.builders.evo_perception_intelligence")
        return True
    except Exception:
        return False


@mcp.tool()
def create_evo_perception_intelligence_report_workflow(
    project_name: str,
    start_date: str,
    end_date: str,
    focus_brand: str = "",
    competitor_brands: str = "",
    primary_reader: str = "",
    desired_perception: str = "",
    attribute_map_source: str = "auto",
    keywords: str = "",
    exclude_keywords: str = "",
    channels: str = "",
    match_mode: str = "any",
    analysis_objective: str = "",
    confirmed_intent_id: str = "",
    confirm_single_brand_fallback: bool = False,
) -> dict[str, Any]:
    """Builder EVO Perception Intelligence Report (Jalur 1 - bottom-up).

    JALUR 1 - BOTTOM-UP. Panggil HANYA bila user MENYEBUT tipe report ini
    secara eksplisit (contoh: "bikin EVO report", "perception intelligence
    brand X", "EVO Le Minerale vs Aqua"). Bila user tidak menyebut tipe report,
    jangan panggil tool ini: panggil get_report_guide() dan jalankan Jalur 2.

    EVO berlaku untuk KLIEN MANA SAJA. focus_brand dan competitor_brands diisi
    saat report dibuat; tidak ada brand yang di-hardcode.

    EVO memakai attribute enrichment: pelabelan persepsi per post oleh Claude,
    cache terverifikasi, lalu Task 1 membekukan metric sebelum Task 2.

    Guardrail (mirror pola BCE/CA):
    - primary_reader kosong -> NEEDS_AUDIENCE, berhenti.
    - competitor_brands kosong -> NEEDS_BENCHMARK (khusus EVO). EVO menghitung
      Best Brand, Attribute Gap, dan Whitespace yang butuh pembanding. Fallback
      single-brand hanya bila caller mengonfirmasi eksplisit lewat
      confirm_single_brand_fallback=True (competitive_analysis: unavailable).
    - attribute_map_source default "auto": category -> evo_seed fallback.

    Sampling atribut mengikuti pakem Cogan (sama seperti spokesperson/topic):
    10% per brand, min 50, max 100 per proses, prioritas engagement lalu
    sentimen negatif lalu terbaru, dedup canonical, hasil di-cache dan bisa
    ditambah via batch. Nilai atribut ditentukan Claude, bukan kode.
    """
    clean_reader = " ".join(str(primary_reader or "").split())
    clean_competitors = _clean_csv(competitor_brands)

    # Gate 1: audience (sama seperti workflow lain)
    if not clean_reader:
        return {
            "success": False,
            "workflow_status": "NEEDS_AUDIENCE",
            "clarification_question": (
                "Report EVO ini dibuat untuk pembaca siapa? (mis. PR/Corcom, "
                "Insight, Management, CEO/Board, Marketing, Brand Team)."
            ),
            "instruction_to_assistant": (
                "Ask the user who the report is for. Do not proceed until "
                "primary_reader is provided."
            ),
        }

    # Gate 2: benchmark (khusus EVO)
    if not clean_competitors and not bool(confirm_single_brand_fallback):
        return {
            "success": False,
            "workflow_status": "NEEDS_BENCHMARK",
            "clarification_question": (
                "EVO membandingkan persepsi antar-brand (Best Brand, Attribute "
                "Gap, Whitespace). Sebutkan minimal satu competitor_brands. "
                "Atau konfirmasi menjalankan diagnosis satu-brand saja "
                "(competitive_analysis akan ditandai unavailable)."
            ),
            "instruction_to_assistant": (
                "EVO needs at least one competitor to run comparative diagnosis. "
                "Ask for competitor_brands. Only if the user explicitly wants a "
                "single-brand run, re-call this tool with "
                "confirm_single_brand_fallback=True."
            ),
        }

    # Gate 3: builder availability
    if not _evo_builder_available():
        return {
            "success": False,
            "workflow_status": "NOT_IMPLEMENTED",
            "report_type_id": "evo_perception_intelligence",
            "message": _EVO_NOT_READY,
            "sampling_policy": _EVO_SAMPLING_POLICY,
            "attribute_map_default": "evo_seed",
        }

    try:
        from reporting.task2.workflows.evo_perception_intelligence_report_workflow import (
            create_evo_perception_intelligence_report_workflow as _workflow,
        )

        return _workflow(
            project_name=project_name,
            start_date=start_date,
            end_date=end_date or None,
            focus_brand=focus_brand or project_name,
            competitor_brands=clean_competitors,
            primary_reader=clean_reader,
            desired_perception=desired_perception or None,
            attribute_map_source=attribute_map_source or "auto",
            keywords=keywords or None,
            exclude_keywords=exclude_keywords or None,
            channels=_clean_csv(channels) or None,
            match_mode=match_mode or "any",
            analysis_objective=analysis_objective or None,
            confirmed_intent_id=confirmed_intent_id or None,
            confirm_single_brand_fallback=bool(confirm_single_brand_fallback),
        )
    except Exception as exc:
        return {"success": False, "workflow_status": "ERROR", "error": str(exc)}


@mcp.tool()
def build_evo_perception_intelligence_report_data_preview(
    report_input_id: str,
    allow_partial: bool = True,
) -> dict[str, Any]:
    """Preview Task 1 EVO sebelum PPT dibuat (mirror build_prepared_report_outline).

    Selain scope + data health seperti report lain, preview EVO menampilkan
    lapisan atribut: attribute map yang dipakai, audit klasifikasi, Attribute
    Gap awal, tahap journey, dan kelengkapan komponen.
    """
    if not _evo_builder_available():
        return {
            "success": False,
            "workflow_status": "NOT_IMPLEMENTED",
            "message": _EVO_NOT_READY,
        }
    try:
        from reporting.task1.builders.evo_perception_intelligence import (
            build_evo_data_preview as _preview,
        )

        return {
            "success": True,
            "preview": _preview(report_input_id, allow_partial=bool(allow_partial)),
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def build_evo_perception_intelligence_report_ppt_package(
    report_input_id: str,
    audience: str = "",
    report_pov: str = "",
    preview_confirmed: bool = False,
) -> dict[str, Any]:
    """Build a PPT-ready EVO package only after audience + preview confirmation.

    Guardrail identik dengan BCE/SFIR/IT plus G14 (client-facing language
    integrity) yang memindai teks slide dari jargon internal sebelum file
    dikembalikan.
    """
    clean_audience = " ".join(str(audience or "").split())
    clean_pov = " ".join(str(report_pov or "").split())
    if not clean_audience and not clean_pov:
        return {
            "success": False,
            "workflow_status": "NEEDS_AUDIENCE",
            "clarification_question": (
                "Report EVO ini dibuat untuk siapa? Pilih salah satu: PR/Corcom, "
                "Insight, Management, CEO/Board, Marketing, atau Brand Team."
            ),
            "instruction_to_assistant": (
                "Ask the user who the report is for. Do not build PPTX yet."
            ),
        }
    if not bool(preview_confirmed):
        return {
            "success": False,
            "workflow_status": "NEEDS_PREVIEW_CONFIRMATION",
            "report_input_id": report_input_id,
            "instruction_to_assistant": (
                "Show Task 1 data preview first using "
                "build_evo_perception_intelligence_report_data_preview(report_input_id). "
                "Then ask the user whether to continue to PPTX. Call again with "
                "preview_confirmed=True only after the user confirms."
            ),
        }
    if not _evo_builder_available():
        return {
            "success": False,
            "workflow_status": "NOT_IMPLEMENTED",
            "message": _EVO_NOT_READY,
        }
    try:
        from reporting.task1.builders.evo_perception_intelligence import (
            build_evo_report_package as _build,
        )

        return _build(
            report_input_id=report_input_id,
            audience_context=clean_audience,
            audience_pov=clean_pov,
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# --- JALUR 1 GATE untuk 3 workflow eksternal ---
#
# Industry Trend / BCE / SFIR didefinisikan di reporting/task2/workflows/,
# tapi FastMCP membaca __doc__ SAAT REGISTRASI. Jadi gate bisa dipasang dari
# sini tanpa menyentuh modul reporting/ sama sekali.
#
# KENAPA GATE HARUS ADA DI DOCSTRING, BUKAN CUMA DI SKILL:
# Docstring tool SELALU menempel di context sejak awal percakapan. Isi
# skill_report.md baru masuk kalau get_report_guide() dipanggil. Kalau aturan
# Jalur 1 / Jalur 2 hanya ditaruh di skill, dia kalah melawan enam tool yang
# selalu terlihat. Itulah sebab Jalur 2 kalah selama ini. Aturan harus ada di
# DUA tempat: docstring (di sini) dan skill (sebagai penguat).

_JALUR0_CLIENT_BRIEF_GATE = """
    JALUR 0 - CLIENT / INTELLIGENCE BRIEF. Panggil bila user meminta client brief,
    presales brief, account brief, meeting prep, BD cheat-sheet, intelligence brief,
    intel brief, intellifence brief, brief klien, brief calon klien, atau meminta
    merapikan raw context dari chat, WhatsApp/WA, email, call note, meeting note,
    CRM/SCS handover, atau RFP menjadi brief.

    Untuk Jalur 0: panggil get_intelligence_brief_guide(). Jangan panggil
    get_report_guide(), jangan panggil create_*_report_workflow, dan jangan scan
    data Cogan kecuali user eksplisit meminta validasi data.

    Output Jalur 0 adalah Client Intelligence Brief / Presales Brief. Setelah brief
    selesai di chat, tanya konfirmasi apakah user mau file DOCX/Google Docs, PDF,
    Markdown+JSON, atau cukup di chat. Jangan membuat file sebelum user memilih.
"""

_JALUR0_SALES_DECK_GATE = """
    JALUR 0B - SALES DECK / PITCH DECK. Panggil bila user meminta sales deck,
    pitch deck, proposal deck, deck proposal, deck jualan, sales presentation,
    commercial deck, client presentation, PPTX proposal, final production PPTX,
    atau deck dari client/intelligence/presales brief.

    Untuk Jalur 0B: panggil get_sales_deck_guide(). Jangan panggil
    get_report_guide(), jangan panggil create_*_report_workflow, dan jangan scan
    data Cogan kecuali user eksplisit meminta validasi data/evidence lookup.

    Preferred input adalah Client Intelligence Brief / Presales Brief / Account Brief.
    Jika user hanya memberi raw sales context, kumpulkan field material yang hilang
    atau bentuk sales-deck intake ringan. Jangan klaim ada client brief final bila
    belum ada.

    Default output adalah CONTENT_DRAFT. Buat PPTX/final production hanya bila user
    eksplisit meminta PPTX/final production atau konten sudah disetujui dan content
    gate tidak BLOCKED.
"""

_JALUR1_GATE = """
    JALUR 1 - BOTTOM-UP. Panggil HANYA bila user MENYEBUT tipe report ini
    secara eksplisit (contoh: {contoh}).

    Jika user meminta sales deck / pitch deck / proposal deck / deck jualan /
    commercial deck / client presentation / PPTX proposal, JANGAN panggil tool
    Jalur 1 ini. Panggil get_sales_deck_guide().

    Jika user meminta client brief / presales brief / account brief / meeting prep /
    BD cheat-sheet / intelligence brief / brief dari chat, WA, email, CRM, RFP,
    JANGAN panggil tool Jalur 1 ini. Panggil get_intelligence_brief_guide().

    Bila user TIDAK menyebut tipe report - hanya bilang "report", "laporan",
    "PPT", "deck", atau memberi pertanyaan seperti "ada topik apa minggu ini",
    "apa yang terjadi pada brand A" - JANGAN panggil tool ini.
    Panggil get_report_guide() dan jalankan JALUR 2 (top-down).

    Ragu apakah user menyebut tipenya? Berarti TIDAK menyebut. Jalur 2.

    Alur Jalur 1 sudah pakem: workflow -> Task 1 preview -> konfirmasi user
    -> Task 2 -> PPT. Jangan campur dengan Intent Confirmation 8 poin milik
    Jalur 2, dan jangan merakit slide manual.
"""

# Kalimat yang menarik model menjadikan Jalur 1 sebagai default. Harus DIBUANG
# dari docstring asli, bukan sekadar ditimpa - kalau tidak, model melihat gate
# Jalur 1 DAN "Preferred tool - use this FIRST" di deskripsi yang SAMA, lalu
# memilih yang lebih menggoda.
_BOTTOM_UP_PULL = (
    "preferred tool",
    "use this first",
    "use this when the user asks naturally",
    "call this first",
)


def _strip_bottom_up_pull(doc: str) -> str:
    """Buang baris yang menjadikan tool ini terlihat sebagai pintu default."""
    kept = []
    for line in (doc or "").splitlines():
        if any(phrase in line.strip().lower() for phrase in _BOTTOM_UP_PULL):
            continue
        kept.append(line)
    return "\n".join(kept).strip()


def _apply_jalur1_gate(func, nama: str, contoh: str):
    """
    Pasang gate Jalur 1 di depan docstring asli, sebelum registrasi MCP.

    FastMCP membaca func.__doc__ pada saat mcp.tool()(func) dipanggil, jadi
    override di sini cukup - modul reporting/ tidak perlu disentuh.
    """
    original = _strip_bottom_up_pull(func.__doc__ or "")
    func.__doc__ = (
        f"Builder {nama} (Jalur 1 - bottom-up).\n"
        + _JALUR1_GATE.format(contoh=contoh)
        + ("\n" + original if original else "")
    )
    return func


_apply_jalur1_gate(
    create_industry_trend_report_workflow,
    "Industry Trend Report",
    '"bikin industry trend report", "laporan tren industri AMDK"',
)
_apply_jalur1_gate(
    create_bce_report_workflow,
    "Brand & Content Effectiveness Report",
    '"bikin BCE report", "brand content effectiveness Gojek"',
)
_apply_jalur1_gate(
    create_sfir_report_workflow,
    "Spokesperson Intelligence Report",
    '"bikin SFIR", "spokesperson report", "laporan juru bicara"',
)


# ---------------------------------------------------------------------
# Bocor 5: gate wrapper untuk BCE / SFIR / Industry Trend
# Pola identik dengan build_daily_social_report_ppt_package.
# Renderer (build_*_report_package) menjadi internal, dipanggil setelah gate lolos.
# ---------------------------------------------------------------------


def build_bce_report_ppt_package(
    report_input_id: str,
    audience: str = "",
    report_pov: str = "",
    preview_confirmed: bool = False,
) -> dict[str, Any]:
    """Build a PPT-ready BCE package only after audience + preview confirmation.

    Guardrail identik dengan Daily/CA/MMR: tanpa audience atau tanpa preview,
    tool mengembalikan status actionable, bukan paket PPT.
    """
    clean_audience = " ".join(str(audience or "").split())
    clean_pov = " ".join(str(report_pov or "").split())
    if not clean_audience and not clean_pov:
        return {
            "success": False,
            "workflow_status": "NEEDS_AUDIENCE",
            "clarification_question": (
                "Report BCE ini dibuat untuk siapa? Pilih salah satu: "
                "PR/Corcom, Insight, Management, CEO/Board, Marketing, atau Brand Team."
            ),
            "instruction_to_assistant": (
                "Ask the user who the report is for. Do not build PPTX yet. "
                "After audience is provided, call create_bce_report_workflow first to show data preview."
            ),
        }
    if not bool(preview_confirmed):
        return {
            "success": False,
            "workflow_status": "NEEDS_PREVIEW_CONFIRMATION",
            "report_input_id": report_input_id,
            "instruction_to_assistant": (
                "Show Task 1 data preview first using build_bce_report_data_preview(report_input_id). "
                "Then ask the user whether to continue to PPTX. "
                "Call this tool again with preview_confirmed=True only after the user confirms."
            ),
        }
    try:
        return build_bce_report_package(
            report_input_id=report_input_id,
            audience_context=clean_audience,
            audience_pov=clean_pov,
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def build_sfir_report_ppt_package(
    report_input_id: str,
    audience: str = "",
    report_pov: str = "",
    preview_confirmed: bool = False,
) -> dict[str, Any]:
    """Build a PPT-ready SFIR (spokesperson) package only after audience + preview confirmation.

    Guardrail identik dengan Daily/CA/MMR: tanpa audience atau tanpa preview,
    tool mengembalikan status actionable, bukan paket PPT.
    """
    clean_audience = " ".join(str(audience or "").split())
    clean_pov = " ".join(str(report_pov or "").split())
    if not clean_audience and not clean_pov:
        return {
            "success": False,
            "workflow_status": "NEEDS_AUDIENCE",
            "clarification_question": (
                "Report SFIR (spokesperson) ini dibuat untuk siapa? Pilih salah satu: "
                "PR/Corcom, Insight, Management, CEO/Board, Marketing, atau Brand Team."
            ),
            "instruction_to_assistant": (
                "Ask the user who the report is for. Do not build PPTX yet. "
                "After audience is provided, call create_sfir_report_workflow first to show data preview."
            ),
        }
    if not bool(preview_confirmed):
        return {
            "success": False,
            "workflow_status": "NEEDS_PREVIEW_CONFIRMATION",
            "report_input_id": report_input_id,
            "instruction_to_assistant": (
                "Show Task 1 data preview first using build_sfir_report_data_preview(report_input_id). "
                "Then ask the user whether to continue to PPTX. "
                "Call this tool again with preview_confirmed=True only after the user confirms."
            ),
        }
    try:
        return build_sfir_report_package(
            report_input_id=report_input_id,
            audience_context=clean_audience,
            audience_pov=clean_pov,
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def build_industry_trend_report_ppt_package(
    report_input_id: str,
    audience: str = "",
    report_pov: str = "",
    preview_confirmed: bool = False,
) -> dict[str, Any]:
    """Build a PPT-ready Industry Trend package only after audience + preview confirmation.

    Guardrail identik dengan Daily/CA/MMR: tanpa audience atau tanpa preview,
    tool mengembalikan status actionable, bukan paket PPT.
    """
    clean_audience = " ".join(str(audience or "").split())
    clean_pov = " ".join(str(report_pov or "").split())
    if not clean_audience and not clean_pov:
        return {
            "success": False,
            "workflow_status": "NEEDS_AUDIENCE",
            "clarification_question": (
                "Report Industry Trend ini dibuat untuk siapa? Pilih salah satu: "
                "PR/Corcom, Insight, Management, CEO/Board, Marketing, atau Brand Team."
            ),
            "instruction_to_assistant": (
                "Ask the user who the report is for. Do not build PPTX yet. "
                "After audience is provided, call create_industry_trend_report_workflow first to show data preview."
            ),
        }
    if not bool(preview_confirmed):
        return {
            "success": False,
            "workflow_status": "NEEDS_PREVIEW_CONFIRMATION",
            "report_input_id": report_input_id,
            "instruction_to_assistant": (
                "Show Task 1 data preview first using build_industry_trend_report_data_preview(report_input_id). "
                "Then ask the user whether to continue to PPTX. "
                "Call this tool again with preview_confirmed=True only after the user confirms."
            ),
        }
    try:
        return build_industry_trend_report_package(
            report_input_id=report_input_id,
            audience_context=clean_audience,
            audience_pov=clean_pov,
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}

mcp.tool()(create_industry_trend_report_workflow)
mcp.tool()(build_industry_trend_report_data_preview)
mcp.tool()(build_industry_trend_report_ppt_package)   # gated wrapper (bukan renderer mentah)

mcp.tool()(create_bce_report_workflow)
mcp.tool()(build_bce_report_data_preview)
mcp.tool()(build_bce_report_ppt_package)              # gated wrapper

mcp.tool()(create_sfir_report_workflow)
mcp.tool()(build_sfir_report_data_preview)
mcp.tool()(build_sfir_report_ppt_package)             # gated wrapper

mcp.tool()(build_evo_perception_intelligence_report_ppt_package)  # gated wrapper (EVO)


@mcp.tool()
def get_intelligence_brief_guide() -> str:
    """
    JALUR 0 — Client / Intelligence Brief / Presales Brief.

    Panggil tool ini bila user meminta client brief, presales brief, account brief,
    meeting prep, BD cheat-sheet, intelligence brief, intel brief, intellifence brief,
    brief klien, brief calon klien, atau ingin mengubah chat/WhatsApp/WA/email/call
    note/meeting note/CRM/SCS/RFP menjadi brief.

    Jangan panggil get_report_guide() untuk request ini. Jangan panggil workflow
    report. Jangan scan data Cogan kecuali user eksplisit meminta validasi data.

    BATAS DENGAN JALUR 0C (ONBOARDING). Tool ini untuk tahap SEBELUM closing -
    calon klien, presales, meeting prep. Bila deal SUDAH ditandatangani dan yang
    diminta adalah project brief / configuration package / keyword package /
    handover / kickoff / welcome summary untuk menyiapkan klien mulai berjalan,
    itu Jalur 0C: panggil get_onboarding_guide(). Bila status deal tidak jelas,
    tanya dulu apakah kontraknya sudah closing.

    Setelah brief selesai di chat, tanya user apakah ingin dibuat sebagai
    DOCX/Google Docs, PDF, Markdown+JSON, atau cukup di chat. Jangan membuat file
    sebelum user memilih format.
    """
    header = (
        "# COGAN JALUR 0 — CLIENT / INTELLIGENCE BRIEF\n"
        "# Gunakan untuk client brief, presales brief, account brief, meeting prep, "
        "BD cheat-sheet, intelligence brief, intel brief, intellifence brief, "
        "brief klien, brief calon klien, atau brief dari chat/WA/email/RFP/CRM.\n"
        "# Jangan panggil report workflow dan jangan scan data Cogan kecuali user "
        "meminta validasi data secara eksplisit.\n"
        "# Setelah output brief selesai di chat, tanyakan format file: DOCX/Google Docs, "
        "PDF, Markdown+JSON, atau chat only. Jangan auto-generate file.\n"
        "# Default vendor/offering jika user tidak memberi konteks: Dataxet/Sonar/Cogan "
        "media intelligence, social listening, mainstream monitoring, competitive "
        "intelligence, reputation intelligence, campaign monitoring, anomaly detection, "
        "spokesperson/media analysis, dashboard/reporting, and insight/report generation.\n"
    )

    parts = [header]
    missing: list[str] = []

    for title, relative_path in _INTELLIGENCE_BRIEF_FILES:
        path = INTELLIGENCE_BRIEF_DIR / relative_path
        if path.exists():
            body = path.read_text(encoding="utf-8-sig")
            parts.append(f"\n\n{'=' * 72}\n### {title}\n{'=' * 72}\n\n{body}")
        else:
            missing.append(relative_path)

    if missing:
        parts.append(
            "\n\n[PERINGATAN] File intelligence brief belum ditemukan: "
            + ", ".join(missing)
            + ". Pastikan folder skills/intelligence-brief-generator sudah terpasang."
        )

    return "".join(parts)


@mcp.tool()
def get_sales_deck_guide() -> str:
    """
    JALUR 0B — Sales Deck / Pitch Deck / Proposal Deck.

    Panggil tool ini bila user meminta sales deck, pitch deck, proposal deck,
    deck proposal, deck jualan, sales presentation, commercial deck, client
    presentation, PPTX proposal, final production PPTX, atau deck dari client
    brief / intelligence brief / presales brief.

    Jangan panggil get_report_guide() untuk request ini. Jangan panggil workflow
    report. Jangan scan data Cogan kecuali user eksplisit meminta validasi data
    atau evidence lookup.

    DISAMBIGUASI KATA "DECK". Tool ini HANYA untuk deck PENAWARAN ke calon
    klien (kapabilitas, scope kerja, harga, kredensial). Bila yang diminta
    adalah deck HASIL ANALISIS DATA monitoring klien berjalan - ada nama
    brand, periode data, metrik, atau kata mingguan/bulanan - itu BUKAN
    Jalur 0B. Panggil get_report_guide().

    Bila sinyalnya CAMPUR atau tidak jelas - contoh: "bikin deck buat klien X"
    tanpa keterangan lain - JANGAN menebak. Tanya satu kalimat lebih dulu:
    "Ini deck proposal untuk calon klien, atau report dari data monitoring?"
    Lanjutkan hanya setelah user menjawab.

    BATAS DENGAN JALUR 0C (ONBOARDING). Tool ini untuk deck MENJUAL ke calon
    klien (deal belum closing). Bila deal SUDAH ditandatangani dan yang diminta
    adalah kickoff deck / onboarding deck / welcome summary untuk klien baru,
    itu Jalur 0C: panggil get_onboarding_guide().

    Preferred input adalah Client Intelligence Brief / Presales Brief / Account Brief.
    Jika brief resmi belum ada, kumpulkan field material atau bentuk sales-deck
    intake ringan. Default output adalah CONTENT_DRAFT; buat PPTX hanya jika user
    eksplisit meminta FINAL_PRODUCTION/PPTX atau konten sudah disetujui.
    """
    header = (
        "# COGAN JALUR 0B — SALES DECK / PITCH DECK\n"
        "# Gunakan untuk sales deck, pitch deck, proposal deck, deck proposal, "
        "deck jualan, commercial deck, client presentation, sales presentation, "
        "PPTX proposal, final production PPTX, atau deck dari client/intelligence/"
        "presales brief.\n"
        "# Jangan panggil report workflow, get_report_guide(), atau anomaly tools "
        "kecuali user eksplisit meminta validasi data/evidence lookup.\n"
        "# Preferred input: Client Intelligence Brief / Presales Brief / Account Brief. "
        "Kalau hanya raw sales context yang ada, minta field material yang hilang "
        "atau buat sales-deck intake ringan; jangan klaim ada client brief final.\n"
        "# Default: CONTENT_DRAFT. Buat PPTX/final production hanya jika user "
        "meminta PPTX/final production atau content sudah approved dan gate tidak BLOCKED.\n"
    )

    parts = [header]
    missing: list[str] = []

    for title, relative_path in _SALES_DECK_FILES:
        path = SALES_DECK_DIR / relative_path
        if path.exists():
            body = path.read_text(encoding="utf-8-sig")
            parts.append(f"\n\n{'=' * 72}\n### {title}\n{'=' * 72}\n\n{body}")
        else:
            missing.append(relative_path)

    if missing:
        parts.append(
            "\n\n[PERINGATAN] File sales deck belum ditemukan: "
            + ", ".join(missing)
            + ". Pastikan folder skills/salesdeck-generator sudah terpasang."
        )

    return "".join(parts)


@mcp.tool()
def get_onboarding_guide() -> str:
    """
    JALUR 0C — Client Onboarding (deal SUDAH closing).

    Panggil tool ini bila user meminta onboarding klien baru, project brief,
    configuration package, keyword package, paket konfigurasi, scope package,
    final handover, onboarding handover, kickoff deck, kickoff summary, atau
    client welcome summary — untuk klien yang kontraknya SUDAH ditandatangani
    dan sedang disiapkan untuk mulai berjalan.

    PENANDA JALUR — TAHAP HUBUNGAN DENGAN KLIEN:
    - Deal BELUM closing (masih calon klien, presales, meeting prep)
      -> BUKAN tool ini. Panggil get_intelligence_brief_guide() (Jalur 0)
         atau get_sales_deck_guide() (Jalur 0B).
    - Deal SUDAH closing, layanan BELUM berjalan
      -> Jalur 0C. Tool ini.
    - Layanan SUDAH berjalan dan sudah ada data monitoring
      -> BUKAN tool ini. Panggil get_report_guide() (Jalur 1 / Jalur 2).

    DISAMBIGUASI KATA YANG BERIRISAN:
    - "brief": project brief untuk delivery setelah closing = Jalur 0C.
      Client/intelligence/presales brief sebelum closing = Jalur 0.
    - "deck": kickoff deck untuk klien yang sudah closing = Jalur 0C.
      Sales/pitch/proposal deck untuk menjual = Jalur 0B.
    - "summary": client welcome summary onboarding = Jalur 0C.
      Ringkasan dari data monitoring = Jalur 1 / Jalur 2.

    Bila status deal tidak jelas dari permintaan user, JANGAN menebak dan
    JANGAN menarik data. Tanya satu kalimat lebih dulu:
    "Kontraknya sudah closing dan ini persiapan onboarding, atau masih tahap
    penawaran ke calon klien?" Lanjutkan hanya setelah user menjawab.

    BATAS KELUARAN — DOKUMEN SAJA. Jalur 0C hanya menghasilkan DOKUMEN
    (Markdown, CSV, DOCX, PDF, atau PPTX). Configuration Package adalah
    dokumen usulan setup untuk dibaca dan diterapkan manusia. Tool ini
    TIDAK BOLEH menulis apa pun ke database Cogan: jangan membuat atau
    mengubah campaign, keyword, atau konfigurasi project lewat tool Cogan.
    Penerapan ke sistem dilakukan manual oleh tim setelah dokumen disetujui.

    Jangan panggil get_report_guide() dan jangan panggil workflow report untuk
    request ini. Jangan scan data Cogan kecuali user eksplisit meminta validasi
    data atau evidence lookup.
    """
    header = (
        "# COGAN JALUR 0C — CLIENT ONBOARDING (DEAL SUDAH CLOSING)\n"
        "# Gunakan untuk onboarding klien baru: project brief, configuration/keyword "
        "package, final handover, kickoff summary/deck, dan client welcome summary.\n"
        "# Sumbernya adalah artefak sisi penjualan (kontrak/SOW, intelligence brief, "
        "sales deck, MoM, onboarding form) - bukan data monitoring Cogan.\n"
        "# JANGAN panggil report workflow. JANGAN scan data Cogan kecuali user "
        "meminta validasi secara eksplisit.\n"
        "# BATAS KELUARAN: dokumen saja. Jangan menulis campaign/keyword/konfigurasi "
        "ke database Cogan. Configuration Package adalah usulan setup untuk diterapkan "
        "manual oleh tim.\n"
        "# Setelah output selesai di chat, tanyakan format file yang diinginkan "
        "sebelum membuat file.\n"
    )

    parts = [header]
    missing: list[str] = []

    for title, relative_path in _ONBOARDING_FILES:
        path = ONBOARDING_DIR / relative_path
        if path.exists():
            body = path.read_text(encoding="utf-8-sig")
            parts.append(f"\n\n{'=' * 72}\n### {title}\n{'=' * 72}\n\n{body}")
        else:
            missing.append(relative_path)

    if missing:
        parts.append(
            "\n\n[PERINGATAN] File onboarding belum ditemukan: "
            + ", ".join(missing)
            + ". Pastikan folder skills/onboarding-generator sudah terpasang."
        )

    return "".join(parts)


@mcp.tool()
def get_report_guide() -> str:
    """
    PINTU DEPAN. Panggil ini SEBELUM apa pun, untuk DUA situasi:

    (a) User meminta report / deck / PPT / laporan — jenis apa pun.
    (b) User bertanya sesuatu yang butuh interpretasi dan akan berujung
        kesimpulan, insight, atau rekomendasi. Contoh:
            "ada topik apa minggu ini di brand A?"
            "apa yang terjadi pada brand A periode B?"
            "cek data brand A dan B, ada yang aneh nggak?"

    Tool ini yang MEMUTUSKAN Jalur 1 (bottom-up) atau Jalur 2 (top-down).
    Jangan menebak sendiri jalurnya; panggil tool ini dulu.

    DISAMBIGUASI KATA "DECK". Kata deck / PPT / presentasi dipakai untuk dua
    hal berbeda:
    - Deck yang DIBANGUN DARI DATA monitoring klien berjalan (apa yang terjadi
      pada brand, periode tertentu) -> ranah tool ini: Jalur 1 / Jalur 2.
    - Deck PENAWARAN ke calon klien (sales / pitch / proposal / commercial:
      kapabilitas, scope kerja, harga) -> BUKAN tool ini.
      Panggil get_sales_deck_guide().

    Bila sinyalnya CAMPUR atau tidak jelas - contoh: "bikin deck buat klien X",
    "buatkan presentasi untuk klien" tanpa menyebut data/periode - JANGAN
    menebak dan JANGAN menarik data. Tanya satu kalimat lebih dulu:
    "Ini deck proposal untuk calon klien, atau report dari data monitoring?"
    Lanjutkan hanya setelah user menjawab.

    BATAS DENGAN JALUR 0C (ONBOARDING). Tool ini untuk klien yang layanannya
    SUDAH berjalan dan sudah ada data monitoring. Bila deal baru saja closing
    dan yang diminta adalah project brief / configuration package / keyword
    package / handover / kickoff / client welcome summary untuk menyiapkan klien
    mulai berjalan - sumbernya kontrak/SOW/sales deck, bukan data monitoring -
    itu Jalur 0C: panggil get_onboarding_guide().

    Tidak perlu dipanggil HANYA untuk permintaan operasional sempit tanpa
    interpretasi: daftar campaign, raw export, satu angka yang scope-nya
    sudah final.

    Membaca panduan editorial client-first.

    Untuk Jalur 2, tampilkan Intent Confirmation dan tunggu persetujuan
    user sebelum memanggil tool analitis. Untuk Jalur 1, ikuti gate
    workflow report masing-masing. Setelah Jalur 2 disetujui:
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
        "# ==================================================================\n"
        "# LANGKAH 0 — TENTUKAN JALUR. Lakukan ini SEBELUM apa pun.\n"
        "# ==================================================================\n"
        "#\n"
        "# Pertama cek apakah ini CLIENT BRIEF/PRESALES BRIEF atau REPORT.\\n"
        "#\\n"
        "# ------------------------------------------------------------------\\n"
        "# JALUR 0 — CLIENT / INTELLIGENCE BRIEF\\n"
        "# ------------------------------------------------------------------\\n"
        "# Pemicu: client brief, presales brief, account brief, meeting prep,\\n"
        "# BD cheat-sheet, intelligence brief, intel brief, intellifence brief,\\n"
        "# brief klien, brief calon klien, brief dari chat/WA/email/RFP/CRM.\\n"
        "#\\n"
        "# Untuk Jalur 0: panggil get_intelligence_brief_guide(). Jangan\\n"
        "# panggil report workflow dan jangan scan data Cogan kecuali user\\n"
        "# eksplisit meminta validasi data. Setelah brief selesai di chat,\\n"
        "# tanya format file: DOCX/Google Docs, PDF, Markdown+JSON, atau\\n"
        "# cukup di chat. Jangan auto-generate file.\\n"
        "#\\n"
        "# Setelah bukan Jalur 0, baru pertanyaannya: USER MENYEBUT TIPE REPORT, ATAU TIDAK?\\n"
        "#\n"
        "# ------------------------------------------------------------------\n"
        "# JALUR 1 — BOTTOM-UP  (user MENYEBUT tipe report)\n"
        "# ------------------------------------------------------------------\n"
        "# Pemicu: user menyebut salah satu jenis ini secara eksplisit —\n"
        "#   'daily report' / 'daily social'       -> create_daily_social_report_workflow\n"
        "#   'MMR' / 'mainstream media report'     -> create_mainstream_media_report_workflow\n"
        "#   'competitive analysis' / 'CA'         -> create_competitive_analysis_report_workflow\n"
        "#   'BCE' / 'brand content effectiveness' -> create_bce_report_workflow\n"
        "#   'industry trend'                      -> create_industry_trend_report_workflow\n"
        "#   'SFIR' / 'spokesperson report'        -> create_sfir_report_workflow\n"
        "#\n"
        "# Alur Jalur 1 sudah PAKEM. Jangan diubah, jangan dicampur:\n"
        "#   workflow -> (audience bila diminta) -> Task 1 preview\n"
        "#            -> user konfirmasi -> Task 2 -> PPT\n"
        "#\n"
        "# Di Jalur 1, Intent Confirmation 8 poin TIDAK dipakai. Workflow punya\n"
        "# gate-nya sendiri. JANGAN menjalankan dua gate.\n"
        "# Di Jalur 1, deck dibangun build_*_ppt_package. JANGAN merakit slide\n"
        "# manual dari perpustakaan_resep_slide.md.\n"
        "#\n"
        "# ------------------------------------------------------------------\n"
        "# JALUR 2 — TOP-DOWN  (user TIDAK menyebut tipe report)\n"
        "# ------------------------------------------------------------------\n"
        "# Pemicu: user memberi INTENT / PERTANYAAN, bukan nama report —\n"
        "#   'ada topik apa minggu ini di brand A?'\n"
        "#   'apa yang terjadi pada brand A periode B?'\n"
        "#   'cek data brand A dan B'\n"
        "#   'bikin laporan' / 'saya mau PPT'   (tanpa menyebut jenisnya)\n"
        "#\n"
        "# Di Jalur 2, DILARANG memanggil:\n"
        "#   create_*_report_workflow\n"
        "#   prepare_report_input\n"
        "#   build_*_ppt_package\n"
        "#\n"
        "# Urutan Jalur 2 (jangan dibalik):\n"
        "#   1. INTENT CONFIRMATION 8 poin -> TAMPILKAN ke user, BERHENTI,\n"
        "#      tunggu persetujuan. Tanyakan audience, brand saja atau plus\n"
        "#      kompetitor, periode, keputusan yang mau dibantu, DAN output\n"
        "#      yang diharapkan (deck / narrative / memo).\n"
        "#      Belum boleh menarik data apa pun sebelum ini disetujui.\n"
        "#   2. Setelah setuju: validate_metric_readiness() + data_health()\n"
        "#   3. Diagnosis: scan_anomalies(), timeline(), get_posts(),\n"
        "#      top_viral_posts(), top_authors(), dst\n"
        "#   4. LAPORKAN TEMUAN ke user di chat lebih dulu\n"
        "#   5. Simpulkan JENIS MASALAHNYA (Crisis/Issue/PR, Competitive,\n"
        "#      Campaign, Brand Health, Segmentation, Custom) lalu konfirmasi\n"
        "#      singkat: 'ini Crisis/Issue, saya susun deck-nya ya'\n"
        "#      JANGAN tanya ulang 'mau PPT atau tidak' — output sudah\n"
        "#      disepakati di langkah 1.\n"
        "#   6. Rakit deck dari SKILL: skill_report.md untuk cerita,\n"
        "#      perpustakaan_resep_slide.md untuk slide. Target 12-18 slide.\n"
        "#      BUKAN lewat Task 1 / Task 2.\n"
        "#\n"
        "# ------------------------------------------------------------------\n"
        "# RAGU?\n"
        "# ------------------------------------------------------------------\n"
        "# Kalau ragu apakah user menyebut tipe report: berarti TIDAK menyebut.\n"
        "# Ambil JALUR 2. Bentuk report adalah HASIL diagnosis, bukan menu yang\n"
        "# dipilih dari cara user menyusun kalimat. Isu krisis tidak otomatis\n"
        "# menjadi 'daily social report' hanya karena datanya sosial dan\n"
        "# rentangnya harian.\n"
        "#\n"
        "# ==================================================================\n"
        "# BERLAKU DI KEDUA JALUR\n"
        "# ==================================================================\n"
        "#\n"
        "# METRIC READINESS\n"
        "#   Panggil validate_metric_readiness() dan data_health() sebelum\n"
        "#   interactions/views dipakai sebagai KPI.\n"
        "#\n"
        "# LINK POST WAJIB\n"
        "#   Setiap post yang dikutip - di deck MAUPUN di tabel/daftar dalam\n"
        "#   chat - wajib menampilkan link-nya.\n"
        "#   Ambil dari field 'url' (output get_posts / top_viral_posts) atau\n"
        "#   '_cogan_url' (output export_raw_data). Nama field-nya BEDA,\n"
        "#   jangan tertukar. Bila kosong, tulis '(link tak tersedia)'.\n"
        "#\n\n"
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
        "# RUNTIME GATE: Tentukan Jalur 1/Jalur 2 lebih dulu. Jalur 1 dipakai "
        "hanya bila user menyebut tipe report eksplisit dan memakai workflow "
        "report masing-masing. Jalur 2 dipakai bila user memberi intent/pertanyaan; "
        "lakukan Intent Confirmation dan tunggu approval sebelum tool analitis dipanggil.\n"
        "# Setelah approval Jalur 2, panggil validate_metric_readiness() dan "
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
