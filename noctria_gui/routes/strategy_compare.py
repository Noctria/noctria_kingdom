#!/usr/bin/env python3
# coding: utf-8

"""
📈 戦略比較ルート
- 複数戦略の選択表示と比較グラフビューを提供
"""

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List
import json
from pathlib import Path

from core.path_config import STRATEGIES_DIR, NOCTRIA_GUI_TEMPLATES_DIR

router = APIRouter(tags=["strategy-compare"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

veritas_dir = STRATEGIES_DIR / "veritas_generated"

@router.get("/strategies/compare", response_class=HTMLResponse)
async def show_compare_form(request: Request):
    """
    📋 戦略選択フォーム表示
    - .jsonファイルから戦略名一覧を取得し、選択肢として表示
    """
    strategies = []
    for file in veritas_dir.glob("*.json"):
        try:
            with open(file, encoding="utf-8") as f:
                j = json.load(f)
                strategies.append({"strategy": j.get("strategy", file.stem)})
        except Exception as e:
            print(f"⚠️ JSON読み込み失敗: {file.name} - {e}")
    return templates.TemplateResponse("strategies/compare_select.html", {
        "request": request,
        "strategies": strategies
    })


@router.post("/strategies/compare/view", response_class=HTMLResponse)
async def show_comparison_result(
    request: Request,
    selected: List[str] = Form(...),
    metric: str = Form(default="win_rate")
):
    """
    📈 選択された戦略を指定メトリクスで比較表示
    """
    selected_data = []
    for file in veritas_dir.glob("*.json"):
        try:
            with open(file, encoding="utf-8") as f:
                j = json.load(f)
                if j.get("strategy") in selected:
                    selected_data.append(j)
        except Exception as e:
            print(f"⚠️ JSON読み込み失敗: {file.name} - {e}")

    return templates.TemplateResponse("strategies/compare_result.html", {
        "request": request,
        "strategies": selected_data,
        "metric": metric
    })
