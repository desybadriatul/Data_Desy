"""
db.py — satu-satunya pintu ke database Cogan.

VERSI 3.1 — metric-safe reporting layer + readiness guardrails

Perubahan utama:
1. Semua analitik memakai canonical post layer:
   - satu URL = satu post per campaign;
   - jika URL duplikat, dipilih row dengan source engagement tertinggi,
     lalu timestamp terbaru, lalu ID terbaru.
2. Interactions dihitung per channel:
   - Instagram: Likes + Comments
   - Facebook: Likes + Comments + Shares
   - YouTube: Likes + Comments
   - TikTok: Likes + Comments + Shares
   - X/Twitter: Likes + Replies + Retweets
3. Views dipisahkan dari interactions.
4. Kolom sumber lama `posts.engagement` hanya dipakai sebagai:
   - prioritas memilih row duplikat;
   - diagnostic/source metric;
   - BUKAN KPI report client-facing.
5. Semua agregasi mendukung scope issue-only:
   keywords, exclude_keywords, match_mode, channels, dan date range.
6. Coverage dihitung dari canonical unique posts, bukan raw rows.

CATATAN PENTING:
- File ini perlu dipakai bersama server.py versi 3.1 yang memakai field
  `interactions`, `views`, `source_engagement`, dan metric readiness guardrail.
- Jangan deploy hanya db.py ini tanpa mengganti server.py pasangannya.
"""

from __future__ import annotations

import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


BASE_DIR = Path(__file__).parent
SCHEMA_PATH = BASE_DIR / "schema.sql"

_pool: ConnectionPool | None = None


# ---------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------
def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError(
            "DATABASE_URL belum di-set. Lihat docs/SETUP_DATABASE_STEPS.md."
        )
    if dsn.startswith("postgres://"):
        dsn = "postgresql://" + dsn[len("postgres://") :]
    return dsn


