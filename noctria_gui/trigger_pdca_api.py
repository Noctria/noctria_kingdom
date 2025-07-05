#!/usr/bin/env python3
# coding: utf-8

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

# ✅ .envの読み込み（/opt/airflow 環境前提）
load_dotenv(dotenv_path="/opt/airflow/.env")

# 🔐 Airflow API 認証情報
AIRFLOW_API_URL = "http://airflow-webserver:8080/api/v1/dags/noctria_kingdom_pdca_dag/dagRuns"
AIRFLOW_USERNAME = os.getenv("AIRFLOW_USERNAME", "airflow")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "airflow")

app = FastAPI(title="Noctria Kingdom PDCA Trigger API")

class TriggerRequest(BaseModel):
    manual_reason: str = "GUIからの王命"

@app.post("/trigger-pdca/")
def trigger_pdca(request: TriggerRequest):
    """👑 GUI からの PDCA サイクル起動API"""
    dag_run_id = f"manual_trigger__{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    payload = {
        "dag_run_id": dag_run_id,
        "conf": {"trigger_source": request.manual_reason},
    }

    try:
        response = requests.post(
            AIRFLOW_API_URL,
            auth=(AIRFLOW_USERNAME, AIRFLOW_PASSWORD),
            json=payload,
            timeout=10,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Airflowへの接続失敗: {e}")

    if response.status_code == 200:
        return {
            "status": "success",
            "message": f"✅ 王命を発令しました: {dag_run_id}",
            "dag_run_id": dag_run_id
        }
    else:
        raise HTTPException(status_code=response.status_code, detail=f"Airflow応答: {response.text}")
