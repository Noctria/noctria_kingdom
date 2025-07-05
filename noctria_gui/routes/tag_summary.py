#!/usr/bin/env python3
# coding: utf-8

"""
📊 タグ別統計ダッシュボードルート
- Veritas戦略のタグ分類統計を表示
- CSVエクスポート機能付き
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
from pathlib import Path
import csv

from core.path_config import GUI_TEMPLATES_DIR, TOOLS_DIR
from noctria_gui.services import tag_summary_service

# ✅ ルーターとテンプレート設定
router = APIRouter()
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))


@router.get("/tag-summary", response_class=HTMLResponse)
async def show_tag_summary(request: Request):
    """
    📊 タグ別戦略統計ページ
    - タグごとに分類された戦略群を統計集計し表示
    """
    all_logs = tag_summary_service.load_all_statistics()
    summary_data = tag_summary_service.summarize_by_tag(all_logs)

    return templates.TemplateResponse("tag_summary.html", {
        "request": request,
        "summary_data": summary_data
    })


@router.get("/tag-summary/export")
async def export_tag_summary_csv():
    """
    📤 タグ統計のCSVエクスポート
    - 出力先: TOOLS_DIR/tag_summary_yyyymmdd_HHMMSS.csv
    """
    all_logs = tag_summary_service.load_all_statistics()
    summary_data = tag_summary_service.summarize_by_tag(all_logs)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = TOOLS_DIR / f"tag_summary_{timestamp}.csv"

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["タグ", "戦略数", "平均勝率", "平均取引数", "平均最大DD", "戦略例"])
        for item in summary_data:
            writer.writerow([
                item["tag"],
                item["strategy_count"],
                item["average_win_rate"],
                item["average_trade_count"],
                item["average_max_drawdown"],
                ", ".join(item["sample_strategies"])
            ])

    return FileResponse(
        output_path,
        filename=output_path.name,
        media_type="text/csv"
    )
