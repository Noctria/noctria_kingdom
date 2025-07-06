#!/usr/bin/env python3
# coding: utf-8

"""
🧭 Noctria Kingdom ダッシュボードルート
- 王国統治の全体概要を表示
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """
    🧭 Noctria Kingdom 統治ダッシュボード
    - 各統治機能へのリンクと概要表示
    """
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
    })
