from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
import requests
import os
import json
from datetime import datetime
import logging

# ✅ ログ設定
LOG_DIR = os.getenv("VERITAS_LOG_DIR", "./logs")
os.makedirs(LOG_DIR, exist_ok=True)
log_path = os.path.join(LOG_DIR, "veritas_trigger.log")

logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ✅ FastAPI起動
app = FastAPI(title="Veritas Trigger API")

# ✅ リクエストボディ定義
class VeritasTriggerRequest(BaseModel):
    conf: dict = {}
    dag_id: str = "veritas_master_dag"  # デフォルト値を指定可能

@app.post("/trigger/veritas")
def trigger_veritas(request: VeritasTriggerRequest):
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

        if response.status_code in (200, 201):
            msg = f"✅ DAG '{request.dag_id}' triggered successfully at {execution_date}"
            logging.info(msg + f" | Payload: {payload}")
            return {
                "status": "success",
                "dag_id": request.dag_id,
                "execution_date": execution_date,
                "response": response.json()
            }
        else:
            msg = f"❌ DAG trigger failed: {response.status_code} - {response.text}"
            logging.error(msg)
            raise HTTPException(status_code=response.status_code, detail=response.text)

    except Exception as e:
        msg = f"🚨 Trigger error: {e}"
        logging.exception(msg)
        raise HTTPException(status_code=500, detail=str(e))
