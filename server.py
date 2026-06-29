"""
Cogan MCP Server.

Tahap 1: ping_cogan() - buktikan connector hidup.
Tahap 2: find_project() - cek data project tersedia.
Tahap 3-4: wordcloud guidance, candidates, dan render PNG/CSV.
"""

from __future__ import annotations

import csv
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).parent
os.environ.setdefault("MPLCONFIGDIR", str(BASE_DIR / "output" / ".matplotlib"))

import pandas as pd
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import FileResponse, PlainTextResponse
from wordcloud import WordCloud

from database import db


mcp = FastMCP("Cogan", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))

DATA_DIR = BASE_DIR / "data"
CONFIG_DIR = BASE_DIR / "config"
# Folder hasil. Set env STORAGE_DIR ke path Railway Volume (mis. /data) agar
# file PERMANEN (tidak hilang saat redeploy). Default: folder sementara.
OUTPUT_DIR = Path(os.environ.get("STORAGE_DIR") or (BASE_DIR / "output"))
try:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
SKILLS_DIR = BASE_DIR / "skills"


def _public_base_url() -> str:
    """Alamat publik server (untuk membuat link unduhan file hasil)."""
    base = os.environ.get("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if base:
        return base
    dom = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip()
    if dom:
        return "https://" + dom
    return ""


@mcp.custom_route("/files/{filename}", methods=["GET"])
async def serve_output_file(request: Request):
    """Pintu unduhan: melayani file hasil (PNG/CSV) lewat link publik,
    supaya wordcloud bisa dibuka/diunduh langsung dari browser."""
    safe = os.path.basename(request.path_params["filename"])  # cegah path traversal
    path = OUTPUT_DIR / safe
    if not path.exists():
        return PlainTextResponse(
            "File tidak ditemukan (kemungkinan terhapus saat server restart). "
            "Silakan generate ulang.",
            status_code=404,
        )
    return FileResponse(str(path))

TEXT_COLUMNS = ("Title", "Content")
DATE_COLUMN = "Date"
CHANNEL_COLUMN = "Channel"
SENTIMENT_COLUMN = "Sentiment"
ENGAGEMENT_COLUMN = "Engagement"

SENTIMENT_COLORS = {
    "positive": "#16a34a",
    "negative": "#dc2626",
    "neutral": "#6b7280",
}

def _load_stopwords() -> set[str]:
    """Baca stopword umum dari config/global_stopwords.json. Tambah/hapus
    kata di file itu langsung berlaku, tidak perlu edit kode ini."""
    path = CONFIG_DIR / "global_stopwords.json"
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return {w.strip().lower() for w in data.get("stopwords", []) if w.strip()}


def _project_id(project_name: str) -> str:
    return project_name.strip().lower()


def _raw_data_path(project_name: str) -> Path:
    return DATA_DIR / _project_id(project_name) / "raw_data.xlsx"


def _guidance_path(project_name: str) -> Path:
    return CONFIG_DIR / f"{_project_id(project_name)}_wordcloud_guidance.json"


def _available_projects() -> list[str]:
    # Sumber kebenaran sekarang: tabel clients di database (bukan folder).
    return db.list_campaigns()


def _read_project_data(project_name: str) -> pd.DataFrame:
    # Kompatibilitas: ambil SEMUA post 1 klien dari database. Untuk jalur
    # berat (kandidat & render) kita pakai versi TERSARING di bawah supaya
    # tidak menarik semua baris dari jutaan data.
    return db.fetch_posts_df(project_name)


def _read_filtered(
    project_name: str,
    start_date: str | None,
    end_date: str | None,
    channels: str | None,
) -> pd.DataFrame:
    # Penyaringan (klien + tanggal + channel) dikerjakan di SISI DATABASE
    # lewat index, jadi Python hanya menerima irisan data yang relevan.
    return db.fetch_posts_df(project_name, start_date, end_date, channels)


def _read_guidance(project_name: str) -> dict[str, Any]:
    guidance = db.get_guidance(project_name)
    if not guidance:
        return {
            "project_id": _project_id(project_name),
            "objective": None,
            "include": [],
            "exclude": [],
            "brand_term_policy": "Tidak ada guidance khusus.",
            "preferred_term_format": "Frasa 1 sampai 3 kata.",
            "default_max_output_terms": 50,
        }
    return guidance


def _prepare_df(
    df: pd.DataFrame,
    start_date: str | None = None,
    end_date: str | None = None,
    channels: str | None = None,
) -> pd.DataFrame:
    result = df.copy()
    if DATE_COLUMN in result.columns:
        # utc=True lalu buang zona waktu -> selalu tz-naive, aman dibanding
        # tanggal dari user. Memperbaiki error perbandingan tanggal dari DB.
        result["_parsed_date"] = (
            pd.to_datetime(result[DATE_COLUMN], errors="coerce", utc=True)
            .dt.tz_localize(None)
        )
        if start_date:
            result = result[result["_parsed_date"] >= pd.to_datetime(start_date)]
        if end_date:
            end_ts = pd.to_datetime(end_date)
            if end_ts == end_ts.normalize():
                end_ts = end_ts + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
            result = result[result["_parsed_date"] <= end_ts]

    if channels and CHANNEL_COLUMN in result.columns:
        wanted = {c.strip().lower() for c in channels.split(",") if c.strip()}
        if wanted:
            result = result[
                result[CHANNEL_COLUMN].fillna("").astype(str).str.lower().isin(wanted)
            ]

    text_parts = []
    for col in TEXT_COLUMNS:
        if col in result.columns:
            text_parts.append(result[col].fillna("").astype(str))
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


def _candidate_terms(tokens: list[str], project_id: str, extra_blocklist: set[str] | None = None) -> set[str]:
    terms: set[str] = set()
    blocklist = _load_stopwords() | {project_id.lower()} | (extra_blocklist or set())

    for n in (1, 2, 3):
        for i in range(0, max(0, len(tokens) - n + 1)):
            gram_tokens = tokens[i : i + n]
            if any(t in blocklist for t in gram_tokens):
                continue
            if all(len(t) <= 2 for t in gram_tokens):
                continue
            if all(t.isdigit() for t in gram_tokens):
                continue
            term = " ".join(gram_tokens).strip()
            if len(term) < 3:
                continue
            terms.add(term)

    return terms


def _majority_sentiment(values: list[str]) -> str:
    normalized = [
        str(v).strip().lower()
        for v in values
        if str(v).strip().lower() in {"positive", "negative", "neutral"}
    ]
    if not normalized:
        return "neutral"
    counts = Counter(normalized)
    top = counts.most_common()
    if len(top) > 1 and top[0][1] == top[1][1]:
        return "neutral"
    return top[0][0]


def _term_matches_text(term_tokens: list[str], text_tokens: list[str], text_norm: str) -> bool:
    if not term_tokens:
        return False
    term_norm = " ".join(term_tokens)
    if term_norm in text_norm:
        return True
    if len(term_tokens) == 1:
        return term_tokens[0] in set(text_tokens)
    text_token_set = set(text_tokens)
    return all(token in text_token_set for token in term_tokens)


def _build_candidates(
    project_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    channels: str | None = None,
    candidate_pool_size: int = 200,
) -> list[dict[str, Any]]:
    project_id = _project_id(project_name)
    df = _prepare_df(_read_filtered(project_name, start_date, end_date, channels), start_date, end_date, channels)
    if df.empty:
        return []

    guidance = _read_guidance(project_name)
    extra_blocklist = {
        str(w).strip().lower()
        for w in guidance.get("extra_blocklist", [])
        if str(w).strip()
    }

    frequency: Counter[str] = Counter()
    engagement: defaultdict[str, float] = defaultdict(float)
    sentiments: defaultdict[str, list[str]] = defaultdict(list)
    examples: dict[str, str] = {}

    for _, row in df.iterrows():
        text = str(row.get("_combined_text", ""))
        tokens = _tokenize(text)
        row_terms = _candidate_terms(tokens, project_id, extra_blocklist)
        row_engagement = pd.to_numeric(row.get(ENGAGEMENT_COLUMN, 0), errors="coerce")
        if pd.isna(row_engagement):
            row_engagement = 0
        row_sentiment = str(row.get(SENTIMENT_COLUMN, "neutral")).strip().lower()

        for term in row_terms:
            frequency[term] += 1
            engagement[term] += float(row_engagement)
            sentiments[term].append(row_sentiment)
            examples.setdefault(term, text[:180])

    rows = []
    for term, freq in frequency.items():
        rows.append(
            {
                "term": term,
                "frequency": int(freq),
                "engagement": int(engagement[term]),
                "sentiment": _majority_sentiment(sentiments[term]),
                "example": examples.get(term, ""),
            }
        )

    rows.sort(key=lambda r: (r["frequency"], r["engagement"], len(r["term"])), reverse=True)
    return rows[: max(1, int(candidate_pool_size))]


def _stats_for_selected_terms(
    project_name: str,
    selected_terms: list[str],
    start_date: str | None = None,
    end_date: str | None = None,
    channels: str | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    df = _prepare_df(_read_filtered(project_name, start_date, end_date, channels), start_date, end_date, channels)
    rows: list[dict[str, Any]] = []
    unmatched: list[str] = []

    for raw_term in selected_terms:
        term = str(raw_term).strip()
        if not term:
            continue

        term_norm = " ".join(_tokenize(term))
        if not term_norm:
            unmatched.append(term)
            continue

        frequency = 0
        total_engagement = 0.0
        sentiments: list[str] = []
        example = ""

        for _, row in df.iterrows():
            text = str(row.get("_combined_text", ""))
            text_tokens = _tokenize(text)
            text_norm = " ".join(text_tokens)
            if not _term_matches_text(term_norm.split(), text_tokens, text_norm):
                continue

            frequency += 1
            row_engagement = pd.to_numeric(row.get(ENGAGEMENT_COLUMN, 0), errors="coerce")
            if not pd.isna(row_engagement):
                total_engagement += float(row_engagement)
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
                "engagement": int(total_engagement),
                "sentiment": _majority_sentiment(sentiments),
                "example": example,
            }
        )

    return rows, unmatched


