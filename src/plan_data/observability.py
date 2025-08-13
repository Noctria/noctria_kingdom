# src/plan_data/observability.py
from __future__ import annotations

import importlib
import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional, Tuple

# =============================================================================
# Observability I/O (PostgreSQL)
# - 旧API互換: plan / infer の簡易ロギングを維持
# - 新API拡張: decisions / exec_events / alerts を追加
# - CREATE IF NOT EXISTS + ALTER IF NOT EXISTS で既存スキーマを前方互換に拡張
# - DSNは NOCTRIA_OBS_PG_DSN から取得（明示指定も可）
# - 追加: ensure_views()/ensure_views_and_mvs()/refresh_latency_daily() で
#         View / MV を自動作成・更新
# =============================================================================

# -----------------------------------------------------------------------------
# logger
# -----------------------------------------------------------------------------
logger = logging.getLogger("noctria.observability")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

# -----------------------------------------------------------------------------
# small utils
# -----------------------------------------------------------------------------
def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

def _json(obj: Any) -> str:
    """
    PythonオブジェクトをJSON文字列へ。
    pandas.Timestamp / datetime 等は isoformat にフォールバック。
    """
    try:
        import pandas as pd  # type: ignore
    except Exception:
        pd = None
    if pd is not None and isinstance(obj, getattr(pd, "Timestamp", ())):
        return json.dumps(obj.isoformat(), ensure_ascii=False)
    return json.dumps(
        obj,
        default=lambda o: o.isoformat() if hasattr(o, "isoformat") else str(o),
        ensure_ascii=False,
    )

def _get_dsn(conn_str: Optional[str]) -> str:
    """
    接続文字列が未指定なら、環境変数 NOCTRIA_OBS_PG_DSN を使う。
    例: postgresql://noctria:******@localhost:5433/noctria_db
    """
    dsn = conn_str or os.getenv("NOCTRIA_OBS_PG_DSN")
    if not dsn:
        raise ValueError(
            "PostgreSQL DSN is not provided. "
            "Set NOCTRIA_OBS_PG_DSN or pass conn_str."
        )
    return dsn

# -----------------------------------------------------------------------------
# driver loader (lazy import)
# -----------------------------------------------------------------------------
_DRIVER = None      # type: ignore[var-annotated]
_DB_KIND = None     # "psycopg2" or "psycopg"

