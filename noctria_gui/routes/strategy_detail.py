#!/usr/bin/env python3
# coding: utf-8

"""
📘 Strategy Detail Route (v3.0)
- 指定戦略のPDCA推移、指標トレンド・分布・履歴を全て可視化するドリルダウンページ
"""

import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
import json
from collections import defaultdict
from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR
from noctria_gui.services import statistics_service

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

router = APIRouter(prefix="/strategies", tags=["strategy-detail"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

DASHBOARD_METRICS = [
    {"key": "win_rate",       "label": "勝率",      "unit": "%",    "dec": 2},
    {"key": "max_drawdown",   "label": "最大DD",    "unit": "%",    "dec": 2},
    {"key": "trade_count",    "label": "取引数",    "unit": "回",   "dec": 0},
    {"key": "profit_factor",  "label": "PF",        "unit": "",     "dec": 2},
]

def get_strategy_history(strategy_name):
    """
    全評価履歴・日付トレンド・分布データ抽出（data/stats/*.json 直読み or サービス経由）
    """
    # 基本: statistics_service.load_all_statistics() 経由
    logs = statistics_service.load_all_statistics()
    hist = [log for log in logs if log.get("strategy") == strategy_name]
    if not hist:
        return None, None, None

    # トレンド&分布データ生成
    trend = defaultdict(lambda: defaultdict(list))
    dist = defaultdict(list)
    for log in hist:
        date = log.get("evaluated_at", "")[:10]
        for m in DASHBOARD_METRICS:
            k = m["key"]
            v = log.get(k)
            if v is not None and k in ["win_rate", "max_drawdown"] and v <= 1.0:
                v = v * 100
            if v is not None and date:
                trend[date][k].append(v)
                dist[k].append(v)
    # 構造変換
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
    return hist, trend_dict, dist

@router.get("/detail/{strategy_name}", response_class=HTMLResponse)
async def show_strategy_detail(request: Request, strategy_name: str):
    """
    📘 指定された戦略名の詳細情報＋トレンド/分布/履歴一覧を可視化
    """
    logging.info(f"戦略詳細の表示要求を受理しました。対象戦略: {strategy_name}")
    try:
        logs = statistics_service.load_all_statistics()

        # 指定戦略の取得
        matched_strategy = next((log for log in logs if log.get("strategy") == strategy_name), None)
        if not matched_strategy:
            logging.warning(f"指定された戦略が見つかりませんでした: {strategy_name}")
            raise HTTPException(status_code=404, detail=f"戦略『{strategy_name}』は見つかりません。")

        # 関連（タグ一致）戦略
        current_tags = matched_strategy.get("tags", [])
        related_strategies = [
            s for s in logs
            if s.get("strategy") != strategy_name and
               any(tag in s.get("tags", []) for tag in current_tags)
        ][:4]

        # トレンド・分布・履歴を取得
        hist, trend_dict, dist = get_strategy_history(strategy_name)
        if hist is None:
            raise HTTPException(status_code=404, detail=f"履歴情報が存在しません。")

    except Exception as e:
        logging.error(f"戦略詳細の取得中にエラーが発生しました: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="戦略詳細情報の取得中に内部エラーが発生しました。")

    return templates.TemplateResponse("strategy_detail.html", {
        "request": request,
        "strategy": matched_strategy,
        "related_strategies": related_strategies,
        "dashboard_metrics": DASHBOARD_METRICS,
        "trend_dict": trend_dict,
        "metric_dist": dist,
        "eval_list": sorted(hist, key=lambda x: x["evaluated_at"], reverse=True)
    })
