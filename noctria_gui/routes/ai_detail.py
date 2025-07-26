#!/usr/bin/env python3
# coding: utf-8

"""
👁️ AI別詳細ドリルダウンルート
- 指定AIの全指標トレンド・分布・全戦略リスト等を集約表示
"""

import os
import json
from collections import defaultdict
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, DATA_DIR

# STATS_DIRを絶対パス化（dataディレクトリのstatsフォルダ）
STATS_DIR = DATA_DIR / "stats"

router = APIRouter(prefix="/ai", tags=["AI Detail"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

DASHBOARD_METRICS = [
    {"key": "win_rate",       "label": "勝率",      "unit": "%",    "dec": 2},
    {"key": "max_drawdown",   "label": "最大DD",    "unit": "%",    "dec": 2},
    {"key": "trade_count",    "label": "取引数",    "unit": "回",   "dec": 0},
    {"key": "profit_factor",  "label": "PF",        "unit": "",     "dec": 2},
]

def get_ai_detail(ai_name):
    trend = defaultdict(lambda: defaultdict(list))
    metric_dist = defaultdict(list)
    strategy_list = []

    if not STATS_DIR.exists():
        print(f"Error: STATS_DIR does not exist: {STATS_DIR}")
        return [], {}, [], []

    for fname in os.listdir(STATS_DIR):
        if not fname.endswith(".json") or fname == "veritas_eval_result.json":
            continue
        path = STATS_DIR / fname
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            if (d.get("ai") or "Unknown") != ai_name:
                continue
            date = d.get("evaluated_at", "")[:10]
            strat = d.get("strategy") or os.path.splitext(fname)[0]
            for m in DASHBOARD_METRICS:
                k = m["key"]
                v = d.get(k)
                if v is not None and k in ["win_rate", "max_drawdown"] and v <= 1.0:
                    v = v * 100
                if v is not None and date:
                    trend[date][k].append(v)
                    metric_dist[k].append(v)
            strategy_list.append({
                "strategy": strat,
                "evaluated_at": d.get("evaluated_at", ""),
                **{m["key"]: d.get(m["key"]) for m in DASHBOARD_METRICS}
            })
        except Exception as e:
            print(f"Failed to load {path}: {e}")
            continue

    dates = sorted(trend.keys())
    trend_dict = {}
    for m in DASHBOARD_METRICS:
        k = m["key"]
        vals = []
        for date in dates:
            day_vals = trend[date][k]
            # 数値のみ抽出して平均値を計算
            numeric_vals = [v for v in day_vals if isinstance(v, (int, float))]
            if numeric_vals:
                avg_val = round(sum(numeric_vals) / len(numeric_vals), m["dec"])
            else:
                avg_val = None
            vals.append(avg_val)
        # floatでラップしJSONシリアライズ可能にする
        trend_dict[k] = {
            "labels": list(dates),
            "values": [float(v) if v is not None else None for v in vals],
            "avg": float(round(sum([v for v in vals if v is not None]) / len([v for v in vals if v is not None]), m["dec"])) if any(vals) else None,
            "max": float(round(max([v for v in vals if v is not None]), m["dec"])) if any(vals) else None,
            "min": float(round(min([v for v in vals if v is not None]), m["dec"])) if any(vals) else None,
            "diff": float(round((vals[-1] - vals[-2]), m["dec"])) if len(vals) >= 2 else None
        }

    # metric_distもfloat化（念のため）
    for k in metric_dist:
        metric_dist[k] = [float(v) for v in metric_dist[k]]

    return ai_name, trend_dict, metric_dist, sorted(strategy_list, key=lambda x: x["evaluated_at"], reverse=True)

@router.get("/{ai_name}", response_class=HTMLResponse)
async def ai_detail_view(request: Request, ai_name: str):
    ai_name, trend_dict, metric_dist, strategy_list = get_ai_detail(ai_name)
    return templates.TemplateResponse("ai_detail.html", {
        "request": request,
        "ai_name": ai_name,
        "dashboard_metrics": DASHBOARD_METRICS,
        "trend_dict": trend_dict,
        "metric_dist": metric_dist,
        "strategy_list": strategy_list,
    })
