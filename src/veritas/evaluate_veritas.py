#!/usr/bin/env python3
# coding: utf-8

"""
⚖️ Veritas Strategy Evaluator (v2.0)
- Veritasによって生成された全戦略を評価し、結果を一つのログファイルに集約する。
- Airflow DAGから呼び出されることを想定。
"""

import importlib.util
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd

# --- 王国の基盤モジュールをインポート ---
# ✅ 修正: path_configから必要な変数を正しくインポート
from src.core.path_config import STRATEGIES_VERITAS_GENERATED_DIR, DATA_DIR, VERITAS_EVAL_LOG

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

# --- 王国の戦略採用基準 ---
WIN_RATE_THRESHOLD = 0.50  # 最低勝率 50%
MAX_DRAWDOWN_THRESHOLD = 0.30 # 最大許容ドローダウン 30%
MIN_TRADES_THRESHOLD = 10 # 最低取引回数

# 評価対象データ
TEST_DATA_PATH = DATA_DIR / "sample_test_data.csv"

def _load_strategy_module(strategy_path: Path):
    """戦略ファイルを動的に読み込み、モジュールとして返す"""
    try:
        module_name = strategy_path.stem
        spec = importlib.util.spec_from_file_location(module_name, strategy_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"モジュールの仕様を読み込めません: {strategy_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        logging.error(f"戦略モジュールの動的読み込みに失敗しました: {strategy_path}, エラー: {e}", exc_info=True)
        return None

def _is_strategy_adopted(result: Dict[str, Any]) -> bool:
    """評価結果が、王国の採用基準を満たしているかを判断する"""
    return (
        result.get("final_capital", 0) > 1_000_000 and
        result.get("win_rate", 0.0) >= WIN_RATE_THRESHOLD and
        result.get("max_drawdown", 1.0) <= MAX_DRAWDOWN_THRESHOLD and
        result.get("total_trades", 0) >= MIN_TRADES_THRESHOLD
    )

def _evaluate_single_strategy(strategy_path: Path, test_data: pd.DataFrame) -> Dict[str, Any]:
    """単一の戦略を評価し、結果を辞書として返す"""
    strategy_module = _load_strategy_module(strategy_path)
    if not hasattr(strategy_module, 'simulate'):
        return {"strategy": strategy_path.name, "error": "simulate関数が存在しません。", "passed": False}

    try:
        result = strategy_module.simulate(test_data)
        result["strategy"] = strategy_path.name
        result["passed"] = _is_strategy_adopted(result)
        return result
    except Exception as e:
        logging.error(f"戦略『{strategy_path.name}』のシミュレーション中にエラー: {e}", exc_info=True)
        return {"strategy": strategy_path.name, "error": str(e), "passed": False}

def main():
    """
    Airflowから呼び出されるメイン関数。
    生成された全ての戦略を評価し、結果を一つのJSONファイルに集約する。
    """
    logging.info("⚖️ [Veritas] 全戦略の評価を開始します…")

    if not TEST_DATA_PATH.exists():
        logging.error(f"評価用データが見つかりません: {TEST_DATA_PATH}")
        raise FileNotFoundError(f"Test data not found: {TEST_DATA_PATH}")
    
    test_data = pd.read_csv(TEST_DATA_PATH)
    results = []

    if not STRATEGIES_VERITAS_GENERATED_DIR.exists():
        logging.warning(f"評価対象の戦略ディレクトリが存在しません: {STRATEGIES_VERITAS_GENERATED_DIR}")
    else:
        strategy_files = sorted(STRATEGIES_VERITAS_GENERATED_DIR.glob("*.py"))
        logging.info(f"{len(strategy_files)}件の戦略を評価対象として発見しました。")
        for path in strategy_files:
            result = _evaluate_single_strategy(path, test_data)
            results.append(result)

    # 評価結果ログを保存
    try:
        VERITAS_EVAL_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(VERITAS_EVAL_LOG, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    except IOError as e:
        logging.error(f"評価ログの書き込みに失敗しました: {VERITAS_EVAL_LOG}, エラー: {e}")

    total = len(results)
    passed_count = sum(1 for r in results if r.get("passed"))
    
    logging.info(f"🧠 評価完了: {total}件の戦略を審査しました。")
    logging.info(f"✅ 採用基準を満たした戦略数: {passed_count}")
    logging.info("📜 王国訓示:『知を吟味し、未来を選び取る者こそ、王国の盾なり』")

# ✅ スクリプト直接実行時（開発・手動検証用）
if __name__ == "__main__":
    main()
