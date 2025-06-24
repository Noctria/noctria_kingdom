from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os

app = FastAPI()

# Airflow Webserver APIエンドポイント（Dockerコンテナからアクセスする想定）
AIRFLOW_API_URL = "http://host.docker.internal:8080/api/v1"
AIRFLOW_USERNAME = os.getenv("AIRFLOW_USERNAME", "airflow")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "airflow")  # Airflow default creds

class DagTriggerRequest(BaseModel):
    dag_id: str
    conf: dict | None = None

@app.post("/trigger-dag")
def trigger_dag(req: DagTriggerRequest):
    trigger_url = f"{AIRFLOW_API_URL}/dags/{req.dag_id}/dagRuns"
    response = requests.post(
        trigger_url,
        auth=(AIRFLOW_USERNAME, AIRFLOW_PASSWORD),
        json={"conf": req.conf or {}}
    )

    if response.status_code == 200 or response.status_code == 201:
        return {"status": "success", "dag_id": req.dag_id, "details": response.json()}
    else:
        return {"status": "error", "message": response.text}
