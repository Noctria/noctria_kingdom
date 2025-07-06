#!/usr/bin/env python3
# coding: utf-8

"""
📌 タグ × 指標ランキングルート
- 各タグの勝率・最大ドローダウン・取引数を比較しランキング表示
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from core.path_config import GUI_TEMPLATES_DIR
from noctria_gui.services import statistics_service

router = APIRouter(tags=["tag-ranking"])
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))


@router.get("/statistics/tag-ranking", response_class=HTMLResponse)
async def tag_ranking_dashboard(request: Request):
    """
    📌 タグ × 指標のランキングページを表示
    """
    try:
        all_logs = statistics_service.load_all_logs()
        tag_stats = statistics_service.aggregate_by_tag(all_logs)
    except Exception as e:
        tag_stats = []
        print(f"[tag_ranking_dashboard] ⚠️ 集計失敗: {e}")

    return templates.TemplateResponse("statistics_tag_ranking.html", {
        "request": request,
        "tag_stats": tag_stats
    })
