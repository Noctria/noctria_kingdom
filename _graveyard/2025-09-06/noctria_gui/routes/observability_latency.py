# noctria_gui/routes/observability_latency.py
# -*- coding: utf-8 -*-
"""
📈 Observability: Latency Dashboard (FastAPI)
- 画面: GET /observability/latency
    日次レイテンシ分布（p50/p90/p99）＋最近トレース一覧
    ?trace_id=... を付けると該当トレースのタイムライン詳細を表示

データ前提:
  - obs_trace_timeline は VIEW または TABLE
    候補列名の違いに自動対応:
      time:   ts / at
      stage:  kind / stage
      name:   action / name
      detail: payload / detail
  - obs_latency_daily は MATERIALIZED VIEW（列: day, events, p50_ms, p90_ms, p99_ms）

DSN:
  - 環境変数 NOCTRIA_OBS_PG_DSN を優先
  - 未設定時はローカルDB既定: postgresql://noctria:noctria@localhost:5432/noctria_db
"""

from __future__ import annotations

import json
import os
import sys
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.templating import Jinja2Templates

# ─────────────────────────────────────────────────────────────────────────────
# Logging（例外を握り潰さない）
# ─────────────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
if not logger.handlers:
    h = logging.StreamHandler(sys.stderr)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
    h.setFormatter(fmt)
    logger.addHandler(h)
logger.setLevel(logging.INFO)

# ─────────────────────────────────────────────────────────────────────────────
# DSN: 観測用 ENV を尊重（未設定ならローカル既定）
# ─────────────────────────────────────────────────────────────────────────────
OBS_DSN = os.getenv(
    "NOCTRIA_OBS_PG_DSN",
    "postgresql://noctria:noctria@localhost:5432/noctria_db",
)

# ─────────────────────────────────────────────────────────────────────────────
# Templates
# ─────────────────────────────────────────────────────────────────────────────
TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/observability", tags=["observability"])


# ─────────────────────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────────────────────
def _connect():
    try:
        return psycopg2.connect(OBS_DSN)
    except Exception as e:
        logger.error("DB connect failed: %s", repr(e))
        raise


def _query(sql: str, params: Tuple[Any, ...] | None = None) -> List[Dict[str, Any]]:
    try:
        conn = _connect()
        with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            logger.debug("SQL: %s ; params=%s", sql, params)
            cur.execute(sql, params or ())
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error("Query failed: %s ; params=%s ; err=%s", sql, params, repr(e))
        return []
    finally:
        try:
            conn.close()  # type: ignore[name-defined]
        except Exception:
            pass


def _one(sql: str, params: Tuple[Any, ...] | None = None) -> Optional[Dict[str, Any]]:
    rows = _query(sql, params)
    return rows[0] if rows else None


def _first_existing_col(schema: str, rel: str, candidates: List[str]) -> Optional[str]:
    """
    information_schema から列存在を確認し、先勝ちで返す。
    """
    placeholders = ", ".join(["%s"] * len(candidates))
    rows = _query(
        f"""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema=%s AND table_name=%s AND column_name IN ({placeholders})
        """,
        tuple([schema, rel] + candidates),
    )
    existing = {r["column_name"] for r in rows}
    for c in candidates:
        if c in existing:
            return c
    return None


def _timeline_column_map() -> Dict[str, str]:
    """
    obs_trace_timeline のカラム名を判定（列名の差異に対応）。
    返り値: {"time":"ts|at", "stage":"kind|stage", "name":"action|name", "detail":"payload|detail"}
    """
    schema, rel = "public", "obs_trace_timeline"
    time_col = _first_existing_col(schema, rel, ["ts", "at"]) or "ts"
    stage_col = _first_existing_col(schema, rel, ["kind", "stage"]) or "kind"
    name_col = _first_existing_col(schema, rel, ["action", "name"]) or "action"
    detail_col = _first_existing_col(schema, rel, ["payload", "detail"]) or "payload"
    return {"time": time_col, "stage": stage_col, "name": name_col, "detail": detail_col}


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


