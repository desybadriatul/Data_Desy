from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg
from psycopg.types.json import Json

from database import db
from integrations.dxt.dxt_api import get_dxt_api
from integrations.dxt.dxt_dashboard_exporter import (
    build_campaign_map,
    build_tag_map,
    convert_rows_to_dashboard_format,
    parse_date_to_epoch,
)


ALL_CHANNEL_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]


def load_config(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def today_jakarta_date() -> datetime:
    # Untuk scheduler Railway, kita cukup hitung date window dari UTC runtime.
    # Window lookback tetap aman karena ambil ulang beberapa hari terakhir.
    return datetime.utcnow() + timedelta(hours=7)


def resolve_window(args, config: dict[str, Any]) -> tuple[str, str]:
    if args.start_date and args.end_date:
        return args.start_date, args.end_date

    lookback_days = int(args.lookback_days or config.get("lookback_days") or 3)
    today = today_jakarta_date().date()
    start = today - timedelta(days=lookback_days)
    end = today + timedelta(days=1)

    return start.isoformat(), end.isoformat()


def first_non_empty(*values):
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def make_dxt_sync_key(row: dict[str, Any]) -> str:
    uuid = first_non_empty(row.get("uuid_s"))
    if uuid:
        return f"dxt:uuid:{uuid}"

    object_id = first_non_empty(row.get("object_id_s"))
    if object_id:
        return f"dxt:object:{object_id}"

    row_id = first_non_empty(row.get("row_id_l"))
    if row_id:
        return f"dxt:row:{row_id}"

    link = first_non_empty(row.get("link_s"))
    channel_id = first_non_empty(row.get("channel_id_i"))
    if link and channel_id:
        return f"dxt:link:{channel_id}:{link}"

    base = "|".join([
        str(first_non_empty(row.get("channel_id_i"), "")),
        str(first_non_empty(row.get("published_ts_l"), "")),
        str(first_non_empty(row.get("author_name_s"), row.get("author_username_s"), row.get("omni_author_t"), "")),
        str(first_non_empty(row.get("content_t"), row.get("raw_content_t"), row.get("summary_t"), row.get("omni_search_t"), "")),
    ])
    digest = hashlib.sha256(base.encode("utf-8", errors="ignore")).hexdigest()
    return f"dxt:hash:{digest}"


def ensure_sync_columns() -> None:
    with db.get_pool().connection() as conn:
        conn.execute("ALTER TABLE posts ADD COLUMN IF NOT EXISTS dxt_sync_key TEXT")
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_posts_dxt_sync_key
            ON posts (dxt_sync_key)
            WHERE dxt_sync_key IS NOT NULL
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_posts_url_channel
            ON posts (url, channel)
        """)
        conn.commit()


def parse_post_datetime(row: dict[str, Any]):
    date_value = row.get("Date")
    time_value = row.get("Time")

    if not date_value:
        return None

    raw = f"{date_value} {time_value or '00:00:00'}"
    ts = pd.to_datetime(raw, errors="coerce", dayfirst=True)

    if pd.isna(ts):
        return None

    return ts.to_pydatetime()


def to_number(value):
    n = pd.to_numeric(value, errors="coerce")
    if pd.isna(n):
        return None
    return float(n)


def json_safe(raw: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for key, value in raw.items():
        if value is None:
            out[str(key)] = None
        elif isinstance(value, float) and pd.isna(value):
            out[str(key)] = None
        elif hasattr(value, "isoformat"):
            out[str(key)] = value.isoformat()
        elif isinstance(value, (str, int, float, bool)):
            out[str(key)] = value
        else:
            out[str(key)] = str(value)
    return out


def find_existing_post_id(cur, dxt_sync_key: str, url: str | None, channel: str | None):
    row = cur.execute(
        "SELECT id FROM posts WHERE dxt_sync_key = %s LIMIT 1",
        (dxt_sync_key,),
    ).fetchone()
    if row:
        return row[0]

    if url and channel:
        row = cur.execute(
            """
            SELECT id
            FROM posts
            WHERE url = %s
              AND channel = %s
            ORDER BY id ASC
            LIMIT 1
            """,
            (url, channel),
        ).fetchone()
        if row:
            return row[0]

    if url:
        row = cur.execute(
            """
            SELECT id
            FROM posts
            WHERE url = %s
            ORDER BY id ASC
            LIMIT 1
            """,
            (url,),
        ).fetchone()
        if row:
            return row[0]

    return None

def upsert_dashboard_row(cur, dashboard_row: dict[str, Any], native_row: dict[str, Any], selected_campaign_name: str):
    dxt_sync_key = make_dxt_sync_key(native_row)

    # Force campaign: hanya campaign yang dipilih di config.
    dashboard_row = dict(dashboard_row)
    dashboard_row["Campaigns"] = selected_campaign_name

    raw = json_safe(dashboard_row)
    raw["_dxt_sync"] = {
        "key": dxt_sync_key,
        "selected_campaign": selected_campaign_name,
        "native_campaign_id_ls": native_row.get("campaign_id_ls"),
        "uuid_s": native_row.get("uuid_s"),
        "object_id_s": native_row.get("object_id_s"),
        "row_id_l": native_row.get("row_id_l"),
        "id": native_row.get("id"),
        "inserted_by": "sync_dxt_daily_to_db.py",
    }

    post_date = parse_post_datetime(dashboard_row)
    channel = dashboard_row.get("Channel")
    author = dashboard_row.get("Author")
    title = dashboard_row.get("Title")
    content = dashboard_row.get("Content")
    sentiment = dashboard_row.get("Sentiment")
    engagement = to_number(dashboard_row.get("Engagement"))
    potential_reach = to_number(dashboard_row.get("Potential Reach"))
    url = dashboard_row.get("Link URL")
    source_no = dashboard_row.get("No")

    existing_id = find_existing_post_id(cur, dxt_sync_key=dxt_sync_key, url=url, channel=channel)

    if existing_id:
        cur.execute(
            """
            UPDATE posts
            SET
                dxt_sync_key = COALESCE(dxt_sync_key, %s),
                source_no = %s,
                post_date = %s,
                channel = %s,
                author = %s,
                title = %s,
                content = %s,
                sentiment = %s,
                engagement = %s,
                potential_reach = %s,
                url = %s,
                raw = %s,
                loaded_at = now()
            WHERE id = %s
            """,
            (
                dxt_sync_key,
                source_no,
                post_date,
                channel,
                author,
                title,
                content,
                sentiment,
                engagement,
                potential_reach,
                url,
                Json(raw),
                existing_id,
            ),
        )
        return existing_id, "updated"

    row = cur.execute(
        """
        INSERT INTO posts (
            dxt_sync_key,
            source_no,
            post_date,
            channel,
            author,
            title,
            content,
            sentiment,
            engagement,
            potential_reach,
            url,
            raw
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
        """,
        (
            dxt_sync_key,
            source_no,
            post_date,
            channel,
            author,
            title,
            content,
            sentiment,
            engagement,
            potential_reach,
            url,
            Json(raw),
        ),
    ).fetchone()

    return row[0], "inserted"


def sync_one_campaign(
    client: str,
    selected_campaign: dict[str, Any],
    channel_ids: list[int],
    start_date: str,
    end_date: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    campaign_id = int(selected_campaign["campaign_id"])
    campaign_name = str(selected_campaign["campaign_name"])

    api = get_dxt_api(client)

    try:
        campaign_map = build_campaign_map(api)
        tag_map = build_tag_map(api, [campaign_id])

        rows = api.fetch_rawdata(
            start_date=parse_date_to_epoch(start_date),
            end_date=parse_date_to_epoch(end_date),
            campaign_ids=[campaign_id],
            query="",
            channel_ids=channel_ids,
        )

        df = convert_rows_to_dashboard_format(
            rows=rows,
            campaign_map=campaign_map,
            tag_map=tag_map,
            dashboard_name=f"DXT Sync - {client}",
        )

    finally:
        close = getattr(api, "close", None)
        if callable(close):
            close()

    result = {
        "client": client,
        "campaign_id": campaign_id,
        "campaign_name": campaign_name,
        "start_date": start_date,
        "end_date": end_date,
        "fetched_rows": len(rows),
        "inserted_posts": 0,
        "updated_posts": 0,
        "relations_created": 0,
        "dry_run": dry_run,
    }

    if dry_run:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result

    cogan_campaign_id = db.get_campaign_id(campaign_name)

    with db.get_pool().connection() as conn:
        with conn.cursor() as cur:
            for idx, native_row in enumerate(rows):
                try:
                    dashboard_row = df.iloc[idx].to_dict()

                    post_id, action = upsert_dashboard_row(
                        cur=cur,
                        dashboard_row=dashboard_row,
                        native_row=native_row,
                        selected_campaign_name=campaign_name,
                    )

                    if action == "inserted":
                        result["inserted_posts"] += 1
                    else:
                        result["updated_posts"] += 1

                    cur.execute(
                        """
                        INSERT INTO post_campaigns (post_id, campaign_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (post_id, cogan_campaign_id),
                    )
                    if cur.rowcount == 1:
                        result["relations_created"] += 1

                except Exception as e:
                    print("ROW_INSERT_FAILED")
                    print("idx=", idx)
                    print("campaign_name=", campaign_name)
                    print("native_keys=", sorted(list(native_row.keys())) if isinstance(native_row, dict) else type(native_row))
                    print("error_type=", type(e).__name__)
                    print("error=", str(e))
                    raise

        conn.commit()

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/dxt_sync_clients.json")
    parser.add_argument("--start-date", default="")
    parser.add_argument("--end-date", default="")
    parser.add_argument("--lookback-days", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    start_date, end_date = resolve_window(args, config)

    channel_ids = config.get("channel_ids") or ALL_CHANNEL_IDS

    if not args.dry_run:
        db.init_db()
        ensure_sync_columns()

    print("DXT_DAILY_SYNC_START")
    print("WINDOW=", start_date, "to", end_date)
    print("CHANNEL_IDS=", channel_ids)
    print("DRY_RUN=", args.dry_run)

    all_results = []

    for client_cfg in config.get("clients", []):
        if not client_cfg.get("enabled", True):
            continue

        client = client_cfg["client"]
        selected_campaigns = client_cfg.get("selected_campaigns") or []

        for selected_campaign in selected_campaigns:
            result = sync_one_campaign(
                client=client,
                selected_campaign=selected_campaign,
                channel_ids=channel_ids,
                start_date=start_date,
                end_date=end_date,
                dry_run=args.dry_run,
            )
            all_results.append(result)

    print("DXT_DAILY_SYNC_DONE")
    print(json.dumps(all_results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
