#!/usr/bin/env python3
# coding: utf-8

"""
👑 Central Governance Dashboard Route (v2.8)
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
        logging.info(f"🧾 predict() 結果タイプ: {type(prediction)}, 内容例: {str(prediction)[:120]}")

        # DataFrameの場合はdict(list)化する
        if prediction is None:
            logging.warning("⚠️ oracle.predict() が None を返しました。")
            forecast_data = []
        elif isinstance(prediction, list):
            if all(isinstance(p, dict) for p in prediction):
                forecast_data = prediction
            else:
                logging.warning("⚠️ list型だがdictでない要素が含まれています。")
        elif hasattr(prediction, "to_dict"):  # DataFrameなど
            try:
                forecast_data = prediction.to_dict(orient="records")
            except Exception as df_e:
                logging.error(f"DataFrame->dict変換エラー: {df_e}")
        else:
            logging.warning("⚠️ 予測値の型が想定外。")

        if not forecast_data:
            logging.warning("⚠️ 予測データが空です。Chart.jsが描画をスキップします。")
            # ダミーデータ例（開発時用、不要なら消す）
            # forecast_data = [
            #     {"date": "2025-07-21", "forecast": 108.3, "lower": 106.8, "upper": 109.7},
            #     {"date": "2025-07-22", "forecast": 108.8, "lower": 107.2, "upper": 110.0}
            # ]
            logging.warning(f"📭 予測データ詳細: {prediction}")

        if hasattr(oracle, "get_metrics"):
            stats_data["oracle_metrics"] = oracle.get_metrics()

        logging.info(f"✅ 予測データ件数: {len(forecast_data)}")
        logging.debug(f"📊 forecast_data preview: {forecast_data[:2]}")
        logging.info(f"✅ oracle_metrics: {stats_data['oracle_metrics']}")

        # oracle.write_forecast_json(n_days=14)  # 必要に応じてファイル出力

    except Exception as e:
        logging.error(f"❌ PrometheusOracle のデータ取得中にエラーが発生: {e}", exc_info=True)
        # ダミーデータ例（開発時用、不要なら消す）
        # forecast_data = [
        #     {"date": "2025-07-21", "forecast": 108.3, "lower": 106.8, "upper": 109.7},
        #     {"date": "2025-07-22", "forecast": 108.8, "lower": 107.2, "upper": 110.0}
        # ]

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats_data,
        "forecast": forecast_data
    })