# ─────────────────────────────────────────────────────────────────────────────
# HTML: /observability/latency
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/latency", response_class=HTMLResponse)
def latency_dashboard(request: Request):
    """
    日次レイテンシ分布（p50/p90/p99）＋最近トレース一覧。
    ?trace_id=... で該当トレースのタイムライン詳細も表示。
    """
    # 1) 日次レイテンシ分布
    daily = _query(
        """
        SELECT day::date AS day, events, p50_ms, p90_ms, p99_ms
        FROM public.obs_latency_daily
        ORDER BY day ASC
        """
    )

    # 2) 最近のトレース20件（列名の差異に対応）
    cols = _timeline_column_map()
    tcol = cols["time"]
    recent_sql = f"""
        SELECT trace_id,
               MIN({tcol}) AS started_at,
               MAX({tcol}) AS finished_at,
               COUNT(*)    AS events
        FROM public.obs_trace_timeline
        GROUP BY trace_id
        ORDER BY MAX({tcol}) DESC
        LIMIT 20
    """
    recent = _query(recent_sql)

    # 3) 任意 trace_id のタイムライン詳細
    trace_id = request.query_params.get("trace_id")
    timeline: List[Dict[str, Any]] = []
    decision: Dict[str, Any] | None = None
    infer: Dict[str, Any] | None = None

    if trace_id:
        scol, ncol, dcol = cols["stage"], cols["name"], cols["detail"]
        detail_sql = f"""
            SELECT
              {tcol} AS at,
              {scol} AS stage,
              {ncol} AS name,
              {dcol} AS detail
            FROM public.obs_trace_timeline
            WHERE trace_id = %s
            ORDER BY {tcol} ASC
        """
        timeline = _query(detail_sql, (trace_id,))

        # INFER / DECISION の1件目を拾って上段に要約表示
        for ev in timeline:
            stage = ev.get("stage")
            if stage == "INFER" and infer is None:
                det = ev.get("detail") or {}
                dur = (det.get("duration_ms") if isinstance(det, dict) else None) or (
                    det.get("dur_ms") if isinstance(det, dict) else None
                )
                infer = {
                    "at": ev.get("at"),
                    "name": ev.get("name"),
                    "dur_ms": _safe_int(dur),
                    "success": bool((det or {}).get("success", False)) if isinstance(det, dict) else None,
                }
            if stage == "DECISION" and decision is None:
                det = ev.get("detail") or {}
                decision = {
                    "at": ev.get("at"),
                    "strategy_name": ev.get("name"),
                    "score": _safe_float((det or {}).get("score")) if isinstance(det, dict) else None,
                    "reason": (det or {}).get("reason") if isinstance(det, dict) else None,
                    "action": (det or {}).get("action") if isinstance(det, dict) else None,
                    "params": (det or {}).get("params") if isinstance(det, dict) else None,
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


# ─────────────────────────────────────────────────────────────────────────────
# Debug: /observability/latency/_debug
#   現在の DSN／列マッピング／件数／直近 trace の一部 を返す
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/latency/_debug", response_class=JSONResponse)
def latency_debug():
    cols = _timeline_column_map()
    tcol = cols["time"]
    try:
        env_dsn = OBS_DSN
        # カウント類
        mv = _one("SELECT COUNT(*) AS c FROM public.obs_latency_daily") or {"c": None}
        tl = _one("SELECT COUNT(*) AS c FROM public.obs_trace_timeline") or {"c": None}
        latest = _one(f"SELECT MAX({tcol}) AS latest FROM public.obs_trace_timeline") or {"latest": None}
        who = _one("SELECT current_user, current_database() AS db, now() AS now")

        # 直近 trace_id 3件
        sample = _query(
            f"""
            SELECT trace_id, MIN({tcol}) AS started_at, MAX({tcol}) AS finished_at, COUNT(*) AS events
            FROM public.obs_trace_timeline
            GROUP BY trace_id
            ORDER BY MAX({tcol}) DESC
            LIMIT 3
            """
        )
        return {
            "dsn": env_dsn,
            "current_user": (who or {}).get("current_user"),
            "current_database": (who or {}).get("db"),
            "now": str((who or {}).get("now")),
            "obs_latency_daily.count": mv.get("c"),
            "obs_trace_timeline.count": tl.get("c"),
            "obs_trace_timeline.latest_ts": None if latest.get("latest") is None else str(latest.get("latest")),
            "timeline_columns": cols,
            "recent_sample": sample,
        }
    except Exception as e:
        logger.error("debug error: %s", repr(e))
        return {"dsn": OBS_DSN, "error": repr(e), "timeline_columns": cols}


# 互換エクスポート（既存コードの参照名を生かす）
bp_obs_latency = router
obs_bp = router
__all__ = ["router", "bp_obs_latency", "obs_bp", "latency_dashboard"]
