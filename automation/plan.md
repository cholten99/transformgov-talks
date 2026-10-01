# TGT post-event automation — working notes

Going through each action one at a time. Recording decisions/findings here as we go.

## 1. Upload video to YouTube

**Needs:** raw video file.

**Finding so far:** uploading needs OAuth2 with YouTube upload scope. The existing
`transformgov_talks_youtube_api_key` secret is a read-only v3 API key (used by
`sync_youtube.py` for stats) — it can't upload.

**Finding:** the recording lands in the TGT Google account's Google Meet recordings
location (exact folder TBD) — Dave confirmed it'll always be the most recent file there.

**Access approach decided:** a plain API key won't work for private Drive files
(unlike the YouTube stats key, which only reads public data). For an unattended
cron-style script, use a **Google Cloud service account**:
1. Create a Google Cloud project, enable the Drive API.
2. Create a service account, download its JSON key → store in `secrets/`.
3. Share the relevant TGT Drive folder(s) with the service account's email address.
4. Script authenticates with the JSON key, no browser login/token refresh needed.

(Separately, uploading to YouTube still needs real OAuth2 w/ upload scope — different
problem, see above.)

**Status:** DONE — service account `access-my-google-docs@sinuous-branch-503021-e4.iam.gserviceaccount.com`
(key: `secrets/cholten99_google_sa.json`) has been shared (Viewer) on the TGT "Google Meet"
Drive folder and confirmed working (tested with a one-off JWT auth script).

**Folder structure found:** under My Drive > "Google Meet" there isn't one consistent
recordings folder — there's a "Meet Recordings" subfolder plus separate per-event
dated subfolders (e.g. "TGT live stream - 2026/09/17 17:32 BST"), and at least one
folder contained recordings from two different event dates mixed together.

**Robust approach:** recursively list all files under the "Google Meet" folder,
filter to names ending in "- Recording" (video/mp4) or "- Notes by Gemini"
(Google Doc), then take the max by `modifiedTime`. Don't rely on folder name/location
alone.

Confirmed latest event (as of 2026-10-01): **2026/09/17 17:32 BST** folder actually
contains the newest files, dated **2026/09/30 17:54 BST**:
- Recording: `TGT live stream - 2026/09/30 17:54 BST - Recording` (mp4, 637MB)
- Gemini summary: `TGT live stream - 2026/09/30 17:54 BST - Notes by Gemini` (Google Doc)

## 2. Gemini summary (for blog/newsletter copy)

**Status:** DONE — same answer as above. It's the "... - Notes by Gemini" Google Doc
sitting alongside the recording. No separate lookup needed; same recursive scan finds
both in one pass.

## 3. YouTube upload — auth

**Why OAuth, not an API key:** write operations like `videos.insert` require OAuth2
user consent identifying the channel, regardless of who uses the app — API keys only
authenticate the calling app, not a channel. Service accounts don't work either (no
Drive-style folder-sharing equivalent for a YouTube channel).

**Decision: skip full "In production" verification.** It needs privacy policy/homepage
info etc., too much for an internal tool. Instead: kept the OAuth consent screen in
**Testing** status, added `transformgovtalks@gmail.com` as a test user. Caveat:
refresh tokens issued under Testing status hard-expire after 7 days regardless of use.
**Accepted tradeoff:** redo the ~30-second browser consent fresh before each event's
upload rather than persisting a long-lived refresh token — trivial next to the rest of
the manual post-event process, and avoids the verification paperwork entirely.

- Client: Desktop app OAuth client, project `tgt-post-event-automation`,
  stored at `secrets/transformgov_talks_youtube_oauth_client.json`.
- Flow: build consent URL (scope `youtube.upload`, `access_type=offline`,
  `prompt=consent`) → Dave opens it signed in as the TGT account → approves →
  redirected to dead `http://localhost/?code=...` → copy the `code` param →
  exchange at the token endpoint for an access token (same-session use only).

**Status:** DONE (auth flow proven end-to-end for the Sept 2026 event upload).

## 4. YouTube upload — title & description

