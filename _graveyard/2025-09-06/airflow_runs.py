# noctria_gui/routes/airflow_runs.py
# -*- coding: utf-8 -*-
"""
Airflow DAG 実行履歴ビュー
- GET  /airflow/runs                : 直近の DAG 実行一覧（デフォルト: noctria_act_pipeline）
- GET  /airflow/runs/{dag_run_id}   : 個別実行の詳細（conf, state, timings, 失敗時の簡易ヒント）
- 追加: Decision Registry との相互リンク（dag_run_id や conf.decision_id をキーに突き合わせ）

依存:
- src/core/airflow_client.py に make_airflow_client() がある想定
  - 想定メソッド:
    - client.list_dag_runs(dag_id: str, limit: int = 50) -> List[dict]
    - client.get_dag_run(dag_id: str, dag_run_id: str) -> dict
    - client.get_task_instances(dag_id: str, dag_run_id: str) -> List[dict]  (任意)
    - client.get_log(dag_id: str, dag_run_id: str, task_id: str, try_number: int=1) -> str  (任意)
"""

from __future__ import annotations
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse

# Airflowクライアント
try:
    from src.core.airflow_client import make_airflow_client
except Exception:
    make_airflow_client = None  # type: ignore

# Decision Registry 照会（相互リンク用）
try:
    from src.core.decision_registry import tail_ledger, list_events
except Exception:
    tail_ledger = None  # type: ignore
    list_events = None  # type: ignore

router = APIRouter(prefix="/airflow", tags=["Airflow"])

DEFAULT_DAG_ID = "noctria_act_pipeline"


def _render(request: Request, template_name: str, **ctx: Any) -> HTMLResponse:
    """テンプレートに request を渡して描画（トースト/フィルタ利用のため）"""
    env = request.app.state.jinja_env
    tmpl = env.get_template(template_name)
    return HTMLResponse(tmpl.render(request=request, **ctx))


def _find_related_decisions_by_run(
    dag_run_id: str,
    dag_id: Optional[str],
    run_conf: Dict[str, Any] | None,
    *,
    max_scan: int = 2000,
) -> List[Dict[str, Any]]:
    """
    Decision Registry を走査して関連イベントを抽出。
    - extra_json.{dag_run_id|run_id} == dag_run_id
    - extra_json.airflow.{dag_run_id|run_id} == dag_run_id
    - extra_json.conf.{dag_run_id|run_id} == dag_run_id
    - conf.decision_id があれば、その decision_id の全イベントを付与
    """
    related: List[Dict[str, Any]] = []
    if tail_ledger is not None:
        rows = tail_ledger(n=max_scan)
        for r in rows:
            try:
                extra = json.loads(r.get("extra_json") or "{}")
            except Exception:
                extra = {}
            found_id = (
                extra.get("dag_run_id")
                or extra.get("run_id")
                or (isinstance(extra.get("airflow"), dict) and (extra["airflow"].get("dag_run_id") or extra["airflow"].get("run_id")))
                or (isinstance(extra.get("conf"), dict) and (extra["conf"].get("dag_run_id") or extra["conf"].get("run_id")))
            )
            if found_id and str(found_id) == str(dag_run_id):
                related.append(r)

    if run_conf and isinstance(run_conf, dict) and list_events is not None:
        d_id = run_conf.get("decision_id")
        if d_id:
            for ev in list_events(decision_id=str(d_id)) or []:
                # 重複を避ける（decision_id と ts_utc でユニーク化）
                if not any(x.get("decision_id") == ev.get("decision_id") and x.get("ts_utc") == ev.get("ts_utc") for x in related):
                    related.append(ev)

    # 新しい順に
    related.sort(key=lambda x: x.get("ts_utc") or "", reverse=True)
    return related


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
        failure_hint = "Git 認証・ブランチの不整合、または戦略ファイル生成パスの権限を確認してください。"

    # Decision Registry との突き合わせ
    conf = run.get("conf") if isinstance(run.get("conf"), dict) else {}
    related_decisions = _find_related_decisions_by_run(
        dag_run_id=dag_run_id,
        dag_id=dag_id,
        run_conf=conf,  # conf.decision_id を利用
    )

    return _render(
        request,
        "airflow_runs.html",
        page_title=f"🌀 Airflow Run: {dag_run_id}",
        mode="detail",
        dag_id=dag_id,
        run=run,
        task_instances=tis,
        failure_hint=failure_hint,
        related_decisions=related_decisions,
        decision_id_from_conf=(conf.get("decision_id") if isinstance(conf, dict) else None),
    )
