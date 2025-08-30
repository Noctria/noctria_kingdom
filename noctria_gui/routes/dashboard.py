#!/usr/bin/env python3
# coding: utf-8

import logging
import os
import json
from collections import defaultdict
from typing import Tuple, List, Dict, Any
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# パス設定が正しいか確認
from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, STATS_DIR
from strategies.prometheus_oracle import PrometheusOracle

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

# ルーター設定
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# ダッシュボードメトリクスの定義
DASHBOARD_METRICS = [
    {"key": "win_rate",       "label": "勝率",      "unit": "%",    "dec": 2},
    {"key": "max_drawdown",   "label": "最大DD",    "unit": "%",    "dec": 2},
    {"key": "trade_count",    "label": "取引数",    "unit": "回",   "dec": 0},
    {"key": "profit_factor",  "label": "PF",        "unit": "",     "dec": 2},
]

# AIメトリクスのトレンドと分布をロードする関数
def load_ai_metrics_trend_and_dist() -> Tuple[List[Dict[str, Any]], List[str], Dict[str, Dict[str, List[float]]]]:
    date_ai_metrics = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    ai_metric_dist = defaultdict(lambda: defaultdict(list))

    # STATS_DIRが存在しない場合は早期リターン
    if not os.path.isdir(STATS_DIR):
        return [], [], {}

    for fname in os.listdir(STATS_DIR):
        # ファイルがjsonで、特定のファイルを除外
        if not fname.endswith(".json") or fname == "veritas_eval_result.json":
            continue
        
        path = os.path.join(STATS_DIR, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            ai = d.get("ai") or "Unknown"
            date = d.get("evaluated_at", "")[:10]  # 日付を取得
            for m in DASHBOARD_METRICS:
                k = m["key"]
                v = d.get(k)
                if v is not None:
                    # 勝率と最大ドローダウンの値をパーセンテージに変換
                    if k in ["win_rate", "max_drawdown"] and v <= 1.0:
                        v = v * 100
                    if date:
                        date_ai_metrics[date][ai][k].append(v)
                    ai_metric_dist[ai][k].append(v)
        except Exception as e:
            logging.warning(f"AI指標ファイル読込失敗: {fname}, エラー: {e}", exc_info=True)

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
                entry[f"{ai}__{k}"] = round(sum(vals)/len(vals), m["dec"]) if vals and len(vals) > 0 else None
        trend.append(entry)
    return trend, ai_names, ai_metric_dist

# ダッシュボード表示のルート
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

    # メトリクスのトレンドと分布をロード
    metric_trend, ai_names, ai_metric_dist = load_ai_metrics_trend_and_dist()

    ai_progress = [
        {"id": "king", "name": "King", "progress": 80, "phase": "評価中"},
        {"id": "aurus", "name": "Aurus", "progress": 65, "phase": "再評価"},
        {"id": "levia", "name": "Levia", "progress": 95, "phase": "最終採用待ち"},
        {"id": "noctus", "name": "Noctus", "progress": 70, "phase": "学習中"},
        {"id": "prometheus", "name": "Prometheus", "progress": 88, "phase": "予測完了"},
    ]

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
                "avg": round(sum(data) / len(data), m["dec"]) if data and len(data) > 0 else None,
                "max": round(max(data), m["dec"]) if data and len(data) > 0 else None,
                "min": round(min(data), m["dec"]) if data and len(data) > 0 else None,
                "diff": round((data[-1] - data[-2]), m["dec"]) if len(data) >= 2 else None
            }

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
        "ai_metric_dist": ai_metric_dist,
    })
