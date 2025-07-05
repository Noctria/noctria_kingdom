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
from noctria_gui.services import statistics_service, tag_summary_service

router = APIRouter()
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))


@router.get("/strategy/detail", response_class=HTMLResponse)
async def show_strategy_detail(request: Request, name: str):
    """
    📘 指定戦略名に一致する戦略詳細情報を表示
    """
    logs = statistics_service.load_all_statistics()

    # 指定戦略の取得
    matched = [log for log in logs if log.get("strategy") == name]
    if not matched:
        raise HTTPException(status_code=404, detail="該当戦略が見つかりません")
    strategy = matched[0]

    # タグの補完（None → []）
    strategy["tags"] = strategy.get("tags", [])

    # 比較用：同じタグを持つ別戦略（最大4件）
    related_strategies = [
        s for s in logs
        if s.get("strategy") != name and
           any(tag in s.get("tags", []) for tag in strategy["tags"])
    ][:4]

    return templates.TemplateResponse("strategy_detail.html", {
        "request": request,
        "strategy": strategy,
        "related_strategies": related_strategies
    })
