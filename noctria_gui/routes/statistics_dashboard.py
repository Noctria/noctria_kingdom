#!/usr//bin/env python3
# coding: utf-8

"""
📊 /statistics/dashboard - 戦略統計HUDダッシュボード画面
"""
import logging  # ✅ 修正: ロギング機能をインポート
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR

# サービス層の利用は任意
try:
    from noctria_gui.services.statistics_service import get_strategy_statistics
except ImportError:
    def get_strategy_statistics():
        # 仮ダミーデータ
        return {
            "num_strategies": 10,
            "avg_win_rate": 58.4,
            "avg_drawdown": 11.3,
        }

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


@router.get("/dashboard", response_class=HTMLResponse)
async def statistics_dashboard(request: Request):
    """
    HUDスタイル統計ダッシュボード画面を表示
    """
    # ✅ 修正: try...exceptブロックで囲み、エラーを確実にログに出力
    try:
        stats = get_strategy_statistics()
    except Exception as e:
        # エラーが発生した場合は、詳細をログに出力
        logging.error(f"Failed to get strategy statistics: {e}", exc_info=True)
        # テンプレート側でエラーにならないよう、空の辞書を渡す
        stats = {}

    return templates.TemplateResponse("statistics_dashboard.html", {
        "request": request,
        "stats": stats,
    })
