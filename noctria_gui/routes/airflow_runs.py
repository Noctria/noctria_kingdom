# noctria_gui/routes/airflow_runs.py
# -*- coding: utf-8 -*-
"""
Airflow DAG 実行履歴ビュー
- GET  /airflow/runs                : 直近の DAG 実行一覧（デフォルト: noctria_act_pipeline）
- GET  /airflow/runs/{dag_run_id}   : 個別実行の詳細（conf, state, timings, 失敗時の簡易ヒント）

依存:
- src/core/airflow_client.py に make_airflow_client() がある想定
  - 想定メソッド:
    - client.list_dag_runs(dag_id: str, limit: int = 50) -> List[dict]
    - client.get_dag_run(dag_id: str, dag_run_id: str) -> dict
    - client.get_task_instances(dag_id: str, dag_run_id: str) -> List[dict]  (任意)
    - client.get_log(dag_id: str, dag_run_id: str, task_id: str, try_number: int=1) -> str  (任意)
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse

try:
    from src.core.airflow_client import make_airflow_client
except Exception:
    make_airflow_client = None  # type: ignore

router = APIRouter(prefix="/airflow", tags=["Airflow"])

DEFAULT_DAG_ID = "noctria_act_pipeline"

def _render(request: Request, template_name: str, **ctx: Any) -> HTMLResponse:
    env = request.app.state.jinja_env
    tmpl = env.get_template(template_name)
    return HTMLResponse(tmpl.render(**ctx))

@router.get("/runs", response_class=HTMLResponse)
async def runs_index(
    request: Request,
    dag_id: str = Query(DEFAULT_DAG_ID),
    limit: int = Query(50, ge=1, le=200),
):
    if make_airflow_client is None:
        return HTMLResponse(
            "<h1>Airflow クライアント未配備</h1><p>src/core/airflow_client.py を配置してください。</p>",
            status_code=501,
        )
    client = make_airflow_client()
    try:
        runs: List[Dict[str, Any]] = client.list_dag_runs(dag_id=dag_id, limit=limit) or []
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Airflow API error: {e}")

    return _render(
        request,
        "airflow_runs.html",
        page_title=f"🌀 Airflow Runs — {dag_id}",
        mode="index",
        dag_id=dag_id,
        runs=runs,
        limit=limit,
    )

@router.get("/runs/{dag_run_id}", response_class=HTMLResponse)
async def run_detail(
    request: Request,
    dag_run_id: str,
    dag_id: str = Query(DEFAULT_DAG_ID),
):
    if make_airflow_client is None:
        return HTMLResponse(
            "<h1>Airflow クライアント未配備</h1><p>src/core/airflow_client.py を配置してください。</p>",
            status_code=501,
        )
    client = make_airflow_client()
    try:
        run: Dict[str, Any] = client.get_dag_run(dag_id=dag_id, dag_run_id=dag_run_id) or {}
        tis: List[Dict[str, Any]] = []
        try:
            tis = client.get_task_instances(dag_id=dag_id, dag_run_id=dag_run_id) or []
        except Exception:
            pass
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Airflow API error: {e}")

    if not run:
        raise HTTPException(status_code=404, detail="dag_run not found")

    # 失敗時の簡易ヒント（Best-effort）
    failure_hint = None
    if (run.get("state") or "").lower() in ("failed", "up_for_retry"):
        # よくある失敗: Git push 認証 / repo 不整合 / ファイル権限
        failure_hint = "Git 認証・ブランチの不整合、または戦略ファイル生成パスの権限を確認してください。"

    return _render(
        request,
        "airflow_runs.html",
        page_title=f"🌀 Airflow Run: {dag_run_id}",
        mode="detail",
        dag_id=dag_id,
        run=run,
        task_instances=tis,
        failure_hint=failure_hint,
    )
