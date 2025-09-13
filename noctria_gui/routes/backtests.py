# noctria_gui/routes/backtests.py
# -*- coding: utf-8 -*-
"""
📊 Backtests Routes (一覧 + 詳細ビュー)

- GET /backtests/            : DAG 実行履歴の一覧
- GET /backtests/{dag_run_id}: 個別の実行詳細ビュー
"""

from __future__ import annotations

import os
import typing as t

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from starlette.templating import Jinja2Templates

try:
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore

# ----------------------------------------------------------------------------
# 設定
# ----------------------------------------------------------------------------
router = APIRouter()
templates = Jinja2Templates(directory="noctria_gui/templates")

AIRFLOW_BASE_URL = os.getenv("AIRFLOW_BASE_URL", "http://localhost:8080")
AIRFLOW_USER = os.getenv("AIRFLOW_USER", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")
DAG_ID = os.getenv("NOCTRIA_BACKTEST_DAG_ID", "noctria_backtest_dag")


# ----------------------------------------------------------------------------
# ユーティリティ
# ----------------------------------------------------------------------------
def _get_dag_runs(limit: int = 20) -> t.List[dict]:
    """
    Airflow REST API から DAG 実行一覧を取得する。
    REST が利用できない場合はダミーデータを返す。
    """
    if not requests:
        return [
            {
                "dag_run_id": "manual__2025-09-13T08:37:43.557371",
                "state": "success",
                "start_date": "2025-09-13T08:37:43",
            }
        ]

    try:
        url = f"{AIRFLOW_BASE_URL.rstrip('/')}/api/v1/dags/{DAG_ID}/dagRuns"
        params = {"order_by": "-execution_date", "limit": limit}
        auth = (AIRFLOW_USER, AIRFLOW_PASSWORD) if (AIRFLOW_USER and AIRFLOW_PASSWORD) else None
        headers = {}
        token = os.getenv("AIRFLOW_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
            auth = None
        resp = requests.get(url, params=params, auth=auth, headers=headers, timeout=10)
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data.get("dag_runs", [])
    except Exception:
        return []


def _get_dag_run_detail(dag_run_id: str) -> dict:
    """
    単一 DAG 実行の詳細を取得する。
    REST が利用できない場合はダミーを返す。
    """
    if not requests:
        return {
            "dag_run_id": dag_run_id,
            "state": "success",
            "start_date": "2025-09-13T08:37:43",
            "end_date": "2025-09-13T09:05:00",
            "conf": {"strategy_glob": "src/strategies/veritas_generated/**.py"},
        }

    try:
        url = f"{AIRFLOW_BASE_URL.rstrip('/')}/api/v1/dags/{DAG_ID}/dagRuns/{dag_run_id}"
        auth = (AIRFLOW_USER, AIRFLOW_PASSWORD) if (AIRFLOW_USER and AIRFLOW_PASSWORD) else None
        headers = {}
        token = os.getenv("AIRFLOW_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
            auth = None
        resp = requests.get(url, auth=auth, headers=headers, timeout=10)
        if resp.status_code != 200:
            return {}
        return resp.json()
    except Exception:
        return {}


# ----------------------------------------------------------------------------
# ルート
# ----------------------------------------------------------------------------
@router.get("/backtests/", response_class=HTMLResponse)
async def backtests_list(request: Request):
    """
    バックテスト一覧
    """
    dag_runs = _get_dag_runs()
    return templates.TemplateResponse(
        "backtests.html", {"request": request, "dag_runs": dag_runs}
    )


@router.get("/backtests/{dag_run_id}", response_class=HTMLResponse)
async def backtest_detail(request: Request, dag_run_id: str):
    """
    個別バックテスト詳細
    """
    detail = _get_dag_run_detail(dag_run_id)
    if not detail:
        return HTMLResponse(f"<pre>run_id={dag_run_id} not found</pre>", status_code=404)

    # Airflow Web UI へのリンクも用意
    detail["logs_url"] = f"{AIRFLOW_BASE_URL.rstrip('/')}/dags/{DAG_ID}/grid?dag_run_id={dag_run_id}"

    return templates.TemplateResponse(
        "backtest_detail.html", {"request": request, "detail": detail}
    )
