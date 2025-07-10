# noctria_gui/routes/pdca_push.py

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse
import requests
from datetime import datetime
import os

router = APIRouter(tags=["PDCA Push"])

@router.post("/pdca/push")
async def push_strategy_to_github(strategy_name: str = Form(...)):
    """
    GitHubに戦略をPushするAirflow DAGをトリガー
    """
    dag_run_id = f"veritas_push__{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    airflow_url = "http://airflow-webserver:8080/api/v1/dags/veritas_push_dag/dagRuns"

    payload = {
        "dag_run_id": dag_run_id,
        "conf": {"strategy_name": strategy_name}
    }

    try:
        res = requests.post(
            airflow_url,
            auth=(os.getenv("AIRFLOW_USERNAME", "airflow"), os.getenv("AIRFLOW_PASSWORD", "airflow")),
            json=payload,
            timeout=10
        )
        if res.status_code in (200, 201):
            return JSONResponse({"detail": "Pushトリガー成功", "dag_run_id": dag_run_id})
        else:
            return JSONResponse(status_code=500, content={"detail": f"Airflowエラー: {res.status_code}"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"通信エラー: {e}"})
