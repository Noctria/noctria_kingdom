from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, ACT_LOG_DIR, ORACLE_FORECAST_JSON
from strategies.prometheus_oracle import PrometheusOracle
from core.king_noctria import KingNoctria

from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import os
import json
import subprocess
import io
import csv
import httpx

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    try:
        if not date_str:
            return None
        return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return None


def aggregate_dashboard_stats() -> Dict[str, Any]:
    stats = {
        "promoted_count": 0,
        "pushed_count": 0,
        "pdca_count": 0,
        "avg_win_rate": 0.0,
        "oracle_metrics": {},
    }

    act_dir = Path(ACT_LOG_DIR)
    win_rates = []

    for file in os.listdir(act_dir):
        if not file.endswith(".json"):
            continue
        try:
            with open(act_dir / file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if data.get("status") == "promoted":
                stats["promoted_count"] += 1

            if data.get("pushed_to_github"):
                stats["pushed_count"] += 1

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
            "RMSE": round(metrics.get("RMSE", 0.0), 4),
            "MAE": round(metrics.get("MAE", 0.0), 4),
            "MAPE": round(metrics.get("MAPE", 0.0), 4),
        }
    except Exception as e:
        stats["oracle_metrics"] = {"error": str(e)}

    return stats


@router.get("/dashboard", response_class=HTMLResponse)
async def show_dashboard(request: Request):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get("http://localhost:8000/prometheus/predict?n_days=14")
            res.raise_for_status()
            data = res.json()
            forecast_data = data.get("predictions", [])
    except Exception as e:
        forecast_data = []
        print("🔴 Oracle予測取得エラー:", e)

    stats = aggregate_dashboard_stats()
    message = request.query_params.get("message")

    try:
        king = KingNoctria()
        mock_market = {
            "price": 1.2530,
            "previous_price": 1.2510,
            "volume": 160,
            "spread": 0.012,
            "order_block": 0.4,
            "volatility": 0.18,
            "trend_prediction": "bullish",
            "sentiment": 0.7,
            "trend_strength": 0.6,
            "liquidity_ratio": 1.1,
            "momentum": 0.8,
            "short_interest": 0.3
        }
        council_result = king.hold_council(mock_market)
    except Exception as e:
        print("🔴 評議会開催エラー:", e)
        council_result = {}

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "forecast": forecast_data,
        "stats": stats,
        "message": message,
        "council": council_result
    })


@router.post("/oracle/predict")
async def trigger_oracle_prediction(
    from_date: Optional[str] = Form(None),
    to_date: Optional[str] = Form(None)
):
    try:
        oracle = PrometheusOracle()
        df = oracle.predict_with_confidence(from_date=from_date, to_date=to_date)
        df = df.rename(columns={
            "forecast": "y_pred",
            "lower": "y_lower",
            "upper": "y_upper"
        })

        ORACLE_FORECAST_JSON.parent.mkdir(parents=True, exist_ok=True)
        df.to_json(ORACLE_FORECAST_JSON, orient="records", force_ascii=False)

        return RedirectResponse(url="/dashboard?message=success", status_code=303)
    except Exception as e:
        print("🔴 Oracle予測失敗:", e)
        return RedirectResponse(url="/dashboard?message=error", status_code=303)


@router.get("/oracle/export")
async def export_oracle_csv():
    try:
        oracle = PrometheusOracle()
        df = oracle.predict_with_confidence(n_days=14).rename(columns={
            "forecast": "y_pred",
            "lower": "y_lower",
            "upper": "y_upper"
        })

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["date", "y_pred", "y_lower", "y_upper", "y_true"])
        for _, row in df.iterrows():
            writer.writerow([row["date"], row["y_pred"], row["y_lower"], row["y_upper"], row.get("y_true", "")])

        buffer.seek(0)
        return StreamingResponse(buffer, media_type="text/csv", headers={
            "Content-Disposition": "attachment; filename=oracle_forecast.csv"
        })

    except Exception as e:
        print("🔴 CSVエクスポート失敗:", e)
        return RedirectResponse(url="/dashboard?message=error", status_code=303)
