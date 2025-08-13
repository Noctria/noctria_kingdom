#!/usr/bin/env python3
# coding: utf-8

"""
📊 PDCA Summary Route (v2.1)
- PDCA再評価ログ（ファイル）を集計してサマリーを表示
- HTML表示 (/pdca/summary) と JSON提供 (/pdca/summary/data) の両方に対応
- 日付パラメータは YYYY-MM-DD を推奨（未指定時は直近14日を自動設定）
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional, Tuple

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, PDCA_LOG_DIR
from src.core.pdca_log_parser import load_and_aggregate_pdca_logs

# -----------------------------------------------------------------------------
# logger
# -----------------------------------------------------------------------------
logger = logging.getLogger("noctria.pdca.summary")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")

# -----------------------------------------------------------------------------
# router / templates
# -----------------------------------------------------------------------------
router = APIRouter(prefix="/pdca", tags=["pdca-summary"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# -----------------------------------------------------------------------------
# helpers
# -----------------------------------------------------------------------------
def _parse_ymd(s: Optional[str]) -> Optional[date]:
    """YYYY-MM-DD を date に。無効時は None。"""
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except Exception:
        logger.warning("Invalid date format (expected YYYY-MM-DD): %s", s)
        return None

def _default_range(days: int = 14) -> Tuple[date, date]:
    """直近days日（今日を含む）の日付範囲を返す。"""
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=days - 1)
    return start, today

def _to_bounds(frm: Optional[date], to: Optional[date]) -> Tuple[datetime, datetime, str, str]:
    """
    date → 日付境界の datetime（UTC, 00:00:00〜23:59:59）に変換。
    文字列（YYYY-MM-DD）も併せて返す。
    """
    if frm is None or to is None:
        d0, d1 = _default_range(14)
    else:
        d0, d1 = (frm, to)

    # from > to の場合はスワップ
    if d0 > d1:
        d0, d1 = d1, d0

    dt_from = datetime(d0.year, d0.month, d0.day, 0, 0, 0, tzinfo=timezone.utc)
    dt_to = datetime(d1.year, d1.month, d1.day, 23, 59, 59, tzinfo=timezone.utc)
    return dt_from, dt_to, d0.isoformat(), d1.isoformat()

def _aggregate(mode: str, limit: int, dt_from: datetime, dt_to: datetime) -> dict:
    """
    ファイルベースのPDCAログを集計（src.core.pdca_log_parser に委譲）。
    例外時は空の結果を返す。
    """
    try:
        res = load_and_aggregate_pdca_logs(
            log_dir=PDCA_LOG_DIR,
            mode=mode,
            limit=limit,
            from_date=dt_from,
            to_date=dt_to,
        )
        logger.info("PDCAログ集計: OK (mode=%s, %s ~ %s)", mode, dt_from.date(), dt_to.date())
        return res or {}
    except Exception as e:
        logger.error("PDCAログ集計エラー: %s", e, exc_info=True)
        return {"stats": {}, "chart": {"labels": [], "data": [], "dd_data": []}}

# -----------------------------------------------------------------------------
# routes
# -----------------------------------------------------------------------------
@router.get("/summary", response_class=HTMLResponse, summary="PDCAサマリー（HTML）")
async def show_pdca_summary(
    request: Request,
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    mode: str = Query(default="strategy", description="集計モード（例: strategy / tag など）"),
    limit: int = Query(default=20, ge=1, le=1000, description="上位N件などの制限"),
) -> HTMLResponse:
    """
    サーバーサイド描画。テンプレートに `summary` / `chart` / `filter` を埋め込む。
    """
    frm_d = _parse_ymd(from_date)
    to_d = _parse_ymd(to_date)
    dt_from, dt_to, frm_str, to_str = _to_bounds(frm_d, to_d)

    result = _aggregate(mode=mode, limit=limit, dt_from=dt_from, dt_to=dt_to)

    context = {
        "request": request,
        "summary": result.get("stats", {}),
        "chart": result.get("chart", {}),
        "filter": {"from": frm_str, "to": to_str},
        "mode": mode,
        "limit": limit,
        # 将来的にボタンのフラッシュメッセージ等に利用
        "recheck_success": None,
        "recheck_fail": None,
    }
    return templates.TemplateResponse("pdca_summary.html", context)

@router.get("/summary/data", response_class=JSONResponse, summary="PDCAサマリー（JSON）")
async def show_pdca_summary_data(
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    mode: str = Query(default="strategy", description="集計モード（例: strategy / tag など）"),
    limit: int = Query(default=20, ge=1, le=1000, description="上位N件などの制限"),
) -> JSONResponse:
    """
    クライアントサイド描画用のJSON（テンプレートやフロントJSから取得）。
    """
    frm_d = _parse_ymd(from_date)
    to_d = _parse_ymd(to_date)
    dt_from, dt_to, frm_str, to_str = _to_bounds(frm_d, to_d)

    result = _aggregate(mode=mode, limit=limit, dt_from=dt_from, dt_to=dt_to)

    return JSONResponse(
        {
            "from": frm_str,
            "to": to_str,
            "mode": mode,
            "limit": limit,
            "stats": result.get("stats", {}),
            "chart": result.get("chart", {"labels": [], "data": [], "dd_data": []}),
        }
    )
