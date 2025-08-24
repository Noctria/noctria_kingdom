# noctria_gui/routes/plan_news.py
from __future__ import annotations
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="", tags=["Plan News"])

def _templates() -> Jinja2Templates:
    """
    main の templates を再利用できるなら使い、無ければローカルの templates を使う。
    import は関数内に閉じて循環を避ける。
    """
    try:
        # main 側でフィルタや env を仕込んでいる場合はこちらを使う
        from noctria_gui.main import templates as main_templates  # type: ignore
        return main_templates
    except Exception:
        tpl_dir = Path(__file__).resolve().parents[1] / "templates"
        return Jinja2Templates(directory=str(tpl_dir))

@router.get("/plan/news", response_class=HTMLResponse)
def plan_news_page(
    request: Request,
    asset: str = Query(default="USDJPY"),
    event_tag: Optional[str] = Query(default="CPI"),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
):
    return _templates().TemplateResponse(
        "plan_news.html",
        {
            "request": request,
            "page_title": "🗞 Plan News & Events",
            "asset": asset,
            "event_tag": event_tag,
            "date_from": date_from,
            "date_to": date_to,
        },
    )

@router.get("/api/plan/news_timeline")
def api_news_timeline(
    asset: str = Query(default="USDJPY"),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
):
    try:
        from noctria_gui.services.plan_news_service import fetch_news_timeline
    except Exception as e:
        return JSONResponse(
            {"error": f"plan_news_service not available: {type(e).__name__}: {e}"},
            status_code=500,
        )
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
    try:
        from noctria_gui.services.plan_news_service import fetch_event_impact
    except Exception as e:
        return JSONResponse(
            {"error": f"plan_news_service not available: {type(e).__name__}: {e}"},
            status_code=500,
        )
    data = fetch_event_impact(
        event_tag=event_tag,
        asset=asset,
        window=(start, end),
        date_from=date_from,
        date_to=date_to,
    )
    return JSONResponse(data)
