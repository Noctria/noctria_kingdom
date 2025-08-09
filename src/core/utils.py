# src/core/utils.py
import logging
import os
import json
import psycopg2
from typing import Optional, Dict, Any

def setup_logger(name: str, level=logging.INFO):
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger

# --- Postgres 接続共通 ---
def _conn():
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "airflow"),
        user=os.getenv("POSTGRES_USER", "airflow"),
        password=os.getenv("POSTGRES_PASSWORD", "airflow"),
        host=os.getenv("POSTGRES_HOST", "noctria_postgres"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
    )

# --- Validation Events ログ書き込み ---
def log_validation_event(
    dag_id: str, task_id: str, run_id: str,
    symbol: str, check_name: str, passed: bool,
    severity: str = "INFO",
    details: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
):
    sql = """
    INSERT INTO validation_events
    (dag_id, task_id, run_id, symbol, check_name, passed, severity, details, context)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)
    """
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (
                dag_id, task_id, run_id, symbol, check_name, passed, severity,
                json.dumps(details or {}), json.dumps(context or {})
            ))

# --- Execution Events ログ書き込み ---
def log_execution_event(
    dag_id: str, task_id: str, run_id: str,
    symbol: str, action: str, qty: float, price: float,
    status: str, broker_order_id: str = None,
    latency_ms: Optional[int] = None,
    error: Optional[str] = None,
    extras: Optional[Dict[str, Any]] = None,
):
    sql = """
    INSERT INTO execution_events
    (dag_id, task_id, run_id, symbol, action, qty, price, status, broker_order_id, latency_ms, error, extras)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
    """
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (
                dag_id, task_id, run_id, symbol, action, qty, price, status,
                broker_order_id, latency_ms, error, json.dumps(extras or {})
            ))

# --- Perf Timeseries ログ書き込み ---
def log_metric(ts, metric_name: str, value: float, tags: Optional[Dict[str, Any]] = None):
    sql = "INSERT INTO perf_timeseries (ts, metric_name, value, tags) VALUES (%s,%s,%s,%s::jsonb)"
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (ts, metric_name, value, json.dumps(tags or {})))
