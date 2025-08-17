# noctria_gui/routes/pdca_summary.py
#!/usr/bin/env python3
# coding: utf-8
"""
📊 PDCA Summary Route (v3.5)

- HTML表示 (/pdca/summary)
- JSON提供 (/pdca/summary/data)
- CSVエクスポート (/pdca/summary.csv)
- 互換API（旧フロント用）:
    - /pdca/api/summary            ← 200でJSONを直接返す（リダイレクト廃止）
    - /pdca/api/summary_timeseries ← 同上（当面は /summary/data と同形）

堅牢化:
- 依存サービスが無い環境でも空結果で継続
- request.app.state.jinja_env があれば優先
"""

from __future__ import annotations

import csv
import logging
import sys
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates

# ---------------------------------------------------------------------
# import path 補強
# ---------------------------------------------------------------------
_THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = _THIS_FILE.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# ---------------------------------------------------------------------
# logger
# ---------------------------------------------------------------------
logger = logging.getLogger("noctria.pdca.summary")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# ---------------------------------------------------------------------
# templates
# ---------------------------------------------------------------------
def _resolve_templates_dir() -> Path:
    for mod_name in ("src.core.path_config", "core.path_config"):
        try:
            mod = __import__(mod_name, fromlist=["NOCTRIA_GUI_TEMPLATES_DIR"])
            p = Path(str(getattr(mod, "NOCTRIA_GUI_TEMPLATES_DIR")))
            if p.exists():
                return p
        except Exception:
            pass
    return PROJECT_ROOT / "noctria_gui" / "templates"

_TEMPLATES_DIR = _resolve_templates_dir()
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

