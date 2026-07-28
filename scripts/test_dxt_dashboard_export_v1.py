import argparse
import json
import os
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from dopscheduler.pipelines.dxt_api import get_dxt_api


TARGET_COLUMNS = [
    "No", "Dashboard Name", "Widget Name", "Campaigns", "Tags", "Channel", "Type",
    "Date", "Time", "Hour", "Author", "Channel URL", "Verified Account", "Title",
    "Content", "Image Description", "Language", "Country", "Extracted Text", "Buzz",
    "Original Reach", "Viral Reach", "Potential Reach", "Viral Score", "Engagement",
    "Replies", "Retweets", "Comments", "Likes", "Shares", "Views", "Ad Value",
    "PR Value", "Readership", "Author Like", "Circulation", "Media Name", "Link URL",
    "Link URL Tracking", "Image URL", "Video URL", "ABSA Result", "Sentiment", "Mood",
    "Media Type", "Spokesperson", "Aspect Based Sentiment", "Generic Sentiment Analysis",
    "Topic Extraction", "People Extraction", "Entity Extraction", "Noun",
    "Sentence Type Classification", "Labels", "Age", "Gender"
]

CHANNEL_MAP = {
    1: "Twitter",
    2: "Facebook",
    3: "OnlineMedia",
    4: "Forum",
    5: "Blog",
    6: "Instagram",
    7: "Youtube",
    8: "PrintedMedia",
    9: "Radio",
    10: "TV",
    11: "Tiktok",
}

SOCIAL_CHANNELS = {1, 2, 6, 7, 11}
MAINSTREAM_CHANNELS = {3, 8, 9, 10}


def first_non_empty(*values):
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def load_env(path=".env"):
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ[name.strip()] = value.strip().strip('"').strip("'")


def parse_int_list(value):
    return [int(x.strip()) for x in str(value).split(",") if x.strip()]


def parse_date_to_epoch(date_str):
    tz = ZoneInfo("Asia/Jakarta")
    dt = datetime.fromisoformat(date_str).replace(tzinfo=tz)
    return int(dt.timestamp())


def dt_from_epoch(ts):
    if not ts:
        return None
    return datetime.fromtimestamp(int(ts), tz=ZoneInfo("Asia/Jakarta"))


def sentiment_label(value):
    if value == 1:
        return "positive"
    if value == -1:
        return "negative"
    if value == 0:
        return "neutral"
    return None


def normalize_language(lang_code):
    if lang_code == "id":
        return "Indonesian"
    if lang_code == "en":
        return "English"
    return lang_code


def type_label(row):
    raw = (row.get("type_s") or "").strip().lower()
    channel_id = int(row.get("channel_id_i") or 0)

    if raw == "post":
        if channel_id in [3, 8]:
            return "Article"
        if channel_id == 1:
            return "Tweet"
        if channel_id in [6, 11, 2]:
            return "Post"
        if channel_id == 7:
            return "Video"
        return "Post"

    if raw:
        return raw.title()

    return None


def get_username(row, channel_id):
    if channel_id in [6, 11]:
        return first_non_empty(row.get("username_s"), row.get("author_username_s"))
    if channel_id == 2:
        return row.get("author_username_s")
    if channel_id == 7:
        return first_non_empty(row.get("channel_id_s"), row.get("author_username_s"))
    if channel_id == 1:
        return first_non_empty(row.get("author_username_s"), row.get("username_s"))
    return first_non_empty(row.get("author_username_s"), row.get("username_s"), row.get("channel_id_s"))


def get_author(row):
    channel_id = int(row.get("channel_id_i") or 0)

    if channel_id in SOCIAL_CHANNELS:
        return first_non_empty(
            row.get("author_name_s"),
            row.get("author_username_s"),
            row.get("username_s"),
            row.get("channel_id_s"),
            row.get("omni_author_t"),
        )

    if channel_id in MAINSTREAM_CHANNELS:
        return first_non_empty(
            row.get("reporter_s"),
            row.get("author_name_s"),
            row.get("author_username_s"),
            "Anonymous",
        )

    return first_non_empty(
        row.get("author_name_s"),
        row.get("author_username_s"),
        row.get("omni_author_t"),
        "Anonymous",
    )


