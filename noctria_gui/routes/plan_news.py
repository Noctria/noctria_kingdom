# noctria_gui/routes/plan_news.py
# -*- coding: utf-8 -*-
"""
Plan News 画面 & API ルーター

用途:
- /plan/news                 : HTML（Chart.js）でニュース時系列/イベント影響を可視化
- /api/plan/news_timeline    : JSON（ニュース件数・センチメントの時系列）
- /api/plan/event_impact     : JSON（特定 event_tag の前後ウィンドウ平均）

ポイント:
- テンプレートは request.app.state.jinja_env に載っている前提（main.pyで登録済み）
- 例外時は {"error": "...", "trace": "..."} を 500 で返す（デバッグしやすさ優先）
- start/end は -30〜30 でバリデーション。start > end の場合は 400 を返す
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from jinja2 import TemplateNotFound
import traceback

from noctria_gui.services.plan_news_service import (
    fetch_news_timeline,
    fetch_event_impact,
)

router = APIRouter(tags=["plan-news"])


# -----------------------------
# HTML ページ
# -----------------------------
@router.get("/plan/news", response_class=HTMLResponse, include_in_schema=False)
async def plan_news_page(
    request: Request,
    asset: str = Query(..., description="例: USDJPY"),
    event_tag: Optional[str] = Query(None, description="例: CPI, FOMC, BOJ"),
) -> HTMLResponse:
    """
    ニュース可視化ページ（Chart.js）。
    - 上段: News Timeline (/api/plan/news_timeline)
    - 下段: Event Impact   (/api/plan/event_impact)
    """
    # main.py が templates.env を app.state.jinja_env に公開済み
    env = getattr(request.app.state, "jinja_env", None)
    if env is None:
        # フォールバック: 分かりやすいメッセージだけ返す
        html = (
            "<h2>Template engine (jinja_env) is not available.</h2>"
            "<p>main.py で Jinja2 の初期化が行われているか確認してください。</p>"
        )
        return HTMLResponse(html, status_code=500)

    try:
        tmpl = env.get_template("plan_news.html")
    except TemplateNotFound:
        # ここで 404 扱いにする（存在しないテンプレート）
        raise HTTPException(status_code=404, detail="template 'plan_news.html' not found")

    html = tmpl.render(request=request, asset=asset, event_tag=event_tag)
    return HTMLResponse(html)


# -----------------------------
# API: News timeline
# -----------------------------
@router.get(
    "/api/plan/news_timeline",
    summary="ニュースの件数・センチメントの時系列（ラベルは日付）",
)
def api_news_timeline(
    asset: str = Query(..., description="例: USDJPY"),
    date_from: Optional[str] = Query(
        None, description="YYYY-MM-DD（含む）。指定がなければ全期間"
    ),
    date_to: Optional[str] = Query(
        None, description="YYYY-MM-DD（含む）。指定がなければ全期間"
    ),
):
    try:
        data = fetch_news_timeline(asset=asset, date_from=date_from, date_to=date_to)
        return JSONResponse(data)
    except Exception as e:
        tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        return JSONResponse(
            {"error": f"{type(e).__name__}: {e}", "trace": tb}, status_code=500
        )


# -----------------------------
# API: Event impact
# -----------------------------
@router.get(
    "/api/plan/event_impact",
    summary="特定イベント（event_tag）前後の平均件数・平均センチメント",
)
def api_event_impact(
    asset: str = Query(..., description="例: USDJPY"),
    event_tag: str = Query(..., description="例: CPI, FOMC, BOJ"),
    start: int = Query(-3, ge=-30, le=30, description="イベント相対日（開始, 例:-3）"),
    end: int = Query(3, ge=-30, le=30, description="イベント相対日（終了, 例:3）"),
    date_from: Optional[str] = Query(
        None, description="YYYY-MM-DD（含む）。指定がなければ全期間"
    ),
    date_to: Optional[str] = Query(
        None, description="YYYY-MM-DD（含む）。指定がなければ全期間"
    ),
):
    if start > end:
        raise HTTPException(status_code=400, detail="start は end 以下である必要があります")

    try:
        data = fetch_event_impact(
            event_tag=event_tag,
            asset=asset,
            window=(start, end),
            date_from=date_from,
            date_to=date_to,
        )
        return JSONResponse(data)
    except Exception as e:
        tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        return JSONResponse(
            {"error": f"{type(e).__name__}: {e}", "trace": tb}, status_code=500
        )