from decimal import Decimal as _Decimal


def _delta(a, b):
    """Selisih A vs B (B sebagai pembanding): diff + persen perubahan."""
    a = a or 0
    b = b or 0
    diff = round(a - b, 2)
    pct = round((a - b) * 100 / b, 1) if b else None
    return {"a": a, "b": b, "diff": diff, "pct_change": pct}


def _num_clean(v):
    """Decimal/None -> angka biasa supaya rapi di JSON."""
    if v is None:
        return 0
    if isinstance(v, _Decimal):
        fv = float(v)
        return int(fv) if fv.is_integer() else round(fv, 2)
    return v


CHANNEL_METRIC_MAP = {
    "tiktok": ["likes", "comments", "shares"],
    "instagram": ["likes", "comments"],
    "twitter": ["likes", "replies", "retweets"],
    "x": ["likes", "replies", "retweets"],
    "facebook": ["likes", "comments", "shares"],
    "youtube": ["likes", "comments"],
    "online media": [],  # online media TIDAK punya engagement; pakai tool top_media (ad value per media)
}
_DEFAULT_CHANNEL_METRICS = ["likes", "comments", "shares"]


@mcp.tool()
def count_posts(project_name: str, start_date: str = "", end_date: str = "") -> dict:
    """
    Hitung jumlah post sebuah campaign/klien + pecahan per channel dan per
    sentiment, lengkap dengan persentase. Bisa difilter rentang tanggal
    (format YYYY-MM-DD). Kosongkan tanggal untuk seluruh periode.
    Gunakan ini saat user bertanya "ada berapa data", "breakdown per channel/
    sentiment", "berapa persen negatif", dsb. Sajikan angka + analisis singkat.
    """
    data = db.count_and_breakdown(project_name, start_date or None, end_date or None)
    if data is None:
        return {"found": False, "error": f"Campaign '{project_name}' tidak ditemukan.",
                "available_campaigns": _available_projects()}

    total = data["total"] or 0

    def _pct(c):
        return round(c * 100 / total, 1) if total else 0.0

    by_channel = [
        {"channel": ch, "count": n, "percent": _pct(n)} for ch, n in data["channels"]
    ]
    by_sentiment = [
        {"sentiment": s, "count": n, "percent": _pct(n)} for s, n in data["sentiments"]
    ]
    return {
        "found": True,
        "project_name": project_name,
        "period": {"from": start_date or None, "to": end_date or None},
        "total_posts": total,
        "by_channel": by_channel,
        "by_sentiment": by_sentiment,
    }


