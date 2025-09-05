#!/usr/bin/env python3
# coding: utf-8

"""
📁 Noctria Kingdom 統治ログ操作ルート
- 統治ログの一括CSV出力やGUIダッシュボード表示を提供
"""

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse
from datetime import datetime
from pathlib import Path
import subprocess

from src.core.path_config import TOOLS_DIR
from fastapi.templating import Jinja2Templates

# 📁 テンプレート（logs_dashboard.html）読み込み用
TEMPLATES_DIR = TOOLS_DIR.parent / "noctria_gui" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()

# ================================
# 📥 統治ログの一括CSVダウンロード
# ================================
@router.get("/logs/export-all")
async def export_all_governance_logs():
    """
    📤 統治ログをまとめてCSV出力し、ダウンロード提供
    """
    script_path = TOOLS_DIR / "export_all_logs.py"

    try:
        result = subprocess.run(
            ["python3", str(script_path)],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"⚠️ スクリプト実行エラー:\n{e.stderr}")
        return HTMLResponse(
            content="<h3>⚠️ 統治ログの出力に失敗しました</h3>",
            status_code=500
        )

    output_dir = TOOLS_DIR / "統治記録"
    try:
        latest_file: Path = max(output_dir.glob("*.csv"), key=lambda p: p.stat().st_mtime)
    except ValueError:
        return HTMLResponse(
            content="<h3>⚠️ 出力ファイルが存在しません</h3>",
            status_code=404
        )

    return FileResponse(
        latest_file,
        filename=latest_file.name,
        media_type="text/csv"
    )


# ================================
# 🖥 統治ログダッシュボードのGUI表示
# ================================
@router.get("/logs-dashboard", response_class=HTMLResponse)
async def show_logs_dashboard(request: Request):
    """
    🖥 統治ログダッシュボード画面（GUI）
    """
    return templates.TemplateResponse("logs_dashboard.html", {"request": request})
