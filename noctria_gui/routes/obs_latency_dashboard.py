# noctria_gui/routes/obs_latency_dashboard.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List

from flask import Blueprint, current_app, jsonify, render_template, request
from sqlalchemy import create_engine, text

bp_obs_latency = Blueprint("obs_latency", __name__, url_prefix="/observability")

# ---- DSN 解決 -------------------------------------------------
def _get_dsn() -> str:
    # 既存プロジェクトの DSN 優先順
    return (
        os.getenv("NOCTRIA_OBS_PG_DSN")
        or os.getenv("POSTGRES_DSN")
        or "postgresql://airflow:airflow@localhost:5432/airflow"
    )

def _engine():
    return create_engine(_get_dsn(), pool_pre_ping=True, future=True)

# ---- クエリ ---------------------------------------------------
Q_DAILY = """
SELECT
  day::date AS day,
  events,
  p50_ms::float8 AS p50_ms,
  p90_ms::float8 AS p90_ms,
  p99_ms::float8 AS p99_ms
FROM obs_latency_daily
ORDER BY day DESC
LIMIT :limit
"""

Q_TIMELINE = """
SELECT
  at,
  stage,
  name,
  detail
FROM obs_trace_timeline
WHERE trace_id = :trace_id
ORDER BY at
"""

Q_SUMMARY = """
SELECT
  trace_id, started_at, finished_at,
  ROUND(total_latency_ms)::int AS total_ms,
  infer_ms, strategy_name, action, params,
  infer_to_decision_ms, events
FROM obs_trace_summary
ORDER BY finished_at DESC
LIMIT :limit
"""

# ---- API: JSON ------------------------------------------------
@bp_obs_latency.get("/latency/data")
def latency_data():
    limit = int(request.args.get("limit", 30))
    with _engine().connect() as conn:
        rows = conn.execute(text(Q_DAILY), {"limit": limit}).mappings().all()
    data = [dict(r) for r in rows][::-1]  # 時系列昇順に並べ替え
    return jsonify({"ok": True, "items": data})

@bp_obs_latency.get("/trace/<trace_id>")
def trace_detail(trace_id: str):
    with _engine().connect() as conn:
        rows = conn.execute(text(Q_TIMELINE), {"trace_id": trace_id}).mappings().all()
    return jsonify({"ok": True, "trace_id": trace_id, "events": [dict(r) for r in rows]})

@bp_obs_latency.get("/summary")
def latency_summary():
    limit = int(request.args.get("limit", 50))
    with _engine().connect() as conn:
        rows = conn.execute(text(Q_SUMMARY), {"limit": limit}).mappings().all()
    return jsonify({"ok": True, "items": [dict(r) for r in rows]})

# ---- HTML: ダッシュボード ------------------------------------
@bp_obs_latency.get("/latency")
def latency_page():
    """
    /observability/latency
    Chart.js で p50/p90/p99 を可視化。裏側は /observability/latency/data をFetch。
    """
    return render_template("obs_latency_dashboard.html", api_url="/observability/latency/data")