def get_pool() -> ConnectionPool:
    """Sekumpulan koneksi siap pakai supaya banyak request bersamaan aman."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool(conninfo=_dsn(), min_size=1, max_size=10, open=True)
    return _pool


def init_db() -> None:
    """Buat semua tabel kalau belum ada. Aman diulang."""
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_pool().connection() as conn:
        conn.execute(schema)
        conn.commit()


# ---------------------------------------------------------------------
# Normalisasi umum
# ---------------------------------------------------------------------
def _norm(value: str) -> str:
    return " ".join(str(value).strip().lower().split())


def _clean_terms(values: str | Iterable[str] | None) -> list[str]:
    """Normalisasi input keyword/channels menjadi list unik tanpa string kosong."""
    if values is None:
        return []

    if isinstance(values, str):
        raw_items = values.split(",")
    else:
        raw_items = list(values)

    result: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        cleaned = str(item).strip()
        key = cleaned.lower()
        if cleaned and key not in seen:
            result.append(cleaned)
            seen.add(key)
    return result


def _channel_label(value: str | None) -> str:
    """
    Normalisasi nama channel untuk aturan metrik.

    Nilai ini hanya dipakai untuk kalkulasi metric layer. Nama channel asli
    tetap disimpan dan dikembalikan ke client.
    """
    raw = _norm(value or "")
    aliases = {
        "instagram": "instagram",
        "ig": "instagram",
        "instagram reels": "instagram",
        "facebook": "facebook",
        "fb": "facebook",
        "youtube": "youtube",
        "yt": "youtube",
        "tiktok": "tiktok",
        "tik tok": "tiktok",
        "twitter": "x",
        "x": "x",
        "twitter/x": "x",
        "x/twitter": "x",
        "online media": "online_media",
        "online": "online_media",
        "news": "online_media",
        "media online": "online_media",
        "forum": "forum",
    }
    return aliases.get(raw, raw or "unknown")


def _channel_norm_sql(alias: str = "p") -> str:
    """
    SQL setara _channel_label().

    Jangan ubah mapping di sini tanpa juga mengubah _channel_label().
    """
    return f"""
        CASE
            WHEN lower(trim(coalesce({alias}.channel, ''))) IN
                 ('instagram', 'ig', 'instagram reels') THEN 'instagram'
            WHEN lower(trim(coalesce({alias}.channel, ''))) IN
                 ('facebook', 'fb') THEN 'facebook'
            WHEN lower(trim(coalesce({alias}.channel, ''))) IN
                 ('youtube', 'yt') THEN 'youtube'
            WHEN lower(trim(coalesce({alias}.channel, ''))) IN
                 ('tiktok', 'tik tok') THEN 'tiktok'
            WHEN lower(trim(coalesce({alias}.channel, ''))) IN
                 ('twitter', 'x', 'twitter/x', 'x/twitter') THEN 'x'
            WHEN lower(trim(coalesce({alias}.channel, ''))) IN
                 ('online media', 'online', 'news', 'media online') THEN 'online_media'
            WHEN lower(trim(coalesce({alias}.channel, ''))) = '' THEN 'unknown'
            ELSE lower(trim(coalesce({alias}.channel, '')))
        END
    """


# ---------------------------------------------------------------------
# Campaigns (= klien)
# ---------------------------------------------------------------------
def list_campaigns() -> list[str]:
    with get_pool().connection() as conn:
        rows = conn.execute("SELECT name FROM campaigns ORDER BY name").fetchall()
    return [r[0] for r in rows]


def get_campaign_id(name: str | None) -> int | None:
    if not name:
        return None
    with get_pool().connection() as conn:
        row = conn.execute(
            "SELECT id FROM campaigns WHERE name_norm = %s",
            (_norm(name),),
        ).fetchone()
    return row[0] if row else None


def ensure_campaigns(names: list[str]) -> dict[str, int]:
    """Pastikan tiap nama campaign ada; kembalikan peta name_norm -> id."""
    result: dict[str, int] = {}
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            for name in names:
                normalized = _norm(name)
                if not normalized or normalized in result:
                    continue
                cur.execute(
                    """
                    INSERT INTO campaigns (name, name_norm)
                    VALUES (%s, %s)
                    ON CONFLICT (name_norm)
                    DO UPDATE SET name = campaigns.name
                    RETURNING id
                    """,
                    (str(name).strip(), normalized),
                )
                result[normalized] = cur.fetchone()[0]
        conn.commit()
    return result


# ---------------------------------------------------------------------
# Raw numeric / availability helpers
# ---------------------------------------------------------------------
# Canonical header is always first. Aliases are fallback only, so current Sonar
# exports with Likes / Comments / Shares / Replies / Retweets / Views continue
# to behave exactly as expected.
RAW_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "Likes": ("Likes", "Like", "Like Count", "Likes Count"),
    "Comments": ("Comments", "Comment", "Comment Count", "Comments Count"),
    "Shares": ("Shares", "Share", "Share Count", "Shares Count"),
    "Replies": ("Replies", "Reply", "Reply Count", "Replies Count"),
    "Retweets": (
        "Retweets",
        "Retweet",
        "Retweet Count",
        "Retweets Count",
        "Reposts",
        "Repost",
        "Repost Count",
    ),
    "Views": (
        "Views",
        "View",
        "View Count",
        "Video Views",
        "Video View Count",
        "Plays",
        "Video Plays",
    ),
    "Engagement": ("Engagement", "Total Engagement", "Engagements"),
    "Buzz": ("Buzz", "Total Buzz"),
    "Ad Value": ("Ad Value", "AdValue", "Advertising Value"),
    "PR Value": ("PR Value", "PRValue"),
    "Viral Score": ("Viral Score", "ViralScore"),
}


def _raw_field_aliases(field: str) -> tuple[str, ...]:
    """Return canonical raw header followed by approved fallback aliases."""
    return RAW_FIELD_ALIASES.get(field, (field,))


def _sql_literal(value: str) -> str:
    """Escape a constant used only as a JSONB key inside generated SQL."""
    return str(value).replace("'", "''")


def _raw_text(field: str, alias: str = "p") -> str:
    """
    Return the first non-empty raw value from canonical header / fallback aliases.

    This is intentionally a SQL expression, not a parsed number. It is used by
    `_raw_num`, `_raw_has`, and metric readiness diagnostics.
    """
    candidates = [
        f"NULLIF(btrim({alias}.raw->>'{_sql_literal(header)}'), '')"
        for header in _raw_field_aliases(field)
    ]
    return "COALESCE(" + ", ".join(candidates) + ")"


def _raw_num(field: str, alias: str = "p") -> str:
    """
    Parse raw JSONB numeric values safely.

    Supported examples:
    - 1,250      -> 1250
    - 12.5K      -> 12500
    - 1.2M       -> 1200000
    - 1,2M       -> 1200000
    - 1.234,56   -> 1234.56
    - blank / - / N/A -> 0

    Availability is evaluated separately by `_raw_has`, so numeric zero remains
    valid data while blank/N/A values are not treated as available.
    """
    raw_text = _raw_text(field, alias)
    compact = (
        f"regexp_replace(lower(trim(coalesce({raw_text}, ''))), "
        r"'\s+', '', 'g')"
    )
    numeric_token = (
        f"regexp_replace({compact}, '[^0-9,.-]', '', 'g')"
    )

    normalized_number = f"""
        CASE
            -- 1,234.56 -> 1234.56
            WHEN {numeric_token} ~ '^-?[0-9]{{1,3}}(,[0-9]{{3}})+([.][0-9]+)?$'
                THEN replace({numeric_token}, ',', '')

            -- 1.234,56 -> 1234.56
            WHEN {numeric_token} ~ '^-?[0-9]{{1,3}}([.][0-9]{{3}})+(,[0-9]+)?$'
                THEN replace(replace({numeric_token}, '.', ''), ',', '.')

            -- 1,2M -> 1.2M
            WHEN {compact} ~ '[kmb]$'
                 AND {numeric_token} ~ '^-?[0-9]+,[0-9]+$'
                THEN replace({numeric_token}, ',', '.')

            -- 1,250 -> 1250
            WHEN {numeric_token} ~ '^-?[0-9]+,[0-9]{{3}}$'
                THEN replace({numeric_token}, ',', '')

            -- 1.234 -> 1234 when there is no K/M/B suffix
            WHEN {compact} !~ '[kmb]$'
                 AND {numeric_token} ~ '^-?[0-9]+[.][0-9]{{3}}$'
                THEN replace({numeric_token}, '.', '')

            -- 12,5 -> 12.5
            WHEN {numeric_token} ~ '^-?[0-9]+,[0-9]+$'
                THEN replace({numeric_token}, ',', '.')

            ELSE {numeric_token}
        END
    """

    multiplier = f"""
        CASE
            WHEN {compact} ~ 'k$' THEN 1000::numeric
            WHEN {compact} ~ 'm$' THEN 1000000::numeric
            WHEN {compact} ~ 'b$' THEN 1000000000::numeric
            ELSE 1::numeric
        END
    """

    return f"""
        CASE
            WHEN {raw_text} IS NULL THEN 0::numeric
            WHEN ({normalized_number}) ~ '^-?[0-9]+([.][0-9]+)?$'
                THEN ({normalized_number})::numeric * ({multiplier})
            ELSE 0::numeric
        END
    """


def _raw_has(field: str, alias: str = "p") -> str:
    """
    True only when a raw value is non-empty and contains at least one digit.

    This keeps "0" as available data, while blank, "-", and "N/A" remain
    unavailable. It prevents availability coverage from silently becoming 100%.
    """
    raw_text = _raw_text(field, alias)
    return (
        f"({raw_text} IS NOT NULL "
        f"AND regexp_replace(lower(trim({raw_text})), '[^0-9]', '', 'g') <> '')"
    )


def _raw_has_header(field: str, alias: str = "p") -> str:
    """True when any configured canonical/fallback raw header exists."""
    checks = [
        f"coalesce({alias}.raw ? '{_sql_literal(header)}', false)"
        for header in _raw_field_aliases(field)
    ]
    return "(" + " OR ".join(checks) + ")"


def _canonical_key_sql(alias: str = "p") -> str:
    """
    Dedup key per campaign.

    Prioritas:
    - URL normalisasi bila tersedia;
    - ID post bila URL kosong agar post tanpa URL tidak disatukan paksa.
    """
    return (
        f"CASE WHEN nullif(trim(coalesce({alias}.url, '')), '') IS NOT NULL "
        f"THEN 'url:' || lower(trim({alias}.url)) "
        f"ELSE 'id:' || {alias}.id::text END"
    )


# ---------------------------------------------------------------------
# Scope builder
# ---------------------------------------------------------------------
def _scope_filters(
    campaign_id: int,
    start_date: str | None = None,
    end_date: str | None = None,
    channels: str | Iterable[str] | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
    post_alias: str = "p",
    campaign_alias: str = "pc",
) -> tuple[list[str], list[Any]]:
    """
    Bangun filter scope yang dipakai seluruh query analytics.

    - keywords + match_mode='any': post lolos bila mengandung salah satu keyword.
    - keywords + match_mode='all': post harus mengandung seluruh keyword.
    - exclude_keywords: post yang memuat salah satu keyword dikeluarkan.
    """
    clauses = [f"{campaign_alias}.campaign_id = %s"]
    params: list[Any] = [campaign_id]

    if start_date:
        clauses.append(f"{post_alias}.post_date >= %s::date")
        params.append(start_date)

    if end_date:
        clauses.append(f"{post_alias}.post_date < (%s::date + interval '1 day')")
        params.append(end_date)

    normalized_channels = sorted({_channel_label(value) for value in _clean_terms(channels)})
    if normalized_channels:
        clauses.append(f"{_channel_norm_sql(post_alias)} = ANY(%s)")
        params.append(normalized_channels)

    text_expr = (
        f"(coalesce({post_alias}.title, '') || ' ' || "
        f"coalesce({post_alias}.content, ''))"
    )

    clean_keywords = _clean_terms(keywords)
    if clean_keywords:
        predicate = []
        for keyword in clean_keywords:
            predicate.append(f"{text_expr} ILIKE %s")
            params.append(f"%{keyword}%")

        mode = (match_mode or "any").strip().lower()
        joiner = " AND " if mode == "all" else " OR "
        clauses.append("(" + joiner.join(predicate) + ")")

    clean_excludes = _clean_terms(exclude_keywords)
    if clean_excludes:
        excluded_predicate = []
        for keyword in clean_excludes:
            excluded_predicate.append(f"{text_expr} ILIKE %s")
            params.append(f"%{keyword}%")
        clauses.append("NOT (" + " OR ".join(excluded_predicate) + ")")

    return clauses, params


def _canonical_cte(
    campaign_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    channels: str | Iterable[str] | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
) -> tuple[str, list[Any]] | tuple[None, None]:
    """
    CTE standar untuk seluruh query report.

    `metric_posts` adalah satu-satunya tabel virtual yang boleh dipakai query
    analitik. Semua agregasi report harus dimulai dari sini agar:
    - dedup konsisten;
    - interactions konsisten per channel;
    - views terpisah;
    - availability/coverage dapat dihitung.
    """
    campaign_id = get_campaign_id(campaign_name)
    if campaign_id is None:
        return None, None

    where, params = _scope_filters(
        campaign_id=campaign_id,
        start_date=start_date,
        end_date=end_date,
        channels=channels,
        keywords=keywords,
        exclude_keywords=exclude_keywords,
        match_mode=match_mode,
    )

    cte = f"""
        WITH scoped_rows AS (
            SELECT
                p.*,
                {_channel_norm_sql("p")} AS channel_norm,
                {_canonical_key_sql("p")} AS canonical_key,
                CASE
                    WHEN {_raw_has("Engagement", "p")}
                    THEN {_raw_num("Engagement", "p")}
                    ELSE p.engagement
                END AS source_engagement,
                {_raw_has("Engagement", "p")} AS has_source_engagement
            FROM posts p
            JOIN post_campaigns pc ON pc.post_id = p.id
            WHERE {" AND ".join(where)}
        ),
        ranked_rows AS (
            SELECT
                sr.*,
                row_number() OVER (
                    PARTITION BY sr.canonical_key
                    ORDER BY
                        sr.source_engagement DESC NULLS LAST,
                        sr.post_date DESC NULLS LAST,
                        sr.id DESC
                ) AS canonical_rank
            FROM scoped_rows sr
        ),
        canonical_posts AS (
            SELECT *
            FROM ranked_rows
            WHERE canonical_rank = 1
        ),
        metric_components AS (
            SELECT
                cp.*,
                {_raw_num("Likes", "cp")} AS likes,
                {_raw_num("Comments", "cp")} AS comments,
                {_raw_num("Shares", "cp")} AS shares,
                {_raw_num("Views", "cp")} AS views,
                {_raw_num("Replies", "cp")} AS replies,
                {_raw_num("Retweets", "cp")} AS retweets,
                {_raw_num("Buzz", "cp")} AS buzz,
                {_raw_num("Ad Value", "cp")} AS ad_value,
                {_raw_num("PR Value", "cp")} AS pr_value,
                {_raw_num("Viral Score", "cp")} AS viral_score,
                {_raw_has("Likes", "cp")} AS has_likes,
                {_raw_has("Comments", "cp")} AS has_comments,
                {_raw_has("Shares", "cp")} AS has_shares,
                {_raw_has("Views", "cp")} AS has_views,
                {_raw_has("Replies", "cp")} AS has_replies,
                {_raw_has("Retweets", "cp")} AS has_retweets,
                {_raw_has("Buzz", "cp")} AS has_buzz,
                {_raw_has("Ad Value", "cp")} AS has_ad_value,
                cp.has_source_engagement AS has_source_engagement,
                lower(nullif(trim(coalesce(cp.sentiment, '')), '')) AS sentiment_norm
            FROM canonical_posts cp
        ),
        metric_posts AS (
            SELECT
                mc.*,
                CASE
                    WHEN mc.channel_norm = 'instagram'
                         AND mc.has_likes AND mc.has_comments
                    THEN mc.likes + mc.comments

                    WHEN mc.channel_norm = 'facebook'
                         AND mc.has_likes AND mc.has_comments AND mc.has_shares
                    THEN mc.likes + mc.comments + mc.shares

                    WHEN mc.channel_norm = 'youtube'
                         AND mc.has_likes AND mc.has_comments
                    THEN mc.likes + mc.comments

                    WHEN mc.channel_norm = 'tiktok'
                         AND mc.has_likes AND mc.has_comments AND mc.has_shares
                    THEN mc.likes + mc.comments + mc.shares

                    WHEN mc.channel_norm = 'x'
                         AND mc.has_likes AND mc.has_replies AND mc.has_retweets
                    THEN mc.likes + mc.replies + mc.retweets

                    ELSE NULL
                END AS interactions,

                CASE
                    WHEN mc.channel_norm IN ('instagram', 'facebook', 'youtube', 'tiktok', 'x')
                    THEN TRUE
                    ELSE FALSE
                END AS interactions_applicable,

                CASE
                    WHEN mc.channel_norm = 'instagram'
                    THEN mc.has_likes AND mc.has_comments

                    WHEN mc.channel_norm = 'facebook'
                    THEN mc.has_likes AND mc.has_comments AND mc.has_shares

                    WHEN mc.channel_norm = 'youtube'
                    THEN mc.has_likes AND mc.has_comments

                    WHEN mc.channel_norm = 'tiktok'
                    THEN mc.has_likes AND mc.has_comments AND mc.has_shares

                    WHEN mc.channel_norm = 'x'
                    THEN mc.has_likes AND mc.has_replies AND mc.has_retweets

                    ELSE FALSE
                END AS interactions_available
            FROM metric_components mc
        )
    """
    return cte, params


def _to_number(value: Any) -> int | float:
    """Decimal/None menjadi angka Python yang aman untuk JSON."""
    if value is None:
        return 0
    if isinstance(value, Decimal):
        number = float(value)
        return int(number) if number.is_integer() else round(number, 2)
    return value


# ---------------------------------------------------------------------
# Posts — dataframe/summary/import
# ---------------------------------------------------------------------
def fetch_posts_df(
    campaign_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    channels: str | Iterable[str] | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
) -> pd.DataFrame:
    """
    Ambil canonical posts ke dataframe.

    Dipakai oleh workflow yang memang perlu membaca banyak row, misalnya
    wordcloud atau pengolahan pandas. Semua row sudah dedup dan memiliki
    Interactions serta Views yang terpisah.
    """
    cte, params = _canonical_cte(
        campaign_name,
        start_date,
        end_date,
        channels,
        keywords,
        exclude_keywords,
        match_mode,
    )
    if cte is None:
        raise FileNotFoundError(
            f"Campaign '{campaign_name}' tidak ada. Tersedia: {list_campaigns()}"
        )

    sql = cte + """
        SELECT
            mp.title AS "Title",
            mp.content AS "Content",
            mp.post_date AS "Date",
            mp.channel AS "Channel",
            mp.sentiment AS "Sentiment",
            mp.interactions AS "Interactions",
            mp.views AS "Views",
            mp.source_engagement AS "Source Engagement",
            mp.potential_reach AS "Potential Reach",
            mp.url AS "Link URL",
            mp.likes AS "Likes",
            mp.comments AS "Comments",
            mp.shares AS "Shares",
            mp.replies AS "Replies",
            mp.retweets AS "Retweets"
        FROM metric_posts mp
        ORDER BY mp.post_date
    """

    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            columns = [description.name for description in cur.description]
            rows = cur.fetchall()
    return pd.DataFrame(rows, columns=columns)


def campaign_summary(campaign_name: str) -> dict[str, Any] | None:
    """Ringkasan canonical campaign: jumlah post, periode, dan channel."""
    cte, params = _canonical_cte(campaign_name)
    if cte is None:
        return None

    sql = cte + """
        SELECT
            count(*) AS total_posts_unique,
            min(mp.post_date) AS date_from,
            max(mp.post_date) AS date_to,
            count(*) FILTER (WHERE mp.title IS NOT NULL AND mp.title <> '') AS has_title,
            count(*) FILTER (WHERE mp.content IS NOT NULL AND mp.content <> '') AS has_content
        FROM metric_posts mp
    """

    channel_sql = cte + """
        SELECT DISTINCT mp.channel
        FROM metric_posts mp
        WHERE mp.channel IS NOT NULL AND mp.channel <> ''
        ORDER BY mp.channel
    """

    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            agg = cur.fetchone()
            cur.execute(channel_sql, params)
            channels = [row["channel"] for row in cur.fetchall()]

    return {"agg": agg, "channels": channels}


def insert_posts_with_campaigns(records: list[dict[str, Any]]) -> int:
    """
    Masukkan post + keanggotaan campaign-nya.

    Tiap record harus memiliki field `campaigns` berupa daftar nama campaign.
    Mencoba mode COPY borongan dulu, lalu fallback ke row insert.
    """
    if not records:
        return 0
    try:
        return _bulk_insert(records)
    except Exception as exc:
        print(f"  [info] mode cepat gagal ({exc}); pakai mode aman (lebih lambat)...")
        return _row_insert(records)


def _bulk_insert(records: list[dict[str, Any]]) -> int:
    """Masukkan borongan pakai COPY ke tabel sementara, lalu set-based insert."""
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TEMP TABLE _staging (
                    sid             bigint,
                    source_no       bigint,
                    post_date       timestamptz,
                    channel         text,
                    author          text,
                    title           text,
                    content         text,
                    sentiment       text,
                    engagement      double precision,
                    potential_reach double precision,
                    url             text,
                    campaigns_text  text,
                    raw             text
                ) ON COMMIT DROP
                """
            )

            copy_sql = (
                "COPY _staging (sid, source_no, post_date, channel, author, title, "
                "content, sentiment, engagement, potential_reach, url, "
                "campaigns_text, raw) FROM STDIN"
            )

            with cur.copy(copy_sql) as copy:
                for index, record in enumerate(records):
                    copy.write_row(
                        [
                            index,
                            record.get("source_no"),
                            record.get("post_date"),
                            record.get("channel"),
                            record.get("author"),
                            record.get("title"),
                            record.get("content"),
                            record.get("sentiment"),
                            record.get("engagement"),
                            record.get("potential_reach"),
                            record.get("url"),
                            ",".join(record.get("campaigns", [])),
                            json.dumps(record.get("raw", {}), ensure_ascii=False),
                        ]
                    )

            cur.execute(
                """
                INSERT INTO campaigns (name, name_norm)
                SELECT DISTINCT
                    btrim(c),
                    lower(regexp_replace(btrim(c), '[[:space:]]+', ' ', 'g'))
                FROM _staging,
                unnest(string_to_array(campaigns_text, ',')) AS c
                WHERE btrim(c) <> ''
                ON CONFLICT (name_norm) DO NOTHING
                """
            )

            cur.execute(
                """
                WITH ins AS (
                    INSERT INTO posts (
                        source_no, post_date, channel, author, title, content,
                        sentiment, engagement, potential_reach, url, raw
                    )
                    SELECT
                        source_no, post_date, channel, author, title, content,
                        sentiment, engagement, potential_reach, url, raw::jsonb
                    FROM _staging
                    ORDER BY sid
                    RETURNING id
                ),
                ins_rn AS (
                    SELECT id, row_number() OVER (ORDER BY id) AS rn
                    FROM ins
                ),
                stg_rn AS (
                    SELECT
                        sid,
                        campaigns_text,
                        row_number() OVER (ORDER BY sid) AS rn
                    FROM _staging
                )
                INSERT INTO post_campaigns (post_id, campaign_id)
                SELECT ir.id, c.id
                FROM ins_rn ir
                JOIN stg_rn s ON s.rn = ir.rn
                JOIN unnest(string_to_array(s.campaigns_text, ',')) AS camp ON true
                JOIN campaigns c
                    ON c.name_norm = lower(
                        regexp_replace(btrim(camp), '[[:space:]]+', ' ', 'g')
                    )
                WHERE btrim(camp) <> ''
                ON CONFLICT DO NOTHING
                """
            )

            cur.execute("SELECT count(*) FROM _staging")
            inserted = cur.fetchone()[0]

        conn.commit()

    return inserted


