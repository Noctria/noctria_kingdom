# core/strategy_evaluator.py

"""
📈 Veritas戦略の共通評価モジュール
- バックテスト評価結果を取得
- GUI / Airflow / CLI から再利用可能
"""

import os
from datetime import datetime
from core.strategy_optimizer_adjusted import simulate_strategy_adjusted
from core.market_loader import load_market_data

def evaluate_strategy(strategy_path: str, market_data: dict) -> dict:
    """
    📊 指定された戦略ファイルを評価し、評価指標を返す

    Parameters:
        strategy_path (str): 評価対象の戦略ファイルのパス
        market_data (dict): 市場データ（load_market_data() で取得）

    Returns:
        dict: 評価結果（勝率、DD、資産、取引数、エラーなど）
    """
    result = simulate_strategy_adjusted(strategy_path, market_data)

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "filename": os.path.basename(strategy_path),
        "status": result.get("status", "error"),
        "final_capital": result.get("final_capital"),
        "win_rate": result.get("win_rate"),
        "max_drawdown": result.get("max_drawdown"),
        "total_trades": result.get("total_trades"),
        "error_message": result.get("error_message")
    }


def is_strategy_adopted(eval_result: dict, capital_threshold: int = 1_050_000) -> bool:
    """
    ✅ 採用基準に基づいて戦略を採用するかを判定する

    Parameters:
        eval_result (dict): evaluate_strategy() の結果
        capital_threshold (int): 採用ラインの資産基準（デフォルト 105万円）

    Returns:
        bool: 採用なら True、不採用なら False
    """
    return (
        eval_result["status"] == "ok" and
        eval_result.get("final_capital", 0) >= capital_threshold
    )
