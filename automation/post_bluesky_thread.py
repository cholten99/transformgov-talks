#!/usr/bin/env python3
"""
post_bluesky_thread.py — Post TGT's post-event Bluesky update as a chain of
linked replies, per the template in "TGT Post Event Automation.docx":
intro+blog, one post per speaker (with photo), YouTube, Spotify, Apple
Podcasts, upcoming events. NOT a single generic announcement post — see
automation/plan.md item 7 for why that was wrong the first time.

Edit the EVENT dict below for each new event, then run:
    python3 post_bluesky_thread.py --dry-run   # print each post + length, posts nothing
    python3 post_bluesky_thread.py
Refuses to post while any EVENT value still contains "TODO".
"""
import io
import json
import sys
from pathlib import Path

import requests
from atproto import Client, client_utils, models
from PIL import Image

BLUESKY_MAX_IMAGE_BYTES = 1_000_000

SECRETS_DIR = Path("/home/dave/secrets")
AUTOMATION_DIR = Path(__file__).parent

EVENT = {
    "location": "Yolk Recruitment in Cardiff",
    "when": "last night",  # match when the thread actually goes out
    "blog_url": "TODO",
    "youtube_url": "TODO",
    "youtube_title": "TransformGov Talks Cymru: November 2026",
    "youtube_thumb_url": "TODO",  # https://i.ytimg.com/vi/<id>/hqdefault.jpg
    "spotify_url": "TODO",
    "apple_url": "TODO",
    # In running order (check the Gemini notes).
    # "quote_topic": False for a description rather than a talk title
    "speakers": [
        {
            "name": "Rachel Meese",
            "org": "Digital Health and Care Wales",
            "topic": "building a user-centred design team in the Welsh public sector",
            "quote_topic": False,
            "photo": AUTOMATION_DIR.parent / "images" / "2026-11-rachel-meese.jpg",
        },
        {
            "name": "Andy Regan",
            "org": "Nesta Cymru",
            "topic": "why government should test and learn rather than rely on big up-front plans",
            "quote_topic": False,
            "photo": AUTOMATION_DIR.parent / "images" / "2026-11-andy-regan.jpg",
        },
        {
            "name": "Omar Idris",
            "org": "Perago",
            "topic": "how a test-and-learn approach helps teams find what works, with less risk",
            "quote_topic": False,
            "photo": AUTOMATION_DIR.parent / "images" / "2026-11-omar-idris.jpg",
        },
    ],
    # Final post. "intro" heads it; each event gets a "Register now!" link.
    "upcoming_intro": "Our next events:",
    "upcoming_events": [
        {
            "text": "25 November, MoJ, London: Peter Thomas; Tom Wynne-Morgan and Jack Strachan (GDS); Beatriz Brown (Attorney General's Office).",
            "luma_url": "https://luma.com/8oaszd9g",
        },
        {
            "text": "9 December, MoJ, London: speakers to be announced soon.",
            "luma_url": "https://luma.com/4pwpi726",
        },
        {
            "text": "Late January, Cardiff: details coming soon.",
            "luma_url": None,
        },
    ],
}

BLUESKY_MAX_GRAPHEMES = 300


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


def _lead_in(i):
    n = len(EVENT["speakers"])
    if i == 0:
        return "Our first speaker was"
    if i == n - 1 and n > 2:
        return "Finally, we heard from"
    return "That was followed by"


def _upcoming_builder():
    tb = client_utils.TextBuilder().text(EVENT["upcoming_intro"])
    for e in EVENT["upcoming_events"]:
        tb.text(f"\n\n{e['text']}")
        if e.get("luma_url"):
            tb.text(" ").link("Register now!", e["luma_url"])
    return tb


def _intro_builder():
    return (
        client_utils.TextBuilder()
        .text(f"Another excellent TGT event {EVENT['when']} at {EVENT['location']}. "
              f"Thanks as always to our speakers, our sponsors and our in-person and online attendees.\n\n"
              f"The full write-up can be found ")
        .link("here", EVENT["blog_url"])
        .text(".")
    )


