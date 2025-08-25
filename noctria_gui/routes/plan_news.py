# noctria_gui/routes/plan_news.py
from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional

from noctria_gui.services.plan_news_service import (
    fetch_news_timeline,
    fetch_event_impact,
)

router = APIRouter(tags=["plan-news"])

# ---------- ページ（HTML） ----------
@router.get("/plan/news", response_class=HTMLResponse, include_in_schema=False)
async def plan_news_page(
    request: Request,
    asset: str = Query(..., description="e.g. USDJPY"),
    event_tag: Optional[str] = Query(None, description="e.g. CPI, FOMC, BOJ"),
):
    # main.py が Jinja2 環境を app.state に公開済み
    env = request.app.state.jinja_env
    tmpl = env.get_template("plan_news.html")
    html = tmpl.render(request=request, asset=asset, event_tag=event_tag)
    return HTMLResponse(html)

# ---------- API（既存） ----------
@router.get("/api/plan/news_timeline")
def api_news_timeline(
    asset: str = Query(...),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    data = fetch_news_timeline(asset=asset, date_from=date_from, date_to=date_to)
    return JSONResponse(data)

@router.get("/api/plan/event_impact")
def api_event_impact(
    asset: str = Query(...),
    event_tag: str = Query(...),
    start: int = Query(-3),
    end: int = Query(3),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    data = fetch_event_impact(event_tag, asset, (start, end), date_from, date_to)
    return JSONResponse(data)
