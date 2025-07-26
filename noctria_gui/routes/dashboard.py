#!/usr/bin/env python3
# coding: utf-8

"""
👑 Central Governance Dashboard Route (v3.0) - 勝率推移グラフ実装
"""

import logging
import os
import json
from collections import defaultdict
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR
from strategies.prometheus_oracle import PrometheusOracle

# --- 勝率推移用データパス
STATS_DIR = "data/stats"  # パスはプロジェクト配置により調整

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

def load_winrate_trend():
    """data/stats/*.jsonから日別平均勝率を取得"""
    date_to_winrates = defaultdict(list)
    if not os.path.isdir(STATS_DIR):
        return []
    for fname in os.listdir(STATS_DIR):
        if not fname.endswith(".json") or fname == "veritas_eval_result.json":
            continue
        path = os.path.join(STATS_DIR, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            win_rate = d.get("win_rate")
            date = d.get("evaluated_at", "")[:10]
            if win_rate is not None and date:
                if win_rate <= 1.0:  # 0.68形式なら%
                    win_rate = win_rate * 100
                date_to_winrates[date].append(win_rate)
        except Exception as e:
            logging.warning(f"勝率ファイル読み込み失敗: {fname}, {e}")
    trend = [
        {"date": date, "win_rate": round(sum(wrs)/len(wrs), 2)}
        for date, wrs in date_to_winrates.items()
    ]
    trend.sort(key=lambda x: x["date"])
    return trend

@router.get("/", response_class=HTMLResponse)
async def dashboard_view(request: Request):
    logging.info("📥 ダッシュボード表示要求を受理しました")

    # --- ① 基本メトリクス ---
    stats_data = {
        "avg_win_rate": 57.1,
        "promoted_count": 8,
        "pushed_count": 15,
        "pdca_count": 7,
        "oracle_metrics": {}
    }
    forecast_data = []

    # --- ② Oracle予測取得 ---
    try:
        oracle = PrometheusOracle()
        logging.info("📤 oracle.predict() 実行")
        prediction = oracle.predict()
        logging.info(f"🧾 predict() 結果タイプ: {type(prediction)}, 内容例: {str(prediction)[:120]}")
        if prediction is None:
            logging.warning("⚠️ oracle.predict() が None を返しました。")
            forecast_data = []
        elif isinstance(prediction, list):
            if all(isinstance(p, dict) for p in prediction):
                forecast_data = prediction
        elif hasattr(prediction, "to_dict"):
            try:
                forecast_data = prediction.to_dict(orient="records")
            except Exception as df_e:
                logging.error(f"DataFrame->dict変換エラー: {df_e}")
        if hasattr(oracle, "get_metrics"):
            stats_data["oracle_metrics"] = oracle.get_metrics()
        logging.info(f"✅ 予測データ件数: {len(forecast_data)}")
    except Exception as e:
        logging.error(f"❌ PrometheusOracle のデータ取得中にエラーが発生: {e}", exc_info=True)

    # --- ③ 勝率推移グラフ用データ ---
    winrate_trend = load_winrate_trend()

    # --- ④ AIごとの進捗（ダミーデータ） ---
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
        "winrate_trend": winrate_trend,
        "ai_progress": ai_progress,
    })
