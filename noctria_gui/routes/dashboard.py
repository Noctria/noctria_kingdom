#!/usr/bin/env python3
# coding: utf-8

"""
📊 /dashboard - 中央統治ダッシュボード
- 各種統計と予測分析を統合表示
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
import pprint

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from core.king_noctria import KingNoctria
from core.path_config import ACT_LOG_DIR, NOCTRIA_GUI_TEMPLATES_DIR, PUSH_LOG_DIR
from strategies.prometheus_oracle import PrometheusOracle

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


def aggregate_dashboard_stats() -> Dict[str, Any]:
    stats = {
        "promoted_count": 0,
        "pushed_count": 0,
        "pdca_count": 0,
        "avg_win_rate": 0.0,
        "oracle_metrics": {},
        "recheck_success": 0,
        "recheck_fail": 0,
    }

    act_dir = Path(ACT_LOG_DIR)
    win_rates = []

    if act_dir.exists():
        for file_name in os.listdir(act_dir):
            if not file_name.endswith(".json"):
                continue
            try:
                with open(act_dir / file_name, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("status") == "promoted":
                    stats["promoted_count"] += 1
                if "pdca_cycle" in data:
                    stats["pdca_count"] += 1
                win = data.get("score", {}).get("win_rate")
                if isinstance(win, (int, float)):
                    win_rates.append(win)
            except Exception as e:
                print(f"Warning: Failed to process log file {file_name}. Error: {e}")

    stats["avg_win_rate"] = round(sum(win_rates) / len(win_rates), 1) if win_rates else 0.0

    try:
        oracle = PrometheusOracle()
        metrics = oracle.evaluate_oracle_model()
        stats["oracle_metrics"] = {
            "RMSE": round(metrics.get("RMSE", 0.0), 4),
            "MAE": round(metrics.get("MAE", 0.0), 4),
            "MAPE": round(metrics.get("MAPE", 0.0), 4),
        }
    except Exception as e:
        print(f"Warning: Failed to get Oracle metrics. Error: {e}")
        stats["oracle_metrics"] = {"RMSE": 0.0, "MAE": 0.0, "MAPE": 0.0, "error": "N/A"}

    stats["pushed_count"] = aggregate_push_stats()

    return stats


def aggregate_push_stats() -> int:
    push_dir = Path(PUSH_LOG_DIR)
    if not push_dir.exists():
        return 0
    return len([name for name in os.listdir(push_dir) if name.endswith(".json")])


@router.get("/", response_class=HTMLResponse)
async def show_dashboard(request: Request):
    forecast_data = []
    try:
        oracle = PrometheusOracle()
        prediction = oracle.predict_market()
        if prediction:
            dates = prediction.get("dates", [])
            forecast = prediction.get("forecast", [])
            lower = prediction.get("lower_bound", [])
            upper = prediction.get("upper_bound", [])

            if all([dates, forecast, lower, upper]) and len(dates) == len(forecast) == len(lower) == len(upper):
                forecast_data = [
                    {"date": d, "forecast": f, "y_lower": lb, "y_upper": ub}
                    for d, f, lb, ub in zip(dates, forecast, lower, upper)
                ]
            else:
                print("🔶 Oracleデータの形式が不正です。")

    except Exception as e:
        print(f"🔴 Error generating forecast data from Oracle: {e}")

    stats = aggregate_dashboard_stats()
    pprint.pprint(stats)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "forecast": forecast_data or [],  # None防止
        "stats": stats
    })
