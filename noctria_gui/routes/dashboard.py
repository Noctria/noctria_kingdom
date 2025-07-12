#!/usr/bin/env python3
# coding: utf-8

# --- Standard Library Imports ---
import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path  # ★★★ この行が重要です: Pathオブジェクトをインポートします ★★★
from typing import Any, Dict

# --- Third-party Imports ---
import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# --- Local Application Imports ---
from core.king_noctria import KingNoctria
from core.path_config import (ACT_LOG_DIR, NOCTRIA_GUI_TEMPLATES_DIR,
                              PUSH_LOG_DIR)
from strategies.prometheus_oracle import PrometheusOracle

# ========================================
# ⚙️ ルーターとテンプレートのセットアップ
# ========================================
router = APIRouter(
    prefix="/dashboard",  # このルーターの全パスは /dashboard から始まる
    tags=["Dashboard"]    # FastAPIのドキュメント用のタグ
)

templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


# ========================================
# 📊 データ集計ロジック
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
            except Exception as e:
                print(f"Warning: Failed to process log file {file_name}. Error: {e}")
                continue
    
    stats["avg_win_rate"] = round(sum(win_rates) / len(win_rates), 1) if win_rates else 0.0

    try:
        oracle = PrometheusOracle()
        metrics = oracle.evaluate_model()
        stats["oracle_metrics"] = {
            "RMSE": metrics.get("RMSE", 0.0), "MAE": metrics.get("MAE", 0.0), "MAPE": metrics.get("MAPE", 0.0),
        }
    except Exception as e:
        print(f"Warning: Failed to get Oracle metrics. Error: {e}")
        stats["oracle_metrics"] = {"error": "N/A"}
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

@router.get("/", response_class=HTMLResponse)
async def show_dashboard(request: Request):
    """
    統計情報と予測データを集計し、メインのダッシュボードページをレンダリングします。
    """
    forecast_data = []
    try:
        # ダミーデータ生成ロジック
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
        print(f"🔴 Error generating forecast data: {e}")

    stats = aggregate_dashboard_stats()
    stats["pushed_count"] = aggregate_push_stats()
    
    context = {"request": request, "forecast": forecast_data, "stats": stats}
    return templates.TemplateResponse("dashboard.html", context)


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

@router.post("/king/hold-council", response_class=JSONResponse)
async def hold_council(market_data: MarketData):
    """
    評議会開催フォームからのPOSTリクエストを処理し、王の判断を返します。
    """
    try:
        king = KingNoctria()
        council_result = king.hold_council(market_data.dict())
        return JSONResponse(content=council_result)
    except Exception as e:
        print(f"🔴 Error during council meeting: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})

