# noctria_gui/routes/observability_latency.py
# -*- coding: utf-8 -*-
"""
📈 Observability: Latency Dashboard (FastAPI版)
- GET /observability/latency
    日次レイテンシ分布（p50/p90/p99）＋最近トレース一覧、?trace_id=... で詳細
- DSN は NOCTRIA_OBS_PG_DSN を優先（未設定はローカルDBにフォールバック）

期待テーブル:
  - obs_latency_daily(day::date, events::int, p50_ms::numeric, p90_ms::numeric, p99_ms::numeric)
  - obs_trace_timeline(trace_id::text, at::timestamptz, stage::text, name::text, detail::jsonb)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from starlette.templating import Jinja2Templates

# ── DSN: 観測用 ENV を尊重（未設定ならローカル既定）
OBS_DSN = os.getenv(
    "NOCTRIA_OBS_PG_DSN",
    "postgresql://noctria:noctria@localhost:5432/noctria_db",
)

# ── Templates（noctria_gui/templates を解決）
TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ✅ FastAPI ルーター（/observability 配下）
router = APIRouter(prefix="/observability", tags=["observability"])

# ---- DB helper ---------------------------------------------------------------

def _query(sql: str, params: Tuple[Any, ...] | None = None) -> List[Dict[str, Any]]:
    """
    クイック読み出し。接続/カーソルは都度開閉。
    例外時は空配列を返す（画面は表示継続）。
    """
    try:
        conn = psycopg2.connect(OBS_DSN)
    except Exception:
        return []
    try:
        with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            rows = cur.fetchall()
            return [dict(r) for r in rows]
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

# ---- Routes ------------------------------------------------------------------

@router.get(
    "/latency",
    response_class=HTMLResponse,
    name="observability_latency.latency_dashboard",  # ← 重要: テンプレの url_for と一致
)
def latency_dashboard(request: Request):
    """
    日次レイテンシ分布（p50/p90/p99）と、最近トレース一覧。
    ?trace_id=... を付けると該当トレースのタイムライン詳細も表示。
    """
    # 1) 日次レイテンシ分布（マテビュー or 集計テーブル想定）
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
            "chart_json": json.dumps(chart),
            "recent": recent,
            "trace_id": trace_id,
            "timeline": timeline,
            "infer": infer,
            "decision": decision,
        },
    )

# 互換エクスポート（旧コードの参照名を生かす）
bp_obs_latency = router
obs_bp = router
__all__ = ["router", "bp_obs_latency", "obs_bp"]
