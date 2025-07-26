#!/usr/bin/env python3
# coding: utf-8

"""
👑 Central Governance Dashboard Route (v4.0) - 全指標（勝率・最大DD・取引数・PF）対応ダッシュボード
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

# ★ 各指標の定義・日本語名・小数点表示など（フロント連携でも使う）
DASHBOARD_METRICS = [
    {"key": "win_rate",       "label": "勝率",      "unit": "%",    "dec": 2},
    {"key": "max_drawdown",   "label": "最大DD",    "unit": "%",    "dec": 2},
    {"key": "trade_count",    "label": "取引数",    "unit": "回",   "dec": 0},
    {"key": "profit_factor",  "label": "PF",        "unit": "",     "dec": 2},
]

def load_ai_metrics_trend():
    """
    data/stats/*.json から日付×AI別の複数指標（勝率/maxDD/取引数/PFなど）を時系列化
    """
    date_ai_metrics = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    if not os.path.isdir(STATS_DIR):
        return [], []

    for fname in os.listdir(STATS_DIR):
        if not fname.endswith(".json") or fname == "veritas_eval_result.json":
            continue
        path = os.path.join(STATS_DIR, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            ai = d.get("ai") or "Unknown"
            date = d.get("evaluated_at", "")[:10]
            for m in DASHBOARD_METRICS:
                k = m["key"]
                v = d.get(k)
                if v is not None and date:
                    # %系は0-1なら100倍
                    if k in ["win_rate", "max_drawdown"] and v <= 1.0:
                        v = v * 100
                    date_ai_metrics[date][ai][k].append(v)
        except Exception as e:
            logging.warning(f"AI指標ファイル読込失敗: {fname}, {e}")

    ai_names = set()
    for d in date_ai_metrics.values():
        ai_names.update(d.keys())
    ai_names = sorted(ai_names)
    trend = []
    for date in sorted(date_ai_metrics.keys()):
        entry = {"date": date}
        for ai in ai_names:
            for m in DASHBOARD_METRICS:
                k = m["key"]
                vals = date_ai_metrics[date][ai][k]
                entry[f"{ai}__{k}"] = round(sum(vals)/len(vals), m["dec"]) if vals else None
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

    # --- 全指標時系列トレンド ---（AI×指標ごと平均値入り）
    metric_trend, ai_names = load_ai_metrics_trend()

    # --- AIごとの進捗（ダミー） ---
    ai_progress = [
        {"id": "king", "name": "King", "progress": 80, "phase": "評価中"},
        {"id": "aurus", "name": "Aurus", "progress": 65, "phase": "再評価"},
        {"id": "levia", "name": "Levia", "progress": 95, "phase": "最終採用待ち"},
        {"id": "noctus", "name": "Noctus", "progress": 70, "phase": "学習中"},
        {"id": "prometheus", "name": "Prometheus", "progress": 88, "phase": "予測完了"},
    ]

    # --- 指標ごと・AIごとに時系列辞書を作成（ {metric_key: {AI: {labels, values, avg, max, min, diff}} } ）---
    metrics_dict = {}
    for m in DASHBOARD_METRICS:
        k = m["key"]
        metrics_dict[k] = {}
        for ai in ai_names:
            values = [row.get(f"{ai}__{k}") for row in metric_trend]
            labels = [row["date"] for row in metric_trend]
            data = [v for v in values if v is not None]
            metrics_dict[k][ai] = {
                "labels": labels,
                "values": values,
                "avg": round(sum(data) / len(data), m["dec"]) if data else None,
                "max": round(max(data), m["dec"]) if data else None,
                "min": round(min(data), m["dec"]) if data else None,
                "diff": round((data[-1] - data[-2]), m["dec"]) if len(data) >= 2 else None
            }

    # --- 全体平均（各指標ごと）---
    overall_metrics = {}
    for m in DASHBOARD_METRICS:
        k = m["key"]
        vals = []
        for row in metric_trend:
            ai_vals = [row.get(f"{ai}__{k}") for ai in ai_names if row.get(f"{ai}__{k}") is not None]
            vals.append(round(sum(ai_vals)/len(ai_vals), m["dec"]) if ai_vals else None)
        overall_metrics[k] = {
            "labels": [row["date"] for row in metric_trend],
            "values": vals,
            "avg": round(sum([v for v in vals if v is not None]) / len([v for v in vals if v is not None]), m["dec"]) if any(vals) else None,
            "max": round(max([v for v in vals if v is not None]), m["dec"]) if any(vals) else None,
            "min": round(min([v for v in vals if v is not None]), m["dec"]) if any(vals) else None,
            "diff": round((vals[-1] - vals[-2]), m["dec"]) if len(vals) >= 2 else None
        }

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats_data,
        "forecast": forecast_data,
        "ai_progress": ai_progress,
        "ai_names": ai_names,
        "dashboard_metrics": DASHBOARD_METRICS,
        "metrics_dict": metrics_dict,
        "overall_metrics": overall_metrics,
    })
