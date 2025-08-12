# src/plan_data/observability.py
from __future__ import annotations

import os
import logging
from typing import Optional
from datetime import datetime, timezone

# ==== DB driver 両対応（psycopg2 → psycopg3 フォールバック） ====
try:
    import psycopg2 as _pg  # psycopg2-binary
    _DB_KIND = "psycopg2"
except ModuleNotFoundError:  # psycopg3
    import psycopg as _pg  # type: ignore
    _DB_KIND = "psycopg3"

_connect = _pg.connect  # 両者で共通

# ---------- logging ----------
logger = logging.getLogger("noctria.observability")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")


# ---------- utils ----------
def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_dsn(conn_str: Optional[str]) -> str:
    """
    接続文字列が未指定なら、環境変数 NOCTRIA_OBS_PG_DSN を使う。
    例: postgresql://user:pass@localhost:5432/noctria_db
    """
    dsn = conn_str or os.getenv("NOCTRIA_OBS_PG_DSN")
    if not dsn:
        raise ValueError("PostgreSQL DSN is not provided. Set NOCTRIA_OBS_PG_DSN or pass conn_str.")
    return dsn


# ---------- schema bootstrap (optional/for dev) ----------
_CREATE_PLAN_RUNS = """
CREATE TABLE IF NOT EXISTS obs_plan_runs (
  id                BIGSERIAL PRIMARY KEY,
  ts                TIMESTAMPTZ NOT NULL DEFAULT now(),
  phase             TEXT NOT NULL,          -- collector / features / statistics など
  dur_sec           INTEGER,
  rows              INTEGER,
  missing_ratio     REAL,
  error_rate        REAL,
  trace_id          TEXT
);
CREATE INDEX IF NOT EXISTS idx_plan_runs_ts    ON obs_plan_runs(ts);
CREATE INDEX IF NOT EXISTS idx_plan_runs_trace ON obs_plan_runs(trace_id);
"""

_CREATE_INFER_CALLS = """
CREATE TABLE IF NOT EXISTS obs_infer_calls (
  id                     BIGSERIAL PRIMARY KEY,
  ts                     TIMESTAMPTZ NOT NULL DEFAULT now(),
  model                  TEXT NOT NULL,     -- AURUS / LEVIA / PROM / VERITAS など
  ver                    TEXT,              -- モデル/戦略バージョン
  dur_ms                 INTEGER,
  success                BOOLEAN,
  feature_staleness_min  INTEGER,
  trace_id               TEXT
);
CREATE INDEX IF NOT EXISTS idx_infer_calls_ts    ON obs_infer_calls(ts);
CREATE INDEX IF NOT EXISTS idx_infer_calls_trace ON obs_infer_calls(trace_id);
"""


def ensure_tables(conn_str: Optional[str] = None) -> None:
    """
    観測テーブル（obs_plan_runs / obs_infer_calls）を存在しなければ作る。
    本番はマイグレーション（Alembic 等）推奨。開発・PoC向けの補助。
    """
    dsn = _get_dsn(conn_str)
    with _connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(_CREATE_PLAN_RUNS)
            cur.execute(_CREATE_INFER_CALLS)
    logger.info("observability tables ensured via %s.", _DB_KIND)


# ---------- public API ----------
def log_plan_run(conn_str: Optional[str],
                 phase: str,
                 rows: int,
                 dur_sec: int | float,
                 missing_ratio: float,
                 error_rate: float,
                 trace_id: Optional[str] = None) -> Optional[int]:
    """
    PLAN層の各フェーズ（collector/features/statistics）の計測を1件記録。
    戻り値: 追加行の id（失敗時は None）
    """
    sql = """
    INSERT INTO obs_plan_runs (ts, phase, dur_sec, rows, missing_ratio, error_rate, trace_id)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    """
    params = (_utcnow(), phase, int(dur_sec), int(rows), float(missing_ratio), float(error_rate), trace_id)
    dsn = _get_dsn(conn_str)
    try:
        with _connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                new_id = cur.fetchone()[0]
                return int(new_id)
    except Exception as e:
        logger.warning("log_plan_run failed: %s (phase=%s, trace_id=%s)", e, phase, trace_id)
        return None


def log_infer_call(conn_str: Optional[str],
                   model: str,
                   ver: str,
                   dur_ms: int,
                   success: bool,
                   feature_staleness_min: int,
                   trace_id: Optional[str] = None) -> Optional[int]:
    """
    AI提案/予測（propose/predict）の呼び出し1件を記録。
    戻り値: 追加行の id（失敗時は None）
    """
    sql = """
    INSERT INTO obs_infer_calls (ts, model, ver, dur_ms, success, feature_staleness_min, trace_id)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    """
    params = (_utcnow(), model, ver, int(dur_ms), bool(success), int(feature_staleness_min), trace_id)
    dsn = _get_dsn(conn_str)
    try:
        with _connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                new_id = cur.fetchone()[0]
                return int(new_id)
    except Exception as e:
        logger.warning("log_infer_call failed: %s (model=%s, trace_id=%s)", e, model, trace_id)
        return None


# ---------- convenience ----------
def ping(conn_str: Optional[str] = None) -> bool:
    """
    接続ヘルスチェック。接続できれば True。
    """
    dsn = _get_dsn(conn_str)
    try:
        with _connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
        return True
    except Exception as e:
        logger.warning("observability ping failed: %s", e)
        return False
