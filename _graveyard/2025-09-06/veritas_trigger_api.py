#!/usr/bin/env python3
# coding: utf-8

"""
📡 veritas_trigger_api.py - Airflow DAGトリガーAPI
- 外部APIルート: /trigger/veritas（FastAPI経由）
- 内部関数: trigger_recheck_dag(strategy_name)（FastAPI以外のPython内部呼び出し用）
- 🆕 trigger_generate_dag(symbol, tag, target_metric)：戦略生成用
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
import os
from datetime import datetime
import logging

router = APIRouter()

# ✅ ログ設定
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
log_path = os.path.join(LOG_DIR, "veritas_trigger.log")
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ===============================
# ✅ 外部呼び出し用 FastAPI ルート
# ===============================
class VeritasTriggerRequest(BaseModel):
    conf: dict = {}
    dag_id: str = "veritas_master_dag"

@router.post("/trigger/veritas")
def trigger_veritas(request: VeritasTriggerRequest):
    """
    🔁 API経由で DAG をトリガー（汎用）
    """
    AIRFLOW_API_URL = os.getenv("AIRFLOW_API_URL", "http://localhost:8080/api/v1")
    AIRFLOW_USERNAME = os.getenv("AIRFLOW_USERNAME", "airflow")
    AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "airflow")

    execution_date = datetime.utcnow().isoformat()
    payload = {
        "conf": request.conf,
        "execution_date": execution_date
    }

    trigger_url = f"{AIRFLOW_API_URL}/dags/{request.dag_id}/dagRuns"

    try:
        response = requests.post(
            trigger_url,
            auth=(AIRFLOW_USERNAME, AIRFLOW_PASSWORD),
            json=payload
        )

        if response.status_code in (200, 201, 202):
            logging.info(f"[TRIGGERED] DAG={request.dag_id} | Payload={payload}")
            return {
                "status": "success",
                "dag_id": request.dag_id,
                "execution_date": execution_date,
                "response": response.json()
            }
        else:
            logging.error(f"[FAILED] {response.status_code}: {response.text}")
            raise HTTPException(status_code=response.status_code, detail=response.text)

    except Exception as e:
        logging.exception("[ERROR] Exception while triggering DAG")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================
# ✅ 内部からの関数呼び出し用（GUI連携向け）
# =========================================
def trigger_recheck_dag(strategy_name: str) -> requests.Response:
    """
    📌 GUIルートなどから Airflow DAG を直接トリガーするための関数（再評価用）
    """
    AIRFLOW_API_URL = os.getenv("AIRFLOW_API_URL", "http://localhost:8080/api/v1")
    AIRFLOW_USERNAME = os.getenv("AIRFLOW_USERNAME", "airflow")
    AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "airflow")
    dag_id = "veritas_recheck_dag"

    execution_date = datetime.utcnow().isoformat()
    payload = {
        "conf": {"strategy_name": strategy_name},
        "execution_date": execution_date
    }

    trigger_url = f"{AIRFLOW_API_URL}/dags/{dag_id}/dagRuns"

    response = requests.post(
        trigger_url,
        auth=(AIRFLOW_USERNAME, AIRFLOW_PASSWORD),
        json=payload
    )

    if response.status_code in (200, 201, 202):
        logging.info(f"[TRIGGERED] DAG={dag_id} | strategy={strategy_name} | Payload={payload}")
    else:
        logging.error(f"[FAILED] DAG={dag_id} | Status={response.status_code} | Text={response.text}")

    return response


# =========================================
# 🆕 内部からの呼び出し用（戦略生成用）
# =========================================
def trigger_generate_dag(symbol: str = "", tag: str = "", target_metric: str = "") -> requests.Response:
    """
    🧠 Veritas戦略生成 DAG（veritas_generate_dag）をトリガー
    """
    AIRFLOW_API_URL = os.getenv("AIRFLOW_API_URL", "http://localhost:8080/api/v1")
    AIRFLOW_USERNAME = os.getenv("AIRFLOW_USERNAME", "airflow")
    AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "airflow")
    dag_id = "veritas_generate_dag"

    execution_date = datetime.utcnow().isoformat()
    payload = {
        "conf": {
            "symbol": symbol,
            "tag": tag,
            "target_metric": target_metric
        },
        "execution_date": execution_date
    }

    trigger_url = f"{AIRFLOW_API_URL}/dags/{dag_id}/dagRuns"

    response = requests.post(
        trigger_url,
        auth=(AIRFLOW_USERNAME, AIRFLOW_PASSWORD),
        json=payload
    )

    if response.status_code in (200, 201, 202):
        logging.info(f"[TRIGGERED] DAG={dag_id} | Payload={payload}")
    else:
        logging.error(f"[FAILED] DAG={dag_id} | Status={response.status_code} | Text={response.text}")

    return response
