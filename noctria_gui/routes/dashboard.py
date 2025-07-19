#!/usr/bin/env python3
# coding: utf-8

"""
👑 Central Governance Dashboard Route (v2.4)
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
    logging.info("📥 ダッシュボード表示要求を受理しました")

    # ✅ 初期統計データ（将来はDB/ログ解析ベースに移行）
    stats_data = {
        "avg_win_rate": 57.1,
        "promoted_count": 8,
        "pushed_count": 15,
        "oracle_metrics": {}
    }
    forecast_data = []

    try:
        oracle = PrometheusOracle()

        # ✅ 予測データ取得
        prediction = oracle.predict()
        if isinstance(prediction, list):
            forecast_data = prediction
        else:
            logging.warning("⚠️ oracle.predict() の結果がリストではありません。空として処理します。")
            forecast_data = []

        # ✅ メトリクス取得（存在する場合のみ）
        if hasattr(oracle, "get_metrics"):
            stats_data["oracle_metrics"] = oracle.get_metrics()

        logging.info(f"✅ 予測データ件数: {len(forecast_data)}")
        logging.info(f"✅ oracle_metrics: {stats_data['oracle_metrics']}")

    except Exception as e:
        logging.error(f"❌ PrometheusOracle のデータ取得中にエラーが発生: {e}", exc_info=True)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats_data,
        "forecast": forecast_data
    })
