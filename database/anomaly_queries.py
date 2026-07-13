"""
anomaly_queries.py — data layer untuk anomaly engine.

VERSI 1.0

FILE INI TIDAK MENGUBAH db.py SAMA SEKALI.
Semua query di sini memakai ulang `_canonical_cte()` milik db.py, sehingga:
- dedup canonical tetap sama;
- definisi interactions per channel tetap sama;
- views tetap terpisah;
- scope (keywords / exclude_keywords / channels / date range) tetap konsisten.

Tidak ada perubahan schema. Tidak ada tabel baru.

Menyediakan 4 "frame" yang dikonsumsi anomaly.py:

    daily_frame()          -> 1 baris per hari, lengkap dengan top-1 post,
                              sentimen by-count DAN engagement-weighted
    author_daily_frame()   -> author x hari (untuk flood & new-author surge)
    duplicate_clusters()   -> klaster teks nyaris identik (untuk buzzer)
    term_daily_frame()     -> hitungan trigger term & noise term per hari

Plus konfigurasi term per project, disimpan di tabel `guidance` yang SUDAH ADA
(kolom JSONB), jadi tidak perlu tabel baru.
"""

from __future__ import annotations

from typing import Any, Iterable

from psycopg.rows import dict_row

from .db import (
    _canonical_cte,
    _clean_terms,
    get_guidance,
    get_pool,
    upsert_guidance,
)


# =====================================================================
# Konfigurasi term (disimpan di tabel guidance yang sudah ada)
# =====================================================================

GUIDANCE_KEY = "anomaly"

# Default trigger term untuk konteks media intelligence Indonesia.
#
# Ini kosakata yang menentukan RISK POSTURE, bukan volume. Kasus Aqua/KDM:
# sentimen agregat hijau (~55-57% positif) tapi ada ~30 artikel memuat
# BPKN / YLKI / DPR / audit / investigasi. Volumenya terlalu kecil untuk
# memicu spike apapun — tapi justru itu yang menentukan postur risiko.
DEFAULT_TRIGGER_TERMS = [
    # Regulator & lembaga
    "BPKN", "YLKI", "BPOM", "KPPU", "OJK", "Ombudsman", "Kominfo",
    "Kemenkes", "Kemenperin", "ESDM", "Kemendag", "BPKP", "BPK",
    # Politik & legislatif
    "DPR", "DPRD", "Komisi VI", "Komisi IX", "RDP", "interpelasi",
    "panggil", "dipanggil", "somasi",
    # Hukum & penegakan
    "gugatan", "class action", "tuntutan hukum", "laporan polisi",
    "kepolisian", "tersangka", "penyidikan", "pidana", "denda", "sanksi",
    "cabut izin", "pencabutan izin", "pelanggaran",
    # Investigasi & pengawasan
    "audit", "investigasi", "sidak", "inspeksi", "razia", "diperiksa",
    "temuan", "dugaan",
    # Krisis publik
    "boikot", "mogok", "unjuk rasa", "demo", "protes",
    "korban", "meninggal", "kecelakaan", "keracunan",
    "pencemaran", "limbah", "kontaminasi", "recall", "penarikan produk",
]


def get_anomaly_config(campaign_name: str) -> dict[str, Any]:
    """
    Ambil konfigurasi anomaly untuk satu project.

    Dibaca dari tabel `guidance` (JSONB), key "anomaly". Tidak ada tabel baru.
    """
    guidance = get_guidance(campaign_name) or {}
    config = guidance.get(GUIDANCE_KEY) or {}

    trigger = _clean_terms(config.get("trigger_terms")) or list(DEFAULT_TRIGGER_TERMS)
    noise = _clean_terms(config.get("noise_terms"))

    return {
        "project_name": campaign_name,
        "trigger_terms": trigger,
        "noise_terms": noise,
        "trigger_source": "custom" if config.get("trigger_terms") else "default",
        "configured": bool(config),
    }


