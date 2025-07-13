#!/usr/bin/env python3
# coding: utf-8

import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict
import pprint

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

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
        metrics = oracle.evaluate_oracle_model()  # ← メソッド名を修正
        stats["oracle_metrics"] = {
            "RMSE": metrics.get("RMSE", 0.0),
            "MAE": metrics.get("MAE", 0.0),
            "MAPE": metrics.get("MAPE", 0.0),
        }
    except Exception as e:
        print(f"Warning: Failed to get Oracle metrics. Error: {e}")
        stats["oracle_metrics"] = {"RMSE": 0.0, "MAE": 0.0, "MAPE": 0.0, "error": "N/A"}

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
        today = datetime.now()
        price = 150.0
        for i in range(14):
            date = today - timedelta(days=(13 - i))
            actual_price = price + (random.random() - 0.5) * 3
            pred_price = actual_price + (random.random() - 0.5) * 1
            forecast_data.append({
                "date": date.strftime("%Y-%m-%d"),
                "y_true": round(actual_price, 2),
                "forecast": round(pred_price, 2),
                "y_lower": round(pred_price - 1.5, 2),
                "y_upper": round(pred_price + 1.5, 2),
            })
            price = actual_price
    except Exception as e:
        print(f"🔴 Error generating forecast data: {e}")

    stats = aggregate_dashboard_stats()
    stats["pushed_count"]_]()
