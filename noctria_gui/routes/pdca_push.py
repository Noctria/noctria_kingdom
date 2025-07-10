from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import requests
from datetime import datetime
import os
import logging

router = APIRouter(tags=["PDCA Push"])
logger = logging.getLogger(__name__)

class DAGTriggerResponse(BaseModel):
    detail: str
    dag_run_id: str | None = None
    response_body: str | None = None

@router.post("/pdca/push", response_model=DAGTriggerResponse)
async def push_strategy_to_github(strategy_name: str = Form(...)):
    """
    GitHub に戦略を Push する Airflow DAG をトリガーするエンドポイント。
    - DAG名: veritas_push_dag
    - 引数: strategy_name（例: "Aurora_VX2"）
    """

    strategy_name = strategy_name.strip()
    if not strategy_name:
        raise HTTPException(status_code=400, detail="strategy_name が空です")

    dag_run_id = f"veritas_push__{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    airflow_url = os.getenv("AIRFLOW_BASE_URL", "http://airflow-webserver:8080")
    dag_trigger_url = f"{airflow_url}/api/v1/dags/veritas_push_dag/dagRuns"

    payload = {
        "dag_run_id": dag_run_id,
        "conf": {
            "strategy_name": strategy_name
        }
    }

    try:
        response = requests.post(
            dag_trigger_url,
            auth=(
                os.getenv("AIRFLOW_USERNAME", "airflow"),
                os.getenv("AIRFLOW_PASSWORD", "airflow")
            ),
            json=payload,
            timeout=10
        )

        if response.status_code in (200, 201):
            logger.info(f"DAG triggered successfully: {dag_run_id}")
            return DAGTriggerResponse(
                detail=f"✅ Airflow DAGトリガー成功 (Run ID: {dag_run_id})",
                dag_run_id=dag_run_id
            )

        logger.error(f"Airflow response error: HTTP {response.status_code} → {response.text}")
        return DAGTriggerResponse(
            detail=f"❌ Airflowからエラー応答 (HTTP {response.status_code})",
            response_body=response.text
        )

    except requests.RequestException as e:
        logger.exception("Airflow Webserver 通信失敗")
        return DAGTriggerResponse(
            detail=f"🚨 Airflow Webserver への通信に失敗: {str(e)}"
        )
