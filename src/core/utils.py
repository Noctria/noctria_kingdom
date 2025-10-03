# [NOCTRIA_CORE_REQUIRED]
# src/core/utils.py
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

__all__ = [
    "setup_logger",
    "log_validation_event",
    "log_execution_event",
    "log_metric",
    # 便利ユーティリティ（任意で使用）
    "ensure_observability_tables",
    "get_obs_dsn",
    "set_obs_dsn",
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
_DSN_CACHE: Optional[str] = None  # set_obs_dsn() で上書き可能


def set_obs_dsn(dsn: str) -> None:
    """コード側から DSN を明示設定したい場合に使用。"""
    global _DSN_CACHE
    _DSN_CACHE = dsn


def get_obs_dsn() -> Optional[str]:
    """有効な DSN を返す（キャッシュ or 環境変数群から組立）。"""
    if _DSN_CACHE:
        return _DSN_CACHE
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


def _import_pg() -> Tuple[Optional[str], Optional[Any]]:
    """
    Returns:
        (driver_name, module_or_None)
        driver_name in {"psycopg2","psycopg"} or None
    """
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


def _get_conn():
    """
    コネクション取得（成功時は conn、失敗時は None）
    psycopg2/psycopg3 どちらでも connect(dsn) で接続可。
    """
    driver, pg = _import_pg()
    if not pg:
        return None
    dsn = get_obs_dsn()
    if not dsn:
        if not _DB_IMPORT_WARNED:
            _logger.warning("PG DSN not provided; set NOCTRIA_OBS_PG_DSN or POSTGRES_* envs.")
        return None
    try:
        return pg.connect(dsn)  # type: ignore[attr-defined]
    except Exception as e:
        _logger.warning("PG connect failed: %s", e)
        return None


def _utcnow():
    return datetime.now(timezone.utc)


# -------------------------------------------------------------------
# Public: Logging to DB (NO-OP friendly)
#   - DBが未設定/未導入でも例外を投げず安全にスキップ
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
    _insert_validation_event(
        ts=_utcnow(),
        dag_id=dag_id,
        task_id=task_id,
        run_id=run_id,
        symbol=symbol,
        check_name=check_name,
        passed=passed,
        severity=severity,
        details=details or {},
        context=context or {},
        trace_id=trace_id,
    )


def _insert_validation_event(**row: Any) -> bool:
    conn = _get_conn()
    if conn is None:
        _logger.debug("log_validation_event skipped (no DB).")
        return False

    sql = """
    INSERT INTO validation_events
      (ts, dag_id, task_id, run_id, symbol, check_name, passed, severity, details, context, trace_id)
    VALUES
      (%s,  %s,     %s,      %s,     %s,     %s,         %s,     %s,       %s::jsonb, %s::jsonb, %s)
    """
    params = (
        row["ts"],
        row["dag_id"],
        row["task_id"],
        row["run_id"],
        row["symbol"],
        row["check_name"],
        row["passed"],
        row["severity"],
        json.dumps(row.get("details", {}), ensure_ascii=False),
        json.dumps(row.get("context", {}), ensure_ascii=False),
        row.get("trace_id"),
    )
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
        return True
    except Exception as e:
        _logger.warning("log_validation_event failed: %s", e)
        return False
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
    _insert_execution_event(
        ts=_utcnow(),
        dag_id=dag_id,
        task_id=task_id,
        run_id=run_id,
        symbol=symbol,
        action=action,
        qty=float(qty),
        price=float(price),
        status=status,
        broker_order_id=broker_order_id,
        latency_ms=latency_ms,
        error=error,
        extras=extras or {},
        trace_id=trace_id,
    )


def _insert_execution_event(**row: Any) -> bool:
    conn = _get_conn()
    if conn is None:
        _logger.debug("log_execution_event skipped (no DB).")
        return False

    sql = """
    INSERT INTO execution_events
      (ts, dag_id, task_id, run_id, symbol, action, qty, price, status,
       broker_order_id, latency_ms, error, extras, trace_id)
    VALUES
      (%s, %s, %s, %s, %s, %s, %s, %s, %s,
       %s, %s, %s, %s::jsonb, %s)
    """
    params = (
        row["ts"],
        row["dag_id"],
        row["task_id"],
        row["run_id"],
        row["symbol"],
        row["action"],
        float(row["qty"]),
        float(row["price"]),
        row["status"],
        row.get("broker_order_id"),
        row.get("latency_ms"),
        row.get("error"),
        json.dumps(row.get("extras", {}), ensure_ascii=False),
        row.get("trace_id"),
    )
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
        return True
    except Exception as e:
        _logger.warning("log_execution_event failed: %s", e)
        return False
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
    _insert_metric(
        ts=ts or _utcnow(),
        metric_name=metric_name,
        value=float(value),
        tags=tags or {},
        trace_id=trace_id,
    )


def _insert_metric(**row: Any) -> bool:
    conn = _get_conn()
    if conn is None:
        _logger.debug("log_metric skipped (no DB).")
        return False

    sql = """
    INSERT INTO perf_timeseries (ts, metric_name, value, tags, trace_id)
    VALUES (%s, %s, %s, %s::jsonb, %s)
    """
    params = (
        row["ts"],
        row["metric_name"],
        float(row["value"]),
        json.dumps(row.get("tags", {}), ensure_ascii=False),
        row.get("trace_id"),
    )
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
        return True
    except Exception as e:
        _logger.warning("log_metric failed: %s", e)
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass


# -------------------------------------------------------------------
# Optional: 最小スキーマの自動作成
# -------------------------------------------------------------------
_OBS_SCHEMA_DDL = [
    """
    CREATE TABLE IF NOT EXISTS validation_events(
        id BIGSERIAL PRIMARY KEY,
        ts timestamptz NOT NULL DEFAULT now(),
        dag_id text, task_id text, run_id text,
        symbol text, check_name text, passed boolean,
        severity text, details jsonb, context jsonb, trace_id text
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS execution_events(
        id BIGSERIAL PRIMARY KEY,
        ts timestamptz NOT NULL DEFAULT now(),
        dag_id text, task_id text, run_id text,
        symbol text, action text, qty double precision, price double precision,
        status text, broker_order_id text, latency_ms integer,
        error text, extras jsonb, trace_id text
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS perf_timeseries(
        id BIGSERIAL PRIMARY KEY,
        ts timestamptz NOT NULL,
        metric_name text NOT NULL,
        value double precision,
        tags jsonb,
        trace_id text
    )
    """,
]


def ensure_observability_tables() -> bool:
    """
    観測テーブル（validation_events / execution_events / perf_timeseries）を作成。
    - 既にあれば NO-OP
    - DB未設定なら False を返すだけ（例外なし）
    """
    conn = _get_conn()
    if conn is None:
        _logger.debug("ensure_observability_tables skipped (no DB).")
        return False

    try:
        with conn:
            with conn.cursor() as cur:
                for ddl in _OBS_SCHEMA_DDL:
                    cur.execute(ddl)
        return True
    except Exception as e:
        _logger.warning("ensure_observability_tables failed: %s", e)
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass
