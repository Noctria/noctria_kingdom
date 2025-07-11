#!/usr/bin/env python3
# coding: utf-8

"""
📘 scripts/recheck_runner.py
- strategy_id を指定して再評価（スコア再計算）を行う
- Airflow DAG から呼び出されることを想定
"""

import sys
import json
import random
from datetime import datetime
from pathlib import Path

# ✅ パス設定（Noctria Kingdom 共通）
from core.path_config import STRATEGIES_DIR, ACT_LOG_DIR


def evaluate_strategy(strategy_id: str):
    """
    📊 戦略を評価してスコアを生成（仮ロジック）
    """
    strategy_path = STRATEGIES_DIR / "veritas_generated" / f"{strategy_id}.json"
    if not strategy_path.exists():
        raise FileNotFoundError(f"戦略ファイルが見つかりません: {strategy_path}")

    with open(strategy_path, "r", encoding="utf-8") as f:
        strategy_data = json.load(f)

    # 疑似的な再評価スコア（安定した値）
    seed_value = sum(ord(c) for c in strategy_id)
    random.seed(seed_value)

    win_rate = round(50 + random.uniform(0, 50), 2)
    max_dd = round(random.uniform(5, 30), 2)

    # 評価結果
    result = {
        "strategy": strategy_id,
        "timestamp": datetime.now().isoformat(),
        "win_rate": win_rate,
        "max_dd": max_dd,
        "source": "recheck_runner",
    }

    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = ACT_LOG_DIR / f"recheck_{strategy_id}_{timestamp_str}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ 再評価完了: {output_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: recheck_runner.py <strategy_id>", file=sys.stderr)
        sys.exit(1)

    strategy_id = sys.argv[1]
    try:
        evaluate_strategy(strategy_id)
    except Exception as e:
        print(f"❌ 再評価中にエラー: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