def set_anomaly_config(
    campaign_name: str,
    trigger_terms: str | Iterable[str] | None = None,
    noise_terms: str | Iterable[str] | None = None,
) -> dict[str, Any]:
    """
    Simpan trigger/noise term untuk satu project.

    Noise term ini yang menyelamatkan kasus nyata:
    - Aqua: "AQUA Elektronik", "badminton" (scope ~90% noise)
    - Bluebird: "ASTS", "satelit", "AST SpaceMobile" (menggelembungkan positif)
    """
    guidance = get_guidance(campaign_name) or {}
    config = dict(guidance.get(GUIDANCE_KEY) or {})

    if trigger_terms is not None:
        config["trigger_terms"] = _clean_terms(trigger_terms)
    if noise_terms is not None:
        config["noise_terms"] = _clean_terms(noise_terms)

    guidance[GUIDANCE_KEY] = config
    upsert_guidance(campaign_name, guidance)
    return get_anomaly_config(campaign_name)


# =====================================================================
# Helper
# =====================================================================

_TEXT_EXPR = "(coalesce(mp.title, '') || ' ' || coalesce(mp.content, ''))"

# Normalisasi teks untuk deteksi duplikat:
# buang URL, mention, hashtag, tanda baca; rapatkan spasi; huruf kecil semua.
_NORM_TEXT = f"""
    btrim(
        regexp_replace(
            regexp_replace(
                regexp_replace(
                    lower({_TEXT_EXPR}),
                    '(https?://[^[:space:]]+|@[[:alnum:]_]+|#[[:alnum:]_]+)', ' ', 'g'
                ),
                '[^a-z0-9[:space:]]', ' ', 'g'
            ),
            '[[:space:]]+', ' ', 'g'
        )
    )
"""


def _run(sql: str, params: list[Any]) -> list[dict[str, Any]]:
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def _scope(
    campaign_name: str,
    start_date: str | None,
    end_date: str | None,
    channel: str | None,
    keywords: str | Iterable[str] | None,
    exclude_keywords: str | Iterable[str] | None,
    match_mode: str,
) -> tuple[str, list[Any]] | tuple[None, None]:
    return _canonical_cte(
        campaign_name,
        start_date,
        end_date,
        [channel] if channel else None,
        keywords,
        exclude_keywords,
        match_mode,
    )


# =====================================================================
# FRAME 1 — daily
# =====================================================================

