
import os
import csv
import io
import zipfile
from pathlib import Path
from flask import Flask, jsonify, request
import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB max upload

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "transformgov_talks")
DB_USER = os.getenv("DB_USER", "replit")
DB_PASS = os.getenv("DB_PASS")


def get_db():
    return psycopg2.connect(host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS)


# ── Mailing list ─────────────────────────────────────────────────────────────

@app.route("/api/subscribers/monthly")
def subscribers_monthly():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    TO_CHAR(DATE_TRUNC('month', created_at), 'YYYY-MM') AS month,
                    COUNT(*)::int                                         AS new_subs,
                    SUM(COUNT(*)) OVER (
                        ORDER BY DATE_TRUNC('month', created_at)
                    )::int                                                AS total
                FROM kit_subscribers
                GROUP BY DATE_TRUNC('month', created_at)
                ORDER BY 1
            """)
            rows = cur.fetchall()
        return jsonify([{"month": r[0], "new": r[1], "total": r[2]} for r in rows])
    finally:
        conn.close()


# ── YouTube ──────────────────────────────────────────────────────────────────

@app.route("/api/youtube/videos")
def youtube_videos():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    video_id,
                    title,
                    published_at,
                    view_count,
                    SUM(view_count) OVER (ORDER BY published_at)::int AS cumulative_views
                FROM yt_videos
                ORDER BY published_at
            """)
            rows = cur.fetchall()
        return jsonify([{
            "video_id":         r[0],
            "title":            r[1],
            "published_at":     r[2].isoformat(),
            "view_count":       r[3],
            "cumulative_views": r[4],
        } for r in rows])
    finally:
        conn.close()


# ── Upload helpers ───────────────────────────────────────────────────────────

CREATE_LIBSYN = """
CREATE TABLE IF NOT EXISTS libsyn_downloads (
    id              SERIAL PRIMARY KEY,
    episode_title   TEXT      NOT NULL,
    release_date    DATE,
    total_downloads INT       NOT NULL DEFAULT 0,
    uploaded_at     TIMESTAMP NOT NULL DEFAULT NOW()
);
"""

CREATE_LUMA = """
CREATE TABLE IF NOT EXISTS luma_attendance (
    id           SERIAL PRIMARY KEY,
    event_name   TEXT        NOT NULL,
    event_date   DATE,
    attendees    INT         NOT NULL DEFAULT 0,
    uploaded_at  TIMESTAMP   NOT NULL DEFAULT NOW()
);
"""


def find_col(headers, *candidates):
    """Return first header that contains any of the candidate strings (case-insensitive)."""
    lower = [h.lower().strip() for h in headers]
    for c in candidates:
        for i, h in enumerate(lower):
            if c in h:
                return i
    return None


def parse_csv_text(text):
    """Parse CSV text, stripping BOM if present."""
    text = text.lstrip("\ufeff")
    return list(csv.reader(io.StringIO(text)))


# ── Libsyn upload ────────────────────────────────────────────────────────────

@app.route("/api/upload/libsyn", methods=["POST"])
def upload_libsyn():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["file"]
    filename = f.filename.lower()

    rows = None
    if filename.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(f.read())) as zf:
            # Look for an episode-level CSV inside the ZIP
            candidates = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            preferred = [n for n in candidates if any(
                k in n.lower() for k in ("episode", "title", "total"))]
            target = preferred[0] if preferred else (candidates[0] if candidates else None)
            if not target:
                return jsonify({"error": "No CSV found inside ZIP"}), 400
            text = zf.read(target).decode("utf-8-sig", errors="replace")
            rows = parse_csv_text(text)
    else:
        text = f.read().decode("utf-8-sig", errors="replace")
        rows = parse_csv_text(text)

    if not rows or len(rows) < 2:
        return jsonify({"error": "CSV appears empty"}), 400

    headers = rows[0]
    title_col = find_col(headers, "title", "episode", "name", "show")
    dl_col    = find_col(headers, "download", "total", "play", "listen", "count")
    date_col  = find_col(headers, "release", "publish", "date")

    if title_col is None or dl_col is None:
        return jsonify({
            "error": "Could not identify episode/download columns",
            "headers_found": headers
        }), 400

    episodes = []
    for row in rows[1:]:
        if len(row) <= max(title_col, dl_col):
            continue
        title = row[title_col].strip()
        raw   = row[dl_col].strip().replace(",", "")
        if not title or not raw.isdigit():
            continue
        date = row[date_col].strip()[:10] if date_col and len(row) > date_col else None
        episodes.append((title, date, int(raw)))

    if not episodes:
        return jsonify({"error": "No valid episode rows found"}), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_LIBSYN)
            cur.execute("ALTER TABLE libsyn_downloads ADD COLUMN IF NOT EXISTS release_date DATE")
            cur.execute("DELETE FROM libsyn_downloads")
            cur.executemany(
                "INSERT INTO libsyn_downloads (episode_title, release_date, total_downloads) VALUES (%s, %s, %s)",
                episodes
            )
            conn.commit()
        return jsonify({"ok": True, "episodes": len(episodes)})
    finally:
        conn.close()


