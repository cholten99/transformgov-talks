#!/usr/bin/env python3
"""
share_gemini_notes.py — Make a "Notes by Gemini" doc readable by anyone with the link.
Usage: python3 automation/share_gemini_notes.py <drive_file_id>
Refuses any file whose name doesn't contain "Notes by Gemini".
"""
import sys
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

SA_KEY = "/home/dave/secrets/cholten99_google_sa.json"
API    = "https://www.googleapis.com/drive/v3/files"


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    file_id = sys.argv[1]
    creds = service_account.Credentials.from_service_account_file(
        SA_KEY, scopes=["https://www.googleapis.com/auth/drive"])
    creds.refresh(Request())
    headers = {"Authorization": f"Bearer {creds.token}"}

    name = requests.get(f"{API}/{file_id}", headers=headers, params={"fields": "name"}, timeout=30)
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
