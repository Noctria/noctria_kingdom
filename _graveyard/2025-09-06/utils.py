# src/core/utils.py
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any

__all__ = [
    "setup_logger",
    "log_validation_event",
    "log_execution_event",
    "log_metric",
]

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
def setup_logger(name: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """
    シンプルなロガー初期化。二重ハンドラ防止付き。
    """
    logger = logging.getLogger(name or __name__)
    if not logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(h)
    logger.setLevel(level)
    return logger


_logger = setup_logger("noctria.core.utils")

# -------------------------------------------------------------------
# PostgreSQL (optional / lazy import)
#   - psycopg2（v2） or psycopg（v3）を**必要時だけ** import
#   - どちらも無ければ、呼び出し関数側で警告して NO-OP
# -------------------------------------------------------------------
_DB_IMPORT_WARNED = False


def _import_pg():
    global _DB_IMPORT_WARNED
    try:
        import psycopg2 as _pg  # type: ignore
        return "psycopg2", _pg
    except ModuleNotFoundError:
        try:
            import psycopg as _pg  # type: ignore
            return "psycopg", _pg
        except ModuleNotFoundError:
            if not _DB_IMPORT_WARNED:
                _logger.warning(
                    "PostgreSQL driver not installed; install one of:\n"
                    "  pip install psycopg2-binary  # (local quickstart)\n"
                    "  or\n"
                    "  pip install 'psycopg[binary]'  # psycopg v3"
                )
                _DB_IMPORT_WARNED = True
            return None, None


def _env_dsn() -> Optional[str]:
    """
    DSNの解決:
      1) NOCTRIA_OBS_PG_DSN（最優先）
      2) POSTGRES_* 環境変数から組み立て
    """
    dsn = os.getenv("NOCTRIA_OBS_PG_DSN")
    if dsn:
        return dsn

    db = os.getenv("POSTGRES_DB", "airflow")
    user = os.getenv("POSTGRES_USER", "airflow")
    pwd = os.getenv("POSTGRES_PASSWORD", "airflow")
    host = os.getenv("POSTGRES_HOST", "noctria_postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    if host and db and user:
        return f"postgresql://{user}:{pwd}@{host}:{port}/{db}"
    return None


def _get_conn():
    """
    コネクション取得（成功時に conn を返す。失敗時は None）
    """
    driver, pg = _import_pg()
    if not pg:
        return None
    dsn = _env_dsn()
    if not dsn:
        if not _DB_IMPORT_WARNED:
            _logger.warning("PG DSN not provided; set NOCTRIA_OBS_PG_DSN or POSTGRES_* envs.")
        return None
    try:
        # psycopg2 でも psycopg3 でも connect(dsn) は同じ
        return pg.connect(dsn)  # type: ignore[attr-defined]
    except Exception as e:
        _logger.warning("PG connect failed: %s", e)
        return None


def _utcnow():
    return datetime.now(timezone.utc)


# -------------------------------------------------------------------
# Public: Logging to DB (NO-OP friendly)
#   - DBが未設定/未導入でも例外を投げずに安全にスキップ
#   - JSONは文字列 + ::jsonb キャストで両ドライバ互換
# -------------------------------------------------------------------
def log_validation_event(
    dag_id: str,
    task_id: str,
    run_id: str,
    symbol: str,
    check_name: str,
    passed: bool,
    severity: str = "INFO",
    details: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
) -> None:
    """
    検証イベントを validation_events に挿入。
    スキーマ例:
      CREATE TABLE IF NOT EXISTS validation_events(
        id BIGSERIAL PRIMARY KEY,
        ts timestamptz NOT NULL DEFAULT now(),
        dag_id text, task_id text, run_id text,
        symbol text, check_name text, passed boolean,
        severity text, details jsonb, context jsonb, trace_id text
      );
    """
    conn = _get_conn()
    if conn is None:
        _logger.debug("log_validation_event skipped (no DB).")
        return

    sql = """
    INSERT INTO validation_events
      (ts, dag_id, task_id, run_id, symbol, check_name, passed, severity, details, context, trace_id)
    VALUES
      (%s,  %s,     %s,      %s,     %s,     %s,         %s,     %s,       %s::jsonb, %s::jsonb, %s)
    """
    params = (
        _utcnow(),
        dag_id,
        task_id,
        run_id,
        symbol,
        check_name,
        passed,
        severity,
        json.dumps(details or {}, ensure_ascii=False),
        json.dumps(context or {}, ensure_ascii=False),
        trace_id,
    )
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
    except Exception as e:
        _logger.warning("log_validation_event failed: %s", e)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def log_execution_event(
    dag_id: str,
    task_id: str,
    run_id: str,
    symbol: str,
    action: str,
    qty: float,
    price: float,
    status: str,
    broker_order_id: Optional[str] = None,
    latency_ms: Optional[int] = None,
    error: Optional[str] = None,
    extras: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
) -> None:
    """
    実行イベントを execution_events に挿入。
    スキーマ例:
      CREATE TABLE IF NOT EXISTS execution_events(
        id BIGSERIAL PRIMARY KEY,
        ts timestamptz NOT NULL DEFAULT now(),
        dag_id text, task_id text, run_id text,
        symbol text, action text, qty double precision, price double precision,
        status text, broker_order_id text, latency_ms integer,
        error text, extras jsonb, trace_id text
      );
    """
    conn = _get_conn()
    if conn is None:
        _logger.debug("log_execution_event skipped (no DB).")
        return

    sql = """
    INSERT INTO execution_events
      (ts, dag_id, task_id, run_id, symbol, action, qty, price, status,
       broker_order_id, latency_ms, error, extras, trace_id)
    VALUES
      (%s, %s, %s, %s, %s, %s, %s, %s, %s,
       %s, %s, %s, %s::jsonb, %s)
    """
    params = (
        _utcnow(),
        dag_id,
        task_id,
        run_id,
        symbol,
        action,
        float(qty),
        float(price),
        status,
        broker_order_id,
        latency_ms,
        error,
        json.dumps(extras or {}, ensure_ascii=False),
        trace_id,
    )
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
    except Exception as e:
        _logger.warning("log_execution_event failed: %s", e)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def log_metric(
    ts: Optional[datetime],
    metric_name: str,
    value: float,
    tags: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
) -> None:
    """
    時系列メトリクスを perf_timeseries に挿入。
    スキーマ例:
      CREATE TABLE IF NOT EXISTS perf_timeseries(
        id BIGSERIAL PRIMARY KEY,
        ts timestamptz NOT NULL,
        metric_name text NOT NULL,
        value double precision,
        tags jsonb,
        trace_id text
      );
    """
    conn = _get_conn()
    if conn is None:
        _logger.debug("log_metric skipped (no DB).")
        return

    sql = """
    INSERT INTO perf_timeseries (ts, metric_name, value, tags, trace_id)
    VALUES (%s, %s, %s, %s::jsonb, %s)
    """
    params = (
        ts or _utcnow(),
        metric_name,
        float(value),
        json.dumps(tags or {}, ensure_ascii=False),
        trace_id,
    )
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
    except Exception as e:
        _logger.warning("log_metric failed: %s", e)
    finally:
        try:
            conn.close()
        except Exception:
            pass
