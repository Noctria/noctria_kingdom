#!/usr/bin/env python3
# coding: utf-8

"""
📂 タグ別戦略詳細ルート
- 指定されたタグに紐づく戦略一覧を表示する
- CSVエクスポートも対応
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
from pathlib import Path
import csv

from noctria_gui.services import tag_summary_service
from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, TOOLS_DIR

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


@router.get("/tag-summary/detail", response_class=HTMLResponse)
async def show_tag_detail(request: Request, tag: str):
    """
    📂 指定タグに紐づく戦略一覧を表示
    - GET /tag-summary/detail?tag=xxx
    """
    try:
        all_logs = tag_summary_service.load_all_statistics()
        filtered = [s for s in all_logs if tag in s.get("tags", [])]
    except Exception as e:
        return HTMLResponse(
            content=f"<h2>⚠️ データの読み込みに失敗しました: {e}</h2>",
            status_code=500
        )

    return templates.TemplateResponse("tag_detail.html", {
        "request": request,
        "tag": tag,
        "strategies": filtered,
    })


@router.get("/tag-summary/detail/export")
async def export_tag_detail_csv(tag: str):
    """
    📤 指定タグの戦略一覧をCSV出力
    - GET /tag-summary/detail/export?tag=xxx
    """
    try:
        all_logs = tag_summary_service.load_all_statistics()
        filtered = [s for s in all_logs if tag in s.get("tags", [])]
    except Exception as e:
        return {"error": f"データの取得に失敗しました: {e}"}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{tag}_strategies_{timestamp}.csv"
    output_path = TOOLS_DIR / filename

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "戦略名", "勝率", "最大DD", "取引回数", "タグ", "評価日時"
        ])
        for s in filtered:
            writer.writerow([
                s.get("strategy", ""),
                s.get("win_rate", ""),
                s.get("max_drawdown", ""),
                s.get("num_trades", ""),
                ", ".join(s.get("tags", [])),
                s.get("timestamp", ""),
            ])

    return FileResponse(
        output_path,
        filename=filename,
        media_type="text/csv"
    )
