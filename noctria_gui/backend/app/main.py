from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import os

app = FastAPI()

AIRFLOW_API_URL = "http://172.20.0.4:8080/api/v1"
AIRFLOW_USERNAME = os.getenv("AIRFLOW_USERNAME", "airflow")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "airflow")

class DagTriggerRequest(BaseModel):
    dag_id: str
    conf: dict | None = None

@app.post("/trigger-dag")
def trigger_dag(req: DagTriggerRequest):
    try:
        trigger_url = f"{AIRFLOW_API_URL}/dags/{req.dag_id}/dagRuns"
        payload = {
            "conf": req.conf or {},
        }

        response = requests.post(
            trigger_url,
            auth=(AIRFLOW_USERNAME, AIRFLOW_PASSWORD),
            json=payload,
            timeout=5
        )

        if response.status_code in [200, 201]:
            return {"status": "success", "dag_id": req.dag_id, "details": response.json()}
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)

    except Exception as e:
        import traceback
        traceback.print_exc()  # 標準出力にスタックトレースを表示
        raise HTTPException(status_code=500, detail=f"🚨 DAG起動中にエラー: {e}")