@mcp.tool()
def export_raw_data(
    project_name: str,
    start_date: str = "",
    end_date: str = "",
    limit: int = 0,
) -> dict:
    """
    Ekspor raw data (semua kolom asli) sebuah campaign ke file CSV, lalu
    kembalikan LINK download. Bisa difilter rentang tanggal (YYYY-MM-DD).
    limit > 0 membatasi jumlah baris (mis. limit=100 untuk contoh/tes);
    limit=0 berarti semua. Gunakan saat user minta "raw data"/"data mentah".
    """
    lim = int(limit) if limit and int(limit) > 0 else None
    records = db.fetch_raw_records(project_name, start_date or None, end_date or None, lim)
    if records is None:
        return {"success": False, "error": f"Campaign '{project_name}' tidak ditemukan.",
                "available_campaigns": _available_projects()}
    if not records:
        return {"success": False, "message": "Tidak ada data pada filter tersebut."}

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(records)
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", project_name.strip().lower()).strip("-")
    parts = [slug or "data"]
    if start_date:
        parts.append(start_date)
    if end_date:
        parts.append(end_date)
    if lim:
        parts.append(f"first{lim}")
    fname = "_".join(parts) + "_raw.csv"
    csv_path = OUTPUT_DIR / fname
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    base = _public_base_url()
    url = f"{base}/files/{fname}" if base else ""
    try:
        db.save_output(project_name, "raw_export",
                       {"start_date": start_date or None, "end_date": end_date or None,
                        "limit": lim},
                       {"row_count": len(records), "file": fname, "download_url": url})
    except Exception:
        pass
    return {
        "success": True,
        "row_count": len(records),
        "column_count": df.shape[1],
        "download_url": url,
        "note": (
            "Buka download_url untuk mengunduh CSV raw data."
            if base else
            "Link belum aktif: set PUBLIC_BASE_URL / RAILWAY_PUBLIC_DOMAIN di server."
        ),
    }


@mcp.tool()
def metrics_summary(project_name: str, start_date: str = "", end_date: str = "",
                    channel: str = "") -> dict:
    """
    Ringkasan METRIK sebuah campaign: total engagement + breakdown per channel
    (likes, comments, shares, views, replies, retweets) dan total keseluruhan.
    Bisa difilter rentang tanggal (YYYY-MM-DD) dan satu channel tertentu.
    Gunakan untuk pertanyaan seperti "total view periode sekian", "breakdown
    engagement IG/TikTok/dll", "berapa total likes/komentar/share".
    Saat menyajikan, tampilkan metrik yang relevan per platform:
    IG = likes & comments; TikTok/Facebook/YouTube = likes, comments, shares,
    views; X/Twitter = likes, replies, retweets. Beri analisis singkat.
    """
    rows = db.metrics_breakdown(project_name, start_date or None, end_date or None,
                                channel or None)
    if rows is None:
        return {"found": False, "error": f"Campaign '{project_name}' tidak ditemukan.",
                "available_campaigns": _available_projects()}
    keys = ["posts", "engagement", "likes", "comments", "shares", "views",
            "replies", "retweets", "buzz", "ad_value", "pr_value"]
    per_channel, totals = [], {k: 0 for k in keys}
    for r in rows:
        d = {"channel": r["ch"]}
        for k in keys:
            v = _num_clean(r.get(k))
            d[k] = v
            totals[k] += v
        d["relevant_metrics"] = CHANNEL_METRIC_MAP.get(
            (r["ch"] or "").strip().lower(), _DEFAULT_CHANNEL_METRICS)
        per_channel.append(d)
    return {
        "found": True,
        "project_name": project_name,
        "period": {"from": start_date or None, "to": end_date or None},
        "totals": totals,
        "by_channel": per_channel,
        "metric_note": ("Tampilkan hanya 'relevant_metrics' tiap channel "
                        "(mis. Online Media pakai ad_value, bukan engagement)."),
    }