def _speaker_text(i, speaker):
    topic = f"\"{speaker['topic']}\"" if speaker.get("quote_topic", True) else speaker["topic"]
    return f"{_lead_in(i)} {speaker['name']}, {speaker['org']}, on {topic}."


def dry_run():
    texts = [_intro_builder().build_text()]
    texts += [_speaker_text(i, sp) for i, sp in enumerate(EVENT["speakers"])]
    texts += ["As usual you can watch the event on YouTube.  [card: " + EVENT["youtube_title"] + "]",
              "You can also listen to it on Spotify.", "Or Apple Podcasts.",
              _upcoming_builder().build_text()]
    ok = True
    for n, t in enumerate(texts, 1):
        length = len(t)
        flag = "" if length <= BLUESKY_MAX_GRAPHEMES else "  <-- TOO LONG"
        ok = ok and not flag
        print(f"--- post {n}/{len(texts)} ({length} chars){flag}\n{t}\n")
    for sp in EVENT["speakers"]:
        if not Path(sp["photo"]).exists():
            print(f"MISSING PHOTO: {sp['photo']}")
    print("Dry run: nothing posted." + ("" if ok else " Shorten the flagged posts."))


def main():
    if "--dry-run" in sys.argv:
        return dry_run()
    todo = [k for k, v in EVENT.items() if "TODO" in json.dumps(v, default=str)]
    if todo:
        raise SystemExit(f"EVENT still has TODO values: {', '.join(todo)}")
    missing = [str(sp["photo"]) for sp in EVENT["speakers"] if not Path(sp["photo"]).exists()]
    if missing:
        raise SystemExit(f"Missing speaker photos: {', '.join(missing)}")
    total = len(EVENT["speakers"]) + 5

    client = Client()
    client.login(_secret("transformgov_talks_bluesky_handle"), _secret("transformgov_talks_bluesky_app_password"))

    # Post 1: intro + link to blog write-up
    text1 = _intro_builder()
    root = client.send_post(text=text1)
    print(f"Post 1/{total} (root): {root.uri}")
    parent = root

    # Then one post per speaker, each with their photo
    for i, speaker in enumerate(EVENT["speakers"]):
        text = _speaker_text(i, speaker)
        reply = client.send_image(
            text=text,
            image=_compressed_jpeg_bytes(speaker["photo"]),
            image_alt=speaker["name"],
            reply_to=models.AppBskyFeedPost.ReplyRef(root=_strong_ref(root), parent=_strong_ref(parent)),
        )
        print(f"Post {i + 2}/{total}: {reply.uri}")
        parent = reply

    # YouTube, as a real embed card (template says "Embed YouTube video")
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
    print(f"Post {total - 3}/{total}: {reply.uri}")
    parent = reply

    # Spotify
    text5 = client_utils.TextBuilder().text("You can also listen to it on ").link("Spotify", EVENT["spotify_url"]).text(".")
    reply = client.send_post(
        text=text5,
        reply_to=models.AppBskyFeedPost.ReplyRef(root=_strong_ref(root), parent=_strong_ref(parent)),
    )
    print(f"Post {total - 2}/{total}: {reply.uri}")
    parent = reply

    # Apple Podcasts
    text6 = client_utils.TextBuilder().text("Or ").link("Apple Podcasts", EVENT["apple_url"]).text(".")
    reply = client.send_post(
        text=text6,
        reply_to=models.AppBskyFeedPost.ReplyRef(root=_strong_ref(root), parent=_strong_ref(parent)),
    )
    print(f"Post {total - 1}/{total}: {reply.uri}")
    parent = reply

    # Last post: upcoming events, each with a registration link
    text7 = _upcoming_builder()
    reply = client.send_post(
        text=text7,
        reply_to=models.AppBskyFeedPost.ReplyRef(root=_strong_ref(root), parent=_strong_ref(parent)),
    )
    print(f"Post {total}/{total}: {reply.uri}")

    print("\nThread posted successfully.")


if __name__ == "__main__":
    main()
