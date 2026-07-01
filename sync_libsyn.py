#!/usr/bin/env python3
"""
sync_libsyn.py — Load a Libsyn episode CSV or ZIP and write data/libsyn.json.
Usage: python3 sync_libsyn.py --file <csv_or_zip>

Replaces all podcast data each time (Libsyn download totals update over time).
"""
import argparse, csv, io, json, zipfile
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "libsyn.json"


def find_col(headers, *candidates):
    lower = [h.lower().strip() for h in headers]
    for c in candidates:
        for i, h in enumerate(lower):
            if c in h:
                return i
    return None


def parse_rows(text):
    text = text.lstrip("﻿")
    return list(csv.reader(io.StringIO(text)))


def parse_file(path):
    p = Path(path)
    if p.suffix.lower() == ".zip":
        with zipfile.ZipFile(p) as zf:
            candidates = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            preferred  = [n for n in candidates if any(k in n.lower() for k in ("episode", "title", "total"))]
            target     = preferred[0] if preferred else (candidates[0] if candidates else None)
            if not target:
                raise SystemExit("No CSV found inside ZIP")
            text = zf.read(target).decode("utf-8-sig", errors="replace")
    else:
        text = p.read_text(encoding="utf-8-sig", errors="replace")

    rows = parse_rows(text)
    if not rows or len(rows) < 2:
        raise SystemExit("CSV appears empty")

    headers   = rows[0]
    title_col = find_col(headers, "title", "episode", "name", "show")
    dl_col    = find_col(headers, "download", "total", "play", "listen", "count")
    date_col  = find_col(headers, "release", "publish", "date")

    if title_col is None or dl_col is None:
        raise SystemExit(f"Could not identify columns. Headers found: {headers}")

    episodes = []
    for row in rows[1:]:
        if len(row) <= max(title_col, dl_col):
            continue
        title = row[title_col].strip()
        raw   = row[dl_col].strip().replace(",", "")
        if not title or not raw.isdigit():
            continue
        date = row[date_col].strip()[:10] if date_col and len(row) > date_col else None
        episodes.append({"title": title, "release_date": date, "downloads": int(raw)})
    return episodes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    args = parser.parse_args()

    episodes = sorted(parse_file(args.file), key=lambda e: (e["release_date"] or ""))
    if not episodes:
        raise SystemExit("No valid episode rows found")

    cumulative, result = 0, []
    for e in episodes:
        cumulative += e["downloads"]
        result.append({**e, "cumulative": cumulative})

    DATA_FILE.write_text(json.dumps(result, indent=2))
    print(f"Wrote {len(result)} episodes to {DATA_FILE} (total downloads: {cumulative})")


if __name__ == "__main__":
    main()
