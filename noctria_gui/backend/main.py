#!/usr/bin/env python3
# coding: utf-8

import sys
from pathlib import Path

# __file__ は main.py のファイルパスです。親ディレクトリから noctria_kingdom を参照します。
# ただし、`sys.path` の設定は不要なので、これを削除します。

# core.path_config と noctria_gui.routes をそのままインポートします
from core.path_config import NOCTRIA_GUI_STATIC_DIR, NOCTRIA_GUI_TEMPLATES_DIR
import noctria_gui.routes as routes_pkg  # 修正: noctria_gui.routesをimportし、routes_pkgとして使う

from fastapi import FastAPI, Request, Query  # 修正: Queryをインポート
from fastapi.responses import RedirectResponse, HTMLResponse  # 修正: HTMLResponseをインポート
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Any
import json

# ========================================
# 🚀 FastAPI GUI アプリケーション構成
# ========================================
app = FastAPI(
    title="Noctria Kingdom GUI",
    description="王国の中枢制御パネル（DAG起動・戦略管理・評価表示など）",
    version="1.0.0",
)

# ✅ 静的ファイルとテンプレートの登録
app.mount("/static", StaticFiles(directory=str(NOCTRIA_GUI_STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# ✅ Jinja2 カスタムフィルタ：from_json（文字列 → dict）
def from_json(value: str) -> Any:
    try:
        return json.loads(value)
    except Exception:
        return {}

templates.env.filters["from_json"] = from_json

# ✅ テンプレート環境を app.state に格納（共通アクセス用）
app.state.templates = templates  # FastAPIの慣習的保存方法

# ========================================
# 🔀 ルートハンドラー
# ========================================
@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """
    ルートアクセス時は /dashboard にリダイレクト
    """
    return RedirectResponse(url="/dashboard")

@app.get("/main", include_in_schema=False)
async def main_alias() -> RedirectResponse:
    """
    /main へのアクセスも /dashboard にリダイレクト
    """
    return RedirectResponse(url="/dashboard")


# ========================================
# 各HTMLページのルートを追加
# ========================================

@app.get("/act-history", response_class=HTMLResponse)
async def show_act_history(request: Request):
    logs = [
        {"strategy": "Strategy A", "symbol": "USD/JPY", "timestamp": "2025-07-13", "score": 85},
        {"strategy": "Strategy B", "symbol": "EUR/USD", "timestamp": "2025-07-12", "score": 78},
    ]
    return templates.TemplateResponse("act_history.html", {"request": request, "logs": logs})

@app.get("/act-history/detail", response_class=HTMLResponse)
async def show_act_detail(request: Request, strategy_name: str = Query(...)):  # 修正: Queryを使ってパラメータを取得
    log = {"strategy": strategy_name, "symbol": "USD/JPY", "timestamp": "2025-07-13", "score": 85}  # 仮のデータ
    return templates.TemplateResponse("act_history_detail.html", {"request": request, "log": log})

@app.get("/base", response_class=HTMLResponse)
async def show_base(request: Request):
    return templates.TemplateResponse("base.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def show_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/king-history", response_class=HTMLResponse)
async def show_king_history(request: Request):
    return templates.TemplateResponse("king_history.html", {"request": request})

@app.get("/pdca-dashboard", response_class=HTMLResponse)
async def show_pdca_dashboard(request: Request):
    return templates.TemplateResponse("pdca_dashboard.html", {"request": request})

# 追加のHTMLファイルに対応するルートを追加
@app.get("/logs-dashboard", response_class=HTMLResponse)
async def show_logs_dashboard(request: Request):
    return templates.TemplateResponse("logs_dashboard.html", {"request": request})

@app.get("/pdca/pdca_history", response_class=HTMLResponse)
async def show_pdca_history(request: Request):
    return templates.TemplateResponse("pdca_history.html", {"request": request})

@app.get("/pdca/pdca_summary", response_class=HTMLResponse)
async def show_pdca_summary(request: Request):
    return templates.TemplateResponse("pdca_summary.html", {"request": request})

@app.get("/push-history", response_class=HTMLResponse)
async def show_push_history(request: Request):
    return templates.TemplateResponse("push_history.html", {"request": request})

@app.get("/push-history/detail", response_class=HTMLResponse)
async def show_push_history_detail(request: Request):
    return templates.TemplateResponse("push_history_detail.html", {"request": request})

@app.get("/scoreboard", response_class=HTMLResponse)
async def show_scoreboard(request: Request):
    return templates.TemplateResponse("scoreboard.html", {"request": request})

@app.get("/statistics/compare", response_class=HTMLResponse)
async def show_statistics_compare(request: Request):
    return templates.TemplateResponse("statistics_compare.html", {"request": request})

@app.get("/statistics/dashboard", response_class=HTMLResponse)
async def show_statistics_dashboard(request: Request):
    return templates.TemplateResponse("statistics_dashboard.html", {"request": request})

@app.get("/statistics/detail", response_class=HTMLResponse)
async def show_statistics_detail(request: Request):
    return templates.TemplateResponse("statistics_detail.html", {"request": request})

@app.get("/statistics/ranking", response_class=HTMLResponse)
async def show_statistics_ranking(request: Request):
    return templates.TemplateResponse("statistics_ranking.html", {"request": request})

@app.get("/statistics/scoreboard", response_class=HTMLResponse)
async def show_statistics_scoreboard(request: Request):
    return templates.TemplateResponse("statistics_scoreboard.html", {"request": request})

@app.get("/statistics/tag_ranking", response_class=HTMLResponse)
async def show_statistics_tag_ranking(request: Request):
    return templates.TemplateResponse("statistics_tag_ranking.html", {"request": request})

@app.get("/strategy/compare", response_class=HTMLResponse)
async def show_strategy_compare(request: Request):
    return templates.TemplateResponse("strategy_compare.html", {"request": request})

@app.get("/strategy/detail", response_class=HTMLResponse)
async def show_strategy_detail(request: Request):
    return templates.TemplateResponse("strategy_detail.html", {"request": request})

@app.get("/tag/detail", response_class=HTMLResponse)
async def show_tag_detail(request: Request):
    return templates.TemplateResponse("tag_detail.html", {"request": request})

@app.get("/tag/summary", response_class=HTMLResponse)
async def show_tag_summary(request: Request):
    return templates.TemplateResponse("tag_summary.html", {"request": request})

@app.get("/trigger", response_class=HTMLResponse)
async def show_trigger(request: Request):
    return templates.TemplateResponse("trigger.html", {"request": request})

@app.get("/upload-history", response_class=HTMLResponse)
async def show_upload_history(request: Request):
    return templates.TemplateResponse("upload_history.html", {"request": request})

@app.get("/upload-strategy", response_class=HTMLResponse)
async def show_upload_strategy(request: Request):
    return templates.TemplateResponse("upload_strategy.html", {"request": request})


# ========================================
# 🔁 ルーターの自動登録
# ========================================
routers = getattr(routes_pkg, "routers", None)
if routers is not None and isinstance(routers, (list, tuple)):
    for router in routers:
        app.include_router(router)
        print(f"🔗 router 統合: tags={getattr(router, 'tags', [])}")
else:
    print("⚠️ noctria_gui.routes に routers が定義されていません")
