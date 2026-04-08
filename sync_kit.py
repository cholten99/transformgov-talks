#!/usr/bin/env python3
  """
  sync_kit.py - Sync Kit mailing list subscribers into PostgreSQL.

  Usage:
    python3 sync_kit.py

  Reads .env from the project root. Upserts Kit subscribers into the
  kit_subscribers table. Safe to run repeatedly - uses upsert on id.
  """
  import os
  import sys
  import logging
  from pathlib import Path

  import requests
  import psycopg2
  from dotenv import load_dotenv

  load_dotenv(Path(__file__).parent / '.env')

  logging.basicConfig(
      level=logging.INFO,
      format='%(asctime)s %(levelname)s: %(message)s'
  )
  log = logging.getLogger(__name__)

  KIT_API_KEY = os.getenv('KIT_API_KEY')
  DB_HOST     = os.getenv('DB_HOST', 'localhost')
  DB_NAME     = os.getenv('DB_NAME', 'transformgov_talks')
  DB_USER     = os.getenv('DB_USER', 'replit')
  DB_PASS     = os.getenv('DB_PASS')

  KIT_BASE = 'https://api.kit.com/v4'
  HEADERS  = {'X-Kit-Api-Key': KIT_API_KEY, 'Accept': 'application/json'}

  CREATE_TABLE = """
  CREATE TABLE IF NOT EXISTS kit_subscribers (
      id            BIGINT PRIMARY KEY,
      email_address TEXT        NOT NULL,
      first_name    TEXT,
      state         TEXT        NOT NULL,
      created_at    TIMESTAMPTZ,
      synced_at     TIMESTAMPTZ DEFAULT NOW()
  );
  """

  UPSERT = """
  INSERT INTO kit_subscribers (id, email_address, first_name, state, created_at, synced_at)
  VALUES (%(id)s, %(email_address)s, %(first_name)s, %(state)s, %(created_at)s, NOW())
  ON CONFLICT (id) DO UPDATE SET
      email_address = EXCLUDED.email_address,
      first_name    = EXCLUDED.first_name,
      state         = EXCLUDED.state,
      synced_at     = NOW();
  """


  def fetch_subscribers(created_after=None):
      """Yield every subscriber from Kit, handling cursor pagination."""
      params = {'per_page': 500}
      if created_after:
          params['created_after'] = created_after.strftime('%Y-%m-%d')

      fetched = 0
      after_cursor = None
      while True:
          if after_cursor:
              params['after'] = after_cursor

          resp = requests.get(f'{KIT_BASE}/subscribers', headers=HEADERS, params=params, timeout=30)
          resp.raise_for_status()
          data = resp.json()

          subscribers = data.get('subscribers', [])
          pagination  = data.get('pagination', {})

          for s in subscribers:
              yield s
          fetched += len(subscribers)
          log.info(f'  ...{fetched} fetched so far')

          if not pagination.get('has_next_page'):
              break
          after_cursor = pagination.get('end_cursor')
          params.pop('after', None)


  def main():
      if not KIT_API_KEY:
          log.error('KIT_API_KEY not set - check .env')
          sys.exit(1)
      if not DB_PASS:
          log.error('DB_PASS not set - check .env')
          sys.exit(1)

      conn = psycopg2.connect(host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS)
      try:
          with conn.cursor() as cur:
              cur.execute(CREATE_TABLE)
              conn.commit()
              log.info('Table ready.')

              cur.execute('SELECT MAX(created_at) FROM kit_subscribers')
              last_date = cur.fetchone()[0]
              if last_date:
                  log.info(f'Incremental sync - fetching subscribers created after {last_date.date()}')
              else:
                  log.info('First run - full sync of all subscribers')

              count = 0
              for sub in fetch_subscribers(created_after=last_date):
                  cur.execute(UPSERT, {
                      'id':            sub['id'],
                      'email_address': sub['email_address'],
                      'first_name':    sub.get('first_name'),
                      'state':         sub['state'],
                      'created_at':    sub.get('created_at'),
                  })
                  count += 1

              conn.commit()
              log.info(f'Sync complete - {count} records upserted.')
      finally:
          conn.close()


  if __name__ == '__main__':
      main()
  