def daily_frame(
    campaign_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    channel: str | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
) -> list[dict[str, Any]] | None:
    """
    Satu baris per hari, jauh lebih kaya daripada timeline().

    Tambahan penting dibanding timeline():
    - top1_interactions + top1_canonical_key  -> deteksi concentration
    - eng_positive / eng_negative             -> sentimen ENGAGEMENT-WEIGHTED
    - unclassified_posts                      -> integritas denominator sentimen
    - distinct_authors                        -> konteks aktor

    eng_positive/eng_negative inilah yang memungkinkan deteksi divergence:
    sentimen by-count hijau tapi yang viral justru negatif (atau sebaliknya).
    """
    cte, params = _scope(
        campaign_name, start_date, end_date, channel,
        keywords, exclude_keywords, match_mode,
    )
    if cte is None:
        return None

    sql = cte + """
        , daily AS (
            SELECT
                mp.post_date::date AS day,
                count(*) AS posts,
                sum(coalesce(mp.interactions, 0)) AS interactions,
                sum(CASE WHEN mp.has_views THEN mp.views ELSE 0 END) AS views,

                count(*) FILTER (WHERE mp.sentiment_norm = 'positive') AS positive_posts,
                count(*) FILTER (WHERE mp.sentiment_norm = 'negative') AS negative_posts,
                count(*) FILTER (WHERE mp.sentiment_norm = 'neutral')  AS neutral_posts,
                count(*) FILTER (
                    WHERE mp.sentiment_norm IS NULL
                       OR mp.sentiment_norm NOT IN ('positive', 'negative', 'neutral')
                ) AS unclassified_posts,

                -- Sentimen ditimbang engagement. Ini yang membedakan
                -- "banyak orang marah" dari "satu orang marah tapi viral".
                sum(coalesce(mp.interactions, 0))
                    FILTER (WHERE mp.sentiment_norm = 'positive') AS eng_positive,
                sum(coalesce(mp.interactions, 0))
                    FILTER (WHERE mp.sentiment_norm = 'negative') AS eng_negative,
                sum(coalesce(mp.interactions, 0))
                    FILTER (WHERE mp.sentiment_norm = 'neutral')  AS eng_neutral,

                count(DISTINCT nullif(btrim(coalesce(mp.author, '')), '')) AS distinct_authors,
                count(*) FILTER (WHERE mp.interactions_available) AS interactions_available_posts,
                count(*) FILTER (WHERE mp.has_views) AS views_available_posts
            FROM metric_posts mp
            GROUP BY day
        ),
        top_post AS (
            SELECT DISTINCT ON (mp.post_date::date)
                mp.post_date::date AS day,
                coalesce(mp.interactions, 0) AS top1_interactions,
                mp.canonical_key AS top1_canonical_key,
                left(coalesce(mp.title, mp.content, ''), 160) AS top1_title,
                mp.author AS top1_author,
                mp.sentiment_norm AS top1_sentiment
            FROM metric_posts mp
            ORDER BY
                mp.post_date::date,
                coalesce(mp.interactions, 0) DESC,
                mp.id DESC
        )
        SELECT
            d.day,
            d.posts,
            d.interactions,
            d.views,
            d.positive_posts,
            d.negative_posts,
            d.neutral_posts,
            d.unclassified_posts,
            (d.positive_posts + d.negative_posts + d.neutral_posts) AS classified_posts,
            coalesce(d.eng_positive, 0) AS eng_positive,
            coalesce(d.eng_negative, 0) AS eng_negative,
            coalesce(d.eng_neutral, 0)  AS eng_neutral,
            d.distinct_authors,
            d.interactions_available_posts,
            d.views_available_posts,
            coalesce(t.top1_interactions, 0) AS top1_interactions,
            t.top1_canonical_key,
            t.top1_title,
            t.top1_author,
            t.top1_sentiment
        FROM daily d
        LEFT JOIN top_post t ON t.day = d.day
        ORDER BY d.day
    """

    rows = _run(sql, params)
    return [_normalise_daily(row) for row in rows]


def _normalise_daily(row: dict[str, Any]) -> dict[str, Any]:
    """Bentuk yang dipahami anomaly.py (key 'date', angka Python biasa)."""
    day = row.get("day")
    return {
        "date": day.strftime("%Y-%m-%d") if day else None,
        "posts": int(row.get("posts") or 0),
        "interactions": float(row.get("interactions") or 0),
        "views": float(row.get("views") or 0),
        "positive_posts": int(row.get("positive_posts") or 0),
        "negative_posts": int(row.get("negative_posts") or 0),
        "neutral_posts": int(row.get("neutral_posts") or 0),
        "unclassified_posts": int(row.get("unclassified_posts") or 0),
        "classified_posts": int(row.get("classified_posts") or 0),
        "eng_positive": float(row.get("eng_positive") or 0),
        "eng_negative": float(row.get("eng_negative") or 0),
        "eng_neutral": float(row.get("eng_neutral") or 0),
        "distinct_authors": int(row.get("distinct_authors") or 0),
        "interactions_available_posts": int(row.get("interactions_available_posts") or 0),
        "views_available_posts": int(row.get("views_available_posts") or 0),
        "top1_interactions": float(row.get("top1_interactions") or 0),
        "top1_canonical_key": row.get("top1_canonical_key"),
        "top1_title": row.get("top1_title"),
        "top1_author": row.get("top1_author"),
        "top1_sentiment": row.get("top1_sentiment"),
    }


# =====================================================================
# FRAME 2 — author x hari
# =====================================================================

