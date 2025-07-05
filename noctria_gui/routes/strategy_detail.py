#!/usr/bin/env python3
# coding: utf-8

"""
📘 戦略詳細表示ルート
- 戦略名を指定して個別の統計・評価情報を表示
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from core.path_config import GUI_TEMPLATES_DIR
from noctria_gui.services import statistics_service

router = APIRouter()
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))


@router.get("/strategy/detail", response_class=HTMLResponse)
async def show_strategy_detail(request: Request, name: str):
    """
    📘 指定戦略名に一致する戦略詳細情報を表示
    """
    logs = statistics_service.load_all_statistics()

    # 戦略名でフィルタ
    matched = [log for log in logs if log.get("strategy") == name]

    if not matched:
        raise HTTPException(status_code=404, detail="該当戦略が見つかりません")

    strategy = matched[0]

    # タグがない場合でも空リストを補完
    strategy["tags"] = strategy.get("tags", [])

    return templates.TemplateResponse("strategy_detail.html", {
        "request": request,
        "strategy": strategy
    })