@mcp.tool()
def top_authors(project_name: str, start_date: str = "", end_date: str = "",
                limit: int = 10) -> dict:
    """
    Top author/akun berdasarkan total engagement pada satu campaign + rentang
    tanggal (limit = berapa banyak, mis. 5/10/20). Untuk tiap author dikembalikan:
    total engagement, jumlah post, channel, pecahan sentiment, DAN post terbaiknya
    (konten, link URL, channel, sentiment, serta breakdown engagement post itu:
    likes/comments/shares/views/replies/retweets). Sajikan dengan analisis.
    """
    rows = db.top_authors(project_name, start_date or None, end_date or None,
                          int(limit) if limit else 10)
    if rows is None:
        return {"found": False, "error": f"Campaign '{project_name}' tidak ditemukan.",
                "available_campaigns": _available_projects()}
    out = []
    for a in rows:
        tp = a.get("top_post") or {}
        content = (tp.get("content") or "")
        out.append({
            "author": a["author"],
            "channel": a["channel"],
            "posts": a["posts"],
            "total_engagement": _num_clean(a["total_engagement"]),
            "sentiment": a["sentiment"],
            "top_post": {
                "content": content[:300],
                "url": tp.get("url"),
                "channel": tp.get("channel"),
                "sentiment": tp.get("sentiment"),
                "engagement": _num_clean(tp.get("engagement")),
                "likes": _num_clean(tp.get("likes")),
                "comments": _num_clean(tp.get("comments")),
                "shares": _num_clean(tp.get("shares")),
                "views": _num_clean(tp.get("views")),
                "replies": _num_clean(tp.get("replies")),
                "retweets": _num_clean(tp.get("retweets")),
            },
        })
    return {
        "found": True,
        "project_name": project_name,
        "period": {"from": start_date or None, "to": end_date or None},
        "limit": int(limit) if limit else 10,
        "top_authors": out,
    }


@mcp.tool()
def timeline(project_name: str, start_date: str = "", end_date: str = "",
             channel: str = "") -> dict:
    """
    Breakdown PER TANGGAL untuk satu campaign: jumlah post, total engagement,
    dan pecahan sentiment tiap hari. Bisa difilter rentang tanggal (YYYY-MM-DD)
    dan channel. Gunakan untuk pertanyaan "data/engagement per tanggal",
    "tren harian", lalu sajikan + bisa dibuat chart oleh Claude.
    """
    rows = db.timeline(project_name, start_date or None, end_date or None, channel or None)
    if rows is None:
        return {"found": False, "error": f"Campaign '{project_name}' tidak ditemukan.",
                "available_campaigns": _available_projects()}
    days = []
    for r in rows:
        days.append({
            "date": r["day"].strftime("%Y-%m-%d") if r["day"] else None,
            "posts": r["posts"],
            "engagement": _num_clean(r["engagement"]),
            "sentiment": {"positive": r["pos"], "negative": r["neg"], "neutral": r["neu"]},
        })
    return {"found": True, "project_name": project_name,
            "period": {"from": start_date or None, "to": end_date or None},
            "timeline": days}


@mcp.tool()
def get_posts(project_name: str, start_date: str = "", end_date: str = "",
              channel: str = "", sentiment: str = "", sort_by: str = "engagement",
              limit: int = 50) -> dict:
    """
    Ambil POST LENGKAP sekaligus (tanggal, channel, author, KONTEN, sentiment,
    link URL, dan semua metrik: engagement, likes, comments, shares, views,
    replies, retweets). Terfilter (rentang tanggal, channel, sentiment) dan
    terurut (sort_by: "engagement" [default], "date", "date_desc"), dengan batas
    jumlah (limit, default 50, maksimum 200).

    Inilah alat untuk ANALISIS BERBASIS ISI: gunakan ini saat user minta
    "isu apa saja", "analisis percakapan", "rangkum narasi", dst. BACA konten
    post yang dikembalikan lalu simpulkan isu/temanya sendiri -- JANGAN menebak
    isu dari frekuensi kata wordcloud. Untuk gambaran luas, urutkan by engagement
    dan ambil cukup banyak (mis. 80-150 post berpengaruh).
    """
    lim = max(1, min(int(limit) if limit else 50, 200))
    rows = db.get_posts(project_name, start_date or None, end_date or None,
                        channel or None, sentiment or None, sort_by or "engagement", lim)
    if rows is None:
        return {"found": False, "error": f"Campaign '{project_name}' tidak ditemukan.",
                "available_campaigns": _available_projects()}
    posts = []
    for r in rows:
        content = (r.get("content") or "")
        posts.append({
            "date": r["post_date"].strftime("%Y-%m-%d %H:%M") if r.get("post_date") else None,
            "channel": r.get("channel"),
            "author": r.get("author"),
            "sentiment": r.get("sentiment"),
            "url": r.get("url"),
            "content": content[:600],
            "engagement": _num_clean(r.get("engagement")),
            "likes": _num_clean(r.get("likes")),
            "comments": _num_clean(r.get("comments")),
            "shares": _num_clean(r.get("shares")),
            "views": _num_clean(r.get("views")),
            "replies": _num_clean(r.get("replies")),
            "retweets": _num_clean(r.get("retweets")),
        })
    return {"found": True, "project_name": project_name,
            "period": {"from": start_date or None, "to": end_date or None},
            "returned": len(posts), "sort_by": sort_by or "engagement", "posts": posts}


@mcp.tool()
def compare_periods(project_name: str, period_a_start: str, period_a_end: str,
                    period_b_start: str, period_b_end: str, channel: str = "") -> dict:
    """
    Bandingkan DUA periode untuk satu campaign (mis. minggu ini vs minggu lalu):
    jumlah post, engagement, sentiment, lengkap dengan selisih & persen perubahan.
    Periode A = pembanding utama, Periode B = baseline. Tanggal format YYYY-MM-DD.
    Sajikan dengan analisis (naik/turun, kemungkinan pemicunya).
    """
    a = db.period_totals(project_name, period_a_start or None, period_a_end or None, channel or None)
    b = db.period_totals(project_name, period_b_start or None, period_b_end or None, channel or None)
    if a is None or b is None:
        return {"found": False, "error": f"Campaign '{project_name}' tidak ditemukan.",
                "available_campaigns": _available_projects()}

    def _pack(t, ps, pe):
        return {"from": ps or None, "to": pe or None, "posts": t["posts"],
                "engagement": _num_clean(t["engagement"]),
                "sentiment": {"positive": t["pos"], "negative": t["neg"], "neutral": t["neu"]}}

    return {
        "found": True, "project_name": project_name,
        "period_a": _pack(a, period_a_start, period_a_end),
        "period_b": _pack(b, period_b_start, period_b_end),
        "change": {
            "posts": _delta(a["posts"], b["posts"]),
            "engagement": _delta(_num_clean(a["engagement"]), _num_clean(b["engagement"])),
            "negative_posts": _delta(a["neg"], b["neg"]),
        },
    }