def _row_insert(records: list[dict[str, Any]]) -> int:
    """Fallback insert satu per satu bila mode COPY gagal."""
    all_names = [campaign for record in records for campaign in record.get("campaigns", [])]
    name_to_id = ensure_campaigns(all_names)

    inserted = 0
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            for record in records:
                cur.execute(
                    """
                    INSERT INTO posts (
                        source_no, post_date, channel, author, title, content,
                        sentiment, engagement, potential_reach, url, raw
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id
                    """,
                    (
                        record.get("source_no"),
                        record.get("post_date"),
                        record.get("channel"),
                        record.get("author"),
                        record.get("title"),
                        record.get("content"),
                        record.get("sentiment"),
                        record.get("engagement"),
                        record.get("potential_reach"),
                        record.get("url"),
                        psycopg.types.json.Json(record.get("raw", {})),
                    ),
                )
                post_id = cur.fetchone()[0]

                campaign_ids = {
                    name_to_id[_norm(campaign)]
                    for campaign in record.get("campaigns", [])
                    if _norm(campaign) in name_to_id
                }
                for campaign_id in campaign_ids:
                    cur.execute(
                        """
                        INSERT INTO post_campaigns (post_id, campaign_id)
                        VALUES (%s,%s)
                        ON CONFLICT DO NOTHING
                        """,
                        (post_id, campaign_id),
                    )
                inserted += 1
        conn.commit()

    return inserted


