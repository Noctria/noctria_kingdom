# noctria_gui/routes/observability_latency.py
# -*- coding: utf-8 -*-
"""
📈 Observability: Latency Dashboard (FastAPI)
- 画面: GET /observability/latency
    日次レイテンシ分布（p50/p90/p99）＋最近トレース一覧
    ?trace_id=... で該当トレースのタイムライン詳細を表示

データ前提:
  - obs_trace_timeline は VIEW
    パターンA: (trace_id, ts,   kind,   action,  payload jsonb)
    パターンB: (trace_id, at,   stage,  name,    detail  jsonb)
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
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.templating import Jinja2Templates

# ---------------------------------------------------------------------------
# DSN
# ---------------------------------------------------------------------------
OBS_DSN = os.getenv(
    "NOCTRIA_OBS_PG_DSN",
    "postgresql://noctria:noctria@localhost:5432/noctria_db",
)

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/observability", tags=["observability"])


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def _query(sql: str, params: Tuple[Any, ...] | None = None) -> List[Dict[str, Any]]:
    """簡易 SELECT。失敗時は空配列で返す。"""
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


def _scalar(sql: str, params: Tuple[Any, ...] | None = None) -> Any:
    """1セル取得（失敗時は None）"""
    try:
        conn = psycopg2.connect(OBS_DSN)
    except Exception:
        return None
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql, params or ())
            r = cur.fetchone()
            return None if r is None else r[0]
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _has_column(schema: str, table: str, column: str) -> bool:
    """テーブル/ビューにカラムが存在するか"""
    q = """
    SELECT 1
      FROM information_schema.columns
     WHERE table_schema=%s AND table_name=%s AND column_name=%s
    """
    return _scalar(q, (schema, table, column)) == 1


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
# Route: Debug (現在の DSN と件数/最新時刻を確認)
# ---------------------------------------------------------------------------
@router.get("/latency/_debug", response_class=JSONResponse)
def latency_debug():
    # obs_trace_timeline のカラム名を推定
    has_ts = _has_column("public", "obs_trace_timeline", "ts")
    has_at = _has_column("public", "obs_trace_timeline", "at")
    time_col = "ts" if has_ts else ("at" if has_at else None)

    count_daily = _scalar("SELECT COUNT(*) FROM public.obs_latency_daily") or 0
    count_tl = _scalar("SELECT COUNT(*) FROM public.obs_trace_timeline") or 0
    latest_ts = None
    if time_col:
        latest_ts = _scalar(f"SELECT MAX({time_col}) FROM public.obs_trace_timeline")

    return {
        "dsn": OBS_DSN if OBS_DSN else None,
        "obs_latency_daily.count": count_daily,
        "obs_trace_timeline.count": count_tl,
        "obs_trace_timeline.latest_ts": str(latest_ts) if latest_ts else None,
        "timeline_time_col": time_col,
    }


# ---------------------------------------------------------------------------
# Route: /observability/latency (HTML)
# ---------------------------------------------------------------------------
@router.get("/latency", response_class=HTMLResponse)
def latency_dashboard(request: Request):
    """
    日次レイテンシ分布（p50/p90/p99）＋最近トレース一覧。
    ?trace_id=... で該当トレースのタイムライン詳細も表示。
    """

    # obs_trace_timeline のカラム差異を環境に応じて吸収
    has_ts = _has_column("public", "obs_trace_timeline", "ts")
    has_at = _has_column("public", "obs_trace_timeline", "at")
    has_kind = _has_column("public", "obs_trace_timeline", "kind")
    has_stage = _has_column("public", "obs_trace_timeline", "stage")
    has_action = _has_column("public", "obs_trace_timeline", "action")
    has_name = _has_column("public", "obs_trace_timeline", "name")
    has_payload = _has_column("public", "obs_trace_timeline", "payload")
    has_detail = _has_column("public", "obs_trace_timeline", "detail")

    # 存在する方を採用（無ければ None）
    time_col = "ts" if has_ts else ("at" if has_at else None)
    stage_col = "kind" if has_kind else ("stage" if has_stage else None)
    name_col = "action" if has_action else ("name" if has_name else None)
    detail_col = "payload" if has_payload else ("detail" if has_detail else None)

    # 1) 日次レイテンシ分布
    daily = _query(
        """
        SELECT day::date AS day, events, p50_ms, p90_ms, p99_ms
        FROM public.obs_latency_daily
        ORDER BY day ASC
        """
    )

    # 2) 最近のトレース20件
    recent: List[Dict[str, Any]] = []
    if time_col:
        recent = _query(
            f"""
            SELECT trace_id,
                   MIN({time_col}) AS started_at,
                   MAX({time_col}) AS finished_at,
                   COUNT(*) AS events
            FROM public.obs_trace_timeline
            GROUP BY trace_id
            ORDER BY MAX({time_col}) DESC
            LIMIT 20
            """
        )

    # 3) 任意 trace_id のタイムライン詳細
    trace_id = request.query_params.get("trace_id")
    timeline: List[Dict[str, Any]] = []
    decision: Dict[str, Any] | None = None
    infer: Dict[str, Any] | None = None

    if trace_id and time_col:
        # 存在するカラム名で投影
        select_time = f"{time_col} AS at" if time_col else "NULL::timestamptz AS at"
        select_stage = f"{stage_col} AS stage" if stage_col else "NULL::text AS stage"
        select_name = f"{name_col} AS name" if name_col else "NULL::text AS name"
        select_detail = f"{detail_col} AS detail" if detail_col else "'{}'::jsonb AS detail"

        timeline = _query(
            f"""
            SELECT
              {select_time},
              {select_stage},
              {select_name},
              {select_detail}
            FROM public.obs_trace_timeline
            WHERE trace_id = %s
            ORDER BY {time_col} ASC
            """,
            (trace_id,),
        )

        # INFER / DECISION の1件目を要約
        for ev in timeline:
            stg = ev.get("stage")
            det = ev.get("detail") or {}

            if stg == "INFER" and infer is None:
                dur = det.get("duration_ms", det.get("dur_ms"))
                infer = {
                    "at": ev.get("at"),
                    "name": ev.get("name"),
                    "dur_ms": _safe_int(dur),
                    "success": bool(det.get("success", False)),
                }

            if stg == "DECISION" and decision is None:
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


# 互換エクスポート
bp_obs_latency = router
obs_bp = router
__all__ = ["router", "bp_obs_latency", "obs_bp", "latency_dashboard"]