@mcp.tool()
def compare_campaigns(campaign_a: str, campaign_b: str, start_date: str = "",
                      end_date: str = "") -> dict:
    """
    Bandingkan DUA campaign/klien pada rentang tanggal yang sama (mis. brand kita
    vs kompetitor): jumlah post, engagement, sentiment, + selisih & persen.
    Tanggal opsional (YYYY-MM-DD). Sajikan dengan analisis.
    """
    a = db.period_totals(campaign_a, start_date or None, end_date or None)
    b = db.period_totals(campaign_b, start_date or None, end_date or None)
    missing = [n for n, t in [(campaign_a, a), (campaign_b, b)] if t is None]
    if missing:
        return {"found": False, "error": f"Campaign tidak ditemukan: {', '.join(missing)}",
                "available_campaigns": _available_projects()}

    def _pack(t):
        return {"posts": t["posts"], "engagement": _num_clean(t["engagement"]),
                "sentiment": {"positive": t["pos"], "negative": t["neg"], "neutral": t["neu"]}}

    return {
        "found": True,
        "period": {"from": start_date or None, "to": end_date or None},
        "campaign_a": {"name": campaign_a, **_pack(a)},
        "campaign_b": {"name": campaign_b, **_pack(b)},
        "difference": {
            "posts": _delta(a["posts"], b["posts"]),
            "engagement": _delta(_num_clean(a["engagement"]), _num_clean(b["engagement"])),
        },
    }


@mcp.tool()
def share_of_voice(start_date: str = "", end_date: str = "", campaigns: str = "",
                   metric: str = "buzz") -> dict:
    """
    Share of Voice: seberapa besar tiap campaign mendominasi percakapan pada
    rentang tanggal tertentu. `metric` penentu ranking & persen share:
    "buzz" (default, ukuran umum SOV), "engagement", atau "posts" (volume).
    `campaigns` = daftar nama dipisah koma; kosongkan untuk SEMUA campaign.
    Catatan: bila satu post terdaftar di beberapa campaign, ia dihitung di
    masing-masing (share bisa tumpang-tindih). Sajikan dengan analisis ranking.
    """
    metric = (metric or "buzz").strip().lower()
    if metric not in ("buzz", "engagement", "posts"):
        metric = "buzz"
    names = [c.strip() for c in campaigns.split(",") if c.strip()] if campaigns else db.list_campaigns()
    rows, grand = [], 0
    for n in names:
        t = db.period_totals(n, start_date or None, end_date or None)
        if t is None:
            continue
        posts = t["posts"]
        eng = _num_clean(t["engagement"])
        buzz = _num_clean(t.get("buzz"))
        value = {"buzz": buzz, "engagement": eng, "posts": posts}[metric]
        rows.append({"campaign": n, "posts": posts, "engagement": eng, "buzz": buzz,
                     "value": value})
        grand += value
    for r in rows:
        r["share_pct"] = round(r["value"] * 100 / grand, 1) if grand else 0
    rows.sort(key=lambda x: -x["value"])
    return {
        "found": True,
        "metric": metric,
        "period": {"from": start_date or None, "to": end_date or None},
        "total_value": grand,
        "share_of_voice": rows,
    }


@mcp.tool()
def detect_spikes(project_name: str, start_date: str = "", end_date: str = "",
                  metric: str = "posts", channel: str = "", threshold: float = 1.8) -> dict:
    """
    Deteksi LONJAKAN (spike) percakapan: hari-hari yang nilainya jauh di atas
    rata-rata. metric = "posts" (volume percakapan, default) atau "engagement".
    threshold = berapa kali lipat di atas rata-rata untuk dianggap lonjakan
    (default 1.8). Mengembalikan timeline harian + hari puncak + daftar hari
    lonjakan. Gunakan untuk "kapan percakapan meledak / deteksi krisis", lalu
    jelaskan PEMICUNYA (boleh lanjut panggil get_posts pada hari lonjakan itu).
    """
    rows = db.timeline(project_name, start_date or None, end_date or None, channel or None)
    if rows is None:
        return {"found": False, "error": f"Campaign '{project_name}' tidak ditemukan.",
                "available_campaigns": _available_projects()}

    series = []
    for r in rows:
        val = r["posts"] if metric != "engagement" else _num_clean(r["engagement"])
        series.append({
            "date": r["day"].strftime("%Y-%m-%d") if r["day"] else None,
            "value": val,
            "posts": r["posts"],
            "engagement": _num_clean(r["engagement"]),
            "sentiment": {"positive": r["pos"], "negative": r["neg"], "neutral": r["neu"]},
        })
    values = [d["value"] for d in series] or [0]
    avg = sum(values) / len(values) if values else 0
    spikes = []
    for d in series:
        if avg > 0 and d["value"] >= avg * float(threshold):
            spikes.append({"date": d["date"], "value": d["value"],
                           "x_above_average": round(d["value"] / avg, 1),
                           "sentiment": d["sentiment"]})
    spikes.sort(key=lambda x: -x["value"])
    peak = max(series, key=lambda d: d["value"]) if series else None

    return {
        "found": True, "project_name": project_name, "metric": metric,
        "period": {"from": start_date or None, "to": end_date or None},
        "average_per_day": round(avg, 1),
        "peak_day": {"date": peak["date"], "value": peak["value"]} if peak else None,
        "spikes": spikes,
        "timeline": series,
    }


