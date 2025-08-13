# noctria_gui/routes/observability.py
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Request, Query
from starlette.responses import HTMLResponse, JSONResponse
from starlette.templating import Jinja2Templates

# パス解決（テンプレ/ルートの場所を集中管理）
try:
    from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR  # running with `python -m`
except Exception:
    from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR      # running from repo root

# observability ユーティリティ（ビュー定義やMVのリフレッシュ呼び出し用）
try:
    from src.plan_data.observability import ensure_views, refresh_materialized  # type: ignore
except Exception:
    from plan_data.observability import ensure_views, refresh_materialized      # type: ignore

# --- DB 接続（psycopg2 → psycopg v3 フォールバック） ----------------------------
_DRIVER = None
_DB_KIND = None  # "psycopg2" | "psycopg"

def _get_dsn() -> str:
    dsn = os.getenv("NOCTRIA_OBS_PG_DSN")
    if not dsn:
        raise RuntimeError("NOCTRIA_OBS_PG_DSN is not set.")
    return dsn

def _import_driver():
    global _DRIVER, _DB_KIND
    if _DRIVER is not None:
        return _DRIVER, _DB_KIND
    try:
        import psycopg2 as drv  # type: ignore
        _DRIVER, _DB_KIND = drv, "psycopg2"
    except ModuleNotFoundError:
        import psycopg as drv   # type: ignore
        _DRIVER, _DB_KIND = drv, "psycopg"
    return _DRIVER, _DB_KIND

def _fetchall(sql: str, params: Tuple[Any, ...] = ()) -> List[Tuple]:
    drv, kind = _import_driver()
    dsn = _get_dsn()
    if kind == "psycopg2":
        conn = drv.connect(dsn)  # autocommit不要（SELECTのみ）
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()
        finally:
            conn.close()
    else:
        # psycopg v3
        with drv.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()

# --- FastAPI ルーター/テンプレ設定 ----------------------------------------------
router = APIRouter(prefix="/pdca", tags=["PDCA / Observability"])
templates = Jinja2Templates(directory=str(NOTRIA_GUI_TEMPLATES_DIR if (NOTRIA_GUI_TEMPLATES_DIR := NOCTRIA_GUI_TEMPLATES_DIR).exists() else "noctria_gui/templates"))

# --- Routes -------------------------------------------------------------------

@router.get("/timeline", response_class=HTMLResponse)
def pdca_timeline(
    request: Request,
    trace_id: Optional[str] = Query(default=None, alias="trace"),
    limit: int = Query(default=200, ge=1, le=2000),
):
    """
    1トレースのイベント時系列（obs_trace_timeline）を表示。
    trace が未指定なら、最近のトレース一覧を提示する。
    """
    if not trace_id:
        rows = _fetchall(
            """
            SELECT trace_id, MAX(ts) AS last_ts, COUNT(*) AS events
            FROM obs_trace_timeline
            WHERE ts >= now() - interval '3 days'
            GROUP BY trace_id
            ORDER BY last_ts DESC
            LIMIT 200
            """
        )
        traces = [{"trace_id": r[0], "last_ts": r[1], "events": r[2]} for r in rows]
        return templates.TemplateResponse(
            "pdca_timeline.html",
            {"request": request, "traces": traces, "events": [], "active_trace": None},
        )

    events = _fetchall(
        """
        SELECT ts, kind, action, payload
        FROM obs_trace_timeline
        WHERE trace_id = %s
        ORDER BY ts
        LIMIT %s
        """,
        (trace_id, limit),
    )
    events_dicts = [{"ts": r[0], "kind": r[1], "action": r[2], "payload": r[3]} for r in events]
    return templates.TemplateResponse(
        "pdca_timeline.html",
        {"request": request, "traces": [], "events": events_dicts, "active_trace": trace_id},
    )

@router.get("/latency/daily", response_class=HTMLResponse)
def pdca_latency_daily(request: Request):
    """
    日次レイテンシ集計（obs_latency_daily）を表示。
    """
    rows = _fetchall(
        """
        SELECT day, p50_ms, p90_ms, p95_ms, max_ms, traces
        FROM obs_latency_daily
        ORDER BY day DESC
        LIMIT 30
        """
    )
    items = [
        {"day": r[0], "p50_ms": r[1], "p90_ms": r[2], "p95_ms": r[3], "max_ms": r[4], "traces": r[5]}
        for r in rows
    ]
    return templates.TemplateResponse(
        "pdca_latency_daily.html",
        {"request": request, "items": items},
    )

@router.post("/observability/refresh")
def pdca_refresh_views():
    """
    ビュー定義とマテビューを再作成/更新。
    GUI から叩く簡易メンテ用（必要に応じてRBACで保護）。
    """
    ensure_views()
    refresh_materialized()
    return JSONResponse({"ok": True, "msg": "views ensured and obs_latency_daily refreshed"})
