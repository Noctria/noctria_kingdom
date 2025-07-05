#!/usr/bin/env python3
# coding: utf-8

"""
📁 Noctria Kingdom 統治ログ操作ルート
- 統治ログの一括CSV出力をGUIから起動可能に
"""

from fastapi import APIRouter
from fastapi.responses import FileResponse
from datetime import datetime
from pathlib import Path
import subprocess

from core.path_config import TOOLS_DIR

router = APIRouter()

@router.get("/logs/export-all")
async def export_all_governance_logs():
    """
    📤 統治ログをまとめてCSV出力し、ダウンロード提供
    """
    # ✅ スクリプトのフルパス
    script_path = TOOLS_DIR / "export_all_logs.py"

    # ✅ スクリプト実行
    result = subprocess.run(
        ["python3", str(script_path)],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"⚠️ スクリプト実行エラー:\n{result.stderr}")
        return {"error": "ログ出力に失敗しました"}

    # ✅ 最新ファイルの取得
    output_dir = TOOLS_DIR / "統治記録"
    latest_file: Path = max(output_dir.glob("*.csv"), key=lambda p: p.stat().st_mtime)

    return FileResponse(
        latest_file,
        filename=latest_file.name,
        media_type="text/csv"
    )
