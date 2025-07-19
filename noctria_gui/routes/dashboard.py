#!/usr/bin/env python3
# coding: utf-8

"""
👑 Central Governance Dashboard Route (v2.3)
- 王国の主要な統計情報と予測分析を統合表示する。
"""

import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR
from strategies.prometheus_oracle import PrometheusOracle  # ✅ 予測AIをインポート

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

    stats_data = {
        "avg_win_rate": 57.1,       # 🧪 ダミーデータ（将来的に動的に差し替え）
        "promoted_count": 8,
        "pushed_count": 15,
        "oracle_metrics": {}
    }
    forecast_data = []

    try:
        oracle = PrometheusOracle()
        forecast_data = oracle.predict()
        stats_data["oracle_metrics"] = oracle.get_metrics()
        logging.info("✅ PrometheusOracle からのデータ取得に成功しました。")

    except Exception as e:
        logging.error(f"PrometheusOracle のデータ取得中にエラーが発生: {e}", exc_info=True)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats_data,
        "forecast": forecast_data
    })
