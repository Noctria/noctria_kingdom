# =====================================================================
# Noctria Kingdom — Plan News Routes
# 用途:
#   - /plan/news               : HUDテンプレ (plan_news.html) を返すHTMLルート
#   - /api/plan/news_timeline  : 日次ニュース件数/感情のタイムライン (JSON)
#   - /api/plan/event_impact   : イベント相対ウィンドウの影響 (JSON)
#
# これが必要な理由:
#   - 画面表示とAPIをひとつの機能単位で完結し、既存ルート群に干渉しない。
#   - 既存 main/app_main と同様の登録方法で、1行追加で機能を有効化できる。
# =====================================================================

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from .app_main import get_templates  # 既存のテンプレ取得関数があれば流用
from noctria_gui.services.plan_news_service import (
    fetch_event_impact,
    fetch_news_timeline,
)

router = APIRouter(prefix="", tags=["Plan News"])

def _templates() -> Jinja2Templates:
    try:
        return get_templates()
    except Exception:
        return Jinja2Templates(directory="noctria_gui/templates")

@router.get("/plan/news", response_class=HTMLResponse)
def plan_news_page(
    request: Request,
    asset: str = Query(default="USDJPY"),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    event_tag: Optional[str] = Query(default="CPI"),
):
    return _templates().TemplateResponse(
        "plan_news.html",
        {
            "request": request,
            "page_title": "🗞 Plan News & Events",
            "asset": asset,
            "date_from": date_from,
            "date_to": date_to,
            "event_tag": event_tag,
        },
    )

@router.get("/api/plan/news_timeline")
def api_news_timeline(
    asset: str = Query(default="USDJPY"),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
):
    data = fetch_news_timeline(asset=asset, date_from=date_from, date_to=date_to)
    return JSONResponse(data)

@router.get("/api/plan/event_impact")
def api_event_impact(
    event_tag: str = Query(default="CPI"),
    asset: str = Query(default="USDJPY"),
    start: int = Query(default=-3),
    end: int = Query(default=3),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
):
    data = fetch_event_impact(
        event_tag=event_tag,
        asset=asset,
        window=(start, end),
        date_from=date_from,
        date_to=date_to,
    )
    return JSONResponse(data)
