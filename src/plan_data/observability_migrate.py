# src/plan_data/observability_migrate.py
# [NOCTRIA_CORE_REQUIRED]
from __future__ import annotations

import os
import sys

import psycopg2
from psycopg2.extras import Json

from src.core.envload import load_noctria_env

DDL = """
-- 既存 obs_plan_runs を“新旧互換”に拡張する（列が無い場合だけ追加）
ALTER TABLE IF EXISTS obs_plan_runs
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ;

ALTER TABLE IF EXISTS obs_plan_runs
  ADD COLUMN IF NOT EXISTS payload JSONB;

-- created_at のデフォルトと NOT NULL（NULLが残ると失敗するので順序に注意）
ALTER TABLE IF EXISTS obs_plan_runs
  ALTER COLUMN created_at SET DEFAULT now();

UPDATE obs_plan_runs
   SET created_at = COALESCE(created_at, ts, now())
 WHERE created_at IS NULL;

ALTER TABLE IF EXISTS obs_plan_runs
  ALTER COLUMN created_at SET NOT NULL;

-- よく使うINDEX
CREATE INDEX IF NOT EXISTS idx_obs_plan_runs_trace_id ON obs_plan_runs(trace_id);
CREATE INDEX IF NOT EXISTS idx_obs_plan_runs_created_at ON obs_plan_runs(created_at);

-- 互換ビュー：旧meta/tsを透過で読める
CREATE OR REPLACE VIEW obs_plan_runs_simple AS
SELECT
  id,
  COALESCE(created_at, ts) AS created_at,
  trace_id,
  COALESCE(payload, meta) AS payload
FROM obs_plan_runs;
"""


def main() -> int:
    load_noctria_env()
    dsn = os.getenv("NOCTRIA_OBS_PG_DSN")
    if not dsn:
        print("[migrate] NOCTRIA_OBS_PG_DSN is not set (check .env loading)", file=sys.stderr)
        return 2

    print(f"[migrate] DSN = {dsn!r}")
    with psycopg2.connect(dsn) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(DDL)
            print("[migrate] DDL/INDEX/VIEW applied.")

        # スモーク行（重複させないよう trace_id を固定でupsert相当）
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO obs_plan_runs(trace_id, payload)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
            """,
                ("obs_migrate_smoke", Json({"ok": True, "migrated": True})),
            )
            cur.execute(
                "SELECT id, created_at, trace_id FROM obs_plan_runs WHERE trace_id=%s ORDER BY id DESC LIMIT 1;",
                ("obs_migrate_smoke",),
            )
            row = cur.fetchone()
            print("[migrate] smoke_row:", row)

    print("[migrate] done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
