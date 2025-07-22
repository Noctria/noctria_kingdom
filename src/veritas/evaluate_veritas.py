#!/usr/bin/env python3
# coding: utf-8

"""
⚖️ Veritas Machina Evaluator (ML専用)
- Veritasが生成した全ML戦略を評価し、合格戦略をJSONに集約
- Airflow等のワークフローからも直接呼び出し可能
"""

import importlib.util
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd

# --- 王国の基盤モジュールをインポート ---
from src.core.path_config import STRATEGIES_VERITAS_GENERATED_DIR, DATA_DIR, VERITAS_EVAL_LOG

# ロガー設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

# --- 戦略採用基準（ML的な数値重視） ---
WIN_RATE_THRESHOLD = 0.50      # 最低勝率50%
MAX_DRAWDOWN_THRESHOLD = 0.30  # 最大ドローダウン30%
MIN_TRADES_THRESHOLD = 10      # 最低取引回数

TEST_DATA_PATH = DATA_DIR / "sample_test_data.csv"

def _load_strategy_module(strategy_path: Path):
    """戦略ファイルを動的にimportしモジュールとして返す"""
    try:
        module_name = strategy_path.stem
        spec = importlib.util.spec_from_file_location(module_name, strategy_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"モジュール仕様の取得失敗: {strategy_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        logging.error(f"戦略モジュール読み込み失敗: {strategy_path}, エラー: {e}", exc_info=True)
        return None

def _is_strategy_adopted(result: Dict[str, Any]) -> bool:
    """王国採用基準（ML/数値基準）判定"""
    return (
        result.get("final_capital", 0) > 1_000_000 and
        result.get("win_rate", 0.0) >= WIN_RATE_THRESHOLD and
        result.get("max_drawdown", 1.0) <= MAX_DRAWDOWN_THRESHOLD and
        result.get("total_trades", 0) >= MIN_TRADES_THRESHOLD
    )

def _evaluate_single_strategy(strategy_path: Path, test_data: pd.DataFrame) -> Dict[str, Any]:
    """単一戦略を評価し辞書で返却"""
    strategy_module = _load_strategy_module(strategy_path)
    if not hasattr(strategy_module, 'simulate'):
        return {"strategy": strategy_path.name, "error": "simulate関数が存在しません。", "passed": False}

    try:
        result = strategy_module.simulate(test_data)
        result["strategy"] = strategy_path.name
        result["passed"] = _is_strategy_adopted(result)
        return result
    except Exception as e:
        logging.error(f"戦略『{strategy_path.name}』評価エラー: {e}", exc_info=True)
        return {"strategy": strategy_path.name, "error": str(e), "passed": False}

def main():
    """Airflow等から呼び出し可能なメイン関数"""
    logging.info("⚖️ [Veritas Machina] 全戦略の評価を開始します…")
    if not TEST_DATA_PATH.exists():
        logging.error(f"評価用データが見つかりません: {TEST_DATA_PATH}")
        raise FileNotFoundError(f"Test data not found: {TEST_DATA_PATH}")

    test_data = pd.read_csv(TEST_DATA_PATH)
    results = []

    if not STRATEGIES_VERITAS_GENERATED_DIR.exists():
        logging.warning(f"戦略ディレクトリが存在しません: {STRATEGIES_VERITAS_GENERATED_DIR}")
    else:
        strategy_files = sorted(STRATEGIES_VERITAS_GENERATED_DIR.glob("*.py"))
        logging.info(f"{len(strategy_files)}件の戦略を発見。")
        for path in strategy_files:
            result = _evaluate_single_strategy(path, test_data)
            results.append(result)

    # 評価結果ログ保存
    try:
        VERITAS_EVAL_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(VERITAS_EVAL_LOG, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    except IOError as e:
        logging.error(f"評価ログ書き込み失敗: {VERITAS_EVAL_LOG}, エラー: {e}")

    total = len(results)
    passed_count = sum(1 for r in results if r.get("passed"))
    logging.info(f"🧠 評価完了: {total}件の戦略を審査、合格: {passed_count}件")
    logging.info("📜 訓示:『数の知恵を集めよ、勝利の礎となすべし』")

if __name__ == "__main__":
    main()