def _import_driver() -> Tuple[object, str]:
    """
    psycopg2 (v2) → psycopg (v3) の順で動的 import。結果をキャッシュ。
    pytest/import 時にドライバ未導入でも直ちに落ちないようにする。
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
            "Install in the SAME venv:\n"
            "  pip install 'psycopg2-binary>=2.9.9,<3.0'\n"
            "  # or\n"
            "  pip install 'psycopg[binary]>=3.1,<3.2'"
        ) from e

@contextmanager
def _get_conn(dsn: str):
    drv, kind = _import_driver()
    if kind == "psycopg2":
        conn = drv.connect(dsn)
        conn.autocommit = True
        try:
            yield conn
        finally:
            conn.close()
    else:
        # psycopg v3
        conn = drv.connect(dsn, autocommit=True)
        try:
            yield conn
        finally:
            conn.close()

def _exec(dsn: str, sql: str, params: Optional[Iterable[Any]] = None) -> None:
    with _get_conn(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())

def _fetchone(dsn: str, sql: str, params: Optional[Iterable[Any]] = None):
    with _get_conn(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()

# -----------------------------------------------------------------------------
# schema bootstrap (for dev/PoC)
# 既存の軽量スキーマを拡張し、Decision/Exec/Alert も記録可能に
# 旧スキーマが既にある場合は不足カラムを追加（ADD COLUMN IF NOT EXISTS）
# -----------------------------------------------------------------------------
_CREATE_PLAN_RUNS = """
CREATE TABLE IF NOT EXISTS obs_plan_runs (
  id                BIGSERIAL PRIMARY KEY,
  ts                TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- 旧API（フェーズ粒度）
  phase             TEXT,
  dur_sec           INTEGER,
  rows              INTEGER,
  missing_ratio     REAL,
  error_rate        REAL,
  -- 新API（スパン粒度）
  trace_id          TEXT,
  started_at        TIMESTAMPTZ,
  finished_at       TIMESTAMPTZ,
  status            TEXT,
  meta              JSONB
);
CREATE INDEX IF NOT EXISTS idx_plan_runs_ts    ON obs_plan_runs(ts);
CREATE INDEX IF NOT EXISTS idx_plan_runs_trace ON obs_plan_runs(trace_id);
"""

_ALTER_PLAN_RUNS = """
ALTER TABLE obs_plan_runs ADD COLUMN IF NOT EXISTS started_at    TIMESTAMPTZ;
ALTER TABLE obs_plan_runs ADD COLUMN IF NOT EXISTS finished_at   TIMESTAMPTZ;
ALTER TABLE obs_plan_runs ADD COLUMN IF NOT EXISTS status        TEXT;
ALTER TABLE obs_plan_runs ADD COLUMN IF NOT EXISTS meta          JSONB;
ALTER TABLE obs_plan_runs ADD COLUMN IF NOT EXISTS phase         TEXT;
ALTER TABLE obs_plan_runs ADD COLUMN IF NOT EXISTS dur_sec       INTEGER;
ALTER TABLE obs_plan_runs ADD COLUMN IF NOT EXISTS rows          INTEGER;
ALTER TABLE obs_plan_runs ADD COLUMN IF NOT EXISTS missing_ratio REAL;
ALTER TABLE obs_plan_runs ADD COLUMN IF NOT EXISTS error_rate    REAL;
ALTER TABLE obs_plan_runs ADD COLUMN IF NOT EXISTS ts            TIMESTAMPTZ DEFAULT now();
"""

_CREATE_INFER_CALLS = """
CREATE TABLE IF NOT EXISTS obs_infer_calls (
  id                     BIGSERIAL PRIMARY KEY,
  ts                     TIMESTAMPTZ NOT NULL DEFAULT now(),
  model                  TEXT,
  ver                    TEXT,
  dur_ms                 INTEGER,
  success                BOOLEAN,
  feature_staleness_min  INTEGER,
  trace_id               TEXT,
  -- 新API
  model_name             TEXT,
  call_at                TIMESTAMPTZ,
  duration_ms            INTEGER,
  inputs                 JSONB,
  outputs                JSONB
);
CREATE INDEX IF NOT EXISTS idx_infer_calls_ts    ON obs_infer_calls(ts);
CREATE INDEX IF NOT EXISTS idx_infer_calls_trace ON obs_infer_calls(trace_id);
"""

_ALTER_INFER_CALLS = """
ALTER TABLE obs_infer_calls ADD COLUMN IF NOT EXISTS model_name TEXT;
ALTER TABLE obs_infer_calls ADD COLUMN IF NOT EXISTS call_at    TIMESTAMPTZ;
ALTER TABLE obs_infer_calls ADD COLUMN IF NOT EXISTS duration_ms INTEGER;
ALTER TABLE obs_infer_calls ADD COLUMN IF NOT EXISTS inputs     JSONB;
ALTER TABLE obs_infer_calls ADD COLUMN IF NOT EXISTS outputs    JSONB;
ALTER TABLE obs_infer_calls ADD COLUMN IF NOT EXISTS model      TEXT;
ALTER TABLE obs_infer_calls ADD COLUMN IF NOT EXISTS ver        TEXT;
ALTER TABLE obs_infer_calls ADD COLUMN IF NOT EXISTS dur_ms     INTEGER;
ALTER TABLE obs_infer_calls ADD COLUMN IF NOT EXISTS success    BOOLEAN;
ALTER TABLE obs_infer_calls ADD COLUMN IF NOT EXISTS feature_staleness_min INTEGER;
ALTER TABLE obs_infer_calls ADD COLUMN IF NOT EXISTS ts         TIMESTAMPTZ DEFAULT now();
"""

_CREATE_DECISIONS = """
CREATE TABLE IF NOT EXISTS obs_decisions (
  id              BIGSERIAL PRIMARY KEY,
  trace_id        TEXT NOT NULL,
  made_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  engine_version  TEXT,
  strategy_name   TEXT,
  score           NUMERIC,
  reason          TEXT,
  features        JSONB,
  decision        JSONB
);
CREATE INDEX IF NOT EXISTS idx_decisions_trace ON obs_decisions(trace_id);
CREATE INDEX IF NOT EXISTS idx_decisions_made  ON obs_decisions(made_at);
"""

_CREATE_EXEC_EVENTS = """
CREATE TABLE IF NOT EXISTS obs_exec_events (
  id        BIGSERIAL PRIMARY KEY,
  trace_id  TEXT NOT NULL,
  sent_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  symbol    TEXT,
  side      TEXT,
  size      NUMERIC,
  provider  TEXT,
  status    TEXT,
  order_id  TEXT,
  response  JSONB
);
CREATE INDEX IF NOT EXISTS idx_exec_events_trace ON obs_exec_events(trace_id);
CREATE INDEX IF NOT EXISTS idx_exec_events_sent  ON obs_exec_events(sent_at);
"""

_CREATE_ALERTS = """
CREATE TABLE IF NOT EXISTS obs_alerts (
  id          BIGSERIAL PRIMARY KEY,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  policy_name TEXT NOT NULL,     -- e.g. risk.max_order_qty
  reason      TEXT NOT NULL,     -- human-readable reason
  severity    TEXT NOT NULL,     -- LOW/MEDIUM/HIGH/CRITICAL
  details     JSONB,
  trace_id    TEXT
);
CREATE INDEX IF NOT EXISTS idx_alerts_trace ON obs_alerts(trace_id);
CREATE INDEX IF NOT EXISTS idx_alerts_time  ON obs_alerts(created_at);
"""

# -----------------------------------------------------------------------------
# Views / Materialized Views
# -----------------------------------------------------------------------------
_CREATE_OR_REPLACE_TRACE_TIMELINE_VIEW = """
CREATE OR REPLACE VIEW obs_trace_timeline AS
-- Decisions
SELECT trace_id,
       made_at  AS ts,
       'DECISION' AS kind,
       decision->>'action' AS action,
       decision AS payload
