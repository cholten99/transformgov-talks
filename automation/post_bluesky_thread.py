#!/usr/bin/env python3
"""
post_bluesky_thread.py — Post TGT's post-event Bluesky update as a chain of
linked replies, per the template in "TGT Post Event Automation.docx":
intro+blog, speaker 1 (photo), speaker 2 (photo), YouTube, Spotify, Apple
Podcasts, next event. NOT a single generic announcement post — see
automation/plan.md item 7 for why that was wrong the first time.

Edit the EVENT dict below for each new event, then run:
    python3 post_bluesky_thread.py
"""
import io
from pathlib import Path

import requests
from atproto import Client, client_utils, models
from PIL import Image

BLUESKY_MAX_IMAGE_BYTES = 1_000_000

SECRETS_DIR = Path("/home/dave/secrets")
AUTOMATION_DIR = Path(__file__).parent

EVENT = {
    "location": "Ministry of Justice",
    "when": "this evening",
    "blog_url": "https://medium.com/@transformgovtalks/transformgov-talks-our-october-2026-london-event-59ccc0384282",
    "youtube_url": "https://youtu.be/0EV_5pcTajU",
    "youtube_title": "TransformGov Talks: October 2026",
    "youtube_thumb_url": "https://i.ytimg.com/vi/0EV_5pcTajU/hqdefault.jpg",
    "spotify_url": "https://open.spotify.com/episode/0hcOCHUWG37wGYnTGc1Ezg",
    "apple_url": "https://podcasts.apple.com/gb/podcast/transformgov-talks-october-2026/id1776623246?i=1000798593195",
    # "quote_topic": False for a description rather than a talk title
    "speakers": [
        {
            "name": "Asma Nafees",
            "org": "NHS Non-Exec Director, Local Authority Social Enterprise NED and Social Care Charity Trustee",
            "topic": "Leadership Without Borders: Challenging the Way We Do Public Service",
            "photo": AUTOMATION_DIR.parent / "images" / "2026-10-asma-nafees.jpg",
        },
        {
            "name": "Harry Trimble",
            "org": "dxw",
            "topic": "prototypes exploring what data and automation in a blueprint for government could be like",
            "quote_topic": False,
            "photo": AUTOMATION_DIR.parent / "images" / "2026-10-harry-trimble.jpg",
        },
    ],
    "next_event": {
        "location": "Ministry of Justice",
        "date": "25 November",
        "speakers": ["Peter Thomas (civilservicereformuk.com)", "Tom Wynne-Morgan and Jack Strachan (Government Digital Service)", "Another speaker tbc"],
        "luma_url": "https://luma.com/8oaszd9g",
    },
}


def _secret(name):
    return (SECRETS_DIR / name).read_text().strip()


def _compressed_jpeg_bytes(path, max_bytes=BLUESKY_MAX_IMAGE_BYTES):
    img = Image.open(path).convert("RGB")
    for quality in (85, 75, 65, 55, 45):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        if buf.tell() <= max_bytes:
            return buf.getvalue()
    img.thumbnail((1600, 1600))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=70)
    return buf.getvalue()


def _strong_ref(response):
    return models.ComAtprotoRepoStrongRef.Main(cid=response.cid, uri=response.uri)


def main():
    client = Client()
    client.login(_secret("transformgov_talks_bluesky_handle"), _secret("transformgov_talks_bluesky_app_password"))

    # Post 1: intro + link to blog write-up
    text1 = (
        client_utils.TextBuilder()
        .text(f"Another excellent TGT event {EVENT['when']} at {EVENT['location']}. "
              f"Thanks as always to our speakers, our sponsors and our in-person and online attendees.\n\n"
              f"The full write-up can be found ")
        .link("here", EVENT["blog_url"])
        .text(".")
    )
    root = client.send_post(text=text1)
    print(f"Post 1/7 (root): {root.uri}")
    parent = root

    # Posts 2-3: speakers, each with their photo
    for i, speaker in enumerate(EVENT["speakers"]):
        topic = f"\"{speaker['topic']}\"" if speaker.get("quote_topic", True) else speaker["topic"]
        if i == 0:
            text = f"Our first speaker was {speaker['name']}, {speaker['org']}, on {topic}."
        else:
            text = f"That was followed by {speaker['name']}, {speaker['org']}, on {topic}."
        reply = client.send_image(
            text=text,
            image=_compressed_jpeg_bytes(speaker["photo"]),
            image_alt=speaker["name"],
            reply_to=models.AppBskyFeedPost.ReplyRef(root=_strong_ref(root), parent=_strong_ref(parent)),
        )
        print(f"Post {i + 2}/7: {reply.uri}")
        parent = reply

    # Post 4: YouTube, as a real embed card (template says "Embed YouTube video")
    thumb_bytes = requests.get(EVENT["youtube_thumb_url"], timeout=15).content
    blob = client.upload_blob(thumb_bytes).blob
    embed = models.AppBskyEmbedExternal.Main(
        external=models.AppBskyEmbedExternal.External(
            uri=EVENT["youtube_url"],
            title=EVENT["youtube_title"],
            description="Watch on YouTube",
            thumb=blob,
        )
    )
    reply = client.send_post(
        text="As usual you can watch the event on YouTube.",
        embed=embed,
        reply_to=models.AppBskyFeedPost.ReplyRef(root=_strong_ref(root), parent=_strong_ref(parent)),
    )
    print(f"Post 4/7: {reply.uri}")
    parent = reply

    # Post 5: Spotify
    text5 = client_utils.TextBuilder().text("You can also listen to it on ").link("Spotify", EVENT["spotify_url"]).text(".")
    reply = client.send_post(
        text=text5,
        reply_to=models.AppBskyFeedPost.ReplyRef(root=_strong_ref(root), parent=_strong_ref(parent)),
    )
    print(f"Post 5/7: {reply.uri}")
    parent = reply

    # Post 6: Apple Podcasts
    text6 = client_utils.TextBuilder().text("Or ").link("Apple Podcasts", EVENT["apple_url"]).text(".")
    reply = client.send_post(
        text=text6,
        reply_to=models.AppBskyFeedPost.ReplyRef(root=_strong_ref(root), parent=_strong_ref(parent)),
    )
    print(f"Post 6/7: {reply.uri}")
    parent = reply

    # Post 7: next event + registration link
    ne = EVENT["next_event"]
    speakers_lines = "\n".join(ne["speakers"])
    text7 = (
        client_utils.TextBuilder()
        .text(f"Our next event is at {ne['location']} on {ne['date']}\n\n{speakers_lines}\n\n")
        .link("Register now!", ne["luma_url"])
    )
    reply = client.send_post(
        text=text7,
        reply_to=models.AppBskyFeedPost.ReplyRef(root=_strong_ref(root), parent=_strong_ref(parent)),
    )
    print(f"Post 7/7: {reply.uri}")

    print("\nThread posted successfully.")


if __name__ == "__main__":
    main()
