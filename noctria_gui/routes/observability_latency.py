# noctria_gui/routes/observability_latency.py
# -*- coding: utf-8 -*-
"""
📈 Observability: Latency Dashboard (FastAPI)
- 画面: GET /observability/latency
    日次レイテンシ分布（p50/p90/p99）＋最近トレース一覧
    ?trace_id=... を付けると該当トレースのタイムライン詳細を表示

データ前提:
  - obs_trace_timeline は VIEW（列: trace_id, ts, kind, action, payload(jsonb)）
    ※ 例: obs_decisions / obs_infer_calls などの UNION ALL
  - obs_latency_daily は MATERIALIZED VIEW（列: day, events, p50_ms, p90_ms, p99_ms）

DSN:
  - 環境変数 NOCTRIA_OBS_PG_DSN を優先
  - 未設定時はローカルDB既定: postgresql://noctria:noctria@localhost:5432/noctria_db
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

# ---------------------------------------------------------------------------
# DSN: 観測用 ENV を尊重（未設定ならローカル既定）
# ---------------------------------------------------------------------------
OBS_DSN = os.getenv(
    "NOCTRIA_OBS_PG_DSN",
    "postgresql://noctria:noctria@localhost:5432/noctria_db",
)

# ---------------------------------------------------------------------------
# Templates: noctria_gui/templates を解決
#   ※ main.py でも Jinja2 を作っていますが、本ルーター単体でも動くように
#     念のためここでも解決しておく（重複しても問題なし）
# ---------------------------------------------------------------------------
TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/observability", tags=["observability"])


# ---------------------------------------------------------------------------
# Helper: クイック読み出し（例外時は空配列を返す）
# ---------------------------------------------------------------------------
def _query(sql: str, params: Tuple[Any, ...] | None = None) -> List[Dict[str, Any]]:
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


# ---------------------------------------------------------------------------
# Route: /observability/latency (HTML)
#   ※ エンドポイント名は関数名 'latency_dashboard' になる
# ---------------------------------------------------------------------------
@router.get("/latency", response_class=HTMLResponse)
def latency_dashboard(request: Request):
    """
    日次レイテンシ分布（p50/p90/p99）＋最近トレース一覧。
    ?trace_id=... で該当トレースのタイムライン詳細も表示。
    """

    # 1) 日次レイテンシ分布（物理化ビュー）
    daily = _query(
        """
        SELECT day::date AS day, events, p50_ms, p90_ms, p99_ms
        FROM public.obs_latency_daily
        ORDER BY day ASC
        """
    )

    # 2) 最近のトレース20件（VIEW: obs_trace_timeline の列に合わせる）
    recent = _query(
        """
        SELECT trace_id,
               MIN(ts) AS started_at,
               MAX(ts) AS finished_at,
               COUNT(*) AS events
        FROM public.obs_trace_timeline
        GROUP BY trace_id
        ORDER BY MAX(ts) DESC
        LIMIT 20
        """
    )

    # 3) 任意 trace_id のタイムライン詳細（列をアプリ期待名にエイリアス）
    trace_id = request.query_params.get("trace_id")
    timeline: List[Dict[str, Any]] = []
    decision: Dict[str, Any] | None = None
    infer: Dict[str, Any] | None = None

    if trace_id:
        timeline = _query(
            """
            SELECT
              ts      AS at,
              kind    AS stage,
              action  AS name,
              payload AS detail
            FROM public.obs_trace_timeline
            WHERE trace_id = %s
            ORDER BY ts ASC
            """,
            (trace_id,),
        )
        # INFER / DECISION の1件目を拾って上段に要約表示
        for ev in timeline:
            stage = ev.get("stage")
            if stage == "INFER" and infer is None:
                det = ev.get("detail") or {}
                # duration_ms / dur_ms の両対応
                dur = det.get("duration_ms")
                if dur is None:
                    dur = det.get("dur_ms")
                infer = {
                    "at": ev.get("at"),
                    "name": ev.get("name"),
                    "dur_ms": _safe_int(dur),
                    "success": bool((det or {}).get("success", False)),
                }
            if stage == "DECISION" and decision is None:
                det = ev.get("detail") or {}
                decision = {
                    "at": ev.get("at"),
                    "strategy_name": ev.get("name"),
                    "score": _safe_float((det or {}).get("score")),
                    "reason": (det or {}).get("reason"),
                    "action": (det or {}).get("action"),
                    "params": (det or {}).get("params"),
                }

    # Chart.js に渡す軽量配列
    chart = {
        "labels": [str(r["day"]) for r in daily],
        "p50": [round(float(r["p50_ms"])) if r.get("p50_ms") is not None else None for r in daily],
        "p90": [round(float(r["p90_ms"])) if r.get("p90_ms") is not None else None for r in daily],
        "p99": [round(float(r["p99_ms"])) if r.get("p99_ms") is not None else None for r in daily],
        "events": [int(r["events"]) for r in daily] if daily else [],
    }

    # HTML レンダリング（テンプレートは obs_latency.html）
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


# 互換エクスポート（既存コードの参照名を生かす）
bp_obs_latency = router
obs_bp = router
__all__ = ["router", "bp_obs_latency", "obs_bp", "latency_dashboard"]
