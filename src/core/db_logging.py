# src/core/db_logging.py
# coding: utf-8
"""
C層共通ログ基盤: DB Logging ヘルパ
- validation_events / execution_events / perf_timeseries へ安全に INSERT するための共通I/F
- Airflowタスク / 臣下AI(Hermes/Veritas) / GUI バックエンドから共用

環境変数（docker-compose 既定値をデフォルト化）
- POSTGRES_DB      (default: airflow)
- POSTGRES_USER    (default: airflow)
- POSTGRES_PASSWORD(default: airflow)
- POSTGRES_HOST    (default: noctria_postgres)
- POSTGRES_PORT    (default: 5432)
"""

from __future__ import annotations

import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, Iterable

import psycopg2
import psycopg2.extras

# --- ロガー -------------------------------------------------
try:
    # 既存プロジェクトのロガーがあれば優先
    from src.core.logger import setup_logger  # type: ignore
except Exception:
    # フォールバック（utilsにある簡易版）
    from src.core.utils import setup_logger  # type: ignore

logger = setup_logger("db_logging")


# --- 接続 ---------------------------------------------------
def get_conn():
    """
    毎回新規コネクションを返す（Airflow等でのリーク防止）
    呼び出し側で commit/close は不要（本モジュールの挿入系が責任を持つ）
    """
    conn = psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "airflow"),
        user=os.getenv("POSTGRES_USER", "airflow"),
        password=os.getenv("POSTGRES_PASSWORD", "airflow"),
        host=os.getenv("POSTGRES_HOST", "noctria_postgres"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
    )
    return conn


# --- テーブルごとの許可カラム（ホワイトリスト） ------------
def _allowed_columns(table: str) -> Optional[Iterable[str]]:
    """
    スキーマ更新時はここを追従
    """
    if table == "validation_events":
        return {
            "created_at", "dag_id", "task_id", "run_id", "symbol",
            "check_name", "passed", "severity", "details", "context"
        }
    if table == "execution_events":
        return {
            "created_at", "dag_id", "task_id", "run_id", "symbol",
            "action", "qty", "price", "status", "broker_order_id",
            "latency_ms", "error", "extras"
        }
    if table == "perf_timeseries":
        # 想定スキーマ: id, ts timestamptz default now(), dag_id, task_id, run_id, metric_name, value, tags jsonb
        return {
            "ts", "dag_id", "task_id", "run_id",
            "metric_name", "value", "tags"
        }
    return None


# --- 汎用 INSERT（dict -> 列動的生成） ----------------------
def _insert_row(table: str, row: Dict[str, Any]) -> None:
    """
    dict のキーだけを列として動的 INSERT
    - JSONB は psycopg2.extras.Json で包む
    - 許可されていない列は警告のうえ無視
    """
    allowed = _allowed_columns(table)
    if allowed is None:
        raise ValueError(f"Unknown or unsupported table: {table}")

    columns: list[str] = []
    values: list[Any] = []
    for k, v in row.items():
        if k not in allowed:
            logger.warning(f"[db_logging] Skip unknown column '{k}' for table '{table}'")
            continue
        if isinstance(v, (dict, list)):
            v = psycopg2.extras.Json(v, dumps=lambda o: json.dumps(o, ensure_ascii=False))
        columns.append(k)
        values.append(v)

    if not columns:
        logger.warning(f"[db_logging] No valid columns to insert for table '{table}'")
        return

    placeholders = ", ".join(["%s"] * len(columns))
    colnames = ", ".join(columns)
    sql = f"INSERT INTO {table} ({colnames}) VALUES ({placeholders})"

    conn = None
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute(sql, values)
        conn.commit()
    except Exception as e:
        logger.error(f"[db_logging] INSERT failed into '{table}': {e}\nrow={row}", exc_info=True)
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


# --- 用途別の糖衣関数 --------------------------------------
def log_validation_event(
    *,
    check_name: str,
    passed: bool,
    severity: str = "INFO",            # "INFO" | "WARN" | "ERROR" | "BLOCK"
    symbol: Optional[str] = None,
    dag_id: Optional[str] = None,
    task_id: Optional[str] = None,
    run_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    created_at: Optional[datetime] = None,
) -> None:
    """
    validation_events へ挿入
    """
    row = {
        "created_at": created_at or None,  # None の場合は DB DEFAULT(now) を使うため省略
        "dag_id": dag_id,
        "task_id": task_id,
        "run_id": run_id,
        "symbol": symbol,
        "check_name": check_name,
        "passed": passed,
        "severity": severity,
        "details": details or {},
        "context": context or {},
    }
    row = {k: v for k, v in row.items() if v is not None}
    _insert_row("validation_events", row)


