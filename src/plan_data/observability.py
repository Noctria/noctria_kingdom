# src/plan_data/observability.py
from __future__ import annotations

import os
import logging
from typing import Optional, Tuple
from datetime import datetime, timezone
import importlib

# ----------------------------------
# logger
# ----------------------------------
logger = logging.getLogger("noctria.observability")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

# ----------------------------------
# small utils
# ----------------------------------
def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

def _get_dsn(conn_str: Optional[str]) -> str:
    """
    接続文字列が未指定なら、環境変数 NOCTRIA_OBS_PG_DSN を使う。
    例: postgresql://noctria:******@localhost:5432/noctria_db
    """
    dsn = conn_str or os.getenv("NOCTRIA_OBS_PG_DSN")
    if not dsn:
        raise ValueError(
            "PostgreSQL DSN is not provided. "
            "Set NOCTRIA_OBS_PG_DSN or pass conn_str."
        )
    return dsn

# ----------------------------------
# driver loader (lazy import)
# ----------------------------------
_DRIVER = None      # type: ignore[var-annotated]
_DB_KIND = None     # "psycopg2" or "psycopg"

def _import_driver() -> Tuple[object, str]:
    """
    psycopg2 (v2) → psycopg (v3) の順で動的 import。結果をキャッシュ。
    pytest の収集時（import 時）にドライバ未導入でも落ちないよう遅延解決する。
    """
    global _DRIVER, _DB_KIND
    if _DRIVER is not None and _DB_KIND is not None:
        return _DRIVER, _DB_KIND

    # try psycopg2 first
    try:
        drv = importlib.import_module("psycopg2")
        _DRIVER, _DB_KIND = drv, "psycopg2"
        return _DRIVER, _DB_KIND
    except ModuleNotFoundError:
        pass

    # fallback: psycopg (v3)
    try:
        drv = importlib.import_module("psycopg")
        _DRIVER, _DB_KIND = drv, "psycopg"
        return _DRIVER, _DB_KIND
    except ModuleNotFoundError as e:
        raise RuntimeError(
            "Neither 'psycopg2' nor 'psycopg' is installed in this interpreter.\n"
            "Install one of them within the SAME venv that runs pytest, e.g.:\n"
            "  pip install 'psycopg2-binary>=2.9.9,<3.0'\n"
            "or\n"
            "  pip install 'psycopg[binary]>=3.1,<3.2'"
        ) from e

# ----------------------------------
# schema bootstrap (for dev/PoC)
# ----------------------------------
_CREATE_PLAN_RUNS = """
CREATE TABLE IF NOT EXISTS obs_plan_runs (
  id                BIGSERIAL PRIMARY KEY,
  ts                TIMESTAMPTZ NOT NULL DEFAULT now(),
  phase             TEXT NOT NULL,          -- collector / features / statistics
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
  model                  TEXT NOT NULL,     -- AURUS / LEVIA / PROM / VERITAS
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
    観測テーブル（obs_plan_runs / obs_infer_calls）を存在しなければ作成。
    本番では Alembic などのマイグレーション推奨。開発・PoC 向けの保険。
    """
    dsn = _get_dsn(conn_str)
    drv, kind = _import_driver()
    # psycopg2 / psycopg 両方とも connect(dsn) と with をサポート
    with drv.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(_CREATE_PLAN_RUNS)
            cur.execute(_CREATE_INFER_CALLS)
    logger.info("observability tables ensured via %s.", kind)

# ----------------------------------
# public API
# ----------------------------------
def log_plan_run(conn_str: Optional[str],
                 phase: str,
                 rows: int,
                 dur_sec: int,
                 missing_ratio: float,
                 error_rate: float,
                 trace_id: Optional[str] = None) -> Optional[int]:
    """
    P層の各フェーズ（collector/features/statistics）の計測を1件記録。
    戻り値: 追加行の id（失敗時は None）
    """
    dsn = _get_dsn(conn_str)
    drv, _ = _import_driver()
    sql = (
        "INSERT INTO obs_plan_runs (ts, phase, dur_sec, rows, missing_ratio, error_rate, trace_id) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id"
    )
    params = (_utcnow(), phase, dur_sec, rows, missing_ratio, error_rate, trace_id)
    try:
        with drv.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                new_id = cur.fetchone()[0]
                return new_id
    except Exception as e:
        logger.warning(
            "log_plan_run failed: %s (phase=%s, trace_id=%s)", e, phase, trace_id
        )
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
    dsn = _get_dsn(conn_str)
    drv, _ = _import_driver()
    sql = (
        "INSERT INTO obs_infer_calls (ts, model, ver, dur_ms, success, feature_staleness_min, trace_id) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id"
    )
    params = (_utcnow(), model, ver, dur_ms, success, feature_staleness_min, trace_id)
    try:
        with drv.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                new_id = cur.fetchone()[0]
                return new_id
    except Exception as e:
        logger.warning(
            "log_infer_call failed: %s (model=%s, trace_id=%s)", e, model, trace_id
        )
        return None

# ----------------------------------
# ping
# ----------------------------------
def ping(conn_str: Optional[str] = None) -> bool:
    """接続ヘルスチェック。接続できれば True。"""
    dsn = _get_dsn(conn_str)
    try:
        drv, _ = _import_driver()
        with drv.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
        return True
    except Exception as e:
        logger.warning("observability ping failed: %s", e)
        return False
