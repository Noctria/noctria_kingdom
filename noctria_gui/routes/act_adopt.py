# noctria_gui/routes/act_adopt.py
# -*- coding: utf-8 -*-
"""
Act層 自動採用ワークフロー（GUI連携）
- 画面: GET  /act/adopt              : フォーム表示（HUD）
- API:  POST /act/adopt/trigger      : 発火（既存互換）
- API:  POST /act/adopt              : 発火（新規; decision 連携あり）

実装方針
- 可能なら Decision を発行して Airflow をトリガ（src/core/decision_hooks.py）。
- フォールバックとして Airflow クライアントのみでも発火可能（src/core/airflow_client.py）。
- セッション toast を使って結果をHUDに通知。成功時は Run 詳細へリダイレクト。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER

# 優先: Decision発行＋Airflow起動の一体ヘルパ
try:
    from src.core.decision_hooks import create_decision_and_trigger_airflow
except Exception:  # pragma: no cover
    create_decision_and_trigger_airflow = None  # type: ignore

# 互換フォールバック: Airflow REST クライアント
try:
    from src.core.airflow_client import make_airflow_client
except Exception:  # pragma: no cover
    make_airflow_client = None  # type: ignore


router = APIRouter(prefix="/act", tags=["Act"])

# UI 初期値（旧来フォーム互換）
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


def _render(request: Request, template: str, **ctx: Any) -> HTMLResponse:
    env = request.app.state.jinja_env
    html = env.get_template(template).render(request=request, **ctx)
    return HTMLResponse(html)


@router.get("/adopt", response_class=HTMLResponse)
async def adopt_form(request: Request):
    """
    HUDフォーム表示
    - 新旧テンプレ両対応のため、page_title / default_dag_id / defaults を渡す
    """
    return _render(
        request,
        "act_adopt.html",
        page_title="⚙️ Act 手動トリガ（採用処理）",
        default_dag_id=DAG_ID,
        defaults=DEFAULTS,
    )


def _trigger_core(
    request: Request,
    *,
    dag_id: str,
    conf: Dict[str, Any],
    note: Optional[str] = None,
) -> RedirectResponse | JSONResponse:
    """
    実行コア:
      1) decision_hooks があれば Decision 発行＋Airflow 起動（conf に decision_id を同梱）
      2) なければ Airflow クライアントで直接起動（互換）
    成功時は /airflow/runs/{dag_run_id}?dag_id=... に 303 で遷移（run_id 取得できなければ一覧へ）
    """
    # 1) 推奨経路: decision_hooks
    if create_decision_and_trigger_airflow is not None:
        try:
            result = create_decision_and_trigger_airflow(
                dag_id=dag_id,
                kind="act",
                issued_by="ui",
                conf=conf,
                note=note or None,
            )
            dag_run_id = (result.get("airflow") or {}).get("dag_run_id") or ""
            decision_id = (result.get("decision") or {}).get("id") or ""
            # Toast
            try:
                request.session["toast"] = {
                    "type": "success",
                    "message": "Act をトリガしました",
                    "detail": f"decision_id={decision_id}\ndag_run_id={dag_run_id}",
                }
            except Exception:
                pass
            if dag_run_id:
                return RedirectResponse(url=f"/airflow/runs/{dag_run_id}?dag_id={dag_id}", status_code=HTTP_303_SEE_OTHER)
            return RedirectResponse(url=f"/airflow/runs?dag_id={dag_id}", status_code=HTTP_303_SEE_OTHER)
        except Exception as e:
            # hooks 経由で失敗した場合は、そのままUI通知
            try:
                request.session["toast"] = {"type": "error", "message": "Trigger failed", "detail": str(e)}
            except Exception:
                pass
            return RedirectResponse(url="/act/adopt", status_code=HTTP_303_SEE_OTHER)

    # 2) フォールバック: Airflow クライアント直接
    if make_airflow_client is None:
        # 開発時確認用: 実際には発火できないが、入力内容を返す
        return JSONResponse(
            {"ok": False, "reason": "airflow_client_not_found", "would_trigger": {"dag_id": dag_id, "conf": conf}},
            status_code=501,
        )
    try:
        client = make_airflow_client()
        resp = client.trigger_dag(dag_id, conf=conf)  # 互換API
        dag_run_id = resp.get("dag_run_id") or resp.get("run_id") or ""
        try:
            request.session["toast"] = {"type": "success", "message": f"DAG triggered: {dag_id}", "detail": str(resp)}
        except Exception:
            pass
        if dag_run_id:
            return RedirectResponse(url=f"/airflow/runs/{dag_run_id}?dag_id={dag_id}", status_code=HTTP_303_SEE_OTHER)
        return RedirectResponse(url=f"/airflow/runs?dag_id={dag_id}", status_code=HTTP_303_SEE_OTHER)
    except Exception as e:
        try:
            request.session["toast"] = {"type": "error", "message": "Trigger failed", "detail": str(e)}
        except Exception:
            pass
        return RedirectResponse(url="/act/adopt", status_code=HTTP_303_SEE_OTHER)


# 新規: POST /act/adopt でも発火できるように（推奨）
@router.post("/adopt", response_class=HTMLResponse)
async def adopt_post(
    request: Request,
    lookback_days: int = Form(DEFAULTS["LOOKBACK_DAYS"]),
    winrate_min_delta_pct: float = Form(DEFAULTS["WINRATE_MIN_DELTA_PCT"]),
    max_dd_max_delta_pct: float = Form(DEFAULTS["MAX_DD_MAX_DELTA_PCT"]),
    min_trades: int = Form(DEFAULTS["MIN_TRADES"]),
    dry_run: Optional[bool] = Form(False),
    tag_prefix: str = Form(DEFAULTS["TAG_PREFIX"]),
    release_notes: str = Form(DEFAULTS["RELEASE_NOTES"]),
    note: Optional[str] = Form(None),
):
    conf: Dict[str, Any] = {
        "LOOKBACK_DAYS": lookback_days,
        "WINRATE_MIN_DELTA_PCT": winrate_min_delta_pct,
        "MAX_DD_MAX_DELTA_PCT": max_dd_max_delta_pct,
        "MIN_TRADES": min_trades,
        "DRY_RUN": bool(dry_run),
        "TAG_PREFIX": tag_prefix,
        "RELEASE_NOTES": release_notes,
    }
    return _trigger_core(request, dag_id=DAG_ID, conf=conf, note=note)


# 既存互換: POST /act/adopt/trigger
@router.post("/adopt/trigger")
async def adopt_trigger_legacy(
    request: Request,
    lookback_days: int = Form(DEFAULTS["LOOKBACK_DAYS"]),
    winrate_min_delta_pct: float = Form(DEFAULTS["WINRATE_MIN_DELTA_PCT"]),
    max_dd_max_delta_pct: float = Form(DEFAULTS["MAX_DD_MAX_DELTA_PCT"]),
    min_trades: int = Form(DEFAULTS["MIN_TRADES"]),
    dry_run: Optional[bool] = Form(False),
    tag_prefix: str = Form(DEFAULTS["TAG_PREFIX"]),
    release_notes: str = Form(DEFAULTS["RELEASE_NOTES"]),
    note: Optional[str] = Form(None),
):
    conf: Dict[str, Any] = {
        "LOOKBACK_DAYS": lookback_days,
        "WINRATE_MIN_DELTA_PCT": winrate_min_delta_pct,
        "MAX_DD_MAX_DELTA_PCT": max_dd_max_delta_pct,
        "MIN_TRADES": min_trades,
        "DRY_RUN": bool(dry_run),
        "TAG_PREFIX": tag_prefix,
        "RELEASE_NOTES": release_notes,
    }
    return _trigger_core(request, dag_id=DAG_ID, conf=conf, note=note)
