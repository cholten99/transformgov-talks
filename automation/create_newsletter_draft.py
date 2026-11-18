#!/usr/bin/env python3
"""
create_newsletter_draft.py — Create (but do NOT send) a Kit broadcast for
TGT's post-event newsletter, using the same content as the blog post.

Creates a draft only: no send_at/published_at is set, so it sits in Kit's
dashboard under Broadcasts for Dave to review and send by hand. Never add
code here that schedules or sends — that step is deliberately manual.

Speaker photos must be hosted somewhere publicly reachable first (e.g.
copied into /var/www/transformgov-talks/images/) — Kit emails need real
image URLs, not local files or attachments.

Edit the EVENT dict below for each new event, then run:
    python3 create_newsletter_draft.py --dry-run > preview.html   # check the HTML, sends nothing
    python3 create_newsletter_draft.py             # creates the Kit draft
Refuses to create the draft while any EVENT value still contains "TODO".
"""
import json
import sys
from pathlib import Path

import requests

SECRETS_DIR = Path("/home/dave/secrets")

EVENT = {
    "subject": "TransformGov Talks Cymru : Our November 2026 Cardiff event!",
    "location": "Yolk Recruitment in Cardiff",
    "event_date": "18 November 2026",
    # Without "title", the line reads "Hosted by <org>."
    "host": {"org": "Transform Wales", "org_url": "https://transform.wales/"},
    "sponsors_line": "Brought to you by our excellent sponsors GovCamp, dxw, TPXimpact, Ceva, Agile, State of the Future, Public Digital and Holistic Agility.",
    # In running order (check the Gemini notes). "quote_topic": False for a
    # description rather than a talk title.
    "speakers": [
        {
            "name": "Rachel Meese", "org": 'Head of UCD at <a href="https://dhcw.nhs.wales/" target="_blank" rel="noopener noreferrer">Digital Health and Care Wales</a>',
            "topic": "building a user-centred design team in the Welsh public sector, and lessons from helping senior leaders recognise the value of user-centred design",
            "quote_topic": False,
            "photo_url": "https://www.transformgov.org.uk/images/2026-11-rachel-meese.jpg",
        },
        {
            "name": "Andy Regan", "org": 'Head of <a href="https://www.nesta.org.uk/" target="_blank" rel="noopener noreferrer">Nesta Cymru</a>',
            "topic": "why government should test and learn rather than rely on big up-front plans",
            "quote_topic": False,
            "photo_url": "https://www.transformgov.org.uk/images/2026-11-andy-regan.jpg",
        },
        {
            "name": "Omar Idris", "org": 'Head of Design at <a href="https://perago.co.uk/" target="_blank" rel="noopener noreferrer">Perago</a>',
            "topic": "how a test-and-learn approach helps teams quickly find what works, with less risk",
            "quote_topic": False,
            "photo_url": "https://www.transformgov.org.uk/images/2026-11-omar-idris.jpg",
        },
    ],
    "blog_url": "TODO",
    "gemini_url": "https://docs.google.com/document/d/1DKyzAlhB1nADv2OGBmC99OOquvgabbm__vejrX5vf-8/edit?usp=sharing",
    "youtube_url": "TODO",
    "spotify_url": "TODO",
    "apple_url": "TODO",
    # (label, url) pairs — drop any event that's already passed by the time of
    # writing. TODO: confirm against tonight's parish notices.
    "parish_notices": [
        ("Policy Camp (report now published)", "https://policycamp.org.uk/"),
        ("National Conversations", "https://nationalconversations.org/"),
        ("Civic Punks", "https://civicpunks.com/"),
        ("Data Bites #63 (2 December)", "https://www.thinkdigitalpartners.com/data-bites/"),
        ("The National Strategy Project", "https://www.nationalstrategy.uk/"),
        ("Open Data Camp (21\u201322 November)", "https://www.odcamp.uk/"),
    ],
    "upcoming_events": [
        {
            "date_line": "25 November 2026, 6-7pm, at the Ministry of Justice in London",
            "speakers_line": "Peter Thomas (civilservicereformuk.com) on what 15 years of GDS tell us about successful reform; Tom Wynne-Morgan and Jack Strachan (Government Digital Service) on &lsquo;Transforming Gov: from digital transactions to digital decisions&rsquo;; and Beatriz Brown (Attorney General&rsquo;s Office) on public engagement on the rule of law",
            "luma_url": "https://luma.com/8oaszd9g",
        },
        {
            "date_line": "9 December 2026, 6-7pm, at the Ministry of Justice in London",
            "speakers_line": "speakers to be announced soon",
            "luma_url": "https://luma.com/4pwpi726",
        },
        {
            # No Luma page yet: listed without a register link.
            "date_line": "Late January 2027, our next TransformGov Talks Cymru in Cardiff",
            "speakers_line": "details coming soon",
            "luma_url": None,
        },
    ],
}


def _secret(name):
    return (SECRETS_DIR / name).read_text().strip()


