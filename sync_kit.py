#!/usr/bin/env python3
"""
sync_kit.py — Fetch Kit mailing list subscribers and write data/subscribers.json.
Usage: python3 sync_kit.py
"""
import json, logging
from pathlib import Path
from collections import defaultdict
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger(__name__)

_secret_path = Path("/home/dave/secrets/transformgov_talks_kit_api_key")
KIT_API_KEY = _secret_path.read_text().strip() if _secret_path.exists() else None
KIT_BASE    = "https://api.kit.com/v4"
HEADERS     = {"X-Kit-Api-Key": KIT_API_KEY, "Accept": "application/json"}
DATA_FILE   = Path(__file__).parent / "data" / "subscribers.json"


def fetch_subscribers():
    params = {"per_page": 500}
    fetched, after_cursor = 0, None
    while True:
        if after_cursor:
            params["after"] = after_cursor
        resp = requests.get(f"{KIT_BASE}/subscribers", headers=HEADERS, params=params, timeout=30)
        resp.raise_for_status()
        data       = resp.json()
        subs       = data.get("subscribers", [])
        pagination = data.get("pagination", {})
        for s in subs:
            yield s
        fetched += len(subs)
        log.info(f"  ...{fetched} fetched")
        if not pagination.get("has_next_page"):
            break
        after_cursor = pagination.get("end_cursor")
        params.pop("after", None)


def main():
    if not KIT_API_KEY:
        log.error("transformgov_talks_kit_api_key not set — check /home/dave/secrets/")
        raise SystemExit(1)

    monthly = defaultdict(int)
    for sub in fetch_subscribers():
        raw = sub.get("created_at")
        if raw:
            monthly[raw[:7]] += 1

    result, total = [], 0
    for month, new in sorted(monthly.items()):
        total += new
        result.append({"month": month, "new": new, "total": total})

    DATA_FILE.write_text(json.dumps(result, indent=2))
    log.info(f"Wrote {len(result)} months to {DATA_FILE}")


if __name__ == "__main__":
    main()
