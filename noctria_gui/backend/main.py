#!/usr/bin/env python3
# coding: utf-8

import sys
from pathlib import Path
import json
from typing import Any, Dict
import random
from datetime import datetime, timedelta

# core.path_config と noctria_gui.routes をインポート
from core.path_config import NOCTRIA_GUI_STATIC_DIR, NOCTRIA_GUI_TEMPLATES_DIR
import noctria_gui.routes as routes_pkg

from fastapi import FastAPI, Request, Query
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

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
    """Jinja2テンプレート内でJSON文字列をPythonオブジェクトに変換するフィルタ"""
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
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
    # 仮のログデータ
    logs = [
        {"strategy": "Strategy A", "symbol": "USD/JPY", "timestamp": "2025-07-13", "score": 85},
        {"strategy": "Strategy B", "symbol": "EUR/USD", "timestamp": "2025-07-12", "score": 78},
    ]
    return templates.TemplateResponse("act_history.html", {"request": request, "logs": logs})

@app.get("/act-history/detail", response_class=HTMLResponse)
async def show_act_detail(request: Request, strategy_name: str = Query(...)):
    # クエリパラメータで受け取った戦略名に基づく仮のデータ
    log = {"strategy": strategy_name, "symbol": "USD/JPY", "timestamp": "2025-07-13", "score": 85}
    return templates.TemplateResponse("act_history_detail.html", {"request": request, "log": log})

@app.get("/base", response_class=HTMLResponse)
async def show_base(request: Request):
    return templates.TemplateResponse("base.html", {"request": request})

# 修正点: dashboardにHTMLが必要とする全ての統計情報とグラフデータを渡す
@app.get("/dashboard", response_class=HTMLResponse)
async def show_dashboard(request: Request):
    """
    ダッシュボードページを表示します。
    テンプレートで必要となる統計情報(stats)とグラフデータ(forecast)を渡します。
    """
    # 修正点: HTMLテンプレートが要求するキー(oracle_metrics, promoted_countなど)を全て含むようにstats_dataを定義
    stats_data = {
        "avg_win_rate": 75.8,
        "promoted_count": 42,
        "pushed_count": 123,
        "oracle_metrics": {
            "RMSE": 0.0123,
            "MAE": 0.0098,
            "MAPE": 1.5
        }
    }

    # Chart.jsで描画するためのダミー予測データ
    forecast_data = []
    today = datetime.now()
    price = 150.0
    for i in range(30):
        date = today - timedelta(days=i)
        actual_price = price + random.uniform(-1.5, 1.5)
        pred_price = actual_price + random.uniform(-0.5, 0.5)
        forecast_data.append({
            "date": date.strftime("%m-%d"),
            "y_actual": round(actual_price, 2),
            "y_pred": round(pred_price, 2),
            "y_lower": round(pred_price - random.uniform(0.8, 1.2), 2),
            "y_upper": round(pred_price + random.uniform(0.8, 1.2), 2),
        })
        price = actual_price
    forecast_data.reverse() # 日付を昇順にする

    context = {
        "request": request,
        "stats": stats_data,
        "forecast": forecast_data
    }
    return templates.TemplateResponse("dashboard.html", context)


# Pydanticモデルを定義してリクエストボディの型を定義
class MarketData(BaseModel):
    price: float
    previous_price: float | None = None
    volume: float | None = None
    spread: float | None = None
    order_block: float | None = None
    volatility: float | None = None
    trend_prediction: str | None = None
    sentiment: float | None = None
    trend_strength: float | None = None
    liquidity_ratio: float | None = None
    momentum: float | None = None
    short_interest: float | None = None

# 追加: /king/hold-council エンドポイント
@app.post("/king/hold-council", response_class=JSONResponse)
async def hold_council(market_data: MarketData):
    """
    評議会開催フォームからのリクエストを処理するAPIエンドポイント。
    ダミーの判断結果を返します。
    """
    decision = random.choice(["BUY", "SELL", "STAY"])
    response_data = {
        "final_decision": decision,
        "veritas": {"decision": decision, "score": round(random.uniform(0.6, 0.95), 3)},
        "prometheus_forecast": {"prediction": random.choice(["bullish", "bearish"]), "confidence": round(random.uniform(0.7, 0.9), 2)},
        "aurus": "OK",
        "levia": "OK",
        "noctus": "OK",
        "received_data": market_data.dict()
    }
    return JSONResponse(content=response_data)


@app.get("/king-history", response_class=HTMLResponse)
async def show_king_history(request: Request):
    return templates.TemplateResponse("king_history.html", {"request": request})

@app.get("/pdca-dashboard", response_class=HTMLResponse)
async def show_pdca_dashboard(request: Request):
    return templates.TemplateResponse("pdca_dashboard.html", {"request": request})

# (以下、他のエンドポイントは変更なし)
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