def author_daily_frame(
    campaign_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    channel: str | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
    top_per_day: int = 25,
) -> list[dict[str, Any]] | None:
    """
    Top author per hari.

    PENTING: setiap baris membawa `day_total_posts` dan `day_total_interactions`.
    Tanpa itu, deteksi flood akan salah hitung ketika daftar author dipotong
    di top-N (share dihitung terhadap total yang terpotong, bukan total asli).
    """
    cte, params = _scope(
        campaign_name, start_date, end_date, channel,
        keywords, exclude_keywords, match_mode,
    )
    if cte is None:
        return None

    sql = cte + """
        , by_author AS (
            SELECT
                mp.post_date::date AS day,
                nullif(btrim(coalesce(mp.author, '')), '') AS author,
                count(*) AS posts,
                sum(coalesce(mp.interactions, 0)) AS interactions,
                (array_agg(
                    mp.canonical_key
                    ORDER BY coalesce(mp.interactions, 0) DESC, mp.id DESC
                ))[1] AS sample_canonical_key
            FROM metric_posts mp
            WHERE nullif(btrim(coalesce(mp.author, '')), '') IS NOT NULL
            GROUP BY day, author
        ),
        day_totals AS (
            SELECT
                mp.post_date::date AS day,
                count(*) AS day_total_posts,
                sum(coalesce(mp.interactions, 0)) AS day_total_interactions
            FROM metric_posts mp
            GROUP BY day
        ),
        ranked AS (
            SELECT
                a.*,
                row_number() OVER (
                    PARTITION BY a.day
                    ORDER BY a.posts DESC, a.interactions DESC
                ) AS rank_by_posts,
                row_number() OVER (
                    PARTITION BY a.day
                    ORDER BY a.interactions DESC, a.posts DESC
                ) AS rank_by_interactions
            FROM by_author a
        )
        SELECT
            r.day,
            r.author,
            r.posts,
            r.interactions,
            r.sample_canonical_key,
            t.day_total_posts,
            t.day_total_interactions
        FROM ranked r
        JOIN day_totals t ON t.day = r.day
        WHERE r.rank_by_posts <= %s OR r.rank_by_interactions <= %s
        ORDER BY r.day, r.posts DESC
    """

    rows = _run(sql, params + [int(top_per_day), int(top_per_day)])

    return [
        {
            "date": row["day"].strftime("%Y-%m-%d") if row.get("day") else None,
            "author": row.get("author"),
            "posts": int(row.get("posts") or 0),
            "interactions": float(row.get("interactions") or 0),
            "sample_canonical_key": row.get("sample_canonical_key"),
            "day_total_posts": int(row.get("day_total_posts") or 0),
            "day_total_interactions": float(row.get("day_total_interactions") or 0),
        }
        for row in rows
    ]


# =====================================================================
# FRAME 3 — klaster duplikat (buzzer / koordinasi)
# =====================================================================