def reset_all_posts() -> None:
    """Kosongkan semua post & keanggotaannya untuk reset test."""
    with get_pool().connection() as conn:
        conn.execute("TRUNCATE post_campaigns, posts RESTART IDENTITY")
        conn.commit()


# ---------------------------------------------------------------------
# Guidance
# ---------------------------------------------------------------------
def get_guidance(campaign_name: str) -> dict[str, Any] | None:
    campaign_id = get_campaign_id(campaign_name)
    if campaign_id is None:
        return None

    with get_pool().connection() as conn:
        row = conn.execute(
            "SELECT guidance FROM campaign_guidance WHERE campaign_id = %s",
            (campaign_id,),
        ).fetchone()

    return row[0] if row else None


def upsert_guidance(campaign_name: str, guidance: dict[str, Any]) -> None:
    campaign_id = ensure_campaigns([campaign_name])[_norm(campaign_name)]
    with get_pool().connection() as conn:
        conn.execute(
            """
            INSERT INTO campaign_guidance (campaign_id, guidance, updated_at)
            VALUES (%s,%s,now())
            ON CONFLICT (campaign_id)
            DO UPDATE SET guidance = EXCLUDED.guidance, updated_at = now()
            """,
            (campaign_id, psycopg.types.json.Json(guidance)),
        )
        conn.commit()