@mcp.tool()
def top_viral_posts(project_name: str, start_date: str = "", end_date: str = "",
                    by: str = "engagement", channel: str = "", limit: int = 10) -> dict:
    """
    Postingan individual paling VIRAL pada satu periode, diurut by metrik:
    "engagement" (default), "views", "shares", "likes", "comments", atau "viral"
    (Viral Score). Tiap post: tanggal, channel, author, konten, link URL,
    sentiment, dan semua metrik. Untuk "post paling viral/rame", "konten apa
    yang paling banyak ditonton/dibagikan". Sajikan + analisis kenapa viral.
    """
    lim = max(1, min(int(limit) if limit else 10, 50))
    rows = db.top_posts(project_name, start_date or None, end_date or None,
                        channel or None, by or "engagement", lim)
    if rows is None:
        return {"found": False, "error": f"Campaign '{project_name}' tidak ditemukan.",
                "available_campaigns": _available_projects()}
    posts = []
    for r in rows:
        content = (r.get("content") or "")
        posts.append({
            "date": r["post_date"].strftime("%Y-%m-%d %H:%M") if r.get("post_date") else None,
            "channel": r.get("channel"), "author": r.get("author"),
            "sentiment": r.get("sentiment"), "url": r.get("url"),
            "content": content[:400],
            "engagement": _num_clean(r.get("engagement")),
            "likes": _num_clean(r.get("likes")), "comments": _num_clean(r.get("comments")),
            "shares": _num_clean(r.get("shares")), "views": _num_clean(r.get("views")),
            "replies": _num_clean(r.get("replies")), "retweets": _num_clean(r.get("retweets")),
            "viral_score": _num_clean(r.get("viral_score")),
        })
    return {"found": True, "project_name": project_name,
            "period": {"from": start_date or None, "to": end_date or None},
            "sorted_by": by or "engagement", "posts": posts}


@mcp.tool()
def top_media(project_name: str, start_date: str = "", end_date: str = "",
              keyword: str = "", limit: int = 10) -> dict:
    """
    Khusus ONLINE MEDIA: daftar media outlet (mis. Kompas, BabelNews) yang
    memberitakan, beserta AD VALUE per media dan jumlah artikelnya, diurut by
    ad value. Ad Value = nilai pemberitaan per media (BUKAN engagement; online
    media tidak punya engagement). `keyword` memfilter ke satu isu/topik
    tertentu (mis. "sumur bor") sehingga terlihat media mana yang paling banyak
    memberitakan isu itu & berapa ad value-nya. Sajikan sebagai ranking media.
    """
    rows = db.top_media(project_name, start_date or None, end_date or None,
                        keyword or None, max(1, min(int(limit) if limit else 10, 50)))
    if rows is None:
        return {"found": False, "error": f"Campaign '{project_name}' tidak ditemukan.",
                "available_campaigns": _available_projects()}
    media = [{
        "media_name": r["media"],
        "articles": r["articles"],
        "ad_value": _num_clean(r["ad_value"]),
        "pr_value": _num_clean(r["pr_value"]),
    } for r in rows]
    return {
        "found": True, "project_name": project_name,
        "period": {"from": start_date or None, "to": end_date or None},
        "keyword": keyword or None,
        "media": media,
        "note": ("Ad value adalah nilai pemberitaan per media outlet, bukan "
                 "engagement. Sajikan sebagai ranking media (mis. 'isu X paling "
                 "banyak diberitakan Kompas, ad value 25jt')."),
    }


@mcp.tool()
def list_campaigns() -> dict:
    """
    Tampilkan daftar semua campaign/klien yang tersedia di database Cogan.
    Berguna saat user belum tahu nama campaign-nya dan ingin memilih.
    """
    names = db.list_campaigns()
    return {"count": len(names), "campaigns": names}


@mcp.tool()
def ping_cogan() -> str:
    """Cek apakah Cogan MCP Server berhasil terhubung ke Claude."""
    return "Cogan is connected."


@mcp.tool()
def find_project(project_name: str) -> dict[str, Any]:
    """
    Cari project/client berdasarkan nama dan kembalikan info dasar datanya.
    """
    summary = db.campaign_summary(project_name)
    if summary is None:
        return {
            "found": False,
            "error": f"Project '{project_name}' tidak ditemukan.",
            "available_projects": _available_projects(),
        }

    agg = summary["agg"]
    date_from = agg.get("date_from")
    date_to = agg.get("date_to")

    return {
        "found": True,
        "project_id": _project_id(project_name),
        "project_name": project_name,
        "total_rows": int(agg.get("total_rows") or 0),
        "available_data_period": {
            "from": date_from.strftime("%Y-%m-%d") if date_from else None,
            "to": date_to.strftime("%Y-%m-%d") if date_to else None,
        },
        "channels_available": summary["channels"],
        "has_title_column": bool(agg.get("has_title")),
        "has_content_column": bool(agg.get("has_content")),
    }


@mcp.tool()
def get_project_wordcloud_guidance(project_name: str) -> dict[str, Any]:
    """Ambil guidance wordcloud khusus project."""
    guidance = _read_guidance(project_name)
    guidance["guidance_file_exists"] = _guidance_path(project_name).exists()
    return guidance


