#!/usr/bin/env python3
# coding: utf-8

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

# ✅ .env読み込み
load_dotenv(dotenv_path="/opt/airflow/.env")

AIRFLOW_API_URL = "http://airflow-webserver:8080/api/v1/dags/noctria_kingdom_pdca_dag/dagRuns"
AIRFLOW_USERNAME = os.getenv("AIRFLOW_USERNAME", "airflow")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "airflow")

app = FastAPI(title="Noctria GUI Trigger")

templates = Jinja2Templates(directory="noctria_gui/templates")

@app.get("/", response_class=HTMLResponse)
async def render_trigger_form(request: Request):
    return templates.TemplateResponse("trigger.html", {"request": request, "result": None})

@app.post("/trigger", response_class=HTMLResponse)
async def trigger_pdca_from_gui(request: Request, manual_reason: str = Form(...)):
    dag_run_id = f"manual_gui__{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    payload = {
        "dag_run_id": dag_run_id,
        "conf": {"trigger_source": manual_reason},
    }

    try:
        res = requests.post(
            AIRFLOW_API_URL,
            auth=(AIRFLOW_USERNAME, AIRFLOW_PASSWORD),
            json=payload,
            timeout=10,
        )
        if res.status_code == 200:
            return templates.TemplateResponse("trigger.html", {
                "request": request,
                "result": f"✅ 王命を発令しました: {dag_run_id}"
            })
        else:
            return templates.TemplateResponse("trigger.html", {
                "request": request,
                "result": f"❌ 発令失敗: {res.status_code} {res.text}"
            })
    except Exception as e:
        return templates.TemplateResponse("trigger.html", {
            "request": request,
            "result": f"❌ 通信エラー: {e}"
        })
