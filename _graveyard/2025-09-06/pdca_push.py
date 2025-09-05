#!/usr/bin/env python3
# coding: utf-8

"""
📌 /pdca/push - 戦略のGitHub Push処理トリガールート
- 戦略IDを受け取り、AirflowのPush DAGをREST API経由で起動する
"""

from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse, RedirectResponse
from core.veritas_trigger_api import trigger_generate_dag, trigger_recheck_dag  # AirflowトリガーAPI関数
from src.core.path_config import STRATEGIES_DIR
from pathlib import Path
import urllib.parse

router = APIRouter()

@router.post("/pdca/push")
async def push_strategy(strategy_name: str = Form(...)):
    """戦略のGitHub Push処理をトリガーするエンドポイント"""
    strategy_path = STRATEGIES_DIR / "veritas_generated" / f"{strategy_name}.json"
    if not strategy_path.exists():
        return JSONResponse(
            status_code=404,
            content={"detail": f"戦略が存在しません: {strategy_name}"}
        )

    try:
        response = trigger_push_dag(strategy_name)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Airflow DAGトリガー失敗: {str(e)}"}
        )

    if response.status_code not in [200, 201, 202]:
        return JSONResponse(
            status_code=response.status_code,
            content={"detail": f"DAGトリガー失敗: {response.text}"}
        )

    query = urllib.parse.urlencode({"mode": "strategy", "key": strategy_name})
    return RedirectResponse(url=f"/statistics/detail?{query}", status_code=303)


def trigger_push_dag(strategy_name: str):
    """内部関数：AirflowのPush DAGをREST API経由でトリガー"""
    from os import getenv
    import requests
    from datetime import datetime

    AIRFLOW_API_URL = getenv("AIRFLOW_API_URL", "http://localhost:8080/api/v1")
    AIRFLOW_USERNAME = getenv("AIRFLOW_USERNAME", "airflow")
    AIRFLOW_PASSWORD = getenv("AIRFLOW_PASSWORD", "airflow")
    dag_id = "veritas_push_dag"

    execution_date = datetime.utcnow().isoformat()
    payload = {
        "conf": {"strategy_id": strategy_name},
        "execution_date": execution_date
    }

    trigger_url = f"{AIRFLOW_API_URL}/dags/{dag_id}/dagRuns"

    response = requests.post(
        trigger_url,
        auth=(AIRFLOW_USERNAME, AIRFLOW_PASSWORD),
        json=payload
    )
    return response