# ── Luma upload ──────────────────────────────────────────────────────────────

@app.route("/api/upload/luma", methods=["POST"])
def upload_luma():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["file"]
    text = f.read().decode("utf-8-sig", errors="replace")
    rows = parse_csv_text(text)

    if not rows or len(rows) < 2:
        return jsonify({"error": "CSV appears empty"}), 400

    headers = rows[0]
    event_col = find_col(headers, "event name", "event", "session", "talk")
    date_col  = find_col(headers, "event start", "event date", "date", "start")

    if event_col is None:
        return jsonify({
            "error": "Could not identify event name column",
            "headers_found": headers
        }), 400

    # Count attendees per event
    from collections import defaultdict
    counts  = defaultdict(int)
    dates   = {}
    for row in rows[1:]:
        if len(row) <= event_col:
            continue
        name = row[event_col].strip()
        if not name:
            continue
        counts[name] += 1
        if date_col is not None and len(row) > date_col and name not in dates:
            dates[name] = row[date_col].strip()[:10] or None

    if not counts:
        return jsonify({"error": "No valid attendee rows found"}), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_LUMA)
            cur.execute("DELETE FROM luma_attendance")
            cur.executemany(
                "INSERT INTO luma_attendance (event_name, event_date, attendees) VALUES (%s, %s, %s)",
                [(name, dates.get(name), count) for name, count in counts.items()]
            )
            conn.commit()
        return jsonify({"ok": True, "events": len(counts)})
    finally:
        conn.close()


# ── Luma registrations read endpoint ────────────────────────────────────────

@app.route("/api/luma/events")
def luma_events():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    event_name,
                    event_date,
                    in_person,
                    online,
                    unknown_type,
                    total,
                    new_unique,
                    cumulative_unique
                FROM luma_attendance
                ORDER BY event_date
            """)
            rows = cur.fetchall()
        return jsonify([{
            "event_name":        r[0],
            "event_date":        r[1].isoformat() if r[1] else None,
            "in_person":         r[2],
            "online":            r[3],
            "unknown_type":      r[4],
            "total":             r[5],
            "new_unique":        r[6],
            "cumulative_unique": r[7],
        } for r in rows])
    finally:
        conn.close()

# ── Libsyn read endpoint ─────────────────────────────────────────────────────

@app.route("/api/libsyn/episodes")
def libsyn_episodes():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    episode_title,
                    release_date,
                    total_downloads,
                    SUM(total_downloads) OVER (ORDER BY release_date)::int AS cumulative
                FROM libsyn_downloads
                ORDER BY release_date
            """)
            rows = cur.fetchall()
        return jsonify([{
            "title":           r[0],
            "release_date":    r[1].isoformat() if r[1] else None,
            "downloads":       r[2],
            "cumulative":      r[3],
        } for r in rows])
    finally:
        conn.close()


# ── Upload status ─────────────────────────────────────────────────────────────

@app.route("/api/upload/status")
def upload_status():
    conn = get_db()
    result = {}
    try:
        with conn.cursor() as cur:
            for table, key in [("libsyn_downloads", "libsyn"), ("luma_attendance", "luma")]:
                try:
                    cur.execute(f"SELECT MAX(uploaded_at), COUNT(*) FROM {table}")
                    row = cur.fetchone()
                    result[key] = {
                        "last_upload": row[0].isoformat() if row[0] else None,
                        "rows": row[1],
                    }
                except Exception:
                    result[key] = {"last_upload": None, "rows": 0}
        return jsonify(result)
    finally:
        conn.close()
