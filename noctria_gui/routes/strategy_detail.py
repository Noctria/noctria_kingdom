#!/usr/bin/env python3
# coding: utf-8

"""
📘 Strategy Detail Route (v2.0)
- 戦略名を指定して個別の統計・評価情報を表示
"""

import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List

# --- 王国の基盤モジュールをインポート ---
# ✅ 修正: path_config.pyのリファクタリングに合わせて、正しい変数名をインポート
from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR
from noctria_gui.services import statistics_service

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

# ✅ 修正: ルーターのprefixを/strategiesに統一
router = APIRouter(prefix="/strategies", tags=["strategy-detail"])
# ✅ 修正: 正しい変数名を使用
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


@router.get("/detail/{strategy_name}", response_class=HTMLResponse)
async def show_strategy_detail(request: Request, strategy_name: str):
    """
    📘 指定された戦略名に一致する戦略詳細情報を表示する。
    """
    logging.info(f"戦略詳細の表示要求を受理しました。対象戦略: {strategy_name}")
    try:
        logs = statistics_service.load_all_statistics()

        # 指定戦略の取得
        matched_strategy = next((log for log in logs if log.get("strategy") == strategy_name), None)
        
        if not matched_strategy:
            logging.warning(f"指定された戦略が見つかりませんでした: {strategy_name}")
            raise HTTPException(status_code=404, detail=f"戦略『{strategy_name}』は見つかりません。")

        # タグの補完（None → []）
        current_tags = matched_strategy.get("tags", [])
        matched_strategy["tags"] = current_tags

        # 比較用：同じタグを持つ別戦略（最大4件）
        related_strategies = [
            s for s in logs
            if s.get("strategy") != strategy_name and
               any(tag in s.get("tags", []) for tag in current_tags)
        ][:4]
        
        logging.info(f"関連戦略を{len(related_strategies)}件発見しました。")

    except Exception as e:
        logging.error(f"戦略詳細の取得中にエラーが発生しました: {e}", exc_info=True)
        # エラーページを表示するか、エラーメッセージ付きのテンプレートを返す
        raise HTTPException(status_code=500, detail="戦略詳細情報の取得中に内部エラーが発生しました。")

    return templates.TemplateResponse("strategy_detail.html", {
        "request": request,
        "strategy": matched_strategy,
        "related_strategies": related_strategies
    })
