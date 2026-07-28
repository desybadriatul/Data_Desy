import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path


def now_jkt_date():
    return (datetime.utcnow() + timedelta(hours=7)).date()


def daterange(start_date, end_date):
    current = start_date
    while current < end_date:
        next_date = current + timedelta(days=1)
        yield current.isoformat(), next_date.isoformat()
        current = next_date


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--commit-every", default="1000")
    parser.add_argument("--sleep", type=float, default=1.0)
    args = parser.parse_args()

    config_path = Path(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))

    today = now_jkt_date()

    if args.start_date and args.end_date:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
    else:
        lookback_days = int(config.get("lookback_days", 1))
        start_date = today - timedelta(days=lookback_days)
        end_date = today + timedelta(days=1)

    channel_ids = config.get("channel_ids") or [3]

    print("SAFE_CHUNK_SYNC_START", flush=True)
    print(f"CONFIG={args.config}", flush=True)
    print(f"WINDOW={start_date.isoformat()} to {end_date.isoformat()}", flush=True)
    print(f"CHANNEL_IDS={channel_ids}", flush=True)

    failures = []
    total_chunks = 0

    env = os.environ.copy()
    env["PYTHONPATH"] = env.get("PYTHONPATH") or "."

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        for client_cfg in config.get("clients", []):
            if not client_cfg.get("enabled", True):
                continue

            client_name = client_cfg["client"]
            campaigns = client_cfg.get("selected_campaigns", [])

            for campaign in campaigns:
                campaign_id = campaign.get("campaign_id")
                campaign_name = campaign.get("campaign_name")

                for channel_id in channel_ids:
                    for chunk_start, chunk_end in daterange(start_date, end_date):
                        total_chunks += 1

                        chunk_config = {
                            "lookback_days": 0,
                            "channel_ids": [channel_id],
                            "clients": [
                                {
                                    "enabled": True,
                                    "client": client_name,
                                    "selected_campaigns": [campaign],
                                }
                            ],
                        }

                        tmp_config_path = tmpdir_path / f"chunk_{client_name}_{campaign_id}_{channel_id}_{chunk_start}.json"
                        tmp_config_path.write_text(
                            json.dumps(chunk_config, ensure_ascii=False),
                            encoding="utf-8",
                        )

                        print(
                            "SAFE_CHUNK_START "
                            f"client={client_name} "
                            f"campaign_id={campaign_id} "
                            f"campaign_name={campaign_name} "
                            f"channel_id={channel_id} "
                            f"window={chunk_start}_to_{chunk_end}",
                            flush=True,
                        )

                        cmd = [
                            sys.executable,
                            "scripts/sync_dxt_bulk_to_db.py",
                            "--config",
                            str(tmp_config_path),
                            "--start-date",
                            chunk_start,
                            "--end-date",
                            chunk_end,
                            "--commit-every",
                            str(args.commit_every),
                        ]

                        result = subprocess.run(cmd, env=env)

                        if result.returncode == 0:
                            print(
                                "SAFE_CHUNK_DONE "
                                f"campaign_id={campaign_id} "
                                f"channel_id={channel_id} "
                                f"window={chunk_start}_to_{chunk_end}",
                                flush=True,
                            )
                        else:
                            failure = {
                                "campaign_id": campaign_id,
                                "campaign_name": campaign_name,
                                "channel_id": channel_id,
                                "start_date": chunk_start,
                                "end_date": chunk_end,
                                "returncode": result.returncode,
                            }
                            failures.append(failure)
                            print("SAFE_CHUNK_FAILED " + json.dumps(failure, ensure_ascii=False), flush=True)

                        if args.sleep:
                            time.sleep(args.sleep)

    print("SAFE_CHUNK_SYNC_DONE", flush=True)
    print(f"TOTAL_CHUNKS={total_chunks}", flush=True)
    print(f"FAILED_CHUNKS={len(failures)}", flush=True)

    if failures:
        print("SAFE_CHUNK_FAILURES=" + json.dumps(failures, ensure_ascii=False, indent=2), flush=True)

    # sengaja exit 0 supaya chunk lain yang berhasil tetap dianggap selesai oleh Railway
    # failure detail tetap muncul di logs untuk rerun manual per tanggal/campaign.
    sys.exit(0)


if __name__ == "__main__":
    main()
