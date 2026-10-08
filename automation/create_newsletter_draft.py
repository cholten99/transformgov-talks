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
    python3 create_newsletter_draft.py
"""
import json
from pathlib import Path

import requests

SECRETS_DIR = Path("/home/dave/secrets")

EVENT = {
    "subject": "TransformGov Talks : Our September 2026 London event!",
    "location": "the Ministry of Justice",
    "event_date": "30 September 2026",
    "host": {"name": "Gavin Freeguard", "title": "Director", "org": "State of the Future", "org_url": "https://sotf.org.uk/"},
    "speakers": [
        {
            "name": "Riz Parveen", "org": "Department for Work and Pensions",
            "topic": "People at the heart of change",
            "photo_url": "https://www.transformgov.org.uk/images/2026-09-riz-parveen.jpg",
        },
        {
            "name": "Julia Finch", "org": "Director, Athene Leadership",
            "topic": "Eggs in One Basket: Strategic Risk in an Age of Volatility",
            "photo_url": "https://www.transformgov.org.uk/images/2026-09-julia-finch.jpg",
        },
    ],
    "blog_url": "https://medium.com/@transformgovtalks/transformgov-talks-our-september-2026-london-event-505e12f717f7",
    "gemini_url": "https://docs.google.com/document/d/1ufpOXhEVzWhIT6G8-csWkepG427Gh151M_0rQtSl6zk/edit?usp=drivesdk",
    "youtube_url": "https://youtu.be/0pio6HFWSO8",
    "spotify_url": "https://open.spotify.com/episode/7kFeIergJysuxfugvFfFaR",
    "apple_url": "https://podcasts.apple.com/gb/podcast/transformgov-talks-september-2026/id1776623246?i=1000792627799",
    # (label, url) pairs — drop any event that's already passed by the time of writing.
    "parish_notices": [
        ("Policy Camp (more post-event publications soon)", "https://policycamp.org.uk/"),
        ("National Conversations", "https://nationalconversations.org/"),
        ("Civic Punks", "https://civicpunks.com/"),
        ("Data Bites", "https://public.digital/data-bites-series"),
        ("Think Digital conferences", "https://www.thinkdigitalpartners.com/"),
        ("The National Strategy Project", "https://www.nationalstrategy.uk/"),
        ("GovCamp Cymru", "https://www.govcamp.cymru/"),
    ],
    "next_event": {
        "date_line": "28 October 2026, 6-7pm, at the Ministry of Justice",
        "speakers_line": "Harry Trimble (dxw) and Asma Nafees, Deputy Chief Operating Officer, NHS England (Arden &amp; GEM)",
        "luma_url": "https://luma.com/424qc6d1",
    },
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
    lead_ins = ["Our first speaker was", "Our second speaker was"]
    for lead_in, speaker in zip(lead_ins, ev["speakers"]):
        speaker_blocks.append(
            f'<p>{lead_in} {speaker["name"]}, {speaker["org"]}, on &ldquo;{speaker["topic"]}&rdquo;.</p>'
            + _image_block(speaker["photo_url"], speaker["name"])
        )

    notices = "".join(
        f'<li><a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a></li>'
        for label, url in ev["parish_notices"]
    )

    return f'''
<table cellPadding="0" cellSpacing="0" style="width:100%;margin:0 auto"><tbody><tr><td>
{_image_block("https://www.transformgov.org.uk/images/logo.png", "TransformGov Talks", width=536)}

<p>Hi everyone,</p>

<p>Our latest event took place at {ev["location"]} (and online!) on {ev["event_date"]}.</p>

<p>Brought to you by our excellent sponsors GovCamp, dxw, TPXimpact, Ceva, Agile, State of the Future, Public Digital and Holistic Agility.</p>

<p>Hosted by {ev["host"]["name"]}, {ev["host"]["title"]}, <a href="{ev["host"]["org_url"]}" target="_blank" rel="noopener noreferrer">{ev["host"]["org"]}</a>.</p>

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

<p>Finally, our next event is on {ev["next_event"]["date_line"]}, featuring {ev["next_event"]["speakers_line"]}.</p>

<p><a href="{ev["next_event"]["luma_url"]}" target="_blank" rel="noopener noreferrer"><strong>You can register now!</strong></a></p>

</td></tr></tbody></table>
'''


def main():
    kit_api_key = _secret("transformgov_talks_kit_api_key")
    headers = {"X-Kit-Api-Key": kit_api_key, "Accept": "application/json", "Content-Type": "application/json"}

    payload = {
        "subject": EVENT["subject"],
        "content": build_content(EVENT),
        "public": False,
        "thumbnail_url": "https://www.transformgov.org.uk/images/logo.png",
        "thumbnail_alt": "TransformGov Talks",
    }

    r = requests.post("https://api.kit.com/v4/broadcasts", headers=headers, data=json.dumps(payload))
    r.raise_for_status()
    result = r.json()
    print(f"Created draft broadcast id={result['id']}, status={result['status']}")
    print("Review and send manually from the Kit dashboard — this script never sends.")


if __name__ == "__main__":
    main()