FROM obs_decisions
UNION ALL
-- Exec events
SELECT trace_id,
       sent_at AS ts,
       'EXEC'  AS kind,
       side    AS action,
       jsonb_build_object(
         'size', size,
         'provider', provider,
         'status', status,
         'order_id', order_id,
         'response', response
       ) AS payload
FROM obs_exec_events
UNION ALL
-- Inference calls
SELECT trace_id,
       COALESCE(call_at, ts) AS ts,
       'INFER' AS kind,
       COALESCE(model_name, model) AS action,
       jsonb_build_object(
         'duration_ms', COALESCE(duration_ms, dur_ms),
         'success', success,
         'inputs', inputs,
         'outputs', outputs
       ) AS payload
FROM obs_infer_calls
UNION ALL
-- Plan spans / phases
SELECT trace_id,
       COALESCE(started_at, ts) AS ts,
       'PLAN:'||COALESCE(status,'phase') AS kind,
       COALESCE(phase,'') AS action,
       jsonb_build_object(
         'rows', rows,
         'missing_ratio', missing_ratio,
         'error_rate', error_rate,
         'meta', meta
       ) AS payload
FROM obs_plan_runs
UNION ALL
-- Alerts
SELECT trace_id,
       created_at AS ts,
       'ALERT'    AS kind,
       COALESCE(policy_name,'') AS action,
       jsonb_build_object(
         'reason', reason,
         'severity', severity,
         'details', details
       ) AS payload
FROM obs_alerts;
"""

_CREATE_OR_REPLACE_TRACE_LATENCY_VIEW = """
CREATE OR REPLACE VIEW obs_trace_latency AS
WITH t AS (
  SELECT trace_id, ts, kind FROM obs_trace_timeline
),
agg AS (
  SELECT
    trace_id,
    MIN(CASE WHEN kind='PLAN:START' THEN ts END) AS plan_start,
    MIN(CASE WHEN kind='INFER'      THEN ts END) AS infer_ts,
    MIN(CASE WHEN kind='DECISION'   THEN ts END) AS decision_ts,
    MIN(CASE WHEN kind='EXEC'       THEN ts END) AS exec_ts
  FROM t
  GROUP BY trace_id
)
SELECT
  trace_id,
  plan_start, infer_ts, decision_ts, exec_ts,
  EXTRACT(EPOCH FROM (infer_ts    - plan_start))*1000  AS ms_plan_to_infer,
  EXTRACT(EPOCH FROM (decision_ts - infer_ts))*1000    AS ms_infer_to_decision,
  EXTRACT(EPOCH FROM (exec_ts     - decision_ts))*1000 AS ms_decision_to_exec,
  EXTRACT(EPOCH FROM (exec_ts     - plan_start))*1000  AS ms_total
