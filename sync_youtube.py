#!/usr/bin/env python3
"""
sync_youtube.py - Sync YouTube channel video stats into PostgreSQL.
Uses YouTube Data API v3 (key stored in .env as YOUTUBE_API_KEY).
Run manually or via cron alongside sync_kit.py.
"""

import os
import sys
import logging
from pathlib import Path
import requests
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

API_KEY    = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = "UCW9P8NYWUYRaGfArX-7jiMQ"
BASE_URL   = "https://www.googleapis.com/youtube/v3"

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "transformgov_talks")
DB_USER = os.getenv("DB_USER", "replit")
DB_PASS = os.getenv("DB_PASS")

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS yt_videos (
    video_id     TEXT PRIMARY KEY,
    title        TEXT        NOT NULL,
    published_at DATE        NOT NULL,
    view_count   INT         NOT NULL DEFAULT 0,
    synced_at    TIMESTAMP   NOT NULL DEFAULT NOW()
);
"""


def get_uploads_playlist():
    r = requests.get(f"{BASE_URL}/channels", params={
        "part": "contentDetails",
        "id": CHANNEL_ID,
        "key": API_KEY,
    }, timeout=10)
    r.raise_for_status()
    return r.json()["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]


def get_video_ids(playlist_id):
    video_ids = []
    params = {
        "part": "contentDetails",
        "playlistId": playlist_id,
        "maxResults": 50,
        "key": API_KEY,
    }
    while True:
        r = requests.get(f"{BASE_URL}/playlistItems", params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        for item in data["items"]:
            video_ids.append(item["contentDetails"]["videoId"])
        if not data.get("nextPageToken"):
            break
        params["pageToken"] = data["nextPageToken"]
    return video_ids


def get_video_details(video_ids):
    videos = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        r = requests.get(f"{BASE_URL}/videos", params={
            "part": "snippet,statistics",
            "id": ",".join(chunk),
            "key": API_KEY,
        }, timeout=10)
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
        log.error("YOUTUBE_API_KEY not set - check .env")
        sys.exit(1)
    if not DB_PASS:
        log.error("DB_PASS not set - check .env")
        sys.exit(1)

    log.info("Fetching uploads playlist ID...")
    playlist_id = get_uploads_playlist()

    log.info("Fetching video IDs from playlist...")
    video_ids = get_video_ids(playlist_id)
    log.info(f"  Found {len(video_ids)} videos")

    log.info("Fetching video details from YouTube API...")
    videos = get_video_details(video_ids)
    log.info(f"  Got details for {len(videos)} videos")

    conn = psycopg2.connect(host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS)
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE)
            conn.commit()
            log.info("Table ready.")

            execute_values(cur, """
                INSERT INTO yt_videos (video_id, title, published_at, view_count)
                VALUES %s
                ON CONFLICT (video_id) DO UPDATE SET
                    title        = EXCLUDED.title,
                    view_count   = EXCLUDED.view_count,
                    synced_at    = NOW()
            """, [(v["video_id"], v["title"], v["published_at"], v["view_count"]) for v in videos])
            conn.commit()
            log.info(f"Sync complete - {len(videos)} videos upserted.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
