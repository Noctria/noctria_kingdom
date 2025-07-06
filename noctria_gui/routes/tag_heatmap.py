#!/usr/bin/env python3
# coding: utf-8

"""
📊 タグ × 指標のヒートマップ表示ルート
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from collections import defaultdict
import statistics as stats

from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR
from noctria_gui.services.tag_summary_service import load_all_tagged_statistics

router = APIRouter(tags=["tag-heatmap"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


@router.get("/strategies/tag-heatmap", response_class=HTMLResponse)
async def show_tag_heatmap(request: Request):
    """
    📊 タグごとの平均勝率・DD・取引数のヒートマップ表示
    """
    all_stats = load_all_tagged_statistics()

    # 集計構造: {tag: {"win_rate": [...], "drawdown": [...], "trades": [...]} }
    tag_metrics = defaultdict(lambda: {"win_rate": [], "drawdown": [], "trades": []})

    for stat in all_stats:
        tags = stat.get("tags", [])
        for tag in tags:
            tag_metrics[tag]["win_rate"].append(stat.get("win_rate", 0))
            tag_metrics[tag]["drawdown"].append(stat.get("max_drawdown", 0))
            tag_metrics[tag]["trades"].append(stat.get("num_trades", 0))

    # 平均算出
    tag_summary = []
    for tag, metrics in tag_metrics.items():
        tag_summary.append({
            "tag": tag,
            "avg_win_rate": round(stats.mean(metrics["win_rate"]), 2) if metrics["win_rate"] else 0,
            "avg_drawdown": round(stats.mean(metrics["drawdown"]), 2) if metrics["drawdown"] else 0,
            "avg_trades": round(stats.mean(metrics["trades"]), 2) if metrics["trades"] else 0,
        })

    # ソート（例：勝率降順）
    tag_summary.sort(key=lambda x: x["avg_win_rate"], reverse=True)

    return templates.TemplateResponse("strategies/tag_heatmap.html", {
        "request": request,
        "tag_summary": tag_summary
    })
