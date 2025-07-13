#!/usr/bin/env python3
# coding: utf-8

"""
📌 /pdca/recheck - 戦略の再評価処理（Airflow DAG経由でスコア再計算をトリガー）
"""

from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse, RedirectResponse
from core.path_config import STRATEGIES_DIR
from pathlib import Path
import urllib.parse

# ========================================
# 修正点: ファイルツリーに基づき、正しい場所から読み込むように修正
# ========================================
# このファイル(pdca_recheck.py)から見て、一つ上の階層(noctria_gui)にある
# backend/app/ ディレクトリの中の veritas_trigger_api.py を読み込みます。
from ..backend.app.veritas_trigger_api import trigger_recheck_dag


router = APIRouter()

@router.post("/pdca/recheck")
async def recheck_strategy(strategy_name: str = Form(...)):
    """戦略の再評価をトリガーするエンドポイント"""
    strategy_path = STRATEGIES_DIR / "veritas_generated" / f"{strategy_name}.json"
    if not strategy_path.exists():
        return JSONResponse(
            status_code=404,
            content={"detail": f"戦略が存在しません: {strategy_name}"}
        )

    try:
        response = trigger_recheck_dag(strategy_name)
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

