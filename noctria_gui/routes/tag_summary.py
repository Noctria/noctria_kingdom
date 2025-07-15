#!/usr/bin/env python3
# coding: utf-8

"""
📊 Tag Summary Route (v2.0)
- Veritas戦略のタグ分類統計を表示
- CSVエクスポート機能付き
"""

import logging
import csv
import io
from datetime import datetime
from typing import List, Dict, Any

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

# --- 王国の基盤モジュールをインポート ---
# ✅ 修正: path_config.pyのリファクタリングに合わせて、正しい変数名をインポート
from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, TOOLS_DIR
from src.noctria_gui.services import tag_summary_service

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

# ✅ 修正: ルーターのprefixを/statisticsに統一
router = APIRouter(prefix="/statistics", tags=["tag-summary"])
# ✅ 修正: 正しい変数名を使用
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


# --- 依存性注入（DI）によるデータ集計ロジックの共通化 ---
def get_tag_summary_data() -> List[Dict[str, Any]]:
    """
    タグごとの統計データを生成する共通関数。
    """
    logging.info("タグ別統計の集計を開始します。")
    try:
        all_logs = tag_summary_service.load_all_statistics()
        summary_data = tag_summary_service.summarize_by_tag(all_logs)
        logging.info(f"{len(summary_data)}件のタグについて集計が完了しました。")
        return summary_data
    except Exception as e:
        logging.error(f"タグ別統計の集計中にエラーが発生しました: {e}", exc_info=True)
        # エラーが発生した場合は空のリストを返し、呼び出し元で処理する
        return []


# --- ルート定義 ---

@router.get("/tag-summary", response_class=HTMLResponse)
async def show_tag_summary(
    request: Request,
    summary_data: List[Dict[str, Any]] = Depends(get_tag_summary_data)
):
    """
    📊 タグ別戦略統計ページ
    - タグごとに分類された戦略群を統計集計し表示
    """
    return templates.TemplateResponse("tag_summary.html", {
        "request": request,
        "summary_data": summary_data
    })


@router.get("/tag-summary/export", response_class=StreamingResponse)
async def export_tag_summary_csv(
    summary_data: List[Dict[str, Any]] = Depends(get_tag_summary_data)
):
    """
    📤 タグ統計のCSVエクスポート
    """
    if not summary_data:
        raise HTTPException(status_code=404, detail="エクスポート対象のデータがありません。")

    output = io.StringIO()
    try:
        fieldnames = ["タグ", "戦略数", "平均勝率", "平均取引数", "平均最大DD", "戦略例"]
        writer = csv.writer(output)
        writer.writerow(fieldnames)
        
        for item in summary_data:
            writer.writerow([
                item.get("tag", "N/A"),
                item.get("strategy_count", 0),
                item.get("average_win_rate", "-"),
                item.get("average_trade_count", "-"),
                item.get("average_max_drawdown", "-"),
                ", ".join(item.get("sample_strategies", []))
            ])
    except Exception as e:
        logging.error(f"CSVの生成中にエラーが発生しました: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"CSV生成に失敗しました: {e}")

    output.seek(0)
    filename = f"tag_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
