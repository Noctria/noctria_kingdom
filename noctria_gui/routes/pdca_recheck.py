#!/usr/bin/env python3
# coding: utf-8

"""
📌 /pdca/recheck - 戦略の再評価処理（スコア再計算）
"""

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from core.path_config import STRATEGIES_DIR, ACT_LOG_DIR  # 環境に応じて調整
import json
from datetime import datetime
from pathlib import Path

router = APIRouter()

@router.post("/pdca/recheck")
async def recheck_strategy(strategy_name: str = Form(...)):
    """
    📌 指定された戦略を再評価（スコア再計算）するルート
    """
    strategy_path = STRATEGIES_DIR / "veritas_generated" / f"{strategy_name}.json"
    if not strategy_path.exists():
        return JSONResponse(status_code=404, content={"detail": "戦略が存在しません"})

    # 🎯 スコア再評価（ここでは仮のロジック、必要に応じて分析関数を呼び出し）
    with open(strategy_path, "r", encoding="utf-8") as f:
        strategy_data = json.load(f)

    new_win_rate = round(50 + (hash(strategy_name) % 50), 2)  # 仮ランダム
    new_max_dd = round((hash(strategy_name[::-1]) % 30), 2)

    # 📦 結果をログとして保存
    result = {
        "strategy": strategy_name,
        "timestamp": datetime.now().isoformat(),
        "win_rate": new_win_rate,
        "max_dd": new_max_dd,
        "source": "recheck",
    }

    output_path = ACT_LOG_DIR / f"recheck_{strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ 再評価完了: {output_path.name}")
    return RedirectResponse(url="/statistics/detail?mode=strategy&key=" + strategy_name, status_code=303)