**Title convention:** `TransformGov Talks: <Month> <Year>` — confirmed against actual
past video titles fetched via the read-only YouTube API (e.g. "TransformGov Talks:
July 2026"). Regional events get different naming (e.g. "TransformGov Talks Scotland :
September 2026") — only applies to the flagship (non-regional) event.

**Description convention:** fetched an existing video's real description via the
YouTube API to copy the exact format:
```
​Hosted by Gavin Freeguard, Director, State of the Future.

* <Speaker>, <role/org>, on '<topic>'.

* <Speaker>, <role/org>, on '<topic>'.
```
Speaker names/topics/host/location come from the event's **Luma page**
(`https://luma.com/bm1xsbsv` — lists past + upcoming TGT events). Host line
(Gavin Freeguard) appears constant across events so far.

**Decision: always publish as Public** (not Unlisted), matching how every past video
has been published.

**Status:** DONE for the Sept 30 2026 event — pulled from Luma: Riz Parveen (DWP)
on "People at the heart of change", Julia Finch (Athene Leadership) on "Eggs in One
Basket: Strategic Risk in an Age of Volatility". Upload in progress.

## 5. Next event info (for website + newsletter CTA)

**Finding:** Luma's event page (`https://luma.com/bm1xsbsv`) doesn't show the next
event yet — only lists the just-happened one as "Past Event". But the **Gemini
summary doc itself** captured the live announcement made during the event: next
event is **October 28 2026**, featuring **Harry Trimble (DXW)** and **Asma Nafi
(NHS England)**. No venue/time/registration link yet — that'll need checking Luma
again closer to the date, once it's published there.

**Status:** partial — have speakers/date, missing logistics + registration link.

## 6. Add MP3 to podcast project

**Finding:** fully documented already in `/var/www/podcast-host/CLAUDE.md`
("Adding a new episode"), reusable as-is:
1. Add audio file to `audio/transformgov-talks/`, named `TGT_<Month>_<Year>.mp3`.
2. Add new entry to top of `episodes:` in the relevant `data/*.yml` (copy shape of
   most recent entry).
3. Re-run `generator/render_feed.py <data.yml> <feed_url> <output.xml>` to
   regenerate `dist/*.xml` (vhost serves `dist/`, not the yml directly).
4. Commit `data/*.yml` (not `dist/`, gitignored).
5. (Bluesky posting — see below, now relevant to TGT.)

**Status:** process known, not yet run for this event (blocked on video download).

## 7. Bluesky cron post — simplification found

**Big find:** podcast-host already has `generator/post_to_bluesky.py` — it posts
the top episode in a `data.yml` to Bluesky as a link card (title + truncated
description + show artwork). It's currently only wired up for WYSLI
(`SHOW_CONFIG` entry using `willyoustillloveit_bluesky_handle`/`_app_password`).
The doc literally says: "Not wired up for TGT — add a `SHOW_CONFIG` entry in the
script if TGT gets its own Bluesky account later." TGT now has one
(`transformgov_talks_bluesky_handle`/`_app_password`, saved this session).

**Mistake made and corrected (2026-10-01):** I initially used
`post_to_bluesky.py` (with a TGT `SHOW_CONFIG` entry added) as TGT's actual
Bluesky posting mechanism, posting one generic "New episode of X: title" link
card. **This is wrong and was reverted (Dave deleted that post).**
`post_to_bluesky.py` is the right tool for WYSLI, which really does just want
a single episode-announcement post — but TGT's own template
(`TGT Post Event Automation.docx`, "Bluesky template" section) explicitly
calls for **a chain of 7 linked reply posts**: intro+blog link, speaker 1
(with photo), speaker 2 (with photo), YouTube (embedded), Spotify, Apple
Podcasts, next event + registration link. A single announcement post is not
an acceptable substitute — don't reach for `post_to_bluesky.py` for TGT again.

**Correct tool:** `automation/post_bluesky_thread.py` — builds the full
7-post reply chain per the template, with an `EVENT` dict at the top to edit
for each new event. Real gotcha hit: Bluesky rejects images over ~1MB
(`blob too big`) — the raw speaker photos from Downloads were 3-4MB, so the
script compresses them (Pillow, iterating JPEG quality down until under
1MB) before upload. Don't skip that step even for "small-looking" photos.

**Status:** DONE — posted successfully for the Sept 2026 event, thread root:
`at://did:plc:il2wth3satwuzblw7ybec7af/app.bsky.feed.post/3mwtpjwuzxu2i`.

## 8. Blog post (Medium)

**Finding:** no Medium credentials exist in `secrets/`. Medium discontinued
self-serve API tokens for new integrations years ago — likely **not
automatable** via official API.

**Decision (2026-10-01):** don't chase Medium automation. For now, generate the
blog/newsletter copy as a `.docx` (filled from the template using YouTube link,
Gemini summary, Luma speaker data, photos, parish notices, next event) and Dave
pastes it into Medium by hand. **Future plan: migrate the blog to WordPress**,
which has a proper REST API — revisit full posting automation once that move
happens.

**Status:** DONE — Dave posted it:
https://medium.com/@transformgovtalks/transformgov-talks-our-september-2026-london-event-505e12f717f7

### Refined template (superseding the first draft, based on Dave's edits)

Dave edited the generated docx by hand before posting; diffing his version
against what I generated (via the docx's embedded hyperlink relationships,
not just visible text) showed a consistent set of copy conventions to use
from now on:

- **Links are real hyperlinks on short anchor text, never visible raw URLs.**
  E.g. "Video on YouTube" / "Read the Gemini AI Summary" / "Register now!" are
  the clickable text — don't write out `https://...` inline like a first
  draft would.
- **Drop the full street address** in running copy — "the Ministry of
  Justice" not "Ministry of Justice, 102 Petty France, London SW1H 9AJ".
  Applies both to the event-just-happened paragraph and the next-event
  paragraph.
- **Hyperlink the host's org name** too — "State of the Future" links to
  `sotf.org.uk`, not just the speakers' orgs.
- **Photo captions**: each speaker photo gets a plain-text name caption
  directly underneath it, not just the bare image.
- **Parish notices is a bulleted list with each item individually
  hyperlinked** to that org's site, not one comma-separated paragraph of
  links. **Drop any notice for an event that's already passed** (he removed
  GovCamp Scotland, which had already happened) — don't carry stale entries
  forward just because they were in a previous event's notices. Short
  editorial asides are fine too (he added "(more post-event publications
  soon)" next to Policy Camp).
