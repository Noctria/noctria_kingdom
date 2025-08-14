# noctria_gui/routes/pdca_summary.py
#!/usr/bin/env python3
# coding: utf-8
"""
📊 PDCA Summary Route (v3.1)

- DBや観測ログを集計してサマリーを提供
- HTML表示 (/pdca/summary) と JSON提供 (/pdca/summary/data)
- 日付は YYYY-MM-DD を推奨（未指定時は直近30日を自動設定）
- テンプレートは HUD 準拠の pdca_summary.html を使用

堅牢化ポイント:
- path_config や plan_data サービスが無い環境でも「空の結果」で動作継続
- テンプレートディレクトリも安全フォールバック
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# -----------------------------------------------------------------------------
# import path 補強（<repo_root> を sys.path に）
# -----------------------------------------------------------------------------
_THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = _THIS_FILE.parents[2]  # <repo_root>
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# -----------------------------------------------------------------------------
# ロガー
# -----------------------------------------------------------------------------
logger = logging.getLogger("noctria.pdca.summary")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

# -----------------------------------------------------------------------------
# テンプレートディレクトリ解決（安全フォールバック）
# -----------------------------------------------------------------------------
def _resolve_templates_dir() -> Path:
    # 1) 推奨: src.core.path_config
    try:
        from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR  # type: ignore
        p = Path(str(NOCTRIA_GUI_TEMPLATES_DIR))
        if p.exists():
            return p
    except Exception:
        pass
    # 2) 互換: core.path_config
    try:
        from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR  # type: ignore
        p = Path(str(NOCTRIA_GUI_TEMPLATES_DIR))
        if p.exists():
            return p
    except Exception:
        pass
    # 3) フォールバック: <repo_root>/noctria_gui/templates
    return PROJECT_ROOT / "noctria_gui" / "templates"


_TEMPLATES_DIR = _resolve_templates_dir()
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

# -----------------------------------------------------------------------------
# データ取得サービス（安全インポート）
# -----------------------------------------------------------------------------
def _load_pdca_services():
    """
    fetch_infer_calls(frm_dt, to_dt) -> List[Dict]
    aggregate_kpis(rows) -> Dict[str, Any]
    aggregate_by_day(rows) -> List[Dict[str, Any]]
    """
    try:
        from src.plan_data.pdca_summary_service import (  # type: ignore
            fetch_infer_calls,
            aggregate_kpis,
            aggregate_by_day,
        )
        return fetch_infer_calls, aggregate_kpis, aggregate_by_day
    except Exception as e:
        logger.warning("pdca_summary_service unavailable (%s) — fallback to empty dataset.", e)

        def _fetch_infer_calls(frm_dt: datetime, to_dt: datetime) -> List[Dict[str, Any]]:
            return []

        def _aggregate_kpis(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
            # UI が期待する最低限のキー
            return {
                "evals": 0,
                "rechecks": 0,
                "adopted": 0,
                "adopt_rate": None,
                "win_rate": None,
                "max_drawdown": None,
                "trades": 0,
            }

        def _aggregate_by_day(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            return []

        return _fetch_infer_calls, _aggregate_kpis, _aggregate_by_day


fetch_infer_calls, aggregate_kpis, aggregate_by_day = _load_pdca_services()

# -----------------------------------------------------------------------------
# ルーター
# -----------------------------------------------------------------------------
router = APIRouter(prefix="/pdca", tags=["PDCA"])

SCHEMA_VERSION = "2025-08-01"

# -----------------------------------------------------------------------------
# ヘルパ
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


def _default_range_days(days: int = 30) -> Tuple[datetime, datetime]:
    """
    直近days日（今日を含む）を返す（naive datetime）。
    """
    today_local = datetime.now(timezone.utc).astimezone().date()
    start = today_local - timedelta(days=days - 1)
    return (
        datetime(start.year, start.month, start.day),
        datetime(today_local.year, today_local.month, today_local.day),
    )


def _normalize_range(
    frm: Optional[datetime], to: Optional[datetime]
) -> Tuple[datetime, datetime, str, str]:
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
# Routes
# -----------------------------------------------------------------------------
@router.get(
    "/summary",
    response_class=HTMLResponse,
    summary="PDCAサマリー（HTML）",
)
async def pdca_summary_page(
    request: Request,
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
) -> HTMLResponse:
    """
    サーバーサイド描画（ページの土台のみ）。実データは /pdca/summary/data から取得。
    テンプレートに default_from / default_to / schema_version を渡す。
    """
    tpl = _TEMPLATES_DIR / "pdca_summary.html"
    if not tpl.exists():
        return HTMLResponse(
            content=(
                "<h3>pdca_summary.html が見つかりません。</h3>"
                f"<p>探索ディレクトリ: {_TEMPLATES_DIR}</p>"
                "<p>noctria_gui/templates/pdca_summary.html を配置してください。</p>"
            ),
            status_code=500,
        )

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


@router.get(
    "/summary/data",
    response_class=JSONResponse,
    summary="PDCAサマリー（JSON）",
)
async def pdca_summary_data(
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
) -> JSONResponse:
    """
    観測ログを期間で集計した JSON を返す。
    - totals: KPI（評価件数・再評価件数・採用件数・採用率・平均勝率・最大DD・取引数）
    - by_day: 日次系列（date, evals, adopted, trades, win_rate など）
    """
    frm = _parse_date_ymd(from_date)
    to = _parse_date_ymd(to_date)
    if not frm or not to:
        raise HTTPException(
            status_code=400, detail="from_date/to_date は YYYY-MM-DD 形式で指定してください。"
        )

    frm, to, from_str, to_str = _normalize_range(frm, to)

    # データ取得＆集計（接続不可・テーブル未作成時は空配列 -> totals/seriesは None/0 で返る）
    try:
        rows = fetch_infer_calls(frm, to)  # List[Dict]
    except Exception as e:
        logger.error("fetch_infer_calls failed: %s", e, exc_info=True)
        rows = []

    try:
        totals = aggregate_kpis(rows)
    except Exception as e:
        logger.error("aggregate_kpis failed: %s", e, exc_info=True)
        totals = {
            "evals": 0,
            "rechecks": 0,
            "adopted": 0,
            "adopt_rate": None,
            "win_rate": None,
            "max_drawdown": None,
            "trades": 0,
        }

    try:
        series = aggregate_by_day(rows)
    except Exception as e:
        logger.error("aggregate_by_day failed: %s", e, exc_info=True)
        series = []

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
