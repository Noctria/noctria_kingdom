#!/usr/bin/env python3
# coding: utf-8

"""
📌 /pdca/recheck - 戦略の再評価処理（Airflow DAG経由でスコア再計算をトリガー）
"""

from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse, RedirectResponse
from core.path_config import STRATEGIES_DIR
from backend.app.veritas_trigger_api import trigger_recheck_dag  # 🔥 Airflow連携トリガー関数
from pathlib import Path
import urllib.parse

router = APIRouter()

@router.post("/pdca/recheck")
async def recheck_strategy(strategy_name: str = Form(...)):
    """
    📌 指定された戦略を再評価（スコア再計算）するルート
    - Airflow の recheck DAG を REST API 経由で実行
    """
    strategy_path = STRATEGIES_DIR / "veritas_generated" / f"{strategy_name}.json"
    if not strategy_path.exists():
        return JSONResponse(
            status_code=404,
            content={"detail": f"戦略が存在しません: {strategy_name}"}
        )

    try:
        # ✅ Airflow DAG 実行（非同期トリガー）
        response = trigger_recheck_dag(strategy_name)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Airflow DAGトリガー失敗: {str(e)}"}
        )

    # 💥 エラーレスポンス検知
    if response.status_code not in [200, 201, 202]:
        return JSONResponse(
            status_code=response.status_code,
            content={"detail": f"DAGトリガー失敗: {response.text}"}
        )

    # 🎯 結果ページへリダイレクト（URLエンコード付き）
    query = urllib.parse.urlencode({"mode": "strategy", "key": strategy_name})
    return RedirectResponse(url=f"/statistics/detail?{query}", status_code=303)
