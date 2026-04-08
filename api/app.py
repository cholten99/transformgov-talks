
  import os
  from pathlib import Path
  from flask import Flask, jsonify
  import psycopg2
  from dotenv import load_dotenv

  load_dotenv(Path(__file__).parent.parent / ".env")

  app = Flask(__name__)

  DB_HOST = os.getenv("DB_HOST", "localhost")
  DB_NAME = os.getenv("DB_NAME", "transformgov_talks")
  DB_USER = os.getenv("DB_USER", "replit")
  DB_PASS = os.getenv("DB_PASS")


  def get_db():
      return psycopg2.connect(host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS)


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
  