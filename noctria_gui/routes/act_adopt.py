# noctria_gui/routes/act_adopt.py
# -*- coding: utf-8 -*-
"""
Act層 自動採用ワークフロー（GUI連携）
- 画面: GET /act/adopt        : フォーム表示（HUD）
- API:  POST /act/adopt/trigger: Airflowの noctria_act_pipeline をトリガ
依存:
- src/core/airflow_client.py: make_airflow_client() が Airflow REST API クライアントを返す
  - 例: client.trigger_dag(dag_id, conf: dict) -> dict
"""

from __future__ import annotations
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.status import HTTP_302_FOUND

try:
    # 既存のAirflow RESTクライアントを利用
    from src.core.airflow_client import make_airflow_client
except Exception as e:  # フォールバック（存在しない場合でもGUIは生かす）
    make_airflow_client = None  # type: ignore

router = APIRouter(prefix="/act", tags=["Act"])

# デフォルト値（UIの初期値）
DEFAULTS = {
    "LOOKBACK_DAYS": 30,
    "WINRATE_MIN_DELTA_PCT": 3.0,
    "MAX_DD_MAX_DELTA_PCT": 2.0,
    "MIN_TRADES": 30,
    "DRY_RUN": False,
    "TAG_PREFIX": "veritas",
    "RELEASE_NOTES": "PDCA auto adopt",
}

DAG_ID = "noctria_act_pipeline"


@router.get("/adopt", response_class=HTMLResponse)
async def adopt_form(request: Request):
    """
    HUDフォーム表示
    """
    return request.app.state.jinja_env.get_template("act_adopt.html").render(defaults=DEFAULTS)


@router.post("/adopt/trigger")
async def adopt_trigger(
    request: Request,
    lookback_days: int = Form(DEFAULTS["LOOKBACK_DAYS"]),
    winrate_min_delta_pct: float = Form(DEFAULTS["WINRATE_MIN_DELTA_PCT"]),
    max_dd_max_delta_pct: float = Form(DEFAULTS["MAX_DD_MAX_DELTA_PCT"]),
    min_trades: int = Form(DEFAULTS["MIN_TRADES"]),
    dry_run: Optional[bool] = Form(False),
    tag_prefix: str = Form(DEFAULTS["TAG_PREFIX"]),
    release_notes: str = Form(DEFAULTS["RELEASE_NOTES"]),
):
    """
    Airflow の DAG を REST でトリガ
    """
    conf: Dict[str, Any] = {
        "LOOKBACK_DAYS": lookback_days,
        "WINRATE_MIN_DELTA_PCT": winrate_min_delta_pct,
        "MAX_DD_MAX_DELTA_PCT": max_dd_max_delta_pct,
        "MIN_TRADES": min_trades,
        "DRY_RUN": bool(dry_run),
        "TAG_PREFIX": tag_prefix,
        "RELEASE_NOTES": release_notes,
    }

    # Airflowクライアントの解決
    if make_airflow_client is None:
        # 既存ユーティリティが未配備でも、要求JSONを返せるようにする（開発時確認用）
        return JSONResponse(
            {
                "ok": False,
                "reason": "airflow_client_not_found",
                "would_trigger": {"dag_id": DAG_ID, "conf": conf},
            },
            status_code=501,
        )

    try:
        client = make_airflow_client()
        resp = client.trigger_dag(DAG_ID, conf=conf)  # 実装想定: dict を返す
        # 画面に戻して通知
        request.session["toast"] = {"type": "success", "message": f"DAG triggered: {DAG_ID}", "detail": resp}
        return RedirectResponse(url="/act/adopt", status_code=HTTP_302_FOUND)
    except Exception as e:
        request.session["toast"] = {"type": "error", "message": "Trigger failed", "detail": str(e)}
        return RedirectResponse(url="/act/adopt", status_code=HTTP_302_FOUND)
