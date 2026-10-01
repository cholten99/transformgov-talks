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
    "blog_url": "https://medium.com/@transformgovtalks/transformgov-talks-our-september-2026-london-event-505e12f717f7",
    "youtube_url": "https://youtu.be/0pio6HFWSO8",
    "youtube_title": "TransformGov Talks: September 2026",
    "youtube_thumb_url": "https://i.ytimg.com/vi/0pio6HFWSO8/hqdefault.jpg",
    "spotify_url": "https://open.spotify.com/episode/7kFeIergJysuxfugvFfFaR",
    "apple_url": "https://podcasts.apple.com/gb/podcast/transformgov-talks-september-2026/id1776623246?i=1000792627799",
    "speakers": [
        {
            "name": "Riz Parveen",
            "org": "Department for Work and Pensions",
            "topic": "People at the heart of change",
            "photo": AUTOMATION_DIR / "Riz.jpg",
        },
        {
            "name": "Julia Finch",
            "org": "Director, Athene Leadership",
            "topic": "Eggs in One Basket: Strategic Risk in an Age of Volatility",
            "photo": AUTOMATION_DIR / "Julia.jpg",
        },
    ],
    "next_event": {
        "location": "Ministry of Justice",
        "date": "28 October",
        "speakers": ["Harry Trimble (dxw)", "Asma Nafees (NHS England)"],
        "luma_url": "https://luma.com/424qc6d1",
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
        .text(f"Another excellent TGT event last night at {EVENT['location']}. "
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
        if i == 0:
            text = f"Our first speaker was {speaker['name']}, {speaker['org']}, on \"{speaker['topic']}\"."
        else:
            text = f"That was followed by {speaker['name']}, {speaker['org']}, on \"{speaker['topic']}\"."
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
