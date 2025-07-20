#!/usr/bin/env python3
# coding: utf-8

"""
👑 Central Governance Dashboard Route (v2.7)
- 王国の主要な統計情報と予測分析を統合表示する。
"""

import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR
from strategies.prometheus_oracle import PrometheusOracle

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
async def dashboard_view(request: Request):
    logging.info("📥 ダッシュボード表示要求を受理しました")

    stats_data = {
        "avg_win_rate": 57.1,
        "promoted_count": 8,
        "pushed_count": 15,
        "oracle_metrics": {}
    }
    forecast_data = []

    try:
        oracle = PrometheusOracle()
        logging.info("📤 oracle.predict() 実行")
        prediction = oracle.predict()
        logging.info(f"🧾 predict() 結果タイプ: {type(prediction)}, 内容例: {prediction[:1] if isinstance(prediction, list) else prediction}")

        if isinstance(prediction, list) and all(isinstance(p, dict) for p in prediction):
            forecast_data = prediction
        else:
            logging.warning("⚠️ oracle.predict() の結果形式が不正です。")

        if not forecast_data:
            logging.warning("⚠️ 予測データが空です。Chart.js が描画をスキップする可能性があります。")
            logging.warning(f"📭 予測データ詳細: {prediction}")

        if hasattr(oracle, "get_metrics"):
            stats_data["oracle_metrics"] = oracle.get_metrics()

        logging.info(f"✅ 予測データ件数: {len(forecast_data)}")
        logging.debug(f"📊 forecast_data preview: {forecast_data[:2]}")
        logging.info(f"✅ oracle_metrics: {stats_data['oracle_metrics']}")

        # oracle.write_forecast_json(n_days=14)  # 必要に応じてファイル出力

    except Exception as e:
        logging.error(f"❌ PrometheusOracle のデータ取得中にエラーが発生: {e}", exc_info=True)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats_data,
        "forecast": forecast_data
    })
