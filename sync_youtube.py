#!/usr/bin/env python3
"""
sync_youtube.py — Fetch YouTube channel stats and write data/videos.json.
Usage: python3 sync_youtube.py
"""
import json, logging
from pathlib import Path
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

_secret_path = Path("/home/dave/secrets/transformgov_talks_youtube_api_key")
API_KEY    = _secret_path.read_text().strip() if _secret_path.exists() else None
CHANNEL_ID = "UCW9P8NYWUYRaGfArX-7jiMQ"
BASE_URL   = "https://www.googleapis.com/youtube/v3"
DATA_FILE  = Path(__file__).parent / "data" / "videos.json"


def get_uploads_playlist():
    r = requests.get(f"{BASE_URL}/channels",
        params={"part": "contentDetails", "id": CHANNEL_ID, "key": API_KEY}, timeout=10)
    r.raise_for_status()
    return r.json()["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]


def get_video_ids(playlist_id):
    ids, params = [], {"part": "contentDetails", "playlistId": playlist_id, "maxResults": 50, "key": API_KEY}
    while True:
        r = requests.get(f"{BASE_URL}/playlistItems", params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        ids += [i["contentDetails"]["videoId"] for i in data["items"]]
        if not data.get("nextPageToken"):
            break
        params["pageToken"] = data["nextPageToken"]
    return ids


def get_video_details(video_ids):
    videos = []
    for i in range(0, len(video_ids), 50):
        r = requests.get(f"{BASE_URL}/videos",
            params={"part": "snippet,statistics", "id": ",".join(video_ids[i:i+50]), "key": API_KEY}, timeout=10)
        r.raise_for_status()
        for item in r.json()["items"]:
            videos.append({
                "video_id":     item["id"],
                "title":        item["snippet"]["title"],
                "published_at": item["snippet"]["publishedAt"][:10],
                "view_count":   int(item["statistics"].get("viewCount", 0)),
            })
    return videos


def main():
    if not API_KEY:
        log.error("transformgov_talks_youtube_api_key not set — check /home/dave/secrets/")
        raise SystemExit(1)

    log.info("Fetching uploads playlist...")
    videos = sorted(get_video_details(get_video_ids(get_uploads_playlist())),
                    key=lambda v: v["published_at"])
    log.info(f"  {len(videos)} videos")

    cumulative, result = 0, []
    for v in videos:
        cumulative += v["view_count"]
        result.append({**v, "cumulative_views": cumulative})

    DATA_FILE.write_text(json.dumps(result, indent=2))
    log.info(f"Wrote {len(result)} videos to {DATA_FILE}")


if __name__ == "__main__":
    main()