FROM agg;
"""

_CREATE_LATENCY_DAILY_MV = """
CREATE MATERIALIZED VIEW IF NOT EXISTS obs_latency_daily AS
SELECT
  date_trunc('day', plan_start)::date AS day,
  percentile_cont(0.5)  WITHIN GROUP (ORDER BY ms_total) AS p50_ms,
  percentile_cont(0.9)  WITHIN GROUP (ORDER BY ms_total) AS p90_ms,
  percentile_cont(0.95) WITHIN GROUP (ORDER BY ms_total) AS p95_ms,
  MAX(ms_total) AS max_ms,
  COUNT(*)      AS traces
FROM obs_trace_latency
GROUP BY 1;
"""

_CREATE_LATENCY_DAILY_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_obs_latency_daily_day
  ON obs_latency_daily(day);
"""

# -----------------------------------------------------------------------------
# ensure (tables & views)
# -----------------------------------------------------------------------------
def ensure_tables(conn_str: Optional[str] = None) -> None:
    """
    観測テーブル（obs_plan_runs / obs_infer_calls / obs_decisions / obs_exec_events / obs_alerts）を
    存在しなければ作成。旧スキーマが存在する場合は、不足カラムを追加（IF NOT EXISTS）。
    本番では Alembic 等のマイグレーションを推奨。開発・PoC向けの保険。
    """
    dsn = _get_dsn(conn_str)
    # CREATE
    _exec(dsn, _CREATE_PLAN_RUNS)
    _exec(dsn, _CREATE_INFER_CALLS)
    _exec(dsn, _CREATE_DECISIONS)
    _exec(dsn, _CREATE_EXEC_EVENTS)
    _exec(dsn, _CREATE_ALERTS)
    # ALTER for forward-compat
    _exec(dsn, _ALTER_PLAN_RUNS)
    _exec(dsn, _ALTER_INFER_CALLS)
    logger.info("observability tables ensured/altered.")

def ensure_views(conn_str: Optional[str] = None) -> None:
    """
    ビュー/マテビュー（timeline / latency / daily）を作成・更新。
    """
    dsn = _get_dsn(conn_str)
    _exec(dsn, _CREATE_OR_REPLACE_TRACE_TIMELINE_VIEW)
    _exec(dsn, _CREATE_OR_REPLACE_TRACE_LATENCY_VIEW)
    _exec(dsn, _CREATE_LATENCY_DAILY_MV)
    _exec(dsn, _CREATE_LATENCY_DAILY_INDEX)
    logger.info("observability views ensured/refreshed (definitions).")

def ensure_views_and_mvs(conn_str: Optional[str] = None) -> None:
    """
    テーブル→ビュー→マテビューの順に保証（ワンストップ）。
    """
    ensure_tables(conn_str)
    ensure_views(conn_str)
    # MVは定義作成のみ。内容は必要に応じて refresh。
    logger.info("tables + views/mviews ensured.")

def refresh_latency_daily(concurrently: bool = True, conn_str: Optional[str] = None) -> None:
    """
    obs_latency_daily をリフレッシュ。CONCURRENTLY はユニークインデックス必須（構築済）。
    """
    dsn = _get_dsn(conn_str)
    if concurrently:
        try:
            _exec(dsn, "REFRESH MATERIALIZED VIEW CONCURRENTLY obs_latency_daily;")
            logger.info("obs_latency_daily refreshed CONCURRENTLY.")
            return
        except Exception as e:
            logger.warning("CONCURRENTLY refresh failed: %s; falling back to non-concurrent refresh.", e)
    _exec(dsn, "REFRESH MATERIALIZED VIEW obs_latency_daily;")
    logger.info("obs_latency_daily refreshed.")

# 後方互換：旧名
def refresh_materialized(conn_str: Optional[str] = None) -> None:
    refresh_latency_daily(concurrently=True, conn_str=conn_str)

# -----------------------------------------------------------------------------
# public API（旧API互換 + 新API）
# -----------------------------------------------------------------------------
def log_plan_run(*args, **kwargs) -> Optional[int]:
    """
    互換ディスパッチャ：
      旧API: log_plan_run(conn_str, phase, rows, dur_sec, missing_ratio, error_rate, trace_id=None)
      新API: log_plan_run(trace_id=..., status='START'|'END'|'ERROR'|..., started_at=..., finished_at=..., meta={...}, conn_str=None)

    返り値: 追加行の id（失敗時 None）
    """
    if "status" in kwargs or ("trace_id" in kwargs and len(args) == 0):
        return _log_plan_status(**kwargs)  # type: ignore[arg-type]
    return _log_plan_phase(*args, **kwargs)  # type: ignore[misc]

