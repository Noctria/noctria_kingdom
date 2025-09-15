#!/usr/bin/env python3
from __future__ import annotations
import os, json
import psycopg2, psycopg2.extras

+DSN = (
+    os.getenv("NOCTRIA_DB_DSN")
+    or os.getenv("NOCTRIA_OBS_PG_DSN")
+    or os.getenv("DATABASE_URL")
+)

def _conn():
    if not DSN:
        return None
    return psycopg2.connect(DSN)

def db_exec(sql: str, params: tuple | None = None):
    if not DSN:
        return
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            conn.commit()

def log_message(trace_id: str, agent: str, role: str, content: str, meta: dict | None = None):
    db_exec("""INSERT INTO agent_message(trace_id, agent, role, content, meta)
               VALUES (%s,%s,%s,%s,%s)""", (trace_id, agent, role, content, json.dumps(meta or {})))

def start_run(trace_id: str, notes: str = ""):
    db_exec("INSERT INTO agent_run(trace_id,status,notes) VALUES (%s,'RUNNING',%s)", (trace_id, notes))

def finish_run(trace_id: str, status: str = "SUCCESS"):
    db_exec("UPDATE agent_run SET status=%s, finished_at=now() WHERE trace_id=%s", (status, trace_id))

def save_artifact(trace_id: str, kind: str, path: str | None = None, payload: dict | None = None):
    db_exec("""INSERT INTO build_artifact(trace_id,kind,path,payload) VALUES (%s,%s,%s,%s)""",
            (trace_id, kind, path, json.dumps(payload or {})))

def save_tests(trace_id: str, summary: dict, junit_path: str | None):
    db_exec("""INSERT INTO test_result(trace_id,total,passed,failed,errors,skipped,junit_xml_path,raw)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (trace_id, summary.get("total"), summary.get("passed"), summary.get("failed"),
             summary.get("errors"), summary.get("skipped"), junit_path, json.dumps(summary)))

def save_lint(trace_id: str, summary: dict, json_path: str | None):
    db_exec("""INSERT INTO lint_result(trace_id,errors,warnings,ruff_json_path,raw)
               VALUES (%s,%s,%s,%s,%s)""",
            (trace_id, summary.get("errors"), summary.get("warnings"), json_path, json.dumps(summary)))

def log_commit(trace_id: str, branch: str, sha: str | None, files: list[str], message: str):
    db_exec("""INSERT INTO git_commit_log(trace_id,branch,sha,files,message) VALUES (%s,%s,%s,%s,%s)""",
            (trace_id, branch, sha, json.dumps(files), message))

def load_recent_chronicle(n: int = 12, topic: str = "PDCA nightly") -> list[dict]:
    if not DSN: return []
    with _conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
          SELECT e.ts, e.title, e.category, e.content_md, e.refs
          FROM chronicle_entry e
          JOIN chronicle_thread t ON e.thread_id=t.id
          WHERE t.topic=%s
          ORDER BY e.ts DESC LIMIT %s
        """, (topic, n))
        return list(cur.fetchall())
