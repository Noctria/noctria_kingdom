#!/usr/bin/env python3
# coding: utf-8

"""
🤖 AI関連ルート統合
- AI一覧 (/ai/)
- AI詳細 (/ai/{ai_name})
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from collections import defaultdict
import os
import json
from pathlib import Path
from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, STATS_DIR  # 必要に応じてパスを修正

router = APIRouter(prefix="/ai", tags=["AI"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# --- AI一覧 ---
@router.get("/", summary="AI一覧ページ", response_class=HTMLResponse)
async def ai_list(request: Request):
    ai_names = ["Aurus", "Levia", "Noctus", "Prometheus", "Veritas"]
    return templates.TemplateResponse("ai_list.html", {
        "request": request,
        "ai_names": ai_names
    })

# --- AI詳細情報取得関数 ---
DASHBOARD_METRICS = [
    {"key": "win_rate",       "label": "勝率",      "unit": "%",    "dec": 2},
    {"key": "max_drawdown",   "label": "最大DD",    "unit": "%",    "dec": 2},
    {"key": "trade_count",    "label": "取引数",    "unit": "回",   "dec": 0},
    {"key": "profit_factor",  "label": "PF",        "unit": "",     "dec": 2},
]

def get_ai_detail(ai_name: str):
    trend = defaultdict(lambda: defaultdict(list))
    metric_dist = defaultdict(list)
    strategy_list = []

    if not os.path.isdir(STATS_DIR):
        return [], {}, [], []

    for fname in os.listdir(STATS_DIR):
        if not fname.endswith(".json") or fname == "veritas_eval_result.json":
            continue
        path = os.path.join(STATS_DIR, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            if (d.get("ai") or "Unknown") != ai_name:
                continue
            date = d.get("evaluated_at", "")[:10]
            strat = d.get("strategy") or os.path.splitext(fname)[0]
            # 指標値
            for m in DASHBOARD_METRICS:
                k = m["key"]
                v = d.get(k)
                if v is not None and k in ["win_rate", "max_drawdown"] and v <= 1.0:
                    v = v * 100
                if v is not None and date:
                    trend[date][k].append(v)
                    metric_dist[k].append(v)
            # 戦略リスト
            strategy_list.append({
                "strategy": strat,
                "evaluated_at": d.get("evaluated_at", ""),
                **{m["key"]: d.get(m["key"]) for m in DASHBOARD_METRICS}
            })
        except Exception:
            continue

    # トレンド集計
    dates = sorted(trend.keys())
    trend_dict = {}
    for m in DASHBOARD_METRICS:
        k = m["key"]
        vals = []
        for date in dates:
            day_vals = trend[date][k]
            vals.append(round(sum(day_vals)/len(day_vals), m["dec"]) if day_vals else None)
        trend_dict[k] = {
            "labels": dates,
            "values": vals,
            "avg": round(sum([v for v in vals if v is not None]) / len([v for v in vals if v is not None]), m["dec"]) if any(vals) else None,
            "max": round(max([v for v in vals if v is not None]), m["dec"]) if any(vals) else None,
            "min": round(min([v for v in vals if v is not None]), m["dec"]) if any(vals) else None,
            "diff": round((vals[-1] - vals[-2]), m["dec"]) if len(vals) >= 2 else None
        }

    return ai_name, trend_dict, metric_dist, sorted(strategy_list, key=lambda x: x["evaluated_at"], reverse=True)

# --- AI詳細ページ ---
@router.get("/{ai_name}", response_class=HTMLResponse, summary="AI詳細ページ")
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
