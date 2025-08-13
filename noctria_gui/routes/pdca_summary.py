#!/usr/bin/env python3
# coding: utf-8
"""
📊 PDCA Summary Route (v3.0)
- DBの観測ログ(obs_infer_calls)を集計してサマリーを提供
- HTML表示 (/pdca/summary) と JSON提供 (/pdca/summary/data)
- 日付は YYYY-MM-DD を推奨（未指定時は直近30日を自動設定）
- テンプレートは HUD 準拠の pdca_summary.html を使用
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from pathlib import Path

# --- sys.path を安全側で補強（<repo_root> を追加: import src.*** を安定化） ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR  # type: ignore
from src.plan_data.pdca_summary_service import (  # type: ignore
    fetch_infer_calls,
    aggregate_kpis,
    aggregate_by_day,
)

# -----------------------------------------------------------------------------
# logger
# -----------------------------------------------------------------------------
logger = logging.getLogger("noctria.pdca.summary")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# -----------------------------------------------------------------------------
# router / templates
# -----------------------------------------------------------------------------
router = APIRouter(prefix="/pdca", tags=["PDCA"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

SCHEMA_VERSION = "2025-08-01"


# -----------------------------------------------------------------------------
# helpers
# -----------------------------------------------------------------------------
def _parse_date_ymd(s: Optional[str]) -> Optional[datetime]:
    """YYYY-MM-DD -> naive datetime（日付のみ）。不正な場合は None。"""
    if not s:
        return None
    try:
        y, m, d = s.split("-")
        return datetime(int(y), int(m), int(d))
    except Exception:
        logger.warning("Invalid date format (expected YYYY-MM-DD): %s", s)
        return None


def _default_range_days(days: int = 30) -> tuple[datetime, datetime]:
    """直近days日（今日を含む）を返す（naive datetime, 00:00:00 と 23:59:59 は下流で設定）。"""
    today_local = datetime.now(timezone.utc).astimezone().date()
    start = today_local - timedelta(days=days - 1)
    return (datetime(start.year, start.month, start.day), datetime(today_local.year, today_local.month, today_local.day))


def _normalize_range(frm: Optional[datetime], to: Optional[datetime]) -> tuple[datetime, datetime, str, str]:
    """
    naive datetime（日付のみ）を受け取り、YYYY-MM-DD 文字列も併せて返す。
    from > to の場合はスワップ。
    """
    if frm is None or to is None:
        frm, to = _default_range_days(30)

    if to < frm:
        frm, to = to, frm

    return frm, to, frm.date().isoformat(), to.date().isoformat()


# -----------------------------------------------------------------------------
# routes
# -----------------------------------------------------------------------------
@router.get("/summary", response_class=HTMLResponse, summary="PDCAサマリー（HTML）")
async def pdca_summary_page(
    request: Request,
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
) -> HTMLResponse:
    """
    サーバーサイド描画（ページの土台のみ）。実データは /pdca/summary/data から取得。
    テンプレートに default_from / default_to / schema_version を渡す。
    """
    frm = _parse_date_ymd(from_date)
    to = _parse_date_ymd(to_date)
    _, _, default_from, default_to = _normalize_range(frm, to)

    context: Dict[str, Any] = {
        "request": request,
        "default_from": default_from,
        "default_to": default_to,
        "schema_version": SCHEMA_VERSION,
    }
    return templates.TemplateResponse("pdca_summary.html", context)


@router.get("/summary/data", response_class=JSONResponse, summary="PDCAサマリー（JSON）")
async def pdca_summary_data(
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
) -> JSONResponse:
    """
    観測ログ (obs_infer_calls) を期間で集計した JSON を返す。
    - totals: KPI（評価件数・再評価件数・採用件数・採用率・平均勝率・最大DD・取引数）
    - by_day: 日次系列（date, evals, adopted, trades, win_rate）
    """
    frm = _parse_date_ymd(from_date)
    to = _parse_date_ymd(to_date)
    if not frm or not to:
        raise HTTPException(status_code=400, detail="from_date/to_date は YYYY-MM-DD 形式で指定してください。")

    frm, to, from_str, to_str = _normalize_range(frm, to)

    # データ取得＆集計（接続不可・テーブル未作成時は空配列 -> totals/seriesは None/0 で返る）
    rows = fetch_infer_calls(frm, to)
    totals = aggregate_kpis(rows)
    series = aggregate_by_day(rows)

    payload = {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "from": from_str,
        "to": to_str,
        "totals": totals,
        "by_day": series,
        "count_rows": len(rows),
    }
    return JSONResponse(payload)
