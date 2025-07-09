# routes/dashboard.py

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, ACT_LOG_DIR
from strategies.prometheus_oracle import PrometheusOracle  # ✅ Oracle本体インポート

from datetime import datetime
from pathlib import Path
from collections import defaultdict
import os
import json
import subprocess
from typing import Optional, Dict, Any
import io
import csv

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """'YYYY-MM-DD'形式の日付文字列→datetime。エラー時None"""
    try:
        if not date_str:
            return None
        return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return None


def aggregate_dashboard_stats() -> Dict[str, Any]:
    """
    📊 ダッシュボード用サマリ統計を集計（昇格数 / Push数 / PDCA数 / 勝率平均）
    + Oracleモデル評価指標（RMSE / MAE / MAPE）も追加
    """
    stats = {
        "promoted_count": 0,
        "push_count": 0,
        "pdca_count": 0,
        "avg_win_rate": 0.0,
        "oracle_metrics": {},  # 👈 精度指標
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
                stats["push_count"] += 1

            if "pdca_cycle" in data:
                stats["pdca_count"] += 1

            score = data.get("score", {})
            win = score.get("win_rate")
            if isinstance(win, (int, float)):
                win_rates.append(win)

        except Exception:
            continue

    stats["avg_win_rate"] = round(sum(win_rates) / len(win_rates), 1) if win_rates else 0.0

    # 📈 Oracleモデル評価追加
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
    """
    🏰 中央統治ダッシュボード画面
    - PrometheusOracle による市場予測（信頼区間付き）を描画
    - 戦略サマリ統計（昇格数・Push数・PDCA実行数など）表示
    """
    # 📈 市場予測呼び出し
    oracle = PrometheusOracle()
    df = oracle.predict_with_confidence(n_days=14)

    # ✅ 列名をテンプレート用に統一
    df = df.rename(columns={
        "forecast": "y_pred",
        "lower": "y_lower",
        "upper": "y_upper"
    })

    forecast_data = df.to_dict(orient="records")

    # 📊 サマリ統計集計（＋Oracle評価指標含む）
    stats = aggregate_dashboard_stats()

    # ✅ 実行メッセージ取得（クエリパラメータから）
    message = request.query_params.get("message")

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "forecast": forecast_data,
        "stats": stats,
        "message": message,
    })


@router.post("/oracle/predict")
async def trigger_oracle_prediction():
    """
    📈 GUIから PrometheusOracle を再実行するエンドポイント
    """
    try:
        subprocess.run(
            ["python3", "strategies/prometheus_oracle.py"],
            check=True,
            env={**os.environ, "PYTHONPATH": "."}
        )
        return RedirectResponse(url="/dashboard?message=success", status_code=303)
    except subprocess.CalledProcessError as e:
        print("🔴 Oracle実行失敗:", e)
        return RedirectResponse(url="/dashboard?message=error", status_code=303)


@router.get("/oracle/export")
async def export_oracle_csv():
    """
    📥 Oracle予測結果をCSVとしてダウンロード
    """
    oracle = PrometheusOracle()
    df = oracle.predict_with_confidence(n_days=14).rename(columns={
        "forecast": "y_pred",
        "lower": "y_lower",
        "upper": "y_upper"
    })

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["date", "y_pred", "y_lower", "y_upper"])
    for _, row in df.iterrows():
        writer.writerow([row["date"], row["y_pred"], row["y_lower"], row["y_upper"]])

    buffer.seek(0)
    return StreamingResponse(buffer, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=oracle_forecast.csv"
    })