def log_execution_event(
    *,
    action: str,                         # "BUY" | "SELL" | "HOLD" | "CANCEL" …
    status: str,                         # "SENT" | "REJECTED" | "FILLED" | …
    symbol: Optional[str] = None,
    qty: Optional[float] = None,
    price: Optional[float] = None,
    broker_order_id: Optional[str] = None,
    latency_ms: Optional[int] = None,
    error: Optional[str] = None,
    extras: Optional[Dict[str, Any]] = None,
    dag_id: Optional[str] = None,
    task_id: Optional[str] = None,
    run_id: Optional[str] = None,
    created_at: Optional[datetime] = None,
) -> None:
    """
    execution_events へ挿入
    """
    row = {
        "created_at": created_at or None,
        "dag_id": dag_id,
        "task_id": task_id,
        "run_id": run_id,
        "symbol": symbol,
        "action": action,
        "qty": qty,
        "price": price,
        "status": status,
        "broker_order_id": broker_order_id,
        "latency_ms": latency_ms,
        "error": error,
        "extras": extras or {},
    }
    row = {k: v for k, v in row.items() if v is not None}
    _insert_row("execution_events", row)


def log_perf_metric(
    *,
    metric_name: str,
    value: float,
    tags: Optional[Dict[str, Any]] = None,
    dag_id: Optional[str] = None,
    task_id: Optional[str] = None,
    run_id: Optional[str] = None,
    ts: Optional[datetime] = None,
) -> None:
    """
    perf_timeseries へ挿入
    """
    row = {
        "ts": ts or None,        # None の場合は DB DEFAULT(now) を利用
        "dag_id": dag_id,
        "task_id": task_id,
        "run_id": run_id,
        "metric_name": metric_name,
        "value": value,
        "tags": tags or {},
    }
    row = {k: v for k, v in row.items() if v is not None}
    _insert_row("perf_timeseries", row)


# --- 旧API互換（最小限） -----------------------------------
def log_event(
    table: str,
    event_type: str,
    payload: Dict[str, Any],
    occurred_at: Optional[datetime] = None
):
    """
    互換レイヤ（古い呼び出しを受け止める）
    - validation_events: event_type -> check_name, payload -> details
    - execution_events : event_type -> status (非推奨), payload -> extras
    - perf_timeseries  : event_type -> metric_name, payload{'value': ...} 必須
    """
    if table == "validation_events":
        log_validation_event(
            check_name=event_type,
            passed=bool(payload.get("passed", True)),
            severity=str(payload.get("severity", "INFO")),
            symbol=payload.get("symbol"),
            dag_id=payload.get("dag_id"),
            task_id=payload.get("task_id"),
            run_id=payload.get("run_id"),
            details=payload,
            context=payload.get("context"),
            created_at=occurred_at,
        )
        return

    if table == "execution_events":
        log_execution_event(
            action=str(payload.get("action", "HOLD")),
            status=event_type,  # 旧I/Fの event_type を status に割当（推奨は明示指定）
            symbol=payload.get("symbol"),
            qty=payload.get("qty"),
            price=payload.get("price"),
            broker_order_id=payload.get("broker_order_id"),
            latency_ms=payload.get("latency_ms"),
            error=payload.get("error"),
            extras=payload,
            dag_id=payload.get("dag_id"),
            task_id=payload.get("task_id"),
            run_id=payload.get("run_id"),
            created_at=occurred_at,
        )
        return

    if table == "perf_timeseries":
        metric_name = event_type
        value = payload.get("value")
        if value is None:
            logger.error("[db_logging] perf_timeseries 互換呼び出しは payload['value'] が必須です。")
            return
        log_perf_metric(
            metric_name=metric_name,
            value=float(value),
            tags=payload.get("tags"),
            dag_id=payload.get("dag_id"),
            task_id=payload.get("task_id"),
            run_id=payload.get("run_id"),
            ts=occurred_at,
        )
        return

    raise ValueError(f"Unsupported table for legacy log_event: {table}")


# --- Airflow から使うときの便利ラッパ ----------------------
def airflow_ids_from_context(kwargs: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """
    Airflow の task callable で **kwargs から dag/task/run のIDを安全に抜き出す
    """
    dag_id = None
    task_id = None
    run_id = None
    try:
        dag = kwargs.get("dag")
        task = kwargs.get("task")
        dag_run = kwargs.get("dag_run")
        dag_id = getattr(dag, "dag_id", None)
        task_id = getattr(task, "task_id", None)
        run_id = getattr(dag_run, "run_id", None)
    except Exception:
        pass
    return {"dag_id": dag_id, "task_id": task_id, "run_id": run_id}
