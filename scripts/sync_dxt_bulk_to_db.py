from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
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


def native_campaign_ids(row: dict[str, Any]) -> list[int]:
    value = row.get("campaign_id_ls")

    if value is None:
        return []

    if isinstance(value, (list, tuple, set)):
        raw_items = list(value)
    else:
        text = str(value).strip()
        if not text:
            return []
        if text.startswith("[") and text.endswith("]"):
            try:
                raw_items = json.loads(text)
            except Exception:
                raw_items = text.strip("[]").split(",")
        else:
            raw_items = text.split(",")

    out: list[int] = []
    for item in raw_items:
        try:
            out.append(int(str(item).strip()))
        except Exception:
            continue

    return sorted(set(out))


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


def ensure_campaign_id_map(campaign_names: list[str]) -> dict[str, int]:
    unique_names = sorted({str(name).strip() for name in campaign_names if str(name).strip()})
    result: dict[str, int] = {}

    with db.get_pool().connection() as conn:
        for name in unique_names:
            name_norm = db._norm(name) if hasattr(db, "_norm") else " ".join(name.lower().split())

            row = conn.execute(
                """
                SELECT id
                FROM campaigns
                WHERE name_norm = %s OR name = %s
                ORDER BY id ASC
                LIMIT 1
                """,
                (name_norm, name),
            ).fetchone()

            if row:
                result[name] = int(row[0])
                continue

            row = conn.execute(
                """
                INSERT INTO campaigns (name, name_norm)
                VALUES (%s, %s)
                RETURNING id
                """,
                (name, name_norm),
            ).fetchone()

            result[name] = int(row[0])

        conn.commit()

    return result


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


def clean_text(value):
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "nat"}:
        return None

    return text


