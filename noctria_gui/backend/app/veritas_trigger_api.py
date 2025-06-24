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
logging.basicConfig(filename=log_path, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class VeritasTriggerRequest(BaseModel):
    conf: dict = {}
    dag_id: str = "veritas_master_dag"

@router.post("/trigger/veritas")
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
