#!/usr/bin/env python3
# coding: utf-8

"""
👑 Central Governance Dashboard Route (v3.2) - AI別勝率推移グラフ本番データ対応
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

STATS_DIR = "data/stats"  # 必要に応じて絶対パス化

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

def load_ai_winrate_trend():
    """
    data/stats/*.json から日付×AI別の勝率を時系列化
    """
    date_ai_to_winrates = defaultdict(lambda: defaultdict(list))
    if not os.path.isdir(STATS_DIR):
        return [], []

    for fname in os.listdir(STATS_DIR):
        if not fname.endswith(".json") or fname == "veritas_eval_result.json":
            continue
        path = os.path.join(STATS_DIR, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            win_rate = d.get("win_rate")
            ai = d.get("ai") or "Unknown"
            date = d.get("evaluated_at", "")[:10]
            if win_rate is not None and date:
                if win_rate <= 1.0:
                    win_rate = win_rate * 100
                date_ai_to_winrates[date][ai].append(win_rate)
        except Exception as e:
            logging.warning(f"AI勝率ファイル読込失敗: {fname}, {e}")

    ai_names = set()
    for d in date_ai_to_winrates.values():
        ai_names.update(d.keys())
    ai_names = sorted(ai_names)
    trend = []
    for date in sorted(date_ai_to_winrates.keys()):
        entry = {"date": date}
        for ai in ai_names:
            wrs = date_ai_to_winrates[date].get(ai, [])
            entry[ai] = round(sum(wrs)/len(wrs), 2) if wrs else None
        trend.append(entry)
    return trend, ai_names

@router.get("/", response_class=HTMLResponse)
async def dashboard_view(request: Request):
    logging.info("📥 ダッシュボード表示要求を受理しました")

    stats_data = {
        "avg_win_rate": 0.0,
        "promoted_count": 0,
        "pushed_count": 0,
        "pdca_count": 0,
        "oracle_metrics": {}
    }
    forecast_data = []

    # Oracle予測取得
    try:
        oracle = PrometheusOracle()
        logging.info("📤 oracle.predict() 実行")
        prediction = oracle.predict()
        logging.info(f"🧾 predict() 結果タイプ: {type(prediction)}, 内容例: {str(prediction)[:120]}")
        if prediction is None:
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

    # --- 勝率推移グラフ（AI別） ---
    winrate_trend, ai_names = load_ai_winrate_trend()
    if winrate_trend:
        # 全AI平均で最新勝率セット
        last = winrate_trend[-1]
        vals = [v for k, v in last.items() if k != "date" and v is not None]
        if vals:
            stats_data["avg_win_rate"] = round(sum(vals) / len(vals), 2)

    # --- AIごとの進捗（ダミー） ---
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
        "ai_names": ai_names,
    })
