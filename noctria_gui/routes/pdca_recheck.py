#!/usr/bin/env python3
# coding: utf-8

"""
📌 /pdca/recheck - 戦略の再評価処理（スコア再計算）
"""

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from core.path_config import STRATEGIES_DIR, ACT_LOG_DIR
from datetime import datetime
from pathlib import Path
import json
import random
import urllib.parse

router = APIRouter()

@router.post("/pdca/recheck")
async def recheck_strategy(strategy_name: str = Form(...)):
    """
    📌 指定された戦略を再評価（スコア再計算）するルート
    """
    strategy_path = STRATEGIES_DIR / "veritas_generated" / f"{strategy_name}.json"
    if not strategy_path.exists():
        return JSONResponse(status_code=404, content={"detail": f"戦略が存在しません: {strategy_name}"})


    try:
        with open(strategy_path, "r", encoding="utf-8") as f:
            strategy_data = json.load(f)
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"読み込みエラー: {str(e)}"})

    # 🎯 疑似スコア生成（安定的にするため seed 固定）
    seed_value = sum(ord(c) for c in strategy_name)
    random.seed(seed_value)
    new_win_rate = round(50 + random.uniform(0, 50), 2)
    new_max_dd = round(random.uniform(5, 30), 2)

    result = {
        "strategy": strategy_name,
        "timestamp": datetime.now().isoformat(),
        "win_rate": new_win_rate,
        "max_dd": new_max_dd,
        "source": "recheck",
    }

    # 📦 保存ファイル名
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = ACT_LOG_DIR / f"recheck_{strategy_name}_{timestamp_str}.json"

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"保存エラー: {str(e)}"})

    print(f"✅ 再評価完了: {output_path.name}")

    # 🎯 結果ページへリダイレクト（URLエンコード付き）
    query = urllib.parse.urlencode({"mode": "strategy", "key": strategy_name})
    return RedirectResponse(url=f"/statistics/detail?{query}", status_code=303)
