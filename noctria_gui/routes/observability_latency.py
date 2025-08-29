# noctria_gui/routes/observability_latency.py
from __future__ import annotations

import os
import json
from typing import Any, Dict, List, Tuple

import psycopg2
import psycopg2.extras
from flask import Blueprint, render_template, request

# ── DSN: 観測用 ENV を尊重（未設定ならローカル既定）
OBS_DSN = os.getenv("NOCTRIA_OBS_PG_DSN", "postgresql://airflow:airflow@localhost:5432/airflow")

# ✅ オートローダが拾いやすい命名（bp_で始まる）
bp_obs_latency = Blueprint(
    "obs_latency",
    __name__,
    url_prefix="/observability",
    template_folder="../templates",
)

def _query(sql: str, params: Tuple[Any, ...] | None = None) -> List[Dict[str, Any]]:
    conn = psycopg2.connect(OBS_DSN)
    try:
        with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    finally:
        conn.close()

@bp_obs_latency.get("/latency")
def latency_dashboard():
    """
    日次レイテンシ分布（p50/p90/p99）と、最近トレースの一覧・1トレース詳細を表示。
    - ?trace_id=... を付けるとそのトレースの時系列詳細を下部に表示
    """
    # 1) 日次レイテンシ分布（マテビュー）
    daily = _query(
        """
        SELECT day::date AS day, events, p50_ms, p90_ms, p99_ms
        FROM obs_latency_daily
        ORDER BY day ASC
        """
    )

    # 2) 最近のトレース20件（サマリ）
    recent = _query(
        """
        SELECT trace_id,
               MIN(at) AS started_at,
               MAX(at) AS finished_at,
               COUNT(*) AS events
        FROM obs_trace_timeline
        GROUP BY trace_id
        ORDER BY MAX(at) DESC
        LIMIT 20
        """
    )

    # 3) 任意の trace_id でタイムライン詳細を表示
    trace_id = request.args.get("trace_id")
    timeline: List[Dict[str, Any]] = []
    decision: Dict[str, Any] | None = None
    infer: Dict[str, Any] | None = None
    if trace_id:
        timeline = _query(
            """
            SELECT at, stage, name, detail
            FROM obs_trace_timeline
            WHERE trace_id = %s
            ORDER BY at ASC
            """,
            (trace_id,),
        )
        # INFER と DECISION を拾っておく（上段カード用）
        for ev in timeline:
            if ev["stage"] == "INFER" and infer is None:
                det = (ev.get("detail") or {})
                infer = {
                    "at": ev["at"],
                    "name": ev["name"],
                    "dur_ms": _safe_int(det.get("dur_ms")),
                    "success": bool(det.get("success", False)),
                }
            if ev["stage"] == "DECISION" and decision is None:
                det = (ev.get("detail") or {})
                decision = {
                    "at": ev["at"],
                    "strategy_name": ev["name"],
                    "score": _safe_float(det.get("score")),
                    "reason": det.get("reason"),
                    "action": det.get("action"),
                    "params": det.get("params"),
                }

    # Chart.js に渡す軽量配列
    chart = {
        "labels": [str(r["day"]) for r in daily],
        "p50": [round(float(r["p50_ms"])) if r["p50_ms"] is not None else None for r in daily],
        "p90": [round(float(r["p90_ms"])) if r["p90_ms"] is not None else None for r in daily],
        "p99": [round(float(r["p99_ms"])) if r["p99_ms"] is not None else None for r in daily],
        "events": [int(r["events"]) for r in daily],
    }

    return render_template(
        "obs_latency.html",
        chart_json=json.dumps(chart),
        recent=recent,
        trace_id=trace_id,
        timeline=timeline,
        infer=infer,
        decision=decision,
    )

def _safe_int(x: Any, default: int | None = None) -> int | None:
    try:
        return int(x) if x is not None else default
    except Exception:
        return default

def _safe_float(x: Any, default: float | None = None) -> float | None:
    try:
        return float(x) if x is not None else default
    except Exception:
        return default

# 🔁 互換エクスポート（既存コードで obs_bp を参照しても動くように）
obs_bp = bp_obs_latency
__all__ = ["bp_obs_latency", "obs_bp"]