# ---------------------------------------------------------------------
# Generated outputs
# ---------------------------------------------------------------------
def save_output(
    campaign_name: str | None,
    kind: str,
    params: dict,
    result: dict,
) -> int:
    campaign_id = get_campaign_id(campaign_name) if campaign_name else None
    with get_pool().connection() as conn:
        row = conn.execute(
            """
            INSERT INTO generated_outputs (campaign_id, kind, params, result)
            VALUES (%s,%s,%s,%s)
            RETURNING id
            """,
            (
                campaign_id,
                kind,
                psycopg.types.json.Json(params),
                psycopg.types.json.Json(result),
            ),
        ).fetchone()
        conn.commit()
    return row[0]


def list_outputs(
    campaign_name: str | None = None,
    kind: str | None = None,
    limit: int = 20,
) -> list[dict]:
    where: list[str] = []
    params: list[Any] = []

    if campaign_name:
        campaign_id = get_campaign_id(campaign_name)
        if campaign_id is None:
            return []
        where.append("campaign_id = %s")
        params.append(campaign_id)

    if kind:
        where.append("kind = %s")
        params.append(kind)

    sql = "SELECT id, campaign_id, kind, params, result, created_at FROM generated_outputs"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)

    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()


# ---------------------------------------------------------------------
# Saved reports
# ---------------------------------------------------------------------
def _ensure_saved_reports() -> None:
    """Buat tabel saved_reports bila belum ada. Aman dipanggil berulang."""
    with get_pool().connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_reports (
                id           SERIAL PRIMARY KEY,
                campaign_id  INTEGER,
                title        TEXT,
                period_start DATE,
                period_end   DATE,
                payload      JSONB NOT NULL,
                created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_saved_reports_campaign
            ON saved_reports (campaign_id, period_end DESC)
            """
        )
        conn.commit()


def save_report(
    campaign_name: str | None,
    period_start: str | None,
    period_end: str | None,
    title: str | None,
    payload: dict,
) -> int:
    """Simpan satu report penuh untuk perbandingan atau regenerasi."""
    _ensure_saved_reports()
    campaign_id = get_campaign_id(campaign_name) if campaign_name else None

    with get_pool().connection() as conn:
        row = conn.execute(
            """
            INSERT INTO saved_reports (
                campaign_id, title, period_start, period_end, payload
            )
            VALUES (%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (
                campaign_id,
                title,
                period_start or None,
                period_end or None,
                psycopg.types.json.Json(payload),
            ),
        ).fetchone()
        conn.commit()

    return row[0]


def get_previous_report(
    campaign_name: str,
    before_date: str | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
) -> dict | None:
    """Ambil report tersimpan untuk campaign ini."""
    _ensure_saved_reports()

    campaign_id = get_campaign_id(campaign_name)
    if campaign_id is None:
        return None

    where = ["campaign_id = %s"]
    params: list[Any] = [campaign_id]

    if period_start and period_end:
        where.append("period_start = %s AND period_end = %s")
        params += [period_start, period_end]
    elif before_date:
        where.append("period_end < %s")
        params.append(before_date)

    sql = (
        "SELECT id, title, period_start, period_end, payload, created_at "
        "FROM saved_reports WHERE "
        + " AND ".join(where)
        + " ORDER BY period_end DESC NULLS LAST, created_at DESC LIMIT 1"
    )

    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchone()


def list_saved_reports(
    campaign_name: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Daftar report tersimpan tanpa payload besar."""
    _ensure_saved_reports()

    where: list[str] = []
    params: list[Any] = []

    if campaign_name:
        campaign_id = get_campaign_id(campaign_name)
        if campaign_id is None:
            return []
        where.append("campaign_id = %s")
        params.append(campaign_id)

    sql = (
        "SELECT id, campaign_id, title, period_start, period_end, created_at "
        "FROM saved_reports"
    )
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)

    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()


# ---------------------------------------------------------------------
# Analytics: canonical count, breakdown, export
# ---------------------------------------------------------------------
def count_and_breakdown(
    campaign_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    channels: str | Iterable[str] | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
) -> dict[str, Any] | None:
    """
    Canonical post count + channel/sentiment breakdown.

    `sentiment_interactions` bersifat diagnostic-only. Server client-facing
    tidak boleh menjadikannya KPI utama tanpa lolos Metric Admission Rule.
    """
    cte, params = _canonical_cte(
        campaign_name,
        start_date,
        end_date,
        channels,
        keywords,
        exclude_keywords,
        match_mode,
    )
    if cte is None:
        return None

    total_sql = cte + """
        SELECT
            count(*) AS total_posts,
            (SELECT count(*) FROM scoped_rows) AS raw_rows,
            count(*) FILTER (
                WHERE mp.sentiment_norm IN ('positive', 'negative', 'neutral')
            ) AS classified_posts
        FROM metric_posts mp
    """

    channel_sql = cte + """
        SELECT
            coalesce(nullif(mp.channel, ''), '(tidak diketahui)') AS channel,
            count(*) AS count
        FROM metric_posts mp
        GROUP BY channel
        ORDER BY count DESC
    """

    sentiment_sql = cte + """
        SELECT
            coalesce(nullif(mp.sentiment_norm, ''), '(tidak diketahui)') AS sentiment,
            count(*) AS count
        FROM metric_posts mp
        GROUP BY sentiment
        ORDER BY count DESC
    """

    sentiment_interactions_sql = cte + """
        SELECT
            mp.sentiment_norm AS sentiment,
            sum(coalesce(mp.interactions, 0)) AS interactions
        FROM metric_posts mp
        WHERE mp.sentiment_norm IN ('positive', 'negative', 'neutral')
        GROUP BY mp.sentiment_norm
    """

    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(total_sql, params)
            total = cur.fetchone()

            cur.execute(channel_sql, params)
            channels_rows = cur.fetchall()

            cur.execute(sentiment_sql, params)
            sentiment_rows = cur.fetchall()

            cur.execute(sentiment_interactions_sql, params)
            sentiment_interactions = {
                row["sentiment"]: _to_number(row["interactions"])
                for row in cur.fetchall()
            }

    return {
        "total": int(total["total_posts"] or 0),
        "raw_rows": int(total["raw_rows"] or 0),
        "duplicates_removed": int((total["raw_rows"] or 0) - (total["total_posts"] or 0)),
        "classified_posts": int(total["classified_posts"] or 0),
        "channels": [
            (row["channel"], int(row["count"] or 0))
            for row in channels_rows
        ],
        "sentiments": [
            (row["sentiment"], int(row["count"] or 0))
            for row in sentiment_rows
        ],
        "sentiment_interactions": sentiment_interactions,
    }


def fetch_raw_records(
    campaign_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
    channels: str | Iterable[str] | None = None,
) -> list[dict] | None:
    """
    Ambil raw record canonical untuk ekspor CSV.

    Raw asli dipertahankan, lalu ditambah metadata `_cogan_*` agar pengguna
    tahu row telah dedup dan interactions/views dihitung terpisah.
    """
    cte, params = _canonical_cte(
        campaign_name,
        start_date,
        end_date,
        channels,
        keywords,
        exclude_keywords,
        match_mode,
    )
    if cte is None:
        return None

    sql = cte + """
        SELECT
            mp.raw,
            mp.id AS canonical_post_id,
            mp.post_date,
            mp.channel,
            mp.url,
            mp.interactions,
            mp.views,
            mp.source_engagement,
            mp.interactions_available,
            mp.has_views
        FROM metric_posts mp
        ORDER BY mp.post_date
    """

    if limit:
        sql += " LIMIT %s"
        params = list(params) + [int(limit)]

    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    records: list[dict] = []
    for row in rows:
        raw = dict(row["raw"] or {})
        raw["_cogan_canonical_post_id"] = row["canonical_post_id"]
        raw["_cogan_post_date"] = row["post_date"].isoformat() if row["post_date"] else None
        raw["_cogan_channel"] = row["channel"]
        raw["_cogan_url"] = row["url"]
        raw["_cogan_interactions"] = _to_number(row["interactions"])
        raw["_cogan_views"] = _to_number(row["views"])
        raw["_cogan_source_engagement"] = _to_number(row["source_engagement"])
        raw["_cogan_interactions_available"] = bool(row["interactions_available"])
        raw["_cogan_views_available"] = bool(row["has_views"])
        records.append(raw)

    return records


# ---------------------------------------------------------------------
# Metrics per channel
# ---------------------------------------------------------------------
def metrics_breakdown(
    campaign_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    channel: str | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
) -> list[dict] | None:
    """
    Canonical metrics per channel.

    Output utama:
    - interactions: hasil rumus channel-specific
    - views: dipisahkan
    - source_engagement: kolom sumber lama, diagnostic only
    """
    channels = [channel] if channel else None
    cte, params = _canonical_cte(
        campaign_name,
        start_date,
        end_date,
        channels,
        keywords,
        exclude_keywords,
        match_mode,
    )
    if cte is None:
        return None

    sql = cte + """
        SELECT
            coalesce(nullif(mp.channel, ''), '(tidak diketahui)') AS channel,
            mp.channel_norm,
            count(*) AS posts,

            sum(coalesce(mp.interactions, 0)) AS interactions,
            sum(CASE WHEN mp.has_views THEN mp.views ELSE 0 END) AS views,
            sum(coalesce(mp.source_engagement, 0)) AS source_engagement,

            sum(mp.likes) AS likes,
            sum(mp.comments) AS comments,
            sum(mp.shares) AS shares,
            sum(mp.replies) AS replies,
            sum(mp.retweets) AS retweets,

            sum(mp.buzz) AS buzz,
            sum(mp.ad_value) AS ad_value,
            sum(mp.pr_value) AS pr_value,

            count(*) FILTER (WHERE mp.interactions_applicable) AS interaction_applicable_posts,
            count(*) FILTER (WHERE mp.interactions_available) AS interaction_available_posts,
            count(*) FILTER (WHERE mp.has_views) AS views_available_posts,
            count(*) FILTER (WHERE mp.has_source_engagement) AS source_engagement_available_posts
        FROM metric_posts mp
        GROUP BY channel, mp.channel_norm
        ORDER BY interactions DESC NULLS LAST, views DESC NULLS LAST, posts DESC
    """

    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()


# ---------------------------------------------------------------------
# Top authors
# ---------------------------------------------------------------------
def top_authors(
    campaign_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 10,
    channels: str | Iterable[str] | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
) -> list[dict] | None:
    """
    Top author by total interactions.

    Identitas = author + channel agar akun yang sama di platform berbeda tidak
    otomatis digabung.
    """
    cte, params = _canonical_cte(
        campaign_name,
        start_date,
        end_date,
        channels,
        keywords,
        exclude_keywords,
        match_mode,
    )
    if cte is None:
        return None

    aggregate_sql = cte + """
        SELECT
            mp.author,
            coalesce(nullif(mp.channel, ''), '(tidak diketahui)') AS channel,
            count(*) AS posts,
            sum(coalesce(mp.interactions, 0)) AS total_interactions,
            sum(CASE WHEN mp.has_views THEN mp.views ELSE 0 END) AS total_views,
            count(*) FILTER (WHERE mp.sentiment_norm = 'positive') AS positive_posts,
            count(*) FILTER (WHERE mp.sentiment_norm = 'negative') AS negative_posts,
            count(*) FILTER (WHERE mp.sentiment_norm = 'neutral') AS neutral_posts
        FROM metric_posts mp
        WHERE mp.author IS NOT NULL AND mp.author <> ''
        GROUP BY mp.author, channel
        ORDER BY total_interactions DESC NULLS LAST, total_views DESC NULLS LAST
        LIMIT %s
    """

    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(aggregate_sql, list(params) + [int(limit)])
            authors = cur.fetchall()

    if not authors:
        return []

    output: list[dict] = []
    for author in authors:
        top_post_sql = cte + """
            SELECT
                mp.content,
                mp.url,
                mp.sentiment,
                mp.post_date,
                mp.channel,
                mp.interactions,
                mp.views,
                mp.source_engagement,
                mp.likes,
                mp.comments,
                mp.shares,
                mp.replies,
                mp.retweets
            FROM metric_posts mp
            WHERE mp.author = %s
              AND coalesce(nullif(mp.channel, ''), '(tidak diketahui)') = %s
            ORDER BY mp.interactions DESC NULLS LAST, mp.views DESC NULLS LAST
            LIMIT 1
        """

        with get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(top_post_sql, list(params) + [author["author"], author["channel"]])
                top_post = cur.fetchone() or {}

        output.append(
            {
                "author": author["author"],
                "channel": author["channel"],
                "posts": int(author["posts"] or 0),
                "total_interactions": _to_number(author["total_interactions"]),
                "total_views": _to_number(author["total_views"]),
                "sentiment": {
                    "positive": int(author["positive_posts"] or 0),
                    "negative": int(author["negative_posts"] or 0),
                    "neutral": int(author["neutral_posts"] or 0),
                },
                "top_post": top_post,
            }
        )

    return output


# ---------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------
def timeline(
    campaign_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    channel: str | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
) -> list[dict] | None:
    """
    Breakdown per tanggal dari canonical posts.

    Memisahkan:
    - posts
    - interactions
    - views
    - source engagement (diagnostic)
    """
    channels = [channel] if channel else None
    cte, params = _canonical_cte(
        campaign_name,
        start_date,
        end_date,
        channels,
        keywords,
        exclude_keywords,
        match_mode,
    )
    if cte is None:
        return None

    sql = cte + """
        SELECT
            mp.post_date::date AS day,
            count(*) AS posts,
            sum(coalesce(mp.interactions, 0)) AS interactions,
            sum(CASE WHEN mp.has_views THEN mp.views ELSE 0 END) AS views,
            sum(coalesce(mp.source_engagement, 0)) AS source_engagement,

            count(*) FILTER (WHERE mp.sentiment_norm = 'positive') AS positive_posts,
            count(*) FILTER (WHERE mp.sentiment_norm = 'negative') AS negative_posts,
            count(*) FILTER (WHERE mp.sentiment_norm = 'neutral') AS neutral_posts
        FROM metric_posts mp
        GROUP BY day
        ORDER BY day
    """

    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()


# ---------------------------------------------------------------------
# Read posts
# ---------------------------------------------------------------------
def get_posts(
    campaign_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    channel: str | None = None,
    sentiment: str | None = None,
    sort_by: str = "interactions",
    limit: int = 50,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
) -> list[dict] | None:
    """
    Ambil canonical posts lengkap untuk membaca konten asli.

    `sort_by`:
    - interactions (default)
    - views
    - shares
    - likes
    - comments
    - date
    - date_desc
    - source_engagement (diagnostic)
    """
    channels = [channel] if channel else None
    cte, params = _canonical_cte(
        campaign_name,
        start_date,
        end_date,
        channels,
        keywords,
        exclude_keywords,
        match_mode,
    )
    if cte is None:
        return None

    order_map = {
        "interactions": "mp.interactions DESC NULLS LAST, mp.views DESC NULLS LAST",
        "engagement": "mp.interactions DESC NULLS LAST, mp.views DESC NULLS LAST",
        "views": "mp.views DESC NULLS LAST, mp.interactions DESC NULLS LAST",
        "shares": "mp.shares DESC NULLS LAST, mp.interactions DESC NULLS LAST",
        "likes": "mp.likes DESC NULLS LAST, mp.interactions DESC NULLS LAST",
        "comments": "mp.comments DESC NULLS LAST, mp.interactions DESC NULLS LAST",
        "source_engagement": "mp.source_engagement DESC NULLS LAST",
        "date": "mp.post_date ASC",
        "date_desc": "mp.post_date DESC",
    }
    order_by = order_map.get(sort_by, order_map["interactions"])

    where = ""
    query_params = list(params)
    if sentiment:
        where = "WHERE mp.sentiment_norm = %s"
        query_params.append(sentiment.strip().lower())

    sql = cte + f"""
        SELECT
            mp.id,
            mp.post_date,
            mp.channel,
            mp.channel_norm,
            mp.author,
            mp.sentiment,
            mp.url,
            mp.title,
            mp.content,

            mp.interactions,
            mp.views,
            mp.source_engagement,

            mp.likes,
            mp.comments,
            mp.shares,
            mp.replies,
            mp.retweets,

            mp.interactions_available,
            mp.has_views,
            mp.buzz,
            mp.ad_value,
            mp.pr_value
        FROM metric_posts mp
        {where}
        ORDER BY {order_by}
        LIMIT %s
    """
    query_params.append(int(limit))

    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, query_params)
            return cur.fetchall()


# ---------------------------------------------------------------------
# Period totals / comparisons
# ---------------------------------------------------------------------
def period_totals(
    campaign_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    channel: str | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
) -> dict | None:
    """Total canonical posts, interactions, views, buzz, dan sentiment."""
    channels = [channel] if channel else None
    cte, params = _canonical_cte(
        campaign_name,
        start_date,
        end_date,
        channels,
        keywords,
        exclude_keywords,
        match_mode,
    )
    if cte is None:
        return None

    sql = cte + """
        SELECT
            count(*) AS posts,
            sum(coalesce(mp.interactions, 0)) AS interactions,
            sum(CASE WHEN mp.has_views THEN mp.views ELSE 0 END) AS views,
            sum(coalesce(mp.source_engagement, 0)) AS source_engagement,
            sum(mp.buzz) AS buzz,

            count(*) FILTER (WHERE mp.sentiment_norm = 'positive') AS positive_posts,
            count(*) FILTER (WHERE mp.sentiment_norm = 'negative') AS negative_posts,
            count(*) FILTER (WHERE mp.sentiment_norm = 'neutral') AS neutral_posts,

            count(*) FILTER (WHERE mp.sentiment_norm IN ('positive', 'negative', 'neutral')) AS classified_posts,
            count(*) FILTER (WHERE mp.interactions_applicable) AS interaction_applicable_posts,
            count(*) FILTER (WHERE mp.interactions_available) AS interaction_available_posts,
            count(*) FILTER (WHERE mp.has_views) AS views_available_posts
        FROM metric_posts mp
    """

    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchone()


# ---------------------------------------------------------------------
# Top posts
# ---------------------------------------------------------------------
def top_posts(
    campaign_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    channel: str | None = None,
    by: str = "interactions",
    limit: int = 10,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
) -> list[dict] | None:
    """
    Post individual teratas dari canonical layer.

    `by`:
    - interactions / engagement
    - views
    - shares
    - likes
    - comments
    - source_engagement
    - viral_score
    """
    channels = [channel] if channel else None
    cte, params = _canonical_cte(
        campaign_name,
        start_date,
        end_date,
        channels,
        keywords,
        exclude_keywords,
        match_mode,
    )
    if cte is None:
        return None

    order_map = {
        "interactions": "mp.interactions",
        "engagement": "mp.interactions",
        "views": "mp.views",
        "shares": "mp.shares",
        "likes": "mp.likes",
        "comments": "mp.comments",
        "source_engagement": "mp.source_engagement",
        "viral": "mp.viral_score",
        "viral_score": "mp.viral_score",
    }
    order_metric = order_map.get(by, "mp.interactions")

    sql = cte + f"""
        SELECT
            mp.post_date,
            mp.channel,
            mp.channel_norm,
            mp.author,
            mp.sentiment,
            mp.url,
            mp.title,
            mp.content,

            mp.interactions,
            mp.views,
            mp.source_engagement,

            mp.likes,
            mp.comments,
            mp.shares,
            mp.replies,
            mp.retweets,
            mp.viral_score,

            mp.interactions_available,
            mp.has_views
        FROM metric_posts mp
        ORDER BY {order_metric} DESC NULLS LAST, mp.post_date DESC
        LIMIT %s
    """

    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, list(params) + [int(limit)])
            return cur.fetchall()


# ---------------------------------------------------------------------
# Online media
# ---------------------------------------------------------------------
def top_media(
    campaign_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    keyword: str | None = None,
    limit: int = 10,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
) -> list[dict] | None:
    """
    Ranking media outlet berdasarkan ad value media online.

    Catatan:
    - ad value bukan engagement;
    - ad value bukan bukti media tier-1;
    - hasil harus dipakai bersama jumlah artikel dan penilaian kualitas outlet.
    """
    keywords = [keyword] if keyword else None
    cte, params = _canonical_cte(
        campaign_name,
        start_date,
        end_date,
        None,
        keywords,
        exclude_keywords,
        match_mode,
    )
    if cte is None:
        return None

    sql = cte + """
        SELECT
            nullif(trim(mp.raw->>'Media Name'), '') AS media_name,
            count(*) AS articles,
            sum(mp.ad_value) AS ad_value,
            sum(mp.pr_value) AS pr_value
        FROM metric_posts mp
        WHERE nullif(trim(mp.raw->>'Media Name'), '') IS NOT NULL
        GROUP BY media_name
        ORDER BY ad_value DESC NULLS LAST, articles DESC
        LIMIT %s
    """

    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, list(params) + [int(limit)])
            return cur.fetchall()


# ---------------------------------------------------------------------
# Data health
# ---------------------------------------------------------------------
def data_health(
    campaign_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    channels: str | Iterable[str] | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
) -> dict[str, Any] | None:
    """
    Bukti data + coverage berbasis canonical posts.

    Penting:
    - `interactions_available` bukan `interactions > 0`;
    - zero interactions tetap dapat dianggap field tersedia;
    - denominator interactions coverage hanya post/channel yang memang applicable.
    """
    cte, params = _canonical_cte(
        campaign_name,
        start_date,
        end_date,
        channels,
        keywords,
        exclude_keywords,
        match_mode,
    )
    if cte is None:
        return None

    overview_sql = cte + """
        SELECT
            count(*) AS n_unique,
            (SELECT count(*) FROM scoped_rows) AS n_rows_raw,
            min(mp.post_date)::date AS date_min,
            max(mp.post_date)::date AS date_max,

            count(*) FILTER (
                WHERE mp.sentiment_norm IN ('positive', 'negative', 'neutral')
            ) AS sentiment_classified_posts,

            count(*) FILTER (
                WHERE mp.interactions_applicable
            ) AS interactions_applicable_posts,

            count(*) FILTER (
                WHERE mp.interactions_available
            ) AS interactions_available_posts,

            count(*) FILTER (
                WHERE mp.has_views
            ) AS views_available_posts,

            count(*) FILTER (
                WHERE mp.has_source_engagement
            ) AS source_engagement_available_posts,

            count(*) FILTER (
                WHERE mp.has_buzz
            ) AS buzz_available_posts,

            count(*) FILTER (
                WHERE mp.has_ad_value
            ) AS ad_value_available_posts
        FROM metric_posts mp
    """

    channel_sql = cte + """
        SELECT
            coalesce(nullif(mp.channel, ''), '(tidak diketahui)') AS channel,
            mp.channel_norm,
            count(*) AS posts,

            count(*) FILTER (
                WHERE mp.interactions_applicable
            ) AS interactions_applicable_posts,

            count(*) FILTER (
                WHERE mp.interactions_available
            ) AS interactions_available_posts,

            count(*) FILTER (
                WHERE mp.has_views
            ) AS views_available_posts,

            count(*) FILTER (
                WHERE mp.sentiment_norm IN ('positive', 'negative', 'neutral')
            ) AS sentiment_classified_posts
        FROM metric_posts mp
        GROUP BY channel, mp.channel_norm
        ORDER BY posts DESC
    """

    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(overview_sql, params)
            overview = cur.fetchone()

            cur.execute(channel_sql, params)
            channels_rows = cur.fetchall()

    return {"row": overview, "channels": channels_rows}


# ---------------------------------------------------------------------
# Metric readiness preflight
# ---------------------------------------------------------------------
def metric_readiness(
    campaign_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    channels: str | Iterable[str] | None = None,
    keywords: str | Iterable[str] | None = None,
    exclude_keywords: str | Iterable[str] | None = None,
    match_mode: str = "any",
) -> dict[str, Any] | None:
    """
    Preflight diagnostic for raw metric fields before report metrics are used.

    This does not replace `data_health()`. It answers a different question:
    whether the canonical raw headers are present, numeric formats are usable,
    and channel names are mapped to a defined interaction formula.
    """
    cte, params = _canonical_cte(
        campaign_name,
        start_date,
        end_date,
        channels,
        keywords,
        exclude_keywords,
        match_mode,
    )
    if cte is None:
        return None

    tracked_fields = (
        "Likes",
        "Comments",
        "Shares",
        "Replies",
        "Retweets",
        "Views",
        "Engagement",
    )
    availability_select = ",\n".join(
        (
            f"count(*) FILTER (WHERE {_raw_has(field, 'mp')}) "
            f"AS {field.lower().replace(' ', '_')}_available_posts"
        )
        for field in tracked_fields
    )

    summary_sql = cte + f"""
        SELECT
            count(*) AS canonical_posts,
            {availability_select},
            count(*) FILTER (
                WHERE mp.channel_norm NOT IN (
                    'instagram', 'facebook', 'youtube', 'tiktok', 'x',
                    'online_media', 'forum'
                )
            ) AS unmapped_channel_posts
        FROM metric_posts mp
    """

    channel_sql = cte + """
        SELECT
            coalesce(nullif(mp.channel, ''), '(tidak diketahui)') AS channel,
            mp.channel_norm,
            count(*) AS posts,
            count(*) FILTER (WHERE mp.interactions_applicable) AS interactions_applicable_posts,
            count(*) FILTER (WHERE mp.interactions_available) AS interactions_available_posts,
            count(*) FILTER (WHERE mp.has_views) AS views_available_posts
        FROM metric_posts mp
        GROUP BY channel, mp.channel_norm
        ORDER BY posts DESC, channel
    """

    all_aliases = sorted(
        {
            raw_header
            for field in tracked_fields
            for raw_header in _raw_field_aliases(field)
        }
    )
    header_sql = cte + """
        SELECT
            raw_key,
            count(*) AS canonical_posts_with_header
        FROM metric_posts mp
        CROSS JOIN LATERAL jsonb_object_keys(
            coalesce(mp.raw, '{}'::jsonb)
        ) AS raw_key
        WHERE raw_key = ANY(%s)
        GROUP BY raw_key
        ORDER BY raw_key
    """

    suffix_select = ",\n".join(
        (
            f"count(*) FILTER (WHERE lower(trim(coalesce({_raw_text(field, 'mp')}, ''))) "
            f"~ '[kmb]$') AS {field.lower().replace(' ', '_')}_suffix_values"
        )
        for field in tracked_fields
    )
    nonstandard_select = ",\n".join(
        (
            f"count(*) FILTER (WHERE {_raw_text(field, 'mp')} IS NOT NULL "
            f"AND regexp_replace(lower(trim({_raw_text(field, 'mp')})), "
            f"'[0-9, .kmb-]', '', 'g') <> '') "
            f"AS {field.lower().replace(' ', '_')}_nonstandard_values"
        )
        for field in tracked_fields
    )
    parse_sql = cte + f"""
        SELECT
            {suffix_select},
            {nonstandard_select}
        FROM metric_posts mp
    """

    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(summary_sql, params)
            overview = cur.fetchone()

            cur.execute(channel_sql, params)
            channel_rows = cur.fetchall()

            cur.execute(header_sql, list(params) + [all_aliases])
            header_rows = cur.fetchall()

            cur.execute(parse_sql, params)
            parse_rows = cur.fetchone()

    headers_by_name = {
        row["raw_key"]: int(row["canonical_posts_with_header"] or 0)
        for row in header_rows
    }

    field_status: dict[str, dict[str, Any]] = {}
    for field in tracked_fields:
        aliases = list(_raw_field_aliases(field))
        field_status[field] = {
            "configured_aliases": aliases,
            "detected_headers": [
                {
                    "header": header,
                    "canonical_posts_with_header": headers_by_name[header],
                }
                for header in aliases
                if header in headers_by_name
            ],
            "available_on_canonical_posts": int(
                overview.get(f"{field.lower().replace(' ', '_')}_available_posts") or 0
            ),
        }

    parse_warnings: dict[str, dict[str, int]] = {}
    for field in tracked_fields:
        key = field.lower().replace(" ", "_")
        parse_warnings[field] = {
            "suffix_values_detected": int(
                parse_rows.get(f"{key}_suffix_values") or 0
            ),
            "nonstandard_values_detected": int(
                parse_rows.get(f"{key}_nonstandard_values") or 0
            ),
        }

    return {
        "overview": overview,
        "raw_field_status": field_status,
        "channels": channel_rows,
        "parse_warnings": parse_warnings,
        "unknown_channel_rows": [
            {
                "channel": row["channel"],
                "channel_norm": row["channel_norm"],
                "posts": int(row["posts"] or 0),
            }
            for row in channel_rows
            if row["channel_norm"]
            not in {"instagram", "facebook", "youtube", "tiktok", "x", "online_media", "forum"}
        ],
    }