def _image_block(url, alt, width=400):
    return (
        '<table width="100%" border="0" cellSpacing="0" cellPadding="0" style="text-align:center" class="email-image">'
        f'<tbody><tr><td align="center"><img src="{url}" alt="{alt}" width="{width}" '
        'style="max-width:100%;width:{width}px;height:auto;border-radius:6px"/></td></tr></tbody></table>'
    ).replace("{width}", str(width))


def build_content(ev):
    speaker_blocks = []
    lead_ins = ["Our first speaker was", "Our second speaker was", "Our third speaker was", "Our fourth speaker was"]
    if len(ev["speakers"]) > len(lead_ins):
        raise SystemExit(f"Only {len(lead_ins)} speakers supported — add more lead-ins")
    for lead_in, speaker in zip(lead_ins, ev["speakers"]):
        speaker_blocks.append(
            f'<p>{lead_in} {speaker["name"]}, {speaker["org"]}, on '
            + (f'&ldquo;{speaker["topic"]}&rdquo;' if speaker.get("quote_topic", True) else speaker["topic"])
            + '.</p>'
            + _image_block(speaker["photo_url"], speaker["name"])
        )

    host = ev["host"]
    host_org = f'<a href="{host["org_url"]}" target="_blank" rel="noopener noreferrer">{host["org"]}</a>'
    host_line = f'{host["name"]}, {host["title"]}, {host_org}' if host.get("title") else host_org

    upcoming = ev["upcoming_events"]
    if len(upcoming) == 1:
        e = upcoming[0]
        upcoming_html = (
            f'<p>Finally, our next event is on {e["date_line"]}, featuring {e["speakers_line"]}.</p>\n\n'
            f'<p><a href="{e["luma_url"]}" target="_blank" rel="noopener noreferrer"><strong>You can register now!</strong></a></p>'
        )
    else:
        items = "".join(
            f'<li>{e["date_line"]}: {e["speakers_line"]}.'
            + (f' <a href="{e["luma_url"]}" target="_blank" rel="noopener noreferrer"><strong>Register now!</strong></a>'
               if e.get("luma_url") else "")
            + '</li>'
            for e in upcoming
        )
        upcoming_html = f'<p>Finally, our next events are:</p>\n<ul>{items}</ul>'

    notices = "".join(
        f'<li><a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a></li>'
        for label, url in ev["parish_notices"]
    )

    return f'''
<table cellPadding="0" cellSpacing="0" style="width:100%;margin:0 auto"><tbody><tr><td>
{_image_block("https://www.transformgov.org.uk/images/logo.png", "TransformGov Talks", width=536)}

<p>Hi everyone,</p>

<p>Our latest event took place at {ev["location"]} (and online!) on {ev["event_date"]}.</p>

<p>{ev["sponsors_line"]}</p>

<p>Hosted by {host_line}.</p>

{"".join(speaker_blocks)}

<p>If you weren&rsquo;t able to attend, you can catch up on the event in more detail:</p>
<ul>
<li>Read the <a href="{ev["blog_url"]}" target="_blank" rel="noopener noreferrer">blog write-up</a></li>
<li>Read the <a href="{ev["gemini_url"]}" target="_blank" rel="noopener noreferrer">Gemini AI Summary</a></li>
<li><a href="{ev["youtube_url"]}" target="_blank" rel="noopener noreferrer">Watch on YouTube</a></li>
<li>Listen on <a href="{ev["spotify_url"]}" target="_blank" rel="noopener noreferrer">Spotify</a> or <a href="{ev["apple_url"]}" target="_blank" rel="noopener noreferrer">Apple Podcasts</a></li>
</ul>

<p>At the end of the event, we included a few parish notices for other events and projects you might be interested in:</p>
<ul>{notices}</ul>

<p>Let us know if you have an event you&rsquo;d like us to publicise.</p>

{upcoming_html}

</td></tr></tbody></table>
'''


def main():
    content = build_content(EVENT)
    if "--dry-run" in sys.argv:
        print(content)
        print("<!-- Dry run: nothing sent to Kit. -->")
        return
    todo = [k for k, v in EVENT.items() if "TODO" in json.dumps(v)]
    if todo:
        raise SystemExit(f"EVENT still has TODO values: {', '.join(todo)}")

    kit_api_key = _secret("transformgov_talks_kit_api_key")
    headers = {"X-Kit-Api-Key": kit_api_key, "Accept": "application/json", "Content-Type": "application/json"}

    payload = {
        "subject": EVENT["subject"],
        "content": content,
        "public": False,
        "thumbnail_url": "https://www.transformgov.org.uk/images/logo.png",
        "thumbnail_alt": "TransformGov Talks",
    }

    r = requests.post("https://api.kit.com/v4/broadcasts", headers=headers, data=json.dumps(payload))
    r.raise_for_status()
    result = r.json()["broadcast"]
    print(f"Created draft broadcast id={result['id']}, send_at={result.get('send_at')}")
    print("Review and send manually from the Kit dashboard — this script never sends.")


if __name__ == "__main__":
    main()