def duplicate_clusters(
    campaign_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    channel: str | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
    min_cluster_size: int = 5,
    min_distinct_authors: int = 3,
    min_words: int = 6,
    limit: int = 40,
) -> list[dict[str, Any]] | None:
    """
    Cari teks yang nyaris identik, diposting banyak akun berbeda.

    METODE: bag-of-words hash.
    Teks dinormalisasi (buang URL/mention/hashtag/tanda baca), lalu diambil
    himpunan kata unik >3 huruf yang diurutkan, lalu di-hash.

    Kenapa bag-of-words dan bukan hash teks mentah:
    buzzer sering mengacak urutan kalimat atau menambah emoji/tagar supaya
    lolos filter duplikat. Bag-of-words tetap menangkapnya.

    KETERBATASAN (harus jujur):
    - Parafrase berat (kata diganti sinonim) tidak tertangkap.
    - Kolom `posts` tidak punya follower count / umur akun, jadi ini
      TIDAK BISA memastikan bot. Ini indikasi koordinasi, bukan vonis.

    `post_date` bertipe timestamptz, jadi span menit betul-betul akurat.
    """
    cte, params = _scope(
        campaign_name, start_date, end_date, channel,
        keywords, exclude_keywords, match_mode,
    )
    if cte is None:
        return None

    sql = cte + f"""
        , normalised AS (
            SELECT
                mp.id,
                mp.canonical_key,
                mp.post_date,
                mp.author,
                coalesce(mp.interactions, 0) AS interactions,
                {_NORM_TEXT} AS norm_text
            FROM metric_posts mp
        ),
        fingerprinted AS (
            SELECT
                n.*,
                ARRAY(
                    SELECT DISTINCT word
                    FROM unnest(string_to_array(n.norm_text, ' ')) AS word
                    WHERE length(word) > 3
                    ORDER BY word
                ) AS bag
            FROM normalised n
            WHERE n.norm_text <> ''
        ),
        hashed AS (
            SELECT
                f.*,
                md5(array_to_string(f.bag, ' ')) AS text_hash,
                cardinality(f.bag) AS word_count
            FROM fingerprinted f
            WHERE cardinality(f.bag) >= %s
        ),
        clusters AS (
            SELECT
                h.post_date::date AS day,
                h.text_hash,
                count(*) AS cluster_size,
                count(DISTINCT nullif(btrim(coalesce(h.author, '')), '')) AS distinct_authors,
                EXTRACT(
                    EPOCH FROM (max(h.post_date) - min(h.post_date))
                ) / 60.0 AS span_minutes,
                (array_agg(h.canonical_key ORDER BY h.post_date))[1:5] AS sample_canonical_keys,
                (array_agg(h.norm_text ORDER BY h.post_date))[1] AS sample_text,
                (array_agg(
                    nullif(btrim(coalesce(h.author, '')), '')
                    ORDER BY h.post_date
                ))[1:5] AS sample_authors
            FROM hashed h
            GROUP BY day, h.text_hash
        )
        SELECT *
        FROM clusters
        WHERE cluster_size >= %s
          AND distinct_authors >= %s
        ORDER BY cluster_size DESC, distinct_authors DESC
        LIMIT %s
    """

    rows = _run(
        sql,
        params + [
            int(min_words),
            int(min_cluster_size),
            int(min_distinct_authors),
            int(limit),
        ],
    )

    return [
        {
            "date": row["day"].strftime("%Y-%m-%d") if row.get("day") else None,
            "text_hash": row.get("text_hash"),
            "cluster_size": int(row.get("cluster_size") or 0),
            "distinct_authors": int(row.get("distinct_authors") or 0),
            "span_minutes": float(row.get("span_minutes") or 0),
            "sample_canonical_keys": list(row.get("sample_canonical_keys") or []),
            "sample_authors": list(row.get("sample_authors") or []),
            "sample_text": row.get("sample_text"),
        }
        for row in rows
    ]


# =====================================================================
# FRAME 4 — trigger term & noise term per hari
# =====================================================================

