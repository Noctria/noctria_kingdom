# noctria_gui/routes/observability.py
from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

# --------------------------------------------------------------------
# テンプレ/パス解決（集中管理）。python -m / 直実行の両対応。
# --------------------------------------------------------------------
try:
    from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR  # when running with `python -m`
except Exception:
    from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR  # when running from repo root

TEMPLATE_DIR: Path = (
    NOCTRIA_GUI_TEMPLATES_DIR if NOCTRIA_GUI_TEMPLATES_DIR.exists() else Path("noctria_gui/templates")
)
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

# --------------------------------------------------------------------
# Observability ユーティリティ（View/MVの作成・更新）
# --------------------------------------------------------------------
try:
    from src.plan_data.observability import ensure_views, refresh_materialized  # type: ignore
except Exception:
    from plan_data.observability import ensure_views, refresh_materialized  # type: ignore

# --------------------------------------------------------------------
# DB 接続（psycopg2 → psycopg v3 フォールバック）
# --------------------------------------------------------------------
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
        import psycopg as drv  # type: ignore

        _DRIVER, _DB_KIND = drv, "psycopg"
    return _DRIVER, _DB_KIND


def _fetchall(sql: str, params: Iterable[Any] = ()) -> List[Tuple]:
    drv, kind = _import_driver()
    dsn = _get_dsn()
    if kind == "psycopg2":
        conn = drv.connect(dsn)
        try:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                return cur.fetchall()
        finally:
            conn.close()
    else:
        # psycopg v3
        with drv.connect(dsn, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                return cur.fetchall()


# --------------------------------------------------------------------
# Router
# --------------------------------------------------------------------
router = APIRouter(prefix="/pdca", tags=["PDCA / Observability"])

# --------------------------------------------------------------------
# /pdca/timeline
#   - trace_id 指定：そのトレースのイベント時系列（payload はテキスト化）
#   - 未指定：最近のトレース一覧 + 直近イベント一覧
# --------------------------------------------------------------------
@router.get("/timeline", response_class=HTMLResponse)
def pdca_timeline(
    request: Request,
    trace_id: Optional[str] = Query(default=None),
    from_date: Optional[str] = Query(default=None),
    to_date: Optional[str] = Query(default=None),
    limit: int = Query(default=300, ge=1, le=2000),
    days: int = Query(default=3, ge=1, le=90, description="期間未指定時に遡る日数（既定3日）"),
):
    try:
        f_dt: Optional[datetime] = None
        t_dt: Optional[datetime] = None
        if from_date:
            f_dt = datetime.fromisoformat(from_date)
        if to_date:
            t_dt = datetime.fromisoformat(to_date)
    except ValueError:
        # フォーマット不正時は期間フィルタ無しで続行
        f_dt = t_dt = None

    # --- 最近のトレース一覧（ドロップダウン用）
    where_recent = []
    params_recent: List[Any] = []
    if f_dt:
        where_recent.append("ts >= %s")
        params_recent.append(f_dt)
    if t_dt:
        where_recent.append("ts <= %s")
        params_recent.append(t_dt)
    if not where_recent:
        # 期間指定が無い場合は days で遡る（timedelta を interval として渡す）
        where_recent.append("ts >= now() - %s")
        params_recent.append(timedelta(days=days))
    sql_recent = f"""
        SELECT trace_id, MAX(ts) AS last_ts, COUNT(*) AS events
          FROM obs_trace_timeline
         WHERE {" AND ".join(where_recent)}
         GROUP BY trace_id
         ORDER BY last_ts DESC
         LIMIT 50;
    """
    recent_rows = _fetchall(sql_recent, tuple(params_recent))
    recent_traces = [{"trace_id": r[0], "last_ts": r[1], "events": r[2]} for r in recent_rows]

    # --- イベント本体
    events: List[Dict[str, Any]] = []
    if trace_id:
        rows = _fetchall(
            """
            SELECT ts, kind, action, payload::text
              FROM obs_trace_timeline
             WHERE trace_id = %s
             ORDER BY ts
             LIMIT %s;
            """,
            (trace_id, limit),
        )
        events = [{"ts": r[0], "kind": r[1], "action": r[2], "payload": r[3]} for r in rows]
    else:
        # トレース未指定時は直近イベント一覧を表示（テンプレ側で trace_id 列が出る）
        where_ev = []
        params_ev: List[Any] = []
        if f_dt:
            where_ev.append("ts >= %s")
            params_ev.append(f_dt)
        if t_dt:
            where_ev.append("ts <= %s")
            params_ev.append(t_dt)
        if not where_ev:
            where_ev.append("ts >= now() - %s")
            params_ev.append(timedelta(days=days))
        rows = _fetchall(
            f"""
            SELECT trace_id, ts, kind, action
              FROM obs_trace_timeline
             WHERE {" AND ".join(where_ev)}
             ORDER BY ts DESC
             LIMIT %s;
            """,
            (*params_ev, limit),
        )
        events = [
            {"trace_id": r[0], "ts": r[1], "kind": r[2], "action": r[3], "payload": None} for r in rows
        ]

    # テンプレへ（前に共有したテンプレと互換のキー名）
    return templates.TemplateResponse(
        "pdca_timeline.html",
        {
            "request": request,
            "trace_id": trace_id,
            "recent_traces": recent_traces,
            "events": events,
            "filter": {"from": from_date, "to": to_date},
            "limit": limit,
            "days": days,
        },
    )


# --------------------------------------------------------------------
# /pdca/latency/daily
#   - obs_latency_daily（MV）を折れ線＆棒で可視化
#   - from/to 未指定時は days で遡る
# --------------------------------------------------------------------
@router.get("/latency/daily", response_class=HTMLResponse)
def pdca_latency_daily(
    request: Request,
    from_date: Optional[str] = Query(default=None),
    to_date: Optional[str] = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
):
    try:
        today = datetime.utcnow().date()
        f_day = today - timedelta(days=days - 1)
        t_day = today
        if from_date:
            f_day = datetime.fromisoformat(from_date).date()
        if to_date:
            t_day = datetime.fromisoformat(to_date).date()
    except ValueError:
        # フォーマット不正時はデフォルト期間
        today = datetime.utcnow().date()
        f_day = today - timedelta(days=days - 1)
        t_day = today

    rows = _fetchall(
        """
        SELECT day, p50_ms, p90_ms, p95_ms, max_ms, traces
          FROM obs_latency_daily
         WHERE day BETWEEN %s AND %s
         ORDER BY day;
        """,
        (f_day, t_day),
    )
    labels = [r[0].isoformat() for r in rows]
    p50 = [float(r[1]) if r[1] is not None else None for r in rows]
    p90 = [float(r[2]) if r[2] is not None else None for r in rows]
    p95 = [float(r[3]) if r[3] is not None else None for r in rows]
    mx = [float(r[4]) if r[4] is not None else None for r in rows]
    n = [int(r[5]) if r[5] is not None else 0 for r in rows]

    # テンプレへ（配列と表データの両方を渡しておく）
    items = [
        {"day": labels[i], "p50_ms": p50[i], "p90_ms": p90[i], "p95_ms": p95[i], "max_ms": mx[i], "traces": n[i]}
        for i in range(len(labels))
    ]
    return templates.TemplateResponse(
        "pdca_latency_daily.html",
        {
            "request": request,
            "labels": labels,
            "p50": p50,
            "p90": p90,
            "p95": p95,
            "mx": mx,
            "traces": n,
            "items": items,  # 互換用
            "filter": {"from": f_day.isoformat(), "to": t_day.isoformat()},
        },
    )


# --------------------------------------------------------------------
# /pdca/observability/refresh
#   - ビューの再定義＋マテビューrefresh（権限なければビューのみ）
# --------------------------------------------------------------------
@router.post("/observability/refresh")
def pdca_refresh_views():
    try:
        ensure_views()
        try:
            refresh_materialized()
            msg = "views ensured and obs_latency_daily refreshed"
        except Exception:
            msg = "views ensured (materialized refresh skipped)"
        return JSONResponse({"ok": True, "msg": msg})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
