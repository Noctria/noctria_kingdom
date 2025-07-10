# noctria_gui/routes/pdca_push.py

from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse
import requests
from datetime import datetime
import os

router = APIRouter(tags=["PDCA Push"])

@router.post("/pdca/push")
async def push_strategy_to_github(strategy_name: str = Form(...)):
    """
    GitHub に戦略を Push する Airflow DAG をトリガーするエンドポイント。
    - DAG名: veritas_push_dag
    - 引数: strategy_name
    """

    # DAG 実行 ID をユニークなタイムスタンプで生成
    dag_run_id = f"veritas_push__{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Airflow Webserver エンドポイントを環境変数から取得（またはデフォルト）
    airflow_url = os.getenv("AIRFLOW_BASE_URL", "http://airflow-webserver:8080")
    dag_trigger_url = f"{airflow_url}/api/v1/dags/veritas_push_dag/dagRuns"

    # 実行時パラメータ
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
            return JSONResponse(
                status_code=200,
                content={
                    "detail": f"✅ Airflow DAGトリガー成功 (Run ID: {dag_run_id})",
                    "dag_run_id": dag_run_id
                }
            )
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "detail": f"❌ Airflowからエラー応答 (HTTP {response.status_code})",
                    "response_body": response.text
                }
            )

    except requests.RequestException as e:
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"🚨 Airflow Webserver への通信に失敗: {str(e)}"
            }
        )
