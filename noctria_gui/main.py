#!/usr/bin/env python3
# coding: utf-8

import sys
from pathlib import Path
import json
from typing import Any, Dict, List
import random
from datetime import datetime, timedelta
import os
import httpx
import io
import csv

# FastAPI関連のインポート
from fastapi import FastAPI, Request, Query, APIRouter
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# プロジェクトのコアモジュールをインポート
from core.path_config import NOCTRIA_GUI_STATIC_DIR, NOCTRIA_GUI_TEMPLATES_DIR, ACT_LOG_DIR, PUSH_LOG_DIR
from strategies.prometheus_oracle import PrometheusOracle
from core.king_noctria import KingNoctria
import noctria_gui.routes as routes_pkg

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

# ✅ Jinja2 カスタムフィルタ
def from_json(value: str) -> Any:
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}
templates.env.filters["from_json"] = from_json

# ========================================
# データ集計ロジック
# ========================================
def aggregate_dashboard_stats() -> Dict[str, Any]:
    """ダッシュボードに表示する各種統計情報を集計する"""
    stats = {
        "promoted_count": 0,
        "pushed_count": 0,
        "pdca_count": 0,
        "avg_win_rate": 0.0,
        "oracle_metrics": {},
        "recheck_success": 0,
        "recheck_fail": 0,
    }
    act_dir = Path(ACT_LOG_DIR)
    win_rates = []

    if act_dir.exists():
        for file_name in os.listdir(act_dir):
            if not file_name.endswith(".json"):
                continue
            try:
                with open(act_dir / file_name, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("status") == "promoted":
                    stats["promoted_count"] += 1
                if "pdca_cycle" in data:
                    stats["pdca_count"] += 1
                win = data.get("score", {}).get("win_rate")
                if isinstance(win, (int, float)):
                    win_rates.append(win)
            except Exception:
                continue
    
    stats["avg_win_rate"] = round(sum(win_rates) / len(win_rates), 1) if win_rates else 0.0

    try:
        oracle = PrometheusOracle()
        metrics = oracle.evaluate_model()
        stats["oracle_metrics"] = {
            "RMSE": metrics.get("RMSE", 0.0),
            "MAE": metrics.get("MAE", 0.0),
            "MAPE": metrics.get("MAPE", 0.0),
        }
    except Exception as e:
        stats["oracle_metrics"] = {"error": str(e)}

    return stats

def aggregate_push_stats() -> int:
    """Pushログの数を集計する"""
    push_dir = Path(PUSH_LOG_DIR)
    if not push_dir.exists():
        return 0
    return len([name for name in os.listdir(push_dir) if name.endswith(".json")])

# ========================================
# 🔀 ルートハンドラー
# ========================================
@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard")

@app.get("/main", include_in_schema=False)
async def main_alias() -> RedirectResponse:
    return RedirectResponse(url="/dashboard")

# --- ダッシュボード表示 (修正版) ---
@app.get("/dashboard", response_class=HTMLResponse)
async def show_dashboard(request: Request):
    """実データを集計してダッシュボードを表示する"""
    forecast_data = []
    # Oracle予測データを取得 (実際のAPIエンドポイントを呼び出す)
    # この例では、内部APIを呼び出す代わりにダミーデータを生成
    try:
        # async with httpx.AsyncClient() as client:
        #     res = await client.get("http://localhost:8001/prometheus/predict?n_days=14") # 実際のAPIサーバーのURL
        #     res.raise_for_status()
        #     forecast_data = res.json().get("predictions", [])
        
        # ダミーデータ生成ロジック (APIが利用できない場合の代替)
        today = datetime.now()
        price = 150.0
        for i in range(14):
            date = today + timedelta(days=i)
            actual_price = price + random.uniform(-1.5, 1.5)
            pred_price = actual_price + random.uniform(-0.5, 0.5)
            forecast_data.append({
                "date": date.strftime("%Y-%m-%d"),
                "y_actual": round(actual_price, 2), "y_pred": round(pred_price, 2),
                "y_lower": round(pred_price - 1.5, 2), "y_upper": round(pred_price + 1.5, 2),
            })
            price = actual_price

    except Exception as e:
        print(f"🔴 Oracle予測取得エラー: {e}")

    stats = aggregate_dashboard_stats()
    stats["pushed_count"] = aggregate_push_stats()
    
    context = {
        "request": request, "forecast": forecast_data, "stats": stats,
    }
    return templates.TemplateResponse("dashboard.html", context)

# --- 評議会開催フォームの処理 ---
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

@app.post("/king/hold-council", response_class=JSONResponse)
async def hold_council(market_data: MarketData):
    """評議会開催フォームからのPOSTリクエストを処理する"""
    try:
        king = KingNoctria()
        council_result = king.hold_council(market_data.dict())
        return JSONResponse(content=council_result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

# ========================================
# 各HTMLページのルートを追加 (ユーザー提供コードから)
# ========================================
@app.get("/act-history", response_class=HTMLResponse)
async def show_act_history(request: Request):
    logs = [
        {"strategy": "Strategy A", "symbol": "USD/JPY", "timestamp": "2025-07-13", "score": 85},
        {"strategy": "Strategy B", "symbol": "EUR/USD", "timestamp": "2025-07-12", "score": 78},
    ]
    return templates.TemplateResponse("act_history.html", {"request": request, "logs": logs})

@app.get("/act-history/detail", response_class=HTMLResponse)
async def show_act_detail(request: Request, strategy_name: str = Query(...)):
    log = {"strategy": strategy_name, "symbol": "USD/JPY", "timestamp": "2025-07-13", "score": 85}
    return templates.TemplateResponse("act_history_detail.html", {"request": request, "log": log})

@app.get("/base", response_class=HTMLResponse)
async def show_base(request: Request):
    return templates.TemplateResponse("base.html", {"request": request})

@app.get("/king-history", response_class=HTMLResponse)
async def show_king_history(request: Request):
    return templates.TemplateResponse("king_history.html", {"request": request})

@app.get("/pdca-dashboard", response_class=HTMLResponse)
async def show_pdca_dashboard(request: Request):
    return templates.TemplateResponse("pdca_dashboard.html", {"request": request})

@app.get("/logs-dashboard", response_class=HTMLResponse)
async def show_logs_dashboard(request: Request):
    return templates.TemplateResponse("logs_dashboard.html", {"request": request})

# (以下、他の多くのエンドポイントも同様にここに含まれます)
# ... 省略 ...

# ========================================
# 🔁 ルーターの自動登録 (ユーザー提供コードから)
# ========================================
routers = getattr(routes_pkg, "routers", None)
if routers is not None and isinstance(routers, (list, tuple)):
    for router in routers:
        app.include_router(router)
        print(f"🔗 router 統合: tags={getattr(router, 'tags', [])}")
else:
    print("⚠️ noctria_gui.routes に routers が定義されていません")
