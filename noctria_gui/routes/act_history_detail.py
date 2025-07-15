#!/usr/bin/env python3
# coding: utf-8

"""
📄 Veritas 昇格ログ詳細ルート
- /act-history/detail?strategy_name=xxx にて詳細ログ表示
"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.core.path_config import GUI_TEMPLATES_DIR
from noctria_gui.services import act_log_service

router = APIRouter()
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))


@router.get("/act-history/detail", response_class=HTMLResponse)
async def show_detail_page(
    request: Request,
    strategy_name: str = Query(...),
):
    """
    📋 指定戦略の昇格ログ詳細を表示
    """
    log = act_log_service.get_log_by_strategy(strategy_name)
    if not log:
        return templates.TemplateResponse("not_found.html", {
            "request": request,
            "message": f"戦略 '{strategy_name}' の昇格ログが見つかりませんでした。"
        })

    return templates.TemplateResponse("act_history_detail.html", {
        "request": request,
        "log": log
    })
