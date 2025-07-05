#!/usr/bin/env python3
# coding: utf-8

"""
📑 戦略比較フォームと結果表示ルート
- 複数戦略を選択して比較グラフを表示
"""

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json

from core.path_config import STRATEGIES_DIR, NOCTRIA_GUI_TEMPLATES_DIR

router = APIRouter(tags=["strategy"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

veritas_dir = STRATEGIES_DIR / "veritas_generated"


@router.get("/strategies/compare", response_class=HTMLResponse)
async def compare_form(request: Request):
    """
    📑 戦略比較のための選択フォームを表示
    """
    strategies = []
    for file in veritas_dir.glob("*.json"):
        try:
            with open(file, encoding="utf-8") as f:
                strategies.append(json.load(f))
        except Exception as e:
            print(f"⚠️ 読み込み失敗: {file.name} - {e}")

    return templates.TemplateResponse("strategies/compare_form.html", {
        "request": request,
        "strategies": strategies
    })


@router.post("/strategies/compare/result", response_class=HTMLResponse)
async def compare_result(request: Request, selected: list[str] = Form(...)):
    """
    📊 選択された戦略の比較グラフを表示
    """
    selected_data = []
    for name in selected:
        file = veritas_dir / f"{name}.json"
        if file.exists():
            try:
                with open(file, encoding="utf-8") as f:
                    selected_data.append(json.load(f))
            except Exception as e:
                print(f"⚠️ 読み込み失敗: {file.name} - {e}")

    return templates.TemplateResponse("strategies/compare_result.html", {
        "request": request,
        "strategies": selected_data
    })
