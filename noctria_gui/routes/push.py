#!/usr/bin/env python3
# coding: utf-8

"""
📦 Push機能統合ルート
- Airflow DAG経由のGitHub Pushトリガー
- Pushログの閲覧／検索／CSV出力／詳細表示
"""

from fastapi import APIRouter, Request, Query, Form, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
import requests
import logging
import json
import csv
import io
import os

from core.path_config import PUSH_LOG_DIR, GUI_TEMPLATES_DIR

router = APIRouter(tags=["Push機能"])
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))

# ----------------------------------------
# 📤 DAGトリガー（GitHub Push）
# ----------------------------------------

class DAGTriggerResponse(BaseModel):
    detail: str
    dag_run_id: str | None = None
    response_body: str | None = None

@router.post("/push/trigger", response_model=DAGTriggerResponse)
async def trigger_push_dag(strategy_name: str = Form(...)):
    """
    Airflow経由でGitHubにPushするDAGをトリガー（veritas_push_dag）
    """
    strategy_name = strategy_name.strip()
    if not strategy_name:
        raise HTTPException(status_code=400, detail="strategy_name が空です")

    dag_run_id = f"veritas_push__{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    airflow_url = os.getenv("AIRFLOW_BASE_URL", "http://airflow-webserver:8080")
    dag_trigger_url = f"{airflow_url}/api/v1/dags/veritas_push_dag/dagRuns"

    payload = {
        "dag_run_id": dag_run_id,
        "conf": {
            "strategy_name": strategy_name
        }
    }

    try:
        response = requests.post(
            dag_trigger_url,
            auth=(os.getenv("AIRFLOW_USERNAME", "airflow"),
                  os.getenv("AIRFLOW_PASSWORD", "airflow")),
            json=payload,
            timeout=10
        )

        if response.status_code in (200, 201):
            return DAGTriggerResponse(
                detail=f"✅ DAGトリガー成功 (Run ID: {dag_run_id})",
                dag_run_id=dag_run_id
            )

        return DAGTriggerResponse(
            detail=f"❌ Airflowエラー応答 (HTTP {response.status_code})",
            response_body=response.text
        )

    except requests.RequestException as e:
        return DAGTriggerResponse(
            detail=f"🚨 Airflow通信失敗: {str(e)}"
        )

# ----------------------------------------
# 📋 Push履歴表示（GET /push/history）
# ----------------------------------------

PAGE_SIZE = 50

@router.get("/push/history", response_class=HTMLResponse)
def view_push_history(
    request: Request,
    strategy: str = Query(default="", description="戦略名"),
    tag: str = Query(default="", description="タグ"),
    start_date: str = Query(default="", description="開始日"),
    end_date: str = Query(default="", description="終了日"),
    keyword: str = Query(default="", description="メッセージ検索"),
    sort: str = Query(default="desc", description="並び順"),
    page: int = Query(default=1, ge=1)
):
    logs = []

    if not PUSH_LOG_DIR.exists():
        PUSH_LOG_DIR.mkdir(parents=True)

    for file in sorted(PUSH_LOG_DIR.glob("*.json")):
        with open(file, "r", encoding="utf-8") as f:
            log = json.load(f)

            if strategy and strategy not in log.get("strategy", ""):
                continue
            if tag and tag != log.get("tag", ""):
                continue
            if keyword and keyword.lower() not in log.get("message", "").lower():
                continue

            log_date = log.get("timestamp", "")[:10]
            if start_date and log_date < start_date:
                continue
            if end_date and log_date > end_date:
                continue

            logs.append(log)

    logs.sort(
        key=lambda x: x.get("timestamp", ""),
        reverse=(sort != "asc")
    )

    tag_list = sorted({log.get("tag") for log in logs if log.get("tag")})

    total_count = len(logs)
    total_pages = max((total_count + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    page = min(page, total_pages)
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    paged_logs = logs[start:end]

    return templates.TemplateResponse("push_history.html", {
        "request": request,
        "logs": paged_logs,
        "tag_list": tag_list,
        "filters": {
            "strategy": strategy,
            "tag": tag,
            "start_date": start_date,
            "end_date": end_date,
            "keyword": keyword,
            "sort": sort,
        },
        "total_count": total_count,
        "total_pages": total_pages,
        "current_page": page,
        "page_size": PAGE_SIZE,
    })

# ----------------------------------------
# 📤 CSV出力（GET /push/export）
# ----------------------------------------

@router.get("/push/export")
def export_push_history_csv(
    strategy: str = Query(default=""),
    tag: str = Query(default=""),
    start_date: str = Query(default=""),
    end_date: str = Query(default=""),
    keyword: str = Query(default="")
):
    logs = []

    for file in sorted(PUSH_LOG_DIR.glob("*.json")):
        with open(file, "r", encoding="utf-8") as f:
            log = json.load(f)

            if strategy and strategy not in log.get("strategy", ""):
                continue
            if tag and tag != log.get("tag", ""):
                continue
            if keyword and keyword.lower() not in log.get("message", "").lower():
                continue

            log_date = log.get("timestamp", "")[:10]
            if start_date and log_date < start_date:
                continue
            if end_date and log_date > end_date:
                continue

            logs.append(log)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["timestamp", "strategy", "tag", "message", "signature"])
    writer.writeheader()

    for log in logs:
        writer.writerow({
            "timestamp": log.get("timestamp", ""),
            "strategy": log.get("strategy", ""),
            "tag": log.get("tag", ""),
            "message": log.get("message", ""),
            "signature": log.get("signature", "")
        })

    output.seek(0)
    filename = f"push_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(output, media_type="text/csv", headers={
        "Content-Disposition": f"attachment; filename={filename}"
    })

# ----------------------------------------
# 🔍 詳細表示（GET /push/detail）
# ----------------------------------------

@router.get("/push/detail", response_class=HTMLResponse)
def push_history_detail(request: Request, timestamp: str):
    log_path = PUSH_LOG_DIR / f"{timestamp}.json"
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="Log not found")

    with open(log_path, "r", encoding="utf-8") as f:
        log = json.load(f)

    return templates.TemplateResponse("push_history_detail.html", {
        "request": request,
        "log": log
    })
