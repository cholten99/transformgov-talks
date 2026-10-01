#!/usr/bin/env python3
"""
check_episode_links.py — Poll Apple Podcasts and Spotify for a TGT episode's
public link, once it's been indexed after publishing.

Usage: python3 check_episode_links.py "TransformGov Talks: September 2026"

Apple: public iTunes Lookup API, no auth needed.
Spotify: no API/app needed either — the public show page
  (open.spotify.com/show/<id>) is server-rendered and lists episode titles
  with their /episode/<id> links directly in the HTML, found by scraping
  rather than the Web API (which would need a registered app + Client
  Credentials just to search). Simpler and avoids a needless credential.
"""
import re
import sys
import requests

APPLE_SHOW_ID = "1776623246"
SPOTIFY_SHOW_ID = "0PUIa0T6fVxo0UkcTO9J2M"


def check_apple(episode_title):
    r = requests.get(
        "https://itunes.apple.com/lookup",
        params={"id": APPLE_SHOW_ID, "entity": "podcastEpisode", "limit": 10, "sort": "recent"},
        timeout=15,
    )
    r.raise_for_status()
    for item in r.json().get("results", []):
        if item.get("wrapperType") == "podcastEpisode" and item.get("trackName") == episode_title:
            return item.get("trackViewUrl")
    return None


def check_spotify(episode_title):
    r = requests.get(
        f"https://open.spotify.com/show/{SPOTIFY_SHOW_ID}",
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=15,
    )
    r.raise_for_status()
    html = r.text

    for m in re.finditer(re.escape(episode_title), html):
        chunk = html[max(0, m.start() - 400):m.start()]
        link_match = re.search(r'href="(/episode/[^"]+)"', chunk)
        if link_match:
            return "https://open.spotify.com" + link_match.group(1)
    return None


def main():
    if len(sys.argv) != 2:
        sys.exit(f"Usage: {sys.argv[0]} <episode title>")
    title = sys.argv[1]

    apple_url = check_apple(title)
    print(f"Apple Podcasts: {apple_url or 'not indexed yet'}")

    spotify_url = check_spotify(title)
    print(f"Spotify: {spotify_url or 'not indexed yet'}")


if __name__ == "__main__":
    main()
