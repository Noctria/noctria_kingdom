#!/usr/bin/env python3
# coding: utf-8

"""
📊 Strategy Evaluator (v2.0)
- Veritasによって生成された戦略を評価し、採用基準を満たすか判断する。
- 評価ロジックとログ保存ロジックを分離し、モジュール性を高める。
"""

import json
import random
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# --- 王国の基盤モジュールをインポート ---
from src.core.path_config import STRATEGIES_VERITAS_GENERATED_DIR, ACT_LOG_DIR

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

# --- 王国の戦略採用基準 ---
WIN_RATE_THRESHOLD = 60.0  # 最低勝率
MAX_DRAWDOWN_THRESHOLD = 20.0 # 最大許容ドローダウン


def is_strategy_adopted(evaluation_result: Dict[str, Any]) -> bool:
    """
    評価結果が、王国の採用基準を満たしているかを判断する。
    """
    win_rate = evaluation_result.get("win_rate", 0)
    max_drawdown = evaluation_result.get("max_drawdown", 100)

    if win_rate >= WIN_RATE_THRESHOLD and max_drawdown <= MAX_DRAWDOWN_THRESHOLD:
        logging.info(f"戦略『{evaluation_result.get('strategy')}』は採用基準を満たしました。")
        return True
    else:
        logging.info(f"戦略『{evaluation_result.get('strategy')}』は基準未達です。(勝率: {win_rate}%, DD: {max_drawdown}%)")
        return False


def evaluate_strategy(strategy_id: str) -> Dict[str, Any]:
    """
    指定された戦略を評価し、その性能指標を算出する（現在はダミー）。
    """
    logging.info(f"戦略『{strategy_id}』の真価を問う、評価の儀を開始します…")
    strategy_path = STRATEGIES_VERITAS_GENERATED_DIR / f"{strategy_id}.py"
    
    if not strategy_path.exists():
        logging.error(f"評価対象の戦略ファイルが見つかりません: {strategy_path}")
        raise FileNotFoundError(f"Strategy file not found: {strategy_path}")

    # --- ここに実際のバックテストやシミュレーションのロジックを実装 ---
    # (現在はダミーの評価結果を生成)
    seed_value = sum(ord(c) for c in strategy_id)
    random.seed(seed_value)
    win_rate = round(random.uniform(50, 75), 2)
    max_drawdown = round(random.uniform(5, 30), 2)
    # --- ここまでダミー処理 ---

    result = {
        "strategy": strategy_id,
        "timestamp": datetime.now().isoformat(),
        "win_rate": win_rate,
        "max_drawdown": max_drawdown,
        "source": "evaluate_strategy",
    }
    
    # 評価結果に、採用基準を満たしたかどうかのフラグを追加
    result["passed"] = is_strategy_adopted(result)
    
    logging.info(f"戦略『{strategy_id}』の評価完了。")
    return result


def log_evaluation_result(evaluation_result: Dict[str, Any]):
    """
    評価結果をJSONファイルとして王国の書庫に記録する。
    """
    strategy_id = evaluation_result.get("strategy")
    if not strategy_id:
        logging.error("記録すべき戦略IDが存在しません。")
        return

    try:
        ACT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = ACT_LOG_DIR / f"eval_{strategy_id}_{timestamp_str}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(evaluation_result, f, ensure_ascii=False, indent=2)
        logging.info(f"評価記録を書庫に納めました: {output_path}")
    except Exception as e:
        logging.error(f"評価記録の保存中にエラーが発生しました: {e}", exc_info=True)


# ========================================
# ✅ 単体テスト＆実行ブロック
# ========================================
if __name__ == "__main__":
    logging.info("--- 戦略評価モジュールの単体テストを開始 ---")
    
    # テスト用のダミー戦略ファイルを作成
    dummy_strategy_id = "veritas_test_strategy_001"
    dummy_file_path = STRATEGIES_VERITAS_GENERATED_DIR / f"{dummy_strategy_id}.py"
    dummy_file_path.parent.mkdir(parents=True, exist_ok=True)
    dummy_file_path.write_text("# This is a dummy strategy file for testing.")
    
    # 1. 戦略を評価
    eval_result = evaluate_strategy(dummy_strategy_id)
    print("\n[評価結果]:")
    print(json.dumps(eval_result, indent=2, ensure_ascii=False))

    # 2. 評価結果をログに記録
    log_evaluation_result(eval_result)
    
    # 3. ダミーファイルを削除
    dummy_file_path.unlink()
    
    logging.info("--- 戦略評価モジュールの単体テストを完了 ---")
