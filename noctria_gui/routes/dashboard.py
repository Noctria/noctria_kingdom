#!/usr/bin/env python3
# coding: utf-8

"""
👑 Central Governance Dashboard Route (v2.1)
- 王国の主要な統計情報と予測分析を統合表示する。
"""

import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR
# from src.noctria_gui.services import dashboard_service # 今後サービス層で整理可

# ロガー設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

@router.get("/", response_class=HTMLResponse)
async def dashboard_view(request: Request):
    """
    GET /dashboard - 中央統治ダッシュボードを表示する。
    """
    logging.info("中央統治ダッシュボードの表示要求を受理しました。")

    try:
        # 実装例: サービス層からリアルタイムで統計・予測値を集約
        # from src.noctria_gui.services.dashboard_service import get_dashboard_data
        # dashboard_data = get_dashboard_data()
        
        # --- デモ用ダミーデータ（実運用では上記関数から取得） ---
        stats_data = {
            "avg_win_rate": 57.1,
            "promoted_count": 8,
            "pushed_count": 15,
            "oracle_metrics": {"RMSE": 0.0342}
        }
        forecast_data = [
            {"date": "2025-07-16", "forecast": 150.12, "lower": 149.5, "upper": 150.9},
            {"date": "2025-07-17", "forecast": 150.38, "lower": 149.8, "upper": 151.1},
        ]
        dashboard_data = {"stats": stats_data, "forecast": forecast_data}
        # -------------------------------------------------------

        logging.info("ダッシュボード用のデータ集計が完了しました。")
    except Exception as e:
        logging.error(f"ダッシュボードデータの取得中にエラーが発生: {e}", exc_info=True)
        dashboard_data = {
            "stats": {"oracle_metrics": {}},
            "forecast": []
        }

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": dashboard_data.get("stats", {}),
        "forecast": dashboard_data.get("forecast", [])
    })
