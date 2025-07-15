#!/usr/bin/env python3
# coding: utf-8

"""
📊 Tag Scoreboard Route (v2.0)
- タグ別の統計情報を表形式で表示
- ソートキー指定に対応（件数・勝率・DD）
"""

import logging
from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# --- 王国の基盤モジュールをインポート ---
# ✅ 修正: path_config.pyのリファクタリングに合わせて、正しい変数名をインポート
from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR
from src.noctria_gui.services import statistics_service

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

router = APIRouter(tags=["scoreboard"])
# ✅ 修正: 正しい変数名を使用
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


@router.get("/statistics/scoreboard", response_class=HTMLResponse)
async def statistics_scoreboard(
    request: Request,
    sort: str = Query(default="count", regex="^(count|avg_win|avg_dd)$")
):
    """
    📊 タグ別統合スコアボードを表示
    - `sort` クエリで降順ソート対象を指定可能
    """
    logging.info(f"タグ別スコアボードの表示要求を受理しました。ソートキー: {sort}")
    try:
        all_logs = statistics_service.load_all_logs()
        tag_stats = statistics_service.aggregate_by_tag(all_logs)
        logging.info(f"{len(tag_stats)}件のタグについて集計が完了しました。")
    except Exception as e:
        logging.error(f"スコアボードの集計中にエラーが発生しました: {e}", exc_info=True)
        # エラーが発生した場合は、テンプレート側でエラーメッセージを表示させることも可能
        # ここでは空のデータを渡して、テンプレート側で「データなし」と表示させる
        tag_stats = {}
        # raise HTTPException(status_code=500, detail="統計データの集計中にエラーが発生しました。")

    # ✅ リスト化＆ソート
    try:
        # 'avg_win' と 'count' は大きい方が良いので降順、'avg_dd' は小さい方が良いので昇順
        reverse_sort = sort != 'avg_dd'
        
        sorted_tags = sorted(
            tag_stats.items(),
            key=lambda item: item[1].get(sort, 0), # getの第二引数でキーが存在しない場合に備える
            reverse=reverse_sort
        )
    except Exception as e:
        logging.error(f"タグ統計のソート中にエラーが発生しました: {e}", exc_info=True)
        sorted_tags = []

    return templates.TemplateResponse("statistics_scoreboard.html", {
        "request": request,
        "tag_stats": sorted_tags,
        "sort_key": sort
    })
