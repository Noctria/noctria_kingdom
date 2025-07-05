#!/usr/bin/env python3
# coding: utf-8

"""
📊 戦略比較ルート
- 選択された複数戦略のメタ情報を比較し、Chart.js でグラフ化
"""

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List
from pathlib import Path
import json

from core.path_config import STRATEGIES_DIR, NOCTRIA_GUI_TEMPLATES_DIR

# ✅ FastAPIルーター初期化
router = APIRouter(tags=["strategy_compare"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# ✅ 戦略ファイルディレクトリ
veritas_dir = STRATEGIES_DIR / "veritas_generated"


@router.get("/strategies/compare", response_class=HTMLResponse)
async def compare_select(request: Request):
    """
    📑 戦略選択フォーム
    - 複数戦略から比較対象を選択
    """
    options = []
    for file in veritas_dir.glob("*.json"):
        try:
            with open(file, encoding="utf-8") as f:
                j = json.load(f)
                strategy_name = j.get("strategy")
                if strategy_name:
                    options.append(j)
        except Exception as e:
            print(f"⚠️ 読み込み失敗: {file.name} - {e}")

    return templates.TemplateResponse("strategies/compare_form.html", {
        "request": request,
        "strategies": sorted(options, key=lambda x: x.get("strategy", ""))
    })


@router.post("/strategies/compare/result", response_class=HTMLResponse)
async def compare_result(request: Request, strategies: List[str] = Form(...)):
    """
    📈 選択戦略の比較グラフを表示（棒グラフ＋レーダー）
    """
    selected = []
    for name in strategies:
        file = veritas_dir / f"{name}.json"
        if file.exists():
            try:
                with open(file, encoding="utf-8") as f:
                    data = json.load(f)
                    selected.append(data)
            except Exception as e:
                print(f"⚠️ ロード失敗: {file.name} - {e}")
                continue

    if not selected:
        raise HTTPException(status_code=404, detail="⚠️ 有効な戦略が選択されていません")

    return templates.TemplateResponse("strategies/compare_result.html", {
        "request": request,
        "strategies": selected
    })


@router.get("/strategies/compare/radar", response_class=HTMLResponse)
async def compare_radar_sample(request: Request):
    """
    🧩 レーダーチャートのサンプル表示（全戦略から上位5件を抽出）
    """
    selected = []
    for file in list(veritas_dir.glob("*.json"))[:5]:
        try:
            with open(file, encoding="utf-8") as f:
                data = json.load(f)
                selected.append(data)
        except Exception as e:
            print(f"⚠️ レーダー用読み込み失敗: {file.name} - {e}")
            continue

    return templates.TemplateResponse("strategies/compare_result.html", {
        "request": request,
        "strategies": selected
    })
