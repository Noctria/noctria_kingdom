#!/usr/bin/env python3
# coding: utf-8

"""
🔥 タグ別ヒートマップ表示ルート
- タグと指標（勝率・DD・取引数）をヒートマップ表示
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from noctria_gui.services import statistics_service
from core.path_config import GUI_TEMPLATES_DIR

router = APIRouter(tags=["tag-heatmap"])
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))


@router.get("/tag-heatmap", response_class=HTMLResponse)
async def tag_heatmap(request: Request):
    """
    🔥 タグ × 指標 のヒートマップを表示
    """
    try:
        all_logs = statistics_service.load_all_logs()
        tag_stats = statistics_service.aggregate_by_tag(all_logs)
    except Exception as e:
        tag_stats = []
        print(f"[tag_heatmap] ⚠️ 集計失敗: {e}")

    return templates.TemplateResponse("tag_heatmap.html", {
        "request": request,
        "tag_stats": tag_stats
    })