def _log_plan_phase(conn_str: Optional[str],
                    phase: str,
                    rows: int,
                    dur_sec: int,
                    missing_ratio: float,
                    error_rate: float,
                    trace_id: Optional[str] = None) -> Optional[int]:
    """
    旧API：P層の各フェーズ（collector/features/statistics 等）の計測を1件記録。
    """
    dsn = _get_dsn(conn_str)
    sql = (
        "INSERT INTO obs_plan_runs (ts, phase, dur_sec, rows, missing_ratio, error_rate, trace_id) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id"
    )
    params = (_utcnow(), phase, int(dur_sec), int(rows), float(missing_ratio), float(error_rate), trace_id)
    try:
        row = _fetchone(dsn, sql, params)
        return row[0] if row else None  # type: ignore[index]
    except Exception as e:
        logger.warning("log_plan_run(phase) failed: %s (phase=%s, trace_id=%s)", e, phase, trace_id)
        return None

def _log_plan_status(*, trace_id: str,
                     status: str,
                     started_at: Optional[datetime] = None,
                     finished_at: Optional[datetime] = None,
                     meta: Optional[Dict[str, Any]] = None,
                     conn_str: Optional[str] = None) -> Optional[int]:
    """
    新API：Plan 実行スパンの開始/終了や状態を記録。
    status 例: START / END / ERROR / CHECKPOINT-xxx など
    """
    dsn = _get_dsn(conn_str)
    sql = (
        "INSERT INTO obs_plan_runs (trace_id, started_at, finished_at, status, meta) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING id"
    )
    params = (
        trace_id,
        started_at or (None if status != "START" else _utcnow()),
        finished_at or (None if status != "END" else _utcnow()),
        status,
        _json(meta or {}),
    )
    try:
        row = _fetchone(dsn, sql, params)
        return row[0] if row else None  # type: ignore[index]
    except Exception as e:
        logger.warning("log_plan_run(status) failed: %s (status=%s, trace_id=%s)", e, status, trace_id)
        return None

def log_infer_call(conn_str: Optional[str] = None, **kwargs) -> Optional[int]:
    """
    互換API：
      旧: log_infer_call(conn_str, model, ver, dur_ms, success, feature_staleness_min, trace_id=None)
      新: log_infer_call(trace_id=..., model_name=..., call_at=..., duration_ms=..., success=True, inputs={}, outputs={})
    """
    # 新フォーム
    if any(k in kwargs for k in ("model_name", "inputs", "outputs", "duration_ms", "call_at")):
        trace_id: Optional[str] = kwargs.get("trace_id")
        model_name: Optional[str] = kwargs.get("model_name")
        call_at: Optional[datetime] = kwargs.get("call_at")
        duration_ms: Optional[int] = kwargs.get("duration_ms")
        success: Optional[bool] = kwargs.get("success", True)
        inputs = kwargs.get("inputs")
        outputs = kwargs.get("outputs")
        dsn = _get_dsn(conn_str)
        sql = (
            "INSERT INTO obs_infer_calls (trace_id, model_name, call_at, duration_ms, success, inputs, outputs) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id"
        )
        params = (trace_id, model_name, call_at or _utcnow(), duration_ms, success, _json(inputs or {}), _json(outputs or {}))
        try:
            row = _fetchone(dsn, sql, params)
            return row[0] if row else None  # type: ignore[index]
        except Exception as e:
            logger.warning("log_infer_call(new) failed: %s (model_name=%s, trace_id=%s)", e, model_name, trace_id)
            return None

    # 旧フォーム
    model: str = kwargs["model"]
    ver: Optional[str] = kwargs.get("ver")
    dur_ms: int = kwargs["dur_ms"]
    success: bool = kwargs["success"]
    feature_staleness_min: int = kwargs.get("feature_staleness_min", 0)
    trace_id: Optional[str] = kwargs.get("trace_id")
    dsn = _get_dsn(conn_str)
    sql = (
        "INSERT INTO obs_infer_calls (ts, model, ver, dur_ms, success, feature_staleness_min, trace_id) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id"
    )
    params = (_utcnow(), model, ver, dur_ms, success, feature_staleness_min, trace_id)
    try:
        row = _fetchone(dsn, sql, params)
        return row[0] if row else None  # type: ignore[index]
    except Exception as e:
        logger.warning("log_infer_call(old) failed: %s (model=%s, trace_id=%s)", e, model, trace_id)
        return None

