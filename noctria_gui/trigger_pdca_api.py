#!/usr/bin/env python3
# coding: utf-8

"""
🚀 /trigger - FastAPI GUI → Airflow DAG Triggerルート
- 王命（DAGトリガー）をGUIフォームから発令
"""

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path
import requests
import os

# =========================
# ✅ 環境変数読み込み（Airflowと共有）
# =========================
dotenv_path = Path("/opt/airflow/.env")
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)

AIRFLOW_API_URL = "http://airflow-webserver:8080/api/v1/dags/noctria_kingdom_pdca_dag/dagRuns"
AIRFLOW_USERNAME = os.getenv("AIRFLOW_USERNAME", "airflow")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "airflow")

# =========================
# ✅ FastAPI Router 初期化
# =========================
router = APIRouter(prefix="/trigger", tags=["Trigger"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# =========================
# 📄 トリガーフォーム表示
# =========================
@router.get("/", response_class=HTMLResponse)
async def render_trigger_form(request: Request):
    return templates.TemplateResponse("trigger.html", {
        "request": request,
        "result": None
    })

# =========================
# 🚀 DAGトリガー実行
# =========================
@router.post("/", response_class=HTMLResponse)
async def trigger_pdca_from_gui(
    request: Request,
    manual_reason: str = Form(...)
):
    dag_run_id = f"manual_gui__{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    payload = {
        "dag_run_id": dag_run_id,
        "conf": {"trigger_source": manual_reason}
    }

    try:
        response = requests.post(
            AIRFLOW_API_URL,
            auth=(AIRFLOW_USERNAME, AIRFLOW_PASSWORD),
            json=payload,
            timeout=10
        )

        if response.status_code in (200, 201):
            result_msg = f"✅ 王命を発令しました: {dag_run_id}"
        else:
            result_msg = f"❌ 発令失敗: {response.status_code} - {response.text}"

    except Exception as e:
        result_msg = f"❌ 通信エラー: {e}"

    return templates.TemplateResponse("trigger.html", {
        "request": request,
        "result": result_msg
    })
