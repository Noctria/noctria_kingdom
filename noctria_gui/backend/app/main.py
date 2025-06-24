from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import os
from datetime import datetime

app = FastAPI(
    title="Noctria DAG Trigger API",
    description="Airflow DAGをFastAPI経由で起動",
    version="1.0.0"
)

# ✅ 環境変数からAirflow設定を取得（Docker環境でも柔軟）
AIRFLOW_API_URL = os.getenv("AIRFLOW_API_URL", "http://host.docker.internal:8080/api/v1")
AIRFLOW_USERNAME = os.getenv("AIRFLOW_USERNAME", "airflow")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "airflow")


# ✅ 入力モデル
class DagTriggerRequest(BaseModel):
    dag_id: str
    conf: dict | None = None


# ✅ DAG起動エンドポイント
@app.post("/trigger-dag")
def trigger_dag(req: DagTriggerRequest):
    trigger_url = f"{AIRFLOW_API_URL}/dags/{req.dag_id}/dagRuns"
    execution_date = datetime.utcnow().isoformat()

    payload = {
        "conf": req.conf or {},
        "execution_date": execution_date
    }

    try:
        response = requests.post(
            trigger_url,
            auth=(AIRFLOW_USERNAME, AIRFLOW_PASSWORD),
            json=payload
            timeout=5
        )

        if response.status_code in (200, 201):
            return {
                "status": "success",
                "dag_id": req.dag_id,
                "execution_date": execution_date,
                "details": response.json()
            }
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 DAG起動中にエラー: {e}")
