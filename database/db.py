"""
db.py — satu-satunya pintu ke database Cogan.

Semua tool di server.py membaca/menulis lewat fungsi di sini. Model data:
campaign = klien; satu post bisa masuk beberapa campaign (lihat schema.sql).

Koneksi diambil dari environment variable DATABASE_URL. Di Railway, kalau
kamu menambah service PostgreSQL, DATABASE_URL muncul otomatis.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

BASE_DIR = Path(__file__).parent
SCHEMA_PATH = BASE_DIR / "schema.sql"

_pool: ConnectionPool | None = None


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError(
            "DATABASE_URL belum di-set. Lihat docs/SETUP_DATABASE_STEPS.md."
        )
    if dsn.startswith("postgres://"):
        dsn = "postgresql://" + dsn[len("postgres://"):]
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
# Campaigns (= klien)
# ---------------------------------------------------------------------
def _norm(name: str) -> str:
    return " ".join(str(name).strip().lower().split())


def list_campaigns() -> list[str]:
    with get_pool().connection() as conn:
        rows = conn.execute("SELECT name FROM campaigns ORDER BY name").fetchall()
    return [r[0] for r in rows]


def get_campaign_id(name: str) -> int | None:
    with get_pool().connection() as conn:
        row = conn.execute(
            "SELECT id FROM campaigns WHERE name_norm = %s", (_norm(name),)
        ).fetchone()
    return row[0] if row else None


def ensure_campaigns(names: list[str]) -> dict[str, int]:
    """Pastikan tiap nama campaign ada; kembalikan peta name_norm -> id."""
    result: dict[str, int] = {}
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            for name in names:
                nn = _norm(name)
                if not nn or nn in result:
                    continue
                cur.execute(
                    """
                    INSERT INTO campaigns (name, name_norm) VALUES (%s, %s)
                    ON CONFLICT (name_norm) DO UPDATE SET name = campaigns.name
                    RETURNING id
                    """,
                    (str(name).strip(), nn),
                )
                result[nn] = cur.fetchone()[0]
        conn.commit()
    return result


# ---------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------
# Kolom dikembalikan dengan NAMA yang dipakai engine wordcloud, supaya
# kode penghitung di server.py tidak perlu diubah.
_SELECT_COLS = """
    SELECT
        p.title           AS "Title",
        p.content         AS "Content",
        p.post_date       AS "Date",
        p.channel         AS "Channel",
        p.sentiment       AS "Sentiment",
        p.engagement      AS "Engagement",
        p.potential_reach AS "Potential Reach",
        p.url             AS "Link URL"
    FROM posts p
    JOIN post_campaigns pc ON pc.post_id = p.id
    JOIN campaigns c       ON c.id = pc.campaign_id
"""


def fetch_posts_df(
    campaign_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    channels: str | None = None,
) -> pd.DataFrame:
    """Ambil post 1 campaign, sudah tersaring di sisi database."""
    if get_campaign_id(campaign_name) is None:
        raise FileNotFoundError(
            f"Campaign '{campaign_name}' tidak ada. Tersedia: {list_campaigns()}"
        )
    where = ["c.name_norm = %s"]
    params: list[Any] = [_norm(campaign_name)]
    if start_date:
        where.append("p.post_date >= %s"); params.append(start_date)
    if end_date:
        where.append("p.post_date <= %s"); params.append(end_date)
    if channels:
        wanted = [x.strip().lower() for x in channels.split(",") if x.strip()]
        if wanted:
            where.append("lower(p.channel) = ANY(%s)"); params.append(wanted)
    sql = _SELECT_COLS + " WHERE " + " AND ".join(where)
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [d.name for d in cur.description]
            data = cur.fetchall()
    return pd.DataFrame(data, columns=cols)


def campaign_summary(campaign_name: str) -> dict[str, Any] | None:
    """Ringkasan campaign (jumlah, periode, channel) dihitung di sisi DB."""
    cid = get_campaign_id(campaign_name)
    if cid is None:
        return None
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT count(*) AS total_rows,
                       min(p.post_date) AS date_from,
                       max(p.post_date) AS date_to,
                       count(*) FILTER (WHERE p.title   IS NOT NULL AND p.title   <> '') AS has_title,
                       count(*) FILTER (WHERE p.content IS NOT NULL AND p.content <> '') AS has_content
                FROM posts p JOIN post_campaigns pc ON pc.post_id = p.id
                WHERE pc.campaign_id = %s
                """,
                (cid,),
            )
            agg = cur.fetchone()
            cur.execute(
                """
                SELECT DISTINCT p.channel FROM posts p
                JOIN post_campaigns pc ON pc.post_id = p.id
                WHERE pc.campaign_id = %s AND p.channel IS NOT NULL AND p.channel <> ''
                ORDER BY p.channel
                """,
                (cid,),
            )
            channels = [r["channel"] for r in cur.fetchall()]
    return {"agg": agg, "channels": channels}


