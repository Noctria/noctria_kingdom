#!/usr/bin/env python3
# coding: utf-8

"""
👑 Central Governance Dashboard Route (v2.0)
- 王国の主要な統計情報と予測分析を統合表示する。
"""

import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# --- 王国の基盤モジュールをインポート ---
# ✅ 修正: path_config.pyのリファクタリングに合わせて、正しいパスと変数名をインポート
from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR
# from src.noctria_gui.services import dashboard_service # 将来的にダッシュボード専用サービスを導入する想定

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
# ✅ 修正: 正しい変数名を使用
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
@router.get("", response_class=HTMLResponse)
async def dashboard_view(request: Request):
    """
    GET /dashboard - 中央統治ダッシュボードを表示する。
    """
    logging.info("中央統治ダッシュボードの表示要求を受理しました。")
    
    try:
        # --- ここでダッシュボードサービスを呼び出し、データを取得する ---
        # from src.noctria_gui.services import dashboard_service
        # dashboard_data = dashboard_service.get_dashboard_data()
        # ----------------------------------------------------

        # (ダミー処理)
        # 実際の運用では、各サービスからデータを集約する
        stats_data = {
            "avg_win_rate": 57.1, "promoted_count": 8, "pushed_count": 15,
            "oracle_metrics": {"RMSE": 0.0342}
        }
        forecast_data = [
            {"date": "2025-07-16", "forecast": 150.12, "y_lower": 149.5, "y_upper": 150.9},
            {"date": "2025-07-17", "forecast": 150.38, "y_lower": 149.8, "y_upper": 151.1},
        ]
        dashboard_data = {"stats": stats_data, "forecast": forecast_data}
        # --- ここまでダミー処理 ---

        logging.info("ダッシュボード用のデータ集計が完了しました。")

    except Exception as e:
        logging.error(f"ダッシュボードデータの取得中にエラーが発生しました: {e}", exc_info=True)
        # エラー発生時は、テンプレートが壊れないように空のデータを渡す
        dashboard_data = {
            "stats": {"oracle_metrics": {}},
            "forecast": []
        }

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": dashboard_data.get("stats", {}),
        "forecast": dashboard_data.get("forecast", [])
    })