@mcp.tool()
def get_wordcloud_candidates(
    project_name: str,
    start_date: str = "",
    end_date: str = "",
    channels: str = "",
    candidate_pool_size: int = 200,
) -> dict[str, Any]:
    """
    Hitung kandidat term mentah dari Title + Content (frequency, engagement,
    sentiment per kandidat).

    candidate_pool_size adalah jumlah KANDIDAT MENTAH yang dikembalikan,
    BUKAN jumlah term final wordcloud. Ini harus jauh lebih besar dari
    jumlah term yang akhirnya dipakai, karena banyak kandidat akan dibuang
    saat penilaian kualitas (noise, generik, duplikasi). Default 200 cukup
    untuk data ratusan post; naikkan kalau project punya ribuan post.

    channels boleh kosong atau comma-separated, contoh: "Tiktok,Instagram".
    """
    candidates = _build_candidates(
        project_name=project_name,
        start_date=start_date or None,
        end_date=end_date or None,
        channels=channels or None,
        candidate_pool_size=candidate_pool_size,
    )
    return {
        "project_id": _project_id(project_name),
        "candidate_pool_size": candidate_pool_size,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


@mcp.tool()
def get_report_guide() -> str:
    """
    WAJIB dipanggil SEBELUM membuat report/competitive analysis/brand report
    apa pun. Membaca panduan `skills/skill_competitive_report.md` yang berisi
    struktur, prinsip narasi insight-led (gaya "EVO"), format output (PPTX dengan
    chart ter-embed, BUKAN HTML/CDN), tool data yang harus ditarik, scorecard
    benchmark yang jujur, dan catatan metodologi. Ikuti panduan ini agar report
    konsisten dan berkualitas tinggi.
    """
    path = SKILLS_DIR / "skill_competitive_report.md"
    if not path.exists():
        return (
            "PERINGATAN: skills/skill_competitive_report.md tidak ditemukan. "
            "Prinsip dasar: output PPTX (chart ter-embed, bukan CDN); tiap slide "
            "diawali kalimat insight 'so-what'; selalu bandingkan brand; dukung "
            "dengan contoh post asli + link; tutup dengan rekomendasi; baca konten "
            "asli via get_posts untuk menyimpulkan isu (bukan dari wordcloud)."
        )
    return path.read_text(encoding="utf-8-sig")


@mcp.tool()
def get_wordcloud_selection_guide() -> str:
    """
    Baca panduan cara Claude memilih term wordcloud.

    Tool ini membaca `skills/skill_wordcloud.md` supaya instruksi seleksi
    term benar-benar masuk ke konteks Claude, bukan hanya tersimpan sebagai
    file dokumen di disk.
    """
    path = SKILLS_DIR / "skill_wordcloud.md"
    if not path.exists():
        return (
            "PERINGATAN: file skills/skill_wordcloud.md tidak ditemukan. "
            "Gunakan kriteria umum: pilih term yang menjelaskan isu spesifik, "
            "bukan kata generik atau kata jurnalistik seperti fakta, temuan, "
            "mengungkap, dan mengejutkan."
        )
    return path.read_text(encoding="utf-8-sig")


@mcp.tool()
def prepare_wordcloud_context(
    project_name: str,
    start_date: str = "",
    end_date: str = "",
    channels: str = "",
    max_output_terms: int = 50,
    mode: str = "frequency",
) -> dict[str, Any]:
    """
    Siapkan semua bahan untuk Claude membuat wordcloud.

    Pakai tool ini saat user meminta sederhana seperti:
    "buat wordcloud AQUA periode 22-23 Okt by frequency".

    Tool ini TIDAK memilih term final. Tool ini mengembalikan KANDIDAT
    MENTAH dalam jumlah besar (candidate_pool_size, jauh lebih besar dari
    max_output_terms) supaya Claude punya cukup bahan untuk menilai dan
    menyaring. PENTING: max_output_terms adalah batas ATAS hasil akhir
    setelah penyaringan kualitas, BUKAN jumlah kandidat yang dikirim ke
    Claude. candidate_count yang besar bukan berarti semuanya harus dipakai
    â€” itu cuma bahan mentah untuk dinilai satu per satu.

    Tool ini mengembalikan:
    - selection_guide dari skills/skill_wordcloud.md,
    - info project,
    - guidance khusus project,
    - kandidat term mentah (candidate_pool_size item) + frequency/
      engagement/sentiment per kandidat.

    Setelah membaca hasil tool ini, Claude harus memilih selected_terms
    final berdasarkan selection_guide + guidance, membuang noise, lalu
    memanggil render_selected_wordcloud.

    mode: "frequency" atau "engagement".
    """
    mode = mode.strip().lower()
    if mode not in {"frequency", "engagement"}:
        mode = "frequency"

    # Kandidat mentah HARUS jauh lebih banyak dari target hasil akhir,
    # supaya ada cukup bahan untuk disaring. Jangan disamakan dengan
    # max_output_terms.
    candidate_pool_size = max(200, max_output_terms * 6)

    selection_guide = get_wordcloud_selection_guide()
    project_info = find_project(project_name)
    guidance = get_project_wordcloud_guidance(project_name)
    candidates = _build_candidates(
        project_name=project_name,
        start_date=start_date or None,
        end_date=end_date or None,
        channels=channels or None,
        candidate_pool_size=candidate_pool_size,
    )

    return {
        "selection_guide": selection_guide,
        "project": project_info,
        "guidance": guidance,
        "mode": mode,
        "max_output_terms": max_output_terms,
        "candidate_pool_size_used": candidate_pool_size,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "output_count_instruction": (
            f"Jumlah output mengikuti permintaan user sampai maksimal "
            f"{max_output_terms}. Jika user meminta {max_output_terms}, "
            f"usahakan mendekati angka itu dengan kandidat yang masih relevan. "
            f"Jangan berhenti di 8-10 hanya karena kandidat teratas sudah jelas. "
            f"Boleh kurang hanya jika sisa kandidat benar-benar noise/tidak relevan."
        ),
        "next_step_for_claude": (
            f"Di atas ada {len(candidates)} KANDIDAT MENTAH (bukan hasil "
            f"final). Baca selection_guide dan guidance, lalu nilai SETIAP "
            f"kandidat satu per satu â€” jangan langsung ambil N teratas "
            f"berdasarkan frequency/engagement mentah. Buang term generik/"
            f"noise, nama akun/media/URL/CTA, dan brand term yang tidak "
            f"perlu. Hasil akhir maksimal {max_output_terms} term, tapi "
            f"BOLEH lebih sedikit kalau memang cuma segitu yang lolos "
            f"penilaian kualitas â€” jangan dipaksa sampai pas "
            f"{max_output_terms}. Setelah itu panggil render_selected_wordcloud "
            f"dengan selected_terms final."
        ),
    }


@mcp.tool()
def render_selected_wordcloud(
    project_name: str,
    selected_terms: list[str],
    start_date: str = "",
    end_date: str = "",
    channels: str = "",
    mode: str = "frequency",
) -> dict[str, Any]:
    """
    Render wordcloud dari term final pilihan Claude.

    Claude memilih term berdasarkan guidance. Tool ini hanya:
    1. mencari post yang mengandung setiap term,
    2. menghitung frequency dan engagement,
    3. menentukan warna dari sentiment mayoritas,
    4. render PNG + CSV.

    mode: "frequency" atau "engagement".
    """
    mode = mode.strip().lower()
    if mode not in {"frequency", "engagement"}:
        mode = "frequency"

    stats, unmatched_terms = _stats_for_selected_terms(
        project_name=project_name,
        selected_terms=selected_terms,
        start_date=start_date or None,
        end_date=end_date or None,
        channels=channels or None,
    )
    if not stats:
        return {
            "success": False,
            "error": "Tidak ada selected_terms yang ditemukan di data.",
            "project_id": _project_id(project_name),
            "unmatched_terms": unmatched_terms,
        }

    project_id = _project_id(project_name)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix_bits = [project_id, "selected"]
    if start_date:
        suffix_bits.append(start_date)
    if end_date:
        suffix_bits.append(end_date)
    if channels:
        suffix_bits.append(re.sub(r"[^a-zA-Z0-9]+", "-", channels.strip()).strip("-"))
    suffix_bits.append(mode)
    suffix = "_".join(suffix_bits)

    png_path = OUTPUT_DIR / f"{suffix}_wordcloud.png"
    csv_path = OUTPUT_DIR / f"{suffix}_terms.csv"
    frequencies = {
        item["term"]: max(1, int(item[mode]))
        for item in stats
        if int(item[mode]) > 0
    }
    sentiment_by_term = {item["term"]: item["sentiment"] for item in stats}

    def color_func(word: str, **_: Any) -> str:
        return SENTIMENT_COLORS.get(sentiment_by_term.get(word, "neutral"), "#6b7280")

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
            fieldnames=["term", "frequency", "engagement", "sentiment", "example"],
        )
        writer.writeheader()
        writer.writerows(stats)

    result = {
        "success": True,
        "project_id": project_id,
        "mode": mode,
        "term_count": len(stats),
        "png_path": str(png_path),
        "csv_path": str(csv_path),
        "terms": stats,
        "unmatched_terms": unmatched_terms,
    }

    # Simpan ke histori supaya bisa ditelusuri & tidak generate ulang dari nol.
    try:
        db.save_output(
            campaign_name=project_id,
            kind="wordcloud",
            params={
                "start_date": start_date,
                "end_date": end_date,
                "channels": channels,
                "mode": mode,
                "selected_terms": selected_terms,
            },
            result={
                "term_count": len(stats),
                "png_path": str(png_path),
                "csv_path": str(csv_path),
                "download_url": (f"{_public_base_url()}/files/{png_path.name}"
                                 if _public_base_url() else ""),
                "csv_url": (f"{_public_base_url()}/files/{csv_path.name}"
                            if _public_base_url() else ""),
                "terms": stats,
            },
        )
    except Exception as exc:  # histori gagal tidak boleh menggagalkan render
        result["history_warning"] = f"Gagal menyimpan histori: {exc}"

    # Buat LINK unduhan publik ke file hasil. Connector "biasa" mengembalikan
    # teks, jadi cara paling andal menampilkan gambar ke user adalah lewat link
    # yang bisa dibuka di browser (bukan menempel gambar ke chat).
    base = _public_base_url()
    if base:
        result["download_url"] = f"{base}/files/{png_path.name}"
        result["csv_url"] = f"{base}/files/{csv_path.name}"
        result["note"] = (
            "Buka download_url untuk melihat/mengunduh gambar wordcloud (PNG). "
            "csv_url berisi daftar term dalam format CSV."
        )
    else:
        result["download_url"] = ""
        result["note"] = (
            "Link unduhan belum aktif: set environment variable PUBLIC_BASE_URL "
            "(atau pastikan RAILWAY_PUBLIC_DOMAIN tersedia) di server."
        )
    return result


