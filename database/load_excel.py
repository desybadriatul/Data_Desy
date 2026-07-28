"""
load_excel.py — muat data Excel/CSV ke database Cogan.

Cara pakai (jalankan dari folder project, setelah DATABASE_URL di-set):

    python -m database.load_excel --init                  # buat tabel
    python -m database.load_excel --file data/namafile.xlsx
    python -m database.load_excel --folder data           # muat semua file di folder
    python -m database.load_excel --reset --folder data   # kosongkan dulu, lalu muat

Kolom 'Campaigns' dipisah koma -> tiap post dicatat ke semua campaign-nya.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

BASE_DIR = Path(__file__).parent.parent
MAPPING_PATH = Path(__file__).parent / "column_mapping.json"
VALID_SENTIMENTS = {"positive", "negative", "neutral"}


def _mapping() -> dict[str, str]:
    data = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    return data["default"]


def _clean(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if v is pd.NaT:
        return None
    return v


def _text(v: Any) -> str | None:
    v = _clean(v)
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _sentiment(v: Any) -> str | None:
    s = _text(v)
    if s is None:
        return None
    s = s.lower()
    return s if s in VALID_SENTIMENTS else "neutral"


def _number(v: Any) -> float | None:
    n = pd.to_numeric(v, errors="coerce")
    return None if pd.isna(n) else float(n)


def _timestamp(v: Any) -> Any:
    t = pd.to_datetime(v, errors="coerce", dayfirst=True)
    return None if pd.isna(t) else t.to_pydatetime()


def _campaign_list(v: Any) -> list[str]:
    s = _text(v)
    if not s:
        return []
    return [part.strip() for part in s.split(",") if part.strip()]


def _json_safe(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, val in raw.items():
        val = _clean(val)
        if val is None:
            out[str(k)] = None
        elif hasattr(val, "isoformat"):
            out[str(k)] = val.isoformat()
        elif isinstance(val, (int, float, bool, str)):
            out[str(k)] = val
        else:
            out[str(k)] = str(val)
    return out


def excel_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """DataFrame mentah -> daftar record. PURE (tanpa database) supaya gampang dites."""
    m = _mapping()
    records = []
    for _, row in df.iterrows():
        d = row.to_dict()
        records.append({
            "source_no": _clean(d.get(m["source_no"])),
            "post_date": _timestamp(d.get(m["post_date"])),
            "channel": _text(d.get(m["channel"])),
            "author": _text(d.get(m["author"])),
            "title": _text(d.get(m["title"])),
            "content": _text(d.get(m["content"])),
            "sentiment": _sentiment(d.get(m["sentiment"])),
            "engagement": _number(d.get(m["engagement"])),
            "potential_reach": _number(d.get(m["potential_reach"])),
            "url": _text(d.get(m["url"])),
            "campaigns": _campaign_list(d.get(m["campaigns"])),
            "raw": _json_safe(d),
        })
    return records


def _read_any(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".csv", ".tsv"}:
        return pd.read_csv(path, sep="\t" if path.suffix.lower() == ".tsv" else ",")
    return pd.read_excel(path)


def load_file(path: Path, batch_size: int = 1000) -> int:
    from . import db
    df = _read_any(path)
    records = excel_to_records(df)
    total = 0
    n = len(records)
    print(f"  [{path.name}] membaca {n} baris, mulai upload...")
    for i in range(0, n, batch_size):
        total += db.insert_posts_with_campaigns(records[i:i + batch_size])
        print(f"    ...{min(i + batch_size, n)}/{n} post")
    print(f"  [{path.name}] SELESAI: {total} post dimuat")
    return total


def load_folder(folder: Path, batch_size: int = 1000) -> None:
    files = sorted([p for p in folder.iterdir()
                    if p.suffix.lower() in {".xlsx", ".xls", ".csv", ".tsv"}])
    if not files:
        print(f"Tidak ada file Excel/CSV di {folder}")
        return
    for f in files:
        load_file(f, batch_size=batch_size)


def main() -> None:
    ap = argparse.ArgumentParser(description="Loader data Excel/CSV -> database Cogan")
    ap.add_argument("--init", action="store_true", help="buat tabel kalau belum ada")
    ap.add_argument("--reset", action="store_true", help="kosongkan semua post dulu")
    ap.add_argument("--file", help="path 1 file Excel/CSV")
    ap.add_argument("--folder", help="folder berisi file Excel/CSV")
    ap.add_argument("--batch-size", type=int, default=1000,
                    help="jumlah baris per dorongan (kecilkan jika DB kehabisan memori, mis. 500)")
    args = ap.parse_args()

    if args.init:
        from . import db
        db.init_db()
        print("Tabel siap.")
    if args.reset:
        from . import db
        db.reset_all_posts()
        print("Semua post lama dihapus.")
    if args.file:
        load_file(Path(args.file), batch_size=args.batch_size)
    if args.folder:
        load_folder(Path(args.folder), batch_size=args.batch_size)
    if not any([args.init, args.reset, args.file, args.folder]):
        ap.print_help()


if __name__ == "__main__":
    main()
