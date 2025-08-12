from typing import Optional, Dict, Any
import json, psycopg2
from datetime import datetime, timezone

def _utcnow():
    return datetime.now(timezone.utc)

def log_plan_run(conn_str: str, phase: str, rows: int, dur_sec: int,
                 missing_ratio: float, error_rate: float, trace_id: Optional[str] = None):
    sql = """
    INSERT INTO obs_plan_runs (ts, phase, dur_sec, rows, missing_ratio, error_rate, trace_id)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    with psycopg2.connect(conn_str) as conn, conn.cursor() as cur:
        cur.execute(sql, (_utcnow(), phase, dur_sec, rows, missing_ratio, error_rate, trace_id))

def log_infer_call(conn_str: str, model: str, ver: str,
                   dur_ms: int, success: bool, feature_staleness_min: int,
                   trace_id: Optional[str] = None):
    sql = """
    INSERT INTO obs_infer_calls (ts, model, ver, dur_ms, success, feature_staleness_min, trace_id)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    with psycopg2.connect(conn_str) as conn, conn.cursor() as cur:
        cur.execute(sql, (_utcnow(), model, ver, dur_ms, success, feature_staleness_min, trace_id))