def insert_posts_with_campaigns(records: list[dict[str, Any]]) -> int:
    """
    Masukkan post + keanggotaan campaign-nya. Tiap record punya field
    'campaigns' (daftar nama campaign). Mencoba cara CEPAT (COPY borongan)
    dulu; kalau gagal, otomatis pakai cara lama yang lambat tapi pasti.
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
                for i, r in enumerate(records):
                    copy.write_row([
                        i,
                        r.get("source_no"),
                        r.get("post_date"),
                        r.get("channel"),
                        r.get("author"),
                        r.get("title"),
                        r.get("content"),
                        r.get("sentiment"),
                        r.get("engagement"),
                        r.get("potential_reach"),
                        r.get("url"),
                        ",".join(r.get("campaigns", [])),
                        json.dumps(r.get("raw", {}), ensure_ascii=False),
                    ])

            # 1) pastikan semua campaign ada (dinormalisasi sama seperti _norm)
            cur.execute(
                """
                INSERT INTO campaigns (name, name_norm)
                SELECT DISTINCT btrim(c),
                       lower(regexp_replace(btrim(c), '[[:space:]]+', ' ', 'g'))
                FROM _staging, unnest(string_to_array(campaigns_text, ',')) AS c
                WHERE btrim(c) <> ''
                ON CONFLICT (name_norm) DO NOTHING
                """
            )

            # 2) insert posts (urut sid -> id serial naik searah sid) + buat link
            cur.execute(
                """
                WITH ins AS (
                    INSERT INTO posts (source_no, post_date, channel, author, title,
                        content, sentiment, engagement, potential_reach, url, raw)
                    SELECT source_no, post_date, channel, author, title, content,
                        sentiment, engagement, potential_reach, url, raw::jsonb
                    FROM _staging ORDER BY sid
                    RETURNING id
                ),
                ins_rn AS (
                    SELECT id, row_number() OVER (ORDER BY id) AS rn FROM ins
                ),
                stg_rn AS (
                    SELECT sid, campaigns_text,
                           row_number() OVER (ORDER BY sid) AS rn
                    FROM _staging
                )
                INSERT INTO post_campaigns (post_id, campaign_id)
                SELECT ir.id, c.id
                FROM ins_rn ir
                JOIN stg_rn s ON s.rn = ir.rn
                JOIN unnest(string_to_array(s.campaigns_text, ',')) AS camp ON true
                JOIN campaigns c
                  ON c.name_norm = lower(regexp_replace(btrim(camp), '[[:space:]]+', ' ', 'g'))
                WHERE btrim(camp) <> ''
                ON CONFLICT DO NOTHING
                """
            )
            cur.execute("SELECT count(*) FROM _staging")
            n = cur.fetchone()[0]
        conn.commit()
    return n


def _row_insert(records: list[dict[str, Any]]) -> int:
    """Cara lama: satu-satu. Lambat, tapi dipakai sebagai cadangan kalau perlu."""
    all_names = [c for r in records for c in r.get("campaigns", [])]
    name_to_id = ensure_campaigns(all_names)
    inserted = 0
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            for r in records:
                cur.execute(
                    """
                    INSERT INTO posts (source_no, post_date, channel, author,
                        title, content, sentiment, engagement, potential_reach,
                        url, raw)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
                    """,
                    (
                        r.get("source_no"), r.get("post_date"), r.get("channel"),
                        r.get("author"), r.get("title"), r.get("content"),
                        r.get("sentiment"), r.get("engagement"),
                        r.get("potential_reach"), r.get("url"),
                        psycopg.types.json.Json(r.get("raw", {})),
                    ),
                )
                post_id = cur.fetchone()[0]
                links = {name_to_id[_norm(c)] for c in r.get("campaigns", []) if _norm(c) in name_to_id}
                for camp_id in links:
                    cur.execute(
                        "INSERT INTO post_campaigns (post_id, campaign_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                        (post_id, camp_id),
                    )
                inserted += 1
        conn.commit()
    return inserted


def reset_all_posts() -> None:
    """Kosongkan semua post & keanggotaannya (untuk mulai ulang saat tes)."""
    with get_pool().connection() as conn:
        conn.execute("TRUNCATE post_campaigns, posts RESTART IDENTITY")
        conn.commit()


# ---------------------------------------------------------------------
# Guidance
# ---------------------------------------------------------------------
def get_guidance(campaign_name: str) -> dict[str, Any] | None:
    cid = get_campaign_id(campaign_name)
    if cid is None:
        return None
    with get_pool().connection() as conn:
        row = conn.execute(
            "SELECT guidance FROM campaign_guidance WHERE campaign_id = %s", (cid,)
        ).fetchone()
    return row[0] if row else None


def upsert_guidance(campaign_name: str, guidance: dict[str, Any]) -> None:
    cid = ensure_campaigns([campaign_name])[_norm(campaign_name)]
    with get_pool().connection() as conn:
        conn.execute(
            """
            INSERT INTO campaign_guidance (campaign_id, guidance, updated_at)
            VALUES (%s,%s,now())
            ON CONFLICT (campaign_id) DO UPDATE SET guidance = EXCLUDED.guidance, updated_at = now()
            """,
            (cid, psycopg.types.json.Json(guidance)),
        )
        conn.commit()


# ---------------------------------------------------------------------
# Generated outputs (histori)
# ---------------------------------------------------------------------
def save_output(campaign_name: str | None, kind: str, params: dict, result: dict) -> int:
    cid = get_campaign_id(campaign_name) if campaign_name else None
    with get_pool().connection() as conn:
        row = conn.execute(
            "INSERT INTO generated_outputs (campaign_id, kind, params, result) VALUES (%s,%s,%s,%s) RETURNING id",
            (cid, kind, psycopg.types.json.Json(params), psycopg.types.json.Json(result)),
        ).fetchone()
        conn.commit()
    return row[0]


def list_outputs(campaign_name: str | None = None, kind: str | None = None, limit: int = 20) -> list[dict]:
    where, params = [], []
    if campaign_name:
        where.append("campaign_id = %s"); params.append(get_campaign_id(campaign_name))
    if kind:
        where.append("kind = %s"); params.append(kind)
    sql = "SELECT id, campaign_id, kind, params, result, created_at FROM generated_outputs"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC LIMIT %s"; params.append(limit)
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()


# ---------------------------------------------------------------------
# Analitik: hitung & breakdown, serta ambil raw data (untuk ekspor)
# ---------------------------------------------------------------------
def _date_where(start_date, end_date):
    """Bangun klausa tanggal (akhir hari inklusif) untuk query."""
    where, params = [], []
    if start_date:
        where.append("p.post_date >= %s::date")
        params.append(start_date)
    if end_date:
        # < (tanggal akhir + 1 hari) -> seluruh hari tanggal akhir ikut terhitung
        where.append("p.post_date < (%s::date + interval '1 day')")
        params.append(end_date)
    return where, params


def count_and_breakdown(campaign_name, start_date=None, end_date=None):
    """Jumlah post + pecahan per channel & per sentiment (difilter di SQL)."""
    cid = get_campaign_id(campaign_name)
    if cid is None:
        return None
    dwhere, dparams = _date_where(start_date, end_date)
    base_where = "pc.campaign_id = %s" + ("" if not dwhere else " AND " + " AND ".join(dwhere))
    base_params = [cid] + dparams
    join = "FROM posts p JOIN post_campaigns pc ON pc.post_id = p.id WHERE " + base_where

    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_UNIQ} {join}", base_params)
            total = cur.fetchone()[0]

            cur.execute(
                f"SELECT coalesce(nullif(p.channel,''),'(tidak diketahui)') AS ch, {_UNIQ} AS n "
                f"{join} GROUP BY ch ORDER BY n DESC",
                base_params,
            )
            channels = cur.fetchall()

            cur.execute(
                f"SELECT coalesce(nullif(p.sentiment,''),'(tidak diketahui)') AS s, {_UNIQ} AS n "
                f"{join} GROUP BY s ORDER BY n DESC",
                base_params,
            )
            sentiments = cur.fetchall()

            # engagement per sentiment (untuk Net Sentiment engagement-weighted)
            cur.execute(
                "SELECT lower(p.sentiment) AS s, sum(coalesce(p.engagement,0)) "
                f"{join} AND lower(p.sentiment) IN ('positive','negative','neutral') "
                "GROUP BY lower(p.sentiment)",
                base_params,
            )
            sent_eng = {row[0]: (row[1] or 0) for row in cur.fetchall()}
    return {"total": total, "channels": channels, "sentiments": sentiments,
            "sentiment_engagement": sent_eng}


def fetch_raw_records(campaign_name, start_date=None, end_date=None, limit=None):
    """Ambil kolom `raw` (data asli lengkap) untuk diekspor jadi CSV."""
    cid = get_campaign_id(campaign_name)
    if cid is None:
        return None
    dwhere, dparams = _date_where(start_date, end_date)
    where = "pc.campaign_id = %s" + ("" if not dwhere else " AND " + " AND ".join(dwhere))
    params = [cid] + dparams
    sql = (
        "SELECT p.raw FROM posts p JOIN post_campaigns pc ON pc.post_id = p.id "
        f"WHERE {where} ORDER BY p.post_date"
    )
    if limit:
        sql += " LIMIT %s"
        params.append(int(limit))
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [row[0] for row in cur.fetchall()]


# ---------------------------------------------------------------------
# Metrik (engagement, likes/comments/shares/views/replies/retweets) & author
# Metrik diambil dari kolom raw (data asli). Pembacaan angka dibuat aman:
# karakter non-angka dibuang dulu, kosong dianggap 0.
# ---------------------------------------------------------------------
def _num(key: str) -> str:
    return (
        "COALESCE(NULLIF(regexp_replace(p.raw->>'" + key + "', '[^0-9.-]', '', 'g'), "
        "'')::numeric, 0)"
    )


# Hitung post UNIK dalam 1 campaign: dedup berdasarkan Link URL; post tanpa
# URL dihitung sendiri (pakai id). Beda campaign tidak dianggap dobel.
_UNIQ = "count(DISTINCT coalesce(nullif(p.url,''), p.id::text))"


def metrics_breakdown(campaign_name, start_date=None, end_date=None, channel=None):
    """Jumlah metrik per channel (engagement, likes, comments, shares, views,
    replies, retweets) untuk satu campaign + rentang tanggal."""
    cid = get_campaign_id(campaign_name)
    if cid is None:
        return None
    dwhere, dparams = _date_where(start_date, end_date)
    where = "pc.campaign_id = %s" + ("" if not dwhere else " AND " + " AND ".join(dwhere))
    params = [cid] + dparams
    if channel:
        where += " AND lower(p.channel) = lower(%s)"
        params.append(channel)
    sql = f"""
        SELECT coalesce(nullif(p.channel,''),'(tidak diketahui)') AS ch,
               {_UNIQ}                          AS posts,
               sum(coalesce(p.engagement,0))    AS engagement,
               sum({_num('Likes')})             AS likes,
               sum({_num('Comments')})          AS comments,
               sum({_num('Shares')})            AS shares,
               sum({_num('Views')})             AS views,
               sum({_num('Replies')})           AS replies,
               sum({_num('Retweets')})          AS retweets,
               sum({_num('Buzz')})              AS buzz,
               sum({_num('Ad Value')})          AS ad_value,
               sum({_num('PR Value')})          AS pr_value
        FROM posts p JOIN post_campaigns pc ON pc.post_id = p.id
        WHERE {where}
        GROUP BY ch ORDER BY engagement DESC
    """
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def top_authors(campaign_name, start_date=None, end_date=None, limit=10):
    """Top author by total engagement, IDENTITAS = author + channel (akun di
    channel berbeda dihitung terpisah). Tiap entri: total engagement, jumlah
    post, sentiment, dan post terbaiknya."""
    cid = get_campaign_id(campaign_name)
    if cid is None:
        return None
    dwhere, dparams = _date_where(start_date, end_date)
    where = (
        "pc.campaign_id = %s AND p.author IS NOT NULL AND p.author <> ''"
        + ("" if not dwhere else " AND " + " AND ".join(dwhere))
    )
    params = [cid] + dparams
    agg_sql = f"""
        SELECT p.author AS author,
               coalesce(nullif(p.channel,''),'(tidak diketahui)') AS channel,
               {_UNIQ} AS posts,
               sum(coalesce(p.engagement,0)) AS total_engagement,
               count(*) FILTER (WHERE p.sentiment='positive') AS pos,
               count(*) FILTER (WHERE p.sentiment='negative') AS neg,
               count(*) FILTER (WHERE p.sentiment='neutral')  AS neu
        FROM posts p JOIN post_campaigns pc ON pc.post_id = p.id
        WHERE {where}
        GROUP BY p.author, channel
        ORDER BY total_engagement DESC
        LIMIT %s
    """
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(agg_sql, params + [int(limit)])
            authors = cur.fetchall()
            if not authors:
                return []
            names = list({a["author"] for a in authors})
            top_sql = f"""
                SELECT DISTINCT ON (p.author, coalesce(nullif(p.channel,''),'(tidak diketahui)'))
                       p.author,
                       coalesce(nullif(p.channel,''),'(tidak diketahui)') AS channel,
                       p.content, p.url, p.sentiment,
                       coalesce(p.engagement,0) AS engagement,
                       {_num('Likes')}    AS likes,
                       {_num('Comments')} AS comments,
                       {_num('Shares')}   AS shares,
                       {_num('Views')}    AS views,
                       {_num('Replies')}  AS replies,
                       {_num('Retweets')} AS retweets
                FROM posts p JOIN post_campaigns pc ON pc.post_id = p.id
                WHERE {where} AND p.author = ANY(%s)
                ORDER BY p.author, channel, coalesce(p.engagement,0) DESC
            """
            cur.execute(top_sql, params + [names])
            top = {(r["author"], r["channel"]): r for r in cur.fetchall()}

    out = []
    for a in authors:
        out.append({
            "author": a["author"],
            "channel": a["channel"],
            "posts": a["posts"],
            "total_engagement": a["total_engagement"],
            "sentiment": {"positive": a["pos"], "negative": a["neg"], "neutral": a["neu"]},
            "top_post": top.get((a["author"], a["channel"]), {}),
        })
    return out


# ---------------------------------------------------------------------
# Timeline harian + ambil post lengkap (semua field) untuk dianalisis
# ---------------------------------------------------------------------
def timeline(campaign_name, start_date=None, end_date=None, channel=None):
    """Breakdown PER TANGGAL: jumlah post, engagement, dan sentiment harian."""
    cid = get_campaign_id(campaign_name)
    if cid is None:
        return None
    dwhere, dparams = _date_where(start_date, end_date)
    where = "pc.campaign_id = %s" + ("" if not dwhere else " AND " + " AND ".join(dwhere))
    params = [cid] + dparams
    if channel:
        where += " AND lower(p.channel) = lower(%s)"
        params.append(channel)
    sql = f"""
        SELECT p.post_date::date AS day,
               {_UNIQ} AS posts,
               sum(coalesce(p.engagement,0)) AS engagement,
               count(*) FILTER (WHERE p.sentiment='positive') AS pos,
               count(*) FILTER (WHERE p.sentiment='negative') AS neg,
               count(*) FILTER (WHERE p.sentiment='neutral')  AS neu
        FROM posts p JOIN post_campaigns pc ON pc.post_id = p.id
        WHERE {where}
        GROUP BY day ORDER BY day
    """
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def get_posts(campaign_name, start_date=None, end_date=None, channel=None,
              sentiment=None, sort_by="engagement", limit=50):
    """Ambil post LENGKAP (tanggal, channel, author, konten, sentiment, url,
    semua metrik) sekaligus, terfilter & terurut, dengan batas jumlah. Dipakai
    Claude untuk membaca konten asli dan menganalisis isu/timeline sendiri."""
    cid = get_campaign_id(campaign_name)
    if cid is None:
        return None
    dwhere, dparams = _date_where(start_date, end_date)
    where = "pc.campaign_id = %s" + ("" if not dwhere else " AND " + " AND ".join(dwhere))
    params = [cid] + dparams
    if channel:
        where += " AND lower(p.channel) = lower(%s)"
        params.append(channel)
    if sentiment:
        where += " AND p.sentiment = %s"
        params.append(sentiment.strip().lower())

    if sort_by == "date":
        order = "p.post_date ASC"
    elif sort_by == "date_desc":
        order = "p.post_date DESC"
    else:
        order = "coalesce(p.engagement,0) DESC"

    sql = f"""
        SELECT p.post_date, p.channel, p.author, p.sentiment, p.url,
               p.title, p.content,
               coalesce(p.engagement,0) AS engagement,
               {_num('Likes')}    AS likes,
               {_num('Comments')} AS comments,
               {_num('Shares')}   AS shares,
               {_num('Views')}    AS views,
               {_num('Replies')}  AS replies,
               {_num('Retweets')} AS retweets
        FROM posts p JOIN post_campaigns pc ON pc.post_id = p.id
        WHERE {where}
        ORDER BY {order}
        LIMIT %s
    """
    params.append(int(limit))
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()


# ---------------------------------------------------------------------
# Ringkasan satu periode (dipakai untuk perbandingan & share of voice)
# ---------------------------------------------------------------------
def period_totals(campaign_name, start_date=None, end_date=None, channel=None):
    """Total post, engagement, dan sentiment untuk 1 campaign + 1 rentang."""
    cid = get_campaign_id(campaign_name)
    if cid is None:
        return None
    dwhere, dparams = _date_where(start_date, end_date)
    where = "pc.campaign_id = %s" + ("" if not dwhere else " AND " + " AND ".join(dwhere))
    params = [cid] + dparams
    if channel:
        where += " AND lower(p.channel) = lower(%s)"
        params.append(channel)
    sql = f"""
        SELECT {_UNIQ} AS posts,
               sum(coalesce(p.engagement,0)) AS engagement,
               sum({_num('Buzz')}) AS buzz,
               count(*) FILTER (WHERE p.sentiment='positive') AS pos,
               count(*) FILTER (WHERE p.sentiment='negative') AS neg,
               count(*) FILTER (WHERE p.sentiment='neutral')  AS neu
        FROM posts p JOIN post_campaigns pc ON pc.post_id = p.id
        WHERE {where}
    """
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchone()


# ---------------------------------------------------------------------
# Top post (paling viral) berdasarkan metrik pilihan
# ---------------------------------------------------------------------
def top_posts(campaign_name, start_date=None, end_date=None, channel=None,
              by="engagement", limit=10):
    """Post individual teratas, diurut by metrik (engagement/views/shares/
    likes/comments/viral). Mengembalikan konten + link + semua metrik."""
    cid = get_campaign_id(campaign_name)
    if cid is None:
        return None
    dwhere, dparams = _date_where(start_date, end_date)
    where = "pc.campaign_id = %s" + ("" if not dwhere else " AND " + " AND ".join(dwhere))
    params = [cid] + dparams
    if channel:
        where += " AND lower(p.channel) = lower(%s)"
        params.append(channel)

    order_map = {
        "engagement": "coalesce(p.engagement,0)",
        "views": _num("Views"),
        "shares": _num("Shares"),
        "likes": _num("Likes"),
        "comments": _num("Comments"),
        "viral": _num("Viral Score"),
    }
    order = order_map.get(by, "coalesce(p.engagement,0)")

    sql = f"""
        SELECT p.post_date, p.channel, p.author, p.sentiment, p.url, p.content,
               coalesce(p.engagement,0) AS engagement,
               {_num('Likes')}    AS likes,
               {_num('Comments')} AS comments,
               {_num('Shares')}   AS shares,
               {_num('Views')}    AS views,
               {_num('Replies')}  AS replies,
               {_num('Retweets')} AS retweets,
               {_num('Viral Score')} AS viral_score
        FROM posts p JOIN post_campaigns pc ON pc.post_id = p.id
        WHERE {where}
        ORDER BY {order} DESC
        LIMIT %s
    """
    params.append(int(limit))
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()


# ---------------------------------------------------------------------
# Top media outlet (online media) berdasarkan Ad Value
# Ad Value = nilai pemberitaan per MEDIA (kolom "Media Name"), bukan engagement.
# ---------------------------------------------------------------------
def top_media(campaign_name, start_date=None, end_date=None, keyword=None, limit=10):
    """Daftar media outlet (Media Name) beserta ad value & jumlah artikelnya,
    diurut by ad value. Bisa difilter kata kunci (untuk fokus ke 1 isu/topik)."""
    cid = get_campaign_id(campaign_name)
    if cid is None:
        return None
    dwhere, dparams = _date_where(start_date, end_date)
    where = (
        "pc.campaign_id = %s "
        "AND p.raw->>'Media Name' IS NOT NULL AND p.raw->>'Media Name' <> ''"
        + ("" if not dwhere else " AND " + " AND ".join(dwhere))
    )
    params = [cid] + dparams
    if keyword:
        where += " AND (p.title ILIKE %s OR p.content ILIKE %s)"
        kw = f"%{keyword}%"
        params += [kw, kw]
    sql = f"""
        SELECT p.raw->>'Media Name' AS media,
               {_UNIQ} AS articles,
               sum({_num('Ad Value')}) AS ad_value,
               sum({_num('PR Value')}) AS pr_value
        FROM posts p JOIN post_campaigns pc ON pc.post_id = p.id
        WHERE {where}
        GROUP BY media
        ORDER BY ad_value DESC NULLS LAST
        LIMIT %s
    """
    params.append(int(limit))
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()


# ---------------------------------------------------------------------
# Data health / coverage: bukti data + keterbatasan (untuk Stage C engine report)
# ---------------------------------------------------------------------
def data_health(campaign_name, start_date=None, end_date=None):
    """Ringkasan ketersediaan data: n post unik, rentang tanggal aktual, channel
    yang ada, dan % coverage tiap metrik (sentiment, engagement, buzz, ad value).
    Dipakai untuk membuktikan data & menyebut keterbatasan secara jujur."""
    cid = get_campaign_id(campaign_name)
    if cid is None:
        return None
    dwhere, dparams = _date_where(start_date, end_date)
    where = "pc.campaign_id = %s" + ("" if not dwhere else " AND " + " AND ".join(dwhere))
    params = [cid] + dparams
    join = "FROM posts p JOIN post_campaigns pc ON pc.post_id = p.id WHERE " + where
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""SELECT {_UNIQ} AS n_unique,
                           count(*) AS n_rows,
                           min(p.post_date)::date AS date_min,
                           max(p.post_date)::date AS date_max,
                           count(*) FILTER (WHERE lower(p.sentiment) IN ('positive','negative','neutral')) AS has_sentiment,
                           count(*) FILTER (WHERE coalesce(p.engagement,0) > 0) AS has_engagement,
                           count(*) FILTER (WHERE {_num('Buzz')} > 0) AS has_buzz,
                           count(*) FILTER (WHERE {_num('Ad Value')} > 0) AS has_ad_value
                    {join}""",
                params,
            )
            row = cur.fetchone()
            cur.execute(
                f"SELECT coalesce(nullif(p.channel,''),'(tidak diketahui)') AS ch, count(*) AS n "
                f"{join} GROUP BY ch ORDER BY n DESC",
                params,
            )
            channels = cur.fetchall()
    return {"row": row, "channels": channels}
