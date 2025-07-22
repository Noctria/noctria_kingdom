#!/usr/bin/env python3
# coding: utf-8

"""
👑 Central Governance Dashboard Route (v2.9) - with AI進捗/勝率推移可視化
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

    # --- ① 基本メトリクス ---
    stats_data = {
        "avg_win_rate": 57.1,
        "promoted_count": 8,
        "pushed_count": 15,
        "pdca_count": 7,  # ここが抜けていたので追加
        "oracle_metrics": {}
    }
    forecast_data = []

    # --- ② Oracle予測取得 ---
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
        elif hasattr(prediction, "to_dict"):
            try:
                forecast_data = prediction.to_dict(orient="records")
            except Exception as df_e:
                logging.error(f"DataFrame->dict変換エラー: {df_e}")
        else:
            logging.warning("⚠️ 予測値の型が想定外。")

        if hasattr(oracle, "get_metrics"):
            stats_data["oracle_metrics"] = oracle.get_metrics()
        logging.info(f"✅ 予測データ件数: {len(forecast_data)}")

    except Exception as e:
        logging.error(f"❌ PrometheusOracle のデータ取得中にエラーが発生: {e}", exc_info=True)

    # --- ③ 勝率推移ダミーデータ（本番はDBやAI履歴から集計） ---
    winrate_trend = [
        {"date": "2025-07-18", "King": 62.4, "Aurus": 65.1, "Levia": 59.7, "Noctus": 60.2, "Prometheus": 61.8},
        {"date": "2025-07-19", "King": 63.0, "Aurus": 64.8, "Levia": 60.3, "Noctus": 61.5, "Prometheus": 61.6},
        {"date": "2025-07-20", "King": 62.0, "Aurus": 66.5, "Levia": 61.2, "Noctus": 60.9, "Prometheus": 62.1},
        {"date": "2025-07-21", "King": 61.8, "Aurus": 66.2, "Levia": 61.5, "Noctus": 60.7, "Prometheus": 62.7},
    ]

    # --- ④ AIごとの進捗ダミーデータ（本番はPDCA/学習進捗から集計） ---
    ai_progress = [
        {"id": "king", "name": "King", "progress": 80, "phase": "評価中"},
        {"id": "aurus", "name": "Aurus", "progress": 65, "phase": "再評価"},
        {"id": "levia", "name": "Levia", "progress": 95, "phase": "最終採用待ち"},
        {"id": "noctus", "name": "Noctus", "progress": 70, "phase": "学習中"},
        {"id": "prometheus", "name": "Prometheus", "progress": 88, "phase": "予測完了"},
    ]

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats_data,
        "forecast": forecast_data,
        "winrate_trend": [],
        "ai_progress": ai_progress,
    })
