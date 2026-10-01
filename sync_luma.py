#!/usr/bin/env python3
"""
sync_luma.py — Add a Lu.ma event guest CSV to data/luma.json.
Usage: python3 sync_luma.py --file <csv> --event-name "June 2026" --event-date 2026-06-19

Reads the guest CSV, computes new unique attendees against all previous events,
appends the event to data/luma.json, and updates private/luma_emails.json.
Also pulls out mailing-list opt-ins (private/luma_mailing_opt_ins.json, for the
Kit sync step) and "how did you hear about us" free-text answers
(data/luma_heard_about.json, for the dashboard).
"""
import argparse, csv, io, json
from pathlib import Path

DATA_FILE        = Path(__file__).parent / "data" / "luma.json"
HEARD_ABOUT_FILE = Path(__file__).parent / "data" / "luma_heard_about.json"
EMAILS_FILE      = Path(__file__).parent / "private" / "luma_emails.json"
OPT_INS_FILE     = Path(__file__).parent / "private" / "luma_mailing_opt_ins.json"


def parse_guests(path):
    text = Path(path).read_text(encoding="utf-8-sig", errors="replace").lstrip("﻿")
    reader  = csv.reader(io.StringIO(text))
    headers = next(reader)
    lower   = [h.lower().strip() for h in headers]

    def col(*candidates):
        for c in candidates:
            for i, h in enumerate(lower):
                if c in h:
                    return i
        return None

    email_col       = col("email")
    ticket_col      = col("ticket_name", "ticket name", "ticket", "type")
    mailing_col     = col("would you like to be added to our mailing list")
    heard_about_col = col("how did you hear about")

    def cell(row, idx):
        return row[idx].strip() if idx is not None and len(row) > idx else ""

    guests = []
    for row in reader:
        email = cell(row, email_col).lower()
        if email:
            guests.append({
                "email":           email,
                "ticket":          cell(row, ticket_col),
                "mailing_opt_in":  cell(row, mailing_col).lower().startswith("yes"),
                "heard_about":     cell(row, heard_about_col),
            })
    return guests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file",       required=True)
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--event-date", required=True)
    args = parser.parse_args()

    guests = parse_guests(args.file)
    if not guests:
        raise SystemExit("No guest rows found in CSV")

    in_person  = sum(1 for g in guests if g["ticket"].lower() == "in person")
    online     = sum(1 for g in guests if g["ticket"].lower() == "online")
    unknown    = len(guests) - in_person - online
    total      = len(guests)
    new_emails = {g["email"] for g in guests}

    seen          = set(json.loads(EMAILS_FILE.read_text()) if EMAILS_FILE.exists() else [])
    new_unique    = len(new_emails - seen)
    events        = json.loads(DATA_FILE.read_text()) if DATA_FILE.exists() else []
    prev_cum      = events[-1]["cumulative_unique"] if events else 0
    cumulative    = prev_cum + new_unique

    events.append({
        "event_name":       args.event_name,
        "event_date":       args.event_date,
        "in_person":        in_person,
        "online":           online,
        "unknown_type":     unknown,
        "total":            total,
        "new_unique":       new_unique,
        "cumulative_unique": cumulative,
    })

    DATA_FILE.write_text(json.dumps(events, indent=2))
    EMAILS_FILE.write_text(json.dumps(sorted(seen | new_emails), indent=2))

    heard_about = json.loads(HEARD_ABOUT_FILE.read_text()) if HEARD_ABOUT_FILE.exists() else []
    heard_about.append({
        "event_name": args.event_name,
        "event_date": args.event_date,
        "answers": [g["heard_about"] for g in guests if g["heard_about"]],
    })
    HEARD_ABOUT_FILE.write_text(json.dumps(heard_about, indent=2))

    opt_ins = json.loads(OPT_INS_FILE.read_text()) if OPT_INS_FILE.exists() else []
    new_opt_ins = [
        {"email": g["email"], "event_name": args.event_name, "event_date": args.event_date}
        for g in guests if g["mailing_opt_in"]
    ]
    opt_ins.extend(new_opt_ins)
    OPT_INS_FILE.write_text(json.dumps(opt_ins, indent=2))

    print(f"Added '{args.event_name}': {total} registrations, {new_unique} new unique (cumulative: {cumulative})")
    print(f"  {len(new_opt_ins)} mailing-list opt-ins recorded for Kit sync")


if __name__ == "__main__":
    main()
