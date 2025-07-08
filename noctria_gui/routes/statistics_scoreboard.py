#!/usr/bin/env python3
# coding: utf-8

"""
📊 タグ統合スコアボード表示ルート
- タグ別の統計情報を表形式で表示
- ソートキー指定に対応（件数・勝率・DD）
"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from core.path_config import GUI_TEMPLATES_DIR
from noctria_gui.services import statistics_service

router = APIRouter(tags=["scoreboard"])
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))


@router.get("/statistics/scoreboard", response_class=HTMLResponse)
async def statistics_scoreboard(
    request: Request,
    sort: str = Query(default="count", regex="^(count|avg_win|avg_dd)$")
):
    """
    📊 タグ別統合スコアボードを表示
    - `sort` クエリで降順ソート対象を指定可能
    """
    try:
        all_logs = statistics_service.load_all_logs()
        tag_stats = statistics_service.aggregate_by_tag(all_logs)
    except Exception as e:
        print(f"[statistics_scoreboard] ⚠️ 集計失敗: {e}")
        tag_stats = []

    # ✅ リスト化＆ソート
    sorted_tags = sorted(
        tag_stats.items(),
        key=lambda item: item[1].get(sort) or 0,
        reverse=True
    )

    return templates.TemplateResponse("statistics_scoreboard.html", {
        "request": request,
        "tag_stats": sorted_tags,
        "sort_key": sort
    })
