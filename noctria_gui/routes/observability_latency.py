# noctria_gui/routes/observability_latency.py
# -*- coding: utf-8 -*-
"""
📈 Observability: Latency Dashboard (FastAPI)
- 画面: GET /observability/latency
    日次レイテンシ分布（p50/p90/p99）＋最近トレース一覧
    ?trace_id=... で該当トレースのタイムライン詳細を表示

前提:
  - obs_trace_timeline は VIEW（trace_id, ts, kind, action, payload(jsonb)）
  - obs_latency_daily は MATERIALIZED VIEW（day, events, p50_ms, p90_ms, p99_ms）

DSN 解決ポリシー:
  1) .env を見つけて読み込む（プロジェクトルートから上位に向かって探索）
  2) 環境変数 NOCTRIA_OBS_PG_DSN を採用（例: postgresql://noctria:noctria@127.0.0.1:5432/noctria_db）
  3) 未設定時は localhost 既定にフォールバック
"""

from __future__ import annotations

import json
import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.templating import Jinja2Templates

# ------------------------- .env をロード（任意） -------------------------
def _load_dotenv_if_exists() -> None:
    try:
        from dotenv import load_dotenv  # python-dotenv
    except Exception:
        return
    # noctria_kingdom/.env を優先的に探す
    here = Path(__file__).resolve()
    for p in [here.parents[i] for i in range(0, 5)]:
        cand = p / ".env"
        if cand.exists():
            load_dotenv(cand.as_posix())
            break

_load_dotenv_if_exists()

# ----------------------------- ロガー -----------------------------------
log = logging.getLogger("noctria_gui.obs_latency")

# ------------------------------ DSN -------------------------------------
def _mask_dsn(dsn: str) -> str:
    # postgresql://user:pass@host:port/db → pass を *** に
    try:
        if "://" in dsn and "@" in dsn:
            scheme_rest = dsn.split("://", 1)
            creds_host = scheme_rest[1]
            if "@" in creds_host and ":" in creds_host.split("@", 1)[0]:
                user, rest = creds_host.split("@", 1)
                u, _ = user.split(":", 1)
                return f"{scheme_rest[0]}://{u}:***@{rest}"
    except Exception:
        pass
    return dsn

OBS_DSN = os.getenv(
    "NOCTRIA_OBS_PG_DSN",
    "postgresql://noctria:noctria@127.0.0.1:5432/noctria_db",
)
log.warning("Observability DSN = %s", _mask_dsn(OBS_DSN))

# --------------------------- Templates -----------------------------------
TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ------------------------------ Router -----------------------------------
router = APIRouter(prefix="/observability", tags=["observability"])

# ------------------------------ DB Help ----------------------------------
def _query(sql: str, params: Tuple[Any, ...] | None = None) -> List[Dict[str, Any]]:
    try:
        conn = psycopg2.connect(OBS_DSN)
    except Exception as e:
        log.warning("DB connect failed: %s (DSN=%s)", e, _mask_dsn(OBS_DSN))
        return []
    try:
        with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        log.warning("DB query failed: %s\nSQL=%s\nparams=%r", e, sql, params)
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

# ----------------------------- HTML: /latency ----------------------------
@router.get(
    "/latency",
    name="observability_latency.latency_dashboard",
    response_class=HTMLResponse,
)
def latency_dashboard(request: Request):
    # 1) 日次レイテンシ分布
    daily = _query(
        """
        SELECT day::date AS day, events, p50_ms, p90_ms, p99_ms
        FROM public.obs_latency_daily
        ORDER BY day ASC
        """
    )

    # 2) 最近のトレース20件
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

    # 3) 指定 trace_id のタイムライン詳細
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
        for ev in timeline:
            stage = ev.get("stage")
            if stage == "INFER" and infer is None:
                det = ev.get("detail") or {}
                dur = det.get("duration_ms", det.get("dur_ms"))
                infer = {
                    "at": ev.get("at"),
                    "name": ev.get("name"),
                    "dur_ms": _safe_int(dur),
                    "success": bool(det.get("success", False)),
                }
            if stage == "DECISION" and decision is None:
                det = ev.get("detail") or {}
                decision = {
                    "at": ev.get("at"),
                    "strategy_name": ev.get("name"),
                    "score": _safe_float(det.get("score")),
                    "reason": det.get("reason"),
                    "action": det.get("action"),
                    "params": det.get("params"),
                }

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

# ----------------------------- /latency/_debug ---------------------------
@router.get("/latency/_debug", response_class=JSONResponse)
def latency_debug():
    """接続確認用: 使っている DSN と件数を返す"""
    daily_cnt = _query("SELECT COUNT(*) AS c FROM public.obs_latency_daily")
    tl_cnt    = _query("SELECT COUNT(*) AS c FROM public.obs_trace_timeline")
    latest    = _query(
        "SELECT MAX(ts) AS last_ts FROM public.obs_trace_timeline"
    )
    return {
        "dsn": _mask_dsn(OBS_DSN),
        "obs_latency_daily.count": (daily_cnt[0]["c"] if daily_cnt else None),
        "obs_trace_timeline.count": (tl_cnt[0]["c"] if tl_cnt else None),
        "obs_trace_timeline.latest_ts": (latest[0]["last_ts"] if latest else None),
    }

# 互換エクスポート
bp_obs_latency = router
obs_bp = router
__all__ = ["router", "bp_obs_latency", "obs_bp", "latency_dashboard"]