# ---------------------------------------------------------------------
# services (safe import)
# ---------------------------------------------------------------------
def _load_pdca_services():
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
            return {
                "evals": 0,
                "rechecks": 0,
                "adopted": 0,
                "adopt_rate": None,
                "adoption_rate": None,  # 互換キー（あればそのまま使うUI向け）
                "win_rate": None,
                "max_drawdown": None,
                "trades": 0,
            }

        def _aggregate_by_day(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            return []

        return _fetch_infer_calls, _aggregate_kpis, _aggregate_by_day

fetch_infer_calls, aggregate_kpis, aggregate_by_day = _load_pdca_services()

# ---------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------
SCHEMA_VERSION = "2025-08-01"

def _parse_date_ymd(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        y, m, d = s.split("-")
        return datetime(int(y), int(m), int(d))
    except Exception:
        logger.warning("Invalid date format (expected YYYY-MM-DD): %s", s)
        return None

def _default_range_days(days: int = 30) -> Tuple[datetime, datetime]:
    today_local = datetime.now(timezone.utc).astimezone().date()
    start = today_local - timedelta(days=days - 1)
    return (
        datetime(start.year, start.month, start.day),
        datetime(today_local.year, today_local.month, today_local.day),
    )

def _normalize_range(frm: Optional[datetime], to: Optional[datetime]) -> Tuple[datetime, datetime, str, str]:
    if frm is None or to is None:
        frm, to = _default_range_days(30)
    if to < frm:
        frm, to = to, frm
    return frm, to, frm.date().isoformat(), to.date().isoformat()

# ---------------------------------------------------------------------
# router
# ---------------------------------------------------------------------
router = APIRouter(prefix="/pdca", tags=["PDCA"])

@router.get("/summary", response_class=HTMLResponse, summary="PDCAサマリー（HTML）")
async def pdca_summary_page(
    request: Request,
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date: Optional[str]   = Query(None, description="YYYY-MM-DD"),
) -> HTMLResponse:
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
    to  = _parse_date_ymd(to_date)
    _, _, default_from, default_to = _normalize_range(frm, to)

    env = getattr(request.app.state, "jinja_env", templates.env)
    html = env.get_template("pdca_summary.html").render(
        request=request,
        page_title="🧭 PDCA Summary",
        default_from=default_from,
        default_to=default_to,
        schema_version=SCHEMA_VERSION,
        recent_adoptions_params={"pattern": "veritas-", "limit": 9, "cols": 3, "title": "🧩 直近採用タグ"},
    )
    return HTMLResponse(html)

@router.get("/summary/data", response_class=JSONResponse, summary="PDCAサマリー（JSON）")
async def pdca_summary_data(
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date:   str = Query(..., description="YYYY-MM-DD"),
) -> JSONResponse:
    frm = _parse_date_ymd(from_date)
    to  = _parse_date_ymd(to_date)
    if not frm or not to:
        raise HTTPException(status_code=400, detail="from_date/to_date は YYYY-MM-DD 形式で指定してください。")

    frm, to, from_str, to_str = _normalize_range(frm, to)

    try:
        rows = fetch_infer_calls(frm, to)
    except Exception as e:
        logger.error("fetch_infer_calls failed: %s", e, exc_info=True)
        rows = []

    try:
        totals = aggregate_kpis(rows)
        # 互換: adopt_rate/adoption_rate の両方を用意（無ければ補完）
        if totals.get("adoption_rate") is None and totals.get("adopt_rate") is not None:
            totals["adoption_rate"] = totals["adopt_rate"]
        if totals.get("adopt_rate") is None and totals.get("adoption_rate") is not None:
            totals["adopt_rate"] = totals["adoption_rate"]
    except Exception as e:
        logger.error("aggregate_kpis failed: %s", e, exc_info=True)
        totals = {
            "evals": 0,
            "rechecks": 0,
            "adopted": 0,
            "adopt_rate": None,
            "adoption_rate": None,
            "win_rate": None,
            "max_drawdown": None,
            "trades": 0,
        }

    try:
        series = aggregate_by_day(rows)
    except Exception as e:
        logger.error("aggregate_by_day failed: %s", e, exc_info=True)
        series = []

    return JSONResponse(
        {
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "from": from_str,
            "to": to_str,
            "totals": totals,
            "by_day": series,
            "count_rows": len(rows),
        }
    )

@router.get("/summary.csv", response_class=Response, summary="PDCAサマリー（日次CSV）")
async def pdca_summary_csv(
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date:   str = Query(..., description="YYYY-MM-DD"),
) -> Response:
    frm = _parse_date_ymd(from_date)
    to  = _parse_date_ymd(to_date)
    if not frm or not to:
        raise HTTPException(status_code=400, detail="from_date/to_date は YYYY-MM-DD 形式で指定してください。")

    frm, to, from_str, to_str = _normalize_range(frm, to)

    try:
        rows = fetch_infer_calls(frm, to)
    except Exception as e:
        logger.error("fetch_infer_calls failed: %s", e, exc_info=True)
        rows = []

    try:
        series = aggregate_by_day(rows)
    except Exception as e:
        logger.error("aggregate_by_day failed: %s", e, exc_info=True)
        series = []

    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(["date", "evals", "adopted", "trades", "win_rate"])
    for r in series:
        w.writerow([
            r.get("date", ""),
            r.get("evals", 0),
            r.get("adopted", 0),
            r.get("trades", 0),
            "" if r.get("win_rate") is None else r.get("win_rate"),
        ])

    headers = {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": f'attachment; filename="pdca_summary_{from_str}_to_{to_str}.csv"',
        "Cache-Control": "no-store",
    }
    return Response(content=buf.getvalue(), headers=headers)

# ---------------------------------------------------------------------
# 互換API（旧フロント向け）— リダイレクトせず200でJSONを返す
# ---------------------------------------------------------------------
@router.get("/api/summary", include_in_schema=False)
async def api_summary_legacy(
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to:   Optional[str] = Query(None, description="YYYY-MM-DD"),
):
    # 値が無ければデフォルト30日
    frm = _parse_date_ymd(date_from)
    to  = _parse_date_ymd(date_to)
    if frm is None or to is None:
        frm, to, from_s, to_s = _normalize_range(frm, to)
    else:
        frm, to, from_s, to_s = _normalize_range(frm, to)
    return await pdca_summary_data(from_date=from_s, to_date=to_s)

@router.get("/api/summary_timeseries", include_in_schema=False)
async def api_summary_timeseries_legacy(
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to:   Optional[str] = Query(None, description="YYYY-MM-DD"),
):
    # 当面は /summary/data と同形を返す
    frm = _parse_date_ymd(date_from)
    to  = _parse_date_ymd(date_to)
    if frm is None or to is None:
        frm, to, from_s, to_s = _normalize_range(frm, to)
    else:
        frm, to, from_s, to_s = _normalize_range(frm, to)
    return await pdca_summary_data(from_date=from_s, to_date=to_s)
