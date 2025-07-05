#!/usr/bin/env python3
# coding: utf-8

"""
📚 Veritas戦略ファイル一覧＆閲覧ルート
- 自動生成されたPython戦略ファイル（.py）の一覧と閲覧機能を提供
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from core.path_config import STRATEGIES_DIR, NOCTRIA_GUI_TEMPLATES_DIR

router = APIRouter(tags=["strategy"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


@router.get("/strategies", response_class=HTMLResponse)
async def list_strategies(request: Request):
    """
    📋 戦略ファイル一覧表示
    - veritas_generated 内の .py 戦略ファイル一覧を表示
    """
    veritas_dir = STRATEGIES_DIR / "veritas_generated"
    if not veritas_dir.exists():
        raise HTTPException(status_code=500, detail="戦略ディレクトリが存在しません")

    strategy_files = sorted(veritas_dir.glob("*.py"))
    strategy_names = [f.name for f in strategy_files]

    return templates.TemplateResponse("strategies/list.html", {
        "request": request,
        "strategies": strategy_names
    })


@router.get("/strategies/view", response_class=HTMLResponse)
async def view_strategy(request: Request, name: str):
    """
    🔍 指定戦略ファイルの内容を表示
    - /strategies/view?name=example.py
    """
    veritas_dir = STRATEGIES_DIR / "veritas_generated"
    target_file = veritas_dir / name

    if not target_file.exists() or target_file.suffix != ".py":
        raise HTTPException(status_code=404, detail="戦略ファイルが存在しません")

    try:
        content = target_file.read_text(encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ファイル読み込み失敗: {e}")

    return templates.TemplateResponse("strategies/view.html", {
        "request": request,
        "filename": name,
        "content": content
    })
