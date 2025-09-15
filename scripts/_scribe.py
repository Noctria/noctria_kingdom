#!/usr/bin/env python3
from __future__ import annotations
import os, json
import psycopg2

+DSN = (
+    os.getenv("NOCTRIA_DB_DSN")
+    or os.getenv("NOCTRIA_OBS_PG_DSN")
+    or os.getenv("DATABASE_URL")
+)

def _conn():
    if not DSN: return None
    return psycopg2.connect(DSN)

def ensure_thread(topic: str, tags: list[str] | None = None) -> int:
    conn = _conn()
    if not conn: return 0
    with conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM chronicle_thread WHERE topic=%s AND is_open=TRUE ORDER BY id DESC LIMIT 1", (topic,))
        row = cur.fetchone()
        if row: return row[0]
        cur.execute("INSERT INTO chronicle_thread(topic,tags) VALUES (%s,%s) RETURNING id", (topic, tags or []))
        return cur.fetchone()[0]

def log_chronicle(
    title: str, category: str, content_md: str,
    trace_id: str | None = None, topic: str = "PDCA nightly",
    tags: list[str] | None = None, refs: dict | None = None
) -> None:
    conn = _conn()
    if not conn: return
    th_id = ensure_thread(topic, tags or [])
    with conn, conn.cursor() as cur:
        cur.execute(
            """INSERT INTO chronicle_entry(thread_id, trace_id, title, category, content_md, refs)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (th_id, trace_id, title, category, content_md, json.dumps(refs or {}))
        )
