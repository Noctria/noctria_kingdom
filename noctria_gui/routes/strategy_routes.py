#!/usr/bin/env python3
# coding: utf-8

"""
📚 Veritas戦略ファイル一覧＆閲覧ルート
- 自動生成されたPython戦略ファイル（.py）の一覧と閲覧機能を提供
- メタ情報（勝率・DDなど）付きの表示や検索機能も対応
"""

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json

from core.path_config import STRATEGIES_DIR, NOCTRIA_GUI_TEMPLATES_DIR

router = APIRouter(tags=["strategy"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# 共通の戦略ディレクトリパス
veritas_dir = STRATEGIES_DIR / "veritas_generated"


# ✅ 修正: main.pyのprefixと組み合わせるため、パスを "/" に変更
@router.get("/", response_class=HTMLResponse)
async def list_strategies(request: Request):
    """
    📋 戦略ファイル一覧表示（.pyファイルのみ）
    """
    if not veritas_dir.exists():
        raise HTTPException(status_code=500, detail="戦略ディレクトリが存在しません")

    strategy_files = sorted(veritas_dir.glob("*.py"))
    strategy_names = [f.name for f in strategy_files]

    return templates.TemplateResponse("strategies/list.html", {
        "request": request,
        "strategies": strategy_names
    })


# ✅ 修正: パスを "/view" に変更
@router.get("/view", response_class=HTMLResponse)
async def view_strategy(request: Request, name: str):
    """
    🔍 指定戦略ファイルの内容を表示（.py）
    """
    if ".." in name or "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail="不正なファイル名です")

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


# ✅ 修正: パスを "/overview" に変更
@router.get("/overview", response_class=HTMLResponse)
async def strategy_overview(request: Request):
    """
    📊 メタ情報付きの戦略一覧表示
    """
    data = []

    for file in veritas_dir.glob("*.json"):
        try:
            with open(file, encoding="utf-8") as f:
                j = json.load(f)
                j["json_name"] = file.name
                j["strategy"] = j.get("strategy", file.stem)
                j["tags"] = j.get("tags", [])
                j["win_rate"] = j.get("win_rate", None)
                j["num_trades"] = j.get("num_trades", None)
                j["max_drawdown"] = j.get("max_drawdown", None)
                data.append(j)
        except Exception as e:
            print(f"⚠️ 読み込み失敗: {file.name} - {e}")

    return templates.TemplateResponse("strategies/strategies_overview.html", {
        "request": request,
        "strategies": data
    })


# ✅ 修正: パスを "/search" に変更
@router.get("/search", response_class=HTMLResponse)
async def strategy_search(request: Request, keyword: str = Query(default="")):
    """
    🔍 戦略のキーワード検索（戦略名 or タグ名にマッチ）
    """
    matched = []

    for file in veritas_dir.glob("*.json"):
        try:
            with open(file, encoding="utf-8") as f:
                j = json.load(f)
                name = j.get("strategy", file.stem)
                tags = j.get("tags", [])
                if keyword.lower() in name.lower() or any(keyword.lower() in t.lower() for t in tags):
                    j["strategy"] = name
                    j["tags"] = tags
                    j["json_name"] = file.name
                    j["win_rate"] = j.get("win_rate", None)
                    j["num_trades"] = j.get("num_trades", None)
                    j["max_drawdown"] = j.get("max_drawdown", None)
                    matched.append(j)
        except Exception as e:
            print(f"⚠️ 検索読み込み失敗: {file.name} - {e}")

    return templates.TemplateResponse("strategies/strategies_overview.html", {
        "request": request,
        "strategies": matched,
        "keyword": keyword
    })


# ✅ 修正: パスを "/export" に変更
@router.get("/export", response_class=FileResponse)
async def export_strategy(name: str):
    """
    📤 Python または JSON 戦略ファイルのダウンロード
    """
    if ".." in name or "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail="不正なファイル名です")

    target = veritas_dir / name
    if not target.exists():
        raise HTTPException(status_code=404, detail="ファイルが存在しません")

    media_type = "text/x-python" if target.suffix == ".py" else "application/json"

    return FileResponse(
        path=target,
        filename=target.name,
        media_type=media_type
    )


# ✅ 追加: /strategies/compare に対応するルートを追加
@router.get("/compare", response_class=HTMLResponse)
async def get_strategy_compare_page(request: Request):
    """
    ⚖️ 戦略比較ページを表示
    """
    # ここでは単純にテンプレートを返すだけの仮実装です。
    # 必要に応じて、比較対象の戦略リストなどを渡す処理を追加してください。
    return templates.TemplateResponse("strategy_compare.html", {"request": request})