def log_decision(*, trace_id: str,
                 engine_version: str,
                 strategy_name: str,
                 score: float,
                 reason: str,
                 features: Dict[str, Any],
                 decision: Dict[str, Any],
                 made_at: Optional[datetime] = None,
                 conn_str: Optional[str] = None) -> Optional[int]:
    """
    DecisionEngine の最終判断を記録（obs_decisions）。
    """
    dsn = _get_dsn(conn_str)
    sql = (
        "INSERT INTO obs_decisions (trace_id, made_at, engine_version, strategy_name, score, reason, features, decision) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"
    )
    params = (
        trace_id,
        made_at or _utcnow(),
        engine_version,
        strategy_name,
        float(score),
        reason,
        _json(features or {}),
        _json(decision or {}),
    )
    try:
        row = _fetchone(dsn, sql, params)
        return row[0] if row else None  # type: ignore[index]
    except Exception as e:
        logger.warning("log_decision failed: %s (strategy=%s, trace_id=%s)", e, strategy_name, trace_id)
        return None

def log_exec_event(*, trace_id: str,
                   symbol: str,
                   side: str,
                   size: float,
                   provider: str,
                   status: str,
                   order_id: Optional[str] = None,
                   response: Optional[Dict[str, Any]] = None,
                   sent_at: Optional[datetime] = None,
                   conn_str: Optional[str] = None) -> Optional[int]:
    """
    実執行（送信結果など）を記録（obs_exec_events）。
    """
    dsn = _get_dsn(conn_str)
    sql = (
        "INSERT INTO obs_exec_events (trace_id, sent_at, symbol, side, size, provider, status, order_id, response) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"
    )
    params = (
        trace_id,
        sent_at or _utcnow(),
        symbol,
        side,
        float(size),
        provider,
        status,
        order_id,
        _json(response or {}),
    )
    try:
        row = _fetchone(dsn, sql, params)
        return row[0] if row else None  # type: ignore[index]
    except Exception as e:
        logger.warning("log_exec_event failed: %s (symbol=%s, status=%s, trace_id=%s)", e, symbol, status, trace_id)
        return None

def log_alert(*,
              policy_name: str,
              reason: str,
              severity: str = "MEDIUM",  # LOW / MEDIUM / HIGH / CRITICAL
              details: Optional[Dict[str, Any]] = None,
              trace_id: Optional[str] = None,
              created_at: Optional[datetime] = None,
              conn_str: Optional[str] = None) -> Optional[int]:
    """
    リスクゲート/再送/整合性チェックなどからのアラートを記録（obs_alerts）。
    """
    dsn = _get_dsn(conn_str)
    sql = (
        "INSERT INTO obs_alerts (created_at, policy_name, reason, severity, details, trace_id) "
        "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id"
    )
    params = (
        created_at or _utcnow(),
        policy_name,
        reason,
        severity,
        _json(details or {}),
        trace_id,
    )
    try:
        row = _fetchone(dsn, sql, params)
        return row[0] if row else None  # type: ignore[index]
    except Exception as e:
        logger.warning("log_alert failed: %s (policy=%s, trace_id=%s)", e, policy_name, trace_id)
        return None

# -----------------------------------------------------------------------------
# ping
# -----------------------------------------------------------------------------
def ping(conn_str: Optional[str] = None) -> bool:
    """接続ヘルスチェック。接続できれば True。"""
    dsn = _get_dsn(conn_str)
    try:
        _exec(dsn, "SELECT 1;")
        return True
    except Exception as e:
        logger.warning("observability ping failed: %s", e)
        return False

__all__ = [
    # ensure
    "ensure_tables", "ensure_views", "ensure_views_and_mvs",
    "refresh_latency_daily", "refresh_materialized",
    # loggers
    "log_plan_run", "log_infer_call", "log_decision",
    "log_exec_event", "log_alert",
    # misc
    "ping",
]