def get_channel_url(row):
    channel_id = int(row.get("channel_id_i") or 0)
    username = get_username(row, channel_id)

    if not username:
        return first_non_empty(row.get("channel_url_s"), row.get("author_url_s"))

    username = str(username).replace("@", "").strip()

    if channel_id == 1:
        return f"https://x.com/{username}"
    if channel_id == 6:
        return f"https://www.instagram.com/{username}"
    if channel_id == 11:
        return f"https://www.tiktok.com/@{username}"
    if channel_id == 7:
        return f"https://www.youtube.com/{username}"
    if channel_id == 2:
        return row.get("author_url_s") or row.get("channel_url_s")

    return first_non_empty(row.get("channel_url_s"), row.get("author_url_s"))


def get_avatar_url(row):
    avatar = row.get("author_avatar_s")
    if isinstance(avatar, str):
        return avatar.replace("_normal.", ".")
    return avatar


def get_content(row):
    return first_non_empty(
        row.get("content_t"),
        row.get("raw_content_t"),
        row.get("summary_t"),
        row.get("omni_search_t"),
    )


def get_media_name(row):
    return first_non_empty(row.get("media_name_s"), row.get("station_s"))


def get_spokesperson(row):
    value = row.get("spokesperson_ss")
    if isinstance(value, list):
        return ", ".join([str(x) for x in value if x])
    return value


def build_campaign_map(api):
    data = api.get_campaigns()
    items = data.get("data_list") or data.get("data") or data.get("result") or data.get("campaigns") or []

    campaign_map = {}
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            cid = item.get("id") or item.get("campaign_id") or item.get("_id")
            name = item.get("name") or item.get("campaign_name") or item.get("title")
            if cid is not None and name:
                campaign_map[int(cid)] = str(name)

    return campaign_map


def build_tag_map(api, campaign_ids):
    tag_map = {}

    for cid in campaign_ids:
        try:
            data = api.get_tag(str(cid))
            items = data.get("data_list") if isinstance(data, dict) else []
            names = []
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and item.get("name"):
                        names.append(str(item["name"]))
            tag_map[int(cid)] = ", ".join(names) if names else None
        except Exception as exc:
            print(f"TAG_FETCH_WARNING campaign_id={cid}: {exc}")
            tag_map[int(cid)] = None

    return tag_map


def get_campaign_names(row, campaign_map):
    campaign_ids = row.get("campaign_id_ls") or []
    if not isinstance(campaign_ids, list):
        return None

    names = []
    for cid in campaign_ids:
        try:
            names.append(campaign_map.get(int(cid), str(cid)))
        except Exception:
            names.append(str(cid))

    return ", ".join(names) if names else None


def get_tags(row, tag_map):
    campaign_ids = row.get("campaign_id_ls") or []
    if not isinstance(campaign_ids, list):
        return None

    tags = []
    for cid in campaign_ids:
        tag = tag_map.get(int(cid))
        if tag:
            tags.append(tag)

    deduped = []
    for tag in tags:
        if tag not in deduped:
            deduped.append(tag)

    return ", ".join(deduped) if deduped else None