- **The "download this poster" line gets a real link** to the poster file
  (he added a Drive link: `drive.google.com/file/d/1ZkA37iPO9NbALvxvNBA431fVpAAMKtwP`)
  — find/ask for this each time rather than leaving it as plain unlinked text.
- The Gemini summary link was used **as-is, still pointing at the private
  Drive doc** (`docs.google.com/document/.../edit`) — Dave didn't ask for it
  to be made public first. Worth flagging each time (public blog readers may
  hit a permission wall) but apparently not a blocker to posting.

**How to apply:** build the next event's docx against this refined list, not
the original flat template text from `TGT Post Event Automation.docx`.

## 9. Luma: finding the next event's page automatically

**Problem found:** Luma's pages are a client-rendered JS app — fetching the
raw HTML (via `curl` or the WebFetch tool) only gets an empty shell; the event
list/cards are loaded dynamically in a real browser and aren't in the static
HTML. This means **the specific URL for the next event can't currently be found
automatically** — not from the series page (`luma.com/bm1xsbsv`, which is
actually just September's own event page, not a calendar) nor from the org's
profile page (`luma.com/user/TransformGTalks`, which also needs JS to render
its event list).

**Decision:** don't try to reverse-engineer Luma's backend API to scrape this
— added to the manual "supply after event" list below instead. Once given the
specific event URL, pulling date/time/venue/speakers from it works fine (its
`__NEXT_DATA__` JSON blob has structured data once you're on the right page).

## 10. Newsletter (Kit)

**Script:** `automation/create_newsletter_draft.py` — builds the same content
as the blog post (speaker photos, all four links, parish notices, next event)
as HTML and creates it as a **Kit broadcast draft** via the v4 API.

**Hard rule: this only ever creates a draft, never sends.** No `send_at`
field is set in the API call — status comes back as `"draft"`. Sending is a
deliberate separate manual step Dave does from the Kit dashboard after
reviewing. **Never add code that schedules or sends** — that was an explicit
instruction, not just a default.

**Dependency:** speaker photos must be hosted somewhere with a public URL
first (Kit emails need real image URLs, not local files) — this session they
were copied into `/var/www/transformgov-talks/images/` and referenced from
there. Do this before running the script.

---

## Manual inputs still needed after every event (can't be found automatically)

These need to be supplied by Dave each time — everything else in this doc is
scriptable/automatic once these are in hand:

1. **Next event's Luma URL** — e.g. `https://luma.com/424qc6d1`. Luma's JS
   rendering blocks automatic discovery (see item 9 above).
2. **Speaker photos** — currently pulled from the Mac's `~/Downloads/` root by
   filename (e.g. `Riz.jpg`, `Julia.jpg`) — works as long as they keep landing
   there with recognisable names.
3. **Gemini AI summary — public link.** We can read the private "Notes by
   Gemini" doc via the service account, but there's no public link to share in
   the blog/newsletter yet — needs a decision on whether to share the doc
   itself, publish an export, or drop this line from the template.
4. **Parish notices confirmation** — assumed unchanged from the website's
   "Related events" strip (`index.shtml`) unless told otherwise each time.
5. **Spotify / Apple Podcasts links** — only exist once the podcast episode
   is published *and* those platforms have indexed it (can take time) —
   can't be fetched at the moment the blog copy is drafted.
6. **Guest list CSV from Luma** — also lands in the Mac's `~/Downloads/` root
   (named like `TransformGov Talks_ <Month> <Year> - Guests - <timestamp>.csv`).
   Needed for both the Kit subscriber sync and the dashboard's "how did you
   hear about us" data. No API access to Luma exists, so this is always a
   manual export + copy, same as the photos above.

### How to reach the Mac to pull photos/guest CSV

The Mac (`Davids-MacBook-Air.local`) is NOT reliably reachable over the
`macair-new` / NordVPN Meshnet SSH alias (`dave-lanin9381.nord`) — it timed
out entirely this session. **Use mDNS/Bonjour discovery on the local LAN
instead**: `avahi-browse -art` and look for a `_ssh._tcp` / "SSH Remote
Terminal" entry — it resolved to `Davids-MacBook-Air.local` at
`192.168.0.213`, which connected fine via plain `ssh`/`scp`. Don't waste time
debugging Meshnet itself (checking `nordvpn status` etc.) — go straight to
the mDNS fallback.

### Where secrets actually live — a gotcha hit this session

**`/home/dave/secrets/` is the canonical, live secrets directory** — every
script in this repo (`sync_youtube.py`, `sync_kit.py`,
`podcast-host/generator/post_to_bluesky.py`, etc.) reads from there.
`/mnt/portable1/managed/config/secrets/` is just a **one-way backup mirror**
(`backup.yml`: `source: /home/dave/secrets/` → that mirror) — writing a new
secret there only does nothing for any running script. Every secret created
during this session (Bluesky handle/password, YouTube OAuth client) had to be
copied into `/home/dave/secrets/` after initially being written only to the
backup path. **Any new secret file must go into `/home/dave/secrets/`
first** — the backup copy will pick it up automatically on the next backup
run, not the other way round.

## Bluesky post — full prerequisite checklist

The rich multi-post thread (from the original automation doc's template) needs
**four** links, not just the video — checked status as of 2026-10-01, right
after publishing the Sept 2026 episode:

- YouTube — ✅ have it (https://youtu.be/0pio6HFWSO8)
- Blog post URL — ❌ doesn't exist until Dave pastes the docx copy into Medium
  by hand (see item 8 above)
- Spotify episode — ✅ DONE, found immediately: **no API app needed at all**.
  Dave questioned why one would be required — correctly. The public show page
  (`open.spotify.com/show/0PUIa0T6fVxo0UkcTO9J2M`) is server-rendered and lists
  episode titles with their `/episode/<id>` links right in the static HTML
  (unlike Luma, which needs JS). `automation/check_episode_links.py` scrapes
  it directly. Got: `https://open.spotify.com/episode/7kFeIergJysuxfugvFfFaR`
- Apple Podcasts episode — ❌ checked via Apple's public, no-auth iTunes
  Lookup API (`https://itunes.apple.com/lookup?id=1776623246&entity=podcastEpisode`)
  — newest episode it has is still Sept 23 (Scotland), not the new one. Re-run
  `check_episode_links.py` periodically until it appears.

**Status (2026-10-01, ~21:00):** Apple indexed too — confirmed via
`itunes.apple.com/lookup` with explicit `country=gb`/`us` params (the earlier
no-country-code query happened to be checking the wrong storefront timing).
`https://podcasts.apple.com/gb/podcast/transformgov-talks-september-2026/id1776623246?i=1000792627799`.
Docx, `previous_events.yml` (past events page, rebuilt via `build_previous.py`)
all updated with YouTube + Spotify + Apple links. The blog post URL was the
last blocker — Dave posted it to Medium:
https://medium.com/@transformgovtalks/transformgov-talks-our-september-2026-london-event-505e12f717f7
(added to `previous_events.yml` too, same rebuild step).

**Bluesky: DONE — see the corrected version in item 7 above.** (First attempt
used the wrong tool — a single generic announcement post via
`post_to_bluesky.py` — which Dave caught and had removed; corrected with
`post_bluesky_thread.py`, the proper 7-post thread.) One real bug hit along
the way, independent of which script: the stored
`transformgov_talks_bluesky_handle` secret had a leading `@`
(`@transformgovtalks.bsky.social`), which broke login with a cryptic
`InvalidEmail` error — Bluesky's login endpoint tries to parse any identifier
containing `@` as an email address, and an empty local-part before the `@`
fails validation. Fixed by storing the bare handle
(`transformgovtalks.bsky.social`), matching the existing WYSLI secret's
format — **no leading `@` for any Bluesky handle secret, ever.**
