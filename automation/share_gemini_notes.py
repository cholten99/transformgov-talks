#!/usr/bin/env python3
"""
share_gemini_notes.py — Make a "Notes by Gemini" doc readable by anyone with the link.
Usage: python3 automation/share_gemini_notes.py <drive_file_id>
Refuses any file whose name doesn't contain "Notes by Gemini".

Uses the cholten99 service account, which only sees what's been shared with
it. Meet creates a new folder per event, so the TGT "Google Meet" folder
must be shared with the service account as Editor for this to reach new
notes. (The TGT: rclone remote can't do this: it's drive.readonly.)
"""
import json, sys, time
import jwt
import requests

SA_KEY = "/home/dave/secrets/cholten99_google_sa.json"
API    = "https://www.googleapis.com/drive/v3/files"


def access_token():
    # Service-account JWT grant (google-auth isn't installed system-wide)
    sa  = json.load(open(SA_KEY))
    now = int(time.time())
    assertion = jwt.encode({
        "iss": sa["client_email"], "scope": "https://www.googleapis.com/auth/drive",
        "aud": sa["token_uri"], "iat": now, "exp": now + 600,
    }, sa["private_key"], algorithm="RS256")
    r = requests.post(sa["token_uri"], data={
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    file_id = sys.argv[1]
    headers = {"Authorization": f"Bearer {access_token()}"}

    name = requests.get(f"{API}/{file_id}", headers=headers, params={"fields": "name"}, timeout=30)
    if name.status_code == 404:
        sys.exit("Not visible to the service account: share the TGT 'Google Meet' folder with it as Editor")
    name.raise_for_status()
    name = name.json()["name"]
    if "Notes by Gemini" not in name:
        sys.exit(f"Refusing: '{name}' is not a Gemini notes doc")

    r = requests.post(f"{API}/{file_id}/permissions", headers=headers,
                      json={"role": "reader", "type": "anyone"}, timeout=30)
    r.raise_for_status()
    print(f"Shared '{name}' as anyone-with-link reader")


if __name__ == "__main__":
    main()
