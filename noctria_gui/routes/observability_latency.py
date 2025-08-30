# noctria_gui/routes/observability_latency.py
# -*- coding: utf-8 -*-
"""
📈 Observability: Latency Dashboard (FastAPI)
Routes:
- GET  /observability/latency                 : HUDページ (obs_latency.html)
- GET  /observability/api/daily?limit=60      : 日次 p50/p90/p99 の配列
- GET  /observability/api/daily.csv?limit=60  : 同CSV
- GET  /observability/summary?limit=10        : 直近トレースのサマリ

期待スキーマ:
  - obs_latency_daily(day::date, events::int, p50_ms::numeric, p90_ms::numeric, p99_ms::numeric)
  - obs_trace_timeline(trace_id::text, at::timestamptz, stage::text, name::text, detail::jsonb)
"""

from __future__ import annotations

import csv
import io
import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Tuple

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from starlette.templating import Jinja2Templates

# ── DSN: 観測用 ENV を尊重（未設定ならローカル既定）
OBS_DSN = os.getenv("NOCTRIA_OBS_PG_DSN", "postgresql://noctria:noctria@localhost:5432/noctria_db")

# ── Templates（noctria_gui/templates を解決）
TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ✅ FastAPI ルーター（/observability 配下）
router = APIRouter(prefix="/observability", tags=["observability"])

# ---- DB helpers --------------------------------------------------------------

def _query(sql: str, params: Tuple[Any, ...] | None = None) -> List[Dict[str, Any]]:
    """クイック読み出し。例外時は空配列を返す（ページは表示継続）。"""
    try:
        conn = psycopg2.connect(OBS_DSN)
    except Exception:
        return []
    try:
        with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            rows = cur.fetchall()
            # Decimal → float に変換（JSON化のため）
            normed: List[Dict[str, Any]] = []
            for r in rows:
                d = dict(r)
                for k, v in list(d.items()):
                    if isinstance(v, Decimal):
                        d[k] = float(v)
                normed.append(d)
            return normed
    except Exception:
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass

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

# ---- Pages -------------------------------------------------------------------

@router.get(
    "/latency",
    response_class=HTMLResponse,
    name="observability_latency.latency_dashboard",  # テンプレの url_for と一致
)
def latency_dashboard(request: Request):
    """
    HUDページ:
      - 上段: 日次パーセンタイル折れ線 (p50/p90/p99)
      - 左: 最近のトレース
      - 右: 選択トレース詳細（?trace_id=...）
    """
    # 1) 日次レイテンシ
    daily = _query(
        """
        SELECT day::date AS day, events, p50_ms, p90_ms, p99_ms
        FROM obs_latency_daily
        ORDER BY day ASC
        """
    )

    # 2) 最近のトレース（20件）
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

    # 3) 任意 trace_id のタイムライン詳細
    trace_id = request.query_params.get("trace_id")
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
        for ev in timeline:
            if (ev.get("stage") == "INFER") and (infer is None):
                det = (ev.get("detail") or {}) if isinstance(ev.get("detail"), dict) else {}
                infer = {
                    "at": ev.get("at"),
                    "name": ev.get("name"),
                    "dur_ms": _safe_int(det.get("dur_ms")),
                    "success": bool(det.get("success", False)),
                }
            if (ev.get("stage") == "DECISION") and (decision is None):
                det = (ev.get("detail") or {}) if isinstance(ev.get("detail"), dict) else {}
                decision = {
                    "at": ev.get("at"),
                    "strategy_name": ev.get("name"),
                    "score": _safe_float(det.get("score")),
                    "reason": det.get("reason"),
                    "action": det.get("action"),
                    "params": det.get("params"),
                }

    # Chart.js に渡す軽量配列
    chart = {
        "labels": [str(r["day"]) for r in daily],
        "p50": [round(float(r["p50_ms"])) if r.get("p50_ms") is not None else None for r in daily],
        "p90": [round(float(r["p90_ms"])) if r.get("p90_ms") is not None else None for r in daily],
        "p99": [round(float(r["p99_ms"])) if r.get("p99_ms") is not None else None for r in daily],
        "events": [int(r["events"]) for r in daily] if daily else [],
    }

    return templates.TemplateResponse(
        "obs_latency.html",
        {
            "request": request,
            "page_title": "⏱️ Observability / Latency",
            "chart_json": json.dumps(chart, ensure_ascii=False),
            "recent": recent,
            "trace_id": trace_id,
            "timeline": timeline,
            "infer": infer,
            "decision": decision,
        },
    )

# ---- APIs --------------------------------------------------------------------

@router.get("/api/daily")
def api_daily(limit: int = Query(60, ge=1, le=365)):
    """日次 p50/p90/p99 を新しい順で limit 件。"""
    rows = _query(
        """
        SELECT day::date AS day, events, p50_ms, p90_ms, p99_ms
        FROM obs_latency_daily
        ORDER BY day DESC
        LIMIT %s
        """,
        (limit,),
    )
    return JSONResponse({"items": rows})

@router.get("/api/daily.csv", response_class=PlainTextResponse)
def api_daily_csv(limit: int = Query(60, ge=1, le=365)):
    """CSVエクスポート（Excel/外部共有用）。"""
    rows = _query(
        """
        SELECT day::date AS day, events, p50_ms, p90_ms, p99_ms
        FROM obs_latency_daily
        ORDER BY day DESC
        LIMIT %s
        """,
        (limit,),
    )
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["day", "events", "p50_ms", "p90_ms", "p99_ms"])
    for r in rows:
        w.writerow([
            r.get("day"),
            r.get("events"),
            r.get("p50_ms"),
            r.get("p90_ms"),
            r.get("p99_ms"),
        ])
    return PlainTextResponse(buf.getvalue(), media_type="text/csv; charset=utf-8")

@router.get("/summary")
def api_summary(limit: int = Query(10, ge=1, le=200)):
    """
    直近トレースのサマリ。
    - total_ms: detail.dur_ms の合計を近似（無い場合は 0）
    - infer_ms: stage='INFER' の dur_ms 合計
    - strategy_name / action: 最後の DECISION から拾う
    - infer_to_decision_ms: window長(ms)を近似（started→finished）
    """
    rows = _query(
        """
        WITH base AS (
          SELECT trace_id,
                 MIN(at) AS started_at,
                 MAX(at) AS finished_at,
                 COUNT(*) AS events,
                 SUM( (CASE WHEN (detail->>'dur_ms') ~ '^[0-9]+(\\.[0-9]+)?$' THEN (detail->>'dur_ms')::numeric ELSE 0 END) )
                    AS total_ms,
                 SUM( (CASE WHEN stage='INFER' AND (detail->>'dur_ms') ~ '^[0-9]+(\\.[0-9]+)?$'
                            THEN (detail->>'dur_ms')::numeric ELSE 0 END) )
                    AS infer_ms,
                 MAX( CASE WHEN stage='DECISION' THEN (detail->>'strategy_name') END ) AS strategy_name,
                 MAX( CASE WHEN stage='DECISION' THEN (detail->>'action') END ) AS action
          FROM obs_trace_timeline
          GROUP BY trace_id
          ORDER BY MAX(at) DESC
          LIMIT %s
        )
        SELECT *,
               EXTRACT(EPOCH FROM (finished_at - started_at))*1000 AS infer_to_decision_ms
        FROM base
        ORDER BY finished_at DESC
        """,
        (limit,),
    )
    return JSONResponse({"items": rows})

# 互換エクスポート（旧コードの参照名を生かす）
bp_obs_latency = router
obs_bp = router
__all__ = ["router", "bp_obs_latency", "obs_bp"]
