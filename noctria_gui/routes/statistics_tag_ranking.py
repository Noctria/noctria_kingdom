#!/usr/bin/env python3
# coding: utf-8

"""
📌 タグ × 指標ランキングルート
- 各タグの勝率・最大ドローダウン・取引数・昇格率を比較しランキング表示
"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from core.path_config import GUI_TEMPLATES_DIR
from noctria_gui.services import statistics_service

router = APIRouter(tags=["tag-ranking"])
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))


@router.get("/statistics/tag-ranking", response_class=HTMLResponse)
async def tag_ranking_dashboard(
    request: Request,
    sort_by: str = Query(default="promotion_rate", description="ソートキー（例: win_rate, max_drawdown, num_trades, promotion_rate）"),
    order: str = Query(default="desc", description="並び順: asc または desc")
):
    """
    📌 タグ × 指標のランキングページを表示
    """
    try:
        # ✅ 全ログ取得 & タグ別集計（昇格率含む）
        all_logs = statistics_service.load_all_logs()
        tag_stats = statistics_service.aggregate_by_tag(all_logs)

        # ✅ ソート（昇順 or 降順）
        reverse = order == "desc"
        tag_stats.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)

    except Exception as e:
        tag_stats = []
        print(f"[tag_ranking_dashboard] ⚠️ 集計失敗: {e}")

    return templates.TemplateResponse("statistics_tag_ranking.html", {
        "request": request,
        "tag_stats": tag_stats,
        "current_sort": sort_by,
        "current_order": order,
    })
