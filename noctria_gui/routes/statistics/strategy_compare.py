#!/usr/bin/env python3
# coding: utf-8

"""
📊 /statistics/compare - 戦略比較フォームおよび結果表示
- 戦略スコアログを読み込み、比較グラフを描画
- compare_form.html + compare_result.html を統一運用
"""

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import List, Dict, Any
from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, ACT_LOG_DIR
import json
import os

router = APIRouter(prefix="/statistics", tags=["statistics"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


def load_strategy_logs() -> List[Dict[str, Any]]:
    logs = []
    if not Path(ACT_LOG_DIR).exists():
        return logs

    for f in os.listdir(ACT_LOG_DIR):
        if f.endswith(".json"):
            try:
                with open(Path(ACT_LOG_DIR) / f, "r", encoding="utf-8") as file:
                    log = json.load(file)
                logs.append(log)
            except Exception:
                continue
    return logs


@router.get("/compare/form", response_class=HTMLResponse)
async def compare_form(request: Request):
    logs = load_strategy_logs()
    strategies = []

    for log in logs:
        try:
            strategies.append({
                "strategy": log.get("strategy_name"),
                "win_rate": log.get("score", {}).get("win_rate", 0),
                "max_drawdown": log.get("score", {}).get("max_drawdown", 0),
                "num_trades": log.get("score", {}).get("num_trades", 0)
            })
        except Exception:
            continue

    # 重複戦略名の除外
    unique = {}
    for s in strategies:
        unique[s["strategy"]] = s
    strategies = list(unique.values())

    return templates.TemplateResponse("strategies/compare_form.html", {
        "request": request,
        "strategies": sorted(strategies, key=lambda x: x["strategy"])
    })


@router.post("/compare/render", response_class=HTMLResponse)
async def render_comparison(request: Request, selected: List[str] = Form(...)):
    if not selected or len(selected) < 2:
        return RedirectResponse("/statistics/compare/form", status_code=302)

    logs = load_strategy_logs()
    filtered = []

    for log in logs:
        if log.get("strategy_name") in selected:
            filtered.append({
                "strategy": log.get("strategy_name"),
                "win_rate": log.get("score", {}).get("win_rate", 0),
                "max_drawdown": log.get("score", {}).get("max_drawdown", 0),
                "num_trades": log.get("score", {}).get("num_trades", 0)
            })

    return templates.TemplateResponse("strategies/compare_result.html", {
        "request": request,
        "strategies": filtered
    })


# ✅ 古いURLの互換リダイレクト（例: /strategy/compare）
@router.get("/../strategy/compare")
async def legacy_redirect():
    return RedirectResponse("/statistics/compare/form")
