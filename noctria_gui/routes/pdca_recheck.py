# noctria_gui/routes/pdca_recheck.py
# -*- coding: utf-8 -*-
"""
📌 /pdca/recheck — 単一戦略の再評価トリガ（方式2: Airflow REST API）
- 既存の core.veritas_trigger_api 依存を排し、共通クライアント (src/core/airflow_client.py) を使用
- 観測ログ (observability) にトリガ結果を記録（失敗しても本処理を止めない）
- 成功時は /statistics/detail?mode=strategy&key={strategy_name} へ 303 Redirect
"""

from __future__ import annotations

import os
import uuid
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# プロジェクトの標準パス設定（src 配下の絶対 import 前提）
from src.core.path_config import STRATEGIES_DIR, NOCTRIA_GUI_TEMPLATES_DIR
from src.core.airflow_client import make_airflow_client

# 観測ログ（存在しない/未配備でも動作を止めない）
try:
    from src.plan_data.observability import ensure_tables, log_infer_call  # type: ignore
except Exception:  # pragma: no cover
    ensure_tables = None
    log_infer_call = None  # type: ignore

router = APIRouter(prefix="/pdca", tags=["PDCA"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# 環境変数でデフォルトDAGを切り替え可能（単体評価用DAGを想定）
DEFAULT_SINGLE_RECHECK_DAG = os.getenv("AIRFLOW_DAG_RECHECK_SINGLE", "veritas_eval_single_dag")
SCHEMA_VERSION = "2025-08-01"


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _obs_safe_log(trace_id: str, ai_name: str, params: Dict[str, Any], metrics: Dict[str, Any], status: str, note: str) -> None:
    if ensure_tables and log_infer_call:
        try:
            ensure_tables()
            now_iso = _now_utc_iso()
            log_infer_call(
                trace_id=trace_id,
                ai_name=ai_name,
                started_at=now_iso,
                ended_at=now_iso,
                params_json=params,
                metrics_json=metrics,
                status=status,
                note=note,
            )
        except Exception:
            # 観測ログの失敗は機能に影響させない
            pass


@router.post("/recheck")
async def recheck_strategy(strategy_name: str = Form(...)):
    """
    単一戦略の再評価を Airflow REST API でトリガする。
    - フォーム入力: strategy_name
    - 成功: /statistics/detail?mode=strategy&key={strategy_name} へ 303 Redirect
    - 失敗: JSON で詳細返却
    """
    # 1) 戦略ファイルの存在を確認（veritas_generated/{name}.json）
    strategy_path: Path = STRATEGIES_DIR / "veritas_generated" / f"{strategy_name}.json"
    if not strategy_path.exists():
        return JSONResponse(
            status_code=404,
            content={"detail": f"戦略が存在しません: {strategy_name}", "strategy_name": strategy_name},
        )

    # 2) Airflow DAG をトリガ
    dag_id = DEFAULT_SINGLE_RECHECK_DAG.strip()
    trace_id = str(uuid.uuid4())
    conf: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "trigger_source": "GUI",
        "trace_id": trace_id,
        "requested_at": _now_utc_iso(),
        "mode": "strategy",
        "strategy_name": strategy_name,
        # DAG 側で解釈可能な将来拡張パラメータ
        "reason": "single_recheck",
        "dry_run": False,
    }

    try:
        client = make_airflow_client()
        res = client.trigger_dag_run(
            dag_id=dag_id,
            conf=conf,
            note=f"Single Recheck from GUI (strategy={strategy_name}, trace_id={trace_id})",
        )
        dag_run_id = res.get("dag_run_id")

        # 観測ログ（成功）
        _obs_safe_log(
            trace_id=trace_id,
            ai_name="PDCA_SingleRecheckTrigger",
            params={"dag_id": dag_id, **conf},
            metrics={"dag_run_id": dag_run_id or "", "response": res},
            status="success",
            note="GUI trigger single recheck",
        )

    except Exception as e:
        # 観測ログ（失敗）
        _obs_safe_log(
            trace_id=trace_id,
            ai_name="PDCA_SingleRecheckTrigger",
            params={"dag_id": dag_id, **conf},
            metrics={"error": str(e)},
            status="failed",
            note="GUI trigger single recheck failed",
        )
        return JSONResponse(
            status_code=500,
            content={"detail": f"Airflow DAGトリガー失敗: {str(e)}", "strategy_name": strategy_name},
        )

    # 3) 成功時、統計詳細ページへリダイレクト
    query = urllib.parse.urlencode(
        {
            "mode": "strategy",
            "key": strategy_name,
            # デバッグ/追跡用（任意でUI側が表示に使える）
            "trace_id": trace_id,
        }
    )
    return RedirectResponse(url=f"/statistics/detail?{query}", status_code=303)


@router.get("/history", summary="PDCA履歴ページ")
async def pdca_history(request: Request):
    """
    PDCA 履歴のプレースホルダページ。
    必要に応じて DB/ログから履歴を取得し、テンプレートへ渡す拡張を想定。
    """
    return templates.TemplateResponse("pdca/history.html", {"request": request})