def convert_rows_to_dashboard_format(rows, campaign_map, tag_map, dashboard_name="-"):
    out_rows = []

    for idx, row in enumerate(rows, start=1):
        dt = dt_from_epoch(row.get("published_ts_l"))
        channel_id = int(row.get("channel_id_i") or 0)
        channel = CHANNEL_MAP.get(channel_id)

        comments = row.get("num_comments_l")
        shares = first_non_empty(row.get("num_share_l"), row.get("num_shares_l"))

        out_rows.append({
            "No": idx,
            "Dashboard Name": dashboard_name,
            "Widget Name": None,
            "Campaigns": get_campaign_names(row, campaign_map),
            "Tags": get_tags(row, tag_map),
            "Channel": channel,
            "Type": type_label(row),
            "Date": dt.strftime("%d-%b-%Y") if dt else None,
            "Time": dt.strftime("%H:%M:%S") if dt else None,
            "Hour": row.get("post_hour_i"),
            "Author": get_author(row),
            "Channel URL": get_channel_url(row),
            "Verified Account": row.get("is_verified_b"),
            "Title": row.get("title_t"),
            "Content": get_content(row),
            "Image Description": None,
            "Language": normalize_language(row.get("lang_code_s")),
            "Country": row.get("country_code_s"),
            "Extracted Text": None,
            "Buzz": row.get("num_buzz_l"),
            "Original Reach": row.get("num_reach_l"),
            "Viral Reach": 0,
            "Potential Reach": row.get("potential_reach_l"),
            "Viral Score": 0,
            "Engagement": row.get("num_eng_l"),
            "Replies": row.get("num_replies_l"),
            "Retweets": row.get("num_rts_l"),
            "Comments": comments,
            "Likes": row.get("num_likes_l"),
            "Shares": shares,
            "Views": row.get("num_views_l"),
            "Ad Value": row.get("ad_value_l"),
            "PR Value": row.get("pr_value_l"),
            "Readership": row.get("unique_visitors_l"),
            "Author Like": row.get("author_like_l"),
            "Circulation": row.get("circulation_l"),
            "Media Name": get_media_name(row),
            "Link URL": row.get("link_s"),
            "Link URL Tracking": None,
            "Image URL": first_non_empty(row.get("image_url_s"), get_avatar_url(row)),
            "Video URL": row.get("video_url_s"),
            "ABSA Result": None,
            "Sentiment": sentiment_label(row.get("sentiment_value_i")),
            "Mood": None,
            "Media Type": row.get("media_coverage_s"),
            "Spokesperson": get_spokesperson(row),
            "Aspect Based Sentiment": None,
            "Generic Sentiment Analysis": None,
            "Topic Extraction": None,
            "People Extraction": None,
            "Entity Extraction": None,
            "Noun": None,
            "Sentence Type Classification": None,
            "Labels": None,
            "Age": row.get("age_i"),
            "Gender": row.get("gender_s"),
        })

    return pd.DataFrame(out_rows, columns=TARGET_COLUMNS)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--client", required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--campaign-ids", required=True)
    parser.add_argument("--channel-ids", default="0")
    parser.add_argument("--query", default="")
    parser.add_argument("--dashboard-name", default="-")
    parser.add_argument("--out-dir", default="exports/dxt_dashboard_format")
    args = parser.parse_args()

    load_env(".env")

    if not os.environ.get("DXT_APP_CODE") or not os.environ.get("DXT_PASS_CODE") or not os.environ.get("DXT_BASE_URL"):
        raise RuntimeError("DXT env belum lengkap: DXT_APP_CODE, DXT_PASS_CODE, DXT_BASE_URL")

    campaign_ids = parse_int_list(args.campaign_ids)
    channel_ids = parse_int_list(args.channel_ids)

    start_ts = parse_date_to_epoch(args.start_date)
    end_ts = parse_date_to_epoch(args.end_date)

    api = get_dxt_api(args.client)

    campaign_map = build_campaign_map(api)
    tag_map = build_tag_map(api, campaign_ids)

    rows = api.fetch_rawdata(
        start_date=start_ts,
        end_date=end_ts,
        campaign_ids=campaign_ids,
        query=args.query,
        channel_ids=channel_ids,
    )

    df = convert_rows_to_dashboard_format(
        rows=rows,
        campaign_map=campaign_map,
        tag_map=tag_map,
        dashboard_name=args.dashboard_name,
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_client = args.client.replace(" ", "_")
    safe_campaigns = "-".join(map(str, campaign_ids))
    safe_channels = "-".join(map(str, channel_ids))

    xlsx_path = out_dir / f"{safe_client}_{args.start_date}_{args.end_date}_campaigns_{safe_campaigns}_channels_{safe_channels}.xlsx"
    json_path = out_dir / f"{safe_client}_{args.start_date}_{args.end_date}_campaigns_{safe_campaigns}_channels_{safe_channels}_native.json"
    meta_path = out_dir / f"{safe_client}_{args.start_date}_{args.end_date}_campaigns_{safe_campaigns}_channels_{safe_channels}_metadata.json"

    df.to_excel(xlsx_path, index=False)

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2, default=str)

    metadata = {
        "client": args.client,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "start_ts": start_ts,
        "end_ts": end_ts,
        "campaign_ids": campaign_ids,
        "channel_ids": channel_ids,
        "query": args.query,
        "dashboard_name": args.dashboard_name,
        "native_rows": len(rows),
        "output_rows": len(df),
        "output_columns": list(df.columns),
        "campaign_map": {str(k): v for k, v in campaign_map.items() if k in campaign_ids},
        "tag_map": {str(k): v for k, v in tag_map.items()},
        "xlsx_path": str(xlsx_path),
        "native_json_path": str(json_path),
    }

    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2, default=str)

    api.close()

    print("DXT_EXPORT_DASHBOARD_FORMAT_OK")
    print("CLIENT=", args.client)
    print("ROWS=", len(df))
    print("COLUMNS=", len(df.columns))
    print("TAG_MAP=", tag_map)
    print("XLSX=", xlsx_path)
    print("NATIVE_JSON=", json_path)
    print("METADATA=", meta_path)


if __name__ == "__main__":
    main()