@mcp.tool()
def get_recent_outputs(project_name: str = "", kind: str = "", limit: int = 10) -> dict[str, Any]:
    """
    Lihat histori hasil yang pernah digenerate (wordcloud, report, dll),
    tersimpan di database. Berguna untuk: cek apa yang sudah pernah dibuat
    untuk satu klien tanpa generate ulang.

    project_name & kind boleh kosong (artinya: semua). kind contohnya
    "wordcloud".
    """
    rows = db.list_outputs(
        campaign_name=project_name or None,
        kind=kind or None,
        limit=max(1, int(limit)),
    )
    for r in rows:
        if r.get("created_at") is not None:
            r["created_at"] = r["created_at"].isoformat()
    return {"count": len(rows), "outputs": rows}


if __name__ == "__main__":
    # Pastikan tabel ada saat server start (aman dijalankan berulang).
    try:
        db.init_db()
    except Exception as exc:
        print(f"[warning] init_db gagal: {exc}")

    # Pakai HTTP kalau dijalankan di cloud (Railway/dst akan set env var PORT
    # secara otomatis). Kalau dijalankan biasa di laptop (lewat Claude
    # Desktop config), tidak ada PORT, jadi tetap pakai stdio seperti biasa.
    # Jadi file ini SAMA untuk testing lokal maupun deploy cloud â€” tidak
    # perlu 2 versi server.py yang beda.
    port = os.environ.get("PORT")
    if port:
        mcp.run(transport="streamable-http")
    else:
        mcp.run()

