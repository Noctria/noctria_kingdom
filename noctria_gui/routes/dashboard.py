#!/usr/bin/env python3
# coding: utf-8

"""
📊 /dashboard - 中央統治ダッシュボード
- 各種統計と予測分析を統合表示
"""
import logging  # ✅ 修正: ロギング機能をインポート
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# 両方のURL（/dashboard, /dashboard/）で呼び出せるようにする
@router.get("/", response_class=HTMLResponse)
@router.get("", response_class=HTMLResponse)
async def dashboard_view(request: Request):
    # ✅ 修正: この関数が実行されたことをログに出力
    logging.info("--- dashboard_view is being executed ---")

    # 必要な統計データ
    stats = {
        "avg_win_rate": 57.1,
        "avg_drawdown": 13.9,
        "total_strategies": 14,
        "promoted_count": 8,
        "pushed_count": 15,
        "oracle_metrics": {
            "RMSE": 0.0342,
            "MAE": 0.0125,
            "MAPE": 2.81,
        },
    }
    # 予測データ
    forecast = [
        {"date": "2025-07-15", "forecast": 150.12, "y_lower": 149.5, "y_upper": 150.9},
        {"date": "2025-07-16", "forecast": 150.38, "y_lower": 149.8, "y_upper": 151.1},
    ]

    # ✅ 修正: テンプレートに渡す直前のデータ（コンテキスト）をログに出力
    context = {
        "request": request,
        "stats": stats,
        "forecast": forecast if forecast is not None else [],
    }
    logging.info(f"Context being passed to template: {context}")

    return templates.TemplateResponse("dashboard.html", context)
