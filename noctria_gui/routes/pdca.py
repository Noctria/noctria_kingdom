#!/usr/bin/env python3
# coding: utf-8

"""
📜 PDCA履歴管理ルート
- 実行ログの表示・フィルタリング・再送命令（DAGトリガー）を統括
"""

from fastapi import APIRouter, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
from pathlib import Path
import os
import json
import requests

from core.path_config import (
    PDCA_LOG_DIR,
    VERITAS_ORDER_JSON,
    NOCTRIA_GUI_TEMPLATES_DIR,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


# ========================================
# 📜 /pdca - 履歴表示ページ（フィルター＋ソート対応）
# ========================================
@router.get("/pdca", response_class=HTMLResponse)
async def show_pdca_dashboard(
    request: Request,
    strategy: str = Query(default=None),
    symbol: str = Query(default=None),
    signal: str = Query(default=None),
    date_from: str = Query(default=None),
    date_to: str = Query(default=None),
    sort: str = Query(default=None),
):
    log_files = sorted(PDCA_LOG_DIR.glob("*.json"), reverse=True)
    logs = []

    for log_file in log_files:
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"⚠️ ログ読み込み失敗: {log_file} -> {e}")
            continue

        ts = data.get("timestamp", "")
        try:
            ts_dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")
        except Exception:
            ts_dt = None

        log_entry = {
            "filename": log_file.name,
            "path": str(log_file),
            "strategy": data.get("strategy", "N/A"),
            "timestamp": ts,
            "timestamp_dt": ts_dt,
            "signal": data.get("signal", "N/A"),
            "symbol": data.get("symbol", "N/A"),
            "lot": data.get("lot", "N/A"),
            "tp": data.get("tp", "N/A"),
            "sl": data.get("sl", "N/A"),
            "win_rate": data.get("win_rate"),
            "max_dd": data.get("max_dd"),
            "trades": data.get("trades"),
            "json_text": json.dumps(data, indent=2, ensure_ascii=False),
        }

        logs.append(log_entry)

    # 🔍 フィルター処理
    def matches(log):
        if strategy and strategy.lower() not in log["strategy"].lower():
            return False
        if symbol and symbol != log["symbol"]:
            return False
        if signal and signal != log["signal"]:
            return False
        if date_from:
            try:
                from_dt = datetime.strptime(date_from, "%Y-%m-%d")
                if log["timestamp_dt"] and log["timestamp_dt"] < from_dt:
                    return False
            except:
                pass
        if date_to:
            try:
                to_dt = datetime.strptime(date_to, "%Y-%m-%d")
                if log["timestamp_dt"] and log["timestamp_dt"] > to_dt:
                    return False
            except:
                pass
        return True

    filtered_logs = [log for log in logs if matches(log)]

    # 🔃 ソート処理
    def get_sort_key_func(key):
        return lambda log: log.get(key) or 0

    if sort:
        reverse = False
        sort_key = sort
        if sort.startswith("-"):
            sort_key = sort[1:]
            reverse = True
        if sort_key in ["win_rate", "max_dd", "trades", "timestamp_dt"]:
            filtered_logs.sort(key=get_sort_key_func(sort_key), reverse=reverse)

    return templates.TemplateResponse("pdca_dashboard.html", {
        "request": request,
        "logs": filtered_logs,
        "filters": {
            "strategy": strategy or "",
            "symbol": symbol or "",
            "signal": signal or "",
            "date_from": date_from or "",
            "date_to": date_to or "",
        },
        "sort": sort or ""
    })


# ========================================
# 🔁 /pdca/replay - 再送命令 & DAGトリガー
# ========================================
@router.post("/pdca/replay")
async def replay_order_from_log(log_path: str = Form(...)):
    airflow_url = os.environ.get("AIRFLOW_API_URL", "http://localhost:8080/api/v1")
    dag_id = "veritas_replay_dag"

    payload = {
        "conf": {"log_path": log_path}
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(
            f"{airflow_url}/dags/{dag_id}/dagRuns",
            json=payload,
            headers=headers,
            auth=("airflow", "airflow")  # 必要に応じて認証情報を修正
        )

        if response.status_code in [200, 201]:
            print(f"✅ 再送DAG起動成功: {log_path}")
            return RedirectResponse(url="/pdca", status_code=303)
        else:
            print("❌ DAGトリガー失敗:", response.text)
            return JSONResponse(status_code=500, content={"detail": "DAG起動に失敗しました"})

    except Exception as e:
        print("❌ DAG通信エラー:", str(e))
        return JSONResponse(status_code=500, content={"detail": str(e)})
