#!/usr/bin/env python3
"""
upload_youtube.py — Upload a TGT event video to the TGT YouTube channel (public).

Sign-in (Testing-mode OAuth: the refresh token lasts 7 days, so do this
before each event's upload; see plan.md item 3):
    python3 upload_youtube.py --consent-url
        -> Dave opens it signed in as the TGT account, approves, and pastes
           back the dead http://localhost/?code=... address
    python3 upload_youtube.py --auth-code '<that whole address or just the code>'
        -> saves ~/secrets/transformgov_talks_youtube_token.json (mode 600)

Upload:
    python3 upload_youtube.py VIDEO.mp4 META.json [--dry-run]
META.json: {"title": ..., "description": ..., "categoryId": "25"}
Uploads resumably in 16 MB chunks and prints the video URL at the end.
Always public (every TGT video has been).
"""
import json
import os
import sys
import time
import urllib.parse

import requests

SECRETS = "/home/dave/secrets"
CLIENT = f"{SECRETS}/transformgov_talks_youtube_oauth_client.json"
TOKEN = f"{SECRETS}/transformgov_talks_youtube_token.json"
CHUNK = 16 * 1024 * 1024


def access_token():
    client = json.load(open(CLIENT))["installed"]
    tok = json.load(open(TOKEN))
    r = requests.post(client["token_uri"], data={
        "client_id": client["client_id"], "client_secret": client["client_secret"],
        "refresh_token": tok["refresh_token"], "grant_type": "refresh_token"}, timeout=30)
    if not r.ok:
        sys.exit(f"Token refresh failed ({r.status_code}): redo the consent step. {r.text[:200]}")
    return r.json()["access_token"]


def consent_url():
    client = json.load(open(CLIENT))["installed"]
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client["client_id"], "redirect_uri": "http://localhost",
        "response_type": "code", "scope": "https://www.googleapis.com/auth/youtube.upload",
        "access_type": "offline", "prompt": "consent"})


def save_token(code_or_url):
    if "code=" in code_or_url:
        code_or_url = urllib.parse.parse_qs(urllib.parse.urlparse(code_or_url).query)["code"][0]
    client = json.load(open(CLIENT))["installed"]
    r = requests.post(client["token_uri"], data={
        "code": code_or_url, "client_id": client["client_id"], "client_secret": client["client_secret"],
        "redirect_uri": "http://localhost", "grant_type": "authorization_code"}, timeout=30)
    if not r.ok:
        sys.exit(f"Code exchange failed ({r.status_code}) — codes expire in minutes: {r.text[:200]}")
    tok = r.json()
    if not tok.get("refresh_token"):
        sys.exit("No refresh token returned — make sure the consent URL had prompt=consent")
    tok["obtained_at"] = int(time.time())
    old = os.umask(0o077)
    try:
        with open(TOKEN, "w") as f:
            json.dump(tok, f)
    finally:
        os.umask(old)
    print(f"Saved {TOKEN} (valid for 7 days)")


def main():
    if "--consent-url" in sys.argv:
        print(consent_url())
        return
    if "--auth-code" in sys.argv:
        return save_token(sys.argv[sys.argv.index("--auth-code") + 1])
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        sys.exit(__doc__)
    video, meta_path = args
    meta = json.load(open(meta_path))
    body = {
        "snippet": {"title": meta["title"], "description": meta["description"],
                    "categoryId": meta.get("categoryId", "25"), "defaultLanguage": "en"},
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False, "embeddable": True},
    }
    size = os.path.getsize(video)
    print(f"{video}: {size / 1e6:.0f} MB\nTitle: {meta['title']}\n\n{meta['description']}\n")
    if "--dry-run" in sys.argv:
        print("Dry run: nothing uploaded.")
        return

    headers = {"Authorization": f"Bearer {access_token()}"}
    r = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        headers={**headers, "Content-Type": "application/json",
                 "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)},
        data=json.dumps(body), timeout=60)
    r.raise_for_status()
    session = r.headers["Location"]

    offset = 0
    with open(video, "rb") as f:
        while offset < size:
            f.seek(offset)
            chunk = f.read(CHUNK)
            end = offset + len(chunk) - 1
            for attempt in range(5):
                try:
                    r = requests.put(session, headers={**headers, "Content-Length": str(len(chunk)),
                                                       "Content-Range": f"bytes {offset}-{end}/{size}"},
                                     data=chunk, timeout=300)
                    break
                except requests.RequestException as e:
                    print(f"  chunk at {offset} failed ({e}), retrying")
                    time.sleep(2 ** attempt)
            else:
                sys.exit(f"Gave up at byte {offset}; session URL to resume: {session}")
            if r.status_code == 308:
                rng = r.headers.get("Range")
                offset = int(rng.split("-")[1]) + 1 if rng else 0
                print(f"  {offset / size:5.1%}", flush=True)
            elif r.status_code in (200, 201):
                vid = r.json()["id"]
                print(f"Uploaded: https://youtu.be/{vid}")
                return
            elif r.status_code in (401,):
                headers = {"Authorization": f"Bearer {access_token()}"}
            else:
                sys.exit(f"Upload failed {r.status_code}: {r.text[:300]}")


if __name__ == "__main__":
    main()
