#!/usr/bin/env python3
"""
sync_podcast_host.py — Merge self-hosted listen counts with the frozen
historical Libsyn baseline, and write data/libsyn.json for dashboard.shtml.

Replaces the old manual "export CSV from Libsyn, run sync_libsyn.py" step
(removed 2026-08-10; see UPDATE_GUIDE.txt) now that the show is self-hosted at
podcast-feed.transformgov.org.uk — there's no Libsyn download report to
export any more. The sibling podcast-host repo's generator/count_listens.py
(cron'd daily on this same server) counts listens per episode from Apache
logs since the self-host cutover; this script adds those to the frozen
pre-migration Libsyn totals in data/libsyn_baseline.json, matched by
release date (the old Libsyn CSV export never included a guid, but every
episode's GUID *and* publish date were preserved 1:1 through the migration
— see podcast-host's TODO.md item 2/7 — so release_date is a reliable join
key here). data/libsyn_baseline.json is a one-time snapshot and is never
regenerated; only new self-hosted listens accumulate on top of it.

Usage: python3 sync_podcast_host.py
"""
import json
from pathlib import Path

BASELINE_FILE = Path(__file__).parent / "data" / "libsyn_baseline.json"
PODCAST_HOST_FILE = Path("/var/www/podcast-host/data/listens-transformgov-talks.json")
OUTPUT_FILE = Path(__file__).parent / "data" / "libsyn.json"


def main():
    baseline_by_date = {
        e["release_date"]: e["downloads"]
        for e in json.loads(BASELINE_FILE.read_text())
    }
    self_hosted = json.loads(PODCAST_HOST_FILE.read_text())

    result = []
    for e in self_hosted:
        historical = baseline_by_date.get(e["release_date"], 0)
        result.append({
            "title": e["title"],
            "release_date": e["release_date"],
            "downloads": historical + e["listens"],
        })

    result.sort(key=lambda e: e["release_date"] or "")
    cumulative = 0
    for e in result:
        cumulative += e["downloads"]
        e["cumulative"] = cumulative

    OUTPUT_FILE.write_text(json.dumps(result, indent=2))
    print(f"Wrote {len(result)} episodes to {OUTPUT_FILE} (total downloads: {cumulative})")


if __name__ == "__main__":
    main()
