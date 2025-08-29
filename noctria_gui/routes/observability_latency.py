# noctria_gui/routes/observability_latency.py
from __future__ import annotations

import os
import json
from datetime import datetime
from typing import Any, Dict, List, Tuple

import psycopg2
import psycopg2.extras
from flask import Blueprint, render_template, request, abort

obs_bp = Blueprint("observability_latency", __name__, template_folder="../templates")

# DSN は既存の観測用 ENV を尊重（なければローカル既定）
OBS_DSN = os.getenv("NOCTRIA_OBS_PG_DSN", "postgresql://airflow:airflow@localhost:5432/airflow")


def _query(sql: str, params: Tuple[Any, ...] | None = None) -> List[Dict[str, Any]]:
    conn = psycopg2.connect(OBS_DSN)
    try:
        with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    finally:
        conn.close()


@obs_bp.route("/observability/latency")
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

    # 2) 最近のトレース10件（サマリ）
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
                infer = {
                    "at": ev["at"],
                    "name": ev["name"],
                    "dur_ms": _safe_int((ev["detail"] or {}).get("dur_ms")),
                    "success": bool((ev["detail"] or {}).get("success", False)),
                }
            if ev["stage"] == "DECISION" and decision is None:
                decision = {
                    "at": ev["at"],
                    "strategy_name": ev["name"],
                    "score": _safe_float((ev["detail"] or {}).get("score")),
                    "reason": (ev["detail"] or {}).get("reason"),
                    "action": (ev["detail"] or {}).get("action"),
                    "params": (ev["detail"] or {}).get("params"),
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
