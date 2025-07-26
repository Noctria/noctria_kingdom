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

from src.core.path_config import STRATEGIES_DIR, NOCTRIA_GUI_TEMPLATES_DIR

router = APIRouter(tags=["strategy"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

veritas_dir = STRATEGIES_DIR / "veritas_generated"

@router.get("/", response_class=HTMLResponse)
async def list_strategies(request: Request):
    if not veritas_dir.exists():
        raise HTTPException(status_code=500, detail="戦略ディレクトリが存在しません")

    strategy_files = sorted(veritas_dir.glob("*.py"))
    strategy_names = [f.name for f in strategy_files]

    return templates.TemplateResponse("strategies/list.html", {
        "request": request,
        "strategies": strategy_names
    })

@router.get("/view", response_class=HTMLResponse)
async def view_strategy(request: Request, name: str):
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

@router.get("/overview", response_class=HTMLResponse)
async def strategy_overview(request: Request):
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
                j["ai"] = j.get("ai", "")
                data.append(j)
        except Exception as e:
            print(f"⚠️ 読み込み失敗: {file.name} - {e}")

    return templates.TemplateResponse("strategies/strategies_overview.html", {
        "request": request,
        "strategies": data
    })

# 拡張版：詳細検索パラメータ追加
@router.get("/search", response_class=HTMLResponse)
async def strategy_search(
    request: Request,
    keyword: str = Query(default=""),
    min_win_rate: float = Query(default=None),
    max_drawdown: float = Query(default=None),
    tags: str = Query(default=""),
    ai: str = Query(default=""),
):
    matched = []
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    for file in veritas_dir.glob("*.json"):
        try:
            with open(file, encoding="utf-8") as f:
                j = json.load(f)
            name = j.get("strategy", file.stem)
            file_tags = j.get("tags", [])
            file_ai = j.get("ai", "")

            # キーワード検索 (戦略名 or タグ)
            if keyword and keyword.lower() not in name.lower() and not any(keyword.lower() in t.lower() for t in file_tags):
                continue

            # 勝率フィルター
            wr = j.get("win_rate")
            if wr is not None and wr <= 1.0:
                wr = wr * 100
            if min_win_rate is not None and (wr is None or wr < min_win_rate):
                continue

            # 最大DDフィルター
            max_dd = j.get("max_drawdown")
            if max_dd is not None and max_drawdown is not None and max_dd > max_drawdown:
                continue

            # タグフィルター (AND条件)
            if tag_list and not all(t in file_tags for t in tag_list):
                continue

            # AIフィルター
            if ai and ai != file_ai:
                continue

            j["strategy"] = name
            j["tags"] = file_tags
            j["ai"] = file_ai
            j["win_rate"] = wr
            j["num_trades"] = j.get("num_trades", None)
            j["max_drawdown"] = max_dd
            matched.append(j)
        except Exception as e:
            print(f"⚠️ 検索読み込み失敗: {file.name} - {e}")

    return templates.TemplateResponse("strategies/search.html", {
        "request": request,
        "strategies": matched,
        "keyword": keyword,
        "min_win_rate": min_win_rate,
        "max_drawdown": max_drawdown,
        "tags": tags,
        "ai": ai,
    })

@router.get("/export", response_class=FileResponse)
async def export_strategy(name: str):
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

@router.get("/compare", response_class=HTMLResponse)
async def get_strategy_compare_page(request: Request):
    return templates.TemplateResponse("strategy_compare.html", {"request": request})