def term_daily_frame(
    campaign_name: str,
    trigger_terms: Iterable[str] | None = None,
    noise_terms: Iterable[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    channel: str | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
) -> list[dict[str, Any]] | None:
    """
    Hitung post yang memuat trigger term (risiko) dan noise term (kontaminasi).

    Pencocokan memakai position(), BUKAN ILIKE, supaya term yang kebetulan
    mengandung '%' atau '_' tidak diperlakukan sebagai wildcard.

    Satu baris per (hari, term_group), lengkap dengan:
    - posts          : jumlah post unik yang cocok
    - total_posts    : total post hari itu (untuk menghitung share noise)
    - matched_terms  : term mana saja yang benar-benar muncul
    - sample_canonical_keys : bukti, langsung bisa di-drill get_posts()
    """
    cte, params = _scope(
        campaign_name, start_date, end_date, channel,
        keywords, exclude_keywords, match_mode,
    )
    if cte is None:
        return None

    groups: list[tuple[str, list[str]]] = []
    trigger = _clean_terms(trigger_terms)
    noise = _clean_terms(noise_terms)
    if trigger:
        groups.append(("trigger", trigger))
    if noise:
        groups.append(("noise", noise))

    if not groups:
        return []

    results: list[dict[str, Any]] = []

    for group_name, terms in groups:
        sql = cte + f"""
            , totals AS (
                SELECT
                    mp.post_date::date AS day,
                    count(*) AS total_posts
                FROM metric_posts mp
                GROUP BY day
            ),
            matched AS (
                SELECT DISTINCT
                    mp.post_date::date AS day,
                    mp.id,
                    mp.canonical_key,
                    coalesce(mp.interactions, 0) AS interactions,
                    t.term
                FROM metric_posts mp
                JOIN LATERAL unnest(%s::text[]) AS t(term)
                    ON position(lower(t.term) in lower({_TEXT_EXPR})) > 0
            ),
            per_day AS (
                SELECT
                    m.day,
                    count(DISTINCT m.id) AS posts,
                    array_agg(DISTINCT m.term) AS matched_terms
                FROM matched m
                GROUP BY m.day
            ),
            unique_posts AS (
                SELECT DISTINCT day, id, canonical_key, interactions
                FROM matched
            ),
            ranked AS (
                SELECT
                    u.*,
                    row_number() OVER (
                        PARTITION BY u.day
                        ORDER BY u.interactions DESC, u.id DESC
                    ) AS rn
                FROM unique_posts u
            ),
            samples AS (
                SELECT
                    r.day,
                    array_agg(r.canonical_key ORDER BY r.rn) AS sample_canonical_keys
                FROM ranked r
                WHERE r.rn <= 5
                GROUP BY r.day
            )
            SELECT
                p.day,
                p.posts,
                p.matched_terms,
                s.sample_canonical_keys,
                t.total_posts
            FROM per_day p
            LEFT JOIN samples s ON s.day = p.day
            LEFT JOIN totals  t ON t.day = p.day
            ORDER BY p.day
        """

        rows = _run(sql, params + [terms])

        for row in rows:
            results.append(
                {
                    "date": row["day"].strftime("%Y-%m-%d") if row.get("day") else None,
                    "term_group": group_name,
                    "posts": int(row.get("posts") or 0),
                    "total_posts": int(row.get("total_posts") or 0),
                    "matched_terms": list(row.get("matched_terms") or []),
                    "sample_canonical_keys": list(row.get("sample_canonical_keys") or []),
                }
            )

    return results


# =====================================================================
# Pengumpul semua frame
# =====================================================================

def collect_frames(
    campaign_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    channel: str | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
    include_actors: bool = True,
    include_terms: bool = True,
) -> dict[str, Any] | None:
    """
    Tarik seluruh frame sekali jalan untuk satu project.

    Return None bila campaign tidak ditemukan, supaya server.py bisa
    mengembalikan pesan error yang konsisten dengan tool lain.
    """
    daily = daily_frame(
        campaign_name, start_date, end_date, channel,
        keywords, exclude_keywords, match_mode,
    )
    if daily is None:
        return None

    config = get_anomaly_config(campaign_name)

    frames: dict[str, Any] = {
        "daily": daily,
        "author_daily": [],
        "duplicate_clusters": [],
        "term_daily": [],
        "config": config,
    }

    if include_actors:
        frames["author_daily"] = author_daily_frame(
            campaign_name, start_date, end_date, channel,
            keywords, exclude_keywords, match_mode,
        ) or []
        frames["duplicate_clusters"] = duplicate_clusters(
            campaign_name, start_date, end_date, channel,
            keywords, exclude_keywords, match_mode,
        ) or []

    if include_terms:
        frames["term_daily"] = term_daily_frame(
            campaign_name,
            trigger_terms=config["trigger_terms"],
            noise_terms=config["noise_terms"],
            start_date=start_date,
            end_date=end_date,
            channel=channel,
            keywords=keywords,
            exclude_keywords=exclude_keywords,
            match_mode=match_mode,
        ) or []

    return frames
