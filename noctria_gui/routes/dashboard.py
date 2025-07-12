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

from fastapi import FastAPI, Request, Query, APIRouter
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# ========================================
# 依存関係のダミー実装 (自己完結して動作させるため)
# 実際の環境では、これらのダミークラス・変数を削除し、
# ご自身のプロジェクトのモジュールを正しくインポートしてください。
# ========================================

# --- ダミーのパス設定 ---
# プロジェクトのルートディレクトリを仮定
DUMMY_PROJECT_ROOT = Path("./noctria_kingdom_data")
NOCTRIA_GUI_STATIC_DIR = DUMMY_PROJECT_ROOT / "noctria_gui" / "static"
NOCTRIA_GUI_TEMPLATES_DIR = DUMMY_PROJECT_ROOT / "noctria_gui" / "templates"
ACT_LOG_DIR = DUMMY_PROJECT_ROOT / "logs" / "act"
PUSH_LOG_DIR = DUMMY_PROJECT_ROOT / "logs" / "push"

# --- ダミーのディレクトリとログファイルを作成 ---
def create_dummy_files():
    """アプリケーションがエラーなく起動するためのダミーファイルを作成"""
    dirs = [NOCTRIA_GUI_STATIC_DIR, NOCTRIA_GUI_TEMPLATES_DIR, ACT_LOG_DIR, PUSH_LOG_DIR]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    # ダミーのactログ
    with open(ACT_LOG_DIR / "log1.json", "w") as f:
        json.dump({"status": "promoted", "pushed_to_github": True, "score": {"win_rate": 80}}, f)
    with open(ACT_LOG_DIR / "log2.json", "w") as f:
        json.dump({"status": "rejected", "pushed_to_github": False, "score": {"win_rate": 45}}, f)
    # ダミーのpushログ
    with open(PUSH_LOG_DIR / "push1.json", "w") as f:
        json.dump({"commit": "abcde123"}, f)
    # ダミーのテンプレート
    if not (NOCTRIA_GUI_TEMPLATES_DIR / "dashboard.html").exists():
        with open(NOCTRIA_GUI_TEMPLATES_DIR / "dashboard.html", "w") as f:
            f.write("<h1>Dashboard Placeholder</h1><p>Please use the correct dashboard.html template.</p>")

create_dummy_files()


# --- ダミーの外部クラス ---
class PrometheusOracle:
    """PrometheusOracleのダミークラス"""
    def evaluate_model(self) -> Dict[str, float]:
        # 仮の評価指標を返す
        return {"RMSE": 0.015, "MAE": 0.011, "MAPE": 1.8}

class KingNoctria:
    """KingNoctriaのダミークラス"""
    def hold_council(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        # 仮の評議会結果を返す
        decision = random.choice(["BUY", "SELL", "STAY"])
        return {
            "final_decision": decision,
            "veritas": {"decision": decision, "score": round(random.uniform(0.6, 0.95), 3)},
            "prometheus_forecast": {"prediction": random.choice(["bullish", "bearish"]), "confidence": round(random.uniform(0.7, 0.9), 2)},
        }

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
# データ集計ロジック (ご提示のコードから)
# ========================================
def aggregate_dashboard_stats() -> Dict[str, Any]:
    """ダッシュボードに表示する各種統計情報を集計する"""
    stats = {
        "promoted_count": 0,
        "pushed_count": 0, # push数は別の関数で集計
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

# --- ダッシュボード表示 ---
@app.get("/dashboard", response_class=HTMLResponse)
async def show_dashboard(request: Request):
    """
    実データを集計してダッシュボードを表示する
    """
    # Oracle予測データを内部APIから取得
    try:
        # httpxを使って自分自身の/prometheus/predictエンドポイントを呼び出す
        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            res = await client.get("/prometheus/predict?n_days=14")
            res.raise_for_status()
            data = res.json()
            forecast_data = data.get("predictions", [])
    except Exception as e:
        forecast_data = []
        print(f"🔴 Oracle予測取得エラー: {e}")

    # 統計情報を集計
    stats = aggregate_dashboard_stats()
    stats["pushed_count"] = aggregate_push_stats()
    
    # テンプレートに渡すコンテキスト
    context = {
        "request": request,
        "forecast": forecast_data,
        "stats": stats,
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
    """
    評議会開催フォームからのPOSTリクエストを処理する
    """
    try:
        king = KingNoctria()
        council_result = king.hold_council(market_data.dict())
        return JSONResponse(content=council_result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})


# --- ダミーのOracle予測エンドポイント ---
@app.get("/prometheus/predict")
async def predict_prometheus(n_days: int = 14):
    """
    Chart.jsで描画するためのダミー予測データを返すAPI
    """
    forecast_data = []
    today = datetime.now()
    price = 150.0
    for i in range(n_days):
        date = today + timedelta(days=i)
        actual_price = price + random.uniform(-1.5, 1.5)
        pred_price = actual_price + random.uniform(-0.5, 0.5)
        forecast_data.append({
            "date": date.strftime("%Y-%m-%d"),
            "y_actual": round(actual_price, 2),
            "y_pred": round(pred_price, 2),
            "y_lower": round(pred_price - random.uniform(0.8, 1.2), 2),
            "y_upper": round(pred_price + random.uniform(0.8, 1.2), 2),
        })
        price = actual_price
    return {"predictions": forecast_data}

# ========================================
# その他のページのルート (変更なし)
# ========================================
# (ここでは簡略化のため省略しますが、必要に応じて他のHTMLページのルートを追加してください)
@app.get("/act-history", response_class=HTMLResponse)
async def show_act_history(request: Request):
    return templates.TemplateResponse("act_history.html", {"request": request, "logs": []})