def json_safe(raw: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for key, value in raw.items():
        if value is None:
            out[str(key)] = None
        elif isinstance(value, float) and pd.isna(value):
            out[str(key)] = None
        elif hasattr(value, "isoformat"):
            out[str(key)] = value.isoformat()
        elif hasattr(value, "item"):
            try:
                out[str(key)] = value.item()
            except Exception:
                out[str(key)] = str(value)
        elif isinstance(value, (str, int, float, bool, list, dict)):
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


def upsert_dashboard_row(
    cur,
    dashboard_row: dict[str, Any],
    native_row: dict[str, Any],
    selected_campaign_names: list[str],
):
    dxt_sync_key = make_dxt_sync_key(native_row)

    dashboard_row = dict(dashboard_row)
    dashboard_row["Campaigns"] = ", ".join(selected_campaign_names)

    raw = json_safe(dashboard_row)
    raw["_dxt_sync"] = {
        "key": dxt_sync_key,
        "selected_campaigns": selected_campaign_names,
        "native_campaign_id_ls": native_row.get("campaign_id_ls"),
        "uuid_s": native_row.get("uuid_s"),
        "object_id_s": native_row.get("object_id_s"),
        "row_id_l": native_row.get("row_id_l"),
        "id": native_row.get("id"),
        "inserted_by": "sync_dxt_bulk_to_db.py",
    }

    post_date = parse_post_datetime(dashboard_row)
    channel = clean_text(dashboard_row.get("Channel"))
    author = clean_text(dashboard_row.get("Author"))
    title = clean_text(dashboard_row.get("Title"))
    content = clean_text(dashboard_row.get("Content"))
    sentiment = clean_text(dashboard_row.get("Sentiment"))
    engagement = to_number(dashboard_row.get("Engagement"))
    potential_reach = to_number(dashboard_row.get("Potential Reach"))
    url = clean_text(dashboard_row.get("Link URL"))
    source_no = clean_text(dashboard_row.get("No"))

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


def sync_client_bulk(
    client_cfg: dict[str, Any],
    channel_ids: list[int],
    start_date: str,
    end_date: str,
    dry_run: bool,
    commit_every: int,
) -> dict[str, Any]:
    client = client_cfg["client"]
    selected_campaigns = client_cfg.get("selected_campaigns") or []

    selected_map = {
        int(item["campaign_id"]): str(item["campaign_name"])
        for item in selected_campaigns
    }
    selected_ids = sorted(selected_map.keys())
    selected_names = [selected_map[campaign_id] for campaign_id in selected_ids]

    result = {
        "client": client,
        "campaign_ids": selected_ids,
        "campaign_names": selected_names,
        "start_date": start_date,
        "end_date": end_date,
        "fetched_rows": 0,
        "unique_rows_processed": 0,
        "inserted_posts": 0,
        "updated_posts": 0,
        "relations_created": 0,
        "skipped_no_selected_campaign": 0,
        "dry_run": dry_run,
    }

    if not selected_ids:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result

    api = get_dxt_api(client)

    try:
        campaign_map = build_campaign_map(api)
        tag_map = build_tag_map(api, selected_ids)

        rows = api.fetch_rawdata(
            start_date=parse_date_to_epoch(start_date),
            end_date=parse_date_to_epoch(end_date),
            campaign_ids=selected_ids,
            query="",
            channel_ids=channel_ids,
        )

        df = convert_rows_to_dashboard_format(
            rows=rows,
            campaign_map=campaign_map,
            tag_map=tag_map,
            dashboard_name=f"DXT Bulk Sync - {client}",
        )

    finally:
        close = getattr(api, "close", None)
        if callable(close):
            close()

    result["fetched_rows"] = len(rows)

    if dry_run:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result

    campaign_id_map = ensure_campaign_id_map(selected_names)

    with db.get_pool().connection() as conn:
        with conn.cursor() as cur:
            for idx, native_row in enumerate(rows):
                native_ids = native_campaign_ids(native_row)
                selected_campaign_names = [
                    selected_map[campaign_id]
                    for campaign_id in native_ids
                    if campaign_id in selected_map
                ]

                if not selected_campaign_names:
                    result["skipped_no_selected_campaign"] += 1
                    continue

                dashboard_row = df.iloc[idx].to_dict()

                try:
                    post_id, action = upsert_dashboard_row(
                        cur=cur,
                        dashboard_row=dashboard_row,
                        native_row=native_row,
                        selected_campaign_names=selected_campaign_names,
                    )

                    result["unique_rows_processed"] += 1

                    if action == "inserted":
                        result["inserted_posts"] += 1
                    else:
                        result["updated_posts"] += 1

                    for campaign_name in selected_campaign_names:
                        cogan_campaign_id = campaign_id_map[campaign_name]
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

                    if result["unique_rows_processed"] % commit_every == 0:
                        conn.commit()
                        print(
                            "BULK_PROGRESS",
                            json.dumps(
                                {
                                    "processed": result["unique_rows_processed"],
                                    "inserted": result["inserted_posts"],
                                    "updated": result["updated_posts"],
                                    "relations": result["relations_created"],
                                },
                                ensure_ascii=False,
                            ),
                        )

                except Exception as e:
                    print("ROW_INSERT_FAILED")
                    print("idx=", idx)
                    print("native_campaign_id_ls=", native_row.get("campaign_id_ls"))
                    print("selected_campaign_names=", selected_campaign_names)
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
    parser.add_argument("--commit-every", type=int, default=1000)
    args = parser.parse_args()

    config = load_config(args.config)
    start_date, end_date = resolve_window(args, config)
    channel_ids = config.get("channel_ids") or ALL_CHANNEL_IDS

    if not args.dry_run:
        db.init_db()
        ensure_sync_columns()

    print("DXT_BULK_SYNC_START")
    print("WINDOW=", start_date, "to", end_date)
    print("CHANNEL_IDS=", channel_ids)
    print("DRY_RUN=", args.dry_run)

    all_results = []

    for client_cfg in config.get("clients", []):
        if not client_cfg.get("enabled", True):
            continue

        result = sync_client_bulk(
            client_cfg=client_cfg,
            channel_ids=channel_ids,
            start_date=start_date,
            end_date=end_date,
            dry_run=args.dry_run,
            commit_every=args.commit_every,
        )
        all_results.append(result)

    print("DXT_BULK_SYNC_DONE")
    print(json.dumps(all_results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
