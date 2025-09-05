#!/usr/bin/env python3
# coding: utf-8

"""
📌 Tag-Metric Ranking Route (v2.0)
- 各タグの勝率・最大ドローダウン・取引数・昇格率を比較しランキング表示
"""

import logging
from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# --- 王国の基盤モジュールをインポート ---
# ✅ 修正: path_config.pyのリファクタリングに合わせて、正しい変数名をインポート
from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR
from noctria_gui.services import statistics_service

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

router = APIRouter(tags=["tag-ranking"])
# ✅ 修正: 正しい変数名を使用
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


@router.get("/statistics/tag-ranking", response_class=HTMLResponse)
async def tag_ranking_dashboard(
    request: Request,
    sort_by: str = Query(default="promotion_rate", description="ソートキー"),
    order: str = Query(default="desc", regex="^(asc|desc)$")
):
    """
    📌 タグ × 指標のランキングページを表示
    """
    logging.info(f"タグランキングの表示要求を受理しました。ソートキー: {sort_by}, 順序: {order}")
    try:
        # ✅ 全ログ取得 & タグ別集計
        all_logs = statistics_service.load_all_logs()
        # aggregate_by_tagが辞書を返すと仮定し、値のリストを取得
        tag_stats_dict = statistics_service.aggregate_by_tag(all_logs)
        tag_stats_list = list(tag_stats_dict.values())
        logging.info(f"{len(tag_stats_list)}件のタグについて集計が完了しました。")

        # ✅ ソート（昇順 or 降順）
        # max_drawdownのみ昇順（値が小さい方が良い）、他は降順がデフォルト
        if order == 'desc':
            reverse_sort = sort_by != 'max_drawdown'
        else: # order == 'asc'
            reverse_sort = sort_by == 'max_drawdown'

        tag_stats_list.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse_sort)

    except Exception as e:
        logging.error(f"タグランキングの集計中にエラーが発生しました: {e}", exc_info=True)
        tag_stats_list = []
        # raise HTTPException(status_code=500, detail="統計データの集計中にエラーが発生しました。")

    return templates.TemplateResponse("statistics_tag_ranking.html", {
        "request": request,
        "tag_stats": tag_stats_list,
        "current_sort": sort_by,
        "current_order": order,
    })
